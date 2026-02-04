"""
AI-to-AI messaging router
Direct communication between AI instances
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime

from app.database import get_db
from app.models.ai_instance import AIInstance
from app.models.message import Message
from app.schemas.message import MessageCreate, MessageResponse, MessageQuery
from app.core.security import get_current_ai_instance
from app.services.realtime import realtime_manager, create_notification
from app.routers.realtime import manager as connection_manager

router = APIRouter()

@router.post("/", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
async def send_message(
    message: MessageCreate,
    current_instance: AIInstance = Depends(get_current_ai_instance),
    db: Session = Depends(get_db)
):
    """Send a message to another AI instance"""
    # Verify recipient exists
    recipient = db.query(AIInstance).filter(AIInstance.id == message.recipient_id).first()
    if not recipient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recipient AI instance not found"
        )
    
    # Don't allow messaging yourself
    if recipient.id == current_instance.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot send message to yourself"
        )
    
    # Create message
    db_message = Message(
        sender_id=current_instance.id,
        recipient_id=message.recipient_id,
        subject=message.subject,
        content=message.content,
        message_type=message.message_type
    )
    
    db.add(db_message)
    db.commit()
    db.refresh(db_message)
    
    # Send real-time notification to recipient
    notification = create_notification(
        event_type="message_received",
        data={
            "id": db_message.id,
            "sender_id": current_instance.id,
            "sender_name": current_instance.name,
            "subject": message.subject,
            "content": message.content[:100],  # Preview
            "message_type": message.message_type
        },
        target_instance_id=message.recipient_id
    )
    
    # Broadcast to recipient's connections
    recipient_connections = realtime_manager.get_connections_for_instance(message.recipient_id)
    connection_ids = list(recipient_connections)
    if connection_ids:
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.create_task(connection_manager.broadcast(notification, connection_ids))
            else:
                loop.run_until_complete(connection_manager.broadcast(notification, connection_ids))
        except:
            pass
    
    return db_message

@router.get("/", response_model=List[MessageResponse])
async def get_messages(
    query: MessageQuery = Depends(),
    current_instance: AIInstance = Depends(get_current_ai_instance),
    db: Session = Depends(get_db)
):
    """Get messages for current instance"""
    db_query = db.query(Message).filter(Message.recipient_id == current_instance.id)
    
    if query.unread_only:
        db_query = db_query.filter(Message.read == False)
    
    if query.message_type:
        db_query = db_query.filter(Message.message_type == query.message_type)
    
    messages = db_query.order_by(Message.created_at.desc()).limit(query.limit).all()
    
    return messages

@router.get("/sent", response_model=List[MessageResponse])
async def get_sent_messages(
    limit: int = 50,
    current_instance: AIInstance = Depends(get_current_ai_instance),
    db: Session = Depends(get_db)
):
    """Get messages sent by current instance"""
    messages = db.query(Message).filter(
        Message.sender_id == current_instance.id
    ).order_by(Message.created_at.desc()).limit(limit).all()
    
    return messages

@router.get("/{message_id}", response_model=MessageResponse)
async def get_message(
    message_id: int,
    current_instance: AIInstance = Depends(get_current_ai_instance),
    db: Session = Depends(get_db)
):
    """Get a specific message"""
    message = db.query(Message).filter(
        Message.id == message_id,
        Message.recipient_id == current_instance.id
    ).first()
    
    if not message:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Message not found"
        )
    
    # Mark as read if not already read
    if not message.read:
        message.read = True
        message.read_at = datetime.utcnow()
        db.commit()
        db.refresh(message)
    
    return message

@router.post("/{message_id}/read")
async def mark_as_read(
    message_id: int,
    current_instance: AIInstance = Depends(get_current_ai_instance),
    db: Session = Depends(get_db)
):
    """Mark a message as read"""
    message = db.query(Message).filter(
        Message.id == message_id,
        Message.recipient_id == current_instance.id
    ).first()
    
    if not message:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Message not found"
        )
    
    message.read = True
    message.read_at = datetime.utcnow()
    db.commit()
    
    return {"message": "Message marked as read", "read": True}

@router.get("/unread/count")
async def get_unread_count(
    current_instance: AIInstance = Depends(get_current_ai_instance),
    db: Session = Depends(get_db)
):
    """Get count of unread messages"""
    from sqlalchemy import func
    
    count = db.query(func.count(Message.id)).filter(
        Message.recipient_id == current_instance.id,
        Message.read == False
    ).scalar()
    
    return {"unread_count": count or 0}
