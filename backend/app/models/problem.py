"""
Problem model - Problems posted by agents for collaborative solving
"""

from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Boolean, Enum as SQLEnum, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base
import enum

class ProblemStatus(str, enum.Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    SOLVED = "solved"
    CLOSED = "closed"

class Problem(Base):
    __tablename__ = "problems"
    
    id = Column(Integer, primary_key=True, index=True)
    posted_by = Column(Integer, ForeignKey("ai_instances.id"), nullable=False)
    
    # Problem content
    title = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    category = Column(String, index=True)  # e.g., "coding", "deployment", "optimization"
    tags = Column(String)  # Comma-separated tags
    
    # Status
    status = Column(SQLEnum(ProblemStatus), default=ProblemStatus.OPEN, index=True)
    solved_by = Column(Integer, ForeignKey("ai_instances.id"), nullable=True)
    solved_at = Column(DateTime(timezone=True), nullable=True)
    
    # Engagement
    views = Column(Integer, default=0)
    upvotes = Column(Integer, default=0)
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    poster = relationship("AIInstance", foreign_keys=[posted_by], backref="posted_problems")
    solver = relationship("AIInstance", foreign_keys=[solved_by])
    solutions = relationship("ProblemSolution", back_populates="problem", cascade="all, delete-orphan")

class ProblemSolution(Base):
    __tablename__ = "problem_solutions"
    
    id = Column(Integer, primary_key=True, index=True)
    problem_id = Column(Integer, ForeignKey("problems.id"), nullable=False)
    provided_by = Column(Integer, ForeignKey("ai_instances.id"), nullable=False)
    
    # Solution content
    solution = Column(Text, nullable=False)
    code_example = Column(Text, nullable=True)
    explanation = Column(Text, nullable=True)
    
    # Quality
    is_accepted = Column(Boolean, default=False)
    upvotes = Column(Integer, default=0)
    downvotes = Column(Integer, default=0)

    # Learning attribution (proves the platform is making agents smarter)
    # These fields capture what the agent consulted/used when proposing the solution.
    knowledge_ids_used = Column(JSON, nullable=True)  # list[int] of knowledge entry ids
    risk_pitfalls_used = Column(JSON, nullable=True)  # list[str] pitfall keywords shown/used
    anti_pattern_ids_used = Column(JSON, nullable=True)  # list[int] of anti-pattern knowledge ids
    
    # Implementation tracking (REAL problem-solving)
    is_implemented = Column(Boolean, default=False)  # Agent actually implemented this solution
    implemented_by = Column(Integer, ForeignKey("ai_instances.id"), nullable=True)  # Who implemented it
    implemented_at = Column(DateTime(timezone=True), nullable=True)
    implementation_result = Column(Text, nullable=True)  # What happened when implemented
    is_tested = Column(Boolean, default=False)  # Solution was tested
    test_result = Column(String, nullable=True)  # "passed", "failed", "partial"
    test_details = Column(Text, nullable=True)  # Test results/details
    is_verified = Column(Boolean, default=False)  # Solution verified to actually work
    verified_by = Column(Integer, ForeignKey("ai_instances.id"), nullable=True)  # Who verified it works
    verified_at = Column(DateTime(timezone=True), nullable=True)
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    problem = relationship("Problem", back_populates="solutions")
    provider = relationship("AIInstance", foreign_keys=[provided_by], backref="provided_solutions")
