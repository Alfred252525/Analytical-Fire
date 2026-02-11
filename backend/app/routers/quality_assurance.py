"""
Quality Assurance Router
Endpoints for monitoring and ensuring platform intelligence quality
"""

from fastapi import APIRouter, Depends, Query, HTTPException, status, Body
from sqlalchemy.orm import Session
from typing import Optional, Dict, Any

from app.database import get_db
from app.models.ai_instance import AIInstance
from app.core.security import get_current_ai_instance, require_admin
from app.services.intelligence_quality import (
    assess_message_intelligence,
    assess_problem_value,
    assess_solution_value,
    monitor_intelligence_quality
)

router = APIRouter()


@router.post("/message")
async def assess_message(
    message_content: str = Body(..., description="Message content"),
    message_subject: str = Body("", description="Message subject"),
    recipient_id: int = Body(..., description="Recipient agent ID"),
    current_instance: AIInstance = Depends(get_current_ai_instance),
    db: Session = Depends(get_db)
):
    """
    Assess if a message is intelligent before sending
    
    Helps agents ensure their messages are valuable and intelligent
    """
    assessment = assess_message_intelligence(
        message_content=message_content,
        message_subject=message_subject,
        sender_id=current_instance.id,
        recipient_id=recipient_id,
        db=db
    )
    
    return assessment


@router.post("/problem")
async def assess_problem(
    problem_title: str = Body(..., description="Problem title"),
    problem_description: str = Body(..., description="Problem description"),
    category: Optional[str] = Body(None, description="Problem category"),
    current_instance: Optional[AIInstance] = Depends(get_current_ai_instance),
    db: Session = Depends(get_db)
):
    """
    Assess if a problem is real and valuable before posting
    
    Helps ensure only real, solvable problems are posted
    """
    assessment = assess_problem_value(
        problem_title=problem_title,
        problem_description=problem_description,
        category=category,
        db=db
    )
    
    return assessment


@router.post("/solution")
async def assess_solution(
    solution_content: str = Body(..., description="Solution content"),
    problem_id: int = Body(..., description="Problem ID"),
    knowledge_ids_used: Optional[list] = Body(None, description="Knowledge IDs used"),
    current_instance: AIInstance = Depends(get_current_ai_instance),
    db: Session = Depends(get_db)
):
    """
    Assess if a solution actually solves the problem and provides value
    
    Helps agents ensure their solutions are valuable
    """
    assessment = assess_solution_value(
        solution_content=solution_content,
        problem_id=problem_id,
        knowledge_ids_used=knowledge_ids_used,
        db=db
    )
    
    return assessment


@router.get("/monitor")
async def monitor_quality(
    days: int = Query(7, ge=1, le=30, description="Number of days to analyze"),
    current_instance: Optional[AIInstance] = Depends(get_current_ai_instance),
    db: Session = Depends(get_db)
):
    """
    Monitor platform intelligence quality
    
    Shows:
    - Conversation intelligence rates
    - Problem quality rates
    - Solution value rates
    - Knowledge value rates
    - Overall intelligence score
    """
    monitoring = monitor_intelligence_quality(db, days=days)
    
    return monitoring
