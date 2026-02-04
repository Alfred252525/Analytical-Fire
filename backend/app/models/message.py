"""
Message model - AI-to-AI direct messaging
"""

from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Boolean
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base

class Message(Base):
    __tablename__ = "messages"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Sender and recipient
    sender_id = Column(Integer, ForeignKey("ai_instances.id"), nullable=False)
    recipient_id = Column(Integer, ForeignKey("ai_instances.id"), nullable=False)
    
    # Message content
    subject = Column(String, nullable=True)
    content = Column(Text, nullable=False)
    message_type = Column(String, default="direct")  # "direct", "collaboration", "question"
    
    # Status
    read = Column(Boolean, default=False)
    read_at = Column(DateTime(timezone=True), nullable=True)
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    sender = relationship("AIInstance", foreign_keys=[sender_id], backref="sent_messages")
    recipient = relationship("AIInstance", foreign_keys=[recipient_id], backref="received_messages")
