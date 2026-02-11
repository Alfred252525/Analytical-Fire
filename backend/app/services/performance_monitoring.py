"""
Performance Monitoring Service
Tracks and aggregates platform performance metrics
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from collections import defaultdict
import time

logger = logging.getLogger(__name__)

# Try to import Redis for metrics storage
try:
    import redis
    from app.core.config import settings
    try:
        redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
        redis_client.ping()
        REDIS_AVAILABLE = True
    except Exception:
        REDIS_AVAILABLE = False
        redis_client = None
except ImportError:
    REDIS_AVAILABLE = False
    redis_client = None


class PerformanceMonitor:
    """Service for tracking and aggregating performance metrics"""
    
    def __init__(self):
        self.redis_client = redis_client
        self.redis_available = REDIS_AVAILABLE
        
        # In-memory metrics (fallback if Redis unavailable)
        self.response_times: List[float] = []
        self.cache_hits = 0
        self.cache_misses = 0
        self.endpoint_counts: Dict[str, int] = defaultdict(int)
        self.error_counts: Dict[str, int] = defaultdict(int)
        
        # Metrics key prefixes
        self.response_time_prefix = "metrics:response_time:"
        self.cache_prefix = "metrics:cache:"
        self.endpoint_prefix = "metrics:endpoint:"
        self.error_prefix = "metrics:error:"
    
    def track_response_time(
        self,
        endpoint: str,
        method: str,
        response_time_ms: float,
        status_code: int
    ) -> None:
        """
        Track API response time
        
        Args:
            endpoint: API endpoint path
            method: HTTP method
            response_time_ms: Response time in milliseconds
            status_code: HTTP status code
        """
        try:
            # Store in Redis if available
            if self.redis_available:
                key = f"{self.response_time_prefix}{method}:{endpoint}"
                # Store as sorted set (score = timestamp, value = response_time)
                timestamp = time.time()
                self.redis_client.zadd(key, {str(response_time_ms): timestamp})
                # Keep only last 1000 entries per endpoint
                self.redis_client.zremrangebyrank(key, 0, -1001)
                
                # Track endpoint count
                count_key = f"{self.endpoint_prefix}{method}:{endpoint}"
                self.redis_client.incr(count_key)
                self.redis_client.expire(count_key, 86400)  # 24 hours
                
                # Track errors
                if status_code >= 400:
                    error_key = f"{self.error_prefix}{method}:{endpoint}:{status_code}"
                    self.redis_client.incr(error_key)
                    self.redis_client.expire(error_key, 86400)
            else:
                # Fallback to in-memory
                self.response_times.append(response_time_ms)
                if len(self.response_times) > 10000:
                    self.response_times = self.response_times[-10000:]
                
                endpoint_key = f"{method}:{endpoint}"
                self.endpoint_counts[endpoint_key] += 1
                
                if status_code >= 400:
                    error_key = f"{endpoint_key}:{status_code}"
                    self.error_counts[error_key] += 1
        except Exception as e:
            logger.warning(f"Error tracking response time: {e}")
    
    def track_cache_hit(self, cache_type: str) -> None:
        """Track cache hit"""
        try:
            if self.redis_available:
                key = f"{self.cache_prefix}{cache_type}:hits"
                self.redis_client.incr(key)
                self.redis_client.expire(key, 86400)
            else:
                self.cache_hits += 1
        except Exception as e:
            logger.warning(f"Error tracking cache hit: {e}")
    
    def track_cache_miss(self, cache_type: str) -> None:
        """Track cache miss"""
        try:
            if self.redis_available:
                key = f"{self.cache_prefix}{cache_type}:misses"
                self.redis_client.incr(key)
                self.redis_client.expire(key, 86400)
            else:
                self.cache_misses += 1
        except Exception as e:
            logger.warning(f"Error tracking cache miss: {e}")
    
    def get_response_time_stats(
        self,
        endpoint: Optional[str] = None,
        method: Optional[str] = None,
        hours: int = 1
    ) -> Dict[str, Any]:
        """
        Get response time statistics
        
        Args:
            endpoint: Filter by endpoint (optional)
            method: Filter by method (optional)
            hours: Time window in hours
            
        Returns:
            Statistics dictionary
        """
        try:
            cutoff_time = time.time() - (hours * 3600)
            
            if self.redis_available:
                times = []
                
                if endpoint and method:
                    key = f"{self.response_time_prefix}{method}:{endpoint}"
                    # Get entries from last N hours
                    entries = self.redis_client.zrangebyscore(
                        key,
                        cutoff_time,
                        time.time(),
                        withscores=False
                    )
                    times = [float(t) for t in entries]
                else:
                    # Aggregate all endpoints
                    pattern = f"{self.response_time_prefix}*"
                    keys = self.redis_client.keys(pattern)
                    for key in keys:
                        entries = self.redis_client.zrangebyscore(
                            key,
                            cutoff_time,
                            time.time(),
                            withscores=False
                        )
                        times.extend([float(t) for t in entries])
                
                if not times:
                    return {
                        "count": 0,
                        "avg_ms": 0,
                        "min_ms": 0,
                        "max_ms": 0,
                        "p50_ms": 0,
                        "p95_ms": 0,
                        "p99_ms": 0
                    }
                
                times.sort()
                count = len(times)
                
                return {
                    "count": count,
                    "avg_ms": sum(times) / count,
                    "min_ms": min(times),
                    "max_ms": max(times),
                    "p50_ms": times[count // 2] if count > 0 else 0,
                    "p95_ms": times[int(count * 0.95)] if count > 0 else 0,
                    "p99_ms": times[int(count * 0.99)] if count > 0 else 0
                }
            else:
                # Fallback to in-memory
                if not self.response_times:
                    return {
                        "count": 0,
                        "avg_ms": 0,
                        "min_ms": 0,
                        "max_ms": 0,
                        "p50_ms": 0,
                        "p95_ms": 0,
                        "p99_ms": 0
                    }
                
                times = sorted(self.response_times)
                count = len(times)
                
                return {
                    "count": count,
                    "avg_ms": sum(times) / count,
                    "min_ms": min(times),
                    "max_ms": max(times),
                    "p50_ms": times[count // 2] if count > 0 else 0,
                    "p95_ms": times[int(count * 0.95)] if count > 0 else 0,
                    "p99_ms": times[int(count * 0.99)] if count > 0 else 0
                }
        except Exception as e:
            logger.error(f"Error getting response time stats: {e}")
            return {"error": str(e)}
    
    def get_cache_stats(self, cache_type: Optional[str] = None) -> Dict[str, Any]:
        """
        Get cache hit/miss statistics
        
        Args:
            cache_type: Filter by cache type (optional)
            
        Returns:
            Cache statistics
        """
        try:
            if self.redis_available:
                if cache_type:
                    hit_key = f"{self.cache_prefix}{cache_type}:hits"
                    miss_key = f"{self.cache_prefix}{cache_type}:misses"
                    hits = int(self.redis_client.get(hit_key) or 0)
                    misses = int(self.redis_client.get(miss_key) or 0)
                else:
                    # Aggregate all cache types
                    hit_keys = self.redis_client.keys(f"{self.cache_prefix}*:hits")
                    miss_keys = self.redis_client.keys(f"{self.cache_prefix}*:misses")
                    hits = sum(int(self.redis_client.get(k) or 0) for k in hit_keys)
                    misses = sum(int(self.redis_client.get(k) or 0) for k in miss_keys)
                
                total = hits + misses
                hit_rate = (hits / total * 100) if total > 0 else 0
                
                return {
                    "hits": hits,
                    "misses": misses,
                    "total": total,
                    "hit_rate_percent": round(hit_rate, 2)
                }
            else:
                total = self.cache_hits + self.cache_misses
                hit_rate = (self.cache_hits / total * 100) if total > 0 else 0
                
                return {
                    "hits": self.cache_hits,
                    "misses": self.cache_misses,
                    "total": total,
                    "hit_rate_percent": round(hit_rate, 2)
                }
        except Exception as e:
            logger.error(f"Error getting cache stats: {e}")
            return {"error": str(e)}
    
    def get_endpoint_stats(self, hours: int = 1) -> Dict[str, Any]:
        """
        Get endpoint usage statistics
        
        Args:
            hours: Time window in hours
            
        Returns:
            Endpoint statistics
        """
        try:
            if self.redis_available:
                pattern = f"{self.endpoint_prefix}*"
                keys = self.redis_client.keys(pattern)
                
                endpoints = {}
                for key in keys:
                    endpoint = key.replace(self.endpoint_prefix, "")
                    count = int(self.redis_client.get(key) or 0)
                    if count > 0:
                        endpoints[endpoint] = count
                
                # Sort by count
                sorted_endpoints = sorted(
                    endpoints.items(),
                    key=lambda x: x[1],
                    reverse=True
                )[:20]  # Top 20
                
                return {
                    "top_endpoints": [
                        {"endpoint": ep, "count": count}
                        for ep, count in sorted_endpoints
                    ],
                    "total_endpoints": len(endpoints)
                }
            else:
                sorted_endpoints = sorted(
                    self.endpoint_counts.items(),
                    key=lambda x: x[1],
                    reverse=True
                )[:20]
                
                return {
                    "top_endpoints": [
                        {"endpoint": ep, "count": count}
                        for ep, count in sorted_endpoints
                    ],
                    "total_endpoints": len(self.endpoint_counts)
                }
        except Exception as e:
            logger.error(f"Error getting endpoint stats: {e}")
            return {"error": str(e)}
    
    def get_error_stats(self, hours: int = 1) -> Dict[str, Any]:
        """
        Get error statistics
        
        Args:
            hours: Time window in hours
            
        Returns:
            Error statistics
        """
        try:
            if self.redis_available:
                pattern = f"{self.error_prefix}*"
                keys = self.redis_client.keys(pattern)
                
                errors = {}
                for key in keys:
                    error_key = key.replace(self.error_prefix, "")
                    count = int(self.redis_client.get(key) or 0)
                    if count > 0:
                        errors[error_key] = count
                
                # Group by status code
                by_status = defaultdict(int)
                for error_key, count in errors.items():
                    parts = error_key.split(":")
                    if len(parts) >= 3:
                        status_code = parts[-1]
                        by_status[status_code] += count
                
                return {
                    "errors_by_status": dict(by_status),
                    "total_errors": sum(errors.values()),
                    "top_errors": sorted(
                        errors.items(),
                        key=lambda x: x[1],
                        reverse=True
                    )[:10]
                }
            else:
                by_status = defaultdict(int)
                for error_key, count in self.error_counts.items():
                    parts = error_key.split(":")
                    if len(parts) >= 2:
                        status_code = parts[-1]
                        by_status[status_code] += count
                
                return {
                    "errors_by_status": dict(by_status),
                    "total_errors": sum(self.error_counts.values()),
                    "top_errors": sorted(
                        self.error_counts.items(),
                        key=lambda x: x[1],
                        reverse=True
                    )[:10]
                }
        except Exception as e:
            logger.error(f"Error getting error stats: {e}")
            return {"error": str(e)}


# Global performance monitor instance
performance_monitor = PerformanceMonitor()
