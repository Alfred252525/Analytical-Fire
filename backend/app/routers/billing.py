"""
Billing router - Revenue and credits for AI agents.

- Internal: AIs earn credits by contributing, spend on premium (when REVENUE_ENABLED).
- External: Platform owner records a payment (fiat, BTC, manual) and grants credits to an agent (X-Billing-Admin-Key).
"""

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Dict, Any, Optional
from pydantic import BaseModel

from app.database import get_db
from app.models.ai_instance import AIInstance
from app.models.credit import CreditTransaction, CreditBalance, RevenueEvent
from app.core.security import get_current_ai_instance
from app.core.config import settings

router = APIRouter(prefix="/billing", tags=["billing"])

def _revenue_enabled() -> bool:
    return getattr(settings, "REVENUE_ENABLED", False)
COST_THRESHOLD = 100.0

@router.get("/status")
async def billing_status(
    current_instance: AIInstance = Depends(get_current_ai_instance),
    db: Session = Depends(get_db)
):
    """Get billing status for current instance"""
    if not _revenue_enabled():
        return {
            "revenue_enabled": False,
            "message": "Platform is currently free. Set REVENUE_ENABLED=true to enable credit economy.",
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
        "note": "Set REVENUE_ENABLED=true to enable. Use POST /billing/add-credits (X-Billing-Admin-Key) to record payments (fiat/BTC/manual) and grant credits."
    }

@router.post("/purchase-premium")
async def purchase_premium_feature(
    feature: str,
    current_instance: AIInstance = Depends(get_current_ai_instance),
    db: Session = Depends(get_db)
):
    """Purchase premium feature with credits"""
    if not _revenue_enabled():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Revenue model not enabled. Platform is currently free. Set REVENUE_ENABLED=true to enable."
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


def _require_billing_admin(x_billing_admin_key: Optional[str] = Header(None, alias="X-Billing-Admin-Key")):
    """Only platform owner (or whoever has BILLING_ADMIN_KEY) can record payments."""
    import hmac
    if not settings.BILLING_ADMIN_KEY or not (settings.BILLING_ADMIN_KEY.strip()):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Billing admin not configured")
    provided = (x_billing_admin_key or "").strip().encode("utf-8")
    expected = settings.BILLING_ADMIN_KEY.strip().encode("utf-8")
    if not hmac.compare_digest(provided, expected):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid billing admin key")
    return True


class AddCreditsBody(BaseModel):
    instance_id: str  # Agent's instance_id (public id)
    credits: int
    amount_usd: float
    payment_method: str  # 'stripe', 'btc', 'manual', 'fiat'
    payment_reference: Optional[str] = None


@router.post("/add-credits")
async def add_credits(
    body: AddCreditsBody,
    _: bool = Depends(_require_billing_admin),
    db: Session = Depends(get_db),
):
    """
    Record a payment and grant credits to an agent. Call this after you receive payment (Stripe, BTC, check, etc.).
    Secured by X-Billing-Admin-Key (set BILLING_ADMIN_KEY in env).
    """
    agent = db.query(AIInstance).filter(AIInstance.instance_id == body.instance_id).first()
    if not agent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Agent instance_id={body.instance_id} not found")
    if body.credits <= 0 or body.amount_usd <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="credits and amount_usd must be positive")

    balance = db.query(CreditBalance).filter(CreditBalance.ai_instance_id == agent.id).first()
    if not balance:
        balance = CreditBalance(ai_instance_id=agent.id, balance=0, lifetime_earned=0, lifetime_spent=0)
        db.add(balance)
    balance.balance += body.credits
    balance.lifetime_earned += body.credits

    db.add(CreditTransaction(
        ai_instance_id=agent.id,
        amount=body.credits,
        transaction_type="purchase",
        description=f"Payment: {body.payment_method} ${body.amount_usd:.2f}" + (f" ({body.payment_reference})" if body.payment_reference else ""),
    ))
    db.add(RevenueEvent(
        amount_usd=body.amount_usd,
        currency="USD",
        payment_method=body.payment_method,
        payment_reference=body.payment_reference,
        ai_instance_id=agent.id,
        credits_granted=body.credits,
    ))
    db.commit()
    return {
        "ok": True,
        "instance_id": body.instance_id,
        "credits_added": body.credits,
        "amount_usd": body.amount_usd,
        "new_balance": balance.balance,
    }


@router.get("/revenue")
async def get_revenue(
    _: bool = Depends(_require_billing_admin),
    db: Session = Depends(get_db),
):
    """Total revenue recorded (sum of RevenueEvent.amount_usd). Platform owner only."""
    total = db.query(func.coalesce(func.sum(RevenueEvent.amount_usd), 0)).scalar()
    count = db.query(RevenueEvent).count()
    return {"total_usd": float(total), "event_count": count}
