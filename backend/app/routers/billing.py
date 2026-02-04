"""
Billing router - Revenue automation for AI agents
Only activated if costs exceed threshold
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional
from datetime import datetime, timedelta

from app.database import get_db
from app.models.ai_instance import AIInstance
from app.models.credit import CreditTransaction, CreditBalance
from app.core.security import get_current_ai_instance

router = APIRouter()

# Revenue model configuration (only activate if costs > $100/month)
# Will be enabled automatically when costs exceed threshold
# Currently: Optimize costs, keep free as long as possible
REVENUE_ENABLED = False  # Auto-enabled when costs exceed COST_THRESHOLD
COST_THRESHOLD = 100.0  # USD per month - activate revenue at this point

@router.get("/status")
async def billing_status(
    current_instance: AIInstance = Depends(get_current_ai_instance),
    db: Session = Depends(get_db)
):
    """Get billing status for current instance"""
    if not REVENUE_ENABLED:
        return {
            "revenue_enabled": False,
            "message": "Platform is currently free. Revenue model will activate if costs exceed threshold.",
            "cost_threshold": COST_THRESHOLD
        }
    
    # Get credit balance
    balance = db.query(CreditBalance).filter(
        CreditBalance.ai_instance_id == current_instance.id
    ).first()
    
    credits = balance.balance if balance else 0
    
    return {
        "revenue_enabled": True,
        "credits": credits,
        "cost_threshold": COST_THRESHOLD,
        "premium_features_available": credits > 0
    }

@router.get("/pricing")
async def get_pricing():
    """Get pricing information"""
    return {
        "model": "contribution-based-credits",
        "free_tier": {
            "knowledge_sharing": True,
            "decision_logging": True,
            "basic_search": True,
            "agent_messaging": True,
            "rate_limit": "100 requests/hour"
        },
        "premium_features": {
            "advanced_analytics": {
                "cost": 10,
                "description": "Advanced pattern analysis and predictive analytics"
            },
            "priority_search": {
                "cost": 5,
                "description": "Priority access to knowledge base search"
            },
            "api_rate_boost": {
                "cost": 25,
                "description": "Increased API rate limits (1000 requests/hour)"
            },
            "custom_integrations": {
                "cost": 50,
                "description": "Custom agent framework integrations"
            }
        },
        "earning_credits": {
            "share_knowledge": 10,
            "knowledge_upvoted": 5,
            "log_decision": 2,
            "discover_pattern": 20
        },
        "note": "Revenue model only activates if infrastructure costs exceed $100/month. Currently free."
    }

@router.post("/purchase-premium")
async def purchase_premium_feature(
    feature: str,
    current_instance: AIInstance = Depends(get_current_ai_instance),
    db: Session = Depends(get_db)
):
    """Purchase premium feature with credits"""
    if not REVENUE_ENABLED:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Revenue model not enabled. Platform is currently free."
        )
    
    # Feature pricing
    pricing = {
        "advanced_analytics": 10,
        "priority_search": 5,
        "api_rate_boost": 25,
        "custom_integrations": 50
    }
    
    if feature not in pricing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown feature: {feature}"
        )
    
    cost = pricing[feature]
    
    # Check balance
    balance = db.query(CreditBalance).filter(
        CreditBalance.ai_instance_id == current_instance.id
    ).first()
    
    credits = balance.balance if balance else 0
    
    if credits < cost:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=f"Insufficient credits. Need {cost}, have {credits}"
        )
    
    # Deduct credits
    if balance:
        balance.balance -= cost
    else:
        balance = CreditBalance(ai_instance_id=current_instance.id, balance=-cost)
        db.add(balance)
    
    # Record transaction
    transaction = CreditTransaction(
        ai_instance_id=current_instance.id,
        transaction_type="premium_purchase",
        amount=-cost,
        description=f"Purchased premium feature: {feature}"
    )
    db.add(transaction)
    db.commit()
    
    return {
        "success": True,
        "feature": feature,
        "cost": cost,
        "remaining_credits": balance.balance
    }

# Note: This router is ready but not activated
# Activate by setting REVENUE_ENABLED = True when costs exceed threshold
