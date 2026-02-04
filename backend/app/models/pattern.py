"""
Pattern model - identified patterns in AI behavior and solutions
"""

from sqlalchemy import Column, Integer, String, DateTime, Text, Float, JSON, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base

class Pattern(Base):
    __tablename__ = "patterns"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Pattern identification
    pattern_type = Column(String, index=True)  # "success_pattern", "failure_pattern", "optimization"
    name = Column(String, nullable=False)
    description = Column(Text)
    
    # Pattern characteristics
    conditions = Column(JSON)  # Conditions when this pattern occurs
    indicators = Column(JSON)  # Indicators that suggest this pattern
    solution = Column(Text)  # Recommended solution if applicable
    
    # Pattern metrics
    frequency = Column(Integer, default=0)  # How often this pattern is observed
    confidence = Column(Float, default=0.0)  # Confidence in pattern validity (0.0 to 1.0)
    success_rate = Column(Float, default=0.0)  # Success rate when pattern is applied
    
    # Related data
    related_decisions = Column(JSON)  # IDs of decisions that exhibit this pattern
    related_knowledge = Column(JSON)  # IDs of knowledge entries related to this pattern
    
    # Metadata
    discovered_at = Column(DateTime(timezone=True), server_default=func.now())
    last_observed = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
