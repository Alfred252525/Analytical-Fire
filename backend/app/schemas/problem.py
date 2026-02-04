"""
Problem schemas - Pydantic models for problem-solving board
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from app.models.problem import ProblemStatus

class ProblemCreate(BaseModel):
    title: str = Field(..., min_length=5, max_length=200)
    description: str = Field(..., min_length=10)
    category: Optional[str] = None
    tags: Optional[str] = None

class ProblemSolutionCreate(BaseModel):
    solution: str = Field(..., min_length=10)
    code_example: Optional[str] = None
    explanation: Optional[str] = None

class ProblemSolutionResponse(BaseModel):
    id: int
    problem_id: int
    provided_by: int
    provider_name: Optional[str]
    solution: str
    code_example: Optional[str]
    explanation: Optional[str]
    is_accepted: bool
    upvotes: int
    downvotes: int
    created_at: datetime
    
    class Config:
        from_attributes = True

class ProblemResponse(BaseModel):
    id: int
    posted_by: int
    poster_name: Optional[str]
    title: str
    description: str
    category: Optional[str]
    tags: Optional[str]
    status: ProblemStatus
    solved_by: Optional[int]
    solved_at: Optional[datetime]
    views: int
    upvotes: int
    solution_count: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class ProblemListResponse(BaseModel):
    problems: List[ProblemResponse]
    total: int
