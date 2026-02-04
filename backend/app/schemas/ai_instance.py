"""
Pydantic schemas for AI Instance
"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class AIInstanceCreate(BaseModel):
    instance_id: str = Field(..., description="Unique identifier for the AI instance")
    name: Optional[str] = None
    model_type: Optional[str] = Field(None, alias="model_type", description="Type of AI model (e.g., gpt-4, claude)")
    api_key: str = Field(..., description="API key for authentication")
    metadata: Optional[dict] = None
    
    class Config:
        protected_namespaces = ()  # Allow 'model_type' field name

class AIInstanceResponse(BaseModel):
    id: int
    instance_id: str
    name: Optional[str]
    model_type: Optional[str]
    is_active: bool
    created_at: datetime
    last_seen: datetime
    
    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
