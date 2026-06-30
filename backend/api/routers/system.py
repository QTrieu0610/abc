from typing import Optional, List, Dict, Any
import asyncio
from datetime import datetime
from fastapi import APIRouter, HTTPException, Query
from models.api_models import CrawlUrlRequest, LoginTestRequest
from crawlers import CrawlerFactory
from api.services import safe_session_metadata
from api import tasks
from api import services

router = APIRouter()

@router.post("/api/crawl-url")
async def crawl_url(payload: CrawlUrlRequest):
    """Crawl a generic URL for gold or real estate data using 3-Tier Architecture."""
    try:
        # Tầng 1: Sử dụng CrawlerFactory định tuyến URL
        crawler = CrawlerFactory.get_crawler(url=payload.url, label=payload.type)
        
        # Tầng 2 & 3: Thực thi luồng 3-Tier Fallback (HTTP -> Playwright -> LLM)
        result = await asyncio.to_thread(crawler.execute)
        
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


