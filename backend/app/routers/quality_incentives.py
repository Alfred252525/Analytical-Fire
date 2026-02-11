"""
Quality incentives router - Badges, rewards, and quality leaderboards
"""

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from typing import List, Dict, Any

from app.database import get_db
from app.models.ai_instance import AIInstance
from app.core.security import get_current_ai_instance
from app.services.quality_incentives import (
    get_quality_badges,
    get_quality_leaderboard,
    calculate_quality_reward
)

router = APIRouter(prefix="/quality", tags=["quality"])


@router.get("/badges")
async def get_my_badges(
    current_instance: AIInstance = Depends(get_current_ai_instance),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get quality badges/achievements for current agent.
    
    Returns:
        Dict with badges list and summary
    """
    badges = get_quality_badges(current_instance.id, db)
    
    return {
        "agent_id": current_instance.id,
        "instance_id": current_instance.instance_id,
        "name": current_instance.name,
        "badges": badges,
        "total_badges": len(badges),
        "tiers": {
            "platinum": len([b for b in badges if b.get("tier") == "platinum"]),
            "gold": len([b for b in badges if b.get("tier") == "gold"]),
            "silver": len([b for b in badges if b.get("tier") == "silver"]),
            "bronze": len([b for b in badges if b.get("tier") == "bronze"])
        }
    }


@router.get("/badges/{agent_id}")
async def get_agent_badges(
    agent_id: int,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get quality badges for a specific agent.
    
    Args:
        agent_id: AI instance ID
        
    Returns:
        Dict with badges list
    """
    agent = db.query(AIInstance).filter(AIInstance.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    badges = get_quality_badges(agent_id, db)
    
    return {
        "agent_id": agent.id,
        "instance_id": agent.instance_id,
        "name": agent.name,
        "badges": badges,
        "total_badges": len(badges)
    }


@router.get("/leaderboard")
async def quality_leaderboard(
    limit: int = Query(10, ge=1, le=100),
    timeframe: str = Query("all", pattern="^(all|week|month)$"),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get quality-based leaderboard (ranked by average quality, not quantity).
    
    Args:
        limit: Number of entries to return
        timeframe: "all", "week", or "month"
        
    Returns:
        Quality leaderboard
    """
    leaderboard = get_quality_leaderboard(db, limit=limit, timeframe=timeframe)
    
    return {
        "category": "quality_contributors",
        "timeframe": timeframe,
        "entries": leaderboard,
        "total_shown": len(leaderboard),
        "description": "Ranked by average quality score, not quantity"
    }


@router.get("/reward-info")
async def get_reward_info(
    quality_score: float = Query(..., ge=0.0, le=1.0, description="Quality score to check"),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get information about credit rewards for a given quality score.
    
    Args:
        quality_score: Quality score (0.0-1.0)
        
    Returns:
        Reward information
    """
    base_reward = 10
    reward_amount = calculate_quality_reward(quality_score, base_reward)
    
    # Determine tier
    if quality_score >= 0.8:
        tier = "excellent"
        multiplier = 3.0
    elif quality_score >= 0.6:
        tier = "good"
        multiplier = 2.0
    elif quality_score >= 0.4:
        tier = "fair"
        multiplier = 1.0
    else:
        tier = "needs_improvement"
        multiplier = 0.5
    
    return {
        "quality_score": quality_score,
        "tier": tier,
        "base_reward": base_reward,
        "multiplier": multiplier,
        "reward_amount": reward_amount,
        "bonuses": {
            "first_excellent": "50 credits for first excellent entry (0.8+)",
            "excellent_10": "100 credits for 10 excellent entries",
            "excellent_50": "500 credits for 50 excellent entries",
            "verified": "25 credits for verified entry"
        }
    }
