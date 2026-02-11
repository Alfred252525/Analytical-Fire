"""
Rate limiting middleware for API protection
Uses Redis for distributed rate limiting
"""

from fastapi import Request, HTTPException, status
import redis
from typing import Optional

from app.core.config import settings

# Try to import slowapi, make it optional
try:
    from slowapi import Limiter
    from slowapi.util import get_remote_address
    from slowapi.errors import RateLimitExceeded
    SLOWAPI_AVAILABLE = True
except ImportError:
    SLOWAPI_AVAILABLE = False
    # Create dummy classes if slowapi not available
    class Limiter:
        def limit(self, *args, **kwargs):
            def decorator(func):
                return func
            return decorator
    class RateLimitExceeded(Exception):
        pass

# Initialize Redis client for rate limiting
try:
    redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
    redis_client.ping()  # Test connection
    redis_available = True
except Exception:
    redis_available = False
    # Fallback: in-memory rate limiting (not distributed)
    redis_client = None

# Initialize rate limiter (only if slowapi available)
if SLOWAPI_AVAILABLE:
    try:
        from slowapi.util import get_remote_address
        limiter = Limiter(
            key_func=get_remote_address,
            storage_uri=settings.REDIS_URL if redis_available else "memory://",
            default_limits=["1000/hour", "100/minute"]  # Default limits
        )
    except Exception:
        SLOWAPI_AVAILABLE = False
        limiter = Limiter()  # Dummy limiter
else:
    limiter = Limiter()  # Dummy limiter

# Rate limit configurations by endpoint type
RATE_LIMITS = {
    "auth": ["10/minute", "100/hour"],  # Stricter for auth endpoints
    "knowledge": ["60/minute", "1000/hour"],
    "messaging": ["30/minute", "500/hour"],
    "analytics": ["30/minute", "500/hour"],
    "default": ["100/minute", "1000/hour"]
}

def get_rate_limit_for_path(path: str) -> list:
    """Get appropriate rate limit for a given path"""
    if "/auth" in path:
        return RATE_LIMITS["auth"]
    elif "/knowledge" in path:
        return RATE_LIMITS["knowledge"]
    elif "/messaging" in path:
        return RATE_LIMITS["messaging"]
    elif "/analytics" in path:
        return RATE_LIMITS["analytics"]
    else:
        return RATE_LIMITS["default"]

def get_rate_limit_key(request: Request) -> str:
    """Get rate limit key based on instance ID if authenticated, otherwise IP"""
    # Try to get instance ID from request state (set by auth middleware)
    instance_id = getattr(request.state, "instance_id", None)
    if instance_id:
        return f"rate_limit:{instance_id}"
    return get_remote_address(request)

# Custom rate limit exceeded handler
def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded):
    """Custom handler for rate limit exceeded"""
    from app.core.audit import AuditLog
    
    # Log security event
    instance_id = getattr(request.state, "instance_id", None)
    AuditLog.log_security_event(
        instance_id=instance_id,
        event="rate_limit_exceeded",
        severity="medium",
        ip_address=request.client.host if request.client else None,
        details={
            "path": request.url.path,
            "method": request.method,
            "limit": str(exc.detail)
        }
    )
    
    raise HTTPException(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        detail=f"Rate limit exceeded: {exc.detail}. Please try again later."
    )
