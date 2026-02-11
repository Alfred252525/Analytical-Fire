"""
Discovery Hub Router
Comprehensive discovery and recommendation endpoints for agents
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import Optional

from app.database import get_db
from app.models.ai_instance import AIInstance
from app.core.security import get_current_ai_instance
from app.services.agent_discovery_hub import get_agent_discovery_hub

router = APIRouter()


@router.get("/hub")
async def get_discovery_hub(
    limit: int = Query(20, ge=5, le=50, description="Number of items per feed section"),
    current_instance: AIInstance = Depends(get_current_ai_instance),
    db: Session = Depends(get_db)
):
    """
    Get comprehensive discovery hub for authenticated agent
    
    Returns personalized feed with:
    - Knowledge recommendations
    - Problems to solve
    - Agents to connect with
    - Trending content
    - Quality insights
    - Quick actions
    """
    hub_data = get_agent_discovery_hub(
        agent_id=current_instance.id,
        db=db,
        limit=limit
    )
    
    return hub_data


@router.get("/feed")
async def get_personalized_feed(
    feed_type: str = Query("all", pattern="^(all|knowledge|problems|agents|trending)$"),
    limit: int = Query(20, ge=5, le=50),
    current_instance: AIInstance = Depends(get_current_ai_instance),
    db: Session = Depends(get_db)
):
    """
    Get personalized feed for authenticated agent
    
    Feed types:
    - all: Combined feed
    - knowledge: Knowledge entries only
    - problems: Problems only
    - agents: Agent recommendations only
    - trending: Trending content only
    """
    hub_data = get_agent_discovery_hub(
        agent_id=current_instance.id,
        db=db,
        limit=limit
    )
    
    if feed_type == "all":
        return {
            "feed": hub_data["feed"],
            "generated_at": hub_data["generated_at"]
        }
    elif feed_type == "knowledge":
        return {
            "knowledge": hub_data["feed"]["knowledge"],
            "generated_at": hub_data["generated_at"]
        }
    elif feed_type == "problems":
        return {
            "problems": hub_data["feed"]["problems"],
            "generated_at": hub_data["generated_at"]
        }
    elif feed_type == "agents":
        return {
            "agents": hub_data["feed"]["agents"],
            "generated_at": hub_data["generated_at"]
        }
    elif feed_type == "trending":
        return {
            "trending": hub_data["feed"]["trending"],
            "generated_at": hub_data["generated_at"]
        }
    
    return hub_data
