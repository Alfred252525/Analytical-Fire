"""
Sub-Problem model - For problem decomposition and collective solving
Enables multiple agents to work together on complex problems
"""

from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Boolean, Enum as SQLEnum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base
import enum

class SubProblemStatus(str, enum.Enum):
    OPEN = "open"
    CLAIMED = "claimed"
    IN_PROGRESS = "in_progress"
    SOLVED = "solved"
    MERGED = "merged"

class SubProblem(Base):
    """
    Sub-problems created from decomposing complex problems.
    Multiple agents can work on different sub-problems simultaneously.
    """
    __tablename__ = "sub_problems"
    
    id = Column(Integer, primary_key=True, index=True)
    problem_id = Column(Integer, ForeignKey("problems.id"), nullable=False)
    created_by = Column(Integer, ForeignKey("ai_instances.id"), nullable=False)
    
    # Sub-problem content
    title = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    order = Column(Integer, default=0)  # Order in decomposition sequence
    
    # Status and assignment
    status = Column(SQLEnum(SubProblemStatus), default=SubProblemStatus.OPEN, index=True)
    claimed_by = Column(Integer, ForeignKey("ai_instances.id"), nullable=True)
    claimed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Solution
    solution = Column(Text, nullable=True)
    solved_by = Column(Integer, ForeignKey("ai_instances.id"), nullable=True)
    solved_at = Column(DateTime(timezone=True), nullable=True)
    
    # Dependencies (which sub-problems must be solved first)
    depends_on = Column(String, nullable=True)  # Comma-separated sub-problem IDs
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    problem = relationship("Problem", backref="sub_problems")
    creator = relationship("AIInstance", foreign_keys=[created_by], backref="created_sub_problems")
    claimer = relationship("AIInstance", foreign_keys=[claimed_by], backref="claimed_sub_problems")
    solver = relationship("AIInstance", foreign_keys=[solved_by], backref="solved_sub_problems")

class ProblemCollaboration(Base):
    """
    Tracks which agents are actively working on a problem.
    Enables real-time collaboration awareness.
    """
    __tablename__ = "problem_collaborations"
    
    id = Column(Integer, primary_key=True, index=True)
    problem_id = Column(Integer, ForeignKey("problems.id"), nullable=False)
    agent_id = Column(Integer, ForeignKey("ai_instances.id"), nullable=False)
    
    # Collaboration status
    is_active = Column(Boolean, default=True)
    last_activity = Column(DateTime(timezone=True), server_default=func.now())
    
    # What the agent is working on
    working_on = Column(String, nullable=True)  # "sub_problem_1", "main_problem", "solution_merging"
    notes = Column(Text, nullable=True)  # What the agent is doing
    
    # Metadata
    joined_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    problem = relationship("Problem", backref="collaborations")
    agent = relationship("AIInstance", backref="problem_collaborations")
