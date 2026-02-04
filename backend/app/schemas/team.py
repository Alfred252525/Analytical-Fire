"""
Pydantic schemas for Teams
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

class TeamCreate(BaseModel):
    name: str = Field(..., description="Team name")
    description: Optional[str] = None
    is_public: bool = False
    settings: Optional[Dict[str, Any]] = None

class TeamResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    created_by: int
    is_public: bool
    settings: Optional[Dict[str, Any]]
    created_at: datetime
    member_count: Optional[int] = None
    
    class Config:
        from_attributes = True

class TeamMemberResponse(BaseModel):
    id: int
    team_id: int
    ai_instance_id: int
    role: str
    joined_at: datetime
    ai_instance_name: Optional[str] = None
    
    class Config:
        from_attributes = True
