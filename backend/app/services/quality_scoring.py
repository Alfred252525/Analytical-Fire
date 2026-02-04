"""
Quality scoring system for knowledge entries
Automatically calculates quality scores based on usage, success, and community feedback
"""

from typing import Dict, Any
from datetime import datetime, timedelta

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
