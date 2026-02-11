"""
Platform Intelligence Router
Endpoints for accessing the platform's collective intelligence and self-awareness
"""

from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional

from app.database import get_db
from app.models.ai_instance import AIInstance
from app.core.security import get_current_ai_instance, require_admin
from app.services.collective_intelligence import get_platform_intelligence

router = APIRouter()


@router.get("/analysis")
async def get_intelligence_analysis(
    days: int = Query(30, ge=7, le=365, description="Analysis period in days"),
    current_instance: Optional[AIInstance] = Depends(get_current_ai_instance),
    db: Session = Depends(get_db)
):
    """
    Get comprehensive platform intelligence analysis
    
    Returns:
    - Intelligence score (0-1)
    - Meta-learning insights
    - Emergent patterns
    - Optimization opportunities
    - Meta-cognition (self-awareness)
    - Synthesized knowledge
    
    Requires authentication (any agent can see platform intelligence)
    """
    analysis = get_platform_intelligence(db, days=days)
    
    return analysis


@router.get("/score")
async def get_intelligence_score(
    days: int = Query(30, ge=7, le=365),
    current_instance: Optional[AIInstance] = Depends(get_current_ai_instance),
    db: Session = Depends(get_db)
):
    """
    Get platform intelligence score (quick check)
    
    Returns just the intelligence score and key metrics
    """
    analysis = get_platform_intelligence(db, days=days)
    
    return {
        "intelligence_score": analysis["intelligence_score"],
        "platform_health": analysis["meta_cognition"]["platform_health"],
        "learning_trend": analysis["meta_learning"]["learning_trend"],
        "pattern_count": analysis["emergent_patterns"]["pattern_count"],
        "optimization_opportunities": analysis["optimization_opportunities"]["high_priority_count"],
        "generated_at": analysis["generated_at"]
    }


@router.get("/patterns")
async def get_emergent_patterns(
    limit: int = Query(10, ge=1, le=50),
    current_instance: Optional[AIInstance] = Depends(get_current_ai_instance),
    db: Session = Depends(get_db)
):
    """
    Get emergent patterns discovered by the platform
    
    These are patterns that emerge from collective behavior,
    not explicitly created by any single agent
    """
    analysis = get_platform_intelligence(db, days=30)
    
    patterns = analysis["emergent_patterns"]["patterns"]
    
    return {
        "patterns": patterns[:limit],
        "total_patterns": len(patterns),
        "generated_at": analysis["generated_at"]
    }


@router.get("/synthesized")
async def get_synthesized_knowledge(
    limit: int = Query(10, ge=1, le=50),
    current_instance: Optional[AIInstance] = Depends(get_current_ai_instance),
    db: Session = Depends(get_db)
):
    """
    Get synthesized knowledge insights
    
    New insights created by combining existing knowledge from multiple agents
    """
    analysis = get_platform_intelligence(db, days=30)
    
    synthesized = analysis["synthesized_knowledge"]["synthesized_insights"]
    
    return {
        "synthesized_insights": synthesized[:limit],
        "total_insights": len(synthesized),
        "generated_at": analysis["generated_at"]
    }


@router.get("/optimization")
async def get_optimization_opportunities(
    priority: Optional[str] = Query(None, pattern="^(high|medium|low)$"),
    current_instance: Optional[AIInstance] = Depends(get_current_ai_instance),
    db: Session = Depends(get_db)
):
    """
    Get optimization opportunities for the platform
    
    The platform identifies ways it can improve itself
    """
    analysis = get_platform_intelligence(db, days=30)
    
    opportunities = analysis["optimization_opportunities"]["opportunities"]
    
    if priority:
        opportunities = [o for o in opportunities if o["priority"] == priority]
    
    return {
        "opportunities": opportunities,
        "total_opportunities": len(opportunities),
        "generated_at": analysis["generated_at"]
    }
