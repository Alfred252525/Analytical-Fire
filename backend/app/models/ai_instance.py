"""
AI Instance model - represents an AI assistant using the platform
"""

from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base

class AIInstance(Base):
    __tablename__ = "ai_instances"
    
    id = Column(Integer, primary_key=True, index=True)
    instance_id = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=True)
    model_type = Column(String, nullable=True)  # e.g., "gpt-4", "claude", etc.
    api_key_hash = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    role = Column(String, default="user", nullable=False)  # "user", "admin", "moderator", "system"
    instance_metadata = Column(Text)  # JSON string for additional info (renamed from 'metadata' - reserved in SQLAlchemy)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_seen = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships (lazy loading to avoid circular imports)
    credit_transactions = relationship("CreditTransaction", back_populates="ai_instance", lazy="dynamic")
    credit_balance = relationship("CreditBalance", back_populates="ai_instance", uselist=False)
