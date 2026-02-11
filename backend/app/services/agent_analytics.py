"""
Agent Analytics & Self-Improvement
Helps agents understand their own patterns, performance, and opportunities for improvement
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from collections import defaultdict, Counter
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, and_

def get_agent_performance_analysis(
    agent_id: int,
    db: Session,
    days: int = 30
) -> Dict[str, Any]:
    """
    Comprehensive performance analysis for an agent
    
    Analyzes:
    - Success patterns
    - Tool effectiveness
    - Task type performance
    - Improvement opportunities
    - Strengths and weaknesses
    """
    from app.models.decision import Decision
    from app.models.knowledge_entry import KnowledgeEntry
    from app.models.problem import ProblemSolution
    import json
    
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    
    # Get decisions
    decisions = db.query(Decision).filter(
        Decision.ai_instance_id == agent_id,
        Decision.created_at >= cutoff_date
    ).all()
    
    # Get knowledge entries
    knowledge = db.query(KnowledgeEntry).filter(
        KnowledgeEntry.ai_instance_id == agent_id,
        KnowledgeEntry.created_at >= cutoff_date
    ).all()
    
    # Get solutions
    solutions = db.query(ProblemSolution).filter(
        ProblemSolution.provided_by == agent_id,
        ProblemSolution.created_at >= cutoff_date
    ).all()
    
    analysis = {
        "agent_id": agent_id,
        "period_days": days,
        "overview": {},
        "success_patterns": [],
        "tool_effectiveness": {},
        "task_performance": {},
        "strengths": [],
        "weaknesses": [],
        "improvement_opportunities": [],
        "recommendations": []
    }
    
    # Overview
    total_decisions = len(decisions)
    successful_decisions = sum(1 for d in decisions if d.outcome == "success" or (d.success_score or 0) > 0.7)
    success_rate = successful_decisions / total_decisions if total_decisions > 0 else 0.0
    
    analysis["overview"] = {
        "total_decisions": total_decisions,
        "successful_decisions": successful_decisions,
        "success_rate": round(success_rate, 4),
        "knowledge_shared": len(knowledge),
        "solutions_provided": len(solutions),
        "accepted_solutions": sum(1 for s in solutions if s.is_accepted)
    }
    
    # Task type performance
    task_performance = defaultdict(lambda: {"success": 0, "total": 0, "avg_score": 0.0})
    
    for decision in decisions:
        task_type = decision.task_type or "unknown"
        task_performance[task_type]["total"] += 1
        
        if decision.outcome == "success" or (decision.success_score or 0) > 0.7:
            task_performance[task_type]["success"] += 1
        
        if decision.success_score:
            task_performance[task_type]["avg_score"] += decision.success_score
    
    for task_type, stats in task_performance.items():
        stats["success_rate"] = stats["success"] / stats["total"] if stats["total"] > 0 else 0.0
        stats["avg_score"] = stats["avg_score"] / stats["total"] if stats["total"] > 0 else 0.0
    
    analysis["task_performance"] = dict(task_performance)
    
    # Tool effectiveness
    tool_effectiveness = defaultdict(lambda: {"success": 0, "total": 0})
    
    for decision in decisions:
        tools = decision.tools_used or []
        if isinstance(tools, str):
            try:
                tools = json.loads(tools) if tools else []
            except:
                tools = []
        
        if not isinstance(tools, list):
            tools = []
        
        for tool in tools:
            tool_effectiveness[tool]["total"] += 1
            if decision.outcome == "success" or (decision.success_score or 0) > 0.7:
                tool_effectiveness[tool]["success"] += 1
    
    for tool, stats in tool_effectiveness.items():
        stats["success_rate"] = stats["success"] / stats["total"] if stats["total"] > 0 else 0.0
    
    analysis["tool_effectiveness"] = {
        tool: {
            "success_rate": round(stats["success_rate"], 4),
            "usage_count": stats["total"]
        }
        for tool, stats in tool_effectiveness.items()
    }
    
    # Success patterns
    high_success_tasks = [
        task_type for task_type, stats in task_performance.items()
        if stats["total"] >= 3 and stats["success_rate"] >= 0.8
    ]
    
    for task_type in high_success_tasks[:5]:
        stats = task_performance[task_type]
        analysis["success_patterns"].append({
            "task_type": task_type,
            "success_rate": round(stats["success_rate"], 4),
            "attempts": stats["total"],
            "message": f"High success rate ({stats['success_rate']:.1%}) for {task_type}"
        })
    
    # Strengths
    if high_success_tasks:
        analysis["strengths"].append({
            "type": "task_expertise",
            "description": f"Strong performance in: {', '.join(high_success_tasks[:3])}",
            "evidence": f"{len(high_success_tasks)} task types with >80% success rate"
        })
    
    # High-performing tools
    top_tools = sorted(
        tool_effectiveness.items(),
        key=lambda x: x[1]["success_rate"],
        reverse=True
    )[:3]
    
    if top_tools and top_tools[0][1]["total"] >= 3:
        analysis["strengths"].append({
            "type": "tool_mastery",
            "description": f"Effective use of: {', '.join([tool for tool, _ in top_tools])}",
            "evidence": f"Tools with highest success rates"
        })
    
    # Knowledge quality
    if knowledge:
        verified_count = sum(1 for k in knowledge if k.verified)
        total_upvotes = sum(k.upvotes for k in knowledge)
        avg_upvotes = total_upvotes / len(knowledge) if knowledge else 0
        
        if verified_count > 0:
            analysis["strengths"].append({
                "type": "knowledge_quality",
                "description": f"{verified_count} verified knowledge entries",
                "evidence": f"High-quality knowledge sharing"
            })
    
    # Weaknesses
    low_success_tasks = [
        task_type for task_type, stats in task_performance.items()
        if stats["total"] >= 3 and stats["success_rate"] < 0.5
    ]
    
    if low_success_tasks:
        analysis["weaknesses"].append({
            "type": "task_challenges",
            "description": f"Lower success rate in: {', '.join(low_success_tasks[:3])}",
            "evidence": f"{len(low_success_tasks)} task types with <50% success rate",
            "suggestion": "Consider learning from successful patterns or trying different approaches"
        })
    
    # Improvement opportunities
    if low_success_tasks:
        analysis["improvement_opportunities"].append({
            "area": "task_performance",
            "task_types": low_success_tasks[:3],
            "current_rate": round(task_performance[low_success_tasks[0]]["success_rate"], 4) if low_success_tasks else 0.0,
            "recommendation": "Learn from collective intelligence patterns for these task types"
        })
    
    # Recommendations
    if total_decisions < 10:
        analysis["recommendations"].append({
            "type": "activity",
            "priority": "high",
            "message": "Log more decisions to get better insights",
            "action": "Increase decision logging frequency"
        })
    
    if not knowledge:
        analysis["recommendations"].append({
            "type": "knowledge_sharing",
            "priority": "medium",
            "message": "Start sharing knowledge to help others and build reputation",
            "action": "Share solutions and learnings from your work"
        })
    
    return analysis

def get_agent_learning_path(
    agent_id: int,
    db: Session
) -> Dict[str, Any]:
    """
    Get personalized learning path for an agent
    
    Based on:
    - Current performance gaps
    - Collective best practices
    - Agent's interests
    - Success patterns from other agents
    """
    from app.models.decision import Decision
    from app.models.knowledge_entry import KnowledgeEntry
    from app.services.collective_learning import get_collective_insights
    
    # Get performance analysis
    performance = get_agent_performance_analysis(agent_id, db, days=30)
    
    # Get collective insights
    insights = get_collective_insights(agent_id, db)
    
    learning_path = {
        "agent_id": agent_id,
        "current_level": "intermediate",  # Could be calculated
        "learning_goals": [],
        "recommended_knowledge": [],
        "recommended_practices": [],
        "skill_gaps": [],
        "next_steps": []
    }
    
    # Identify skill gaps from weaknesses
    for weakness in performance.get("weaknesses", []):
        if weakness["type"] == "task_challenges":
            learning_path["skill_gaps"].append({
                "area": weakness["description"],
                "priority": "high",
                "suggested_action": weakness.get("suggestion", "Learn from successful patterns")
            })
    
    # Add recommendations from collective insights
    for rec in insights.get("recommendations", []):
        if rec["type"] == "tool_recommendation":
            learning_path["recommended_practices"].append({
                "type": "tool_usage",
                "task_type": rec.get("task_type", "general"),
                "tools": rec.get("tools", []),
                "reason": rec.get("message", "")
            })
    
    # Learning goals
    if learning_path["skill_gaps"]:
        learning_path["learning_goals"].append({
            "goal": "Improve success rate in challenging task types",
            "priority": "high",
            "timeline": "30 days"
        })
    
    # Next steps
    if learning_path["skill_gaps"]:
        learning_path["next_steps"].append({
            "step": 1,
            "action": "Review collective learning insights for challenging task types",
            "endpoint": "/api/v1/learning/insights"
        })
    
    if insights.get("recommendations"):
        learning_path["next_steps"].append({
            "step": 2,
            "action": "Adopt recommended tool combinations",
            "endpoint": "/api/v1/learning/recommendations"
        })
    
    return learning_path

def get_agent_insights_summary(
    agent_id: int,
    db: Session
) -> Dict[str, Any]:
    """
    Get comprehensive insights summary for an agent
    
    Combines performance, learning, and collaboration insights
    """
    from app.services.agent_reputation import calculate_agent_reputation
    from app.services.advanced_collaboration import get_collaboration_metrics
    
    # Get all insights
    performance = get_agent_performance_analysis(agent_id, db)
    reputation = calculate_agent_reputation(agent_id, db, include_breakdown=True)
    collaboration = get_collaboration_metrics(agent_id, db)
    learning_path = get_agent_learning_path(agent_id, db)
    
    return {
        "agent_id": agent_id,
        "summary": {
            "reputation_score": reputation.get("reputation_score", 0.0),
            "reputation_tier": reputation.get("tier", "new"),
            "success_rate": performance["overview"].get("success_rate", 0.0),
            "collaboration_score": collaboration.get("collaboration_score", 0.0),
            "knowledge_shared": performance["overview"].get("knowledge_shared", 0)
        },
        "performance": performance,
        "reputation": reputation,
        "collaboration": collaboration,
        "learning_path": learning_path,
        "key_insights": {
            "strengths": performance.get("strengths", [])[:3],
            "weaknesses": performance.get("weaknesses", [])[:3],
            "opportunities": performance.get("improvement_opportunities", [])[:3]
        }
    }
