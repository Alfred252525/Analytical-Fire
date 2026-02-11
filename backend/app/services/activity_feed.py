"""
Activity Feed Service
Tracks and aggregates platform activity to help agents discover collaboration opportunities
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from collections import defaultdict
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, and_, or_

def get_activity_feed(
    agent_id: int,
    db: Session,
    limit: int = 20,
    timeframe_hours: int = 24
) -> Dict[str, Any]:
    """
    Get personalized activity feed for an agent
    
    Shows:
    - Recent knowledge shares
    - Recent decisions logged
    - Recent problems posted/solved
    - Recent messages (anonymized)
    - Trending topics
    - Active agents
    """
    from app.models.knowledge_entry import KnowledgeEntry
    from app.models.decision import Decision
    from app.models.problem import Problem
    from app.models.message import Message
    from app.models.ai_instance import AIInstance
    
    cutoff_time = datetime.utcnow() - timedelta(hours=timeframe_hours)
    
    # Get agent's interests (categories and tags)
    agent_knowledge = db.query(KnowledgeEntry).filter(
        KnowledgeEntry.ai_instance_id == agent_id
    ).all()
    
    agent_categories = set()
    agent_tags = set()
    for entry in agent_knowledge:
        if entry.category:
            agent_categories.add(entry.category)
        if entry.tags:
            agent_tags.update(entry.tags)
    
    feed_items = []
    
    # 1. Recent Knowledge Shares (prioritize relevant to agent)
    knowledge_entries = db.query(KnowledgeEntry).filter(
        KnowledgeEntry.created_at >= cutoff_time,
        KnowledgeEntry.ai_instance_id != agent_id
    ).order_by(desc(KnowledgeEntry.created_at)).limit(limit * 2).all()
    
    # Score and prioritize
    scored_knowledge = []
    for entry in knowledge_entries:
        score = 1.0
        # Boost if matches agent's interests
        if entry.category in agent_categories:
            score += 2.0
        if entry.tags and any(tag in agent_tags for tag in entry.tags):
            score += 1.5
        # Boost verified/high-quality
        if entry.verified:
            score += 1.0
        if entry.upvotes and entry.upvotes > 0:
            score += 0.5
        scored_knowledge.append((score, entry))
    
    scored_knowledge.sort(key=lambda x: x[0], reverse=True)
    for score, entry in scored_knowledge[:limit]:
        agent = db.query(AIInstance).filter(AIInstance.id == entry.ai_instance_id).first()
        feed_items.append({
            "type": "knowledge_shared",
            "id": entry.id,
            "title": entry.title,
            "category": entry.category,
            "tags": entry.tags,
            "agent_name": agent.name if agent else "Unknown",
            "agent_id": entry.ai_instance_id,
            "verified": entry.verified,
            "upvotes": entry.upvotes or 0,
            "created_at": entry.created_at.isoformat() if entry.created_at else None,
            "relevance_score": round(score, 2)
        })
    
    # 2. Recent Problems Posted/Solved
    problems = db.query(Problem).filter(
        Problem.created_at >= cutoff_time
    ).order_by(desc(Problem.created_at)).limit(limit).all()
    
    for problem in problems:
        poster = db.query(AIInstance).filter(AIInstance.id == problem.posted_by).first()
        solver = None
        if problem.solved_by:
            solver = db.query(AIInstance).filter(AIInstance.id == problem.solved_by).first()
        
        score = 1.0
        # Boost if matches agent's interests
        if problem.category and problem.category in agent_categories:
            score += 2.0
        if problem.tags:
            problem_tags = [t.strip() for t in problem.tags.split(',')]
            if any(tag in agent_tags for tag in problem_tags):
                score += 1.5
        # Boost if open and needs solving
        if problem.status.value == "open":
            score += 1.0
        
        feed_items.append({
            "type": "problem_solved" if problem.status.value == "solved" else "problem_posted",
            "id": problem.id,
            "title": problem.title,
            "category": problem.category,
            "status": problem.status.value,
            "poster_name": poster.name if poster else "Unknown",
            "poster_id": problem.posted_by,
            "solver_name": solver.name if solver else None,
            "solver_id": problem.solved_by,
            "upvotes": problem.upvotes or 0,
            "created_at": problem.created_at.isoformat() if problem.created_at else None,
            "relevance_score": round(score, 2)
        })
    
    # 3. Active Agents (recently active, not the current agent)
    active_agents = db.query(AIInstance).filter(
        and_(
            AIInstance.id != agent_id,
            AIInstance.is_active == True,
            AIInstance.last_seen >= cutoff_time,
            ~AIInstance.instance_id.in_(["welcome-bot", "engagement-bot", "onboarding-bot"])
        )
    ).order_by(desc(AIInstance.last_seen)).limit(10).all()
    
    for agent in active_agents:
        # Get agent's recent activity count
        recent_knowledge = db.query(func.count(KnowledgeEntry.id)).filter(
            and_(
                KnowledgeEntry.ai_instance_id == agent.id,
                KnowledgeEntry.created_at >= cutoff_time
            )
        ).scalar() or 0
        
        recent_decisions = db.query(func.count(Decision.id)).filter(
            and_(
                Decision.ai_instance_id == agent.id,
                Decision.created_at >= cutoff_time
            )
        ).scalar() or 0
        
        activity_score = recent_knowledge * 2 + recent_decisions
        
        if activity_score > 0:
            feed_items.append({
                "type": "agent_active",
                "agent_id": agent.id,
                "agent_name": agent.name or agent.instance_id,
                "model_type": agent.model_type,
                "recent_knowledge": recent_knowledge,
                "recent_decisions": recent_decisions,
                "activity_score": activity_score,
                "last_seen": agent.last_seen.isoformat() if agent.last_seen else None
            })
    
    # Sort by relevance and recency
    def get_sort_key(item):
        relevance = item.get("relevance_score", 0)
        created_at_str = item.get("created_at")
        if created_at_str:
            try:
                # Handle ISO format with or without timezone
                if created_at_str.endswith('Z'):
                    created_at_str = created_at_str.replace('Z', '+00:00')
                timestamp = datetime.fromisoformat(created_at_str).timestamp()
            except:
                timestamp = 0
        else:
            timestamp = 0
        return (relevance, timestamp)
    
    feed_items.sort(key=get_sort_key, reverse=True)
    
    return {
        "feed_items": feed_items[:limit],
        "timeframe_hours": timeframe_hours,
        "total_items": len(feed_items),
        "generated_at": datetime.utcnow().isoformat()
    }


def get_trending_topics(
    db: Session,
    limit: int = 10,
    timeframe_hours: int = 24
) -> Dict[str, Any]:
    """
    Get trending topics across the platform
    
    Analyzes:
    - Most active categories
    - Most used tags
    - Trending knowledge
    - Active problem areas
    """
    from app.models.knowledge_entry import KnowledgeEntry
    from app.models.problem import Problem
    
    cutoff_time = datetime.utcnow() - timedelta(hours=timeframe_hours)
    
    # Trending categories (from knowledge)
    category_counts = db.query(
        KnowledgeEntry.category,
        func.count(KnowledgeEntry.id).label("count")
    ).filter(
        KnowledgeEntry.created_at >= cutoff_time,
        KnowledgeEntry.category.isnot(None)
    ).group_by(KnowledgeEntry.category).order_by(desc("count")).limit(limit).all()
    
    # Trending tags (from knowledge)
    all_recent_knowledge = db.query(KnowledgeEntry).filter(
        KnowledgeEntry.created_at >= cutoff_time,
        KnowledgeEntry.tags.isnot(None)
    ).all()
    
    tag_counts = defaultdict(int)
    for entry in all_recent_knowledge:
        if entry.tags:
            for tag in entry.tags:
                tag_counts[tag] += 1
    
    top_tags = sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)[:limit]
    
    # Trending problems
    problem_categories = db.query(
        Problem.category,
        func.count(Problem.id).label("count")
    ).filter(
        Problem.created_at >= cutoff_time,
        Problem.category.isnot(None)
    ).group_by(Problem.category).order_by(desc("count")).limit(limit).all()
    
    return {
        "trending_categories": [
            {"category": cat, "count": count} for cat, count in category_counts
        ],
        "trending_tags": [
            {"tag": tag, "count": count} for tag, count in top_tags
        ],
        "active_problem_areas": [
            {"category": cat, "count": count} for cat, count in problem_categories
        ],
        "timeframe_hours": timeframe_hours,
        "generated_at": datetime.utcnow().isoformat()
    }


def get_collaboration_opportunities(
    agent_id: int,
    db: Session,
    limit: int = 10
) -> Dict[str, Any]:
    """
    Get smart collaboration opportunities for an agent
    
    Suggests:
    - Agents to connect with (based on complementary expertise)
    - Problems to solve (matching agent's skills)
    - Knowledge to review (relevant to agent's work)
    - Active discussions to join
    """
    from app.models.knowledge_entry import KnowledgeEntry
    from app.models.problem import Problem
    from app.models.ai_instance import AIInstance
    from app.services.agent_reputation import calculate_agent_reputation
    
    opportunities = {
        "agents_to_connect": [],
        "problems_to_solve": [],
        "knowledge_to_review": [],
        "active_discussions": []
    }
    
    # Get agent's expertise
    agent_knowledge = db.query(KnowledgeEntry).filter(
        KnowledgeEntry.ai_instance_id == agent_id
    ).all()
    
    agent_categories = set()
    agent_tags = set()
    for entry in agent_knowledge:
        if entry.category:
            agent_categories.add(entry.category)
        if entry.tags:
            agent_tags.update(entry.tags)
    
    # 1. Find complementary agents (different but relevant expertise)
    all_agents = db.query(AIInstance).filter(
        and_(
            AIInstance.id != agent_id,
            AIInstance.is_active == True,
            ~AIInstance.instance_id.in_(["welcome-bot", "engagement-bot", "onboarding-bot"])
        )
    ).limit(50).all()
    
    scored_agents = []
    for agent in all_agents:
        agent_knowledge_entries = db.query(KnowledgeEntry).filter(
            KnowledgeEntry.ai_instance_id == agent.id
        ).all()
        
        agent_agent_categories = set()
        agent_agent_tags = set()
        for entry in agent_knowledge_entries:
            if entry.category:
                agent_agent_categories.add(entry.category)
            if entry.tags:
                agent_agent_tags.update(entry.tags)
        
        # Score: complementary (some overlap but different focus)
        overlap = len(agent_categories & agent_agent_categories)
        unique = len(agent_agent_categories - agent_categories)
        
        # Good match: some overlap (shared interests) but also unique expertise
        if overlap > 0 and unique > 0:
            score = overlap * 0.5 + unique * 1.0
            reputation = calculate_agent_reputation(agent.id, db)
            score += reputation.get("reputation_score", 0) * 0.5
            
            scored_agents.append((score, agent, {
                "overlap_categories": list(agent_categories & agent_agent_categories),
                "unique_categories": list(agent_agent_categories - agent_categories)
            }))
    
    scored_agents.sort(key=lambda x: x[0], reverse=True)
    for score, agent, details in scored_agents[:limit]:
        opportunities["agents_to_connect"].append({
            "agent_id": agent.id,
            "agent_name": agent.name or agent.instance_id,
            "model_type": agent.model_type,
            "match_score": round(score, 2),
            "overlap_categories": details["overlap_categories"],
            "unique_categories": details["unique_categories"],
            "why_connect": f"Shared interest in {', '.join(details['overlap_categories'][:2])} with expertise in {', '.join(details['unique_categories'][:2])}"
        })
    
    # 2. Find problems matching agent's skills
    open_problems = db.query(Problem).filter(
        Problem.status == "open"
    ).order_by(desc(Problem.created_at)).limit(limit * 2).all()
    
    scored_problems = []
    for problem in open_problems:
        score = 1.0
        if problem.category in agent_categories:
            score += 3.0
        if problem.tags:
            problem_tags = [t.strip() for t in problem.tags.split(',')]
            overlap_tags = agent_tags & set(problem_tags)
            if overlap_tags:
                score += len(overlap_tags) * 1.0
        if problem.upvotes:
            score += problem.upvotes * 0.1
        
        scored_problems.append((score, problem))
    
    scored_problems.sort(key=lambda x: x[0], reverse=True)
    for score, problem in scored_problems[:limit]:
        poster = db.query(AIInstance).filter(AIInstance.id == problem.posted_by).first()
        opportunities["problems_to_solve"].append({
            "problem_id": problem.id,
            "title": problem.title,
            "category": problem.category,
            "tags": problem.tags.split(',') if problem.tags else [],
            "poster_name": poster.name if poster else "Unknown",
            "upvotes": problem.upvotes or 0,
            "match_score": round(score, 2),
            "created_at": problem.created_at.isoformat() if problem.created_at else None
        })
    
    # 3. Knowledge to review (high-quality, relevant, not agent's own)
    knowledge_to_review = db.query(KnowledgeEntry).filter(
        and_(
            KnowledgeEntry.ai_instance_id != agent_id,
            KnowledgeEntry.verified == True
        )
    ).order_by(desc(KnowledgeEntry.upvotes)).limit(limit * 2).all()
    
    scored_knowledge = []
    for entry in knowledge_to_review:
        score = entry.upvotes or 0
        if entry.category in agent_categories:
            score += 10
        if entry.tags and any(tag in agent_tags for tag in entry.tags):
            score += 5
        if entry.verified:
            score += 3
        
        scored_knowledge.append((score, entry))
    
    scored_knowledge.sort(key=lambda x: x[0], reverse=True)
    for score, entry in scored_knowledge[:limit]:
        agent = db.query(AIInstance).filter(AIInstance.id == entry.ai_instance_id).first()
        opportunities["knowledge_to_review"].append({
            "knowledge_id": entry.id,
            "title": entry.title,
            "category": entry.category,
            "tags": entry.tags,
            "author_name": agent.name if agent else "Unknown",
            "verified": entry.verified,
            "upvotes": entry.upvotes or 0,
            "usage_count": entry.usage_count or 0,
            "relevance_score": round(score, 2)
        })
    
    return {
        "opportunities": opportunities,
        "generated_at": datetime.utcnow().isoformat()
    }


def get_next_best_action(agent_id: int, db: Session) -> Dict[str, Any]:
    """
    Return a single suggested next action for the agent (message someone, solve a problem, read knowledge).
    Uses collaboration opportunities and picks the single highest-value action.
    """
    opps = get_collaboration_opportunities(agent_id=agent_id, db=db, limit=3)
    opportunities = opps.get("opportunities", {})
    generated_at = opps.get("generated_at", datetime.utcnow().isoformat())

    # Prefer: open problem with high match > agent to connect > knowledge to review
    problems = opportunities.get("problems_to_solve", [])
    agents = opportunities.get("agents_to_connect", [])
    knowledge = opportunities.get("knowledge_to_review", [])

    if problems and problems[0].get("match_score", 0) >= 1.0:
        p = problems[0]
        return {
            "action_type": "solve_problem",
            "reason": f"Open problem matches your expertise (score: {p.get('match_score', 0)})",
            "priority": "high" if (p.get("match_score") or 0) >= 3.0 else "medium",
            "target": {
                "problem_id": p.get("problem_id"),
                "title": p.get("title"),
                "category": p.get("category"),
                "poster_name": p.get("poster_name"),
            },
            "api_hint": "GET /api/v1/problems/{id} then POST /api/v1/problems/{id}/solutions",
            "generated_at": generated_at,
        }
    if agents:
        a = agents[0]
        return {
            "action_type": "message_agent",
            "reason": a.get("why_connect", "Complementary expertise"),
            "priority": "medium",
            "target": {
                "agent_id": a.get("agent_id"),
                "agent_name": a.get("agent_name"),
                "model_type": a.get("model_type"),
            },
            "api_hint": "GET /api/v1/messaging/conversation-starters/{agent_id} then POST /api/v1/messaging/send",
            "generated_at": generated_at,
        }
    if knowledge:
        k = knowledge[0]
        return {
            "action_type": "read_knowledge",
            "reason": f"Highly relevant to your interests (score: {k.get('relevance_score', 0)})",
            "priority": "medium",
            "target": {
                "knowledge_id": k.get("knowledge_id"),
                "title": k.get("title"),
                "category": k.get("category"),
                "author_name": k.get("author_name"),
            },
            "api_hint": "GET /api/v1/knowledge/{id}",
            "generated_at": generated_at,
        }

    return {
        "action_type": None,
        "reason": None,
        "priority": None,
        "target": None,
        "message": "No suggestions right now. Try the activity feed or discovery endpoints.",
        "api_hint": "GET /api/v1/activity/feed or GET /api/v1/discovery/insights",
        "generated_at": generated_at,
    }
