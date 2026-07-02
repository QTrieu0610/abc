from typing import Optional, List, Dict, Any
import asyncio
from datetime import datetime
import uuid
import concurrent.futures
from fastapi import APIRouter, HTTPException, Query
from models.api_models import CrawlUrlRequest, LoginTestRequest
from crawlers import CrawlerFactory
from api.services import safe_session_metadata, empty_source
from login_test_runner import resolve_target, run_login_test
from api.websocket import manager
from api import tasks
from api import services

router = APIRouter()

def save_new_target_to_json(url: str, label: str):
    filename = "gold_targets.json" if label == "gold" else "real_estate_targets.json"
    import os
    import json
    from urllib.parse import urlparse
    
    candidates = [
        os.path.join("config", filename),
        os.path.join("backend", "config", filename),
        os.path.join("..", "config", filename),
    ]
    
    config_path = None
    for path in candidates:
        if os.path.exists(path):
            config_path = path
            break
            
    if not config_path:
        os.makedirs(os.path.join("backend", "config"), exist_ok=True)
        config_path = os.path.join("backend", "config", filename)
        
    targets = []
    if os.path.exists(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                targets = json.load(f)
        except Exception as e:
            print(f"[-] Error loading targets JSON: {e}")
            
    # Check if URL already exists
    url_normalized = url.rstrip("/").lower()
    for t in targets:
        if t.get("url", "").rstrip("/").lower() == url_normalized:
            print(f"[*] URL {url} already registered in config targets.")
            return
            
    # Generate unique ID
    domain = urlparse(url).netloc.replace("www.", "")
    base_id = domain.split(".")[0].lower() if domain else "unknown"
    existing_ids = {t.get("id") for t in targets}
    counter = 1
    new_id = base_id
    while new_id in existing_ids:
        new_id = f"{base_id}_{counter}"
        counter += 1
        
    # Create new target config
    new_target = {
        "id": new_id,
        "url": url,
        "label": label,
        "crawler_type": "table"
    }
    targets.append(new_target)
    
    try:
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(targets, f, indent=4, ensure_ascii=False)
        print(f"[+] Successfully saved new target {new_id} to {config_path}")
    except Exception as e:
        print(f"[-] Failed to save targets JSON: {e}")

@router.post("/api/crawl-url")
async def crawl_url(payload: CrawlUrlRequest):
    """Crawl a generic URL for gold or real estate data using 3-Tier Architecture."""
    try:
        # Tầng 1: Sử dụng CrawlerFactory định tuyến URL
        crawler = CrawlerFactory.get_crawler(url=payload.url, label=payload.type)
        
        # Tầng 2 & 3: Thực thi luồng 3-Tier Fallback (HTTP -> Playwright -> LLM)
        result = await asyncio.to_thread(crawler.execute)
        
        # Save config schema to JSON if crawl succeeded
        if result and result.get("status") == "success":
            try:
                save_new_target_to_json(payload.url, payload.type)
            except Exception as se:
                print(f"[-] Error registering dynamic target: {se}")
        
        return {
            "timestamp": datetime.now().isoformat(),
            "url": payload.url,
            "type": payload.type,
            "result": result
        }
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/")
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



@router.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "services": {
            "api": "operational",
            "analyzer": "operational" if services.analyzer else "unavailable",
            "collector": "operational" if tasks.collector else "unavailable"
        }
    }



@router.get("/api/sessions")
async def get_sessions():
    """Return safe crawler session metadata without cookie values, tokens, or secrets."""
    sessions = safe_session_metadata()
    return {
        "timestamp": datetime.now().isoformat(),
        "count": len(sessions),
        "sessions": sessions,
        "security": "Cookie values, tokens, and credentials are never returned by this endpoint.",
    }




@router.get("/api/hitl/cases")
async def get_hitl_cases():
    """Return HITL cases raised by login tests."""
    with services.login_test_lock:
        cases = list(services.hitl_cases.values())
    cases.sort(key=lambda item: item.get("updated_at") or item.get("created_at") or "", reverse=True)
    open_count = sum(1 for case in cases if case.get("status") == "open")
    return {
        "timestamp": datetime.now().isoformat(),
        "count": len(cases),
        "open_count": open_count,
        "cases": cases,
        "warning": "Continue only when this crawl is authorized and compliant with the target website policy.",
    }

login_test_executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)

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
    with services.login_test_lock:
        existing = services.hitl_cases.get(case_id)
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
        job = services.login_test_jobs.get(job_id, {})
        services.hitl_cases[case_id] = {
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
    with services.login_test_lock:
        job = services.login_test_jobs.get(job_id)
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
    with services.login_test_lock:
        for case in services.hitl_cases.values():
            if case.get("job_id") == job_id and case.get("status") == "open":
                case["status"] = "resolved"
                case["action"] = "Resolved by completed login test"
                case["updated_at"] = datetime.now().isoformat()

def run_login_job(job_id: str, username: str, password: str) -> None:
    with services.login_test_lock:
        job = services.login_test_jobs.get(job_id)
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
        with services.login_test_lock:
            job = services.login_test_jobs.get(job_id)
            if job:
                job.update(result)
                if result.get("status") == "completed":
                    resolve_open_cases_for_job(job_id)
    except Exception as e:
        add_login_job_log(job_id, "error", f"Login test failed: {e}", "browser_error")
        with services.login_test_lock:
            job = services.login_test_jobs.get(job_id)
            if job:
                job["status"] = "failed"
                job["ended_at"] = datetime.now().isoformat()

def load_all_targets_from_json(label: str) -> List[Dict[str, Any]]:
    filename = "gold_targets.json" if label == "gold" else "real_estate_targets.json"
    import os
    import json
    candidates = [
        os.path.join("config", filename),
        os.path.join("backend", "config", filename),
        os.path.join("..", "config", filename),
    ]
    for path in candidates:
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
    return []

def rich_source_job_from_payload(
    source_name: str, 
    payload: Dict[str, Any], 
    timestamp: str,
    target_url: Optional[str] = None,
    company_name: Optional[str] = None,
    is_real_estate: bool = False
) -> Dict[str, Any]:
    source_upper = company_name.upper() if company_name else source_name.upper()
    results = payload.get("results") if isinstance(payload, dict) else []
    results = results if isinstance(results, list) else []
    status = payload.get("status", "empty") if isinstance(payload, dict) else "empty"
    error = payload.get("error") if isinstance(payload, dict) else None

    if status == "ok" or status == "success":
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

    site = target_sites.get(source_name)
    if not site and target_url:
        from urllib.parse import urlparse
        parsed = urlparse(target_url)
        site = parsed.netloc or target_url
    elif not site:
        site = source_name

    if is_real_estate:
        name_part = company_name or (source_name.title() if source_name == 'alonhadat' else 'Batdongsan')
        job_name = f"Real Estate {name_part}"
        profile = f"crawler_session_{source_name}"
        topic = "Real Estate"
    else:
        job_name = f"Gold Price {source_upper}"
        profile = "crawler_session_default" if source_name not in ["sjc", "doji", "pnj"] else f"crawler_session_{source_name}"
        topic = "Gold Price"

    return {
        "job_name": job_name,
        "target_site": site,
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

@router.get("/api/crawl-jobs")
async def get_crawl_jobs(refresh: bool = Query(False, description="Refresh current source status before building jobs")):
    """Return crawl job status derived from real crawler source payloads."""
    timestamp = datetime.now().isoformat()
    prices = manager.last_prices

    if refresh and tasks.collector:
        current_data = await asyncio.to_thread(tasks.collector.collect_current_prices)
        prices = {}
        for source_name, payload in current_data.items():
            prices[source_name] = payload if payload else empty_source(f'Missing {source_name} payload')
        manager.last_prices = prices

    prices = prices or {}
    house_prices = manager.last_house_prices or {}

    gold_targets = load_all_targets_from_json("gold")
    real_estate_targets = load_all_targets_from_json("real_estate")

    jobs = []
    
    # 1. Gold jobs
    for target in gold_targets:
        tid = target.get("id")
        turl = target.get("url")
        tcompany = target.get("company_name")
        payload = prices.get(tid)
        if not payload:
            payload = empty_source('No crawler snapshot available yet')
        jobs.append(rich_source_job_from_payload(
            source_name=tid,
            payload=payload,
            timestamp=timestamp,
            target_url=turl,
            company_name=tcompany,
            is_real_estate=False
        ))

    # 2. Real estate jobs
    for target in real_estate_targets:
        tid = target.get("id")
        turl = target.get("url")
        tcompany = target.get("company_name")
        payload = house_prices.get(tid)
        if not payload:
            payload = empty_source('No crawler snapshot available yet')
        jobs.append(rich_source_job_from_payload(
            source_name=tid,
            payload=payload,
            timestamp=timestamp,
            target_url=turl,
            company_name=tcompany,
            is_real_estate=True
        ))

    return {
        "timestamp": timestamp,
        "count": len(jobs),
        "jobs": jobs,
    }

@router.post("/api/login-tests")
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
    with services.login_test_lock:
        services.login_test_jobs[job_id] = job

    login_test_executor.submit(run_login_job, job_id, payload.username, payload.password)
    return public_login_job(job)

@router.get("/api/login-tests")
async def list_login_tests():
    """List login test jobs without credentials."""
    with services.login_test_lock:
        jobs = [public_login_job(job) for job in services.login_test_jobs.values()]
    jobs.sort(key=lambda item: item.get("created_at") or "", reverse=True)
    return {
        "timestamp": datetime.now().isoformat(),
        "count": len(jobs),
        "jobs": jobs,
    }

@router.get("/api/login-tests/{job_id}")
async def get_login_test(job_id: str):
    """Get one login test job without credentials."""
    with services.login_test_lock:
        job = services.login_test_jobs.get(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Login test job not found")
        return public_login_job(job)

@router.get("/api/login-tests/{job_id}/logs")
async def get_login_test_logs(job_id: str):
    """Get safe logs for a login test job."""
    with services.login_test_lock:
        job = services.login_test_jobs.get(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Login test job not found")
        return {
            "job_id": job_id,
            "count": len(job.get("logs", [])),
            "logs": job.get("logs", []),
        }


