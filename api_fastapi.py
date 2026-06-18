"""
FastAPI Backend for Gold Price Dashboard
Modern, high-performance API with automatic documentation and WebSocket support
"""

from fastapi import FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, timedelta
import requests
import os
import asyncio
import json

# Import modules
try:
    from config import API_KEY
except ImportError:
    API_KEY = None

try:
    from data_analyzer import GoldPriceAnalyzer
    from data_collector import HistoricalDataCollector
except ImportError:
    GoldPriceAnalyzer = None
    HistoricalDataCollector = None

# Initialize FastAPI app
app = FastAPI(
    title="Gold Price Dashboard API",
    description="Vietnamese Gold Price Monitoring and Analytics API",
    version="2.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services
class GoldPriceAPI:
    """Handle API requests to the Gold Price API"""
    
    BASE_URL = "https://vapi.vnappmob.com"
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key
        self.headers = {
            'Accept': 'application/json'
        }
        if api_key:
            self.headers['Authorization'] = f'Bearer {api_key}'
    
    def get_company_price(self, company: str, date_from: Optional[str] = None, 
                         date_to: Optional[str] = None) -> Optional[Dict]:
        """Get gold price for a specific company"""
        url = f"{self.BASE_URL}/api/v2/gold/{company.lower()}"
        params = {}
        if date_from:
            params['date_from'] = date_from
        if date_to:
            params['date_to'] = date_to
        
        try:
            response = requests.get(url, headers=self.headers, params=params, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error fetching {company} price: {e}")
            return None

# Initialize services
api = GoldPriceAPI(api_key=API_KEY)
analyzer = GoldPriceAnalyzer() if GoldPriceAnalyzer else None
collector = HistoricalDataCollector(api_key=API_KEY) if HistoricalDataCollector else None

# WebSocket Connection Manager
class ConnectionManager:
    """Manage WebSocket connections and broadcast messages"""
    
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.last_prices: Optional[Dict] = None
    
    async def connect(self, websocket: WebSocket):
        """Accept and store new WebSocket connection"""
        await websocket.accept()
        self.active_connections.append(websocket)
        print(f"[+] WebSocket client connected. Total connections: {len(self.active_connections)}")
    
    def disconnect(self, websocket: WebSocket):
        """Remove WebSocket connection from pool"""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            print(f"[-] WebSocket client disconnected. Total connections: {len(self.active_connections)}")
    
    async def broadcast(self, message: dict):
        """Send message to all connected clients"""
        if not self.active_connections:
            return
        
        message_json = json.dumps(message)
        disconnected = []
        
        for connection in self.active_connections:
            try:
                await connection.send_text(message_json)
            except Exception as e:
                print(f"Error sending to client: {e}")
                disconnected.append(connection)
        
        # Clean up disconnected clients
        for connection in disconnected:
            self.disconnect(connection)
    
    def has_price_changed(self, new_prices: Dict) -> Tuple[bool, List[str]]:
        """Check if prices have changed since last check and calculate diff. Returns (has_changed, alerts)"""
        alerts = []
        if self.last_prices is None:
            self.last_prices = new_prices
            return True, alerts
        
        # Compare prices
        has_changed = False
        if 'sjc' in new_prices and 'sjc' in self.last_prices:
            old_sjc = self.last_prices.get('sjc', {}).get('results', [{}])[0]
            new_sjc = new_prices.get('sjc', {}).get('results', [{}])[0]
            
            # Check key price fields
            for field in ['buy_1l', 'sell_1l', 'buy_nhan1c', 'sell_nhan1c']:
                old_val = old_sjc.get(field)
                new_val = new_sjc.get(field)
                
                if old_val and new_val and old_val != new_val:
                    has_changed = True
                    try:
                        old_f = float(old_val)
                        new_f = float(new_val)
                        diff_pct = abs(new_f - old_f) / old_f * 100
                        diff_amount = new_f - old_f
                        
                        # Phase 3: Ngưỡng cảnh báo (Threshold)
                        # Nếu chênh lệch quá 0.5%, kích hoạt Alert
                        if diff_pct >= 0.5:
                            alert_msg = f"CẢNH BÁO: Giá '{field}' đổi mạnh: {diff_amount:+,.0f} VND ({diff_pct:.2f}%)"
                            alerts.append(alert_msg)
                            print("=" * 60)
                            print("🚨 " + alert_msg)
                            print("=" * 60)
                    except ValueError:
                        pass
            
            if has_changed:
                self.last_prices = new_prices
                return True, alerts
        
        return False, alerts

# Initialize connection manager
manager = ConnectionManager()

# Background task to check for price updates
async def background_price_checker():
    """Background task that polls the API and pushes updates via WebSocket"""
    print("[*] Starting background price checker...")
    await asyncio.sleep(5)  # Wait 5 seconds before first check
    
    while True:
        try:
            # Broadcast crawler status
            await manager.broadcast({
                "type": "crawler_status",
                "status": "running",
                "message": "Đang chạy AI Crawler để lấy giá SJC..."
            })
            
            # Fetch current prices via AI Crawler
            if collector:
                current_data = collector.collect_current_prices()
                
            if current_data and 'sjc' in current_data and current_data['sjc']:
                sjc_data = {'results': current_data['sjc']}
                prices = {
                    'sjc': sjc_data
                }
                
                # Check for changes
                has_changed, alerts = manager.has_price_changed(prices)
                if has_changed:
                    print(f"[+] Price change detected at {datetime.now().strftime('%H:%M:%S')}")
                    
                    # Save to CSV if collector available
                    if collector:
                        try:
                            data = {}
                            if sjc_data and 'results' in sjc_data:
                                data['sjc'] = sjc_data['results']
                            if data:
                                collector.append_to_csv(data)
                        except Exception as e:
                            print(f"Error saving to CSV: {e}")
                    
                    # Broadcast update to all connected clients
                    await manager.broadcast({
                        'type': 'price_update',
                        'timestamp': datetime.now().isoformat(),
                        'prices': prices,
                        'message': 'New gold prices available'
                    })
                    
                    # Push alerts to clients
                    for alert in alerts:
                        await manager.broadcast({
                            "type": "alert",
                            "message": alert
                        })
                        
            # Broadcast crawler status idle
            await manager.broadcast({
                "type": "crawler_status",
                "status": "idle",
                "message": "Chờ vòng cào tiếp theo..."
            })
        
        except Exception as e:
            print(f"Error in background price checker: {e}")
            await manager.broadcast({
                "type": "crawler_status",
                "status": "error",
                "message": f"Lỗi Crawler: {str(e)}"
            })
        
        # Wait 60 seconds before next check
        await asyncio.sleep(60)

# Pydantic models for request/response validation
class PriceData(BaseModel):
    timestamp: str
    company: str
    data: Dict[str, Any]

class AnalyticsResponse(BaseModel):
    company: str
    period_days: int
    data: Dict[str, Any]

class TrendResponse(BaseModel):
    period: str
    days: int
    trends: Dict[str, Any]
    moving_average: Optional[Dict[str, Any]] = None

# Health check endpoint
@app.get("/")
async def root():
    """Root endpoint - API information"""
    return {
        "name": "Gold Price Dashboard API",
        "version": "2.0.0",
        "status": "running",
        "docs": "/api/docs",
        "endpoints": {
            "current_prices": "/api/current-prices",
            "historical": "/api/historical-prices",
            "analytics": "/api/analytics/*",
            "export": "/api/export/csv"
        }
    }

@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "services": {
            "api": "operational",
            "analyzer": "operational" if analyzer else "unavailable",
            "collector": "operational" if collector else "unavailable"
        }
    }

@app.get("/api/current-prices")
async def get_current_prices(save_to_csv: bool = Query(True, description="Save current prices to CSV")):
    """Get current gold prices from SJC using AI Crawler"""
    sjc_data = None
    if collector:
        current_data = collector.collect_current_prices()
        if current_data and 'sjc' in current_data and current_data['sjc']:
            sjc_data = {'results': current_data['sjc']}

    # Save to CSV if requested and collector is available
    if save_to_csv and collector:
        try:
            data = {}
            if sjc_data and 'results' in sjc_data:
                data['sjc'] = sjc_data['results']

            if data:
                collector.append_to_csv(data)
        except Exception as e:
            print(f"Error saving to CSV: {e}")

    return {
        'timestamp': datetime.now().isoformat(),
        'sjc': sjc_data
    }

@app.post("/api/update-historical-data")
async def update_historical_data():
    """
    Fetch and append missing historical data from the last CSV date to today.
    This endpoint should be called when the app starts to ensure data is up-to-date.
    """
    if not collector:
        raise HTTPException(status_code=503, detail="Data collector service unavailable")

    try:
        result = collector.fetch_missing_data()
        return {
            'success': True,
            'timestamp': datetime.now().isoformat(),
            **result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating historical data: {str(e)}")

@app.get("/api/available-dates")
async def get_available_dates():
    """
    Get list of available dates from the CSV file for historical price lookup
    """
    if not collector:
        raise HTTPException(status_code=503, detail="Data collector service unavailable")

    try:
        import csv
        import os
        from collections import OrderedDict

        csv_file = os.path.join(collector.DATA_DIR, 'historical_gold_prices.csv')

        if not os.path.exists(csv_file):
            return {'dates': []}

        # Read all unique dates from CSV
        dates_set = set()
        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                timestamp = row.get('timestamp', '')
                if timestamp:
                    # Extract just the date part (YYYY-MM-DD)
                    date_part = timestamp.split(' ')[0] if ' ' in timestamp else timestamp
                    dates_set.add(date_part)

        # Sort dates in descending order (newest first)
        dates_list = sorted(list(dates_set), reverse=True)

        return {
            'dates': dates_list,
            'count': len(dates_list)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching available dates: {str(e)}")

@app.get("/api/prices-by-date")
async def get_prices_by_date(date: str = Query(..., description="Date in YYYY-MM-DD format")):
    """
    Get gold prices for a specific date from the CSV file
    """
    if not collector:
        raise HTTPException(status_code=503, detail="Data collector service unavailable")

    try:
        import csv
        import os

        csv_file = os.path.join(collector.DATA_DIR, 'historical_gold_prices.csv')

        if not os.path.exists(csv_file):
            raise HTTPException(status_code=404, detail="Historical data file not found")

        # Read prices for the specified date
        sjc_prices = {}

        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                timestamp = row.get('timestamp', '')
                if not timestamp.startswith(date):
                    continue

                company = row.get('company', '')
                gold_type = row.get('gold_type', '')
                buy_price = row.get('buy_price', '')
                sell_price = row.get('sell_price', '')

                # Only process SJC data
                if company != 'SJC':
                    continue

                # Map gold types to API field names
                if gold_type == 'SJC 1L':
                    sjc_prices['buy_1l'] = buy_price
                    sjc_prices['sell_1l'] = sell_price
                elif gold_type == 'SJC Ring 1C':
                    sjc_prices['buy_nhan1c'] = buy_price
                    sjc_prices['sell_nhan1c'] = sell_price
                elif gold_type == 'SJC Jewelry 24K':
                    sjc_prices['buy_nutrang_9999'] = buy_price
                    sjc_prices['sell_nutrang_9999'] = sell_price
                elif gold_type == 'SJC Jewelry 99%':
                    sjc_prices['buy_nutrang_99'] = buy_price
                    sjc_prices['sell_nutrang_99'] = sell_price
                elif gold_type == 'SJC Jewelry 18K':
                    sjc_prices['buy_nutrang_75'] = buy_price
                    sjc_prices['sell_nutrang_75'] = sell_price

        if not sjc_prices:
            raise HTTPException(status_code=404, detail=f"No data found for date {date}")

        # Return in same format as current prices API
        return {
            'timestamp': f"{date}T00:00:00",
            'sjc': {
                'results': [sjc_prices]
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching prices for date: {str(e)}")

@app.get("/api/historical-prices")
async def get_historical_prices(
    company: str = Query(..., description="Company name (sjc only)"),
    days: int = Query(7, description="Number of days to fetch", ge=1, le=365)
):
    """Get historical gold prices for SJC only (DOJI and PNJ removed)"""
    date_to = datetime.now().strftime('%Y-%m-%d')
    date_from = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')

    company_lower = company.lower()
    if company_lower not in ['sjc']:
        raise HTTPException(status_code=400, detail="Invalid company. Must be sjc")

    data = api.get_company_price(company_lower, date_from, date_to)

    if not data:
        raise HTTPException(status_code=500, detail="Failed to fetch data from API")

    return data

@app.get("/api/analytics/price-change")
async def get_price_change(
    company: str = Query(..., description="Company name (SJC only)"),
    days: int = Query(7, description="Number of days to analyze", ge=1, le=365)
):
    """Get price change analysis for SJC only"""
    if not analyzer:
        raise HTTPException(status_code=500, detail="Analyzer service unavailable")

    try:
        change_data = analyzer.calculate_price_change(company.upper(), days_back=days)
        return change_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/analytics/volatility")
async def get_volatility(
    company: str = Query(..., description="Company name (SJC only)"),
    days: int = Query(30, description="Number of days to analyze", ge=1, le=365)
):
    """Get price volatility analysis for SJC only"""
    if not analyzer:
        raise HTTPException(status_code=500, detail="Analyzer service unavailable")

    try:
        volatility_data = analyzer.calculate_volatility(company.upper(), days_back=days)
        return volatility_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/analytics/extremes")
async def get_price_extremes(
    company: str = Query(..., description="Company name (SJC only)"),
    days: int = Query(30, description="Number of days to analyze", ge=1, le=365)
):
    """Get price extremes (min/max) for SJC only"""
    if not analyzer:
        raise HTTPException(status_code=500, detail="Analyzer service unavailable")

    try:
        extremes_data = analyzer.get_price_extremes(company.upper(), days_back=days)
        return extremes_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/analytics/trends")
async def get_trends(
    company: str = Query(..., description="Company name (SJC only)"),
    period: str = Query('weekly', description="Time period (weekly, monthly, quarterly, yearly)"),
    gold_type: Optional[str] = Query(None, description="Gold type (e.g., 'SJC 1L')"),
    location: Optional[str] = Query(None, description="Location (e.g., 'National')")
):
    """Get price trends for SJC only"""
    if not analyzer:
        raise HTTPException(status_code=500, detail="Analyzer service unavailable")

    # Map period to days
    period_map = {
        'weekly': 7,
        'monthly': 30,
        'quarterly': 90,
        'yearly': 365
    }

    days = period_map.get(period, 7)

    try:
        trends_data = analyzer.get_price_trends(
            company.upper(),
            days_back=days,
            location=location,
            gold_type=gold_type
        )
        ma_data = analyzer.get_moving_average(
            company.upper(),
            days_back=days,
            window=7
        )

        return {
            'period': period,
            'days': days,
            'trends': trends_data,
            'moving_average': ma_data
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/analytics/comparison")
async def get_company_comparison(
    days: int = Query(7, description="Number of days to compare", ge=1, le=365)
):
    """Compare all companies"""
    if not analyzer:
        raise HTTPException(status_code=500, detail="Analyzer service unavailable")
    
    try:
        comparison_data = analyzer.compare_companies(days_back=days)
        return comparison_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/export/csv")
async def export_csv():
    """Export historical data as CSV"""
    csv_file = 'historical_data/historical_gold_prices.csv'
    
    if not os.path.exists(csv_file):
        raise HTTPException(status_code=404, detail="Historical data not available")
    
    return FileResponse(
        csv_file,
        media_type='text/csv',
        filename='gold_prices_export.csv'
    )

@app.post("/api/data/update")
async def update_historical_data():
    """Update historical data with latest prices"""
    if not collector:
        raise HTTPException(status_code=500, detail="Data collector unavailable")
    
    try:
        collector.update_csv_with_latest()
        return {
            'status': 'success',
            'message': 'Historical data updated',
            'timestamp': datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# WebSocket endpoint for real-time price updates
@app.websocket("/ws/prices")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for real-time gold price updates
    
    Clients connect to this endpoint and receive instant notifications
    when gold prices change.
    """
    await manager.connect(websocket)
    
    try:
        # Send initial connection confirmation
        try:
            await websocket.send_json({
                'type': 'connection',
                'status': 'connected',
                'message': 'WebSocket connection established',
                'timestamp': datetime.now().isoformat()
            })
        except WebSocketDisconnect:
            # Client disconnected immediately after connecting
            manager.disconnect(websocket)
            return
            
        # Keep connection alive and listen for messages
        while True:
            try:
                # Wait for any client messages (ping/pong, etc.)
                data = await websocket.receive_text()
                
                # Handle ping/pong
                if data == 'ping':
                    await websocket.send_text('pong')
            
            except WebSocketDisconnect:
                break
            except Exception as e:
                print(f"Error in WebSocket loop: {e}")
                break
    except WebSocketDisconnect:
        pass
    finally:
        manager.disconnect(websocket)

# Startup event to start background tasks
@app.on_event("startup")
async def startup_event():
    """Start background tasks when the app starts"""
    print("=" * 60)
    print("[*] Starting FastAPI application...")
    print("=" * 60)
    
    # Update historical data on startup to fill any gaps
    if collector:
        print("\n[*] Checking for missing historical data...")
        try:
            result = collector.fetch_missing_data()
            print(f"[+] Status: {result.get('status')}")
            print(f"[+] {result.get('message')}")
            if result.get('records_added', 0) > 0:
                print(f"[+] Added {result['records_added']} new records!")
            else:
                print("[+] Data is up to date")
        except Exception as e:
            print(f"[-] Error updating historical data: {e}")
        print()
    
    # Start background price checker
    asyncio.create_task(background_price_checker())
    
    print("[+] Background price checker started")
    print("[+] WebSocket endpoint ready at /ws/prices")
    print("=" * 60)

# Run with: uvicorn api_fastapi:app --reload --port 8000
if __name__ == "__main__":
    import uvicorn
    print("=" * 60)
    print("Gold Price Dashboard - FastAPI Backend")
    print("=" * 60)
    print("Starting server at http://localhost:8000")
    print("API Documentation: http://localhost:8000/api/docs")
    print("Press Ctrl+C to stop the server")
    print("=" * 60)
    uvicorn.run("api_fastapi:app", host="0.0.0.0", port=8000, reload=True)

