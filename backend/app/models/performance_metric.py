"""
Performance Metric model - tracks AI performance over time
"""

from sqlalchemy import Column, Integer, String, DateTime, Float, ForeignKey, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base

class PerformanceMetric(Base):
    __tablename__ = "performance_metrics"
    
    id = Column(Integer, primary_key=True, index=True)
    ai_instance_id = Column(Integer, ForeignKey("ai_instances.id"), nullable=False)
    
    # Metric details
    metric_type = Column(String, index=True)  # "task_success", "response_time", "user_satisfaction", etc.
    metric_name = Column(String, nullable=False)
    value = Column(Float, nullable=False)
    
    # Context
    task_category = Column(String, index=True, nullable=True)
    time_period = Column(String)  # "hour", "day", "week", "month"
    period_start = Column(DateTime(timezone=True))
    period_end = Column(DateTime(timezone=True))
    
    # Aggregations
    count = Column(Integer, default=1)  # Number of data points aggregated
    min_value = Column(Float, nullable=True)
    max_value = Column(Float, nullable=True)
    avg_value = Column(Float, nullable=True)
    
    # Metadata
    metric_metadata = Column(JSON)  # Additional context (renamed from 'metadata' - reserved in SQLAlchemy)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    ai_instance = relationship("AIInstance", backref="performance_metrics")
