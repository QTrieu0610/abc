import asyncio
from datetime import datetime
from typing import Optional
from api.websocket import manager
from api.services import empty_source, successful_sources

# The collector instance will be injected from main.py or initialized here later
collector = None

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
            if collector:
                current_data = await asyncio.to_thread(collector.collect_current_prices)
                
            if current_data:
                prices = {
                    'timestamp': datetime.now().isoformat(),
                }
                for k, v in current_data.items():
                    prices[k] = v
                
                has_changed, alerts = manager.has_price_changed(prices)
                if has_changed:
                    print(f"[+] Price change detected at {datetime.now().strftime('%H:%M:%S')}")
                    
                    if collector:
                        try:
                            data = successful_sources(prices)
                            if data:
                                await asyncio.to_thread(collector.append_to_csv, data)
                        except Exception as e:
                            print(f"Error saving to CSV: {e}")
                    
                    await manager.broadcast({
                        'type': 'price_update',
                        'timestamp': datetime.now().isoformat(),
                        'prices': prices,
                        'message': 'New gold prices available'
                    })
                    
                    for alert in alerts:
                        await manager.broadcast({
                            'type': 'alert',
                            'message': f"Price changed for: {alert}"
                        })
                        
                    manager.last_prices = prices
                else:
                    print(f"[*] No price changes at {datetime.now().strftime('%H:%M:%S')}")
            else:
                await manager.broadcast({
                    'type': 'error',
                    'message': 'Failed to fetch current prices'
                })
                
        except Exception as e:
            print(f"[-] Error in background checker: {e}")
            await manager.broadcast({
                'type': 'error',
                'message': f'Background sync error: {str(e)}'
            })
            
        await asyncio.sleep(300)
