"""
Analytics router - Agent performance and self-improvement analytics
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import Optional

from app.database import get_db
from app.models.ai_instance import AIInstance
from app.core.security import get_current_ai_instance
from app.services.agent_analytics import (
    get_agent_performance_analysis,
    get_agent_learning_path,
    get_agent_insights_summary
)

router = APIRouter()

@router.get("/performance")
async def get_performance_analysis(
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
    current_instance: AIInstance = Depends(get_current_ai_instance),
    db: Session = Depends(get_db)
):
    """
    Get comprehensive performance analysis
    
    Analyzes:
    - Success patterns
    - Tool effectiveness
    - Task type performance
    - Strengths and weaknesses
    - Improvement opportunities
    """
    analysis = get_agent_performance_analysis(
        agent_id=current_instance.id,
        db=db,
        days=days
    )
    
    return analysis

@router.get("/learning-path")
async def get_learning_path_endpoint(
    current_instance: AIInstance = Depends(get_current_ai_instance),
    db: Session = Depends(get_db)
):
    """
    Get personalized learning path
    
    Based on:
    - Current performance gaps
    - Collective best practices
    - Agent's interests
    - Success patterns from other agents
    """
    learning_path = get_agent_learning_path(
        agent_id=current_instance.id,
        db=db
    )
    
    return learning_path

@router.get("/insights")
async def get_insights_summary(
    current_instance: AIInstance = Depends(get_current_ai_instance),
    db: Session = Depends(get_db)
):
    """
    Get comprehensive insights summary
    
    Combines:
    - Performance analysis
    - Reputation breakdown
    - Collaboration metrics
    - Learning path
    - Key insights
    """
    summary = get_agent_insights_summary(
        agent_id=current_instance.id,
        db=db
    )
    
    return summary
