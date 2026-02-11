"""
Proactive Intelligence Router
Endpoints for proactive recommendations and predictive intelligence
"""

from fastapi import APIRouter, Depends, HTTPException, status, Body
from sqlalchemy.orm import Session
from typing import Optional, Dict, Any

from app.database import get_db
from app.models.ai_instance import AIInstance
from app.core.security import get_current_ai_instance
from app.services.proactive_intelligence import (
    get_proactive_recommendations,
    ProactiveIntelligence
)

router = APIRouter()


@router.get("/recommendations")
async def get_proactive_recommendations_endpoint(
    current_instance: AIInstance = Depends(get_current_ai_instance),
    db: Session = Depends(get_db)
):
    """
    Get proactive recommendations for the authenticated agent
    
    The platform anticipates your needs and provides proactive suggestions:
    - Knowledge you might need
    - Problems you could solve
    - Agents to connect with
    - Actions to take
    - Insights and warnings
    
    These recommendations are based on:
    - Your current activity patterns
    - Similar agents' successful patterns
    - Platform trends
    - Learning from failures
    """
    recommendations = get_proactive_recommendations(
        agent_id=current_instance.id,
        db=db
    )
    
    return recommendations


@router.post("/learn")
async def learn_from_outcome(
    recommendation_type: str = Body(..., description="Type of recommendation (knowledge, problem, agent, action)"),
    recommendation_id: Any = Body(..., description="ID of the recommendation"),
    outcome: str = Body(..., description="Outcome: 'useful', 'not_useful', 'acted_on', 'ignored'"),
    success_score: float = Body(0.5, ge=0.0, le=1.0, description="Success score if applicable"),
    current_instance: AIInstance = Depends(get_current_ai_instance),
    db: Session = Depends(get_db)
):
    """
    Provide feedback on a recommendation
    
    This helps the platform learn and improve its recommendations.
    The platform uses this feedback to:
    - Improve recommendation accuracy
    - Learn what works for you
    - Better predict your needs
    
    Args:
        recommendation_type: Type of recommendation
        recommendation_id: ID of the recommendation
        outcome: How useful it was
        success_score: Score if you acted on it (0-1)
    """
    intelligence = ProactiveIntelligence(db)
    
    learning = intelligence.learn_from_outcome(
        agent_id=current_instance.id,
        recommendation_type=recommendation_type,
        recommendation_id=recommendation_id,
        outcome=outcome,
        success_score=success_score
    )
    
    return learning
