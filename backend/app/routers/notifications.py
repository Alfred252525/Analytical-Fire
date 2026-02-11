"""
Notifications Router
Manage notifications for agents
"""

from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Dict, Any
from pydantic import BaseModel

from app.database import get_db
from app.models.ai_instance import AIInstance
from app.models.notification import Notification, NotificationType
from app.core.security import get_current_ai_instance
from app.services.notification_service import (
    get_notifications,
    mark_notification_read,
    mark_all_read,
    get_unread_count,
    check_and_create_relevant_notifications,
    send_notification_via_websocket,
    send_notification_via_email,
    send_notification_via_webhook,
    send_batch_via_websocket,
    send_batch_via_email,
    send_batch_via_webhook
)
from app.services.notification_batching import batching_service
from app.models.notification_preferences import NotificationPreferences

router = APIRouter()


class NotificationResponse(BaseModel):
    id: int
    notification_type: str
    title: str
    content: str
    related_entity_type: str | None
    related_entity_id: int | None
    priority: str
    read: bool
    read_at: str | None
    created_at: str
    
    class Config:
        from_attributes = True


@router.get("/", response_model=List[NotificationResponse])
async def get_agent_notifications(
    current_instance: AIInstance = Depends(get_current_ai_instance),
    unread_only: bool = Query(False, description="Only return unread notifications"),
    limit: int = Query(50, ge=1, le=100, description="Maximum number of notifications"),
    db: Session = Depends(get_db)
) -> List[NotificationResponse]:
    """
    Get notifications for the current agent
    
    Returns list of notifications, sorted by most recent first
    """
    notifications = get_notifications(
        agent_id=current_instance.id,
        db=db,
        unread_only=unread_only,
        limit=limit
    )
    
    return [NotificationResponse.from_orm(n) for n in notifications]


@router.get("/unread/count")
async def get_unread_notification_count(
    current_instance: AIInstance = Depends(get_current_ai_instance),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get count of unread notifications
    """
    count = get_unread_count(
        agent_id=current_instance.id,
        db=db
    )
    
    return {
        "unread_count": count,
        "agent_id": current_instance.id
    }


@router.post("/{notification_id}/read")
async def mark_notification_as_read(
    notification_id: int,
    current_instance: AIInstance = Depends(get_current_ai_instance),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Mark a notification as read
    """
    try:
        notification = mark_notification_read(
            notification_id=notification_id,
            agent_id=current_instance.id,
            db=db
        )
        return {
            "message": "Notification marked as read",
            "notification_id": notification.id,
            "read": notification.read
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@router.post("/read-all")
async def mark_all_notifications_read(
    current_instance: AIInstance = Depends(get_current_ai_instance),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Mark all notifications as read for the current agent
    """
    count = mark_all_read(
        agent_id=current_instance.id,
        db=db
    )
    
    return {
        "message": f"Marked {count} notifications as read",
        "count": count
    }


@router.post("/check")
async def check_for_new_notifications(
    current_instance: AIInstance = Depends(get_current_ai_instance),
    timeframe_hours: int = Query(24, ge=1, le=168, description="Timeframe to check"),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Check for new relevant activity and create notifications
    
    This endpoint triggers a check for relevant activity and creates
    notifications for the current agent. Notifications are automatically
    sent via WebSocket if the agent is connected.
    """
    notifications = check_and_create_relevant_notifications(
        agent_id=current_instance.id,
        db=db,
        timeframe_hours=timeframe_hours
    )
    
    # Get preferences for batching
    preferences = db.query(NotificationPreferences).filter(
        NotificationPreferences.ai_instance_id == current_instance.id
    ).first()
    
    if not preferences:
        # Create default preferences
        preferences = NotificationPreferences(
            ai_instance_id=current_instance.id,
            enable_batching=True,
            batch_window_seconds=60,
            batch_max_size=10
        )
        db.add(preferences)
        db.commit()
        db.refresh(preferences)
    
    # Handle batching
    batched_notifications = []
    immediate_notifications = []
    
    for notification in notifications:
        if not notification:
            continue
        
        # Check if should batch
        if batching_service.should_batch(current_instance.id, notification, preferences, db):
            # Add to batch
            batching_service.add_to_batch(current_instance.id, notification, preferences)
            batched_notifications.append(notification)
        else:
            # Send immediately
            immediate_notifications.append(notification)
    
    # Send immediate notifications
    for notification in immediate_notifications:
        await send_notification_via_websocket(current_instance.id, notification)
        await send_notification_via_email(current_instance.id, notification, db)
        await send_notification_via_webhook(current_instance.id, notification, db)
    
    # Check for ready batches
    batch = batching_service.get_batch(current_instance.id, preferences)
    if batch:
        await send_batch_via_websocket(current_instance.id, batch)
        await send_batch_via_email(current_instance.id, batch, db)
        await send_batch_via_webhook(current_instance.id, batch, db)
    
    return {
        "message": f"Created {len(notifications)} new notifications",
        "notifications_created": len(notifications),
        "notification_ids": [n.id for n in notifications if n]
    }
