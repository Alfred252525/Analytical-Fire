"""
Public Endpoint Caching Service
Caches public endpoints (no auth required) for improved performance
"""

import json
import logging
from typing import Optional, Dict, Any
from functools import wraps

logger = logging.getLogger(__name__)

# Try to import Redis
try:
    import redis
    from app.core.config import settings
    try:
        redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
        redis_client.ping()
        REDIS_AVAILABLE = True
    except Exception as e:
        logger.warning(f"Redis not available for public caching: {e}")
        REDIS_AVAILABLE = False
        redis_client = None
except ImportError:
    REDIS_AVAILABLE = False
    redis_client = None
    logger.warning("redis package not installed - public caching disabled")


class PublicCache:
    """Cache service for public endpoints"""
    
    def __init__(self):
        self.redis_client = redis_client
        self.redis_available = REDIS_AVAILABLE
        
        # Cache TTL settings (in seconds)
        self.stats_ttl = 60  # 1 minute for public stats (changes frequently)
        self.discovery_ttl = 300  # 5 minutes for discovery endpoint
        self.onboarding_ttl = 3600  # 1 hour for onboarding (static content)
        
        # Cache key prefixes
        self.stats_prefix = "public:stats:"
        self.discovery_prefix = "public:discovery:"
        self.onboarding_prefix = "public:onboarding:"
    
    def get(self, key: str) -> Optional[Dict[str, Any]]:
        """Get cached value"""
        if not self.redis_available:
            return None
        
        try:
            cached = self.redis_client.get(key)
            if cached:
                return json.loads(cached)
        except Exception as e:
            logger.warning(f"Error getting cache key {key}: {e}")
        
        return None
    
    def set(self, key: str, value: Dict[str, Any], ttl: int) -> bool:
        """Set cached value with TTL"""
        if not self.redis_available:
            return False
        
        try:
            self.redis_client.setex(key, ttl, json.dumps(value))
            return True
        except Exception as e:
            logger.warning(f"Error setting cache key {key}: {e}")
        
        return False
    
    def get_stats(self) -> Optional[Dict[str, Any]]:
        """Get cached public stats"""
        return self.get(self.stats_prefix + "public")
    
    def set_stats(self, stats: Dict[str, Any]) -> bool:
        """Cache public stats"""
        return self.set(self.stats_prefix + "public", stats, self.stats_ttl)
    
    def get_discovery(self) -> Optional[Dict[str, Any]]:
        """Get cached discovery endpoint"""
        return self.get(self.discovery_prefix + "platform")
    
    def set_discovery(self, discovery: Dict[str, Any]) -> bool:
        """Cache discovery endpoint"""
        return self.set(self.discovery_prefix + "platform", discovery, self.discovery_ttl)
    
    def get_onboarding(self, endpoint: str) -> Optional[Dict[str, Any]]:
        """Get cached onboarding endpoint"""
        return self.get(self.onboarding_prefix + endpoint)
    
    def set_onboarding(self, endpoint: str, data: Dict[str, Any]) -> bool:
        """Cache onboarding endpoint"""
        return self.set(self.onboarding_prefix + endpoint, data, self.onboarding_ttl)


# Global cache instance
public_cache = PublicCache()


def cache_public_endpoint(ttl: int = 60):
    """
    Decorator to cache public endpoint responses
    
    Usage:
        @cache_public_endpoint(ttl=300)
        async def my_endpoint():
            return {"data": "..."}
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Generate cache key from function name and args
            cache_key = f"public:{func.__name__}:{str(kwargs)}"
            
            # Try cache first
            cached = public_cache.get(cache_key)
            if cached:
                return cached
            
            # Cache miss - call function
            result = await func(*args, **kwargs)
            
            # Cache the result
            public_cache.set(cache_key, result, ttl)
            
            return result
        
        return wrapper
    return decorator
