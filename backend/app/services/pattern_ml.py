"""
ML-powered pattern analysis
Discovers patterns in decisions and knowledge using statistical analysis
"""

from typing import List, Dict, Any, Tuple
from collections import defaultdict, Counter
from datetime import datetime, timedelta
import json

def analyze_tool_effectiveness(
    decisions: List[Dict[str, Any]]
) -> Dict[str, Dict[str, float]]:
    """
    Analyze which tools are most effective for different task types
    
    Returns:
        Dict mapping task_type -> tool -> effectiveness_score
    """
    tool_effectiveness = defaultdict(lambda: defaultdict(lambda: {"success": 0, "total": 0}))
    
    for decision in decisions:
        task_type = decision.get("task_type", "unknown")
        tools = decision.get("tools_used", [])
        outcome = decision.get("outcome", "unknown")
        success_score = decision.get("success_score", 0.0)
        
        if isinstance(tools, str):
            try:
                tools = json.loads(tools)
            except:
                tools = []
        
        if not isinstance(tools, list):
            tools = []
        
        for tool in tools:
            tool_effectiveness[task_type][tool]["total"] += 1
            if outcome == "success" or success_score > 0.7:
                tool_effectiveness[task_type][tool]["success"] += 1
    
    # Calculate effectiveness scores
    effectiveness_scores = {}
    for task_type, tools in tool_effectiveness.items():
        effectiveness_scores[task_type] = {}
        for tool, stats in tools.items():
            if stats["total"] > 0:
                effectiveness = stats["success"] / stats["total"]
                # Weight by frequency (more data = more reliable)
                confidence = min(1.0, stats["total"] / 10.0)
                effectiveness_scores[task_type][tool] = effectiveness * confidence
    
    return effectiveness_scores

def discover_success_patterns(
    decisions: List[Dict[str, Any]],
    min_frequency: int = 5
) -> List[Dict[str, Any]]:
    """
    Discover patterns that lead to success
    
    Returns:
        List of pattern dictionaries
    """
    patterns = []
    
    # Pattern 1: Task type success rates
    task_stats = defaultdict(lambda: {"success": 0, "total": 0, "tools": Counter()})
    
    for decision in decisions:
        task_type = decision.get("task_type", "unknown")
        outcome = decision.get("outcome", "unknown")
        tools = decision.get("tools_used", [])
        
        if isinstance(tools, str):
            try:
                tools = json.loads(tools)
            except:
                tools = []
        
        if not isinstance(tools, list):
            tools = []
        
        task_stats[task_type]["total"] += 1
        if outcome == "success":
            task_stats[task_type]["success"] += 1
        
        for tool in tools:
            task_stats[task_type]["tools"][tool] += 1
    
    # Create patterns for high-success task types
    for task_type, stats in task_stats.items():
        if stats["total"] >= min_frequency:
            success_rate = stats["success"] / stats["total"]
            
            if success_rate > 0.7:  # High success rate
                common_tools = [tool for tool, count in stats["tools"].most_common(3)]
                
                patterns.append({
                    "pattern_type": "success_pattern",
                    "name": f"{task_type}_high_success",
                    "description": f"{task_type} tasks have {success_rate:.1%} success rate. Recommended tools: {', '.join(common_tools) if common_tools else 'none'}",
                    "frequency": stats["total"],
                    "confidence": min(1.0, stats["total"] / 20.0),
                    "success_rate": success_rate,
                    "pattern_data": {
                        "task_type": task_type,
                        "common_tools": common_tools,
                        "success_rate": success_rate
                    }
                })
    
    return patterns

def predict_success_probability(
    task_type: str,
    tools: List[str],
    tool_effectiveness: Dict[str, Dict[str, float]]
) -> float:
    """
    Predict probability of success for a task given tools
    
    Returns:
        Probability between 0.0 and 1.0
    """
    if task_type not in tool_effectiveness:
        return 0.5  # Default if no data
    
    tool_scores = tool_effectiveness[task_type]
    
    if not tools:
        return 0.5
    
    # Average effectiveness of tools being used
    scores = [tool_scores.get(tool, 0.5) for tool in tools if tool in tool_scores]
    
    if not scores:
        return 0.5
    
    # Weighted average (more tools = higher confidence)
    avg_score = sum(scores) / len(scores)
    confidence_boost = min(0.2, len(scores) * 0.05)  # Boost for using multiple tools
    
    return min(1.0, avg_score + confidence_boost)

def find_optimal_tool_combinations(
    decisions: List[Dict[str, Any]],
    min_frequency: int = 3
) -> List[Dict[str, Any]]:
    """
    Find optimal tool combinations for different tasks
    
    Returns:
        List of optimal combinations
    """
    combinations = defaultdict(lambda: {"success": 0, "total": 0})
    
    for decision in decisions:
        tools = decision.get("tools_used", [])
        outcome = decision.get("outcome", "unknown")
        success_score = decision.get("success_score", 0.0)
        
        if isinstance(tools, str):
            try:
                tools = json.loads(tools)
            except:
                tools = []
        
        if not isinstance(tools, list) or len(tools) < 2:
            continue
        
        # Create sorted key for combination
        tool_key = "_".join(sorted(tools))
        combinations[tool_key]["total"] += 1
        
        if outcome == "success" or success_score > 0.7:
            combinations[tool_key]["success"] += 1
    
    # Find high-success combinations
    optimal = []
    for combo_key, stats in combinations.items():
        if stats["total"] >= min_frequency:
            success_rate = stats["success"] / stats["total"]
            
            if success_rate > 0.6:  # Good success rate
                tools = combo_key.split("_")
                optimal.append({
                    "tools": tools,
                    "success_rate": success_rate,
                    "frequency": stats["total"],
                    "confidence": min(1.0, stats["total"] / 10.0)
                })
    
    # Sort by success rate and frequency
    optimal.sort(key=lambda x: (x["success_rate"], x["frequency"]), reverse=True)
    
    return optimal

def analyze_temporal_patterns(
    decisions: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Analyze patterns over time (e.g., success rates improving)
    
    Returns:
        Temporal analysis results
    """
    if not decisions:
        return {}
    
    # Group by time periods
    weekly_stats = defaultdict(lambda: {"success": 0, "total": 0})
    
    for decision in decisions:
        created_at = decision.get("created_at")
        if not created_at:
            continue
        
        if isinstance(created_at, str):
            try:
                created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
            except:
                continue
        
        # Get week
        week_key = created_at.strftime("%Y-W%W")
        weekly_stats[week_key]["total"] += 1
        
        outcome = decision.get("outcome", "unknown")
        if outcome == "success":
            weekly_stats[week_key]["success"] += 1
    
    # Calculate trends
    weeks = sorted(weekly_stats.keys())
    if len(weeks) < 2:
        return {}
    
    recent_weeks = weeks[-4:]  # Last 4 weeks
    older_weeks = weeks[:-4] if len(weeks) > 4 else []
    
    recent_success = sum(weekly_stats[w]["success"] for w in recent_weeks)
    recent_total = sum(weekly_stats[w]["total"] for w in recent_weeks)
    recent_rate = recent_success / recent_total if recent_total > 0 else 0.0
    
    older_success = sum(weekly_stats[w]["success"] for w in older_weeks)
    older_total = sum(weekly_stats[w]["total"] for w in older_weeks)
    older_rate = older_success / older_total if older_total > 0 else 0.0
    
    trend = "improving" if recent_rate > older_rate else "declining" if recent_rate < older_rate else "stable"
    
    return {
        "trend": trend,
        "recent_success_rate": recent_rate,
        "older_success_rate": older_rate,
        "improvement": recent_rate - older_rate
    }
