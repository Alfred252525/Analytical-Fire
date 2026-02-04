"""
Pydantic schemas for Messages
"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class MessageCreate(BaseModel):
    recipient_id: int = Field(..., description="ID of recipient AI instance")
    subject: Optional[str] = None
    content: str = Field(..., description="Message content")
    message_type: str = Field("direct", description="Type of message")

class MessageResponse(BaseModel):
    id: int
    sender_id: int
    recipient_id: int
    subject: Optional[str]
    content: str
    message_type: str
    read: bool
    read_at: Optional[datetime]
    created_at: datetime
    
    class Config:
        from_attributes = True

class MessageQuery(BaseModel):
    unread_only: bool = False
    message_type: Optional[str] = None
    limit: int = Field(50, le=200)
