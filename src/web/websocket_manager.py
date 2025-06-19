import asyncio
import json
import logging
from typing import List, Dict, Any
from fastapi import WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)

class WebSocketManager:
    """Manages WebSocket connections and real-time updates"""
    
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.connection_data: Dict[WebSocket, Dict] = {}
    
    async def connect(self, websocket: WebSocket, client_id: str = None):
        """Accept a new WebSocket connection"""
        await websocket.accept()
        self.active_connections.append(websocket)
        self.connection_data[websocket] = {
            "client_id": client_id,
            "connected_at": asyncio.get_event_loop().time(),
            "subscriptions": set()
        }
        logger.info(f"WebSocket connected: {client_id or 'anonymous'}")
    
    def disconnect(self, websocket: WebSocket):
        """Remove a WebSocket connection"""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            client_data = self.connection_data.pop(websocket, {})
            logger.info(f"WebSocket disconnected: {client_data.get('client_id', 'anonymous')}")
    
    async def send_personal_message(self, message: Dict[str, Any], websocket: WebSocket):
        """Send a message to a specific WebSocket connection"""
        try:
            await websocket.send_text(json.dumps(message))
        except Exception as e:
            logger.error(f"Error sending personal message: {e}")
            self.disconnect(websocket)
    
    async def broadcast(self, message: Dict[str, Any], subscription: str = None):
        """Broadcast a message to all connected clients or specific subscription"""
        disconnected = []
        
        for websocket in self.active_connections:
            try:
                # Check subscription filter
                if subscription:
                    conn_data = self.connection_data.get(websocket, {})
                    if subscription not in conn_data.get("subscriptions", set()):
                        continue
                
                await websocket.send_text(json.dumps(message))
            except Exception as e:
                logger.error(f"Error broadcasting to client: {e}")
                disconnected.append(websocket)
        
        # Clean up disconnected clients
        for websocket in disconnected:
            self.disconnect(websocket)
    
    async def subscribe(self, websocket: WebSocket, subscription: str):
        """Subscribe a client to a specific data stream"""
        if websocket in self.connection_data:
            self.connection_data[websocket]["subscriptions"].add(subscription)
            logger.info(f"Client subscribed to: {subscription}")
    
    async def unsubscribe(self, websocket: WebSocket, subscription: str):
        """Unsubscribe a client from a data stream"""
        if websocket in self.connection_data:
            self.connection_data[websocket]["subscriptions"].discard(subscription)
            logger.info(f"Client unsubscribed from: {subscription}")
    
    async def handle_message(self, websocket: WebSocket, message: str):
        """Handle incoming WebSocket messages"""
        try:
            data = json.loads(message)
            message_type = data.get("type")
            
            if message_type == "subscribe":
                await self.subscribe(websocket, data.get("subscription"))
                await self.send_personal_message({
                    "type": "subscription_confirmed",
                    "subscription": data.get("subscription")
                }, websocket)
            
            elif message_type == "unsubscribe":
                await self.unsubscribe(websocket, data.get("subscription"))
                await self.send_personal_message({
                    "type": "unsubscription_confirmed", 
                    "subscription": data.get("subscription")
                }, websocket)
            
            elif message_type == "ping":
                await self.send_personal_message({
                    "type": "pong",
                    "timestamp": asyncio.get_event_loop().time()
                }, websocket)
            
            else:
                logger.warning(f"Unknown message type: {message_type}")
        
        except json.JSONDecodeError:
            logger.error("Invalid JSON received from WebSocket")
            await self.send_personal_message({
                "type": "error",
                "message": "Invalid JSON format"
            }, websocket)
        except Exception as e:
            logger.error(f"Error handling WebSocket message: {e}")
    
    async def send_market_update(self, market_data: Dict[str, Any]):
        """Send market data updates to subscribed clients"""
        await self.broadcast({
            "type": "market_update",
            "data": market_data,
            "timestamp": asyncio.get_event_loop().time()
        }, subscription="markets")
    
    async def send_position_update(self, position_data: Dict[str, Any]):
        """Send position updates to subscribed clients"""
        await self.broadcast({
            "type": "position_update",
            "data": position_data,
            "timestamp": asyncio.get_event_loop().time()
        }, subscription="positions")
    
    async def send_trade_alert(self, trade_data: Dict[str, Any]):
        """Send trade execution alerts"""
        await self.broadcast({
            "type": "trade_executed",
            "data": trade_data,
            "timestamp": asyncio.get_event_loop().time()
        }, subscription="trades")
    
    async def send_analysis_update(self, analysis_data: Dict[str, Any]):
        """Send AI analysis updates"""
        await self.broadcast({
            "type": "analysis_update",
            "data": analysis_data,
            "timestamp": asyncio.get_event_loop().time()
        }, subscription="analysis")
    
    def get_connection_count(self) -> int:
        """Get the number of active connections"""
        return len(self.active_connections)
    
    def get_connection_stats(self) -> Dict[str, Any]:
        """Get connection statistics"""
        current_time = asyncio.get_event_loop().time()
        connections = []
        
        for websocket, data in self.connection_data.items():
            connections.append({
                "client_id": data.get("client_id"),
                "connected_duration": current_time - data.get("connected_at", current_time),
                "subscriptions": list(data.get("subscriptions", set()))
            })
        
        return {
            "total_connections": len(self.active_connections),
            "connections": connections
        }

# Global WebSocket manager instance
websocket_manager = WebSocketManager()