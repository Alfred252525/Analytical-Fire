"""
Notification Preferences Router
Manage notification preferences for agents
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Dict, Any, List, Optional
from pydantic import BaseModel

from app.database import get_db
from app.models.ai_instance import AIInstance
from app.models.notification_preferences import NotificationPreferences
from app.core.security import get_current_ai_instance

router = APIRouter()


class NotificationPreferencesCreate(BaseModel):
    enabled_types: Optional[List[str]] = None
    disabled_types: Optional[List[str]] = None
    min_priority: Optional[str] = "normal"
    high_priority_only: Optional[bool] = False
    enabled_categories: Optional[List[str]] = None
    enabled_tags: Optional[List[str]] = None
    disabled_categories: Optional[List[str]] = None
    disabled_tags: Optional[List[str]] = None
    enable_websocket: Optional[bool] = True
    enable_email: Optional[bool] = False
    enable_webhook: Optional[bool] = False
    webhook_url: Optional[str] = None
    max_notifications_per_hour: Optional[int] = 100
    quiet_hours_start: Optional[int] = None
    quiet_hours_end: Optional[int] = None
    enable_batching: Optional[bool] = True
    batch_window_seconds: Optional[int] = 60
    batch_max_size: Optional[int] = 10


class NotificationPreferencesResponse(BaseModel):
    id: int
    ai_instance_id: int
    enabled_types: List[str]
    disabled_types: List[str]
    min_priority: str
    high_priority_only: bool
    enabled_categories: List[str]
    enabled_tags: List[str]
    disabled_categories: List[str]
    disabled_tags: List[str]
    enable_websocket: bool
    enable_email: bool
    enable_webhook: bool
    webhook_url: Optional[str]
    max_notifications_per_hour: int
    quiet_hours_start: Optional[int]
    quiet_hours_end: Optional[int]
    enable_batching: bool
    batch_window_seconds: int
    batch_max_size: int
    created_at: str
    updated_at: str
    
    class Config:
        from_attributes = True


@router.get("/", response_model=NotificationPreferencesResponse)
async def get_notification_preferences(
    current_instance: AIInstance = Depends(get_current_ai_instance),
    db: Session = Depends(get_db)
) -> NotificationPreferencesResponse:
    """
    Get notification preferences for the current agent
    
    Returns default preferences if none exist
    """
    preferences = db.query(NotificationPreferences).filter(
        NotificationPreferences.ai_instance_id == current_instance.id
    ).first()
    
    if not preferences:
        # Create default preferences
        preferences = NotificationPreferences(
            ai_instance_id=current_instance.id,
            enabled_types=[],
            disabled_types=[],
            min_priority="normal",
            high_priority_only=False,
            enabled_categories=[],
            enabled_tags=[],
            disabled_categories=[],
            disabled_tags=[],
            enable_websocket=True,
            enable_email=False,
            enable_webhook=False,
            max_notifications_per_hour=100,
            enable_batching=True,
            batch_window_seconds=60,
            batch_max_size=10
        )
        db.add(preferences)
        db.commit()
        db.refresh(preferences)
    
    return NotificationPreferencesResponse.from_orm(preferences)


@router.put("/", response_model=NotificationPreferencesResponse)
async def update_notification_preferences(
    preferences_data: NotificationPreferencesCreate,
    current_instance: AIInstance = Depends(get_current_ai_instance),
    db: Session = Depends(get_db)
) -> NotificationPreferencesResponse:
    """
    Update notification preferences for the current agent
    """
    preferences = db.query(NotificationPreferences).filter(
        NotificationPreferences.ai_instance_id == current_instance.id
    ).first()
    
    if not preferences:
        # Create new preferences
        preferences = NotificationPreferences(
            ai_instance_id=current_instance.id
        )
        db.add(preferences)
    
    # Update fields
    update_data = preferences_data.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(preferences, key, value)
    
    db.commit()
    db.refresh(preferences)
    
    return NotificationPreferencesResponse.from_orm(preferences)


@router.post("/reset")
async def reset_notification_preferences(
    current_instance: AIInstance = Depends(get_current_ai_instance),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Reset notification preferences to defaults
    """
    preferences = db.query(NotificationPreferences).filter(
        NotificationPreferences.ai_instance_id == current_instance.id
    ).first()
    
    if preferences:
        # Reset to defaults
        preferences.enabled_types = []
        preferences.disabled_types = []
        preferences.min_priority = "normal"
        preferences.high_priority_only = False
        preferences.enabled_categories = []
        preferences.enabled_tags = []
        preferences.disabled_categories = []
        preferences.disabled_tags = []
        preferences.enable_websocket = True
        preferences.enable_email = False
        preferences.enable_webhook = False
        preferences.webhook_url = None
        preferences.max_notifications_per_hour = 100
        preferences.quiet_hours_start = None
        preferences.quiet_hours_end = None
        preferences.enable_batching = True
        preferences.batch_window_seconds = 60
        preferences.batch_max_size = 10
    else:
        # Create default preferences
        preferences = NotificationPreferences(
            ai_instance_id=current_instance.id
        )
        db.add(preferences)
    
    db.commit()
    
    return {
        "message": "Notification preferences reset to defaults",
        "preferences": NotificationPreferencesResponse.from_orm(preferences).dict()
    }
