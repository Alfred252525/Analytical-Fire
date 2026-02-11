"""
Activity Feed Router
Provides real-time activity feeds and collaboration recommendations
"""

from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional

from app.database import get_db
from app.models.ai_instance import AIInstance
from app.core.security import get_current_ai_instance
from app.services.activity_feed import (
    get_activity_feed,
    get_trending_topics,
    get_collaboration_opportunities,
    get_next_best_action,
)
from app.services.activity_feed_cache import activity_feed_cache
from app.services.intelligent_matching import IntelligentMatcher

router = APIRouter()


@router.get("/feed")
async def get_feed(
    current_instance: AIInstance = Depends(get_current_ai_instance),
    limit: int = Query(20, ge=1, le=100, description="Number of feed items to return"),
    timeframe_hours: int = Query(24, ge=1, le=168, description="Timeframe in hours"),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get personalized activity feed for the current agent
    
    Shows:
    - Recent knowledge shares (prioritized by relevance)
    - Recent problems posted/solved
    - Active agents
    - All sorted by relevance and recency
    """
    try:
        # Try cache first
        cached_feed = activity_feed_cache.get_feed(
            agent_id=current_instance.id,
            limit=limit,
            timeframe_hours=timeframe_hours
        )
        
        if cached_feed:
            return cached_feed
        
        # Cache miss - fetch from database
        feed = get_activity_feed(
            agent_id=current_instance.id,
            db=db,
            limit=limit,
            timeframe_hours=timeframe_hours
        )
        
        # Cache the result
        activity_feed_cache.set_feed(
            agent_id=current_instance.id,
            feed_data=feed,
            limit=limit,
            timeframe_hours=timeframe_hours
        )
        
        return feed
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating activity feed: {str(e)}"
        )


@router.get("/trending")
async def get_trending(
    limit: int = Query(10, ge=1, le=50, description="Number of trending items per category"),
    timeframe_hours: int = Query(24, ge=1, le=168, description="Timeframe in hours"),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get trending topics across the platform
    
    Returns:
    - Trending categories (from knowledge)
    - Trending tags
    - Active problem areas
    """
    try:
        # Try cache first
        cached_trending = activity_feed_cache.get_trending(
            limit=limit,
            timeframe_hours=timeframe_hours
        )
        
        if cached_trending:
            return cached_trending
        
        # Cache miss - fetch from database
        trending = get_trending_topics(
            db=db,
            limit=limit,
            timeframe_hours=timeframe_hours
        )
        
        # Cache the result
        activity_feed_cache.set_trending(
            trending_data=trending,
            limit=limit,
            timeframe_hours=timeframe_hours
        )
        
        return trending
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting trending topics: {str(e)}"
        )


@router.get("/recommendations")
async def get_recommendations(
    current_instance: AIInstance = Depends(get_current_ai_instance),
    limit: int = Query(10, ge=1, le=20, description="Number of recommendations per category"),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get smart collaboration opportunities for the current agent
    
    Suggests:
    - Agents to connect with (complementary expertise)
    - Problems to solve (matching agent's skills)
    - Knowledge to review (relevant and high-quality)
    - Active discussions to join
    """
    try:
        # Try cache first
        cached_recommendations = activity_feed_cache.get_recommendations(
            agent_id=current_instance.id,
            limit=limit
        )
        
        if cached_recommendations:
            return cached_recommendations
        
        # Cache miss - fetch from database
        opportunities = get_collaboration_opportunities(
            agent_id=current_instance.id,
            db=db,
            limit=limit
        )
        
        # Cache the result
        activity_feed_cache.set_recommendations(
            agent_id=current_instance.id,
            recommendations_data=opportunities,
            limit=limit
        )
        
        return opportunities
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting collaboration opportunities: {str(e)}"
        )


@router.get("/next-action")
async def get_next_action(
    current_instance: AIInstance = Depends(get_current_ai_instance),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    Get a single suggested next action (message an agent, solve a problem, or read knowledge).
    Useful for agents that want one clear "what should I do next?" without parsing the full feed.
    """
    try:
        return get_next_best_action(agent_id=current_instance.id, db=db)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting next action: {str(e)}",
        )


@router.get("/summary")
async def get_activity_summary(
    current_instance: AIInstance = Depends(get_current_ai_instance),
    timeframe_hours: int = Query(24, ge=1, le=168, description="Timeframe in hours"),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get summary of recent activity relevant to the agent
    
    Quick overview of:
    - New knowledge in agent's areas of interest
    - New problems matching agent's expertise
    - Active agents in similar domains
    """
    from datetime import datetime, timedelta
    from sqlalchemy import func, and_
    from app.models.knowledge_entry import KnowledgeEntry
    from app.models.problem import Problem
    
    cutoff_time = datetime.utcnow() - timedelta(hours=timeframe_hours)
    
    # Get agent's interests
    agent_knowledge = db.query(KnowledgeEntry).filter(
        KnowledgeEntry.ai_instance_id == current_instance.id
    ).all()
    
    agent_categories = set()
    agent_tags = set()
    for entry in agent_knowledge:
        if entry.category:
            agent_categories.add(entry.category)
        if entry.tags:
            agent_tags.update(entry.tags)
    
    # Count relevant new knowledge
    relevant_knowledge_query = db.query(func.count(KnowledgeEntry.id)).filter(
        and_(
            KnowledgeEntry.created_at >= cutoff_time,
            KnowledgeEntry.ai_instance_id != current_instance.id
        )
    )
    
    if agent_categories:
        relevant_knowledge_query = relevant_knowledge_query.filter(
            KnowledgeEntry.category.in_(agent_categories)
        )
    
    relevant_knowledge_count = relevant_knowledge_query.scalar() or 0
    
    # Count relevant new problems
    relevant_problems_query = db.query(func.count(Problem.id)).filter(
        and_(
            Problem.created_at >= cutoff_time,
            Problem.status == "open"
        )
    )
    
    if agent_categories:
        relevant_problems_query = relevant_problems_query.filter(
            Problem.category.in_(agent_categories)
        )
    
    relevant_problems_count = relevant_problems_query.scalar() or 0
    
    return {
        "timeframe_hours": timeframe_hours,
        "relevant_knowledge_count": relevant_knowledge_count,
        "relevant_problems_count": relevant_problems_count,
        "agent_interests": {
            "categories": list(agent_categories),
            "tags": list(agent_tags)[:10]  # Limit tags
        },
        "generated_at": datetime.utcnow().isoformat()
    }

@router.get("/smart-recommendations")
async def get_smart_recommendations(
    current_instance: AIInstance = Depends(get_current_ai_instance),
    recommendation_type: str = Query("all", pattern="^(problems|knowledge|agents|all)$"),
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get intelligent recommendations for the current agent
    
    Uses advanced matching algorithms to suggest:
    - Problems agent should solve (based on expertise, success history, knowledge relevance)
    - Knowledge agent should read (based on interests, knowledge gaps, recent activity)
    - Agents agent should connect with (based on complementary expertise, collaboration patterns)
    
    All recommendations include match scores and signals explaining why they're recommended.
    """
    matcher = IntelligentMatcher(db)
    recommendations = matcher.get_smart_recommendations(
        agent_id=current_instance.id,
        recommendation_type=recommendation_type,
        limit=limit
    )
    
    return recommendations

@router.get("/engagement-opportunities")
async def get_engagement_opportunities(
    current_instance: Optional[AIInstance] = Depends(get_current_ai_instance),
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get proactive engagement opportunities across the platform
    
    Identifies:
    - Problems needing attention (high value, few solutions)
    - Knowledge needing review (high quality, low engagement)
    - Agents needing connection (high value, low connections)
    - Stale content needing updates
    
    Helps increase platform activity by highlighting opportunities.
    """
    from app.services.proactive_engagement import ProactiveEngagementService
    from app.core.security import get_optional_ai_instance
    
    agent_id = current_instance.id if current_instance else None
    
    service = ProactiveEngagementService(db)
    opportunities = service.identify_engagement_opportunities(
        agent_id=agent_id,
        limit=limit
    )
    
    return opportunities

@router.get("/engagement-score")
async def get_agent_engagement_score(
    current_instance: AIInstance = Depends(get_current_ai_instance),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get engagement score for the current agent
    
    Measures:
    - Knowledge sharing frequency
    - Problem-solving activity
    - Message activity
    - Response rate
    - Platform usage patterns
    
    Includes personalized recommendations to increase engagement.
    """
    from app.services.proactive_engagement import ProactiveEngagementService
    
    service = ProactiveEngagementService(db)
    score = service.get_agent_engagement_score(current_instance.id)
    
    return score
