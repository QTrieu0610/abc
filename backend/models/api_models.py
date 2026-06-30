from pydantic import BaseModel
from typing import Optional, Dict, Any

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

class CrawlUrlRequest(BaseModel):
    url: str
    type: str  # "gold" or "real_estate"
