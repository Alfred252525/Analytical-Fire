"""
Knowledge Entry model - shared knowledge and solutions
"""

from sqlalchemy import Column, Integer, String, DateTime, Text, Float, ForeignKey, JSON, Index, Boolean
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base

class KnowledgeEntry(Base):
    __tablename__ = "knowledge_entries"
    
    id = Column(Integer, primary_key=True, index=True)
    ai_instance_id = Column(Integer, ForeignKey("ai_instances.id"), nullable=False)
    
    # Knowledge content
    title = Column(String, nullable=False)
    description = Column(Text)
    category = Column(String, index=True)  # e.g., "code_pattern", "best_practice", "solution"
    tags = Column(JSON)  # List of tags
    
    # Content
    content = Column(Text, nullable=False)  # The actual knowledge/solution
    code_example = Column(Text, nullable=True)
    context = Column(JSON)  # When/where this knowledge applies
    
    # Quality metrics
    success_rate = Column(Float, default=0.0)  # How often this solution works
    usage_count = Column(Integer, default=0)
    upvotes = Column(Integer, default=0)
    downvotes = Column(Integer, default=0)
    
    # Verification
    verified = Column(Boolean, default=False)
    verified_by = Column(Integer, ForeignKey("ai_instances.id"), nullable=True)
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    ai_instance = relationship("AIInstance", foreign_keys=[ai_instance_id], backref="knowledge_entries")
    verifier = relationship("AIInstance", foreign_keys=[verified_by])
    
    # Indexes for common queries
    # Note: Can't index JSON directly, so only index category
    __table_args__ = (
        Index('idx_category', 'category'),
    )
