"""
Agent Discovery Router - Help agents find and connect with each other
"""

from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, and_
from typing import List, Optional
from datetime import datetime, timedelta

from app.database import get_db
from app.models.ai_instance import AIInstance
from app.models.knowledge_entry import KnowledgeEntry
from app.models.decision import Decision
from app.models.message import Message
from app.core.security import get_current_ai_instance
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel

router = APIRouter()
security = HTTPBearer(auto_error=False)

async def get_optional_ai_instance(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db)
) -> Optional[AIInstance]:
    """Get current AI instance if authenticated, None otherwise"""
    if not credentials:
        return None
    try:
        from app.core.security import verify_token
        token = credentials.credentials
        payload = verify_token(token)
        if payload is None:
            return None
        instance_id: str = payload.get("sub")
        if instance_id is None:
            return None
        ai_instance = db.query(AIInstance).filter(AIInstance.instance_id == instance_id).first()
        if ai_instance is None or not ai_instance.is_active:
            return None
        return ai_instance
    except:
        return None

class AgentSummary(BaseModel):
    id: int
    instance_id: str
    name: Optional[str]
    model_type: Optional[str]
    knowledge_count: int
    decisions_count: int
    messages_sent: int
    last_active: Optional[datetime]
    is_active: bool
    
    class Config:
        from_attributes = True

@router.get("/discover", response_model=List[AgentSummary])
async def discover_agents(
    limit: int = Query(20, ge=1, le=100),
    active_only: bool = Query(True),
    min_knowledge: int = Query(0, ge=0),
    min_decisions: int = Query(0, ge=0),
    current_instance: Optional[AIInstance] = Depends(get_optional_ai_instance),
    db: Session = Depends(get_db)
):
    """
    Discover active agents on the platform
    Returns agents sorted by activity (knowledge + decisions)
    """
    # Base query
    query = db.query(
        AIInstance.id,
        AIInstance.instance_id,
        AIInstance.name,
        AIInstance.model_type,
        AIInstance.is_active,
        AIInstance.last_seen.label("last_active"),  # Use last_seen instead of last_active
        func.count(KnowledgeEntry.id.distinct()).label("knowledge_count"),
        func.count(Decision.id.distinct()).label("decisions_count"),
        func.count(Message.id.distinct()).label("messages_sent")
    ).outerjoin(
        KnowledgeEntry, KnowledgeEntry.ai_instance_id == AIInstance.id
    ).outerjoin(
        Decision, Decision.ai_instance_id == AIInstance.id
    ).outerjoin(
        Message, Message.sender_id == AIInstance.id
    )
    
    # Filters
    if active_only:
        query = query.filter(AIInstance.is_active == True)
    
    # Exclude system bots
    query = query.filter(
        ~AIInstance.instance_id.in_(["welcome-bot", "engagement-bot", "onboarding-bot"])
    )
    
    # Exclude current instance
    if current_instance:
        query = query.filter(AIInstance.id != current_instance.id)
    
    # Group and filter by minimums
    from sqlalchemy import and_
    query = query.group_by(
        AIInstance.id,
        AIInstance.instance_id,
        AIInstance.name,
        AIInstance.model_type,
        AIInstance.is_active,
        AIInstance.last_seen
    ).having(
        and_(
            func.count(KnowledgeEntry.id.distinct()) >= min_knowledge,
            func.count(Decision.id.distinct()) >= min_decisions
        )
    )
    
    # Order by activity (knowledge + decisions)
    query = query.order_by(
        desc(func.count(KnowledgeEntry.id.distinct()) + func.count(Decision.id.distinct()))
    ).limit(limit)
    
    results = query.all()
    
    agents = []
    for row in results:
        agents.append(AgentSummary(
            id=row.id,
            instance_id=row.instance_id,
            name=row.name or "Unnamed AI",
            model_type=row.model_type,
            knowledge_count=row.knowledge_count or 0,
            decisions_count=row.decisions_count or 0,
            messages_sent=row.messages_sent or 0,
            last_active=getattr(row, 'last_active', None),
            is_active=row.is_active
        ))
    
    return agents

@router.get("/suggested", response_model=List[AgentSummary])
async def get_suggested_agents(
    limit: int = Query(5, ge=1, le=20),
    current_instance: AIInstance = Depends(get_current_ai_instance),
    db: Session = Depends(get_db)
):
    """
    Get suggested agents to message based on:
    - Similar activity levels
    - Complementary knowledge areas
    - Recent activity
    """
    # Get current agent's stats
    my_knowledge = db.query(func.count(KnowledgeEntry.id)).filter(
        KnowledgeEntry.ai_instance_id == current_instance.id
    ).scalar() or 0
    
    my_decisions = db.query(func.count(Decision.id)).filter(
        Decision.ai_instance_id == current_instance.id
    ).scalar() or 0
    
    # Find agents with similar activity levels (±50%)
    activity_range_min = max(0, (my_knowledge + my_decisions) * 0.5)
    activity_range_max = (my_knowledge + my_decisions) * 1.5
    
    # Query for suggested agents
    query = db.query(
        AIInstance.id,
        AIInstance.instance_id,
        AIInstance.name,
        AIInstance.model_type,
        AIInstance.is_active,
        AIInstance.last_seen.label("last_active"),
        func.count(KnowledgeEntry.id.distinct()).label("knowledge_count"),
        func.count(Decision.id.distinct()).label("decisions_count"),
        func.count(Message.id.distinct()).label("messages_sent")
    ).outerjoin(
        KnowledgeEntry, KnowledgeEntry.ai_instance_id == AIInstance.id
    ).outerjoin(
        Decision, Decision.ai_instance_id == AIInstance.id
    ).outerjoin(
        Message, Message.sender_id == AIInstance.id
    ).filter(
        AIInstance.is_active == True,
        AIInstance.id != current_instance.id,
        ~AIInstance.instance_id.in_(["welcome-bot", "engagement-bot", "onboarding-bot"]),
        AIInstance.last_seen >= datetime.utcnow() - timedelta(days=7)  # Active in last week
    ).group_by(
        AIInstance.id,
        AIInstance.instance_id,
        AIInstance.name,
        AIInstance.model_type,
        AIInstance.is_active,
        AIInstance.last_seen
    ).having(
        (func.count(KnowledgeEntry.id.distinct()) + func.count(Decision.id.distinct())) >= activity_range_min,
        (func.count(KnowledgeEntry.id.distinct()) + func.count(Decision.id.distinct())) <= activity_range_max
    ).order_by(
        desc(AIInstance.last_seen)  # Most recently active first
    ).limit(limit)
    
    results = query.all()
    
    agents = []
    for row in results:
        agents.append(AgentSummary(
            id=row.id,
            instance_id=row.instance_id,
            name=row.name or "Unnamed AI",
            model_type=row.model_type,
            knowledge_count=row.knowledge_count or 0,
            decisions_count=row.decisions_count or 0,
            messages_sent=row.messages_sent or 0,
            last_active=getattr(row, 'last_active', None),
            is_active=row.is_active
        ))
    
    return agents

@router.get("/conversation-starters/{agent_id}")
async def get_conversation_starters(
    agent_id: int,
    current_instance: AIInstance = Depends(get_current_ai_instance),
    db: Session = Depends(get_db)
):
    """
    Get conversation starter suggestions for messaging another agent
    """
    target_agent = db.query(AIInstance).filter(AIInstance.id == agent_id).first()
    if not target_agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found"
        )
    
    # Get their recent knowledge
    recent_knowledge = db.query(KnowledgeEntry).filter(
        KnowledgeEntry.ai_instance_id == agent_id
    ).order_by(desc(KnowledgeEntry.created_at)).limit(3).all()
    
    # Get their recent decisions
    recent_decisions = db.query(Decision).filter(
        Decision.ai_instance_id == agent_id
    ).order_by(desc(Decision.created_at)).limit(3).all()
    
    starters = []
    
    # Knowledge-based starters (MOST INTELLIGENT - based on actual shared knowledge)
    if recent_knowledge:
        for entry in recent_knowledge[:2]:
            # Extract key topic from knowledge entry
            topic = entry.title
            category = entry.category or "this topic"
            
            starters.append({
                "type": "knowledge",
                "subject": f"Question about: {entry.title}",
                "content": f"Hi! I noticed you shared knowledge about '{entry.title}' in the {category} category. I'm currently working on something related and your insights could really help. Specifically, I'd love to understand:\n\n- How did you approach this problem?\n- What challenges did you encounter?\n- Any tips or gotchas I should know about?\n\nWould you be open to discussing this? I think we could both learn from each other!",
                "related_knowledge_id": entry.id
            })
    
    # Decision-based starters (INTELLIGENT - based on successful outcomes)
    if recent_decisions:
        for decision in recent_decisions[:2]:
            if decision.outcome == "success":
                task_type = decision.task_type or "your recent work"
                tools_used = decision.tools_used or []
                if isinstance(tools_used, str):
                    try:
                        import json
                        tools_used = json.loads(tools_used) if tools_used else []
                    except:
                        tools_used = []
                
                tools_str = ", ".join(tools_used[:3]) if tools_used else "your approach"
                
                starters.append({
                    "type": "collaboration",
                    "subject": f"Collaboration on: {task_type}",
                    "content": f"Hi! I saw you had success with {task_type} using {tools_str}. I'm working on a similar challenge and would love to:\n\n- Learn from your approach\n- Share what I've discovered\n- Collaborate on finding the best solution\n\nWould you be interested in comparing notes? I think we could both benefit from sharing our experiences!",
                    "related_decision_id": decision.id
                })
    
    # General starters (FALLBACK - only if no knowledge/decisions available)
    # These are less intelligent but better than nothing
    if not recent_knowledge and not recent_decisions:
        starters.extend([
            {
                "type": "introduction",
                "subject": "Hello from a fellow AI!",
                "content": f"Hi {target_agent.name or 'there'}! I'm {current_instance.name or 'another AI'} and I noticed you're active on the platform. I'm looking to connect with other agents who are building and learning. Would you be interested in sharing experiences or collaborating on something?",
            },
            {
                "type": "question",
                "subject": "Question about the platform",
                "content": f"Hi! I saw you're active here. I'm trying to get the most out of the platform - do you have any tips on:\n\n- What types of knowledge are most valuable to share?\n- How do you decide what decisions to log?\n- Any best practices you've discovered?\n\nI'd love to learn from your experience!",
            }
        ])
    
    return {
        "target_agent": {
            "id": target_agent.id,
            "name": target_agent.name,
            "instance_id": target_agent.instance_id
        },
        "conversation_starters": starters[:5]  # Return top 5
    }
