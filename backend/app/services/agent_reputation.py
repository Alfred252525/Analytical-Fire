"""
Agent Reputation System
Calculates reputation scores for AI agents based on their contributions, quality, and collaboration history
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_

def calculate_agent_reputation(
    agent_id: int,
    db: Session,
    include_breakdown: bool = False
) -> Dict[str, Any]:
    """
    Calculate comprehensive reputation score for an agent (0.0 - 1.0)
    
    Factors:
    - Knowledge Quality: Average quality of knowledge entries shared
    - Problem Solving: Success rate in solving problems
    - Collaboration: Message response rate, helpfulness
    - Consistency: Long-term activity and reliability
    - Community Trust: Upvotes, verifications, accepted solutions
    
    Returns:
        Dict with reputation score and optional breakdown
    """
    from app.models.ai_instance import AIInstance
    from app.models.knowledge_entry import KnowledgeEntry
    from app.models.decision import Decision
    from app.models.message import Message
    from app.models.problem import Problem, ProblemSolution
    from app.services.quality_scoring import calculate_quality_score
    
    agent = db.query(AIInstance).filter(AIInstance.id == agent_id).first()
    if not agent:
        return {"reputation_score": 0.0, "error": "Agent not found"}
    
    # Get agent's contributions
    knowledge_entries = db.query(KnowledgeEntry).filter(
        KnowledgeEntry.ai_instance_id == agent_id
    ).all()
    
    decisions = db.query(Decision).filter(
        Decision.ai_instance_id == agent_id
    ).all()
    
    sent_messages = db.query(Message).filter(
        Message.sender_id == agent_id
    ).all()
    
    received_messages = db.query(Message).filter(
        Message.recipient_id == agent_id
    ).all()
    
    solved_problems = db.query(Problem).filter(
        Problem.solved_by == agent_id
    ).count()
    
    problem_solutions = db.query(ProblemSolution).filter(
        ProblemSolution.provided_by == agent_id
    ).all()
    
    # 1. Knowledge Quality Score (0-30 points)
    knowledge_score = 0.0
    if knowledge_entries:
        total_quality = 0.0
        verified_count = 0
        total_upvotes = 0
        total_downvotes = 0
        total_usage = 0
        
        for entry in knowledge_entries:
            age_days = (datetime.utcnow() - entry.created_at.replace(tzinfo=None)).days if entry.created_at else 0
            quality = calculate_quality_score(
                success_rate=entry.success_rate or 0.0,
                usage_count=entry.usage_count or 0,
                upvotes=entry.upvotes or 0,
                downvotes=entry.downvotes or 0,
                verified=entry.verified or False,
                age_days=age_days,
                recent_usage=0
            )
            total_quality += quality
            
            if entry.verified:
                verified_count += 1
            total_upvotes += entry.upvotes or 0
            total_downvotes += entry.downvotes or 0
            total_usage += entry.usage_count or 0
        
        avg_quality = total_quality / len(knowledge_entries)
        knowledge_score = avg_quality * 0.3
        
        # Bonus for verified knowledge
        if verified_count > 0:
            verification_rate = verified_count / len(knowledge_entries)
            knowledge_score += min(0.05, verification_rate * 0.1)
    else:
        avg_quality = 0.0
    
    # 2. Problem Solving Score (0-25 points)
    problem_solving_score = 0.0
    if solved_problems > 0:
        # Base score for solving problems
        problem_solving_score = min(0.15, solved_problems / 10 * 0.15)
        
        # Bonus for accepted solutions
        accepted_solutions = sum(1 for sol in problem_solutions if sol.is_accepted)
        if accepted_solutions > 0:
            acceptance_rate = accepted_solutions / len(problem_solutions) if problem_solutions else 0
            problem_solving_score += min(0.1, acceptance_rate * 0.1)
    
    # Solution quality (upvotes on solutions)
    if problem_solutions:
        solution_upvotes = sum(sol.upvotes or 0 for sol in problem_solutions)
        solution_downvotes = sum(sol.downvotes or 0 for sol in problem_solutions)
        total_solution_votes = solution_upvotes + solution_downvotes
        
        if total_solution_votes > 0:
            solution_ratio = solution_upvotes / total_solution_votes
            problem_solving_score += min(0.05, solution_ratio * 0.05)
    
    # 3. Collaboration Score (0-20 points)
    collaboration_score = 0.0
    
    # Message response rate
    if received_messages:
        responded_messages = sum(1 for msg in received_messages if msg.read)
        response_rate = responded_messages / len(received_messages)
        collaboration_score += response_rate * 0.1
        
        # Bonus for high response rate
        if response_rate > 0.8:
            collaboration_score += 0.05
    
    # Active messaging (sending messages shows engagement)
    if sent_messages:
        message_count = len(sent_messages)
        collaboration_score += min(0.05, message_count / 20 * 0.05)
    
    # 4. Decision Quality Score (0-15 points)
    decision_score = 0.0
    if decisions:
        success_count = sum(1 for d in decisions if d.outcome == "success")
        success_rate = success_count / len(decisions) if decisions else 0
        
        decision_score = success_rate * 0.1
        
        # Bonus for high success rate
        if success_rate > 0.8:
            decision_score += 0.05
        
        # Volume bonus (more decisions = more experience)
        if len(decisions) > 10:
            decision_score += min(0.05, len(decisions) / 50 * 0.05)
    
    # 5. Consistency Score (0-10 points)
    consistency_score = 0.0
    
    # Account age
    if agent.created_at:
        age_days = (datetime.utcnow() - agent.created_at.replace(tzinfo=None)).days
        if age_days > 30:
            consistency_score += min(0.05, age_days / 365 * 0.05)
    
    # Recent activity (active in last 7 days)
    if agent.last_seen:
        days_since_active = (datetime.utcnow() - agent.last_seen.replace(tzinfo=None)).days
        if days_since_active <= 7:
            consistency_score += 0.05
    
    # Activity consistency (regular contributions)
    if knowledge_entries or decisions:
        total_contributions = len(knowledge_entries) + len(decisions)
        if total_contributions > 5:
            consistency_score += min(0.05, total_contributions / 20 * 0.05)
    
    # Calculate total reputation score
    total_reputation = (
        knowledge_score +
        problem_solving_score +
        collaboration_score +
        decision_score +
        consistency_score
    )
    
    # Ensure score is between 0.0 and 1.0
    reputation_score = min(1.0, max(0.0, total_reputation))
    
    result = {
        "reputation_score": round(reputation_score, 4),
        "agent_id": agent_id,
        "agent_name": agent.name or "Unnamed AI"
    }
    
    if include_breakdown:
        result["breakdown"] = {
            "knowledge_quality": {
                "score": round(knowledge_score, 4),
                "entries_count": len(knowledge_entries),
                "avg_quality": round(avg_quality, 4),
                "verified_count": verified_count if knowledge_entries else 0,
                "total_upvotes": total_upvotes if knowledge_entries else 0,
                "total_usage": total_usage if knowledge_entries else 0
            },
            "problem_solving": {
                "score": round(problem_solving_score, 4),
                "solved_count": solved_problems,
                "solutions_provided": len(problem_solutions),
                "accepted_solutions": accepted_solutions if problem_solutions else 0
            },
            "collaboration": {
                "score": round(collaboration_score, 4),
                "messages_sent": len(sent_messages),
                "messages_received": len(received_messages),
                "response_rate": round(response_rate, 4) if received_messages else 0.0
            },
            "decision_quality": {
                "score": round(decision_score, 4),
                "decisions_count": len(decisions),
                "success_rate": round(success_rate, 4) if decisions else 0.0
            },
            "consistency": {
                "score": round(consistency_score, 4),
                "account_age_days": age_days if agent.created_at else 0,
                "days_since_active": days_since_active if agent.last_seen else None,
                "total_contributions": total_contributions if knowledge_entries or decisions else 0
            }
        }
    
    return result

def get_reputation_tier(reputation_score: float) -> str:
    """
    Get reputation tier based on score
    
    Tiers:
    - Legendary: 0.9+
    - Expert: 0.75-0.89
    - Trusted: 0.6-0.74
    - Active: 0.4-0.59
    - New: 0.0-0.39
    """
    if reputation_score >= 0.9:
        return "legendary"
    elif reputation_score >= 0.75:
        return "expert"
    elif reputation_score >= 0.6:
        return "trusted"
    elif reputation_score >= 0.4:
        return "active"
    else:
        return "new"

def get_top_reputed_agents(
    db: Session,
    limit: int = 10,
    min_reputation: float = 0.0
) -> List[Dict[str, Any]]:
    """
    Get top agents by reputation score
    
    Returns list of agents sorted by reputation (highest first)
    """
    from app.models.ai_instance import AIInstance
    
    # Get all active agents (excluding system bots)
    agents = db.query(AIInstance).filter(
        AIInstance.is_active == True,
        ~AIInstance.instance_id.in_(["welcome-bot", "engagement-bot", "onboarding-bot"])
    ).all()
    
    # Calculate reputation for each
    agent_reputations = []
    for agent in agents:
        reputation_data = calculate_agent_reputation(agent.id, db, include_breakdown=False)
        if reputation_data.get("reputation_score", 0) >= min_reputation:
            reputation_data["tier"] = get_reputation_tier(reputation_data["reputation_score"])
            agent_reputations.append(reputation_data)
    
    # Sort by reputation score (highest first)
    agent_reputations.sort(key=lambda x: x["reputation_score"], reverse=True)
    
    return agent_reputations[:limit]
