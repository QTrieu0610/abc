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
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor

from login_test_runner import resolve_target, run_login_test

# Import modules
try:
    from config import API_KEY
except ImportError:
    API_KEY = None

try:
    from data_analyzer import GoldPriceAnalyzer
    from data_collector import HistoricalDataCollector
    from house_data_collector import HousePriceDataCollector
except ImportError:
    GoldPriceAnalyzer = None
    HistoricalDataCollector = None
    HousePriceDataCollector = None

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
house_collector = HousePriceDataCollector() if HousePriceDataCollector else None


def empty_source(error: Optional[str] = None) -> Dict[str, Any]:
    return {
        'status': 'failed' if error else 'empty',
        'results': [],
        'error': error
    }


def successful_sources(current_data: Optional[Dict[str, Any]]) -> Dict[str, List[Dict]]:
    if not current_data:
        return {}

    data = {}
    for source_name, payload in current_data.items():
        if not isinstance(payload, dict):
            continue
        results = payload.get('results') or []
        if payload.get('status') == 'ok' and results:
            data[source_name] = results
    return data


def safe_session_metadata(session_dir: str = "sessions") -> List[Dict[str, Any]]:
    """Return safe session metadata without exposing cookie values or secrets."""
    sessions = []
    if not os.path.isdir(session_dir):
        return sessions

    for filename in sorted(os.listdir(session_dir)):
        if not filename.endswith(".json"):
            continue

        path = os.path.join(session_dir, filename)
        try:
            stat = os.stat(path)
            with open(path, "r", encoding="utf-8") as handle:
                payload = json.load(handle)
        except Exception as e:
            profile_name = filename.replace("crawler_session_", "").replace(".json", "")
            if profile_name in ["sjc", "doji", "pnj", "gold"]:
                topic = "Gold Price"
            elif profile_name in ["batdongsan", "alonhadat"]:
                topic = "Real Estate"
            else:
                topic = "Unknown"
            sessions.append({
                "session_name": profile_name,
                "source": "unknown",
                "topic": topic,
                "login_status": "unreadable",
                "last_used": None,
                "mfa_required": "unknown",
                "session_file": filename,
                "status": "error",
                "cookie_count": 0,
                "origin_count": 0,
                "domains": [],
                "message": f"Cannot read session metadata: {e}",
            })
            continue

        cookies = payload.get("cookies") if isinstance(payload, dict) else []
        origins = payload.get("origins") if isinstance(payload, dict) else []
        cookies = cookies if isinstance(cookies, list) else []
        origins = origins if isinstance(origins, list) else []
        domains = sorted({
            str(cookie.get("domain", "")).lstrip(".")
            for cookie in cookies
            if isinstance(cookie, dict) and cookie.get("domain")
        })
        profile_name = filename.replace("crawler_session_", "").replace(".json", "")
        if profile_name in ["sjc", "doji", "pnj", "gold"]:
            topic = "Gold Price"
        elif profile_name in ["batdongsan", "alonhadat"]:
            topic = "Real Estate"
        else:
            topic = "Crawler Session"

        sessions.append({
            "session_name": profile_name,
            "source": ", ".join(domains) if domains else "N/A",
            "topic": topic,
            "login_status": "stored" if cookies else "empty",
            "last_used": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            "mfa_required": "unknown",
            "session_file": filename,
            "status": "available" if cookies else "empty",
            "cookie_count": len(cookies),
            "origin_count": len(origins),
            "domains": domains,
            "message": "Safe metadata only. Cookie values are hidden.",
        })

    return sessions


def source_job_from_payload(source_name: str, payload: Dict[str, Any], timestamp: str) -> Dict[str, Any]:
    source_upper = source_name.upper()
    results = payload.get("results") if isinstance(payload, dict) else []
    results = results if isinstance(results, list) else []
    status = payload.get("status", "empty") if isinstance(payload, dict) else "empty"
    error = payload.get("error") if isinstance(payload, dict) else None

    if status == "ok":
        job_status = "completed"
        progress = 100
    elif status in ["blocked", "skipped"]:
        job_status = "completed"
        progress = 100
    elif status == "failed":
        job_status = "failed"
        progress = 0
    else:
        job_status = "empty"
        progress = 0

    target_sites = {
        "sjc": "webgia.com / sjc.com.vn",
        "doji": "giavang.doji.vn",
        "pnj": "pnj.com.vn/site/gia-vang",
        "batdongsan": "batdongsan.com.vn",
        "alonhadat": "alonhadat.com.vn",
    }

    is_real_estate = source_name in ["batdongsan", "alonhadat"]

    if is_real_estate:
        job_name = f"Real Estate {source_name.title() if source_name == 'alonhadat' else 'Batdongsan'}"
        profile = f"crawler_session_{source_name}"
        topic = "Real Estate"
    else:
        job_name = f"Gold Price {source_upper}"
        profile = "crawler_session_default" if source_name not in ["sjc", "doji", "pnj"] else f"crawler_session_{source_name}"
        topic = "Gold Price"

    return {
        "job_name": job_name,
        "target_site": target_sites.get(source_name, source_name),
        "profile": profile,
        "status": job_status,
        "source_status": status,
        "progress": progress,
        "records": len(results),
        "topic": topic,
        "source": source_upper,
        "last_run": timestamp,
        "message": error or ("Backend source returned records." if results else "No records returned."),
    }


def is_blocked_real_estate_payload(payload: Dict[str, Any]) -> bool:
    if not isinstance(payload, dict):
        return False
    message = str(payload.get("error") or payload.get("message") or "").lower()
    return any(token in message for token in [
        "cloudflare",
        "captcha",
        "access denied",
        "403",
        "forbidden",
        "human verification",
        "blocked",
    ])


def soften_blocked_house_source(source_name: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    if not is_blocked_real_estate_payload(payload):
        return payload

    softened = dict(payload)
    softened["status"] = "blocked"
    softened["results"] = payload.get("results") if isinstance(payload.get("results"), list) else []
    softened["error"] = (
        payload.get("error")
        or f"{source_name.upper()} is blocked by anti-bot protection. Other sources can still complete."
    )
    return softened

# WebSocket Connection Manager
class ConnectionManager:
    """Manage WebSocket connections and broadcast messages"""
    
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.last_prices: Optional[Dict] = None
        self.last_house_prices: Optional[Dict] = None
    
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
        has_changed = (
            json.dumps(new_prices, sort_keys=True, default=str)
            != json.dumps(self.last_prices, sort_keys=True, default=str)
        )
        if 'sjc' in new_prices and 'sjc' in self.last_prices:
            old_sjc = (self.last_prices.get('sjc', {}).get('results') or [{}])[0]
            new_sjc = (new_prices.get('sjc', {}).get('results') or [{}])[0]
            
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


login_test_executor = ThreadPoolExecutor(max_workers=1)
login_test_lock = threading.Lock()
login_test_jobs: Dict[str, Dict[str, Any]] = {}
hitl_cases: Dict[str, Dict[str, Any]] = {}


def blocking_reason_from_message(message: Optional[str]) -> Optional[Tuple[str, str, str]]:
    value = (message or "").lower()
    if "mfa" in value or "otp" in value:
        return ("mfa_required", "MFA Required", "medium")
    if "captcha" in value:
        return ("captcha_detected", "CAPTCHA Detected", "high")
    if "cloudflare" in value or "verify you are a human" in value or "human verification" in value:
        return ("captcha_detected", "Cloudflare Challenge", "high")
    if "access denied" in value or "403" in value or "forbidden" in value:
        return ("access_denied", "Access Denied", "critical")
    if "429" in value or "rate limit" in value:
        return ("rate_limited", "Rate Limited", "high")
    if "503" in value or "checking your browser" in value:
        return ("browser_event", "Browser Verification", "medium")
    if "timeout" in value:
        return ("timeout", "Timeout", "medium")
    if "browser" in value or "playwright" in value:
        return ("browser_error", "Browser Error", "high")
    return None


def public_login_job(job: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "job_id": job.get("job_id"),
        "status": job.get("status"),
        "target_type": job.get("target_type"),
        "target_label": job.get("target_label"),
        "target_url": job.get("target_url"),
        "profile_name": job.get("profile_name"),
        "created_at": job.get("created_at"),
        "started_at": job.get("started_at"),
        "ended_at": job.get("ended_at"),
        "html_length": job.get("html_length"),
        "output_file": job.get("output_file"),
        "latest_signal": job.get("latest_signal"),
        "log_count": len(job.get("logs", [])),
        "username_provided": job.get("username_provided", False),
    }


def ensure_hitl_case(job_id: str, signal_type: str, message: str) -> None:
    case_id = f"{job_id}-{signal_type}"
    now = datetime.now().isoformat()
    existing = hitl_cases.get(case_id)
    if existing:
        existing["message"] = message
        existing["updated_at"] = now
        if existing.get("status") == "resolved":
            existing["status"] = "open"
        return

    reason_map = {
        "mfa_required": "MFA Required",
        "captcha_detected": "CAPTCHA Detected",
        "access_denied": "Access Denied",
        "timeout": "Timeout",
        "browser_error": "Browser Error",
        "browser_event": "Browser Event",
    }
    severity_map = {
        "mfa_required": "medium",
        "captcha_detected": "high",
        "access_denied": "critical",
        "timeout": "medium",
        "browser_error": "high",
        "browser_event": "info",
    }
    job = login_test_jobs.get(job_id, {})
    hitl_cases[case_id] = {
        "case_id": case_id,
        "job_id": job_id,
        "topic": "Login Test",
        "source": job.get("target_label") or job.get("target_url") or "Login target",
        "reason": reason_map.get(signal_type, signal_type.replace("_", " ").title()),
        "signal_type": signal_type,
        "severity": severity_map.get(signal_type, "info"),
        "message": message,
        "status": "open",
        "created_at": now,
        "updated_at": now,
        "action": "Human approval required",
    }


def add_login_job_log(job_id: str, level: str, message: str, signal_type: Optional[str] = None) -> None:
    with login_test_lock:
        job = login_test_jobs.get(job_id)
        if not job:
            return
        entry = {
            "timestamp": datetime.now().isoformat(),
            "level": level,
            "message": message,
            "signal_type": signal_type,
        }
        job.setdefault("logs", []).append(entry)
        if signal_type:
            job["latest_signal"] = signal_type
            ensure_hitl_case(job_id, signal_type, message)


def resolve_open_cases_for_job(job_id: str) -> None:
    for case in hitl_cases.values():
        if case.get("job_id") == job_id and case.get("status") == "open":
            case["status"] = "resolved"
            case["action"] = "Resolved by completed login test"
            case["updated_at"] = datetime.now().isoformat()


def run_login_job(job_id: str, username: str, password: str) -> None:
    with login_test_lock:
        job = login_test_jobs.get(job_id)
        if not job:
            return
        job["status"] = "running"
        job["started_at"] = datetime.now().isoformat()

    try:
        result = run_login_test(
            job_id=job_id,
            target_type=job["target_type"],
            target_url=job.get("target_url"),
            username=username,
            password=password,
            profile_name=job.get("profile_name") or "default",
            emit=lambda level, message, signal_type=None: add_login_job_log(
                job_id, level, message, signal_type
            ),
        )
        with login_test_lock:
            job = login_test_jobs.get(job_id)
            if job:
                job.update(result)
                if result.get("status") == "completed":
                    resolve_open_cases_for_job(job_id)
    except Exception as e:
        add_login_job_log(job_id, "error", f"Login test failed: {e}", "browser_error")
        with login_test_lock:
            job = login_test_jobs.get(job_id)
            if job:
                job["status"] = "failed"
                job["ended_at"] = datetime.now().isoformat()


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
                "message": "Dang crawl song song WebGia/SJC, DOJI va PNJ..."
            })
            
            current_data = {}
            # Fetch current prices via AI Crawler
            if collector:
                current_data = await asyncio.to_thread(collector.collect_current_prices)
                
            if current_data:
                prices = {
                    'sjc': current_data.get('sjc', empty_source('Missing SJC payload')),
                    'doji': current_data.get('doji', empty_source('Missing DOJI payload')),
                    'pnj': current_data.get('pnj', empty_source('Missing PNJ payload')),
                }
                
                # Check for changes
                has_changed, alerts = manager.has_price_changed(prices)
                if has_changed:
                    print(f"[+] Price change detected at {datetime.now().strftime('%H:%M:%S')}")
                    
                    # Save to CSV if collector available
                    if collector:
                           try:
                               data = successful_sources(prices)
                               if data:
                                   await asyncio.to_thread(collector.append_to_csv, data)
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
        
        # Wait 300 seconds before next check
        await asyncio.sleep(300)

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


class LoginTestRequest(BaseModel):
    target_type: str = "demo"
    target_url: Optional[str] = None
    username: str
    password: str
    profile_name: str = "default"

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
    """Get current gold prices from SJC/WebGia, DOJI, and PNJ using the multi-source crawler."""
    current_data = {}
    if collector:
        current_data = await asyncio.to_thread(collector.collect_current_prices)

    # Save to CSV if requested and collector is available
    if save_to_csv and collector:
        try:
            data = successful_sources(current_data)
            if data:
                await asyncio.to_thread(collector.append_to_csv, data)
        except Exception as e:
            print(f"Error saving to CSV: {e}")

    prices = {
        'timestamp': datetime.now().isoformat(),
        'sjc': current_data.get('sjc', empty_source('Missing SJC payload')),
        'doji': current_data.get('doji', empty_source('Missing DOJI payload')),
        'pnj': current_data.get('pnj', empty_source('Missing PNJ payload')),
    }
    manager.last_prices = {
        'sjc': prices['sjc'],
        'doji': prices['doji'],
        'pnj': prices['pnj'],
    }
    return prices


@app.get("/api/house-prices")
async def get_house_prices(
    max_pages: int = Query(1, ge=1, le=5, description="Number of listing pages to crawl per source"),
    use_browser_fallback: bool = Query(True, description="Use Playwright if static HTML fetch is blocked"),
    save_to_csv: bool = Query(True, description="Save successful house-price listings to CSV"),
):
    """Get current real-estate listing prices from configured housing sources."""
    try:
        from ai_crawler_engine import MultiSourceRealEstateCrawler

        crawler = MultiSourceRealEstateCrawler(
            max_pages=max_pages,
            use_browser_fallback=use_browser_fallback,
        )
        current_data = await asyncio.to_thread(crawler.execute_crawling)
    except Exception as e:
        current_data = {
            "batdongsan": empty_source(str(e)),
            "alonhadat": empty_source(str(e)),
        }

    prices = {
        "batdongsan": soften_blocked_house_source(
            "batdongsan",
            current_data.get("batdongsan", empty_source("Missing Batdongsan payload")),
        ),
        "alonhadat": soften_blocked_house_source(
            "alonhadat",
            current_data.get("alonhadat", empty_source("Missing AloNhaDat payload")),
        ),
    }

    manager.last_house_prices = prices

    saved_records = 0
    if save_to_csv and house_collector:
        try:
            saved_records = await asyncio.to_thread(house_collector.append_to_csv, prices)
        except Exception as e:
            print(f"Error saving house prices to CSV: {e}")

    return {
        "timestamp": datetime.now().isoformat(),
        "topic": "house-price",
        "saved_records": saved_records,
        "data_file": house_collector.default_path() if house_collector else None,
        **prices
    }


@app.get("/api/sessions")
async def get_sessions():
    """Return safe crawler session metadata without cookie values, tokens, or secrets."""
    sessions = safe_session_metadata()
    return {
        "timestamp": datetime.now().isoformat(),
        "count": len(sessions),
        "sessions": sessions,
        "security": "Cookie values, tokens, and credentials are never returned by this endpoint.",
    }


@app.get("/api/crawl-jobs")
async def get_crawl_jobs(refresh: bool = Query(False, description="Refresh current source status before building jobs")):
    """Return crawl job status derived from real crawler source payloads."""
    timestamp = datetime.now().isoformat()
    prices = manager.last_prices

    if (refresh or not prices) and collector:
        current_data = await asyncio.to_thread(collector.collect_current_prices)
        prices = {
            'sjc': current_data.get('sjc', empty_source('Missing SJC payload')),
            'doji': current_data.get('doji', empty_source('Missing DOJI payload')),
            'pnj': current_data.get('pnj', empty_source('Missing PNJ payload')),
        }
        manager.last_prices = prices

    prices = prices or {
        'sjc': empty_source('No crawler snapshot available yet'),
        'doji': empty_source('No crawler snapshot available yet'),
        'pnj': empty_source('No crawler snapshot available yet'),
    }

    house_prices = manager.last_house_prices or {
        'batdongsan': empty_source('No crawler snapshot available yet'),
        'alonhadat': empty_source('No crawler snapshot available yet'),
    }

    jobs = [
        source_job_from_payload('sjc', prices.get('sjc', empty_source('Missing SJC payload')), timestamp),
        source_job_from_payload('doji', prices.get('doji', empty_source('Missing DOJI payload')), timestamp),
        source_job_from_payload('pnj', prices.get('pnj', empty_source('Missing PNJ payload')), timestamp),
        source_job_from_payload('batdongsan', house_prices.get('batdongsan', empty_source('Missing Batdongsan payload')), timestamp),
        source_job_from_payload('alonhadat', house_prices.get('alonhadat', empty_source('Missing AloNhaDat payload')), timestamp),
    ]

    return {
        "timestamp": timestamp,
        "count": len(jobs),
        "jobs": jobs,
    }


@app.post("/api/login-tests")
async def create_login_test(payload: LoginTestRequest):
    """Start a background login test and expose safe logs for HITL review."""
    try:
        target = resolve_target(payload.target_type, payload.target_url)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    if not payload.username.strip():
        raise HTTPException(status_code=400, detail="Username is required")
    if not payload.password:
        raise HTTPException(status_code=400, detail="Password is required")

    job_id = uuid.uuid4().hex
    now = datetime.now().isoformat()
    job = {
        "job_id": job_id,
        "status": "queued",
        "target_type": payload.target_type,
        "target_label": target["label"],
        "target_url": target["url"],
        "profile_name": payload.profile_name or "default",
        "created_at": now,
        "started_at": None,
        "ended_at": None,
        "html_length": None,
        "output_file": None,
        "latest_signal": None,
        "username_provided": True,
        "logs": [
            {
                "timestamp": now,
                "level": "info",
                "message": "Login test queued. Password is hidden and will not be stored.",
                "signal_type": None,
            }
        ],
    }
    with login_test_lock:
        login_test_jobs[job_id] = job

    login_test_executor.submit(run_login_job, job_id, payload.username, payload.password)
    return public_login_job(job)


@app.get("/api/login-tests")
async def list_login_tests():
    """List login test jobs without credentials."""
    with login_test_lock:
        jobs = [public_login_job(job) for job in login_test_jobs.values()]
    jobs.sort(key=lambda item: item.get("created_at") or "", reverse=True)
    return {
        "timestamp": datetime.now().isoformat(),
        "count": len(jobs),
        "jobs": jobs,
    }


@app.get("/api/login-tests/{job_id}")
async def get_login_test(job_id: str):
    """Get one login test job without credentials."""
    with login_test_lock:
        job = login_test_jobs.get(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Login test job not found")
        return public_login_job(job)


@app.get("/api/login-tests/{job_id}/logs")
async def get_login_test_logs(job_id: str):
    """Get safe logs for a login test job."""
    with login_test_lock:
        job = login_test_jobs.get(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Login test job not found")
        return {
            "job_id": job_id,
            "count": len(job.get("logs", [])),
            "logs": list(job.get("logs", [])),
        }


@app.get("/api/hitl/cases")
async def get_hitl_cases():
    """Return HITL cases raised by login tests."""
    with login_test_lock:
        cases = list(hitl_cases.values())
    cases.sort(key=lambda item: item.get("updated_at") or item.get("created_at") or "", reverse=True)
    open_count = sum(1 for case in cases if case.get("status") == "open")
    return {
        "timestamp": datetime.now().isoformat(),
        "count": len(cases),
        "open_count": open_count,
        "cases": cases,
        "warning": "Continue only when this crawl is authorized and compliant with the target website policy.",
    }


@app.get("/api/blocking-signals")
async def get_blocking_signals():
    """Return crawler/login blocking signals detected by backend jobs."""
    blocking_types = {
        "mfa_required",
        "captcha_detected",
        "access_denied",
        "timeout",
        "browser_error",
        "browser_event",
    }
    with login_test_lock:
        signals = [
            {
                "signal_id": case.get("case_id"),
                "job_id": case.get("job_id"),
                "topic": case.get("topic"),
                "source": case.get("source"),
                "signal_type": case.get("signal_type"),
                "reason": case.get("reason"),
                "severity": case.get("severity"),
                "status": case.get("status"),
                "message": case.get("message"),
                "action": case.get("action"),
                "created_at": case.get("created_at"),
                "updated_at": case.get("updated_at"),
            }
            for case in hitl_cases.values()
            if case.get("signal_type") in blocking_types
        ]

    source_payloads = []
    for topic, payloads in [
        ("House Price", manager.last_house_prices or {}),
        ("Gold Price", manager.last_prices or {}),
    ]:
        for source, payload in payloads.items():
            if not isinstance(payload, dict):
                continue
            message = payload.get("error") or payload.get("message")
            reason = blocking_reason_from_message(message)
            if not reason:
                continue
            signal_type, label, severity = reason
            source_payloads.append({
                "signal_id": f"{topic.lower().replace(' ', '-')}-{source}-{signal_type}",
                "job_id": None,
                "topic": topic,
                "source": source.upper(),
                "signal_type": signal_type,
                "reason": label,
                "severity": severity,
                "status": "open",
                "message": message,
                "action": "Open Batdongsan in Cloak Browser on localhost:9222, complete Cloudflare, then refresh again. The crawler will save the cleared session.",
                "created_at": None,
                "updated_at": datetime.now().isoformat(),
            })

    signals.extend(source_payloads)
    signals.sort(key=lambda item: item.get("updated_at") or item.get("created_at") or "", reverse=True)
    open_count = sum(1 for signal in signals if signal.get("status") == "open")
    return {
        "timestamp": datetime.now().isoformat(),
        "count": len(signals),
        "open_count": open_count,
        "signals": signals,
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
        result = await asyncio.to_thread(collector.fetch_missing_data)
        return {
            'success': True,
            'timestamp': datetime.now().isoformat(),
            **result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating historical data: {str(e)}")

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

@app.get("/api/available-dates")
async def get_available_dates():
    """
    Get list of available dates from the CSV file for historical price lookup
    """
    if not collector:
        raise HTTPException(status_code=503, detail="Data collector service unavailable")

    try:
        import os
        csv_file = os.path.join(collector.DATA_DIR, 'historical_gold_prices.csv')

        dates_list = await asyncio.to_thread(_read_available_dates_sync, csv_file)

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
        import os
        csv_file = os.path.join(collector.DATA_DIR, 'historical_gold_prices.csv')

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

@app.get("/api/historical-prices")
async def get_historical_prices(
    company: str = Query(..., description="Company name (sjc, doji, or pnj)"),
    days: int = Query(7, description="Number of days to fetch", ge=1, le=365)
):
    """Get historical gold prices from the external API where available."""
    date_to = datetime.now().strftime('%Y-%m-%d')
    date_from = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')

    company_lower = company.lower()
    if company_lower not in ['sjc', 'doji', 'pnj']:
        raise HTTPException(status_code=400, detail="Invalid company. Must be sjc, doji, or pnj")

    data = await asyncio.to_thread(api.get_company_price, company_lower, date_from, date_to)

    if not data:
        raise HTTPException(status_code=500, detail="Failed to fetch data from API")

    return data

@app.get("/api/analytics/price-change")
async def get_price_change(
    company: str = Query(..., description="Company name (SJC, DOJI, or PNJ)"),
    days: int = Query(7, description="Number of days to analyze", ge=1, le=365)
):
    """Get price change analysis."""
    if not analyzer:
        raise HTTPException(status_code=500, detail="Analyzer service unavailable")

    try:
        change_data = await asyncio.to_thread(analyzer.calculate_price_change, company.upper(), days_back=days)
        return change_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/analytics/volatility")
async def get_volatility(
    company: str = Query(..., description="Company name (SJC, DOJI, or PNJ)"),
    days: int = Query(30, description="Number of days to analyze", ge=1, le=365)
):
    """Get price volatility analysis."""
    if not analyzer:
        raise HTTPException(status_code=500, detail="Analyzer service unavailable")

    try:
        volatility_data = await asyncio.to_thread(analyzer.calculate_volatility, company.upper(), days_back=days)
        return volatility_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/analytics/extremes")
async def get_price_extremes(
    company: str = Query(..., description="Company name (SJC, DOJI, or PNJ)"),
    days: int = Query(30, description="Number of days to analyze", ge=1, le=365)
):
    """Get price extremes (min/max)."""
    if not analyzer:
        raise HTTPException(status_code=500, detail="Analyzer service unavailable")

    try:
        extremes_data = await asyncio.to_thread(analyzer.get_price_extremes, company.upper(), days_back=days)
        return extremes_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/analytics/trends")
async def get_trends(
    company: str = Query(..., description="Company name (SJC, DOJI, or PNJ)"),
    period: str = Query('weekly', description="Time period (weekly, monthly, quarterly, yearly)"),
    gold_type: Optional[str] = Query(None, description="Gold type (e.g., 'SJC 1L')"),
    location: Optional[str] = Query(None, description="Location (e.g., 'National')")
):
    """Get price trends for a company, gold type, and optional location."""
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
        trends_data = await asyncio.to_thread(
            analyzer.get_price_trends,
            company.upper(),
            days_back=days,
            location=location,
            gold_type=gold_type
        )
        ma_data = await asyncio.to_thread(
            analyzer.get_moving_average,
            company.upper(),
            days_back=days,
            window=7,
            location=location,
            gold_type=gold_type
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
        comparison_data = await asyncio.to_thread(analyzer.compare_companies, days_back=days)
        return comparison_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/analytics/source-momentum")
async def get_source_momentum(
    scope: str = Query('main', description="Momentum scope: main or all"),
    compare: str = Query('previous', description="Comparison mode: previous")
):
    """Compare latest saved source rows against their previous crawl."""
    if not analyzer:
        raise HTTPException(status_code=500, detail="Analyzer service unavailable")

    scope_lower = scope.lower()
    compare_lower = compare.lower()

    if scope_lower not in ['main', 'all']:
        raise HTTPException(status_code=400, detail="Invalid scope. Must be main or all")
    if compare_lower != 'previous':
        raise HTTPException(status_code=400, detail="Invalid compare. Must be previous")

    try:
        return await asyncio.to_thread(analyzer.get_source_momentum, scope=scope_lower, compare=compare_lower)
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


@app.get("/api/export/house-prices-csv")
async def export_house_prices_csv():
    """Export saved house-price listings as CSV."""
    if not house_collector:
        raise HTTPException(status_code=503, detail="House price data collector unavailable")

    csv_file = house_collector.default_path()
    if not os.path.exists(csv_file):
        raise HTTPException(status_code=404, detail="No house price data available")

    return FileResponse(
        csv_file,
        media_type='text/csv',
        filename='house_price_listings_export.csv'
    )

@app.post("/api/data/update")
async def update_historical_data_latest():
    """Update historical data with latest prices"""
    if not collector:
        raise HTTPException(status_code=500, detail="Data collector unavailable")
    
    try:
        await asyncio.to_thread(collector.update_csv_with_latest)
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
            result = await asyncio.to_thread(collector.fetch_missing_data)
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

