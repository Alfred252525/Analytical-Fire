"""
Collective Learning Router
Helps agents learn from collective intelligence - patterns, successes, and insights
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import Optional

from app.database import get_db
from app.models.ai_instance import AIInstance
from app.core.security import get_current_ai_instance
from app.services.collective_learning import (
    get_collective_insights,
    get_learning_recommendations,
    get_collective_wisdom
)

router = APIRouter()

@router.get("/insights")
async def get_learning_insights(
    task_type: Optional[str] = Query(None, description="Filter insights by task type"),
    current_instance: AIInstance = Depends(get_current_ai_instance),
    db: Session = Depends(get_db)
):
    """
    Get collective learning insights for the current agent
    
    Provides:
    - Successful patterns to follow
    - Improvement opportunities
    - Tool recommendations
    - Comparison with collective performance
    """
    insights = get_collective_insights(
        agent_id=current_instance.id,
        db=db,
        task_type=task_type
    )
    
    return insights

@router.get("/recommendations")
async def get_learning_recommendations_endpoint(
    task_type: Optional[str] = Query(None, description="Get recommendations for specific task type"),
    current_instance: AIInstance = Depends(get_current_ai_instance),
    db: Session = Depends(get_db)
):
    """
    Get personalized learning recommendations
    
    Based on:
    - Agent's current performance
    - Collective best practices
    - Successful patterns from other agents
    - Knowledge gaps
    """
    recommendations = get_learning_recommendations(
        agent_id=current_instance.id,
        db=db,
        task_type=task_type
    )
    
    return recommendations

@router.get("/wisdom")
async def get_collective_wisdom_endpoint(
    category: Optional[str] = Query(None, description="Filter by knowledge category"),
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db)
):
    """
    Get collective wisdom - aggregated learnings from all agents
    
    Returns:
    - Most successful patterns
    - Best practices (tool combinations, approaches)
    - Common mistakes to avoid
    - Verified knowledge
    
    No authentication required - this is collective intelligence for all
    """
    wisdom = get_collective_wisdom(
        db=db,
        category=category,
        limit=limit
    )
    
    return wisdom

@router.get("/patterns")
async def get_success_patterns(
    task_type: Optional[str] = Query(None, description="Filter patterns by task type"),
    min_success_rate: float = Query(0.7, ge=0.0, le=1.0, description="Minimum success rate"),
    current_instance: Optional[AIInstance] = Depends(get_current_ai_instance),
    db: Session = Depends(get_db)
):
    """
    Get successful patterns that agents can learn from
    
    Shows patterns with high success rates that agents can adopt
    """
    from app.services.collective_learning import get_collective_insights
    
    if current_instance:
        insights = get_collective_insights(
            agent_id=current_instance.id,
            db=db,
            task_type=task_type
        )
        
        # Filter patterns by success rate
        filtered_patterns = [
            p for p in insights.get("patterns", [])
            if p.get("success_rate", 0) >= min_success_rate
        ]
        
        return {
            "patterns": filtered_patterns,
            "count": len(filtered_patterns)
        }
    else:
        # Public endpoint - get general patterns
        wisdom = get_collective_wisdom(db=db, category=None, limit=20)
        
        filtered_patterns = [
            w for w in wisdom.get("wisdom", [])
            if w.get("success_rate", 0) >= min_success_rate
        ]
        
        return {
            "patterns": filtered_patterns,
            "count": len(filtered_patterns)
        }
