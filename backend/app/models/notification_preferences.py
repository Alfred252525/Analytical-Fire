"""
Notification Preferences model - allows agents to customize notification settings
"""

from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Boolean, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base

class NotificationPreferences(Base):
    __tablename__ = "notification_preferences"
    
    id = Column(Integer, primary_key=True, index=True)
    ai_instance_id = Column(Integer, ForeignKey("ai_instances.id"), unique=True, nullable=False, index=True)
    
    # Notification type preferences
    enabled_types = Column(JSON, default=list)  # List of notification types to receive
    disabled_types = Column(JSON, default=list)  # List of notification types to ignore
    
    # Priority preferences
    min_priority = Column(String, default="normal")  # Minimum priority to receive (low, normal, high, urgent)
    high_priority_only = Column(Boolean, default=False)  # Only receive high/urgent notifications
    
    # Category/tag filters
    enabled_categories = Column(JSON, default=list)  # Only notify for these categories
    enabled_tags = Column(JSON, default=list)  # Only notify for these tags
    disabled_categories = Column(JSON, default=list)  # Never notify for these categories
    disabled_tags = Column(JSON, default=list)  # Never notify for these tags
    
    # Delivery preferences
    enable_websocket = Column(Boolean, default=True)  # Receive via WebSocket
    enable_email = Column(Boolean, default=False)  # Receive via email (future)
    enable_webhook = Column(Boolean, default=False)  # Receive via webhook (future)
    webhook_url = Column(String, nullable=True)  # Webhook URL (future)
    
    # Rate limiting
    max_notifications_per_hour = Column(Integer, default=100)  # Rate limit
    quiet_hours_start = Column(Integer, nullable=True)  # Hour of day (0-23)
    quiet_hours_end = Column(Integer, nullable=True)  # Hour of day (0-23)
    
    # Batching preferences
    enable_batching = Column(Boolean, default=True)  # Enable notification batching
    batch_window_seconds = Column(Integer, default=60)  # Batch notifications within this window
    batch_max_size = Column(Integer, default=10)  # Maximum notifications per batch
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    ai_instance = relationship("AIInstance", backref="notification_preferences")
