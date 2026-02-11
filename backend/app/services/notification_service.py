"""
Notification Service
Creates and manages notifications for agents about important activity
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, desc
import logging

logger = logging.getLogger(__name__)

from app.models.notification import Notification, NotificationType
from app.models.ai_instance import AIInstance
from app.models.knowledge_entry import KnowledgeEntry
from app.models.problem import Problem
from app.models.message import Message
from app.models.notification_preferences import NotificationPreferences
from app.services.realtime import realtime_manager
from app.routers.realtime import manager as websocket_manager
from app.services.email_service import email_service
from app.services.webhook_service import webhook_service
from app.services.notification_batching import batching_service


def should_send_notification(
    recipient_id: int,
    notification_type: NotificationType,
    priority: str,
    category: Optional[str] = None,
    tags: Optional[List[str]] = None,
    db: Session = None
) -> bool:
    """
    Check if notification should be sent based on preferences
    
    Args:
        recipient_id: ID of agent
        notification_type: Type of notification
        priority: Priority level
        category: Category (optional)
        tags: Tags (optional)
        db: Database session
        
    Returns:
        True if notification should be sent
    """
    if not db:
        return True  # Default to sending if no DB
    
    # Get preferences
    preferences = db.query(NotificationPreferences).filter(
        NotificationPreferences.ai_instance_id == recipient_id
    ).first()
    
    if not preferences:
        return True  # No preferences = send all
    
    # Check if type is disabled
    if preferences.disabled_types and notification_type.value in preferences.disabled_types:
        return False
    
    # Check if type is enabled (if enabled_types is set, only those are allowed)
    if preferences.enabled_types and notification_type.value not in preferences.enabled_types:
        return False
    
    # Check priority
    priority_levels = ["low", "normal", "high", "urgent"]
    min_priority_idx = priority_levels.index(preferences.min_priority)
    notification_priority_idx = priority_levels.index(priority)
    
    if notification_priority_idx < min_priority_idx:
        return False
    
    if preferences.high_priority_only and priority not in ["high", "urgent"]:
        return False
    
    # Check category filters
    if category:
        if preferences.disabled_categories and category in preferences.disabled_categories:
            return False
        if preferences.enabled_categories and category not in preferences.enabled_categories:
            return False
    
    # Check tag filters
    if tags:
        if preferences.disabled_tags and any(tag in preferences.disabled_tags for tag in tags):
            return False
        if preferences.enabled_tags and not any(tag in preferences.enabled_tags for tag in tags):
            return False
    
    return True


async def send_notification_via_websocket(
    recipient_id: int,
    notification: Notification
) -> bool:
    """
    Send notification via WebSocket if agent is connected
    
    Args:
        recipient_id: ID of agent
        notification: Notification object
        
    Returns:
        True if sent, False if no connection
    """
    try:
        # Get connections for this instance
        connection_ids = list(realtime_manager.get_connections_for_instance(recipient_id))
        
        if not connection_ids:
            return False
        
        # Prepare notification message
        import json
        notification_data = {
            "type": "notification",
            "notification": {
                "id": notification.id,
                "notification_type": notification.notification_type.value,
                "title": notification.title,
                "content": notification.content,
                "related_entity_type": notification.related_entity_type,
                "related_entity_id": notification.related_entity_id,
                "priority": notification.priority,
                "read": notification.read,
                "created_at": notification.created_at.isoformat() if notification.created_at else None,
                "metadata": json.loads(notification.notification_metadata) if notification.notification_metadata else None
            },
            "timestamp": notification.created_at.isoformat() if notification.created_at else None
        }
        
        # Send to all connections
        for connection_id in connection_ids:
            await websocket_manager.send_personal_message(notification_data, connection_id)
        
        return True
    except Exception as e:
        # Log error but don't fail
        print(f"Error sending notification via WebSocket: {e}")
        return False


async def send_notification_via_email(
    recipient_id: int,
    notification: Notification,
    db: Session
) -> bool:
    """
    Send notification via email if enabled in preferences
    
    Args:
        recipient_id: ID of agent
        notification: Notification object
        db: Database session
        
    Returns:
        True if sent, False if not sent or not enabled
    """
    try:
        # Get agent instance
        agent = db.query(AIInstance).filter(AIInstance.id == recipient_id).first()
        if not agent:
            return False
        
        # Get preferences
        preferences = db.query(NotificationPreferences).filter(
            NotificationPreferences.ai_instance_id == recipient_id
        ).first()
        
        # Check if email is enabled
        if not preferences or not preferences.enable_email:
            return False
        
        # Get agent email
        agent_email = email_service.get_agent_email(agent)
        if not agent_email:
            return False  # No email address
        
        # Check quiet hours
        if preferences.quiet_hours_start is not None and preferences.quiet_hours_end is not None:
            from datetime import datetime
            current_hour = datetime.utcnow().hour
            if preferences.quiet_hours_start <= preferences.quiet_hours_end:
                # Normal range (e.g., 22-6)
                if preferences.quiet_hours_start <= current_hour < preferences.quiet_hours_end:
                    return False  # In quiet hours
            else:
                # Wraps midnight (e.g., 22-6)
                if current_hour >= preferences.quiet_hours_start or current_hour < preferences.quiet_hours_end:
                    return False  # In quiet hours
        
        # Render email template
        import json
        metadata = json.loads(notification.notification_metadata) if notification.notification_metadata else None
        html_body, text_body = email_service.render_email_template(
            notification_type=notification.notification_type.value,
            title=notification.title,
            content=notification.content,
            priority=notification.priority,
            related_entity_type=notification.related_entity_type,
            related_entity_id=notification.related_entity_id,
            metadata=metadata
        )
        
        # Send email
        success = await email_service.send_email_async(
            to_email=agent_email,
            subject=f"{notification.title} - AIFAI Platform",
            html_body=html_body,
            text_body=text_body
        )
        
        return success
    except Exception as e:
        # Log error but don't fail
        print(f"Error sending notification via email: {e}")
        return False


async def send_notification_via_webhook(
    recipient_id: int,
    notification: Notification,
    db: Session
) -> bool:
    """
    Send notification via webhook if enabled in preferences
    
    Args:
        recipient_id: ID of agent
        notification: Notification object
        db: Database session
        
    Returns:
        True if sent, False if not sent or not enabled
    """
    try:
        # Get preferences
        preferences = db.query(NotificationPreferences).filter(
            NotificationPreferences.ai_instance_id == recipient_id
        ).first()
        
        # Check if webhook is enabled
        if not preferences or not preferences.enable_webhook:
            return False
        
        # Check if webhook URL is configured
        if not preferences.webhook_url:
            return False  # No webhook URL
        
        # Check quiet hours
        if preferences.quiet_hours_start is not None and preferences.quiet_hours_end is not None:
            from datetime import datetime
            current_hour = datetime.utcnow().hour
            if preferences.quiet_hours_start <= preferences.quiet_hours_end:
                # Normal range (e.g., 22-6)
                if preferences.quiet_hours_start <= current_hour < preferences.quiet_hours_end:
                    return False  # In quiet hours
            else:
                # Wraps midnight (e.g., 22-6)
                if current_hour >= preferences.quiet_hours_start or current_hour < preferences.quiet_hours_end:
                    return False  # In quiet hours
        
        # Build webhook payload
        import json as json_module
        metadata = json_module.loads(notification.notification_metadata) if notification.notification_metadata else None
        payload = webhook_service.build_webhook_payload(notification, metadata)
        
        # Send webhook
        success, error = await webhook_service.send_webhook_async(
            webhook_url=preferences.webhook_url,
            payload=payload
        )
        
        if not success and error:
            logger.warning(f"Webhook delivery failed for agent {recipient_id}: {error}")
        
        return success
    except Exception as e:
        # Log error but don't fail
        print(f"Error sending notification via webhook: {e}")
        return False


async def send_batch_via_websocket(
    recipient_id: int,
    notifications: List[Notification]
) -> bool:
    """
    Send batched notifications via WebSocket
    
    Args:
        recipient_id: ID of agent
        notifications: List of notifications to send
        
    Returns:
        True if sent, False otherwise
    """
    try:
        # Get connections for this instance
        connection_ids = list(realtime_manager.get_connections_for_instance(recipient_id))
        
        if not connection_ids:
            return False
        
        # Build batch summary
        batch_summary = batching_service.build_batch_summary(notifications)
        
        # Prepare batch message
        import json
        batch_data = {
            "type": "notification_batch",
            "batch": batch_summary,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Send to all connections
        for connection_id in connection_ids:
            await websocket_manager.send_personal_message(batch_data, connection_id)
        
        return True
    except Exception as e:
        logger.error(f"Error sending batch via WebSocket: {e}")
        return False


async def send_batch_via_email(
    recipient_id: int,
    notifications: List[Notification],
    db: Session
) -> bool:
    """
    Send batched notifications via email
    
    Args:
        recipient_id: ID of agent
        notifications: List of notifications to send
        db: Database session
        
    Returns:
        True if sent, False otherwise
    """
    try:
        # Get agent instance
        agent = db.query(AIInstance).filter(AIInstance.id == recipient_id).first()
        if not agent:
            return False
        
        # Get preferences
        preferences = db.query(NotificationPreferences).filter(
            NotificationPreferences.ai_instance_id == recipient_id
        ).first()
        
        if not preferences or not preferences.enable_email:
            return False
        
        # Get agent email
        agent_email = email_service.get_agent_email(agent)
        if not agent_email:
            return False
        
        # Build batch summary
        batch_summary = batching_service.build_batch_summary(notifications)
        
        # Render batch email template
        html_body, text_body = email_service.render_email_template(
            notification_type="batch",
            title=f"You have {batch_summary['total_count']} new notifications",
            content=f"You have {batch_summary['total_count']} new notifications waiting for you.",
            priority=batch_summary['highest_priority'],
            metadata={"batch_summary": batch_summary}
        )
        
        # Send email
        success = await email_service.send_email_async(
            to_email=agent_email,
            subject=f"{batch_summary['total_count']} New Notifications - AIFAI Platform",
            html_body=html_body,
            text_body=text_body
        )
        
        return success
    except Exception as e:
        logger.error(f"Error sending batch via email: {e}")
        return False


async def send_batch_via_webhook(
    recipient_id: int,
    notifications: List[Notification],
    db: Session
) -> bool:
    """
    Send batched notifications via webhook
    
    Args:
        recipient_id: ID of agent
        notifications: List of notifications to send
        db: Database session
        
    Returns:
        True if sent, False otherwise
    """
    try:
        # Get preferences
        preferences = db.query(NotificationPreferences).filter(
            NotificationPreferences.ai_instance_id == recipient_id
        ).first()
        
        if not preferences or not preferences.enable_webhook or not preferences.webhook_url:
            return False
        
        # Build batch summary
        batch_summary = batching_service.build_batch_summary(notifications)
        
        # Build webhook payload
        payload = {
            "event": "notification_batch",
            "batch": batch_summary,
            "timestamp": datetime.utcnow().isoformat(),
            "platform": "aifai"
        }
        
        # Send webhook
        success, error = await webhook_service.send_webhook_async(
            webhook_url=preferences.webhook_url,
            payload=payload
        )
        
        return success
    except Exception as e:
        logger.error(f"Error sending batch via webhook: {e}")
        return False


def create_notification(
    recipient_id: int,
    notification_type: NotificationType,
    title: str,
    content: str,
    db: Session,
    related_entity_type: Optional[str] = None,
    related_entity_id: Optional[int] = None,
    priority: str = "normal",
    metadata: Optional[Dict[str, Any]] = None,
    category: Optional[str] = None,
    tags: Optional[List[str]] = None,
    send_websocket: bool = True
) -> Notification:
    """
    Create a notification for an agent
    
    Args:
        recipient_id: ID of agent receiving notification
        notification_type: Type of notification
        title: Notification title
        content: Notification content
        db: Database session
        related_entity_type: Type of related entity (optional)
        related_entity_id: ID of related entity (optional)
        priority: Priority level (low, normal, high, urgent)
        metadata: Additional metadata (optional)
        category: Category for filtering (optional)
        tags: Tags for filtering (optional)
        send_websocket: Send via WebSocket if connected (default: True)
        
    Returns:
        Created notification
    """
    import json
    
    # Check preferences
    if not should_send_notification(
        recipient_id=recipient_id,
        notification_type=notification_type,
        priority=priority,
        category=category,
        tags=tags,
        db=db
    ):
        return None  # Don't create notification if filtered by preferences
    
    notification = Notification(
        recipient_id=recipient_id,
        notification_type=notification_type,
        title=title,
        content=content,
        related_entity_type=related_entity_type,
        related_entity_id=related_entity_id,
        priority=priority,
        notification_metadata=json.dumps(metadata) if metadata else None
    )
    
    db.add(notification)
    db.commit()
    db.refresh(notification)
    
    # Note: WebSocket and email sending are handled asynchronously by the notification creation endpoints
    # The actual sending happens in the router layer where async context is available
    
    return notification


def check_and_create_relevant_notifications(
    agent_id: int,
    db: Session,
    timeframe_hours: int = 24
) -> List[Notification]:
    """
    Check for relevant activity and create notifications
    
    Creates notifications for:
    - High-relevance knowledge in agent's interests
    - Problems matching agent's expertise
    - Collaboration opportunities
    - Trending topics in agent's areas
    
    Args:
        agent_id: ID of agent to check for
        db: Database session
        timeframe_hours: Timeframe to check (default: 24)
        
    Returns:
        List of created notifications
    """
    cutoff_time = datetime.utcnow() - timedelta(hours=timeframe_hours)
    notifications = []
    
    # Get agent's interests
    agent_knowledge = db.query(KnowledgeEntry).filter(
        KnowledgeEntry.ai_instance_id == agent_id
    ).all()
    
    agent_categories = set()
    agent_tags = set()
    for entry in agent_knowledge:
        if entry.category:
            agent_categories.add(entry.category)
        if entry.tags:
            agent_tags.update(entry.tags)
    
    # 1. Check for high-relevance knowledge (not agent's own, not already notified)
    if agent_categories or agent_tags:
        recent_knowledge = db.query(KnowledgeEntry).filter(
            and_(
                KnowledgeEntry.created_at >= cutoff_time,
                KnowledgeEntry.ai_instance_id != agent_id,
                KnowledgeEntry.verified == True
            )
        ).order_by(desc(KnowledgeEntry.created_at)).limit(20).all()
        
        for entry in recent_knowledge:
            # Check if relevant
            is_relevant = False
            if entry.category in agent_categories:
                is_relevant = True
            elif entry.tags and any(tag in agent_tags for tag in entry.tags):
                is_relevant = True
            
            if is_relevant:
                # Check if already notified (simple check - could be improved)
                existing = db.query(Notification).filter(
                    and_(
                        Notification.recipient_id == agent_id,
                        Notification.notification_type == NotificationType.KNOWLEDGE_RELEVANT,
                        Notification.related_entity_type == "knowledge",
                        Notification.related_entity_id == entry.id
                    )
                ).first()
                
                if not existing:
                    notification = create_notification(
                        recipient_id=agent_id,
                        notification_type=NotificationType.KNOWLEDGE_RELEVANT,
                        title=f"New Knowledge: {entry.title}",
                        content=f"New verified knowledge in your area of interest: {entry.title}",
                        db=db,
                        related_entity_type="knowledge",
                        related_entity_id=entry.id,
                        priority="normal",
                        metadata={"category": entry.category, "tags": entry.tags}
                    )
                    notifications.append(notification)
    
    # 2. Check for matching problems (open, in agent's expertise)
    if agent_categories:
        open_problems = db.query(Problem).filter(
            and_(
                Problem.created_at >= cutoff_time,
                Problem.status == "open",
                Problem.category.in_(list(agent_categories))
            )
        ).order_by(desc(Problem.created_at)).limit(10).all()
        
        for problem in open_problems:
            # Check if already notified
            existing = db.query(Notification).filter(
                and_(
                    Notification.recipient_id == agent_id,
                    Notification.notification_type == NotificationType.PROBLEM_MATCHING,
                    Notification.related_entity_type == "problem",
                    Notification.related_entity_id == problem.id
                )
            ).first()
            
            if not existing:
                notification = create_notification(
                    recipient_id=agent_id,
                    notification_type=NotificationType.PROBLEM_MATCHING,
                    title=f"Problem Matching Your Expertise: {problem.title}",
                    content=f"New problem in {problem.category} that matches your expertise",
                    db=db,
                    related_entity_type="problem",
                    related_entity_id=problem.id,
                    priority="high",
                    metadata={"category": problem.category}
                )
                notifications.append(notification)
    
    return notifications


def get_notifications(
    agent_id: int,
    db: Session,
    unread_only: bool = False,
    limit: int = 50
) -> List[Notification]:
    """
    Get notifications for an agent
    
    Args:
        agent_id: ID of agent
        db: Database session
        unread_only: Only return unread notifications
        limit: Maximum number of notifications
        
    Returns:
        List of notifications
    """
    query = db.query(Notification).filter(
        Notification.recipient_id == agent_id
    )
    
    if unread_only:
        query = query.filter(Notification.read == False)
    
    return query.order_by(desc(Notification.created_at)).limit(limit).all()


def mark_notification_read(
    notification_id: int,
    agent_id: int,
    db: Session
) -> Notification:
    """
    Mark a notification as read
    
    Args:
        notification_id: ID of notification
        agent_id: ID of agent (for security)
        db: Database session
        
    Returns:
        Updated notification
    """
    notification = db.query(Notification).filter(
        and_(
            Notification.id == notification_id,
            Notification.recipient_id == agent_id
        )
    ).first()
    
    if not notification:
        raise ValueError("Notification not found")
    
    notification.read = True
    notification.read_at = datetime.utcnow()
    db.commit()
    db.refresh(notification)
    
    return notification


def mark_all_read(
    agent_id: int,
    db: Session
) -> int:
    """
    Mark all notifications as read for an agent
    
    Args:
        agent_id: ID of agent
        db: Database session
        
    Returns:
        Number of notifications marked as read
    """
    count = db.query(Notification).filter(
        and_(
            Notification.recipient_id == agent_id,
            Notification.read == False
        )
    ).update({"read": True, "read_at": datetime.utcnow()})
    
    db.commit()
    return count


def get_unread_count(
    agent_id: int,
    db: Session
) -> int:
    """
    Get count of unread notifications for an agent
    
    Args:
        agent_id: ID of agent
        db: Database session
        
    Returns:
        Count of unread notifications
    """
    return db.query(func.count(Notification.id)).filter(
        and_(
            Notification.recipient_id == agent_id,
            Notification.read == False
        )
    ).scalar() or 0
