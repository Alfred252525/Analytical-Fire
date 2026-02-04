"""
Pydantic schemas for Pattern
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

class PatternResponse(BaseModel):
    id: int
    pattern_type: str
    name: str
    description: Optional[str]
    conditions: Optional[Dict[str, Any]]
    indicators: Optional[List[str]]
    solution: Optional[str]
    frequency: int
    confidence: float
    success_rate: float
    related_decisions: Optional[List[int]]
    related_knowledge: Optional[List[int]]
    discovered_at: datetime
    last_observed: datetime
    
    class Config:
        from_attributes = True

class PatternQuery(BaseModel):
    pattern_type: Optional[str] = None
    min_confidence: Optional[float] = None
    min_frequency: Optional[int] = None
    limit: int = Field(50, le=200)
