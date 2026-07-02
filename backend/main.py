import os
import asyncio
from typing import Optional, Dict, Any
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from api.routers import gold, real_estate, analytics, system, targets
from api.tasks import background_price_checker
from api import tasks, services
from data_collector import HistoricalDataCollector
from data_analyzer import GoldPriceAnalyzer

# Initialize Data Collector & Analyzer
API_KEY = os.environ.get("VAPI_API_KEY", "")
collector_instance = HistoricalDataCollector(api_key=API_KEY)
analyzer_instance = GoldPriceAnalyzer()

# Inject into routers
tasks.collector = collector_instance
services.analyzer = analyzer_instance

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Start background tasks
    task = asyncio.create_task(background_price_checker())
    yield
    # Shutdown
    task.cancel()

app = FastAPI(
    title="Gold Price Dashboard API (3-Tier Architecture)",
    description="API for fetching and caching gold and real estate prices using 3-Tier Fallback Strategy",
    version="3.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(gold.router)
app.include_router(real_estate.router)
app.include_router(analytics.router)
app.include_router(system.router)
app.include_router(targets.router)

def load_latest_gold_prices_from_csv() -> Optional[Dict[str, Any]]:
    import csv
    csv_file = 'historical_data/historical_gold_prices.csv'
    if not os.path.exists(csv_file):
        return None
        
    rows = []
    try:
        from data_collector import csv_lock
        with csv_lock:
            with open(csv_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for r in reader:
                    rows.append(r)
    except Exception as e:
        print(f"Error reading gold CSV on startup: {e}")
        return None
        
    if not rows:
        return None
        
    latest_ts = max(r.get('timestamp', '') for r in rows)
    if not latest_ts:
        return None
        
    latest_rows = [r for r in rows if r.get('timestamp') == latest_ts]
    prices = {
        'timestamp': latest_ts
    }
    
    from api.routers.system import load_all_targets_from_json
    gold_targets = load_all_targets_from_json("gold")
    id_map = {}
    for t in gold_targets:
        tid = t.get("id")
        company_name = t.get("company_name")
        id_map[tid.upper()] = tid
        if company_name:
            id_map[company_name.upper()] = tid
            
    for r in latest_rows:
        company = r.get('company', '')
        if not company:
            continue
        tid = id_map.get(company.upper(), company.lower())
        try:
            buy = int(float(r.get('buy_price'))) if r.get('buy_price') else None
        except Exception:
            buy = None
        try:
            sell = int(float(r.get('sell_price'))) if r.get('sell_price') else None
        except Exception:
            sell = None
            
        record = {
            'company': company,
            'gold_type': r.get('gold_type'),
            'buy_price': buy,
            'sell_price': sell,
            'location': r.get('location', 'National'),
            'timestamp': latest_ts,
            'source': r.get('source') or company
        }
        if tid not in prices:
            prices[tid] = {
                'status': 'success',
                'results': [],
                'error': None
            }
        prices[tid]['results'].append(record)
    return prices

def load_latest_house_prices_from_csv() -> Optional[Dict[str, Any]]:
    import csv
    csv_file = 'historical_data/historical_house_prices.csv'
    if not os.path.exists(csv_file):
        return None
        
    rows = []
    try:
        from data_collector import csv_lock
        with csv_lock:
            with open(csv_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for r in reader:
                    rows.append(r)
    except Exception as e:
        print(f"Error reading house CSV on startup: {e}")
        return None
        
    if not rows:
        return None
        
    latest_ts = max(r.get('timestamp', '') for r in rows)
    if not latest_ts:
        return None
        
    latest_rows = [r for r in rows if r.get('timestamp') == latest_ts]
    prices = {
        'timestamp': latest_ts
    }
    
    from api.routers.system import load_all_targets_from_json
    re_targets = load_all_targets_from_json("real_estate")
    id_map = {}
    for t in re_targets:
        tid = t.get("id")
        company_name = t.get("company_name")
        id_map[tid.upper()] = tid
        if company_name:
            id_map[company_name.upper()] = tid
            
    for r in latest_rows:
        source = r.get('source', '')
        if not source:
            continue
        tid = id_map.get(source.upper(), source.lower())
        try:
            price = int(float(r.get('price'))) if r.get('price') else None
        except Exception:
            price = None
        try:
            area = float(r.get('area_m2')) if r.get('area_m2') else None
        except Exception:
            area = None
        try:
            price_per_m2 = float(r.get('price_per_m2')) if r.get('price_per_m2') else None
        except Exception:
            price_per_m2 = None
            
        record = {
            'title': r.get('title'),
            'price': price,
            'price_text': r.get('price_text'),
            'area_m2': area,
            'price_per_m2': price_per_m2,
            'location': r.get('location'),
            'url': r.get('url'),
            'timestamp': latest_ts,
            'source': source
        }
        if tid not in prices:
            prices[tid] = {
                'status': 'success',
                'results': [],
                'error': None
            }
        prices[tid]['results'].append(record)
    return prices

try:
    from api.websocket import manager
    latest_gold = load_latest_gold_prices_from_csv()
    if latest_gold:
        manager.last_prices = latest_gold
        print(f"[+] Loaded latest gold prices from CSV: {latest_gold.get('timestamp')}")
        
    latest_house = load_latest_house_prices_from_csv()
    if latest_house:
        manager.last_house_prices = latest_house
        print(f"[+] Loaded latest house prices from CSV: {latest_house.get('timestamp')}")
except Exception as e:
    print(f"[-] Error loading cached data from CSV: {e}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
