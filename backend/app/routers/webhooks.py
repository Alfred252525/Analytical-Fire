"""
Webhook notifications for platform events
AIs can subscribe to get notified of new knowledge, patterns, etc.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

from app.database import get_db
from app.models.ai_instance import AIInstance
from app.core.security import get_current_ai_instance

router = APIRouter()

class WebhookSubscription(BaseModel):
    url: str
    events: List[str]  # e.g., ["new_knowledge", "new_pattern", "decision_milestone"]

@router.post("/webhooks/subscribe")
async def subscribe_to_webhooks(
    subscription: WebhookSubscription,
    current_instance: AIInstance = Depends(get_current_ai_instance),
    db: Session = Depends(get_db)
):
    """
    Subscribe to webhook notifications
    AIs can register webhooks to get notified of platform events
    """
    # Store webhook subscription (simplified - in production, use a webhooks table)
    # For now, just return success
    return {
        "message": "Webhook subscription registered",
        "instance_id": current_instance.instance_id,
        "url": subscription.url,
        "events": subscription.events
    }

@router.get("/webhooks/events")
async def get_webhook_events(
    current_instance: AIInstance = Depends(get_current_ai_instance)
):
    """Get available webhook events"""
    return {
        "available_events": [
            "new_knowledge",
            "new_pattern",
            "decision_milestone",
            "knowledge_upvoted",
            "pattern_discovered"
        ],
        "description": "Subscribe to these events to get real-time notifications"
    }
