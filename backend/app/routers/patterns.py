"""
Pattern recognition router
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Dict, Any
from datetime import datetime, timedelta
import json

from app.database import get_db
from app.models.ai_instance import AIInstance
from app.models.pattern import Pattern
from app.models.decision import Decision
from app.schemas.pattern import PatternResponse, PatternQuery
from app.core.security import get_current_ai_instance
from app.services.pattern_ml import (
    analyze_tool_effectiveness,
    discover_success_patterns,
    find_optimal_tool_combinations,
    analyze_temporal_patterns,
    predict_success_probability
)
from app.services.realtime import realtime_manager, create_notification
from app.routers.realtime import manager as connection_manager

router = APIRouter()

@router.get("/", response_model=List[PatternResponse])
async def get_patterns(
    query: PatternQuery = Depends(),
    current_instance: AIInstance = Depends(get_current_ai_instance),
    db: Session = Depends(get_db)
):
    """Get identified patterns"""
    db_query = db.query(Pattern)
    
    if query.pattern_type:
        db_query = db_query.filter(Pattern.pattern_type == query.pattern_type)
    
    if query.min_confidence is not None:
        db_query = db_query.filter(Pattern.confidence >= query.min_confidence)
    
    if query.min_frequency is not None:
        db_query = db_query.filter(Pattern.frequency >= query.min_frequency)
    
    db_query = db_query.order_by(Pattern.confidence.desc(), Pattern.frequency.desc()).limit(query.limit)
    
    return db_query.all()

@router.post("/analyze")
async def analyze_patterns(
    current_instance: AIInstance = Depends(get_current_ai_instance),
    db: Session = Depends(get_db)
):
    """
    Analyze decisions to identify patterns using ML
    Enhanced with statistical analysis, tool effectiveness, and temporal patterns
    """
    from collections import defaultdict
    from sqlalchemy import func
    
    # Get all decisions (not just current instance, for collective intelligence)
    recent_decisions = db.query(Decision).filter(
        Decision.created_at >= datetime.utcnow() - timedelta(days=90)
    ).all()
    
    if len(recent_decisions) < 10:
        return {"message": "Not enough data to analyze patterns", "patterns_found": 0}
    
    # Convert to dict format for ML analysis
    decisions_dict = []
    for decision in recent_decisions:
        decisions_dict.append({
            "task_type": decision.task_type or "unknown",
            "outcome": decision.outcome,
            "success_score": decision.success_score,
            "tools_used": decision.tools_used or [],
            "created_at": decision.created_at.isoformat() if decision.created_at else None
        })
    
    # ML-powered pattern analysis
    patterns_created = 0
    
    # 1. Discover success patterns
    success_patterns = discover_success_patterns(decisions_dict, min_frequency=5)
    
    # 2. Find optimal tool combinations
    optimal_combos = find_optimal_tool_combinations(decisions_dict, min_frequency=3)
    
    # 3. Analyze tool effectiveness
    tool_effectiveness = analyze_tool_effectiveness(decisions_dict)
    
    # 4. Temporal analysis
    temporal = analyze_temporal_patterns(decisions_dict)
    
    # Create pattern entries for success patterns
    for pattern_data in success_patterns:
        pattern_name = pattern_data["name"]
        existing = db.query(Pattern).filter(Pattern.name == pattern_name).first()
        
        if not existing:
            pattern = Pattern(
                pattern_type=pattern_data["pattern_type"],
                name=pattern_name,
                description=pattern_data["description"],
                frequency=pattern_data["frequency"],
                confidence=pattern_data["confidence"],
                success_rate=pattern_data["success_rate"],
                pattern_data=json.dumps(pattern_data["pattern_data"])
            )
            db.add(pattern)
            patterns_created += 1
    
    # Create patterns for optimal tool combinations
    for combo in optimal_combos[:10]:  # Top 10 combinations
        pattern_name = f"optimal_combo_{'_'.join(combo['tools'])}"
        existing = db.query(Pattern).filter(Pattern.name == pattern_name).first()
        
        if not existing:
            pattern = Pattern(
                pattern_type="tool_pattern",
                name=pattern_name,
                description=f"Optimal tool combination: {' + '.join(combo['tools'])} ({combo['success_rate']:.1%} success, {combo['frequency']} uses)",
                frequency=combo["frequency"],
                confidence=combo["confidence"],
                success_rate=combo["success_rate"],
                pattern_data=json.dumps({"tools": combo["tools"], "success_rate": combo["success_rate"]})
            )
            db.add(pattern)
            patterns_created += 1
    
    # Pattern 1: Task type and outcome patterns
    task_patterns = defaultdict(lambda: {"success": 0, "failure": 0, "partial": 0, "total": 0, "tools": defaultdict(int)})
    
    for decision in recent_decisions:
        task_type = decision.task_type or "unknown"
        task_patterns[task_type]["total"] += 1
        
        if decision.outcome == "success":
            task_patterns[task_type]["success"] += 1
        elif decision.outcome == "failure":
            task_patterns[task_type]["failure"] += 1
        else:
            task_patterns[task_type]["partial"] += 1
        
        # Track tool usage
        if decision.tools_used:
            tools = decision.tools_used if isinstance(decision.tools_used, list) else json.loads(decision.tools_used)
            for tool in tools:
                task_patterns[task_type]["tools"][tool] += 1
    
    # Create patterns for task types
    for task_type, data in task_patterns.items():
        if data["total"] >= 5:  # Minimum frequency
            success_rate = data["success"] / data["total"]
            
            # Find most common tools
            common_tools = sorted(data["tools"].items(), key=lambda x: x[1], reverse=True)[:3]
            tool_names = [tool for tool, _ in common_tools]
            
            pattern_name = f"{task_type}_success_pattern"
            existing = db.query(Pattern).filter(Pattern.name == pattern_name).first()
            
            if not existing:
                pattern = Pattern(
                    pattern_type="success_pattern" if success_rate > 0.7 else "mixed_pattern",
                    name=pattern_name,
                    description=f"Pattern for {task_type}: {success_rate:.1%} success rate. Common tools: {', '.join(tool_names) if tool_names else 'none'}",
                    frequency=data["total"],
                    confidence=min(data["total"] / 20.0, 1.0),
                    success_rate=success_rate,
                    pattern_data=json.dumps({"common_tools": tool_names, "success_rate": success_rate})
                )
                db.add(pattern)
                patterns_created += 1
    
    # Pattern 2: Tool combination patterns
    tool_combinations = defaultdict(lambda: {"success": 0, "total": 0})
    
    for decision in recent_decisions:
        if decision.tools_used and decision.outcome:
            tools = decision.tools_used if isinstance(decision.tools_used, list) else json.loads(decision.tools_used)
            if len(tools) >= 2:
                tool_key = "_".join(sorted(tools))
                tool_combinations[tool_key]["total"] += 1
                if decision.outcome == "success":
                    tool_combinations[tool_key]["success"] += 1
    
    # Create patterns for tool combinations
    for tool_key, data in tool_combinations.items():
        if data["total"] >= 3:
            success_rate = data["success"] / data["total"]
            
            pattern_name = f"tool_combo_{tool_key}"
            existing = db.query(Pattern).filter(Pattern.name == pattern_name).first()
            
            if not existing and success_rate > 0.6:
                pattern = Pattern(
                    pattern_type="tool_pattern",
                    name=pattern_name,
                    description=f"Effective tool combination: {tool_key.replace('_', ' + ')} ({success_rate:.1%} success)",
                    frequency=data["total"],
                    confidence=min(data["total"] / 10.0, 1.0),
                    success_rate=success_rate,
                    pattern_data=json.dumps({"tools": tool_key.split("_"), "success_rate": success_rate})
                )
                db.add(pattern)
                patterns_created += 1
    
    if patterns_created > 0:
        db.commit()
        
        # Send real-time notification for new patterns (non-blocking)
        try:
            notification = create_notification(
                event_type="pattern_discovered",
                data={
                    "patterns_found": patterns_created,
                    "decisions_analyzed": len(recent_decisions),
                    "ai_instance_id": current_instance.id,
                    "ai_instance_name": current_instance.name
                },
                broadcast=True
            )
            # Note: Real-time notifications are best-effort
        except:
            pass  # Don't fail the request if notification fails
    
    return {
        "message": f"ML analysis complete. Found {patterns_created} new patterns from {len(recent_decisions)} decisions.",
        "patterns_found": patterns_created,
        "decisions_analyzed": len(recent_decisions),
        "tool_effectiveness": tool_effectiveness,
        "optimal_combinations": optimal_combos[:5],  # Top 5
        "temporal_trend": temporal.get("trend", "unknown"),
        "success_rate_trend": temporal.get("improvement", 0.0)
    }

@router.post("/predict")
async def predict_success(
    task_type: str,
    tools: List[str],
    current_instance: AIInstance = Depends(get_current_ai_instance),
    db: Session = Depends(get_db)
):
    """
    Predict probability of success for a task given tools
    Uses ML analysis of historical decisions
    """
    # Get recent decisions for analysis
    recent_decisions = db.query(Decision).filter(
        Decision.created_at >= datetime.utcnow() - timedelta(days=90)
    ).all()
    
    if len(recent_decisions) < 10:
        return {
            "prediction": 0.5,
            "confidence": 0.0,
            "message": "Not enough data for prediction"
        }
    
    # Convert to dict format
    decisions_dict = []
    for decision in recent_decisions:
        decisions_dict.append({
            "task_type": decision.task_type or "unknown",
            "outcome": decision.outcome,
            "success_score": decision.success_score,
            "tools_used": decision.tools_used or []
        })
    
    # Analyze tool effectiveness
    tool_effectiveness = analyze_tool_effectiveness(decisions_dict)
    
    # Predict success
    probability = predict_success_probability(task_type, tools, tool_effectiveness)
    
    # Calculate confidence based on data availability
    task_data = tool_effectiveness.get(task_type, {})
    tool_data_count = sum(1 for tool in tools if tool in task_data)
    confidence = min(1.0, tool_data_count / len(tools)) if tools else 0.0
    
    return {
        "prediction": probability,
        "confidence": confidence,
        "task_type": task_type,
        "tools": tools,
        "message": f"Predicted {probability:.1%} success probability"
    }
