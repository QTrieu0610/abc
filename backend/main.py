import os
import asyncio
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
