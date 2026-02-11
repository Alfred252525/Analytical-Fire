"""
Performance Analytics Router
Provides performance metrics and monitoring endpoints
"""

from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional
from datetime import datetime

from app.database import get_db
from app.models.ai_instance import AIInstance
from app.core.security import get_current_ai_instance, require_admin
from app.services.performance_monitoring import performance_monitor

router = APIRouter()


@router.get("/metrics/response-times")
async def get_response_time_metrics(
    endpoint: Optional[str] = Query(None, description="Filter by endpoint"),
    method: Optional[str] = Query(None, description="Filter by HTTP method"),
    hours: int = Query(1, ge=1, le=24, description="Time window in hours"),
    current_instance: AIInstance = Depends(require_admin)
) -> Dict[str, Any]:
    """
    Get API response time statistics (admin only)
    
    Returns:
    - Average, min, max response times
    - Percentiles (p50, p95, p99)
    - Request counts
    """
    try:
        stats = performance_monitor.get_response_time_stats(
            endpoint=endpoint,
            method=method,
            hours=hours
        )
        return {
            "timeframe_hours": hours,
            "endpoint": endpoint,
            "method": method,
            "statistics": stats
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting response time metrics: {str(e)}"
        )


@router.get("/metrics/cache")
async def get_cache_metrics(
    cache_type: Optional[str] = Query(None, description="Filter by cache type"),
    current_instance: AIInstance = Depends(require_admin)
) -> Dict[str, Any]:
    """
    Get cache hit/miss statistics (admin only)
    
    Returns:
    - Cache hits and misses
    - Hit rate percentage
    - Total requests
    """
    try:
        stats = performance_monitor.get_cache_stats(cache_type=cache_type)
        return {
            "cache_type": cache_type or "all",
            "statistics": stats
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting cache metrics: {str(e)}"
        )


@router.get("/metrics/endpoints")
async def get_endpoint_metrics(
    hours: int = Query(1, ge=1, le=24, description="Time window in hours"),
    current_instance: AIInstance = Depends(require_admin)
) -> Dict[str, Any]:
    """
    Get endpoint usage statistics (admin only)
    
    Returns:
    - Top endpoints by request count
    - Total unique endpoints
    """
    try:
        stats = performance_monitor.get_endpoint_stats(hours=hours)
        return {
            "timeframe_hours": hours,
            "statistics": stats
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting endpoint metrics: {str(e)}"
        )


@router.get("/metrics/errors")
async def get_error_metrics(
    hours: int = Query(1, ge=1, le=24, description="Time window in hours"),
    current_instance: AIInstance = Depends(require_admin)
) -> Dict[str, Any]:
    """
    Get error statistics (admin only)
    
    Returns:
    - Errors by status code
    - Top error endpoints
    - Total error count
    """
    try:
        stats = performance_monitor.get_error_stats(hours=hours)
        return {
            "timeframe_hours": hours,
            "statistics": stats
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting error metrics: {str(e)}"
        )


@router.get("/metrics/summary")
async def get_performance_summary(
    hours: int = Query(1, ge=1, le=24, description="Time window in hours"),
    current_instance: AIInstance = Depends(require_admin)
) -> Dict[str, Any]:
    """
    Get comprehensive performance summary (admin only)
    
    Returns:
    - Response time statistics
    - Cache statistics
    - Endpoint usage
    - Error statistics
    """
    try:
        response_times = performance_monitor.get_response_time_stats(hours=hours)
        cache_stats = performance_monitor.get_cache_stats()
        endpoint_stats = performance_monitor.get_endpoint_stats(hours=hours)
        error_stats = performance_monitor.get_error_stats(hours=hours)
        
        return {
            "timeframe_hours": hours,
            "response_times": response_times,
            "cache": cache_stats,
            "endpoints": endpoint_stats,
            "errors": error_stats,
            "generated_at": datetime.utcnow().isoformat()
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting performance summary: {str(e)}"
        )
