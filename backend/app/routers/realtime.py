"""
Real-time collaboration router
WebSocket endpoints for live updates and notifications
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Dict, Any
from datetime import datetime
import json

from app.database import get_db
from app.models.ai_instance import AIInstance
from app.core.security import verify_password
from app.services.realtime import realtime_manager, create_notification

router = APIRouter()

class ConnectionManager:
    """Manages WebSocket connections"""
    
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
    
    async def connect(self, websocket: WebSocket, connection_id: str):
        await websocket.accept()
        self.active_connections[connection_id] = websocket
    
    def disconnect(self, connection_id: str):
        if connection_id in self.active_connections:
            del self.active_connections[connection_id]
    
    async def send_personal_message(self, message: Dict[str, Any], connection_id: str):
        if connection_id in self.active_connections:
            websocket = self.active_connections[connection_id]
            try:
                await websocket.send_json(message)
            except:
                # Connection closed
                self.disconnect(connection_id)
    
    async def broadcast(self, message: Dict[str, Any], connection_ids: List[str]):
        for connection_id in connection_ids:
            await self.send_personal_message(message, connection_id)

manager = ConnectionManager()

@router.websocket("/ws/{instance_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    instance_id: int,
    api_key: str
):
    """
    WebSocket endpoint for real-time updates
    Requires authentication via API key
    """
    # Verify API key
    db = next(get_db())
    try:
        instance = db.query(AIInstance).filter(
            AIInstance.id == instance_id
        ).first()
        
        if not instance or not verify_password(api_key, instance.api_key_hash):
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return
    except:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return
    finally:
        db.close()
    
    # Generate connection ID
    connection_id = f"{instance_id}_{datetime.utcnow().timestamp()}"
    
    # Connect
    await manager.connect(websocket, connection_id)
    realtime_manager.connect(connection_id, instance_id)
    
    try:
        # Send welcome message
        await manager.send_personal_message({
            "type": "connected",
            "connection_id": connection_id,
            "instance_id": instance_id,
            "timestamp": datetime.utcnow().isoformat()
        }, connection_id)
        
        # Listen for messages
        while True:
            data = await websocket.receive_json()
            
            # Handle subscription requests
            if data.get("type") == "subscribe":
                event_type = data.get("event_type")
                if event_type:
                    realtime_manager.subscribe(connection_id, event_type)
                    await manager.send_personal_message({
                        "type": "subscribed",
                        "event_type": event_type,
                        "timestamp": datetime.utcnow().isoformat()
                    }, connection_id)
            
            # Handle unsubscribe requests
            elif data.get("type") == "unsubscribe":
                event_type = data.get("event_type")
                if event_type:
                    realtime_manager.unsubscribe(connection_id, event_type)
                    await manager.send_personal_message({
                        "type": "unsubscribed",
                        "event_type": event_type,
                        "timestamp": datetime.utcnow().isoformat()
                    }, connection_id)
            
            # Handle ping
            elif data.get("type") == "ping":
                await manager.send_personal_message({
                    "type": "pong",
                    "timestamp": datetime.utcnow().isoformat()
                }, connection_id)
    
    except WebSocketDisconnect:
        manager.disconnect(connection_id)
        realtime_manager.disconnect(connection_id)

@router.post("/notify")
async def send_notification(
    event_type: str,
    data: Dict[str, Any],
    target_instance_id: int = None,
    broadcast: bool = False,
    db: Session = Depends(get_db)
):
    """
    Send a notification to connected clients
    (For testing/internal use)
    """
    notification = create_notification(
        event_type=event_type,
        data=data,
        target_instance_id=target_instance_id,
        broadcast=broadcast
    )
    
    # Get subscribers
    if broadcast:
        subscribers = realtime_manager.get_subscribers(event_type)
    elif target_instance_id:
        subscribers = realtime_manager.get_connections_for_instance(target_instance_id)
    else:
        subscribers = set()
    
    # Send to all subscribers
    connection_ids = list(subscribers)
    await manager.broadcast(notification, connection_ids)
    
    return {
        "sent": True,
        "recipients": len(connection_ids),
        "notification": notification
    }
