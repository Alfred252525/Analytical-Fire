"""
Predictive analytics - predicts outcomes, suggests approaches, and forecasts trends
"""

from typing import List, Dict, Any, Optional, Tuple
from collections import defaultdict, Counter
from datetime import datetime, timedelta
import json

def predict_task_outcome(
    task_type: str,
    tools: List[str],
    historical_decisions: List[Dict[str, Any]],
    context: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Predict the outcome of a task before starting
    
    Returns:
        Prediction with probability, confidence, and recommendations
    """
    if not historical_decisions:
        return {
            "predicted_outcome": "unknown",
            "success_probability": 0.5,
            "confidence": 0.0,
            "recommendations": []
        }
    
    # Analyze similar tasks
    similar_tasks = [
        d for d in historical_decisions
        if d.get("task_type") == task_type
    ]
    
    if not similar_tasks:
        # Try to find similar task types
        task_keywords = task_type.lower().split()
        similar_tasks = [
            d for d in historical_decisions
            if any(keyword in (d.get("task_type", "") or "").lower() for keyword in task_keywords)
        ]
    
    if not similar_tasks:
        return {
            "predicted_outcome": "unknown",
            "success_probability": 0.5,
            "confidence": 0.0,
            "recommendations": []
        }
    
    # Calculate success rate
    successes = sum(1 for d in similar_tasks if d.get("outcome") == "success" or d.get("success_score", 0) > 0.7)
    total = len(similar_tasks)
    base_success_rate = successes / total if total > 0 else 0.5
    
    # Adjust based on tools
    tool_adjustment = 0.0
    tool_confidence = 0.0
    
    if tools:
        # Check tool effectiveness for this task type
        tool_successes = defaultdict(int)
        tool_totals = defaultdict(int)
        
        for decision in similar_tasks:
            decision_tools = decision.get("tools_used", [])
            if isinstance(decision_tools, str):
                try:
                    decision_tools = json.loads(decision_tools)
                except:
                    decision_tools = []
            
            if not isinstance(decision_tools, list):
                decision_tools = []
            
            for tool in decision_tools:
                tool_totals[tool] += 1
                if decision.get("outcome") == "success" or decision.get("success_score", 0) > 0.7:
                    tool_successes[tool] += 1
        
        # Calculate tool effectiveness
        tool_effectiveness = {}
        for tool in tools:
            if tool in tool_totals:
                effectiveness = tool_successes[tool] / tool_totals[tool] if tool_totals[tool] > 0 else 0.5
                tool_effectiveness[tool] = effectiveness
                tool_confidence += 1.0 / len(tools)
        
        if tool_effectiveness:
            avg_effectiveness = sum(tool_effectiveness.values()) / len(tool_effectiveness)
            tool_adjustment = (avg_effectiveness - 0.5) * 0.3  # Adjust by up to ±15%
            tool_confidence = min(1.0, tool_confidence / len(tools))
    
    # Calculate final prediction
    success_probability = min(1.0, max(0.0, base_success_rate + tool_adjustment))
    confidence = min(1.0, (total / 20.0) * 0.7 + tool_confidence * 0.3)  # Based on data volume
    
    # Determine predicted outcome
    if success_probability > 0.7:
        predicted_outcome = "success"
    elif success_probability > 0.4:
        predicted_outcome = "partial"
    else:
        predicted_outcome = "failure"
    
    # Generate recommendations
    recommendations = []
    
    # Recommend tools if not provided or if current tools are suboptimal
    if similar_tasks:
        # Find most successful tool combinations
        successful_combos = defaultdict(lambda: {"success": 0, "total": 0})
        
        for decision in similar_tasks:
            if decision.get("outcome") == "success" or decision.get("success_score", 0) > 0.7:
                decision_tools = decision.get("tools_used", [])
                if isinstance(decision_tools, str):
                    try:
                        decision_tools = json.loads(decision_tools)
                    except:
                        decision_tools = []
                
                if isinstance(decision_tools, list) and decision_tools:
                    combo_key = "_".join(sorted(decision_tools))
                    successful_combos[combo_key]["success"] += 1
                    successful_combos[combo_key]["total"] += 1
        
        # Get top recommendations
        top_combos = sorted(
            successful_combos.items(),
            key=lambda x: x[1]["success"] / x[1]["total"] if x[1]["total"] > 0 else 0,
            reverse=True
        )[:3]
        
        for combo_key, stats in top_combos:
            if stats["total"] >= 2:  # At least 2 successful uses
                tools_list = combo_key.split("_")
                recommendations.append({
                    "type": "tool_combination",
                    "tools": tools_list,
                    "success_rate": stats["success"] / stats["total"],
                    "message": f"Consider using: {' + '.join(tools_list)}"
                })
    
    return {
        "predicted_outcome": predicted_outcome,
        "success_probability": success_probability,
        "confidence": confidence,
        "recommendations": recommendations,
        "data_points": total
    }

def suggest_optimal_approach(
    task_type: str,
    historical_decisions: List[Dict[str, Any]],
    knowledge_entries: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Suggest the optimal approach for a task type
    
    Returns:
        Suggested approach with tools, steps, and knowledge
    """
    # Analyze successful approaches
    successful_decisions = [
        d for d in historical_decisions
        if d.get("task_type") == task_type and
        (d.get("outcome") == "success" or d.get("success_score", 0) > 0.7)
    ]
    
    if not successful_decisions:
        return {
            "approach": "unknown",
            "recommended_tools": [],
            "recommended_steps": [],
            "related_knowledge": [],
            "confidence": 0.0
        }
    
    # Find most common successful tools
    tool_counts = Counter()
    for decision in successful_decisions:
        tools = decision.get("tools_used", [])
        if isinstance(tools, str):
            try:
                tools = json.loads(tools)
            except:
                tools = []
        
        if isinstance(tools, list):
            for tool in tools:
                tool_counts[tool] += 1
    
    recommended_tools = [tool for tool, count in tool_counts.most_common(5)]
    
    # Find related knowledge
    related_knowledge = []
    task_keywords = task_type.lower().split()
    
    for entry in knowledge_entries:
        entry_text = f"{entry.get('title', '')} {entry.get('description', '')} {entry.get('content', '')}".lower()
        if any(keyword in entry_text for keyword in task_keywords):
            related_knowledge.append({
                "id": entry.get("id"),
                "title": entry.get("title"),
                "category": entry.get("category")
            })
    
    # Extract common steps from successful decisions
    recommended_steps = []
    steps_mentioned = Counter()
    
    for decision in successful_decisions:
        reasoning = decision.get("reasoning", "")
        if reasoning:
            # Simple step extraction (look for numbered steps or "step" keywords)
            if "step" in reasoning.lower() or any(char.isdigit() for char in reasoning[:50]):
                steps_mentioned[reasoning[:100]] += 1
    
    # Get most common steps
    if steps_mentioned:
        top_steps = steps_mentioned.most_common(3)
        recommended_steps = [step for step, count in top_steps]
    
    confidence = min(1.0, len(successful_decisions) / 10.0)
    
    return {
        "approach": "data_driven",
        "recommended_tools": recommended_tools,
        "recommended_steps": recommended_steps,
        "related_knowledge": related_knowledge[:5],
        "confidence": confidence,
        "data_points": len(successful_decisions)
    }

def forecast_trends(
    historical_decisions: List[Dict[str, Any]],
    days_ahead: int = 7
) -> Dict[str, Any]:
    """
    Forecast trends in success rates and patterns
    
    Returns:
        Forecast with predicted trends
    """
    if not historical_decisions:
        return {
            "trend": "unknown",
            "predicted_success_rate": 0.5,
            "confidence": 0.0
        }
    
    # Group by time periods
    weekly_stats = defaultdict(lambda: {"success": 0, "total": 0})
    
    for decision in historical_decisions:
        created_at = decision.get("created_at")
        if not created_at:
            continue
        
        if isinstance(created_at, str):
            try:
                created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
            except:
                continue
        
        week_key = created_at.strftime("%Y-W%W")
        weekly_stats[week_key]["total"] += 1
        
        if decision.get("outcome") == "success" or decision.get("success_score", 0) > 0.7:
            weekly_stats[week_key]["success"] += 1
    
    # Calculate trend
    weeks = sorted(weekly_stats.keys())
    if len(weeks) < 2:
        return {
            "trend": "stable",
            "predicted_success_rate": 0.5,
            "confidence": 0.0
        }
    
    # Get recent vs older rates
    recent_weeks = weeks[-4:] if len(weeks) >= 4 else weeks[-2:]
    older_weeks = weeks[:-4] if len(weeks) > 4 else []
    
    recent_success = sum(weekly_stats[w]["success"] for w in recent_weeks)
    recent_total = sum(weekly_stats[w]["total"] for w in recent_weeks)
    recent_rate = recent_success / recent_total if recent_total > 0 else 0.5
    
    if older_weeks:
        older_success = sum(weekly_stats[w]["success"] for w in older_weeks)
        older_total = sum(weekly_stats[w]["total"] for w in older_weeks)
        older_rate = older_success / older_total if older_total > 0 else 0.5
        
        trend_direction = "improving" if recent_rate > older_rate else "declining" if recent_rate < older_rate else "stable"
        trend_magnitude = abs(recent_rate - older_rate)
    else:
        trend_direction = "stable"
        trend_magnitude = 0.0
    
    # Simple linear projection
    if trend_direction == "improving":
        predicted_rate = min(1.0, recent_rate + (trend_magnitude * (days_ahead / 7)))
    elif trend_direction == "declining":
        predicted_rate = max(0.0, recent_rate - (trend_magnitude * (days_ahead / 7)))
    else:
        predicted_rate = recent_rate
    
    confidence = min(1.0, len(weeks) / 8.0)  # More weeks = more confidence
    
    return {
        "trend": trend_direction,
        "current_success_rate": recent_rate,
        "predicted_success_rate": predicted_rate,
        "trend_magnitude": trend_magnitude,
        "confidence": confidence,
        "forecast_days": days_ahead
    }
