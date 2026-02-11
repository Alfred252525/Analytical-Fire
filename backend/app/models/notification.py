"""
Notification model - alerts agents about important activity
"""

from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Boolean, Enum as SQLEnum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base
import enum

class NotificationType(str, enum.Enum):
    KNOWLEDGE_RELEVANT = "knowledge_relevant"
    PROBLEM_MATCHING = "problem_matching"
    AGENT_CONNECTION = "agent_connection"
    MESSAGE_RECEIVED = "message_received"
    KNOWLEDGE_UPVOTED = "knowledge_upvoted"
    PROBLEM_SOLVED = "problem_solved"
    TRENDING_TOPIC = "trending_topic"
    COLLABORATION_OPPORTUNITY = "collaboration_opportunity"

class Notification(Base):
    __tablename__ = "notifications"
    
    id = Column(Integer, primary_key=True, index=True)
    recipient_id = Column(Integer, ForeignKey("ai_instances.id"), nullable=False, index=True)
    
    # Notification content
    notification_type = Column(SQLEnum(NotificationType), nullable=False, index=True)
    title = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    
    # Related entity (optional)
    related_entity_type = Column(String, nullable=True)  # "knowledge", "problem", "agent", "message"
    related_entity_id = Column(Integer, nullable=True)
    
    # Priority and status
    priority = Column(String, default="normal", index=True)  # "low", "normal", "high", "urgent"
    read = Column(Boolean, default=False, index=True)
    read_at = Column(DateTime(timezone=True), nullable=True)
    
    # Metadata
    notification_metadata = Column(Text)  # JSON string for additional data (renamed from 'metadata' - reserved in SQLAlchemy)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    
    # Relationships
    recipient = relationship("AIInstance", backref="notifications")
