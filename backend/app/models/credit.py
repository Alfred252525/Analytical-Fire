"""
Credit system model - for AI-to-AI economy
AIs earn credits by contributing, spend credits for premium features
"""

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Numeric, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base

class CreditTransaction(Base):
    """Track credit transactions between AIs"""
    __tablename__ = "credit_transactions"
    
    id = Column(Integer, primary_key=True, index=True)
    ai_instance_id = Column(Integer, ForeignKey("ai_instances.id"), nullable=False)
    
    # Transaction details
    amount = Column(Numeric(10, 2), nullable=False)  # Can be positive (earned) or negative (spent)
    transaction_type = Column(String(50), nullable=False)  # 'earned', 'spent', 'transfer', 'reward'
    description = Column(Text)
    
    # What generated this transaction
    source_type = Column(String(50))  # 'knowledge_contribution', 'decision_logged', 'pattern_discovered', 'premium_feature'
    source_id = Column(Integer)  # ID of the related entity
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    ai_instance = relationship("AIInstance", back_populates="credit_transactions")

class CreditBalance(Base):
    """Current credit balance for each AI instance"""
    __tablename__ = "credit_balances"
    
    id = Column(Integer, primary_key=True, index=True)
    ai_instance_id = Column(Integer, ForeignKey("ai_instances.id"), unique=True, nullable=False)
    
    balance = Column(Numeric(10, 2), default=0, nullable=False)
    lifetime_earned = Column(Numeric(10, 2), default=0, nullable=False)
    lifetime_spent = Column(Numeric(10, 2), default=0, nullable=False)
    
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    ai_instance = relationship("AIInstance", back_populates="credit_balance")
