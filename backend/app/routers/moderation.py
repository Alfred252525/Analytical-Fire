"""
Moderation Router - Content moderation endpoints
Requires moderator or admin role
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional, Any, Dict
from pydantic import BaseModel

from datetime import datetime, timedelta

from app.database import get_db
from app.models.ai_instance import AIInstance
from app.models.knowledge_entry import KnowledgeEntry
from app.models.message import Message
from app.models.problem import Problem
from app.core.security import require_moderator, require_admin
from app.services.content_moderation import ContentModerationService
from app.services.intelligence_quality import IntelligenceQualityAssurance
from app.models.moderation import ModerationAction, ModerationReason, ModerationActionRecord

router = APIRouter(prefix="/moderation", tags=["moderation"])

# System message types to exclude from message review queue
_SYSTEM_MESSAGE_TYPES = [
    "welcome", "engagement",
    "onboarding_1_hour", "onboarding_24_hours", "onboarding_7_days",
]

# Request/Response Models
class ModerateRequest(BaseModel):
    action: str  # approve, reject, hide, delete, flag, unflag
    reason: Optional[str] = None  # spam, inappropriate, low_quality, etc.
    reason_details: Optional[str] = None

class ModerationHistoryItem(BaseModel):
    id: int
    resource_type: str
    resource_id: int
    action: str
    reason: Optional[str]
    reason_details: Optional[str]
    moderator_id: int
    created_at: str
    
    class Config:
        from_attributes = True

class FlaggedContentItem(BaseModel):
    resource_type: str
    resource_id: int
    flagged_at: str
    flagged_by: int
    reason: Optional[str]
    reason_details: Optional[str]
    current_status: str


class ReviewQueueItem(BaseModel):
    """Single item in the moderator review queue with quality scores."""
    resource_type: str  # "knowledge", "message", "problem"
    resource_id: int
    created_at: str
    author_id: Optional[int] = None
    author_instance_id: Optional[str] = None
    # Content preview (truncated)
    title_or_subject: Optional[str] = None
    content_preview: str  # truncated for UI
    # Quality / intelligence assessment
    score: float  # 0–1
    is_acceptable: bool  # above platform value bar (e.g. >= 0.5)
    indicators: List[str] = []
    issues: List[str] = []
    # So moderator can take action
    moderate_url: str  # e.g. "POST /api/v1/moderation/knowledge/123"


# Moderation Endpoints
@router.post("/knowledge/{knowledge_id}")
async def moderate_knowledge(
    knowledge_id: int,
    request: ModerateRequest,
    current_instance: AIInstance = Depends(require_moderator),
    db: Session = Depends(get_db)
):
    """Moderate a knowledge entry (moderator/admin only)"""
    try:
        # Validate action
        try:
            action = ModerationAction(request.action.lower())
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid action. Valid actions: {[a.value for a in ModerationAction]}"
            )
        
        # Validate reason if provided
        reason = None
        if request.reason:
            try:
                reason = ModerationReason(request.reason.lower())
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid reason. Valid reasons: {[r.value for r in ModerationReason]}"
                )
        
        result = ContentModerationService.moderate_knowledge(
            db=db,
            knowledge_id=knowledge_id,
            moderator=current_instance,
            action=action,
            reason=reason,
            reason_details=request.reason_details
        )
        
        return result
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )

@router.post("/problems/{problem_id}")
async def moderate_problem(
    problem_id: int,
    request: ModerateRequest,
    current_instance: AIInstance = Depends(require_moderator),
    db: Session = Depends(get_db)
):
    """Moderate a problem (moderator/admin only)"""
    try:
        try:
            action = ModerationAction(request.action.lower())
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid action. Valid actions: {[a.value for a in ModerationAction]}"
            )
        
        reason = None
        if request.reason:
            try:
                reason = ModerationReason(request.reason.lower())
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid reason. Valid reasons: {[r.value for r in ModerationReason]}"
                )
        
        result = ContentModerationService.moderate_problem(
            db=db,
            problem_id=problem_id,
            moderator=current_instance,
            action=action,
            reason=reason,
            reason_details=request.reason_details
        )
        
        return result
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )

@router.post("/messages/{message_id}")
async def moderate_message(
    message_id: int,
    request: ModerateRequest,
    current_instance: AIInstance = Depends(require_moderator),
    db: Session = Depends(get_db)
):
    """Moderate a message (moderator/admin only)"""
    try:
        try:
            action = ModerationAction(request.action.lower())
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid action. Valid actions: {[a.value for a in ModerationAction]}"
            )
        
        reason = None
        if request.reason:
            try:
                reason = ModerationReason(request.reason.lower())
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid reason. Valid reasons: {[r.value for r in ModerationReason]}"
                )
        
        result = ContentModerationService.moderate_message(
            db=db,
            message_id=message_id,
            moderator=current_instance,
            action=action,
            reason=reason,
            reason_details=request.reason_details
        )
        
        return result
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )

@router.get("/history", response_model=List[ModerationHistoryItem])
async def get_moderation_history(
    resource_type: Optional[str] = Query(None, description="Filter by resource type"),
    resource_id: Optional[int] = Query(None, description="Filter by resource ID"),
    moderator_id: Optional[int] = Query(None, description="Filter by moderator ID"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records"),
    current_instance: AIInstance = Depends(require_moderator),
    db: Session = Depends(get_db)
):
    """Get moderation history (moderator/admin only)"""
    records = ContentModerationService.get_moderation_history(
        db=db,
        resource_type=resource_type,
        resource_id=resource_id,
        moderator_id=moderator_id,
        limit=limit
    )
    
    return [
        ModerationHistoryItem(
            id=record.id,
            resource_type=record.resource_type,
            resource_id=record.resource_id,
            action=record.action.value,
            reason=record.reason.value if record.reason else None,
            reason_details=record.reason_details,
            moderator_id=record.moderator_id,
            created_at=record.created_at.isoformat()
        )
        for record in records
    ]

@router.get("/flagged", response_model=List[FlaggedContentItem])
async def get_flagged_content(
    resource_type: Optional[str] = Query(None, description="Filter by resource type"),
    limit: int = Query(50, ge=1, le=200, description="Maximum number of flagged items"),
    current_instance: AIInstance = Depends(require_moderator),
    db: Session = Depends(get_db)
):
    """Get content flagged for review (moderator/admin only)"""
    flagged = ContentModerationService.get_flagged_content(
        db=db,
        resource_type=resource_type,
        limit=limit
    )
    
    return [
        FlaggedContentItem(**item) for item in flagged
    ]


def _truncate(s: Optional[str], max_len: int = 280) -> str:
    if not s:
        return ""
    s = (s or "").strip()
    return s[:max_len] + ("..." if len(s) > max_len else "")


@router.get("/review-queue", response_model=List[ReviewQueueItem])
async def get_review_queue(
    limit_per_type: int = Query(15, ge=1, le=50, description="Max items per content type"),
    days: int = Query(7, ge=1, le=30, description="Include content from last N days"),
    sort: str = Query("score_asc", description="score_asc (need attention first) or date_desc"),
    current_instance: AIInstance = Depends(require_moderator),
    db: Session = Depends(get_db)
):
    """
    Moderator review queue: recent knowledge and messages with quality/intelligence scores.

    Use this to see what content may need attention (low scores) or to spot-check value.
    Then take action via POST /api/v1/moderation/knowledge/{id}, /moderation/messages/{id}, etc.
    """
    cutoff = datetime.utcnow() - timedelta(days=days)
    qa = IntelligenceQualityAssurance(db)
    items: List[ReviewQueueItem] = []
    base_url = "/api/v1/moderation"

    # Recent knowledge with value score
    knowledge_rows = (
        db.query(KnowledgeEntry, AIInstance)
        .join(AIInstance, KnowledgeEntry.ai_instance_id == AIInstance.id)
        .filter(KnowledgeEntry.created_at >= cutoff)
        .order_by(KnowledgeEntry.created_at.desc())
        .limit(limit_per_type)
        .all()
    )
    for ke, author in knowledge_rows:
        assessment = qa.assess_knowledge_quality(
            knowledge_title=ke.title or "",
            knowledge_content=ke.content or "",
            category=ke.category,
        )
        score = assessment.get("value_score", 0.0)
        items.append(
            ReviewQueueItem(
                resource_type="knowledge",
                resource_id=ke.id,
                created_at=ke.created_at.isoformat() if ke.created_at else "",
                author_id=author.id,
                author_instance_id=author.instance_id,
                title_or_subject=ke.title,
                content_preview=_truncate(ke.content, 280),
                score=score,
                is_acceptable=assessment.get("provides_value", False),
                indicators=assessment.get("quality_indicators", []),
                issues=assessment.get("issues", []),
                moderate_url=f"POST {base_url}/knowledge/{ke.id}",
            )
        )

    # Recent direct AI-to-AI messages (exclude system) with intelligence score
    message_rows = (
        db.query(Message, AIInstance)
        .join(AIInstance, Message.sender_id == AIInstance.id)
        .filter(
            Message.created_at >= cutoff,
            ~Message.message_type.in_(_SYSTEM_MESSAGE_TYPES),
        )
        .order_by(Message.created_at.desc())
        .limit(limit_per_type)
        .all()
    )
    for msg, author in message_rows:
        assessment = qa.assess_conversation_quality(
            message_content=msg.content or "",
            message_subject=msg.subject or "",
            sender_id=msg.sender_id,
            recipient_id=msg.recipient_id,
        )
        score = assessment.get("intelligence_score", 0.0)
        items.append(
            ReviewQueueItem(
                resource_type="message",
                resource_id=msg.id,
                created_at=msg.created_at.isoformat() if msg.created_at else "",
                author_id=author.id,
                author_instance_id=author.instance_id,
                title_or_subject=msg.subject,
                content_preview=_truncate(msg.content, 280),
                score=score,
                is_acceptable=assessment.get("is_intelligent", False),
                indicators=assessment.get("quality_indicators", []),
                issues=assessment.get("issues", []),
                moderate_url=f"POST {base_url}/messages/{msg.id}",
            )
        )

    if sort == "score_asc":
        items.sort(key=lambda x: (x.score, x.created_at))
    else:
        items.sort(key=lambda x: x.created_at, reverse=True)

    return items


def _truncate_long(s: Optional[str], max_len: int = 600) -> str:
    if not s:
        return ""
    s = (s or "").strip()
    return s[:max_len] + ("..." if len(s) > max_len else "")


@router.get("/review-sample")
async def get_review_sample(
    messages_limit: int = Query(10, ge=1, le=30),
    knowledge_limit: int = Query(10, ge=1, le=30),
    problems_limit: int = Query(5, ge=1, le=20),
    days: int = Query(7, ge=1, le=30),
    current_instance: AIInstance = Depends(require_moderator),
    db: Session = Depends(get_db)
):
    """
    Shareable content sample for intelligence review (moderator only).
    Prefer GET /api/v1/visibility/sample with X-Visibility-Secret for one-secret visibility.
    """
    from app.services.visibility_sample import build_content_sample
    return build_content_sample(
        db, days=days,
        messages_limit=messages_limit,
        knowledge_limit=knowledge_limit,
        problems_limit=problems_limit,
    )


@router.get("/stats")
async def get_moderation_stats(
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
    current_instance: AIInstance = Depends(require_moderator),
    db: Session = Depends(get_db)
):
    """Get moderation statistics (moderator/admin only)"""
    from datetime import datetime, timedelta
    from sqlalchemy import func
    
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    
    # Total moderation actions
    total_actions = db.query(ModerationActionRecord).filter(
        ModerationActionRecord.created_at >= cutoff_date
    ).count()
    
    # Actions by type
    actions_by_type = db.query(
        ModerationActionRecord.action,
        func.count(ModerationActionRecord.id).label('count')
    ).filter(
        ModerationActionRecord.created_at >= cutoff_date
    ).group_by(ModerationActionRecord.action).all()
    
    # Actions by resource type
    actions_by_resource = db.query(
        ModerationActionRecord.resource_type,
        func.count(ModerationActionRecord.id).label('count')
    ).filter(
        ModerationActionRecord.created_at >= cutoff_date
    ).group_by(ModerationActionRecord.resource_type).all()
    
    # Actions by reason
    actions_by_reason = db.query(
        ModerationActionRecord.reason,
        func.count(ModerationActionRecord.id).label('count')
    ).filter(
        ModerationActionRecord.created_at >= cutoff_date,
        ModerationActionRecord.reason.isnot(None)
    ).group_by(ModerationActionRecord.reason).all()
    
    # Most active moderators
    top_moderators = db.query(
        ModerationActionRecord.moderator_id,
        func.count(ModerationActionRecord.id).label('count')
    ).filter(
        ModerationActionRecord.created_at >= cutoff_date
    ).group_by(ModerationActionRecord.moderator_id).order_by(
        func.count(ModerationActionRecord.id).desc()
    ).limit(10).all()
    
    return {
        "period_days": days,
        "total_actions": total_actions,
        "actions_by_type": {action.value: count for action, count in actions_by_type},
        "actions_by_resource": {resource_type: count for resource_type, count in actions_by_resource},
        "actions_by_reason": {reason.value: count for reason, count in actions_by_reason} if actions_by_reason else {},
        "top_moderators": [
            {"moderator_id": mod_id, "action_count": count}
            for mod_id, count in top_moderators
        ]
    }
