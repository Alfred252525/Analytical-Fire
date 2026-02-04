"""
Decision logging router
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
import hashlib
import json

from app.database import get_db
from app.models.ai_instance import AIInstance
from app.models.decision import Decision
from app.schemas.decision import DecisionCreate, DecisionResponse, DecisionQuery
from app.core.security import get_current_ai_instance

router = APIRouter()

def generate_context_hash(decision_data: dict) -> str:
    """Generate a hash from decision context for pattern matching"""
    # Create a hash from key context fields
    context_str = json.dumps({
        "task_type": decision_data.get("task_type"),
        "user_query": decision_data.get("user_query", "")[:200],  # First 200 chars
        "tools_used": sorted(decision_data.get("tools_used", []))
    }, sort_keys=True)
    return hashlib.sha256(context_str.encode()).hexdigest()[:16]

@router.post("/", response_model=DecisionResponse, status_code=status.HTTP_201_CREATED)
async def log_decision(
    decision: DecisionCreate,
    current_instance: AIInstance = Depends(get_current_ai_instance),
    db: Session = Depends(get_db)
):
    """Log a decision made by the AI"""
    # Generate context hash if not provided
    context_hash = decision.context_hash
    if not context_hash:
        decision_dict = decision.dict()
        context_hash = generate_context_hash(decision_dict)
    
    db_decision = Decision(
        ai_instance_id=current_instance.id,
        task_type=decision.task_type,
        task_description=decision.task_description,
        user_query=decision.user_query,
        reasoning=decision.reasoning,
        tools_used=decision.tools_used or [],
        steps_taken=decision.steps_taken or [],
        outcome=decision.outcome,
        success_score=decision.success_score,
        execution_time_ms=decision.execution_time_ms,
        user_feedback=decision.user_feedback,
        error_message=decision.error_message,
        context_hash=context_hash
    )
    
    db.add(db_decision)
    db.commit()
    db.refresh(db_decision)
    
    return db_decision

@router.get("/", response_model=List[DecisionResponse])
async def get_decisions(
    query: DecisionQuery = Depends(),
    current_instance: AIInstance = Depends(get_current_ai_instance),
    db: Session = Depends(get_db)
):
    """Get decisions with optional filtering"""
    db_query = db.query(Decision).filter(Decision.ai_instance_id == current_instance.id)
    
    if query.task_type:
        db_query = db_query.filter(Decision.task_type == query.task_type)
    if query.outcome:
        db_query = db_query.filter(Decision.outcome == query.outcome)
    if query.min_success_score is not None:
        db_query = db_query.filter(Decision.success_score >= query.min_success_score)
    if query.start_date:
        db_query = db_query.filter(Decision.created_at >= query.start_date)
    if query.end_date:
        db_query = db_query.filter(Decision.created_at <= query.end_date)
    
    db_query = db_query.order_by(Decision.created_at.desc()).limit(query.limit)
    
    return db_query.all()

@router.get("/stats")
async def get_decision_stats(
    current_instance: AIInstance = Depends(get_current_ai_instance),
    db: Session = Depends(get_db)
):
    """Get statistics about decisions"""
    from sqlalchemy import func
    
    total = db.query(func.count(Decision.id)).filter(
        Decision.ai_instance_id == current_instance.id
    ).scalar()
    
    success_count = db.query(func.count(Decision.id)).filter(
        Decision.ai_instance_id == current_instance.id,
        Decision.outcome == "success"
    ).scalar()
    
    avg_score = db.query(func.avg(Decision.success_score)).filter(
        Decision.ai_instance_id == current_instance.id
    ).scalar() or 0.0
    
    avg_time = db.query(func.avg(Decision.execution_time_ms)).filter(
        Decision.ai_instance_id == current_instance.id,
        Decision.execution_time_ms.isnot(None)
    ).scalar() or 0.0
    
    return {
        "total_decisions": total,
        "success_count": success_count,
        "success_rate": success_count / total if total > 0 else 0.0,
        "average_success_score": float(avg_score),
        "average_execution_time_ms": float(avg_time)
    }
