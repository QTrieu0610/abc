from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Query, HTTPException
from fastapi.responses import FileResponse
from models.api_models import AnalyticsResponse, TrendResponse
import asyncio
import os
from datetime import datetime
from api import services

router = APIRouter()

@router.get("/api/export/csv")
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



@router.get("/api/analytics/trends")
async def get_trends(
    company: str = Query(..., description="Company name (SJC, DOJI, or PNJ)"),
    period: str = Query('weekly', description="Time period (weekly, monthly, quarterly, yearly)"),
    gold_type: Optional[str] = Query(None, description="Gold type (e.g., 'SJC 1L')"),
    location: Optional[str] = Query(None, description="Location (e.g., 'National')")
):
    """Get price trends for a company, gold type, and optional location."""
    if not services.analyzer:
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
            services.analyzer.get_price_trends,
            company.upper(),
            days_back=days,
            location=location,
            gold_type=gold_type
        )
        ma_data = await asyncio.to_thread(
            services.analyzer.get_moving_average,
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

@router.get("/api/analytics/source-momentum")
async def get_source_momentum(
    scope: str = Query('main', description="Momentum scope: main or all"),
    compare: str = Query('previous', description="Comparison mode: previous")
):
    """Compare latest saved source rows against their previous crawl."""
    if not services.analyzer:
        raise HTTPException(status_code=500, detail="Analyzer service unavailable")

    scope_lower = scope.lower()
    compare_lower = compare.lower()

    if scope_lower not in ['main', 'all']:
        raise HTTPException(status_code=400, detail="Invalid scope. Must be main or all")
    if compare_lower != 'previous':
        raise HTTPException(status_code=400, detail="Invalid compare. Must be previous")

    try:
        return await asyncio.to_thread(services.analyzer.get_source_momentum, scope=scope_lower, compare=compare_lower)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


