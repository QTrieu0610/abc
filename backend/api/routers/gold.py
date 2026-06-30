import os
from typing import Optional, List, Dict, Any, Tuple
from fastapi import APIRouter, Query, HTTPException, WebSocket, WebSocketDisconnect
import asyncio
from datetime import datetime
from api.websocket import manager
from api import tasks
from api.services import empty_source, successful_sources

router = APIRouter()

@router.get("/api/current-prices")
async def get_current_prices(save_to_csv: bool = Query(True, description="Save current prices to CSV"), refresh: bool = Query(False, description="Force a new crawl")):
    """Get current gold prices using the multi-source crawler."""
    if not refresh and getattr(manager, "last_prices", None):
        return manager.last_prices
    if not refresh:
        return None

    current_data = {}
    if tasks.collector:
        current_data = await asyncio.to_thread(tasks.collector.collect_current_prices)

    # Save to CSV if requested and collector is available
    if save_to_csv and tasks.collector:
        try:
            data = successful_sources(current_data)
            if data:
                await asyncio.to_thread(tasks.collector.append_to_csv, data)
        except Exception as e:
            print(f"Error saving to CSV: {e}")

    prices = {
        'timestamp': datetime.now().isoformat(),
    }
    for k, v in current_data.items():
        prices[k] = v

    manager.last_prices = prices
    return prices



@router.get("/api/available-dates")
async def get_available_dates():
    """
    Get list of available dates from the CSV file for historical price lookup
    """
    if not tasks.collector:
        raise HTTPException(status_code=503, detail="Data collector service unavailable")

    try:
        import os
        csv_file = os.path.join(tasks.collector.DATA_DIR, 'historical_gold_prices.csv')

        dates_list = await asyncio.to_thread(_read_available_dates_sync, csv_file)

        return {
            'dates': dates_list,
            'count': len(dates_list)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching available dates: {str(e)}")


@router.get("/api/prices-by-date")
async def get_prices_by_date(date: str = Query(..., description="Date in YYYY-MM-DD format")):
    """
    Get gold prices for a specific date from the CSV file
    """
    if not tasks.collector:
        raise HTTPException(status_code=503, detail="Data collector service unavailable")

    try:
        import os
        csv_file = os.path.join(tasks.collector.DATA_DIR, 'historical_gold_prices.csv')

        result = await asyncio.to_thread(_read_prices_by_date_sync, csv_file, date)
        if result is None:
            raise HTTPException(status_code=404, detail="Historical data file not found")

        sjc_prices, doji_prices, pnj_prices = result

        if not sjc_prices and not doji_prices and not pnj_prices:
            raise HTTPException(status_code=404, detail=f"No data found for date {date}")

        # Return in same format as current prices API
        return {
            'timestamp': f"{date}T00:00:00",
            'sjc': {
                'status': 'ok' if sjc_prices else 'empty',
                'results': [sjc_prices] if sjc_prices else [],
                'error': None if sjc_prices else 'No SJC data for date'
            },
            'doji': {
                'status': 'ok' if doji_prices else 'empty',
                'results': doji_prices,
                'error': None if doji_prices else 'No DOJI data for date'
            },
            'pnj': {
                'status': 'ok' if pnj_prices else 'empty',
                'results': pnj_prices,
                'error': None if pnj_prices else 'No PNJ data for date'
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching prices for date: {str(e)}")


@router.websocket("/ws/prices")
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


def _read_available_dates_sync(csv_file) -> list:
    from data_collector import csv_lock
    import csv
    if not os.path.exists(csv_file):
        return []
    dates_set = set()
    with csv_lock:
        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                timestamp = row.get('timestamp', '')
                if timestamp:
                    date_part = timestamp.split(' ')[0] if ' ' in timestamp else timestamp
                    dates_set.add(date_part)
    return sorted(list(dates_set), reverse=True)

def _read_prices_by_date_sync(csv_file, date) -> Optional[Tuple[Dict, List[Dict], List[Dict]]]:
    from data_collector import csv_lock
    import csv
    if not os.path.exists(csv_file):
        return None
    sjc_prices = {}
    doji_prices = []
    pnj_prices = []
    with csv_lock:
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
                location = row.get('location', '')

                if company == 'SJC':
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
                elif company == 'DOJI':
                    doji_prices.append({
                        'company': 'DOJI',
                        'gold_type': gold_type,
                        'buy_price': buy_price,
                        'sell_price': sell_price,
                        'location': location
                    })
                elif company == 'PNJ':
                    pnj_prices.append({
                        'company': 'PNJ',
                        'gold_type': gold_type,
                        'buy_price': buy_price,
                        'sell_price': sell_price,
                        'location': location
                    })
    return sjc_prices, doji_prices, pnj_prices
