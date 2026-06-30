from api.websocket import manager
from api.services import empty_source, successful_sources
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Query, HTTPException
import asyncio
from datetime import datetime
from api import tasks

router = APIRouter()

@router.get("/api/house-prices")
async def get_house_prices(
    max_pages: int = Query(1, ge=1, le=5, description="Number of listing pages to crawl per source"),
    use_browser_fallback: bool = Query(True, description="Use Playwright if static HTML fetch is blocked"),
    save_to_csv: bool = Query(True, description="Save house prices to CSV"),
    refresh: bool = Query(False, description="Force a new crawl")
):
    """Get current real-estate listing prices from configured housing sources."""
    if not refresh and getattr(manager, "last_house_prices", None):
        return manager.last_house_prices
    if not refresh:
        return None

    try:
        import json, os
        from crawlers.factory import CrawlerFactory
        from concurrent.futures import ThreadPoolExecutor
        from crawlers.utils import source_result
        
        config_path = os.path.join('config', 'real_estate_targets.json')
        if not os.path.exists(config_path):
            current_data = {}
        else:
            with open(config_path, 'r', encoding='utf-8') as f:
                targets = json.load(f)
                
            crawlers = {}
            for t in targets:
                crawlers[t['id']] = CrawlerFactory.get_crawler(url=t['url'], label=t['label'])
                
            results = {t['id']: empty_source('Not started') for t in targets}
            
            def execute_crawling(crawlers):
                with ThreadPoolExecutor(max_workers=len(crawlers) or 1) as executor:
                    future_map = {
                        executor.submit(crawler.execute): source_name
                        for source_name, crawler in crawlers.items()
                    }
                    for future in future_map:
                        source_name = future_map[future]
                        try:
                            data = future.result()
                            results[source_name] = data if data else empty_source('No data')
                        except Exception as exc:
                            results[source_name] = empty_source(str(exc))
                return results

            current_data = await asyncio.to_thread(execute_crawling, crawlers)
    except Exception as e:
        current_data = {'error': empty_source(str(e))}

    prices = current_data

    manager.last_house_prices = prices

    if save_to_csv and tasks.collector:
        try:
            house_data = successful_sources(current_data)
            if house_data:
                await asyncio.to_thread(tasks.collector.append_house_prices_to_csv, house_data)
        except Exception as e:
            print(f"Error saving house prices to CSV: {e}")

    return {
        "timestamp": datetime.now().isoformat(),
        "topic": "house-price",
        **prices
    }



