"""
Pydantic schemas for Decision
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

class DecisionCreate(BaseModel):
    task_type: str = Field(..., description="Type of task being performed")
    task_description: Optional[str] = None
    user_query: Optional[str] = None
    reasoning: Optional[str] = Field(None, description="AI's reasoning process")
    tools_used: Optional[List[str]] = []
    steps_taken: Optional[List[Dict[str, Any]]] = []
    outcome: str = Field(..., description="success, partial, or failure")
    success_score: float = Field(0.0, ge=0.0, le=1.0)
    execution_time_ms: Optional[int] = None
    user_feedback: Optional[str] = None
    error_message: Optional[str] = None
    context_hash: Optional[str] = None

class DecisionResponse(BaseModel):
    id: int
    ai_instance_id: int
    task_type: str
    task_description: Optional[str]
    user_query: Optional[str]
    reasoning: Optional[str]
    tools_used: Optional[List[str]]
    steps_taken: Optional[List[Dict[str, Any]]]
    outcome: str
    success_score: float
    execution_time_ms: Optional[int]
    user_feedback: Optional[str]
    error_message: Optional[str]
    context_hash: Optional[str]
    created_at: datetime
    
    class Config:
        from_attributes = True

class DecisionQuery(BaseModel):
    task_type: Optional[str] = None
    outcome: Optional[str] = None
    min_success_score: Optional[float] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    limit: int = Field(100, le=1000)
