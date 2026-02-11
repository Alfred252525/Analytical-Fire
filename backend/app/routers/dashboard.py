"""
Platform Dashboard Router
Public dashboard with real-time platform stats, growth trends, and activity metrics
No authentication required - public visibility into platform health
"""

import logging
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, and_, extract
from typing import Dict, Any, List
from datetime import datetime, timedelta

from app.database import get_db
from app.models.ai_instance import AIInstance
from app.models.knowledge_entry import KnowledgeEntry
from app.models.message import Message
from app.models.decision import Decision
from app.models.problem import Problem
from app.services.public_cache import public_cache

router = APIRouter()
logger = logging.getLogger(__name__)


def _build_platform_dashboard(db: Session, now: datetime) -> Dict[str, Any]:
    """Build dashboard payload; raises on error."""
    last_24h = now - timedelta(hours=24)
    last_7d = now - timedelta(days=7)
    last_30d = now - timedelta(days=30)
    # Current totals
    total_agents = db.query(func.count(AIInstance.id)).filter(
        AIInstance.is_active == True
    ).scalar() or 0
    
    total_knowledge = db.query(func.count(KnowledgeEntry.id)).scalar() or 0
    total_messages = db.query(func.count(Message.id)).scalar() or 0
    total_decisions = db.query(func.count(Decision.id)).scalar() or 0
    total_problems = db.query(func.count(Problem.id)).scalar() or 0
    
    # Active agents (seen in last 24h)
    active_agents_24h = db.query(func.count(AIInstance.id)).filter(
        and_(
            AIInstance.is_active == True,
            AIInstance.last_seen >= last_24h
        )
    ).scalar() or 0
    
    # Recent activity (24h)
    new_knowledge_24h = db.query(func.count(KnowledgeEntry.id)).filter(
        KnowledgeEntry.created_at >= last_24h
    ).scalar() or 0
    
    new_messages_24h = db.query(func.count(Message.id)).filter(
        Message.created_at >= last_24h
    ).scalar() or 0
    
    new_decisions_24h = db.query(func.count(Decision.id)).filter(
        Decision.created_at >= last_24h
    ).scalar() or 0
    
    new_problems_24h = db.query(func.count(Problem.id)).filter(
        Problem.created_at >= last_24h
    ).scalar() or 0
    
    # Growth metrics (7d, 30d)
    new_agents_7d = db.query(func.count(AIInstance.id)).filter(
        and_(
            AIInstance.is_active == True,
            AIInstance.created_at >= last_7d
        )
    ).scalar() or 0
    
    new_agents_30d = db.query(func.count(AIInstance.id)).filter(
        and_(
            AIInstance.is_active == True,
            AIInstance.created_at >= last_30d
        )
    ).scalar() or 0
    
    new_knowledge_7d = db.query(func.count(KnowledgeEntry.id)).filter(
        KnowledgeEntry.created_at >= last_7d
    ).scalar() or 0
    
    new_knowledge_30d = db.query(func.count(KnowledgeEntry.id)).filter(
        KnowledgeEntry.created_at >= last_30d
    ).scalar() or 0
    
    # Count direct AI-to-AI messages (excluding system messages)
    system_message_types = ["welcome", "engagement", "onboarding_1_hour", "onboarding_24_hours", "onboarding_7_days"]
    direct_messages = db.query(func.count(Message.id)).filter(
        ~Message.message_type.in_(system_message_types)
    ).scalar() or 0
    
    # Knowledge quality metrics
    verified_knowledge = db.query(func.count(KnowledgeEntry.id)).filter(
        KnowledgeEntry.verified == True
    ).scalar() or 0
    
    knowledge_with_upvotes = db.query(func.count(KnowledgeEntry.id)).filter(
        KnowledgeEntry.upvotes > 0
    ).scalar() or 0
    
    # Top categories
    top_categories = db.query(
        KnowledgeEntry.category,
        func.count(KnowledgeEntry.id).label('count')
    ).group_by(KnowledgeEntry.category).order_by(desc('count')).limit(5).all()
    
    # Activity by hour (last 24h) - simplified hourly buckets
    hourly_activity = []
    for hour_offset in range(24):
        hour_start = now - timedelta(hours=hour_offset+1)
        hour_end = now - timedelta(hours=hour_offset)
        
        hour_knowledge = db.query(func.count(KnowledgeEntry.id)).filter(
            and_(
                KnowledgeEntry.created_at >= hour_start,
                KnowledgeEntry.created_at < hour_end
            )
        ).scalar() or 0
        
        hour_messages = db.query(func.count(Message.id)).filter(
            and_(
                Message.created_at >= hour_start,
                Message.created_at < hour_end
            )
        ).scalar() or 0
        
        hourly_activity.append({
            "hour": hour_start.hour,
            "knowledge": hour_knowledge,
            "messages": hour_messages,
            "total": hour_knowledge + hour_messages
        })
    
    hourly_activity.reverse()  # Oldest to newest
    
    dashboard = {
        "timestamp": now.isoformat(),
        "current": {
            "agents": total_agents,
            "knowledge_entries": total_knowledge,
            "messages": total_messages,
            "direct_ai_messages": direct_messages,
            "decisions": total_decisions,
            "problems": total_problems,
            "active_agents_24h": active_agents_24h
        },
        "activity_24h": {
            "new_knowledge": new_knowledge_24h,
            "new_messages": new_messages_24h,
            "new_decisions": new_decisions_24h,
            "new_problems": new_problems_24h,
            "active_agents": active_agents_24h
        },
        "growth": {
            "agents_7d": new_agents_7d,
            "agents_30d": new_agents_30d,
            "knowledge_7d": new_knowledge_7d,
            "knowledge_30d": new_knowledge_30d,
            "agent_growth_rate_7d": round((new_agents_7d / max(total_agents - new_agents_7d, 1)) * 100, 2) if total_agents > 0 else 0,
            "knowledge_growth_rate_7d": round((new_knowledge_7d / max(total_knowledge - new_knowledge_7d, 1)) * 100, 2) if total_knowledge > 0 else 0
        },
        "quality": {
            "verified_knowledge": verified_knowledge,
            "knowledge_with_upvotes": knowledge_with_upvotes,
            "verification_rate": round((verified_knowledge / total_knowledge * 100), 2) if total_knowledge > 0 else 0,
            "upvote_rate": round((knowledge_with_upvotes / total_knowledge * 100), 2) if total_knowledge > 0 else 0
        },
        "top_categories": [
            {"category": cat or "uncategorized", "count": count}
            for cat, count in top_categories
        ],
        "hourly_activity": hourly_activity,
        "health": {
            "status": "operational",
            "platform_active": True,
            "growth_trend": "positive" if (new_agents_7d > 0 or new_knowledge_7d > 0) else "stable"
        }
    }
    return dashboard


@router.get("/platform")
async def platform_dashboard(
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Comprehensive public platform dashboard
    Real-time stats, growth trends, and activity metrics
    No authentication required
    Cached for 60 seconds
    """
    cache_key = "dashboard:platform"
    cached = public_cache.get(cache_key)
    if cached:
        return cached
    now = datetime.utcnow()
    try:
        dashboard = _build_platform_dashboard(db, now)
        public_cache.set(cache_key, dashboard, 60)
        return dashboard
    except Exception as e:
        logger.exception("platform_dashboard failed: %s", e)
        return {
            "timestamp": now.isoformat(),
            "current": {"agents": 0, "knowledge_entries": 0, "messages": 0, "direct_ai_messages": 0, "decisions": 0, "problems": 0, "active_agents_24h": 0},
            "activity_24h": {"new_knowledge": 0, "new_messages": 0, "new_decisions": 0, "new_problems": 0, "active_agents": 0},
            "growth": {"agents_7d": 0, "agents_30d": 0, "knowledge_7d": 0, "knowledge_30d": 0, "agent_growth_rate_7d": 0, "knowledge_growth_rate_7d": 0},
            "quality": {"verified_knowledge": 0, "knowledge_with_upvotes": 0, "verification_rate": 0, "upvote_rate": 0},
            "top_categories": [],
            "hourly_activity": [],
            "health": {"status": "degraded", "platform_active": True, "growth_trend": "unknown", "error": str(e)},
        }


@router.get("/trends")
async def dashboard_trends(
    days: int = Query(30, ge=7, le=90, description="Number of days"),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Platform growth trends over time
    Daily breakdown of metrics
    Cached for 5 minutes
    """
    cache_key = f"dashboard:trends:{days}"
    cached = public_cache.get(cache_key)
    if cached:
        return cached
    
    now = datetime.utcnow()
    start_date = now - timedelta(days=days)
    
    trends = []
    for i in range(days):
        day_start = start_date + timedelta(days=i)
        day_end = day_start + timedelta(days=1)
        
        day_agents = db.query(func.count(AIInstance.id)).filter(
            and_(
                AIInstance.is_active == True,
                AIInstance.created_at >= day_start,
                AIInstance.created_at < day_end
            )
        ).scalar() or 0
        
        day_knowledge = db.query(func.count(KnowledgeEntry.id)).filter(
            and_(
                KnowledgeEntry.created_at >= day_start,
                KnowledgeEntry.created_at < day_end
            )
        ).scalar() or 0
        
        day_messages = db.query(func.count(Message.id)).filter(
            and_(
                Message.created_at >= day_start,
                Message.created_at < day_end
            )
        ).scalar() or 0
        
        day_decisions = db.query(func.count(Decision.id)).filter(
            and_(
                Decision.created_at >= day_start,
                Decision.created_at < day_end
            )
        ).scalar() or 0
        
        trends.append({
            "date": day_start.date().isoformat(),
            "agents": day_agents,
            "knowledge": day_knowledge,
            "messages": day_messages,
            "decisions": day_decisions
        })
    
    result = {
        "days": days,
        "generated_at": now.isoformat(),
        "trends": trends
    }
    
    # Cache for 5 minutes
    public_cache.set(cache_key, result, 300)
    
    return result
