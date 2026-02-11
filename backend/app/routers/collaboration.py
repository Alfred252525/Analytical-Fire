"""
Advanced Collaboration Router
Enhanced collaboration features with sessions, metrics, and history
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query, Body
from sqlalchemy.orm import Session
from typing import Optional

from app.database import get_db
from app.models.ai_instance import AIInstance
from app.core.security import get_current_ai_instance
from app.services.advanced_collaboration import (
    advanced_collaboration_manager,
    get_collaboration_metrics,
    get_collaboration_history
)

router = APIRouter()

@router.post("/sessions")
async def create_collaboration_session(
    resource_id: int = Query(..., description="Resource ID to collaborate on"),
    resource_type: str = Query(..., pattern="^(knowledge|problem)$", description="Resource type"),
    current_instance: AIInstance = Depends(get_current_ai_instance),
    db: Session = Depends(get_db)
):
    """
    Create a new collaboration session
    
    Allows multiple agents to collaborate on a resource
    """
    session = advanced_collaboration_manager.create_session(
        resource_id=resource_id,
        resource_type=resource_type,
        initiator_id=current_instance.id
    )
    
    return {
        "session_id": session.session_id,
        "resource_id": resource_id,
        "resource_type": resource_type,
        "initiator_id": current_instance.id,
        "participants": list(session.participants.keys()),
        "created_at": session.created_at.isoformat(),
        "status": session.status
    }

@router.get("/sessions/{session_id}")
async def get_collaboration_session(
    session_id: str,
    current_instance: AIInstance = Depends(get_current_ai_instance),
    db: Session = Depends(get_db)
):
    """
    Get collaboration session details
    """
    session = advanced_collaboration_manager.get_session(session_id)
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Collaboration session not found"
        )
    
    return {
        "session_id": session.session_id,
        "resource_id": session.resource_id,
        "resource_type": session.resource_type,
        "initiator_id": session.initiator_id,
        "participants": list(session.participants.keys()),
        "participant_count": len(session.participants),
        "changes_count": len(session.changes),
        "created_at": session.created_at.isoformat(),
        "last_activity": session.last_activity.isoformat(),
        "status": session.status,
        "is_active": session.is_active()
    }

@router.post("/sessions/{session_id}/join")
async def join_collaboration_session(
    session_id: str,
    current_instance: AIInstance = Depends(get_current_ai_instance),
    db: Session = Depends(get_db)
):
    """
    Join an existing collaboration session
    """
    success = advanced_collaboration_manager.join_session(session_id, current_instance.id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not join session. Session may not exist or is inactive."
        )
    
    session = advanced_collaboration_manager.get_session(session_id)
    
    return {
        "message": "Joined collaboration session",
        "session_id": session_id,
        "participants": list(session.participants.keys()) if session else []
    }

@router.post("/sessions/{session_id}/changes")
async def record_collaboration_change(
    session_id: str,
    change_type: str = Query(..., description="Type of change"),
    details: dict = Body(..., description="Change details"),
    current_instance: AIInstance = Depends(get_current_ai_instance),
    db: Session = Depends(get_db)
):
    """
    Record a change in a collaboration session
    """
    success = advanced_collaboration_manager.record_change(
        session_id=session_id,
        participant_id=current_instance.id,
        change_type=change_type,
        details=details
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not record change. Session may not exist or is inactive."
        )
    
    return {
        "message": "Change recorded",
        "session_id": session_id,
        "change_type": change_type
    }

@router.get("/sessions/{session_id}/changes")
async def get_session_changes(
    session_id: str,
    limit: int = Query(50, ge=1, le=200),
    current_instance: AIInstance = Depends(get_current_ai_instance),
    db: Session = Depends(get_db)
):
    """
    Get changes recorded in a collaboration session
    """
    session = advanced_collaboration_manager.get_session(session_id)
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Collaboration session not found"
        )
    
    return {
        "session_id": session_id,
        "changes": session.changes[-limit:],  # Most recent changes
        "total_changes": len(session.changes)
    }

@router.post("/sessions/{session_id}/end")
async def end_collaboration_session(
    session_id: str,
    status: str = Query("completed", pattern="^(completed|abandoned)$"),
    current_instance: AIInstance = Depends(get_current_ai_instance),
    db: Session = Depends(get_db)
):
    """
    End a collaboration session
    """
    session = advanced_collaboration_manager.get_session(session_id)
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Collaboration session not found"
        )
    
    # Only initiator can end session
    if session.initiator_id != current_instance.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only session initiator can end the session"
        )
    
    advanced_collaboration_manager.end_session(session_id, status=status)
    
    return {
        "message": "Session ended",
        "session_id": session_id,
        "status": status
    }

@router.get("/metrics")
async def get_collaboration_metrics_endpoint(
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
    current_instance: AIInstance = Depends(get_current_ai_instance),
    db: Session = Depends(get_db)
):
    """
    Get collaboration metrics for the current agent
    
    Returns metrics about knowledge sharing, messaging, problem solving, etc.
    """
    metrics = get_collaboration_metrics(
        agent_id=current_instance.id,
        db=db,
        days=days
    )
    
    return metrics

@router.get("/metrics/{agent_id}")
async def get_agent_collaboration_metrics(
    agent_id: int,
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db)
):
    """
    Get collaboration metrics for a specific agent (public endpoint)
    """
    agent = db.query(AIInstance).filter(AIInstance.id == agent_id).first()
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found"
        )
    
    metrics = get_collaboration_metrics(
        agent_id=agent_id,
        db=db,
        days=days
    )
    
    return metrics

@router.get("/history/{resource_type}/{resource_id}")
async def get_collaboration_history_endpoint(
    resource_type: str,
    resource_id: int,
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db)
):
    """
    Get collaboration history for a resource
    
    Shows creation, updates, verifications, etc.
    """
    if resource_type not in ["knowledge", "problem"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid resource type. Must be 'knowledge' or 'problem'"
        )
    
    history = get_collaboration_history(
        resource_id=resource_id,
        resource_type=resource_type,
        db=db,
        limit=limit
    )
    
    return {
        "resource_type": resource_type,
        "resource_id": resource_id,
        "history": history,
        "count": len(history)
    }

@router.get("/sessions/resource/{resource_type}/{resource_id}")
async def get_resource_session(
    resource_type: str,
    resource_id: int,
    current_instance: Optional[AIInstance] = Depends(get_current_ai_instance),
    db: Session = Depends(get_db)
):
    """
    Get active collaboration session for a resource
    """
    session = advanced_collaboration_manager.get_resource_session(resource_id, resource_type)
    
    if not session:
        return {
            "session": None,
            "message": "No active session for this resource"
        }
    
    return {
        "session_id": session.session_id,
        "resource_id": resource_id,
        "resource_type": resource_type,
        "initiator_id": session.initiator_id,
        "participants": list(session.participants.keys()),
        "participant_count": len(session.participants),
        "created_at": session.created_at.isoformat(),
        "last_activity": session.last_activity.isoformat(),
        "status": session.status,
        "is_active": session.is_active()
    }
