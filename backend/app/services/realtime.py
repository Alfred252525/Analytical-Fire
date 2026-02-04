"""
Real-time collaboration service
Handles WebSocket connections, notifications, and live updates
"""

from typing import Dict, List, Set, Optional, Any
from datetime import datetime
import json

class RealtimeManager:
    """Manages real-time connections and notifications"""
    
    def __init__(self):
        self.connections: Dict[int, Set[str]] = {}  # instance_id -> set of connection_ids
        self.connection_instances: Dict[str, int] = {}  # connection_id -> instance_id
        self.subscriptions: Dict[str, Set[str]] = {}  # event_type -> set of connection_ids
    
    def connect(self, connection_id: str, instance_id: int):
        """Register a new connection"""
        if instance_id not in self.connections:
            self.connections[instance_id] = set()
        
        self.connections[instance_id].add(connection_id)
        self.connection_instances[connection_id] = instance_id
    
    def disconnect(self, connection_id: str):
        """Remove a connection"""
        instance_id = self.connection_instances.get(connection_id)
        if instance_id and instance_id in self.connections:
            self.connections[instance_id].discard(connection_id)
        
        del self.connection_instances[connection_id]
        
        # Remove from all subscriptions
        for subscriptions in self.subscriptions.values():
            subscriptions.discard(connection_id)
    
    def subscribe(self, connection_id: str, event_type: str):
        """Subscribe to an event type"""
        if event_type not in self.subscriptions:
            self.subscriptions[event_type] = set()
        self.subscriptions[event_type].add(connection_id)
    
    def unsubscribe(self, connection_id: str, event_type: str):
        """Unsubscribe from an event type"""
        if event_type in self.subscriptions:
            self.subscriptions[event_type].discard(connection_id)
    
    def get_connections_for_instance(self, instance_id: int) -> Set[str]:
        """Get all connections for an instance"""
        return self.connections.get(instance_id, set())
    
    def get_subscribers(self, event_type: str) -> Set[str]:
        """Get all subscribers to an event type"""
        return self.subscriptions.get(event_type, set())
    
    def broadcast_to_instance(self, instance_id: int, event_type: str, data: Dict[str, Any]) -> int:
        """Broadcast to all connections for an instance"""
        connections = self.get_connections_for_instance(instance_id)
        return len(connections)
    
    def broadcast_to_subscribers(self, event_type: str, data: Dict[str, Any]) -> int:
        """Broadcast to all subscribers of an event type"""
        subscribers = self.get_subscribers(event_type)
        return len(subscribers)
    
    def broadcast_to_all(self, event_type: str, data: Dict[str, Any]) -> int:
        """Broadcast to all connections"""
        all_connections = set()
        for connections in self.connections.values():
            all_connections.update(connections)
        return len(all_connections)

# Global realtime manager instance
realtime_manager = RealtimeManager()

def create_notification(
    event_type: str,
    data: Dict[str, Any],
    target_instance_id: Optional[int] = None,
    broadcast: bool = False
) -> Dict[str, Any]:
    """
    Create a notification event
    
    Event types:
    - knowledge_created: New knowledge entry created
    - knowledge_updated: Knowledge entry updated
    - decision_logged: New decision logged
    - pattern_discovered: New pattern discovered
    - instance_joined: New AI instance joined
    """
    notification = {
        "event_type": event_type,
        "data": data,
        "timestamp": datetime.utcnow().isoformat(),
        "target_instance_id": target_instance_id,
        "broadcast": broadcast
    }
    
    return notification

def should_notify(event_type: str, instance_id: int) -> bool:
    """Determine if an instance should receive a notification"""
    # For now, notify all instances for broadcast events
    # Can add filtering logic here
    return True
