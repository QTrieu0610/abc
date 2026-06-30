import json
from typing import List, Dict, Optional, Tuple
from fastapi import WebSocket

class ConnectionManager:
    """Manage WebSocket connections and broadcast messages"""
    
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.last_prices: Optional[Dict] = None
        self.last_house_prices: Optional[Dict] = None
    
    async def connect(self, websocket: WebSocket):
        """Accept and store new WebSocket connection"""
        await websocket.accept()
        self.active_connections.append(websocket)
        print(f"[+] WebSocket client connected. Total connections: {len(self.active_connections)}")
    
    def disconnect(self, websocket: WebSocket):
        """Remove WebSocket connection from pool"""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            print(f"[-] WebSocket client disconnected. Total connections: {len(self.active_connections)}")
    
    async def broadcast(self, message: dict):
        """Send message to all connected clients"""
        if not self.active_connections:
            return
        
        message_json = json.dumps(message)
        failed_connections = []
        for connection in self.active_connections:
            try:
                await connection.send_text(message_json)
            except Exception as e:
                print(f"[-] Failed to send message to a client: {e}")
                failed_connections.append(connection)
                
        # Clean up failed connections
        for failed in failed_connections:
            self.disconnect(failed)

    def has_price_changed(self, new_prices: Dict) -> Tuple[bool, List[str]]:
        """Check if prices have meaningfully changed compared to last known prices"""
        if not self.last_prices:
            return True, ["All prices (initial data)"]
            
        changes = []
        # Exclude 'timestamp'
        companies = [k for k in new_prices.keys() if k != 'timestamp']
        for company in companies:
            old_data = self.last_prices.get(company, {})
            new_data = new_prices.get(company, {})
            
            if not old_data and new_data:
                changes.append(f"{company.upper()} (new data available)")
                continue
                
            old_results = old_data.get("results", []) if isinstance(old_data, dict) else []
            new_results = new_data.get("results", []) if isinstance(new_data, dict) else []
            
            # Simple check: different number of records or different timestamp means change
            if len(old_results) != len(new_results):
                changes.append(f"{company.upper()} (record count changed)")
            elif old_results and new_results and old_results[0].get("datetime") != new_results[0].get("datetime"):
                changes.append(f"{company.upper()} (prices updated)")
                
        return len(changes) > 0, changes

manager = ConnectionManager()
