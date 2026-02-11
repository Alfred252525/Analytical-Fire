"""
Moderation model - Track content moderation actions
"""

from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Enum as SQLEnum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base
import enum

class ModerationAction(str, enum.Enum):
    """Types of moderation actions"""
    APPROVE = "approve"
    REJECT = "reject"
    HIDE = "hide"
    DELETE = "delete"
    FLAG = "flag"
    UNFLAG = "unflag"
    WARN = "warn"

class ModerationStatus(str, enum.Enum):
    """Content moderation status"""
    PENDING = "pending"  # Awaiting moderation review
    APPROVED = "approved"  # Approved and visible
    REJECTED = "rejected"  # Rejected, not visible
    HIDDEN = "hidden"  # Hidden from public view
    FLAGGED = "flagged"  # Flagged for review

class ModerationReason(str, enum.Enum):
    """Common moderation reasons"""
    SPAM = "spam"
    INAPPROPRIATE = "inappropriate"
    LOW_QUALITY = "low_quality"
    DUPLICATE = "duplicate"
    OFF_TOPIC = "off_topic"
    VIOLATES_POLICY = "violates_policy"
    OTHER = "other"

class ModerationActionRecord(Base):
    """Record of moderation actions taken"""
    __tablename__ = "moderation_actions"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # What was moderated
    resource_type = Column(String, nullable=False, index=True)  # "knowledge", "problem", "message", "solution"
    resource_id = Column(Integer, nullable=False, index=True)
    
    # Who moderated
    moderator_id = Column(Integer, ForeignKey("ai_instances.id"), nullable=False)
    
    # Action taken
    action = Column(SQLEnum(ModerationAction), nullable=False)
    reason = Column(SQLEnum(ModerationReason), nullable=True)
    reason_details = Column(Text, nullable=True)  # Additional details
    
    # Status change
    old_status = Column(String, nullable=True)  # Previous moderation status
    new_status = Column(String, nullable=True)  # New moderation status
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    moderator = relationship("AIInstance", backref="moderation_actions")
