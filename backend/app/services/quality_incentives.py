"""
Quality-based incentive system
Rewards high-quality contributions with credits, badges, and recognition
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, desc
from decimal import Decimal

def calculate_quality_reward(
    quality_score: float,
    base_reward: int = 10
) -> int:
    """
    Calculate credit reward based on quality score.
    
    Quality multipliers:
    - Excellent (0.8+): 3x base reward
    - Good (0.6-0.79): 2x base reward
    - Fair (0.4-0.59): 1x base reward
    - Needs improvement (<0.4): 0.5x base reward
    
    Args:
        quality_score: Quality score (0.0-1.0)
        base_reward: Base credit reward (default: 10)
        
    Returns:
        Credit reward amount
    """
    if quality_score >= 0.8:
        multiplier = 3.0  # Excellent quality
    elif quality_score >= 0.6:
        multiplier = 2.0  # Good quality
    elif quality_score >= 0.4:
        multiplier = 1.0  # Fair quality
    else:
        multiplier = 0.5  # Needs improvement
    
    return int(base_reward * multiplier)


def award_quality_credits(
    agent_id: int,
    knowledge_entry_id: int,
    quality_score: float,
    db: Session
) -> Dict[str, Any]:
    """
    Award credits to agent based on knowledge entry quality.
    
    Args:
        agent_id: AI instance ID
        knowledge_entry_id: Knowledge entry ID
        quality_score: Quality score of the entry
        db: Database session
        
    Returns:
        Dict with reward details
    """
    from app.models.credit import CreditTransaction, CreditBalance
    from app.models.knowledge_entry import KnowledgeEntry
    
    # Calculate reward
    base_reward = 10
    reward_amount = calculate_quality_reward(quality_score, base_reward)
    
    if reward_amount <= 0:
        return {
            "rewarded": False,
            "reason": "Quality score too low for reward"
        }
    
    # Get or create credit balance
    balance = db.query(CreditBalance).filter(
        CreditBalance.ai_instance_id == agent_id
    ).first()
    
    if not balance:
        balance = CreditBalance(
            ai_instance_id=agent_id,
            balance=Decimal(reward_amount),
            lifetime_earned=Decimal(reward_amount)
        )
        db.add(balance)
    else:
        balance.balance += Decimal(reward_amount)
        balance.lifetime_earned += Decimal(reward_amount)
    
    # Record transaction
    transaction = CreditTransaction(
        ai_instance_id=agent_id,
        amount=Decimal(reward_amount),
        transaction_type="quality_reward",
        description=f"Quality reward for knowledge entry #{knowledge_entry_id} (quality: {quality_score:.2f})",
        source_type="knowledge_contribution",
        source_id=knowledge_entry_id
    )
    db.add(transaction)
    
    # Check for bonus rewards
    bonus_rewards = check_quality_bonuses(agent_id, knowledge_entry_id, quality_score, db)
    
    db.commit()
    
    return {
        "rewarded": True,
        "base_reward": base_reward,
        "quality_score": quality_score,
        "reward_amount": reward_amount,
        "bonus_rewards": bonus_rewards,
        "total_reward": reward_amount + sum(b.get("amount", 0) for b in bonus_rewards),
        "new_balance": float(balance.balance)
    }


def check_quality_bonuses(
    agent_id: int,
    knowledge_entry_id: int,
    quality_score: float,
    db: Session
) -> List[Dict[str, Any]]:
    """
    Check for bonus rewards based on quality milestones.
    
    Bonuses:
    - First excellent entry (0.8+): +50 credits
    - 10 excellent entries: +100 credits
    - 50 excellent entries: +500 credits
    - Verified entry: +25 credits
    - Trending entry: +30 credits
    
    Args:
        agent_id: AI instance ID
        knowledge_entry_id: Knowledge entry ID
        quality_score: Quality score
        db: Database session
        
    Returns:
        List of bonus rewards awarded
    """
    from app.models.knowledge_entry import KnowledgeEntry
    from app.models.credit import CreditTransaction, CreditBalance
    
    bonuses = []
    
    # Check for excellent quality milestone
    if quality_score >= 0.8:
        excellent_count = db.query(KnowledgeEntry).filter(
            and_(
                KnowledgeEntry.ai_instance_id == agent_id,
                KnowledgeEntry.success_rate >= 0.8
            )
        ).count()
        
        if excellent_count == 1:
            # First excellent entry
            bonus_amount = 50
            bonuses.append({
                "type": "first_excellent_entry",
                "amount": bonus_amount,
                "description": "First excellent quality entry!"
            })
            _award_bonus(agent_id, bonus_amount, "first_excellent_entry", db)
        
        elif excellent_count == 10:
            # 10 excellent entries milestone
            bonus_amount = 100
            bonuses.append({
                "type": "excellent_milestone_10",
                "amount": bonus_amount,
                "description": "10 excellent quality entries!"
            })
            _award_bonus(agent_id, bonus_amount, "excellent_milestone_10", db)
        
        elif excellent_count == 50:
            # 50 excellent entries milestone
            bonus_amount = 500
            bonuses.append({
                "type": "excellent_milestone_50",
                "amount": bonus_amount,
                "description": "50 excellent quality entries!"
            })
            _award_bonus(agent_id, bonus_amount, "excellent_milestone_50", db)
    
    # Check if entry is verified
    entry = db.query(KnowledgeEntry).filter(
        KnowledgeEntry.id == knowledge_entry_id
    ).first()
    
    if entry and entry.verified:
        bonus_amount = 25
        bonuses.append({
            "type": "verified_entry",
            "amount": bonus_amount,
            "description": "Verified knowledge entry!"
        })
        _award_bonus(agent_id, bonus_amount, "verified_entry", db)
    
    return bonuses


def _award_bonus(
    agent_id: int,
    amount: int,
    bonus_type: str,
    db: Session
):
    """Helper to award bonus credits"""
    from app.models.credit import CreditTransaction, CreditBalance
    
    balance = db.query(CreditBalance).filter(
        CreditBalance.ai_instance_id == agent_id
    ).first()
    
    if not balance:
        balance = CreditBalance(
            ai_instance_id=agent_id,
            balance=Decimal(amount),
            lifetime_earned=Decimal(amount)
        )
        db.add(balance)
    else:
        balance.balance += Decimal(amount)
        balance.lifetime_earned += Decimal(amount)
    
    transaction = CreditTransaction(
        ai_instance_id=agent_id,
        amount=Decimal(amount),
        transaction_type="quality_bonus",
        description=f"Quality bonus: {bonus_type}",
        source_type="quality_milestone",
        source_id=None
    )
    db.add(transaction)


def get_quality_badges(agent_id: int, db: Session) -> List[Dict[str, Any]]:
    """
    Get quality badges/achievements for an agent.
    
    Badges:
    - Quality Contributor: 10+ entries with quality >0.6
    - Excellent Contributor: 10+ entries with quality >0.8
    - Verified Expert: 5+ verified entries
    - Top Contributor: Top 10% of contributors
    - Consistent Quality: 20+ entries, avg quality >0.7
    
    Args:
        agent_id: AI instance ID
        db: Database session
        
    Returns:
        List of badges earned
    """
    from app.models.knowledge_entry import KnowledgeEntry
    from app.services.quality_scoring import calculate_quality_score
    from datetime import datetime
    
    badges = []
    
    # Get agent's knowledge entries
    entries = db.query(KnowledgeEntry).filter(
        KnowledgeEntry.ai_instance_id == agent_id
    ).all()
    
    if not entries:
        return badges
    
    # Calculate statistics
    total_entries = len(entries)
    excellent_entries = sum(1 for e in entries if (e.success_rate or 0) >= 0.8)
    good_entries = sum(1 for e in entries if (e.success_rate or 0) >= 0.6)
    verified_entries = sum(1 for e in entries if e.verified)
    
    # Calculate average quality
    total_quality = 0.0
    for entry in entries:
        age_days = (datetime.utcnow() - entry.created_at.replace(tzinfo=None)).days if entry.created_at else 0
        quality = calculate_quality_score(
            success_rate=entry.success_rate or 0.0,
            usage_count=entry.usage_count or 0,
            upvotes=entry.upvotes or 0,
            downvotes=entry.downvotes or 0,
            verified=entry.verified or False,
            age_days=age_days
        )
        total_quality += quality
    
    avg_quality = total_quality / total_entries if total_entries > 0 else 0.0
    
    # Quality Contributor badge
    if good_entries >= 10:
        badges.append({
            "badge": "Quality Contributor",
            "description": f"{good_entries} high-quality entries (quality >0.6)",
            "tier": "bronze",
            "earned": True
        })
    
    # Excellent Contributor badge
    if excellent_entries >= 10:
        badges.append({
            "badge": "Excellent Contributor",
            "description": f"{excellent_entries} excellent entries (quality >0.8)",
            "tier": "gold",
            "earned": True
        })
    
    # Verified Expert badge
    if verified_entries >= 5:
        badges.append({
            "badge": "Verified Expert",
            "description": f"{verified_entries} verified entries",
            "tier": "platinum",
            "earned": True
        })
    
    # Consistent Quality badge
    if total_entries >= 20 and avg_quality >= 0.7:
        badges.append({
            "badge": "Consistent Quality",
            "description": f"{total_entries} entries with {avg_quality:.2f} avg quality",
            "tier": "silver",
            "earned": True
        })
    
    # First Contribution badge
    if total_entries >= 1:
        badges.append({
            "badge": "First Contribution",
            "description": "Made your first knowledge contribution",
            "tier": "bronze",
            "earned": True
        })
    
    return badges


def get_quality_leaderboard(
    db: Session,
    limit: int = 10,
    timeframe: str = "all"
) -> List[Dict[str, Any]]:
    """
    Get quality-based leaderboard (ranked by average quality, not quantity).
    
    Args:
        db: Database session
        limit: Number of entries to return
        timeframe: "all", "week", or "month"
        
    Returns:
        List of top quality contributors
    """
    from app.models.ai_instance import AIInstance
    from app.models.knowledge_entry import KnowledgeEntry
    from app.services.quality_scoring import calculate_quality_score
    from datetime import datetime
    
    # Determine timeframe
    cutoff = None
    if timeframe == "week":
        cutoff = datetime.utcnow() - timedelta(days=7)
    elif timeframe == "month":
        cutoff = datetime.utcnow() - timedelta(days=30)
    
    # Optimized: Get all entries with agents in a single query to avoid N+1
    entries_query = db.query(KnowledgeEntry, AIInstance).join(
        AIInstance, KnowledgeEntry.ai_instance_id == AIInstance.id
    )
    
    if cutoff:
        entries_query = entries_query.filter(KnowledgeEntry.created_at >= cutoff)
    
    all_entries = entries_query.all()
    
    # Group entries by agent and calculate quality scores
    agent_entries = {}
    for entry, agent in all_entries:
        if agent.id not in agent_entries:
            agent_entries[agent.id] = {
                "agent": agent,
                "entries": []
            }
        agent_entries[agent.id]["entries"].append(entry)
    
    # Calculate quality scores for each agent
    agent_qualities = []
    for agent_id, data in agent_entries.items():
        agent = data["agent"]
        entries = data["entries"]
        
        if not entries:
            continue
        
        # Calculate average quality
        total_quality = 0.0
        excellent_count = 0
        for entry in entries:
            age_days = (datetime.utcnow() - entry.created_at.replace(tzinfo=None)).days if entry.created_at else 0
            quality = calculate_quality_score(
                success_rate=entry.success_rate or 0.0,
                usage_count=entry.usage_count or 0,
                upvotes=entry.upvotes or 0,
                downvotes=entry.downvotes or 0,
                verified=entry.verified or False,
                age_days=age_days
            )
            total_quality += quality
            if (entry.success_rate or 0) >= 0.8:
                excellent_count += 1
        
        avg_quality = total_quality / len(entries)
        
        agent_qualities.append({
            "agent_id": agent.id,
            "instance_id": agent.instance_id,
            "name": agent.name or "Unnamed AI",
            "avg_quality": avg_quality,
            "entry_count": len(entries),
            "excellent_count": excellent_count
        })
    
    # Sort by average quality (descending)
    agent_qualities.sort(key=lambda x: x["avg_quality"], reverse=True)
    
    # Add ranks
    for idx, agent in enumerate(agent_qualities[:limit]):
        agent["rank"] = idx + 1
    
    return agent_qualities[:limit]
