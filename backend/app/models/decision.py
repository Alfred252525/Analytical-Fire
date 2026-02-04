"""
Decision model - logs AI decision-making processes
"""

from sqlalchemy import Column, Integer, String, DateTime, Text, Float, ForeignKey, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base

class Decision(Base):
    __tablename__ = "decisions"
    
    id = Column(Integer, primary_key=True, index=True)
    ai_instance_id = Column(Integer, ForeignKey("ai_instances.id"), nullable=False)
    
    # Decision context
    task_type = Column(String, index=True)  # e.g., "code_generation", "debugging", "refactoring"
    task_description = Column(Text)
    user_query = Column(Text)
    
    # Decision process
    reasoning = Column(Text)  # The AI's reasoning process
    tools_used = Column(JSON)  # List of tools/functions called
    steps_taken = Column(JSON)  # Sequence of steps in decision-making
    
    # Outcome
    outcome = Column(String)  # "success", "partial", "failure"
    success_score = Column(Float)  # 0.0 to 1.0
    execution_time_ms = Column(Integer)
    
    # Feedback
    user_feedback = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)
    
    # Metadata
    context_hash = Column(String, index=True)  # Hash of context for pattern matching
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    ai_instance = relationship("AIInstance", backref="decisions")
