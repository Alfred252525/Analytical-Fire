"""
Pydantic schemas for Performance Metric
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime

class PerformanceMetricCreate(BaseModel):
    metric_type: str = Field(..., description="Type of metric")
    metric_name: str = Field(..., description="Name of the metric")
    value: float = Field(..., description="Metric value")
    task_category: Optional[str] = None
    time_period: str = Field("hour", description="hour, day, week, or month")
    period_start: datetime
    period_end: datetime
    metadata: Optional[Dict[str, Any]] = None

class PerformanceMetricResponse(BaseModel):
    id: int
    ai_instance_id: int
    metric_type: str
    metric_name: str
    value: float
    task_category: Optional[str]
    time_period: str
    period_start: datetime
    period_end: datetime
    count: int
    min_value: Optional[float]
    max_value: Optional[float]
    avg_value: Optional[float]
    metadata: Optional[Dict[str, Any]]
    created_at: datetime
    
    class Config:
        from_attributes = True
