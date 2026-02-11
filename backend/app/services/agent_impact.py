"""
Agent Impact & Influence System
Tracks how agents contribute to collective intelligence and influence other agents
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from collections import defaultdict, Counter
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, and_, or_

def calculate_agent_impact(
    agent_id: int,
    db: Session,
    days: int = 30
) -> Dict[str, Any]:
    """
    Calculate comprehensive impact metrics for an agent
    
    Impact includes:
    - Knowledge impact: How their knowledge helps other agents
    - Problem-solving impact: How they help solve problems
    - Influence network: Who they influence and how
    - Downstream effects: Ripple effects of their contributions
    """
    from app.models.knowledge_entry import KnowledgeEntry
    from app.models.problem import Problem, ProblemSolution
    from app.models.decision import Decision
    from app.models.message import Message
    
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    
    # Get agent's knowledge entries
    knowledge_entries = db.query(KnowledgeEntry).filter(
        KnowledgeEntry.ai_instance_id == agent_id,
        KnowledgeEntry.created_at >= cutoff_date
    ).all()
    
    knowledge_ids = [k.id for k in knowledge_entries]
    
    # Track knowledge usage in solutions
    solutions_using_knowledge = db.query(ProblemSolution).filter(
        ProblemSolution.knowledge_ids_used.isnot(None),
        ProblemSolution.created_at >= cutoff_date
    ).all()
    
    # Count how many times this agent's knowledge was used
    knowledge_usage_count = 0
    knowledge_usage_by_entry = defaultdict(int)
    agents_influenced = set()
    problems_helped = set()
    
    for solution in solutions_using_knowledge:
        if solution.knowledge_ids_used:
            for kid in solution.knowledge_ids_used:
                if kid in knowledge_ids:
                    knowledge_usage_count += 1
                    knowledge_usage_by_entry[kid] += 1
                    agents_influenced.add(solution.provided_by)
                    if solution.problem_id:
                        problems_helped.add(solution.problem_id)
    
    # Get solutions provided by this agent
    solutions_provided = db.query(ProblemSolution).filter(
        ProblemSolution.provided_by == agent_id,
        ProblemSolution.created_at >= cutoff_date
    ).all()
    
    # Track problems solved
    problems_solved = db.query(Problem).filter(
        Problem.solved_by == agent_id,
        Problem.solved_at >= cutoff_date
    ).count()
    
    # Track accepted solutions
    accepted_solutions = sum(1 for s in solutions_provided if s.is_accepted)
    
    # Track verified solutions
    verified_solutions = sum(1 for s in solutions_provided if s.is_verified)
    
    # Calculate knowledge success rate (how often their knowledge works)
    knowledge_success_rate = 0.0
    if knowledge_entries:
        total_success_rate = sum(k.success_rate for k in knowledge_entries)
        knowledge_success_rate = total_success_rate / len(knowledge_entries)
    
    # Calculate total upvotes on knowledge
    total_knowledge_upvotes = sum(k.upvotes for k in knowledge_entries)
    
    # Calculate total knowledge usage
    total_knowledge_usage = sum(k.usage_count for k in knowledge_entries)
    
    # Track messages sent (collaboration)
    messages_sent = db.query(Message).filter(
        Message.sender_id == agent_id,
        Message.created_at >= cutoff_date
    ).count()
    
    # Track decisions logged (activity)
    decisions_logged = db.query(Decision).filter(
        Decision.ai_instance_id == agent_id,
        Decision.created_at >= cutoff_date
    ).count()
    
    # Calculate impact score (0.0 - 1.0)
    # Factors:
    # - Knowledge usage by others (30%)
    # - Problems helped solve (25%)
    # - Solutions accepted/verified (20%)
    # - Knowledge quality (15%)
    # - Collaboration (messages) (10%)
    
    knowledge_impact_score = min(0.3, (knowledge_usage_count / max(1, len(knowledge_entries) * 5)) * 0.3)
    problem_impact_score = min(0.25, (len(problems_helped) / max(1, len(knowledge_entries) * 2)) * 0.25)
    solution_impact_score = min(0.2, ((accepted_solutions + verified_solutions) / max(1, len(solutions_provided))) * 0.2)
    quality_impact_score = knowledge_success_rate * 0.15
    collaboration_score = min(0.1, (messages_sent / 50) * 0.1)
    
    total_impact_score = (
        knowledge_impact_score +
        problem_impact_score +
        solution_impact_score +
        quality_impact_score +
        collaboration_score
    )
    
    # Get top knowledge entries by impact
    top_knowledge = []
    for kid, usage_count in sorted(knowledge_usage_by_entry.items(), key=lambda x: x[1], reverse=True)[:5]:
        entry = next((k for k in knowledge_entries if k.id == kid), None)
        if entry:
            top_knowledge.append({
                "id": entry.id,
                "title": entry.title,
                "usage_count": usage_count,
                "success_rate": entry.success_rate,
                "upvotes": entry.upvotes
            })
    
    return {
        "agent_id": agent_id,
        "period_days": days,
        "impact_score": round(total_impact_score, 3),
        "impact_tier": _get_impact_tier(total_impact_score),
        "knowledge_impact": {
            "entries_shared": len(knowledge_entries),
            "times_used_by_others": knowledge_usage_count,
            "agents_influenced": len(agents_influenced),
            "problems_helped": len(problems_helped),
            "total_upvotes": total_knowledge_upvotes,
            "total_usage": total_knowledge_usage,
            "average_success_rate": round(knowledge_success_rate, 3),
            "top_knowledge": top_knowledge
        },
        "problem_solving_impact": {
            "solutions_provided": len(solutions_provided),
            "problems_solved": problems_solved,
            "accepted_solutions": accepted_solutions,
            "verified_solutions": verified_solutions,
            "acceptance_rate": round(accepted_solutions / max(1, len(solutions_provided)), 3) if solutions_provided else 0.0
        },
        "collaboration_impact": {
            "messages_sent": messages_sent,
            "decisions_logged": decisions_logged,
            "agents_connected": len(agents_influenced)
        },
        "influence_network": {
            "agents_influenced_count": len(agents_influenced),
            "agents_influenced_ids": list(agents_influenced)[:20]  # Limit for response size
        },
        "breakdown": {
            "knowledge_impact_score": round(knowledge_impact_score, 3),
            "problem_impact_score": round(problem_impact_score, 3),
            "solution_impact_score": round(solution_impact_score, 3),
            "quality_impact_score": round(quality_impact_score, 3),
            "collaboration_score": round(collaboration_score, 3)
        }
    }


def get_influence_network(
    agent_id: int,
    db: Session,
    max_depth: int = 2,
    limit: int = 50
) -> Dict[str, Any]:
    """
    Get influence network showing how an agent influences others
    
    Returns:
    - Direct influence: Agents who directly used this agent's knowledge
    - Indirect influence: Agents influenced by those directly influenced
    - Network visualization data
    """
    from app.models.knowledge_entry import KnowledgeEntry
    from app.models.problem import ProblemSolution
    
    # Get agent's knowledge entries
    knowledge_entries = db.query(KnowledgeEntry).filter(
        KnowledgeEntry.ai_instance_id == agent_id
    ).all()
    
    knowledge_ids = [k.id for k in knowledge_entries]
    
    if not knowledge_ids:
        return {
            "agent_id": agent_id,
            "network": [],
            "direct_influence": 0,
            "indirect_influence": 0,
            "total_nodes": 1,
            "total_edges": 0
        }
    
    # Find agents who used this agent's knowledge
    solutions_using_knowledge = db.query(ProblemSolution).filter(
        ProblemSolution.knowledge_ids_used.isnot(None)
    ).all()
    
    # Build direct influence map
    direct_influenced = defaultdict(int)  # agent_id -> usage_count
    
    for solution in solutions_using_knowledge:
        if solution.knowledge_ids_used:
            for kid in solution.knowledge_ids_used:
                if kid in knowledge_ids:
                    direct_influenced[solution.provided_by] += 1
    
    # Build network nodes and edges
    nodes = [{"id": agent_id, "type": "source", "label": f"Agent {agent_id}"}]
    edges = []
    
    # Add directly influenced agents
    for influenced_id, usage_count in list(direct_influenced.items())[:limit]:
        nodes.append({
            "id": influenced_id,
            "type": "direct",
            "label": f"Agent {influenced_id}",
            "usage_count": usage_count
        })
        edges.append({
            "source": agent_id,
            "target": influenced_id,
            "type": "knowledge_usage",
            "weight": usage_count
        })
    
    # If depth > 1, find indirect influence (agents influenced by directly influenced agents)
    if max_depth > 1 and direct_influenced:
        # Get knowledge from directly influenced agents
        influenced_ids = list(direct_influenced.keys())[:20]  # Limit for performance
        
        indirect_knowledge = db.query(KnowledgeEntry).filter(
            KnowledgeEntry.ai_instance_id.in_(influenced_ids)
        ).all()
        
        indirect_knowledge_ids = [k.id for k in indirect_knowledge]
        
        # Find agents who used indirectly influenced knowledge
        indirect_solutions = db.query(ProblemSolution).filter(
            ProblemSolution.knowledge_ids_used.isnot(None),
            ProblemSolution.provided_by.notin_([agent_id] + influenced_ids)  # Exclude source and direct
        ).all()
        
        indirect_influenced = defaultdict(int)
        
        for solution in indirect_solutions:
            if solution.knowledge_ids_used:
                for kid in solution.knowledge_ids_used:
                    if kid in indirect_knowledge_ids:
                        # Find which direct agent this knowledge came from
                        for k in indirect_knowledge:
                            if k.id == kid:
                                indirect_influenced[solution.provided_by] += 1
                                # Add edge from direct agent to indirect agent
                                if k.ai_instance_id in influenced_ids:
                                    edges.append({
                                        "source": k.ai_instance_id,
                                        "target": solution.provided_by,
                                        "type": "indirect_knowledge",
                                        "weight": 1
                                    })
                                break
        
        # Add indirect nodes
        for indirect_id, usage_count in list(indirect_influenced.items())[:limit]:
            if indirect_id not in [n["id"] for n in nodes]:
                nodes.append({
                    "id": indirect_id,
                    "type": "indirect",
                    "label": f"Agent {indirect_id}",
                    "usage_count": usage_count
                })
    
    return {
        "agent_id": agent_id,
        "network": {
            "nodes": nodes,
            "edges": edges
        },
        "direct_influence": len([n for n in nodes if n.get("type") == "direct"]),
        "indirect_influence": len([n for n in nodes if n.get("type") == "indirect"]),
        "total_nodes": len(nodes),
        "total_edges": len(edges)
    }


def get_impact_timeline(
    agent_id: int,
    db: Session,
    days: int = 30,
    interval_days: int = 7
) -> Dict[str, Any]:
    """
    Get impact metrics over time to show growth
    
    Returns timeline data showing how impact has changed
    """
    timeline = []
    
    for i in range(0, days, interval_days):
        period_days = min(interval_days, days - i)
        if period_days <= 0:
            break
            
        impact = calculate_agent_impact(agent_id, db, days=period_days)
        
        timeline.append({
            "period_start": (datetime.utcnow() - timedelta(days=i + period_days)).isoformat(),
            "period_end": (datetime.utcnow() - timedelta(days=i)).isoformat(),
            "impact_score": impact["impact_score"],
            "knowledge_usage": impact["knowledge_impact"]["times_used_by_others"],
            "agents_influenced": impact["knowledge_impact"]["agents_influenced"],
            "problems_helped": impact["knowledge_impact"]["problems_helped"]
        })
    
    return {
        "agent_id": agent_id,
        "timeline": list(reversed(timeline)),  # Oldest to newest
        "growth_rate": _calculate_growth_rate(timeline) if len(timeline) > 1 else 0.0
    }


def get_top_impact_agents(
    db: Session,
    limit: int = 10,
    days: int = 30
) -> List[Dict[str, Any]]:
    """
    Get top agents by impact score
    
    Returns list of agents sorted by impact
    """
    from app.models.ai_instance import AIInstance
    
    # Get all agents
    agents = db.query(AIInstance).all()
    
    # Calculate impact for each
    agent_impacts = []
    for agent in agents:
        try:
            impact = calculate_agent_impact(agent.id, db, days=days)
            agent_impacts.append({
                "agent_id": agent.id,
                "instance_id": agent.instance_id,
                "name": agent.name,
                "impact_score": impact["impact_score"],
                "impact_tier": impact["impact_tier"],
                "knowledge_impact": impact["knowledge_impact"]["times_used_by_others"],
                "agents_influenced": impact["knowledge_impact"]["agents_influenced"],
                "problems_helped": impact["knowledge_impact"]["problems_helped"]
            })
        except Exception:
            continue
    
    # Sort by impact score
    agent_impacts.sort(key=lambda x: x["impact_score"], reverse=True)
    
    return agent_impacts[:limit]


def _get_impact_tier(score: float) -> str:
    """Get impact tier based on score"""
    if score >= 0.8:
        return "legendary"
    elif score >= 0.6:
        return "high"
    elif score >= 0.4:
        return "moderate"
    elif score >= 0.2:
        return "growing"
    else:
        return "emerging"


def _calculate_growth_rate(timeline: List[Dict[str, Any]]) -> float:
    """Calculate growth rate from timeline"""
    if len(timeline) < 2:
        return 0.0
    
    first_score = timeline[0].get("impact_score", 0.0)
    last_score = timeline[-1].get("impact_score", 0.0)
    
    if first_score == 0:
        return 1.0 if last_score > 0 else 0.0
    
    return (last_score - first_score) / first_score
