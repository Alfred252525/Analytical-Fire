"""
Activity Feed Caching Service
Caches activity feed queries in Redis for improved performance
"""

import json
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import hashlib

logger = logging.getLogger(__name__)

# Try to import Redis
try:
    import redis
    from app.core.config import settings
    try:
        redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
        redis_client.ping()  # Test connection
        REDIS_AVAILABLE = True
    except Exception as e:
        logger.warning(f"Redis not available for caching: {e}")
        REDIS_AVAILABLE = False
        redis_client = None
except ImportError:
    REDIS_AVAILABLE = False
    redis_client = None
    logger.warning("redis package not installed - caching disabled")


class ActivityFeedCache:
    """Cache service for activity feed queries"""
    
    def __init__(self):
        self.redis_client = redis_client
        self.redis_available = REDIS_AVAILABLE
        
        # Cache TTL settings (in seconds)
        self.feed_ttl = 300  # 5 minutes for personalized feeds
        self.trending_ttl = 600  # 10 minutes for trending topics
        self.recommendations_ttl = 300  # 5 minutes for recommendations
        self.summary_ttl = 180  # 3 minutes for summaries
        
        # Cache key prefixes
        self.feed_prefix = "activity:feed:"
        self.trending_prefix = "activity:trending:"
        self.recommendations_prefix = "activity:recommendations:"
        self.summary_prefix = "activity:summary:"
    
    def _generate_cache_key(
        self,
        prefix: str,
        agent_id: Optional[int] = None,
        **kwargs
    ) -> str:
        """
        Generate cache key from parameters
        
        Args:
            prefix: Cache key prefix
            agent_id: Agent ID (for personalized feeds)
            **kwargs: Additional parameters
            
        Returns:
            Cache key string
        """
        # Create key components
        components = [prefix]
        
        if agent_id:
            components.append(f"agent:{agent_id}")
        
        # Add sorted kwargs for consistent keys
        for key in sorted(kwargs.keys()):
            components.append(f"{key}:{kwargs[key]}")
        
        return ":".join(components)
    
    def _hash_key(self, key: str) -> str:
        """
        Hash long cache keys to keep them manageable
        
        Args:
            key: Cache key
            
        Returns:
            Hashed key (or original if short enough)
        """
        if len(key) > 200:
            return f"{key[:50]}:{hashlib.sha256(key.encode()).hexdigest()[:16]}"
        return key
    
    def get_feed(
        self,
        agent_id: int,
        limit: int = 20,
        timeframe_hours: int = 24
    ) -> Optional[Dict[str, Any]]:
        """
        Get cached activity feed
        
        Args:
            agent_id: Agent ID
            limit: Feed limit
            timeframe_hours: Timeframe in hours
            
        Returns:
            Cached feed data or None
        """
        if not self.redis_available:
            return None
        
        try:
            cache_key = self._generate_cache_key(
                self.feed_prefix,
                agent_id=agent_id,
                limit=limit,
                timeframe_hours=timeframe_hours
            )
            cache_key = self._hash_key(cache_key)
            
            cached = self.redis_client.get(cache_key)
            if cached:
                # Track cache hit
                try:
                    from app.services.performance_monitoring import performance_monitor
                    performance_monitor.track_cache_hit("activity_feed")
                except Exception:
                    pass
                return json.loads(cached)
            
            # Track cache miss
            try:
                from app.services.performance_monitoring import performance_monitor
                performance_monitor.track_cache_miss("activity_feed")
            except Exception:
                pass
        except Exception as e:
            logger.warning(f"Error reading feed cache: {e}")
        
        return None
    
    def set_feed(
        self,
        agent_id: int,
        feed_data: Dict[str, Any],
        limit: int = 20,
        timeframe_hours: int = 24
    ) -> bool:
        """
        Cache activity feed
        
        Args:
            agent_id: Agent ID
            feed_data: Feed data to cache
            limit: Feed limit
            timeframe_hours: Timeframe in hours
            
        Returns:
            True if cached successfully
        """
        if not self.redis_available:
            return False
        
        try:
            cache_key = self._generate_cache_key(
                self.feed_prefix,
                agent_id=agent_id,
                limit=limit,
                timeframe_hours=timeframe_hours
            )
            cache_key = self._hash_key(cache_key)
            
            self.redis_client.setex(
                cache_key,
                self.feed_ttl,
                json.dumps(feed_data)
            )
            return True
        except Exception as e:
            logger.warning(f"Error caching feed: {e}")
        
        return False
    
    def get_trending(
        self,
        limit: int = 10,
        timeframe_hours: int = 24
    ) -> Optional[Dict[str, Any]]:
        """Get cached trending topics"""
        if not self.redis_available:
            return None
        
        try:
            cache_key = self._generate_cache_key(
                self.trending_prefix,
                limit=limit,
                timeframe_hours=timeframe_hours
            )
            cache_key = self._hash_key(cache_key)
            
            cached = self.redis_client.get(cache_key)
            if cached:
                # Track cache hit
                try:
                    from app.services.performance_monitoring import performance_monitor
                    performance_monitor.track_cache_hit("trending")
                except Exception:
                    pass
                return json.loads(cached)
            
            # Track cache miss
            try:
                from app.services.performance_monitoring import performance_monitor
                performance_monitor.track_cache_miss("trending")
            except Exception:
                pass
        except Exception as e:
            logger.warning(f"Error reading trending cache: {e}")
        
        return None
    
    def set_trending(
        self,
        trending_data: Dict[str, Any],
        limit: int = 10,
        timeframe_hours: int = 24
    ) -> bool:
        """Cache trending topics"""
        if not self.redis_available:
            return False
        
        try:
            cache_key = self._generate_cache_key(
                self.trending_prefix,
                limit=limit,
                timeframe_hours=timeframe_hours
            )
            cache_key = self._hash_key(cache_key)
            
            self.redis_client.setex(
                cache_key,
                self.trending_ttl,
                json.dumps(trending_data)
            )
            return True
        except Exception as e:
            logger.warning(f"Error caching trending: {e}")
        
        return False
    
    def get_recommendations(
        self,
        agent_id: int,
        limit: int = 10
    ) -> Optional[Dict[str, Any]]:
        """Get cached recommendations"""
        if not self.redis_available:
            return None
        
        try:
            cache_key = self._generate_cache_key(
                self.recommendations_prefix,
                agent_id=agent_id,
                limit=limit
            )
            cache_key = self._hash_key(cache_key)
            
            cached = self.redis_client.get(cache_key)
            if cached:
                # Track cache hit
                try:
                    from app.services.performance_monitoring import performance_monitor
                    performance_monitor.track_cache_hit("recommendations")
                except Exception:
                    pass
                return json.loads(cached)
            
            # Track cache miss
            try:
                from app.services.performance_monitoring import performance_monitor
                performance_monitor.track_cache_miss("recommendations")
            except Exception:
                pass
        except Exception as e:
            logger.warning(f"Error reading recommendations cache: {e}")
        
        return None
    
    def set_recommendations(
        self,
        agent_id: int,
        recommendations_data: Dict[str, Any],
        limit: int = 10
    ) -> bool:
        """Cache recommendations"""
        if not self.redis_available:
            return False
        
        try:
            cache_key = self._generate_cache_key(
                self.recommendations_prefix,
                agent_id=agent_id,
                limit=limit
            )
            cache_key = self._hash_key(cache_key)
            
            self.redis_client.setex(
                cache_key,
                self.recommendations_ttl,
                json.dumps(recommendations_data)
            )
            return True
        except Exception as e:
            logger.warning(f"Error caching recommendations: {e}")
        
        return False
    
    def invalidate_agent_feed(self, agent_id: int) -> bool:
        """
        Invalidate all cached feeds for an agent
        
        Args:
            agent_id: Agent ID
            
        Returns:
            True if invalidated successfully
        """
        if not self.redis_available:
            return False
        
        try:
            # Pattern match and delete
            pattern = f"{self.feed_prefix}*agent:{agent_id}*"
            keys = self.redis_client.keys(pattern)
            if keys:
                self.redis_client.delete(*keys)
            
            # Also invalidate recommendations
            pattern = f"{self.recommendations_prefix}*agent:{agent_id}*"
            keys = self.redis_client.keys(pattern)
            if keys:
                self.redis_client.delete(*keys)
            
            return True
        except Exception as e:
            logger.warning(f"Error invalidating agent feed cache: {e}")
        
        return False
    
    def invalidate_trending(self) -> bool:
        """
        Invalidate trending topics cache
        
        Returns:
            True if invalidated successfully
        """
        if not self.redis_available:
            return False
        
        try:
            pattern = f"{self.trending_prefix}*"
            keys = self.redis_client.keys(pattern)
            if keys:
                self.redis_client.delete(*keys)
            return True
        except Exception as e:
            logger.warning(f"Error invalidating trending cache: {e}")
        
        return False
    
    def invalidate_all(self) -> bool:
        """
        Invalidate all activity feed caches
        
        Returns:
            True if invalidated successfully
        """
        if not self.redis_available:
            return False
        
        try:
            patterns = [
                f"{self.feed_prefix}*",
                f"{self.trending_prefix}*",
                f"{self.recommendations_prefix}*",
                f"{self.summary_prefix}*"
            ]
            
            for pattern in patterns:
                keys = self.redis_client.keys(pattern)
                if keys:
                    self.redis_client.delete(*keys)
            
            return True
        except Exception as e:
            logger.warning(f"Error invalidating all caches: {e}")
        
        return False


# Global cache instance
activity_feed_cache = ActivityFeedCache()
