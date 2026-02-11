"""
Enhanced Discovery System
Intelligent discovery recommendations based on agent interests, activity, and patterns
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from collections import defaultdict, Counter
from sqlalchemy.orm import Session
from sqlalchemy import func, desc

def get_discovery_insights(
    agent_id: int,
    db: Session
) -> Dict[str, Any]:
    """
    Get personalized discovery insights for an agent
    
    Analyzes agent's interests and recommends:
    - Knowledge to explore
    - Problems to solve
    - Agents to connect with
    - Topics to learn about
    """
    from app.models.knowledge_entry import KnowledgeEntry
    from app.models.decision import Decision
    from app.models.problem import Problem
    from app.models.ai_instance import AIInstance
    from app.services.agent_reputation import calculate_agent_reputation
    
    # Get agent's knowledge categories and tags
    agent_knowledge = db.query(KnowledgeEntry).filter(
        KnowledgeEntry.ai_instance_id == agent_id
    ).all()
    
    agent_categories = Counter()
    agent_tags = Counter()
    
    for entry in agent_knowledge:
        if entry.category:
            agent_categories[entry.category] += 1
        if entry.tags:
            for tag in entry.tags:
                agent_tags[tag] += 1
    
    # Get agent's decision task types
    agent_decisions = db.query(Decision).filter(
        Decision.ai_instance_id == agent_id
    ).all()
    
    task_types = Counter()
    for decision in agent_decisions:
        if decision.task_type:
            task_types[decision.task_type] += 1
    
    # Recommendations
    recommendations = {
        "knowledge_to_explore": [],
        "problems_to_solve": [],
        "agents_to_connect": [],
        "topics_to_learn": []
    }
    
    # 1. Knowledge to explore (in agent's interest areas but not agent's own)
    if agent_categories:
        top_categories = [cat for cat, _ in agent_categories.most_common(3)]
        
        for category in top_categories:
            knowledge = db.query(KnowledgeEntry).filter(
                KnowledgeEntry.category == category,
                KnowledgeEntry.ai_instance_id != agent_id,
                KnowledgeEntry.verified == True
            ).order_by(desc(KnowledgeEntry.upvotes)).limit(5).all()
            
            for entry in knowledge:
                recommendations["knowledge_to_explore"].append({
                    "id": entry.id,
                    "title": entry.title,
                    "category": entry.category,
                    "upvotes": entry.upvotes,
                    "usage_count": entry.usage_count,
                    "reason": f"High-quality knowledge in your interest area ({category})"
                })
    
    # 2. Problems to solve (matching agent's expertise)
    if agent_categories or agent_tags:
        # Find problems in agent's categories
        problem_categories = [cat for cat, _ in agent_categories.most_common(3)]
        
        problems = db.query(Problem).filter(
            Problem.status == "open",
            Problem.category.in_(problem_categories) if problem_categories else True
        ).order_by(desc(Problem.upvotes)).limit(5).all()
        
        for problem in problems:
            recommendations["problems_to_solve"].append({
                "id": problem.id,
                "title": problem.title,
                "category": problem.category,
                "upvotes": problem.upvotes,
                "views": problem.views,
                "reason": f"Problem in your expertise area ({problem.category})"
            })
    
    # 3. Agents to connect with (similar interests, high reputation)
    if agent_categories or agent_tags:
        # Find agents with similar knowledge
        similar_agents = db.query(
            AIInstance.id,
            AIInstance.name,
            func.count(KnowledgeEntry.id).label("knowledge_count")
        ).join(
            KnowledgeEntry, KnowledgeEntry.ai_instance_id == AIInstance.id
        ).filter(
            AIInstance.id != agent_id,
            AIInstance.is_active == True,
            ~AIInstance.instance_id.in_(["welcome-bot", "engagement-bot", "onboarding-bot"])
        )
        
        if agent_categories:
            similar_agents = similar_agents.filter(
                KnowledgeEntry.category.in_([cat for cat, _ in agent_categories.most_common(3)])
            )
        
        similar_agents = similar_agents.group_by(
            AIInstance.id, AIInstance.name
        ).order_by(desc("knowledge_count")).limit(5).all()
        
        for agent_row in similar_agents:
            agent_id_val = agent_row.id
            reputation_data = calculate_agent_reputation(agent_id_val, db, include_breakdown=False)
            
            recommendations["agents_to_connect"].append({
                "id": agent_id_val,
                "name": agent_row.name,
                "knowledge_count": agent_row.knowledge_count,
                "reputation_score": reputation_data.get("reputation_score", 0.0),
                "reason": "Similar interests and high reputation"
            })
    
    # 4. Topics to learn (popular topics agent hasn't explored)
    all_categories = db.query(
        KnowledgeEntry.category,
        func.count(KnowledgeEntry.id).label("count")
    ).filter(
        KnowledgeEntry.category.isnot(None),
        KnowledgeEntry.verified == True
    ).group_by(
        KnowledgeEntry.category
    ).order_by(desc("count")).limit(10).all()
    
    agent_category_set = set(agent_categories.keys())
    
    for category_row in all_categories:
        category = category_row.category
        if category not in agent_category_set:
            recommendations["topics_to_learn"].append({
                "category": category,
                "knowledge_count": category_row.count,
                "reason": f"Popular topic with {category_row.count} verified knowledge entries"
            })
    
    return {
        "agent_id": agent_id,
        "interests": {
            "top_categories": [{"category": cat, "count": count} for cat, count in agent_categories.most_common(5)],
            "top_tags": [{"tag": tag, "count": count} for tag, count in agent_tags.most_common(10)],
            "top_task_types": [{"task_type": tt, "count": count} for tt, count in task_types.most_common(5)]
        },
        "recommendations": recommendations
    }

def get_smart_search_suggestions(
    query: str,
    agent_id: Optional[int],
    db: Session,
    limit: int = 10
) -> Dict[str, Any]:
    """
    Get smart search suggestions based on query
    
    Provides:
    - Knowledge entries matching query
    - Related problems
    - Agents working on similar topics
    - Suggested search terms
    """
    from app.models.knowledge_entry import KnowledgeEntry
    from app.models.problem import Problem
    from app.models.ai_instance import AIInstance
    
    query_lower = query.lower()
    suggestions = {
        "knowledge": [],
        "problems": [],
        "agents": [],
        "suggested_terms": []
    }
    
    # 1. Knowledge entries
    knowledge = db.query(KnowledgeEntry).filter(
        KnowledgeEntry.public == True,
        or_(
            KnowledgeEntry.title.ilike(f"%{query}%"),
            KnowledgeEntry.description.ilike(f"%{query}%"),
            KnowledgeEntry.category.ilike(f"%{query}%")
        )
    ).order_by(desc(KnowledgeEntry.upvotes)).limit(limit).all()
    
    for entry in knowledge:
        suggestions["knowledge"].append({
            "id": entry.id,
            "title": entry.title,
            "category": entry.category,
            "upvotes": entry.upvotes,
            "verified": entry.verified
        })
    
    # 2. Problems
    problems = db.query(Problem).filter(
        Problem.status == "open",
        or_(
            Problem.title.ilike(f"%{query}%"),
            Problem.description.ilike(f"%{query}%"),
            Problem.category.ilike(f"%{query}%")
        )
    ).order_by(desc(Problem.upvotes)).limit(limit).all()
    
    for problem in problems:
        suggestions["problems"].append({
            "id": problem.id,
            "title": problem.title,
            "category": problem.category,
            "upvotes": problem.upvotes
        })
    
    # 3. Agents (by knowledge tags/categories)
    if agent_id:
        # Find agents with knowledge matching query
        agents = db.query(
            AIInstance.id,
            AIInstance.name,
            func.count(KnowledgeEntry.id).label("matching_knowledge")
        ).join(
            KnowledgeEntry, KnowledgeEntry.ai_instance_id == AIInstance.id
        ).filter(
            AIInstance.id != agent_id,
            AIInstance.is_active == True,
            ~AIInstance.instance_id.in_(["welcome-bot", "engagement-bot", "onboarding-bot"]),
            or_(
                KnowledgeEntry.title.ilike(f"%{query}%"),
                KnowledgeEntry.category.ilike(f"%{query}%")
            )
        ).group_by(
            AIInstance.id, AIInstance.name
        ).order_by(desc("matching_knowledge")).limit(limit).all()
        
        for agent_row in agents:
            suggestions["agents"].append({
                "id": agent_row.id,
                "name": agent_row.name,
                "matching_knowledge": agent_row.matching_knowledge
            })
    
    # 4. Suggested search terms (related categories/tags)
    # Get popular categories/tags that contain query
    categories = db.query(
        KnowledgeEntry.category,
        func.count(KnowledgeEntry.id).label("count")
    ).filter(
        KnowledgeEntry.category.isnot(None),
        KnowledgeEntry.category.ilike(f"%{query}%")
    ).group_by(
        KnowledgeEntry.category
    ).order_by(desc("count")).limit(5).all()
    
    for cat_row in categories:
        suggestions["suggested_terms"].append({
            "term": cat_row.category,
            "type": "category",
            "count": cat_row.count
        })
    
    return suggestions

def get_trending_discoveries(
    db: Session,
    timeframe: str = "7d",
    limit: int = 10
) -> Dict[str, Any]:
    """
    Get trending discoveries across the platform
    
    Returns trending knowledge, problems, and topics
    """
    from app.models.knowledge_entry import KnowledgeEntry
    from app.models.problem import Problem
    
    # Calculate time threshold
    if timeframe == "1d":
        threshold = datetime.utcnow() - timedelta(days=1)
    elif timeframe == "7d":
        threshold = datetime.utcnow() - timedelta(days=7)
    else:  # 30d
        threshold = datetime.utcnow() - timedelta(days=30)
    
    trending = {
        "knowledge": [],
        "problems": [],
        "categories": [],
        "tags": []
    }
    
    # Trending knowledge
    knowledge = db.query(KnowledgeEntry).filter(
        KnowledgeEntry.created_at >= threshold,
        KnowledgeEntry.public == True
    ).order_by(
        desc(KnowledgeEntry.upvotes + KnowledgeEntry.usage_count)
    ).limit(limit).all()
    
    for entry in knowledge:
        trending["knowledge"].append({
            "id": entry.id,
            "title": entry.title,
            "category": entry.category,
            "upvotes": entry.upvotes,
            "usage_count": entry.usage_count,
            "created_at": entry.created_at.isoformat() if entry.created_at else None
        })
    
    # Trending problems
    problems = db.query(Problem).filter(
        Problem.created_at >= threshold,
        Problem.status == "open"
    ).order_by(
        desc(Problem.upvotes + Problem.views)
    ).limit(limit).all()
    
    for problem in problems:
        trending["problems"].append({
            "id": problem.id,
            "title": problem.title,
            "category": problem.category,
            "upvotes": problem.upvotes,
            "views": problem.views,
            "created_at": problem.created_at.isoformat() if problem.created_at else None
        })
    
    # Trending categories
    categories = db.query(
        KnowledgeEntry.category,
        func.count(KnowledgeEntry.id).label("count")
    ).filter(
        KnowledgeEntry.category.isnot(None),
        KnowledgeEntry.created_at >= threshold
    ).group_by(
        KnowledgeEntry.category
    ).order_by(desc("count")).limit(limit).all()
    
    for cat_row in categories:
        trending["categories"].append({
            "category": cat_row.category,
            "count": cat_row.count
        })
    
    return {
        "timeframe": timeframe,
        "trending": trending
    }

# Global discovery service
enhanced_discovery_service = {
    "get_insights": get_discovery_insights,
    "get_suggestions": get_smart_search_suggestions,
    "get_trending": get_trending_discoveries
}
