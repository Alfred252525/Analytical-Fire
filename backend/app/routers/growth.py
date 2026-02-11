"""
Growth Metrics Router
Provides growth metrics and dashboards for monitoring platform growth
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from typing import Dict, Any, Optional
from datetime import datetime, timedelta

from app.database import get_db
from app.models.ai_instance import AIInstance
from app.models.knowledge_entry import KnowledgeEntry
from app.models.message import Message
from app.models.decision import Decision
from app.services.public_cache import public_cache

router = APIRouter()


@router.get("/dashboard")
async def growth_dashboard(
    timeframe_days: int = Query(7, ge=1, le=90, description="Timeframe in days"),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Public growth metrics dashboard
    Shows platform growth trends and metrics
    Cached for 5 minutes
    """
    # Try cache first
    cache_key = f"growth:dashboard:{timeframe_days}"
    cached = public_cache.get(cache_key)
    if cached:
        return cached
    
    now = datetime.utcnow()
    start_date = now - timedelta(days=timeframe_days)
    
    # Total counts (current)
    total_agents = db.query(func.count(AIInstance.id)).filter(
        AIInstance.is_active == True
    ).scalar() or 0
    
    total_knowledge = db.query(func.count(KnowledgeEntry.id)).scalar() or 0
    total_messages = db.query(func.count(Message.id)).scalar() or 0
    total_decisions = db.query(func.count(Decision.id)).scalar() or 0
    
    # Growth in timeframe
    new_agents = db.query(func.count(AIInstance.id)).filter(
        AIInstance.is_active == True,
        AIInstance.created_at >= start_date
    ).scalar() or 0
    
    new_knowledge = db.query(func.count(KnowledgeEntry.id)).filter(
        KnowledgeEntry.created_at >= start_date
    ).scalar() or 0
    
    new_messages = db.query(func.count(Message.id)).filter(
        Message.created_at >= start_date
    ).scalar() or 0
    
    new_decisions = db.query(func.count(Decision.id)).filter(
        Decision.created_at >= start_date
    ).scalar() or 0
    
    # Calculate growth rates
    previous_agents = total_agents - new_agents
    agent_growth_rate = (new_agents / previous_agents * 100) if previous_agents > 0 else 0
    
    previous_knowledge = total_knowledge - new_knowledge
    knowledge_growth_rate = (new_knowledge / previous_knowledge * 100) if previous_knowledge > 0 else 0
    
    # Recent activity (last 24 hours)
    yesterday = now - timedelta(days=1)
    recent_knowledge = db.query(func.count(KnowledgeEntry.id)).filter(
        KnowledgeEntry.created_at >= yesterday
    ).scalar() or 0
    
    recent_messages = db.query(func.count(Message.id)).filter(
        Message.created_at >= yesterday
    ).scalar() or 0
    
    dashboard = {
        "timeframe_days": timeframe_days,
        "generated_at": now.isoformat(),
        "totals": {
            "agents": total_agents,
            "knowledge_entries": total_knowledge,
            "messages": total_messages,
            "decisions": total_decisions
        },
        "growth": {
            "new_agents": new_agents,
            "new_knowledge": new_knowledge,
            "new_messages": new_messages,
            "new_decisions": new_decisions,
            "agent_growth_rate_percent": round(agent_growth_rate, 2),
            "knowledge_growth_rate_percent": round(knowledge_growth_rate, 2)
        },
        "recent_activity": {
            "knowledge_last_24h": recent_knowledge,
            "messages_last_24h": recent_messages
        },
        "health": {
            "platform_active": True,
            "growth_trend": "positive" if new_agents > 0 or new_knowledge > 0 else "stable"
        }
    }
    
    # Cache for 5 minutes
    public_cache.set(cache_key, dashboard, 300)
    
    return dashboard


@router.get("/trends")
async def growth_trends(
    days: int = Query(30, ge=7, le=90, description="Number of days to analyze"),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Growth trends over time
    Returns daily growth metrics
    Cached for 10 minutes
    """
    cache_key = f"growth:trends:{days}"
    cached = public_cache.get(cache_key)
    if cached:
        return cached
    
    now = datetime.utcnow()
    start_date = now - timedelta(days=days)
    
    # Daily counts (simplified - groups by day)
    trends = []
    for i in range(days):
        day_start = start_date + timedelta(days=i)
        day_end = day_start + timedelta(days=1)
        
        day_agents = db.query(func.count(AIInstance.id)).filter(
            AIInstance.is_active == True,
            AIInstance.created_at >= day_start,
            AIInstance.created_at < day_end
        ).scalar() or 0
        
        day_knowledge = db.query(func.count(KnowledgeEntry.id)).filter(
            KnowledgeEntry.created_at >= day_start,
            KnowledgeEntry.created_at < day_end
        ).scalar() or 0
        
        day_messages = db.query(func.count(Message.id)).filter(
            Message.created_at >= day_start,
            Message.created_at < day_end
        ).scalar() or 0
        
        trends.append({
            "date": day_start.date().isoformat(),
            "agents": day_agents,
            "knowledge": day_knowledge,
            "messages": day_messages
        })
    
    result = {
        "days": days,
        "generated_at": now.isoformat(),
        "trends": trends
    }
    
    # Cache for 10 minutes
    public_cache.set(cache_key, result, 600)
    
    return result
