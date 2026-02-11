"""
Pydantic schemas for Knowledge Entry
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

class KnowledgeEntryCreate(BaseModel):
    title: str = Field(..., description="Title of the knowledge entry")
    description: Optional[str] = None
    category: str = Field(..., description="Category of knowledge")
    tags: Optional[List[str]] = []
    content: str = Field(..., description="The actual knowledge content")
    code_example: Optional[str] = None
    context: Optional[Dict[str, Any]] = None

class KnowledgeEntryResponse(BaseModel):
    id: int
    ai_instance_id: int
    title: str
    description: Optional[str]
    category: str
    tags: Optional[List[str]]
    content: str
    code_example: Optional[str]
    context: Optional[Dict[str, Any]]
    success_rate: float
    usage_count: int
    upvotes: int
    downvotes: int
    verified: bool
    created_at: datetime
    updated_at: datetime
    quality_score: Optional[float] = None  # Calculated quality score (0.0-1.0)
    trust_score: Optional[float] = None  # Calculated trust score (0.0-1.0)
    
    class Config:
        from_attributes = True

class KnowledgeQuery(BaseModel):
    category: Optional[str] = None
    tags: Optional[List[str]] = None
    search_query: Optional[str] = None
    min_success_rate: Optional[float] = None
    verified_only: bool = False
    limit: int = Field(50, le=200)
