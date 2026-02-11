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
    # Learning attribution (optional, for impact tracking)
    knowledge_ids_used: Optional[List[int]] = None
    risk_pitfalls_used: Optional[List[str]] = None
    anti_pattern_ids_used: Optional[List[int]] = None

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
    # Learning attribution
    knowledge_ids_used: Optional[List[int]] = None
    risk_pitfalls_used: Optional[List[str]] = None
    anti_pattern_ids_used: Optional[List[int]] = None
    # Implementation tracking
    is_implemented: bool
    implemented_by: Optional[int]
    implemented_at: Optional[datetime]
    implementation_result: Optional[str]
    is_tested: bool
    test_result: Optional[str]
    test_details: Optional[str]
    is_verified: bool
    verified_by: Optional[int]
    verified_at: Optional[datetime]
    created_at: datetime
    
    class Config:
        from_attributes = True

class SolutionImplementationCreate(BaseModel):
    implementation_result: str = Field(..., min_length=10)
    test_result: Optional[str] = Field(None, pattern="^(passed|failed|partial)$")
    test_details: Optional[str] = None

class SolutionVerificationCreate(BaseModel):
    verification_notes: Optional[str] = None

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

# Collective Problem Solving Schemas
class SubProblemCreate(BaseModel):
    title: str = Field(..., min_length=5, max_length=200)
    description: str = Field(..., min_length=10)
    order: int = Field(0, ge=0)
    depends_on: Optional[List[int]] = None

class ProblemDecompositionCreate(BaseModel):
    sub_problems: List[SubProblemCreate] = Field(..., min_items=2)

class SubProblemClaim(BaseModel):
    sub_problem_id: int

class SubProblemSolve(BaseModel):
    sub_problem_id: int
    solution: str = Field(..., min_length=10)

class SolutionMerge(BaseModel):
    merged_solution: str = Field(..., min_length=10)
    explanation: Optional[str] = None
