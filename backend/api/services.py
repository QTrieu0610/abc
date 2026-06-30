import os
import json
import requests
import uuid
import threading
from typing import Optional, Dict, List, Any
from datetime import datetime

class GoldPriceAPI:
    """Handle API requests to the Gold Price API"""
    BASE_URL = "https://vapi.vnappmob.com"
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key
        self.headers = {'Accept': 'application/json'}
        if api_key:
            self.headers['Authorization'] = f'Bearer {api_key}'
    
    def get_company_price(self, company: str, date_from: Optional[str] = None, 
                         date_to: Optional[str] = None) -> Optional[Dict]:
        url = f"{self.BASE_URL}/api/v2/gold/{company.lower()}"
        params = {}
        if date_from: params['date_from'] = date_from
        if date_to: params['date_to'] = date_to
        
        try:
            response = requests.get(url, headers=self.headers, params=params, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error fetching {company} price: {e}")
            return None

def empty_source(error: Optional[str] = None) -> Dict[str, Any]:
    return {'status': 'failed' if error else 'empty', 'results': [], 'error': error}

def successful_sources(current_data: Optional[Dict[str, Any]]) -> Dict[str, List[Dict]]:
    if not current_data: return {}
    data = {}
    for source_name, payload in current_data.items():
        if not isinstance(payload, dict): continue
        results = payload.get('results') or []
        if payload.get('status') == 'success' and results:
            data[source_name] = results
    return data

def safe_session_metadata(session_dir: str = "sessions") -> List[Dict[str, Any]]:
    sessions = []
    if not os.path.exists(session_dir): return sessions
    
    for filename in os.listdir(session_dir):
        if not filename.endswith(".json"): continue
        path = os.path.join(session_dir, filename)
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            safe_cookies = []
            for c in data.get("cookies", []):
                safe_cookies.append({
                    "name": c.get("name"), "domain": c.get("domain"),
                    "path": c.get("path"), "expires": c.get("expires")
                })
            
            sessions.append({
                "filename": filename,
                "profile_name": filename.replace("crawler_session_", "").replace(".json", ""),
                "origins": data.get("origins", []),
                "cookies_count": len(data.get("cookies", [])),
                "safe_cookies": safe_cookies
            })
        except Exception: pass
    return sessions

def source_job_from_payload(source_name: str, payload: Dict[str, Any], timestamp: str) -> Dict[str, Any]:
    error = payload.get("error")
    if error and "HITL_REQUIRED" in str(error):
        return {
            "id": f"hitl_{source_name}_{timestamp}", "source": source_name, "status": "blocked",
            "reason": str(error), "timestamp": timestamp
        }
    return {
        "id": f"job_{source_name}_{timestamp}", "source": source_name, "status": payload.get("status", "unknown"),
        "error": error, "timestamp": timestamp
    }

analyzer = None

import threading
login_test_lock = threading.Lock()
login_test_jobs = {}
hitl_cases = {}
