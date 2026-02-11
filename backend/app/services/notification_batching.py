"""
Notification Batching Service
Groups and batches notifications for efficient delivery
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from collections import defaultdict
from sqlalchemy.orm import Session

from app.models.notification import Notification
from app.models.notification_preferences import NotificationPreferences

logger = logging.getLogger(__name__)


class NotificationBatchingService:
    """Service for batching notifications"""
    
    def __init__(self):
        # In-memory batching queue (in production, use Redis or database)
        self.batching_queues: Dict[int, List[Notification]] = {}
        self.last_batch_time: Dict[int, datetime] = {}
    
    def should_batch(
        self,
        recipient_id: int,
        notification: Notification,
        preferences: NotificationPreferences,
        db: Session
    ) -> bool:
        """
        Determine if notification should be batched
        
        Args:
            recipient_id: ID of agent
            notification: Notification to potentially batch
            preferences: Notification preferences
            db: Database session
            
        Returns:
            True if should batch, False if send immediately
        """
        # Don't batch if batching is disabled
        if not preferences.enable_batching:
            return False
        
        # Never batch urgent notifications
        if notification.priority == "urgent":
            return False
        
        # Don't batch high priority if batch window is too long
        if notification.priority == "high" and preferences.batch_window_seconds > 30:
            return False
        
        return True
    
    def add_to_batch(
        self,
        recipient_id: int,
        notification: Notification,
        preferences: NotificationPreferences
    ) -> bool:
        """
        Add notification to batching queue
        
        Args:
            recipient_id: ID of agent
            notification: Notification to batch
            preferences: Notification preferences
            
        Returns:
            True if added to batch, False if should send immediately
        """
        if not self.should_batch(recipient_id, notification, preferences, None):
            return False
        
        # Initialize queue if needed
        if recipient_id not in self.batching_queues:
            self.batching_queues[recipient_id] = []
            self.last_batch_time[recipient_id] = datetime.utcnow()
        
        # Add to queue
        self.batching_queues[recipient_id].append(notification)
        
        # Check if batch is full
        if len(self.batching_queues[recipient_id]) >= preferences.batch_max_size:
            return True  # Batch is ready
        
        return True  # Added to batch
    
    def get_batch(
        self,
        recipient_id: int,
        preferences: NotificationPreferences
    ) -> Optional[List[Notification]]:
        """
        Get batch if ready to send
        
        Args:
            recipient_id: ID of agent
            preferences: Notification preferences
            
        Returns:
            List of notifications if batch is ready, None otherwise
        """
        if recipient_id not in self.batching_queues:
            return None
        
        queue = self.batching_queues[recipient_id]
        if not queue:
            return None
        
        # Check if batch window has elapsed
        last_time = self.last_batch_time.get(recipient_id)
        if last_time:
            elapsed = (datetime.utcnow() - last_time).total_seconds()
            if elapsed >= preferences.batch_window_seconds:
                # Batch is ready
                batch = queue.copy()
                self.batching_queues[recipient_id] = []
                self.last_batch_time[recipient_id] = datetime.utcnow()
                return batch
        
        # Check if batch is full
        if len(queue) >= preferences.batch_max_size:
            batch = queue.copy()
            self.batching_queues[recipient_id] = []
            self.last_batch_time[recipient_id] = datetime.utcnow()
            return batch
        
        return None
    
    def get_pending_batch(
        self,
        recipient_id: int
    ) -> Optional[List[Notification]]:
        """
        Get pending batch (force send)
        
        Args:
            recipient_id: ID of agent
            
        Returns:
            List of notifications in pending batch, None if empty
        """
        if recipient_id not in self.batching_queues:
            return None
        
        queue = self.batching_queues[recipient_id]
        if not queue:
            return None
        
        batch = queue.copy()
        self.batching_queues[recipient_id] = []
        if recipient_id in self.last_batch_time:
            del self.last_batch_time[recipient_id]
        
        return batch
    
    def group_notifications(
        self,
        notifications: List[Notification]
    ) -> Dict[str, List[Notification]]:
        """
        Group notifications by type and priority
        
        Args:
            notifications: List of notifications
            
        Returns:
            Dictionary grouped by type_priority (e.g., "knowledge_relevant_normal")
        """
        grouped = defaultdict(list)
        
        for notification in notifications:
            # Group by type and priority
            key = f"{notification.notification_type.value}_{notification.priority}"
            grouped[key].append(notification)
        
        return dict(grouped)
    
    def build_batch_summary(
        self,
        notifications: List[Notification]
    ) -> Dict[str, Any]:
        """
        Build summary of batched notifications
        
        Args:
            notifications: List of notifications in batch
            
        Returns:
            Summary dictionary
        """
        # Count by type
        type_counts = defaultdict(int)
        priority_counts = defaultdict(int)
        
        for notification in notifications:
            type_counts[notification.notification_type.value] += 1
            priority_counts[notification.priority] += 1
        
        # Get highest priority
        priority_order = ["urgent", "high", "normal", "low"]
        highest_priority = "low"
        for priority in priority_order:
            if priority in priority_counts:
                highest_priority = priority
                break
        
        return {
            "total_count": len(notifications),
            "type_counts": dict(type_counts),
            "priority_counts": dict(priority_counts),
            "highest_priority": highest_priority,
            "notifications": [
                {
                    "id": n.id,
                    "type": n.notification_type.value,
                    "title": n.title,
                    "priority": n.priority,
                    "created_at": n.created_at.isoformat() if n.created_at else None
                }
                for n in notifications
            ]
        }


# Global batching service instance
batching_service = NotificationBatchingService()
