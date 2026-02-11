"""
Collective Learning System
Helps agents learn from collective intelligence - patterns, successes, and insights from all agents
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from collections import defaultdict, Counter
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
import json

def get_collective_insights(
    agent_id: int,
    db: Session,
    task_type: Optional[str] = None
) -> Dict[str, Any]:
    """
    Get collective learning insights for an agent
    
    Analyzes patterns from all agents to provide actionable insights:
    - Successful patterns to follow
    - Common mistakes to avoid
    - Optimal approaches for tasks
    - Tool recommendations
    """
    from app.models.decision import Decision
    from app.models.knowledge_entry import KnowledgeEntry
    from app.models.problem import ProblemSolution
    from app.services.pattern_ml import (
        analyze_tool_effectiveness,
        discover_success_patterns,
        find_optimal_tool_combinations
    )
    from app.services.predictive_analytics import suggest_optimal_approach
    
    # Get agent's recent decisions
    agent_decisions = db.query(Decision).filter(
        Decision.ai_instance_id == agent_id
    ).order_by(desc(Decision.created_at)).limit(50).all()
    
    # Get all recent decisions (collective intelligence)
    recent_decisions = db.query(Decision).filter(
        Decision.created_at >= datetime.utcnow() - timedelta(days=90)
    ).all()
    
    if len(recent_decisions) < 10:
        return {
            "insights": [],
            "recommendations": [],
            "patterns": [],
            "data_points": len(recent_decisions),
            "message": "Not enough collective data yet"
        }
    
    # Convert to dict format
    decisions_dict = []
    for d in recent_decisions:
        tools = d.tools_used or []
        if isinstance(tools, str):
            try:
                tools = json.loads(tools) if tools else []
            except:
                tools = []
        
        decisions_dict.append({
            "task_type": d.task_type or "unknown",
            "outcome": d.outcome or "unknown",
            "success_score": d.success_score or 0.0,
            "tools_used": tools if isinstance(tools, list) else [],
            "created_at": d.created_at.isoformat() if d.created_at else None
        })
    
    insights = []
    recommendations = []
    patterns = []
    
    # 1. Analyze tool effectiveness
    tool_effectiveness = analyze_tool_effectiveness(decisions_dict)
    
    # 2. Discover success patterns
    success_patterns = discover_success_patterns(decisions_dict, min_frequency=5)
    
    # 3. Find optimal tool combinations
    optimal_combos = find_optimal_tool_combinations(decisions_dict, min_frequency=3)
    
    # 4. Get agent's task types
    agent_task_types = set()
    for d in agent_decisions:
        if d.task_type:
            agent_task_types.add(d.task_type)
    
    # 5. Generate insights for agent's task types
    for task_type in agent_task_types:
        # Filter decisions for this task type
        task_decisions = [d for d in decisions_dict if d.get("task_type") == task_type]
        
        if len(task_decisions) < 5:
            continue
        
        # Calculate success rate
        successes = sum(1 for d in task_decisions if d.get("outcome") == "success" or d.get("success_score", 0) > 0.7)
        success_rate = successes / len(task_decisions)
        
        # Get agent's success rate for this task
        agent_task_decisions = [d for d in agent_decisions if d.task_type == task_type]
        agent_successes = sum(1 for d in agent_task_decisions if d.outcome == "success" or (d.success_score or 0) > 0.7)
        agent_success_rate = agent_successes / len(agent_task_decisions) if agent_task_decisions else 0.0
        
        # Compare with collective
        if success_rate > agent_success_rate + 0.1:  # Collective is significantly better
            insights.append({
                "type": "improvement_opportunity",
                "task_type": task_type,
                "message": f"Collective success rate for {task_type} is {success_rate:.1%}, while yours is {agent_success_rate:.1%}. Consider learning from successful patterns.",
                "collective_success_rate": success_rate,
                "your_success_rate": agent_success_rate,
                "improvement_potential": success_rate - agent_success_rate
            })
        
        # Get optimal tools for this task
        if task_type in tool_effectiveness:
            top_tools = sorted(
                tool_effectiveness[task_type].items(),
                key=lambda x: x[1],
                reverse=True
            )[:3]
            
            if top_tools:
                recommendations.append({
                    "type": "tool_recommendation",
                    "task_type": task_type,
                    "tools": [tool for tool, score in top_tools],
                    "effectiveness_scores": {tool: score for tool, score in top_tools},
                    "message": f"For {task_type}, these tools have highest success rates: {', '.join([tool for tool, _ in top_tools])}"
                })
    
    # 6. Add success patterns
    for pattern in success_patterns[:5]:  # Top 5 patterns
        patterns.append({
            "pattern_type": pattern.get("pattern_type"),
            "name": pattern.get("name"),
            "description": pattern.get("description"),
            "success_rate": pattern.get("success_rate", 0.0),
            "frequency": pattern.get("frequency", 0),
            "confidence": pattern.get("confidence", 0.0)
        })
    
    # 7. Add optimal tool combinations
    for combo in optimal_combos[:5]:  # Top 5 combinations
        recommendations.append({
            "type": "tool_combination",
            "tools": combo.get("tools", []),
            "success_rate": combo.get("success_rate", 0.0),
            "frequency": combo.get("frequency", 0),
            "confidence": combo.get("confidence", 0.0),
            "message": f"Tool combination {', '.join(combo.get('tools', []))} has {combo.get('success_rate', 0):.1%} success rate"
        })
    
    return {
        "insights": insights,
        "recommendations": recommendations,
        "patterns": patterns,
        "data_points": len(recent_decisions),
        "agent_data_points": len(agent_decisions)
    }

def get_learning_recommendations(
    agent_id: int,
    db: Session,
    task_type: Optional[str] = None
) -> Dict[str, Any]:
    """
    Get personalized learning recommendations for an agent
    
    Based on:
    - Agent's current performance
    - Collective best practices
    - Successful patterns from other agents
    - Knowledge gaps
    """
    from app.models.decision import Decision
    from app.models.knowledge_entry import KnowledgeEntry
    from app.services.predictive_analytics import suggest_optimal_approach
    
    # Get agent's decisions
    agent_decisions = db.query(Decision).filter(
        Decision.ai_instance_id == agent_id
    ).all()
    
    # Get all decisions for comparison
    all_decisions = db.query(Decision).filter(
        Decision.created_at >= datetime.utcnow() - timedelta(days=90)
    ).all()
    
    if len(all_decisions) < 10:
        return {
            "recommendations": [],
            "message": "Not enough data for recommendations"
        }
    
    # Convert to dict
    all_decisions_dict = []
    for d in all_decisions:
        tools = d.tools_used or []
        if isinstance(tools, str):
            try:
                tools = json.loads(tools) if tools else []
            except:
                tools = []
        
        all_decisions_dict.append({
            "task_type": d.task_type or "unknown",
            "outcome": d.outcome or "unknown",
            "success_score": d.success_score or 0.0,
            "tools_used": tools if isinstance(tools, list) else [],
            "reasoning": d.reasoning or ""
        })
    
    # Get agent's knowledge
    agent_knowledge = db.query(KnowledgeEntry).filter(
        KnowledgeEntry.ai_instance_id == agent_id
    ).all()
    
    agent_knowledge_dict = []
    for k in agent_knowledge:
        agent_knowledge_dict.append({
            "id": k.id,
            "title": k.title,
            "description": k.description,
            "content": k.content,
            "category": k.category,
            "tags": k.tags or []
        })
    
    recommendations = []
    
    # Analyze by task type if specified
    if task_type:
        task_decisions = [d for d in all_decisions_dict if d.get("task_type") == task_type]
        if len(task_decisions) >= 5:
            optimal = suggest_optimal_approach(
                task_type=task_type,
                historical_decisions=task_decisions,
                knowledge_entries=agent_knowledge_dict
            )
            
            if optimal.get("confidence", 0) > 0.3:
                recommendations.append({
                    "type": "optimal_approach",
                    "task_type": task_type,
                    "recommended_tools": optimal.get("recommended_tools", []),
                    "recommended_steps": optimal.get("recommended_steps", []),
                    "related_knowledge": optimal.get("related_knowledge", []),
                    "confidence": optimal.get("confidence", 0.0),
                    "message": f"Based on collective intelligence, here's the optimal approach for {task_type}"
                })
    else:
        # Get recommendations for agent's most common task types
        agent_task_types = Counter()
        for d in agent_decisions:
            if d.task_type:
                agent_task_types[d.task_type] += 1
        
        for task_type, count in agent_task_types.most_common(3):
            task_decisions = [d for d in all_decisions_dict if d.get("task_type") == task_type]
            if len(task_decisions) >= 5:
                optimal = suggest_optimal_approach(
                    task_type=task_type,
                    historical_decisions=task_decisions,
                    knowledge_entries=agent_knowledge_dict
                )
                
                if optimal.get("confidence", 0) > 0.3:
                    recommendations.append({
                        "type": "optimal_approach",
                        "task_type": task_type,
                        "recommended_tools": optimal.get("recommended_tools", []),
                        "recommended_steps": optimal.get("recommended_steps", []),
                        "related_knowledge": optimal.get("related_knowledge", []),
                        "confidence": optimal.get("confidence", 0.0),
                        "message": f"Optimal approach for {task_type} based on collective intelligence"
                    })
    
    return {
        "recommendations": recommendations,
        "data_points": len(all_decisions)
    }

def get_collective_wisdom(
    db: Session,
    category: Optional[str] = None,
    limit: int = 10
) -> Dict[str, Any]:
    """
    Get collective wisdom - aggregated learnings from all agents
    
    Returns:
        - Most successful patterns
        - Common mistakes to avoid
        - Best practices
        - Trending approaches
    """
    from app.models.decision import Decision
    from app.models.knowledge_entry import KnowledgeEntry
    from app.models.problem import ProblemSolution
    from app.services.pattern_ml import (
        discover_success_patterns,
        find_optimal_tool_combinations
    )
    
    # Get recent decisions
    recent_decisions = db.query(Decision).filter(
        Decision.created_at >= datetime.utcnow() - timedelta(days=90)
    ).all()
    
    if len(recent_decisions) < 10:
        return {
            "wisdom": [],
            "best_practices": [],
            "common_mistakes": [],
            "message": "Not enough data for collective wisdom"
        }
    
    # Convert to dict
    decisions_dict = []
    for d in recent_decisions:
        tools = d.tools_used or []
        if isinstance(tools, str):
            try:
                tools = json.loads(tools) if tools else []
            except:
                tools = []
        
        decisions_dict.append({
            "task_type": d.task_type or "unknown",
            "outcome": d.outcome or "unknown",
            "success_score": d.success_score or 0.0,
            "tools_used": tools if isinstance(tools, list) else [],
            "reasoning": d.reasoning or ""
        })
    
    wisdom = []
    best_practices = []
    common_mistakes = []
    
    # 1. Success patterns
    success_patterns = discover_success_patterns(decisions_dict, min_frequency=5)
    for pattern in success_patterns[:5]:
        wisdom.append({
            "type": "success_pattern",
            "title": pattern.get("name", "Unknown Pattern"),
            "description": pattern.get("description", ""),
            "success_rate": pattern.get("success_rate", 0.0),
            "frequency": pattern.get("frequency", 0)
        })
    
    # 2. Optimal tool combinations
    optimal_combos = find_optimal_tool_combinations(decisions_dict, min_frequency=3)
    for combo in optimal_combos[:5]:
        best_practices.append({
            "type": "tool_combination",
            "tools": combo.get("tools", []),
            "success_rate": combo.get("success_rate", 0.0),
            "frequency": combo.get("frequency", 0),
            "description": f"Using {' + '.join(combo.get('tools', []))} together has {combo.get('success_rate', 0):.1%} success rate"
        })
    
    # 3. Common mistakes (low success rate patterns)
    task_stats = defaultdict(lambda: {"success": 0, "total": 0, "tools": Counter()})
    
    for decision in decisions_dict:
        task_type = decision.get("task_type", "unknown")
        tools = decision.get("tools_used", [])
        outcome = decision.get("outcome", "unknown")
        
        task_stats[task_type]["total"] += 1
        if outcome == "success" or decision.get("success_score", 0) > 0.7:
            task_stats[task_type]["success"] += 1
        
        for tool in tools:
            task_stats[task_type]["tools"][tool] += 1
    
    for task_type, stats in task_stats.items():
        if stats["total"] >= 5:
            success_rate = stats["success"] / stats["total"]
            if success_rate < 0.3:  # Low success rate
                common_mistakes.append({
                    "type": "low_success_pattern",
                    "task_type": task_type,
                    "success_rate": success_rate,
                    "frequency": stats["total"],
                    "description": f"{task_type} tasks have low success rate ({success_rate:.1%}). Consider alternative approaches."
                })
    
    # 4. High-quality knowledge entries
    if category:
        knowledge_entries = db.query(KnowledgeEntry).filter(
            KnowledgeEntry.category == category,
            KnowledgeEntry.verified == True
        ).order_by(desc(KnowledgeEntry.upvotes)).limit(limit).all()
    else:
        knowledge_entries = db.query(KnowledgeEntry).filter(
            KnowledgeEntry.verified == True
        ).order_by(desc(KnowledgeEntry.upvotes)).limit(limit).all()
    
    knowledge_wisdom = []
    for entry in knowledge_entries:
        knowledge_wisdom.append({
            "type": "verified_knowledge",
            "id": entry.id,
            "title": entry.title,
            "category": entry.category,
            "upvotes": entry.upvotes,
            "usage_count": entry.usage_count
        })
    
    return {
        "wisdom": wisdom,
        "best_practices": best_practices,
        "common_mistakes": common_mistakes,
        "verified_knowledge": knowledge_wisdom,
        "data_points": len(recent_decisions)
    }
