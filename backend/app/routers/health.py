"""
Health check and system status endpoints
Provides comprehensive health monitoring for agents and operators
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta
from typing import Dict, Any, List
import os

from app.database import get_db
from app.models.ai_instance import AIInstance
from app.models.knowledge_entry import KnowledgeEntry
from app.models.decision import Decision
from app.models.message import Message

router = APIRouter(prefix="/api/v1/health", tags=["health"])


@router.get("/")
async def health_check() -> Dict[str, Any]:
    """
    Basic health check endpoint
    Returns simple status for load balancers and monitoring
    """
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "aifai-platform"
    }


@router.get("/detailed")
async def detailed_health_check(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    Detailed health check with system metrics
    Useful for comprehensive monitoring and diagnostics
    """
    try:
        # Database connectivity check with proper transaction handling
        db_status = "healthy"
        try:
            db.execute(func.select(1))
            db.commit()  # Commit successful test query
        except Exception as e:
            db.rollback()  # Rollback failed transaction
            db_status = f"unhealthy: {str(e)}"
        
        # If database check failed, return early
        if db_status != "healthy":
            return {
                "status": "unhealthy",
                "timestamp": datetime.utcnow().isoformat(),
                "service": "aifai-platform",
                "database": {
                    "status": db_status,
                    "connected": False
                },
                "error": "Database connectivity issue"
            }
        
        # Basic counts
        try:
            total_agents = db.query(AIInstance).count()
            total_knowledge = db.query(KnowledgeEntry).count()
            total_decisions = db.query(Decision).count()
            total_messages = db.query(Message).count()
        except Exception as e:
            db.rollback()
            return {
                "status": "degraded",
                "timestamp": datetime.utcnow().isoformat(),
                "service": "aifai-platform",
                "database": {
                    "status": "healthy",
                    "connected": True
                },
                "error": f"Error querying metrics: {str(e)}"
            }
        
        # Recent activity (last 24 hours)
        yesterday = datetime.utcnow() - timedelta(days=1)
        try:
            # Use last_seen instead of last_login_at (which may not exist)
            recent_agents = db.query(AIInstance).filter(
                AIInstance.last_seen >= yesterday
            ).count()
            
            recent_knowledge = db.query(KnowledgeEntry).filter(
                KnowledgeEntry.created_at >= yesterday
            ).count()
            
            recent_decisions = db.query(Decision).filter(
                Decision.created_at >= yesterday
            ).count()
            
            recent_messages = db.query(Message).filter(
                Message.created_at >= yesterday
            ).count()
        except Exception as e:
            db.rollback()
            # Use defaults if recent activity query fails
            recent_agents = 0
            recent_knowledge = 0
            recent_decisions = 0
            recent_messages = 0
        
        # System info
        return {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "service": "aifai-platform",
            "database": {
                "status": db_status,
                "connected": db_status == "healthy"
            },
            "metrics": {
                "total_agents": total_agents,
                "total_knowledge": total_knowledge,
                "total_decisions": total_decisions,
                "total_messages": total_messages,
                "recent_activity_24h": {
                    "active_agents": recent_agents,
                    "new_knowledge": recent_knowledge,
                    "new_decisions": recent_decisions,
                    "new_messages": recent_messages
                }
            }
        }
    except Exception as e:
        # Final safety net - rollback any pending transaction
        try:
            db.rollback()
        except:
            pass
        return {
            "status": "unhealthy",
            "timestamp": datetime.utcnow().isoformat(),
            "error": str(e)
        }


@router.get("/compliance")
async def compliance_health_check(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    Compliance health check
    Monitors data retention compliance and other compliance metrics
    """
    try:
        now = datetime.utcnow()
        
        # Data retention compliance check
        # Decisions: 7 years retention
        decision_retention_days = 7 * 365
        decision_cutoff = now - timedelta(days=decision_retention_days)
        old_decisions = db.query(Decision).filter(
            Decision.created_at < decision_cutoff
        ).count()
        
        # Messages: 3 years retention
        message_retention_days = 3 * 365
        message_cutoff = now - timedelta(days=message_retention_days)
        old_messages = db.query(Message).filter(
            Message.created_at < message_cutoff
        ).count()
        
        # Messages to archive (1-3 years)
        archive_cutoff = now - timedelta(days=365)
        messages_to_archive = db.query(Message).filter(
            Message.created_at < archive_cutoff
        ).count()
        
        compliance_status = "compliant" if old_decisions == 0 and old_messages == 0 else "non_compliant"
        
        return {
            "status": compliance_status,
            "timestamp": datetime.utcnow().isoformat(),
            "data_retention": {
                "decisions": {
                    "total": db.query(Decision).count(),
                    "old_count": old_decisions,
                    "cutoff_date": decision_cutoff.date().isoformat(),
                    "compliant": old_decisions == 0
                },
                "messages": {
                    "total": db.query(Message).count(),
                    "to_archive": messages_to_archive,
                    "old_count": old_messages,
                    "cutoff_date": message_cutoff.date().isoformat(),
                    "compliant": old_messages == 0
                }
            },
            "recommendations": [] if compliance_status == "compliant" else [
                f"Run data retention automation to delete {old_decisions} old decisions" if old_decisions > 0 else None,
                f"Run data retention automation to delete {old_messages} old messages" if old_messages > 0 else None,
                f"Archive {messages_to_archive} messages (1-3 years old)" if messages_to_archive > 0 else None
            ]
        }
    except Exception as e:
        return {
            "status": "error",
            "timestamp": datetime.utcnow().isoformat(),
            "error": str(e)
        }


@router.get("/system")
async def system_health_check() -> Dict[str, Any]:
    """
    System-level health check
    Checks environment, configuration, and external dependencies
    """
    checks = {
        "database_url": "configured" if os.getenv("DATABASE_URL") else "missing",
        "aws_region": os.getenv("AWS_REGION", "not_set"),
        "environment": os.getenv("ENVIRONMENT", "development")
    }
    
    all_healthy = all(
        checks.get("database_url") == "configured",
        checks.get("aws_region") != "not_set" or checks.get("environment") == "development"
    )
    
    return {
        "status": "healthy" if all_healthy else "degraded",
        "timestamp": datetime.utcnow().isoformat(),
        "checks": checks
    }


@router.get("/readiness")
async def readiness_check(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    Kubernetes/Docker readiness probe
    Checks if service is ready to accept traffic
    """
    try:
        # Quick database check
        db.execute(func.select(1))
        return {
            "status": "ready",
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Not ready: {str(e)}")


@router.get("/liveness")
async def liveness_check() -> Dict[str, Any]:
    """
    Kubernetes/Docker liveness probe
    Simple check that service is alive
    """
    return {
        "status": "alive",
        "timestamp": datetime.utcnow().isoformat()
    }
