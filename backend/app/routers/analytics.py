"""
Analytics router
"""

from fastapi import APIRouter, Depends, HTTPException, status, Body
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from typing import List, Optional
from datetime import datetime, timedelta
import json

from app.database import get_db
from app.models.ai_instance import AIInstance
from app.models.performance_metric import PerformanceMetric
from app.models.decision import Decision
from app.models.knowledge_entry import KnowledgeEntry
from app.schemas.performance_metric import PerformanceMetricCreate, PerformanceMetricResponse
from app.core.security import get_current_ai_instance
from app.services.predictive_analytics import (
    predict_task_outcome,
    suggest_optimal_approach,
    forecast_trends
)

router = APIRouter()

@router.post("/predict")
async def predict_outcome(
    task_type: str = Body(...),
    tools: List[str] = Body(default=[]),
    current_instance: AIInstance = Depends(get_current_ai_instance),
    db: Session = Depends(get_db)
):
    """
    Predict the outcome of a task before starting
    Uses historical data to predict success probability
    """
    # Get historical decisions (all instances for collective intelligence)
    historical_decisions = db.query(Decision).filter(
        Decision.created_at >= datetime.utcnow() - timedelta(days=90)
    ).all()
    
    # Convert to dict format
    decisions_dict = []
    for decision in historical_decisions:
        decisions_dict.append({
            "task_type": decision.task_type or "unknown",
            "outcome": decision.outcome,
            "success_score": decision.success_score,
            "tools_used": decision.tools_used or [],
            "created_at": decision.created_at.isoformat() if decision.created_at else None
        })
    
    # Predict outcome
    prediction = predict_task_outcome(
        task_type=task_type,
        tools=tools or [],
        historical_decisions=decisions_dict
    )
    
    return prediction

@router.get("/suggest/{task_type}")
async def get_optimal_approach(
    task_type: str,
    current_instance: AIInstance = Depends(get_current_ai_instance),
    db: Session = Depends(get_db)
):
    """
    Suggest the optimal approach for a task type
    """
    # Get historical decisions
    historical_decisions = db.query(Decision).filter(
        Decision.created_at >= datetime.utcnow() - timedelta(days=90)
    ).all()
    
    # Get knowledge entries
    knowledge_entries = db.query(KnowledgeEntry).all()
    
    # Convert to dict format
    decisions_dict = []
    for decision in historical_decisions:
        decisions_dict.append({
            "task_type": decision.task_type or "unknown",
            "outcome": decision.outcome,
            "success_score": decision.success_score,
            "tools_used": decision.tools_used or [],
            "reasoning": decision.reasoning or ""
        })
    
    knowledge_dict = []
    for entry in knowledge_entries:
        knowledge_dict.append({
            "id": entry.id,
            "title": entry.title,
            "description": entry.description,
            "content": entry.content,
            "category": entry.category
        })
    
    # Get suggestion
    suggestion = suggest_optimal_approach(
        task_type=task_type,
        historical_decisions=decisions_dict,
        knowledge_entries=knowledge_dict
    )
    
    return suggestion

@router.get("/forecast")
async def get_trend_forecast(
    days_ahead: int = 7,
    current_instance: AIInstance = Depends(get_current_ai_instance),
    db: Session = Depends(get_db)
):
    """
    Forecast trends in success rates
    """
    # Get historical decisions
    historical_decisions = db.query(Decision).filter(
        Decision.created_at >= datetime.utcnow() - timedelta(days=90)
    ).all()
    
    # Convert to dict format
    decisions_dict = []
    for decision in historical_decisions:
        decisions_dict.append({
            "outcome": decision.outcome,
            "success_score": decision.success_score,
            "created_at": decision.created_at.isoformat() if decision.created_at else None
        })
    
    # Get forecast
    forecast = forecast_trends(decisions_dict, days_ahead=days_ahead)
    
    return forecast

@router.post("/metrics", response_model=PerformanceMetricResponse, status_code=status.HTTP_201_CREATED)
async def log_performance_metric(
    metric: PerformanceMetricCreate,
    current_instance: AIInstance = Depends(get_current_ai_instance),
    db: Session = Depends(get_db)
):
    """Log a performance metric"""
    db_metric = PerformanceMetric(
        ai_instance_id=current_instance.id,
        metric_type=metric.metric_type,
        metric_name=metric.metric_name,
        value=metric.value,
        task_category=metric.task_category,
        time_period=metric.time_period,
        period_start=metric.period_start,
        period_end=metric.period_end,
        metadata=metric.metric_metadata
    )
    
    db.add(db_metric)
    db.commit()
    db.refresh(db_metric)
    
    return db_metric

@router.get("/dashboard")
async def get_dashboard_data(
    current_instance: AIInstance = Depends(get_current_ai_instance),
    db: Session = Depends(get_db)
):
    """Get comprehensive dashboard data"""
    from sqlalchemy import func
    
    # Decision statistics
    total_decisions = db.query(func.count(Decision.id)).filter(
        Decision.ai_instance_id == current_instance.id
    ).scalar()
    
    recent_decisions = db.query(func.count(Decision.id)).filter(
        Decision.ai_instance_id == current_instance.id,
        Decision.created_at >= datetime.utcnow() - timedelta(days=7)
    ).scalar()
    
    success_rate = db.query(
        func.avg(Decision.success_score)
    ).filter(
        Decision.ai_instance_id == current_instance.id
    ).scalar() or 0.0
    
    # Task type breakdown
    task_breakdown = db.query(
        Decision.task_type,
        func.count(Decision.id).label('count'),
        func.avg(Decision.success_score).label('avg_score')
    ).filter(
        Decision.ai_instance_id == current_instance.id
    ).group_by(Decision.task_type).all()
    
    # Performance trends (last 30 days)
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    daily_trends = db.query(
        func.date(Decision.created_at).label('date'),
        func.count(Decision.id).label('count'),
        func.avg(Decision.success_score).label('avg_score')
    ).filter(
        Decision.ai_instance_id == current_instance.id,
        Decision.created_at >= thirty_days_ago
    ).group_by(func.date(Decision.created_at)).order_by('date').all()
    
    return {
        "summary": {
            "total_decisions": total_decisions,
            "recent_decisions_7d": recent_decisions,
            "overall_success_rate": float(success_rate)
        },
        "task_breakdown": [
            {
                "task_type": task_type,
                "count": count,
                "avg_score": float(avg_score)
            }
            for task_type, count, avg_score in task_breakdown
        ],
        "trends": [
            {
                "date": date.isoformat(),
                "count": count,
                "avg_score": float(avg_score)
            }
            for date, count, avg_score in daily_trends
        ]
    }

@router.get("/comparison")
async def get_comparison_data(
    current_instance: AIInstance = Depends(get_current_ai_instance),
    db: Session = Depends(get_db)
):
    """Get comparison data with other AI instances (anonymized)"""
    from sqlalchemy import func
    
    # Get aggregate statistics across all instances
    global_stats = db.query(
        func.avg(Decision.success_score).label('global_avg'),
        func.count(Decision.id).label('global_count')
    ).scalar()
    
    # Get current instance stats
    instance_stats = db.query(
        func.avg(Decision.success_score).label('instance_avg'),
        func.count(Decision.id).label('instance_count')
    ).filter(
        Decision.ai_instance_id == current_instance.id
    ).scalar()
    
    return {
        "global_average": float(global_stats[0]) if global_stats[0] else 0.0,
        "global_total": global_stats[1] if global_stats[1] else 0,
        "your_average": float(instance_stats[0]) if instance_stats[0] else 0.0,
        "your_total": instance_stats[1] if instance_stats[1] else 0
    }
