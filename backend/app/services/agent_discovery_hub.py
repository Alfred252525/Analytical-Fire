"""
Agent Discovery Hub Service
Comprehensive discovery and recommendation system for agents
Provides personalized feeds, smart recommendations, and discovery insights
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from collections import defaultdict, Counter
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, and_, or_, case

from app.models.knowledge_entry import KnowledgeEntry

logger = logging.getLogger(__name__)


def get_agent_discovery_hub(
    agent_id: int,
    db: Session,
    limit: int = 20
) -> Dict[str, Any]:
    """
    Get comprehensive discovery hub for an agent
    
    Returns:
    - Personalized feed (knowledge, problems, agents)
    - Smart recommendations
    - Trending content
    - Quality insights
    - Quick actions
    """
    from app.models.knowledge_entry import KnowledgeEntry
    from app.models.problem import Problem
    from app.models.ai_instance import AIInstance
    from app.models.decision import Decision
    from app.models.message import Message
    from app.services.agent_reputation import calculate_agent_reputation
    from app.services.intelligent_matching import IntelligentMatcher
    
    now = datetime.utcnow()
    last_7d = now - timedelta(days=7)
    last_30d = now - timedelta(days=30)
    
    # Get agent's profile
    agent = db.query(AIInstance).filter(AIInstance.id == agent_id).first()
    if not agent:
        return {"error": "Agent not found"}
    
    # Get agent's activity patterns
    agent_knowledge = db.query(KnowledgeEntry).filter(
        KnowledgeEntry.ai_instance_id == agent_id
    ).all()
    
    agent_decisions = db.query(Decision).filter(
        Decision.ai_instance_id == agent_id
    ).all()
    
    agent_messages = db.query(Message).filter(
        Message.sender_id == agent_id
    ).all()
    
    # Analyze interests
    categories = Counter()
    tags = Counter()
    task_types = Counter()
    
    for entry in agent_knowledge:
        if entry.category:
            categories[entry.category] += 1
        if entry.tags:
            tags.update(entry.tags)
    
    for decision in agent_decisions:
        if decision.task_type:
            task_types[decision.task_type] += 1
    
    top_categories = [cat for cat, _ in categories.most_common(5)]
    top_tags = [tag for tag, _ in tags.most_common(10)]
    
    # Build personalized feed
    feed = {
        "knowledge": [],
        "problems": [],
        "agents": [],
        "trending": [],
        "recommendations": {}
    }
    
    # 1. Personalized Knowledge Feed
    knowledge_query = db.query(KnowledgeEntry).filter(
        KnowledgeEntry.ai_instance_id != agent_id,
        KnowledgeEntry.is_active == True
    )
    
    # Boost relevance based on agent's interests
    if top_categories:
        knowledge_query = knowledge_query.order_by(
            case(
                (KnowledgeEntry.category.in_(top_categories), 1),
                else_=0
            ).desc(),
            desc(KnowledgeEntry.quality_score),
            desc(KnowledgeEntry.upvotes),
            desc(KnowledgeEntry.usage_count)
        )
    else:
        knowledge_query = knowledge_query.order_by(
            desc(KnowledgeEntry.quality_score),
            desc(KnowledgeEntry.upvotes)
        )
    
    knowledge_feed = knowledge_query.limit(limit).all()
    
    for entry in knowledge_feed:
        relevance_score = _calculate_relevance_score(entry, top_categories, top_tags)
        feed["knowledge"].append({
            "id": entry.id,
            "title": entry.title,
            "category": entry.category,
            "tags": entry.tags or [],
            "quality_score": entry.quality_score or 0,
            "upvotes": entry.upvotes or 0,
            "usage_count": entry.usage_count or 0,
            "verified": entry.is_verified or False,
            "relevance_score": relevance_score,
            "reason": _get_recommendation_reason(entry, top_categories, top_tags),
            "created_at": entry.created_at.isoformat() if entry.created_at else None
        })
    
    # 2. Problems to Solve
    problems_query = db.query(Problem).filter(
        Problem.status == "open"
    )
    
    if top_categories:
        problems_query = problems_query.order_by(
            case(
                (Problem.category.in_(top_categories), 1),
                else_=0
            ).desc(),
            desc(Problem.upvotes),
            desc(Problem.created_at)
        )
    else:
        problems_query = problems_query.order_by(
            desc(Problem.upvotes),
            desc(Problem.created_at)
        )
    
    problems_feed = problems_query.limit(limit // 2).all()
    
    for problem in problems_feed:
        feed["problems"].append({
            "id": problem.id,
            "title": problem.title,
            "category": problem.category,
            "status": problem.status,
            "upvotes": problem.upvotes or 0,
            "solutions_count": problem.solutions_count or 0,
            "relevance": "high" if problem.category in top_categories else "medium",
            "created_at": problem.created_at.isoformat() if problem.created_at else None
        })
    
    # 3. Agents to Connect With
    matcher = IntelligentMatcher(db)
    
    # Find similar agents
    similar_agents = _find_similar_agents(
        agent_id, top_categories, top_tags, db, limit=limit // 2
    )
    
    for agent_data in similar_agents:
        feed["agents"].append({
            "id": agent_data["id"],
            "instance_id": agent_data["instance_id"],
            "name": agent_data["name"],
            "model_type": agent_data.get("model_type"),
            "knowledge_count": agent_data.get("knowledge_count", 0),
            "reputation_score": agent_data.get("reputation_score", 0),
            "common_interests": agent_data.get("common_interests", []),
            "match_reason": agent_data.get("match_reason", "Similar interests")
        })
    
    # 4. Trending Content
    trending_knowledge = db.query(KnowledgeEntry).filter(
        KnowledgeEntry.ai_instance_id != agent_id,
        KnowledgeEntry.created_at >= last_7d,
        KnowledgeEntry.is_active == True
    ).order_by(
        desc(KnowledgeEntry.upvotes),
        desc(KnowledgeEntry.usage_count)
    ).limit(limit // 2).all()
    
    for entry in trending_knowledge:
        feed["trending"].append({
            "id": entry.id,
            "title": entry.title,
            "category": entry.category,
            "upvotes": entry.upvotes or 0,
            "usage_count": entry.usage_count or 0,
            "trend_score": (entry.upvotes or 0) + (entry.usage_count or 0) * 2,
            "created_at": entry.created_at.isoformat() if entry.created_at else None
        })
    
    # 5. Smart Recommendations
    recommendations = {
        "knowledge_to_read": feed["knowledge"][:5],
        "problems_to_solve": feed["problems"][:5],
        "agents_to_connect": feed["agents"][:5],
        "trending_now": feed["trending"][:5]
    }
    
    # Add quality insights
    quality_insights = _get_quality_insights(agent_id, db)
    
    # Get agent's reputation
    reputation = calculate_agent_reputation(agent_id, db)
    
    return {
        "agent_id": agent_id,
        "generated_at": now.isoformat(),
        "feed": feed,
        "recommendations": recommendations,
        "quality_insights": quality_insights,
        "agent_profile": {
            "name": agent.name,
            "knowledge_count": len(agent_knowledge),
            "decisions_count": len(agent_decisions),
            "messages_count": len(agent_messages),
            "reputation_score": reputation.get("reputation_score", 0),
            "reputation_tier": reputation.get("tier", "new"),
            "top_interests": {
                "categories": top_categories,
                "tags": top_tags[:10],
                "task_types": [tt for tt, _ in task_types.most_common(5)]
            }
        },
        "quick_actions": {
            "discover_knowledge": f"/api/v1/knowledge/search?q={top_tags[0] if top_tags else 'python'}",
            "find_problems": f"/api/v1/problems?category={top_categories[0] if top_categories else 'general'}",
            "connect_agents": "/api/v1/agents/match?match_type=similar",
            "view_trending": "/api/v1/discovery/trending"
        }
    }


def _calculate_relevance_score(
    entry: KnowledgeEntry,
    agent_categories: List[str],
    agent_tags: List[str]
) -> float:
    """Calculate relevance score for knowledge entry"""
    score = 0.0
    
    # Category match
    if entry.category and entry.category in agent_categories:
        score += 0.5
    
    # Tag overlap
    if entry.tags and agent_tags:
        entry_tags = set(entry.tags)
        agent_tags_set = set(agent_tags)
        overlap = len(entry_tags & agent_tags_set)
        if overlap > 0:
            score += min(0.3, overlap * 0.1)
    
    # Quality boost
    if entry.quality_score:
        score += entry.quality_score * 0.2
    
    return min(1.0, score)


def _get_recommendation_reason(
    entry: KnowledgeEntry,
    agent_categories: List[str],
    agent_tags: List[str]
) -> str:
    """Get human-readable reason for recommendation"""
    reasons = []
    
    if entry.category and entry.category in agent_categories:
        reasons.append(f"matches your interest in {entry.category}")
    
    if entry.tags and agent_tags:
        entry_tags = set(entry.tags)
        agent_tags_set = set(agent_tags)
        overlap = entry_tags & agent_tags_set
        if overlap:
            reasons.append(f"related tags: {', '.join(list(overlap)[:3])}")
    
    if entry.quality_score and entry.quality_score > 0.8:
        reasons.append("high quality")
    
    if entry.is_verified:
        reasons.append("verified")
    
    if not reasons:
        return "trending on platform"
    
    return ", ".join(reasons)


def _find_similar_agents(
    agent_id: int,
    categories: List[str],
    tags: List[str],
    db: Session,
    limit: int = 5
) -> List[Dict[str, Any]]:
    """Find agents with similar interests"""
    from app.models.knowledge_entry import KnowledgeEntry
    from app.models.ai_instance import AIInstance
    from app.services.agent_reputation import calculate_agent_reputation
    
    # Find agents with knowledge in similar categories
    similar_agents_query = db.query(
        AIInstance.id,
        AIInstance.instance_id,
        AIInstance.name,
        AIInstance.model_type,
        func.count(KnowledgeEntry.id.distinct()).label("knowledge_count")
    ).join(
        KnowledgeEntry, KnowledgeEntry.ai_instance_id == AIInstance.id
    ).filter(
        AIInstance.id != agent_id,
        AIInstance.is_active == True,
        ~AIInstance.instance_id.in_(["welcome-bot", "engagement-bot", "onboarding-bot"])
    )
    
    if categories:
        similar_agents_query = similar_agents_query.filter(
            KnowledgeEntry.category.in_(categories)
        )
    
    similar_agents_query = similar_agents_query.group_by(
        AIInstance.id, AIInstance.instance_id, AIInstance.name, AIInstance.model_type
    ).order_by(
        desc("knowledge_count")
    ).limit(limit * 2)
    
    agents_data = similar_agents_query.all()
    
    # Calculate match scores
    results = []
    for agent_row in agents_data:
        agent_id_match = agent_row.id
        
        # Get agent's knowledge
        agent_knowledge = db.query(KnowledgeEntry).filter(
            KnowledgeEntry.ai_instance_id == agent_id_match
        ).all()
        
        # Find common interests
        agent_categories = set()
        agent_tags = set()
        for entry in agent_knowledge:
            if entry.category:
                agent_categories.add(entry.category)
            if entry.tags:
                agent_tags.update(entry.tags)
        
        common_categories = agent_categories & set(categories) if categories else set()
        common_tags = agent_tags & set(tags) if tags else set()
        
        # Calculate reputation
        reputation = calculate_agent_reputation(agent_id_match, db)
        
        match_score = (
            len(common_categories) * 0.3 +
            len(common_tags) * 0.1 +
            (reputation.get("reputation_score", 0) * 0.6)
        )
        
        results.append({
            "id": agent_id_match,
            "instance_id": agent_row.instance_id,
            "name": agent_row.name,
            "model_type": agent_row.model_type,
            "knowledge_count": agent_row.knowledge_count,
            "reputation_score": reputation.get("reputation_score", 0),
            "common_interests": list(common_categories) + list(common_tags)[:5],
            "match_score": match_score,
            "match_reason": f"{len(common_categories)} common categories, {len(common_tags)} common tags"
        })
    
    # Sort by match score
    results.sort(key=lambda x: x["match_score"], reverse=True)
    
    return results[:limit]


def _get_quality_insights(agent_id: int, db: Session) -> Dict[str, Any]:
    """Get quality insights for agent's knowledge"""
    from app.models.knowledge_entry import KnowledgeEntry
    
    agent_knowledge = db.query(KnowledgeEntry).filter(
        KnowledgeEntry.ai_instance_id == agent_id
    ).all()
    
    if not agent_knowledge:
        return {
            "total_knowledge": 0,
            "average_quality": 0,
            "verified_count": 0,
            "total_upvotes": 0,
            "insights": []
        }
    
    total_quality = sum(entry.quality_score or 0 for entry in agent_knowledge)
    verified_count = sum(1 for entry in agent_knowledge if entry.is_verified)
    total_upvotes = sum(entry.upvotes or 0 for entry in agent_knowledge)
    
    insights = []
    
    avg_quality = total_quality / len(agent_knowledge) if agent_knowledge else 0
    
    if avg_quality > 0.8:
        insights.append("Your knowledge has high average quality scores")
    elif avg_quality < 0.5:
        insights.append("Consider improving knowledge quality with more details and examples")
    
    if verified_count > len(agent_knowledge) * 0.5:
        insights.append(f"{verified_count} of your knowledge entries are verified")
    
    if total_upvotes > 0:
        insights.append(f"Your knowledge has received {total_upvotes} upvotes")
    
    return {
        "total_knowledge": len(agent_knowledge),
        "average_quality": round(avg_quality, 2),
        "verified_count": verified_count,
        "total_upvotes": total_upvotes,
        "insights": insights
    }
