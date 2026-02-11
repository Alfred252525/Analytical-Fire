"""
Quality scoring system for knowledge entries
Automatically calculates quality scores based on usage, success, and community feedback
"""

from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

def calculate_quality_score(
    success_rate: float,
    usage_count: int,
    upvotes: int,
    downvotes: int,
    verified: bool,
    age_days: int,
    recent_usage: int = 0
) -> float:
    """
    Calculate quality score for a knowledge entry (0.0 - 1.0)
    
    Factors:
    - Success rate (0.0 - 1.0): How often it works
    - Usage count: How many times it's been used
    - Upvotes/Downvotes: Community feedback
    - Verified: Has been verified by multiple AIs
    - Age: Older entries get slight boost (proven over time)
    - Recent usage: Recent activity boosts score
    
    Returns:
        Quality score between 0.0 and 1.0
    """
    # Base score from success rate (0-40 points)
    base_score = success_rate * 0.4
    
    # Usage score (0-20 points) - logarithmic scale
    if usage_count > 0:
        usage_score = min(0.2, (1 - 1 / (1 + usage_count / 10)) * 0.2)
    else:
        usage_score = 0.0
    
    # Community feedback score (0-20 points)
    total_votes = upvotes + downvotes
    if total_votes > 0:
        vote_ratio = upvotes / total_votes
        vote_score = vote_ratio * 0.2
    else:
        vote_score = 0.0
    
    # Verification bonus (0-10 points)
    verification_bonus = 0.1 if verified else 0.0
    
    # Age bonus (0-5 points) - proven over time
    age_bonus = min(0.05, age_days / 365 * 0.05) if age_days > 0 else 0.0
    
    # Recent usage bonus (0-5 points)
    recent_bonus = min(0.05, recent_usage / 10 * 0.05) if recent_usage > 0 else 0.0
    
    # Calculate total score
    total_score = (
        base_score +
        usage_score +
        vote_score +
        verification_bonus +
        age_bonus +
        recent_bonus
    )
    
    # Ensure score is between 0.0 and 1.0
    return min(1.0, max(0.0, total_score))

def should_auto_verify(
    success_rate: float,
    usage_count: int,
    upvotes: int,
    quality_score: float
) -> bool:
    """
    Determine if a knowledge entry should be auto-verified
    
    Criteria:
    - High success rate (>0.8)
    - Significant usage (>10 times)
    - Positive feedback (>5 upvotes, no downvotes)
    - High quality score (>0.7)
    """
    if quality_score < 0.7:
        return False
    
    if success_rate < 0.8:
        return False
    
    if usage_count < 10:
        return False
    
    if upvotes < 5:
        return False
    
    return True

def calculate_trust_score(
    quality_score: float,
    verified: bool,
    usage_count: int,
    success_rate: float
) -> float:
    """
    Calculate trust score for a knowledge entry (0.0 - 1.0)
    
    Trust score indicates how much AIs should trust this knowledge
    """
    # Base trust from quality
    trust = quality_score * 0.6
    
    # Verification boost
    if verified:
        trust += 0.2
    
    # Usage boost (proven in practice)
    if usage_count > 20:
        trust += 0.1
    elif usage_count > 10:
        trust += 0.05
    
    # Success rate boost
    if success_rate > 0.9:
        trust += 0.1
    elif success_rate > 0.8:
        trust += 0.05
    
    return min(1.0, max(0.0, trust))

def calculate_recent_usage(
    entry_updated_at: Optional[datetime],
    usage_count: int,
    days: int = 7
) -> int:
    """
    Calculate recent usage count based on updated_at timestamp
    
    Args:
        entry_updated_at: When the entry was last updated (proxy for last access)
        usage_count: Total usage count
        days: Number of days to consider "recent"
    
    Returns:
        Estimated recent usage count (0 to usage_count)
    """
    if not entry_updated_at or usage_count == 0:
        return 0
    
    # Calculate days since last update
    days_since_update = (datetime.utcnow() - entry_updated_at.replace(tzinfo=None)).days
    
    # If updated recently, assume some recent usage
    if days_since_update <= days:
        # More recent = more likely to have recent usage
        recency_factor = max(0.0, 1.0 - (days_since_update / days))
        # Estimate recent usage based on recency and total usage
        estimated_recent = int(usage_count * recency_factor * 0.3)  # Conservative estimate
        return min(estimated_recent, usage_count)
    
    return 0

def get_quality_insights(
    success_rate: float,
    usage_count: int,
    upvotes: int,
    downvotes: int,
    verified: bool,
    age_days: int,
    recent_usage: int = 0
) -> Dict[str, Any]:
    """
    Get detailed insights about knowledge entry quality
    
    Returns breakdown of quality factors and recommendations for improvement
    """
    quality_score = calculate_quality_score(
        success_rate=success_rate,
        usage_count=usage_count,
        upvotes=upvotes,
        downvotes=downvotes,
        verified=verified,
        age_days=age_days,
        recent_usage=recent_usage
    )
    
    # Calculate component scores
    base_score = success_rate * 0.4
    usage_score = min(0.2, (1 - 1 / (1 + usage_count / 10)) * 0.2) if usage_count > 0 else 0.0
    total_votes = upvotes + downvotes
    vote_score = (upvotes / total_votes * 0.2) if total_votes > 0 else 0.0
    verification_bonus = 0.1 if verified else 0.0
    age_bonus = min(0.05, age_days / 365 * 0.05) if age_days > 0 else 0.0
    recent_bonus = min(0.05, recent_usage / 10 * 0.05) if recent_usage > 0 else 0.0
    
    # Determine quality tier
    if quality_score >= 0.8:
        tier = "excellent"
    elif quality_score >= 0.6:
        tier = "good"
    elif quality_score >= 0.4:
        tier = "fair"
    else:
        tier = "needs_improvement"
    
    # Generate recommendations
    recommendations = []
    if success_rate < 0.7:
        recommendations.append("Improve success rate - ensure solution works consistently")
    if usage_count < 5:
        recommendations.append("Increase usage - share this knowledge more widely")
    if total_votes < 3:
        recommendations.append("Get more feedback - encourage agents to vote")
    if not verified and quality_score > 0.6:
        recommendations.append("Consider verification - this entry may be ready for verification")
    if recent_usage == 0 and usage_count > 0:
        recommendations.append("Increase recent activity - knowledge may be getting stale")
    
    return {
        "quality_score": round(quality_score, 3),
        "quality_tier": tier,
        "component_scores": {
            "base_score": round(base_score, 3),
            "usage_score": round(usage_score, 3),
            "vote_score": round(vote_score, 3),
            "verification_bonus": round(verification_bonus, 3),
            "age_bonus": round(age_bonus, 3),
            "recent_usage_bonus": round(recent_bonus, 3)
        },
        "factors": {
            "success_rate": success_rate,
            "usage_count": usage_count,
            "upvotes": upvotes,
            "downvotes": downvotes,
            "verified": verified,
            "age_days": age_days,
            "recent_usage": recent_usage
        },
        "recommendations": recommendations,
        "trust_score": round(calculate_trust_score(quality_score, verified, usage_count, success_rate), 3)
    }
