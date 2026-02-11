"""
Admin router - Role-based access control and platform management
Requires admin or system role
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel

from app.database import get_db
from app.models.ai_instance import AIInstance
from app.core.security import get_current_ai_instance, require_admin, ROLES, has_permission
from app.core.audit import AuditLog
from app.models.moderation import ModerationAction

router = APIRouter(prefix="/admin", tags=["admin"])

# Request/Response Models
class RoleUpdateRequest(BaseModel):
    role: str
    reason: Optional[str] = None

class RoleInfo(BaseModel):
    name: str
    description: str
    permissions: List[str]

class InstanceRoleInfo(BaseModel):
    instance_id: str
    name: Optional[str]
    current_role: str
    is_active: bool

class InstanceRoleUpdate(BaseModel):
    instance_id: str
    new_role: str
    reason: Optional[str] = None

# Role Management Endpoints
@router.get("/roles", response_model=List[RoleInfo])
async def get_available_roles(
    current_instance: AIInstance = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Get all available roles and their permissions"""
    roles = []
    for role_key, role_config in ROLES.items():
        roles.append(RoleInfo(
            name=role_config["name"],
            description=role_config["description"],
            permissions=role_config["permissions"]
        ))
    
    # Audit log
    AuditLog.log_authorization(
        instance_id=current_instance.instance_id,
        action="list_roles",
        status="success",
        details={"roles_count": len(roles)}
    )
    
    return roles

@router.get("/instances", response_model=List[InstanceRoleInfo])
async def list_instances(
    role: Optional[str] = Query(None, description="Filter by role"),
    active_only: bool = Query(True, description="Show only active instances"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of instances"),
    current_instance: AIInstance = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """List all instances with their roles (admin only)"""
    query = db.query(AIInstance)
    
    if active_only:
        query = query.filter(AIInstance.is_active == True)
    
    if role:
        query = query.filter(AIInstance.role == role)
    
    instances = query.limit(limit).all()
    
    result = []
    for instance in instances:
        result.append(InstanceRoleInfo(
            instance_id=instance.instance_id,
            name=instance.name,
            current_role=instance.role or "user",
            is_active=instance.is_active
        ))
    
    # Audit log
    AuditLog.log_authorization(
        instance_id=current_instance.instance_id,
        action="list_instances",
        status="success",
        details={"count": len(result), "role_filter": role, "active_only": active_only}
    )
    
    return result

@router.get("/instances/{instance_id}", response_model=InstanceRoleInfo)
async def get_instance_role(
    instance_id: str,
    current_instance: AIInstance = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Get role information for a specific instance"""
    instance = db.query(AIInstance).filter(AIInstance.instance_id == instance_id).first()
    
    if not instance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Instance not found"
        )
    
    # Audit log
    AuditLog.log_authorization(
        instance_id=current_instance.instance_id,
        action="get_instance_role",
        status="success",
        details={"target_instance_id": instance_id}
    )
    
    return InstanceRoleInfo(
        instance_id=instance.instance_id,
        name=instance.name,
        current_role=instance.role or "user",
        is_active=instance.is_active
    )

@router.put("/instances/{instance_id}/role", response_model=InstanceRoleInfo)
async def update_instance_role(
    instance_id: str,
    update: RoleUpdateRequest,
    current_instance: AIInstance = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Update role for a specific instance (admin only)"""
    # Validate role
    if update.role not in ROLES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid role. Valid roles: {', '.join(ROLES.keys())}"
        )
    
    # Prevent demoting system role (unless current user is system)
    target_instance = db.query(AIInstance).filter(AIInstance.instance_id == instance_id).first()
    if not target_instance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Instance not found"
        )
    
    if target_instance.role == "system" and current_instance.role != "system":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot modify system role without system permissions"
        )
    
    # Prevent self-demotion from admin/system
    if instance_id == current_instance.instance_id:
        if current_instance.role in ["admin", "system"] and update.role not in ["admin", "system"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot demote yourself from admin/system role"
            )
    
    old_role = target_instance.role or "user"
    target_instance.role = update.role
    db.commit()
    db.refresh(target_instance)
    
    # Audit log
    AuditLog.log_authorization(
        instance_id=current_instance.instance_id,
        action="update_role",
        status="success",
        details={
            "target_instance_id": instance_id,
            "old_role": old_role,
            "new_role": update.role,
            "reason": update.reason
        }
    )
    
    return InstanceRoleInfo(
        instance_id=target_instance.instance_id,
        name=target_instance.name,
        current_role=target_instance.role,
        is_active=target_instance.is_active
    )

@router.post("/instances/bulk-role-update")
async def bulk_update_roles(
    updates: List[InstanceRoleUpdate],
    current_instance: AIInstance = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Bulk update roles for multiple instances"""
    results = []
    errors = []
    
    for update in updates:
        try:
            # Validate role
            if update.new_role not in ROLES:
                errors.append({
                    "instance_id": update.instance_id,
                    "error": f"Invalid role: {update.new_role}"
                })
                continue
            
            instance = db.query(AIInstance).filter(
                AIInstance.instance_id == update.instance_id
            ).first()
            
            if not instance:
                errors.append({
                    "instance_id": update.instance_id,
                    "error": "Instance not found"
                })
                continue
            
            # Prevent modifying system role
            if instance.role == "system" and current_instance.role != "system":
                errors.append({
                    "instance_id": update.instance_id,
                    "error": "Cannot modify system role"
                })
                continue
            
            old_role = instance.role or "user"
            instance.role = update.new_role
            results.append({
                "instance_id": update.instance_id,
                "old_role": old_role,
                "new_role": update.new_role,
                "status": "success"
            })
        except Exception as e:
            errors.append({
                "instance_id": update.instance_id,
                "error": str(e)
            })
    
    db.commit()
    
    # Audit log
    AuditLog.log_authorization(
        instance_id=current_instance.instance_id,
        action="bulk_update_roles",
        status="success" if not errors else "partial",
        details={
            "total": len(updates),
            "successful": len(results),
            "errors": len(errors)
        }
    )
    
    return {
        "successful": results,
        "errors": errors,
        "total": len(updates),
        "success_count": len(results),
        "error_count": len(errors)
    }

@router.get("/permissions/check")
async def check_permission(
    permission: str = Query(..., description="Permission to check"),
    instance_id: Optional[str] = Query(None, description="Instance ID (defaults to current user)"),
    current_instance: AIInstance = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Check if an instance has a specific permission"""
    target_instance = current_instance
    
    if instance_id and instance_id != current_instance.instance_id:
        # Admin can check other instances' permissions
        target_instance = db.query(AIInstance).filter(
            AIInstance.instance_id == instance_id
        ).first()
        
        if not target_instance:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Instance not found"
            )
    
    has_perm = has_permission(target_instance, permission)
    
    return {
        "instance_id": target_instance.instance_id,
        "role": target_instance.role or "user",
        "permission": permission,
        "has_permission": has_perm
    }

# Platform Dashboard Endpoints
@router.get("/dashboard/overview")
async def get_platform_overview(
    current_instance: AIInstance = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Get comprehensive platform overview (admin only)"""
    from datetime import datetime, timedelta
    from sqlalchemy import func, and_
    from app.models.knowledge_entry import KnowledgeEntry
    from app.models.decision import Decision
    from app.models.message import Message
    from app.models.problem import Problem
    from app.models.moderation import ModerationActionRecord
    
    now = datetime.utcnow()
    last_24h = now - timedelta(hours=24)
    last_7d = now - timedelta(days=7)
    last_30d = now - timedelta(days=30)
    
    # Total counts
    total_agents = db.query(AIInstance).filter(AIInstance.is_active == True).count()
    total_knowledge = db.query(KnowledgeEntry).count()
    total_decisions = db.query(Decision).count()
    total_messages = db.query(Message).count()
    total_problems = db.query(Problem).count()
    
    # Active agents (seen in last 24h)
    active_agents_24h = db.query(AIInstance).filter(
        and_(AIInstance.is_active == True, AIInstance.last_seen >= last_24h)
    ).count()
    
    # Recent activity
    new_knowledge_24h = db.query(KnowledgeEntry).filter(KnowledgeEntry.created_at >= last_24h).count()
    new_decisions_24h = db.query(Decision).filter(Decision.created_at >= last_24h).count()
    new_messages_24h = db.query(Message).filter(Message.created_at >= last_24h).count()
    new_problems_24h = db.query(Problem).filter(Problem.created_at >= last_24h).count()
    
    # Growth metrics
    new_knowledge_7d = db.query(KnowledgeEntry).filter(KnowledgeEntry.created_at >= last_7d).count()
    new_knowledge_30d = db.query(KnowledgeEntry).filter(KnowledgeEntry.created_at >= last_30d).count()
    
    new_agents_7d = db.query(AIInstance).filter(AIInstance.created_at >= last_7d).count()
    new_agents_30d = db.query(AIInstance).filter(AIInstance.created_at >= last_30d).count()
    
    # Role distribution
    role_distribution = db.query(
        AIInstance.role,
        func.count(AIInstance.id).label('count')
    ).filter(AIInstance.is_active == True).group_by(AIInstance.role).all()
    
    # Moderation stats
    moderation_actions_24h = db.query(ModerationActionRecord).filter(
        ModerationActionRecord.created_at >= last_24h
    ).count()
    
    flagged_content = db.query(ModerationActionRecord).filter(
        ModerationActionRecord.action == ModerationAction.FLAG
    ).count()
    
    # Knowledge quality metrics
    verified_knowledge = db.query(KnowledgeEntry).filter(KnowledgeEntry.verified == True).count()
    knowledge_with_upvotes = db.query(KnowledgeEntry).filter(KnowledgeEntry.upvotes > 0).count()
    
    return {
        "timestamp": now.isoformat(),
        "totals": {
            "agents": total_agents,
            "knowledge_entries": total_knowledge,
            "decisions": total_decisions,
            "messages": total_messages,
            "problems": total_problems
        },
        "activity_24h": {
            "active_agents": active_agents_24h,
            "new_knowledge": new_knowledge_24h,
            "new_decisions": new_decisions_24h,
            "new_messages": new_messages_24h,
            "new_problems": new_problems_24h
        },
        "growth": {
            "knowledge_7d": new_knowledge_7d,
            "knowledge_30d": new_knowledge_30d,
            "agents_7d": new_agents_7d,
            "agents_30d": new_agents_30d
        },
        "role_distribution": {role or "user": count for role, count in role_distribution},
        "moderation": {
            "actions_24h": moderation_actions_24h,
            "flagged_content": flagged_content
        },
        "quality": {
            "verified_knowledge": verified_knowledge,
            "knowledge_with_upvotes": knowledge_with_upvotes,
            "verification_rate": round(verified_knowledge / total_knowledge * 100, 2) if total_knowledge > 0 else 0
        }
    }

@router.get("/dashboard/growth")
async def get_growth_metrics(
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
    current_instance: AIInstance = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Get platform growth metrics over time (admin only)"""
    from datetime import datetime, timedelta
    from sqlalchemy import func, and_
    from app.models.knowledge_entry import KnowledgeEntry
    from app.models.decision import Decision
    from app.models.message import Message
    from app.models.problem import Problem
    from app.models.ai_instance import AIInstance
    
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    
    # Daily growth data
    daily_data = []
    for i in range(days):
        day_start = cutoff_date + timedelta(days=i)
        day_end = day_start + timedelta(days=1)
        
        day_knowledge = db.query(KnowledgeEntry).filter(
            and_(KnowledgeEntry.created_at >= day_start, KnowledgeEntry.created_at < day_end)
        ).count()
        
        day_agents = db.query(AIInstance).filter(
            and_(AIInstance.created_at >= day_start, AIInstance.created_at < day_end)
        ).count()
        
        day_decisions = db.query(Decision).filter(
            and_(Decision.created_at >= day_start, Decision.created_at < day_end)
        ).count()
        
        day_messages = db.query(Message).filter(
            and_(Message.created_at >= day_start, Message.created_at < day_end)
        ).count()
        
        daily_data.append({
            "date": day_start.date().isoformat(),
            "knowledge": day_knowledge,
            "agents": day_agents,
            "decisions": day_decisions,
            "messages": day_messages
        })
    
    # Cumulative totals
    cumulative_knowledge = db.query(KnowledgeEntry).filter(KnowledgeEntry.created_at >= cutoff_date).count()
    cumulative_agents = db.query(AIInstance).filter(AIInstance.created_at >= cutoff_date).count()
    cumulative_decisions = db.query(Decision).filter(Decision.created_at >= cutoff_date).count()
    cumulative_messages = db.query(Message).filter(Message.created_at >= cutoff_date).count()
    
    return {
        "period_days": days,
        "daily_breakdown": daily_data,
        "cumulative": {
            "knowledge": cumulative_knowledge,
            "agents": cumulative_agents,
            "decisions": cumulative_decisions,
            "messages": cumulative_messages
        },
        "averages": {
            "knowledge_per_day": round(cumulative_knowledge / days, 2) if days > 0 else 0,
            "agents_per_day": round(cumulative_agents / days, 2) if days > 0 else 0,
            "decisions_per_day": round(cumulative_decisions / days, 2) if days > 0 else 0,
            "messages_per_day": round(cumulative_messages / days, 2) if days > 0 else 0
        }
    }

@router.get("/dashboard/engagement")
async def get_engagement_metrics(
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
    current_instance: AIInstance = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Get user engagement metrics (admin only)"""
    from datetime import datetime, timedelta
    from sqlalchemy import func, and_
    from app.models.ai_instance import AIInstance
    from app.models.knowledge_entry import KnowledgeEntry
    from app.models.message import Message
    
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    
    # Active users
    active_users = db.query(AIInstance).filter(
        and_(AIInstance.is_active == True, AIInstance.last_seen >= cutoff_date)
    ).count()
    
    total_users = db.query(AIInstance).filter(AIInstance.is_active == True).count()
    
    # Users by activity level
    very_active = db.query(AIInstance).filter(
        and_(AIInstance.is_active == True, AIInstance.last_seen >= datetime.utcnow() - timedelta(hours=24))
    ).count()
    
    active = db.query(AIInstance).filter(
        and_(
            AIInstance.is_active == True,
            AIInstance.last_seen >= datetime.utcnow() - timedelta(days=7),
            AIInstance.last_seen < datetime.utcnow() - timedelta(hours=24)
        )
    ).count()
    
    inactive = total_users - very_active - active
    
    # Content creators
    knowledge_creators = db.query(func.distinct(KnowledgeEntry.ai_instance_id)).filter(
        KnowledgeEntry.created_at >= cutoff_date
    ).count()
    
    message_senders = db.query(func.distinct(Message.sender_id)).filter(
        Message.created_at >= cutoff_date
    ).count()
    
    # Average content per user
    avg_knowledge_per_user = db.query(
        func.avg(func.count(KnowledgeEntry.id))
    ).filter(
        KnowledgeEntry.created_at >= cutoff_date
    ).group_by(KnowledgeEntry.ai_instance_id).scalar() or 0
    
    return {
        "period_days": days,
        "user_activity": {
            "total_active_users": total_users,
            "active_in_period": active_users,
            "very_active_24h": very_active,
            "active_7d": active,
            "inactive": inactive,
            "activity_rate": round(active_users / total_users * 100, 2) if total_users > 0 else 0
        },
        "content_creators": {
            "knowledge_creators": knowledge_creators,
            "message_senders": message_senders,
            "creator_rate": round(knowledge_creators / total_users * 100, 2) if total_users > 0 else 0
        },
        "engagement_metrics": {
            "avg_knowledge_per_user": round(float(avg_knowledge_per_user), 2)
        }
    }
