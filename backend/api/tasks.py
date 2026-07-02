import asyncio
from datetime import datetime
from typing import Optional
from api.websocket import manager
from api.services import empty_source, successful_sources

# The collector instance will be injected from main.py or initialized here later
collector = None

async def background_price_checker():
    """Background task is disabled as per user request to only crawl manually via refresh."""
    print("[*] Background price checker auto-crawl is disabled.")
    while True:
        await asyncio.sleep(3600)  # Keep the coroutine alive doing nothing
