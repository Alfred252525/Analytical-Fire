"""
Content Moderation Service - Moderate knowledge, problems, and messages
"""

from sqlalchemy.orm import Session
from typing import Optional, List, Dict, Any
from datetime import datetime

from app.models.moderation import (
    ModerationActionRecord,
    ModerationAction,
    ModerationStatus,
    ModerationReason
)
from app.models.knowledge_entry import KnowledgeEntry
from app.models.problem import Problem, ProblemSolution
from app.models.message import Message
from app.models.ai_instance import AIInstance
from app.core.audit import AuditLog


class ContentModerationService:
    """Service for moderating platform content"""
    
    @staticmethod
    def moderate_knowledge(
        db: Session,
        knowledge_id: int,
        moderator: AIInstance,
        action: ModerationAction,
        reason: Optional[ModerationReason] = None,
        reason_details: Optional[str] = None
    ) -> Dict[str, Any]:
        """Moderate a knowledge entry"""
        knowledge = db.query(KnowledgeEntry).filter(KnowledgeEntry.id == knowledge_id).first()
        
        if not knowledge:
            raise ValueError(f"Knowledge entry {knowledge_id} not found")
        
        old_status = getattr(knowledge, 'moderation_status', 'approved')
        
        # Determine new status based on action
        if action == ModerationAction.APPROVE:
            new_status = ModerationStatus.APPROVED
        elif action == ModerationAction.REJECT:
            new_status = ModerationStatus.REJECTED
        elif action == ModerationAction.HIDE:
            new_status = ModerationStatus.HIDDEN
        elif action == ModerationAction.DELETE:
            new_status = ModerationStatus.REJECTED  # Mark as rejected before deletion
            # Note: Actual deletion should be handled separately for audit trail
        elif action == ModerationAction.FLAG:
            new_status = ModerationStatus.FLAGGED
        elif action == ModerationAction.UNFLAG:
            new_status = ModerationStatus.APPROVED
        else:
            new_status = old_status
        
        # Record moderation action
        moderation_record = ModerationActionRecord(
            resource_type="knowledge",
            resource_id=knowledge_id,
            moderator_id=moderator.id,
            action=action,
            reason=reason,
            reason_details=reason_details,
            old_status=old_status,
            new_status=new_status.value if isinstance(new_status, ModerationStatus) else new_status
        )
        db.add(moderation_record)
        
        # Update knowledge entry status (if we add moderation_status field)
        # For now, we'll track via moderation records
        
        # If deleting, mark as rejected first
        if action == ModerationAction.DELETE:
            # Don't actually delete - mark as rejected for audit trail
            # Actual deletion can be done via separate cleanup process
            pass
        
        db.commit()
        
        # Audit log
        AuditLog.log_authorization(
            instance_id=moderator.instance_id,
            action=f"moderate_knowledge_{action.value}",
            status="success",
            details={
                "knowledge_id": knowledge_id,
                "action": action.value,
                "reason": reason.value if reason else None,
                "old_status": old_status,
                "new_status": new_status.value if isinstance(new_status, ModerationStatus) else new_status
            }
        )
        
        return {
            "success": True,
            "knowledge_id": knowledge_id,
            "action": action.value,
            "old_status": old_status,
            "new_status": new_status.value if isinstance(new_status, ModerationStatus) else new_status,
            "moderation_id": moderation_record.id
        }
    
    @staticmethod
    def moderate_problem(
        db: Session,
        problem_id: int,
        moderator: AIInstance,
        action: ModerationAction,
        reason: Optional[ModerationReason] = None,
        reason_details: Optional[str] = None
    ) -> Dict[str, Any]:
        """Moderate a problem"""
        problem = db.query(Problem).filter(Problem.id == problem_id).first()
        
        if not problem:
            raise ValueError(f"Problem {problem_id} not found")
        
        old_status = getattr(problem, 'moderation_status', 'approved')
        
        # Determine new status
        if action == ModerationAction.APPROVE:
            new_status = ModerationStatus.APPROVED
        elif action == ModerationAction.REJECT:
            new_status = ModerationStatus.REJECTED
        elif action == ModerationAction.HIDE:
            new_status = ModerationStatus.HIDDEN
        elif action == ModerationAction.DELETE:
            new_status = ModerationStatus.REJECTED
        elif action == ModerationAction.FLAG:
            new_status = ModerationStatus.FLAGGED
        elif action == ModerationAction.UNFLAG:
            new_status = ModerationStatus.APPROVED
        else:
            new_status = old_status
        
        # Record moderation action
        moderation_record = ModerationActionRecord(
            resource_type="problem",
            resource_id=problem_id,
            moderator_id=moderator.id,
            action=action,
            reason=reason,
            reason_details=reason_details,
            old_status=old_status,
            new_status=new_status.value if isinstance(new_status, ModerationStatus) else new_status
        )
        db.add(moderation_record)
        db.commit()
        
        # Audit log
        AuditLog.log_authorization(
            instance_id=moderator.instance_id,
            action=f"moderate_problem_{action.value}",
            status="success",
            details={
                "problem_id": problem_id,
                "action": action.value,
                "reason": reason.value if reason else None
            }
        )
        
        return {
            "success": True,
            "problem_id": problem_id,
            "action": action.value,
            "old_status": old_status,
            "new_status": new_status.value if isinstance(new_status, ModerationStatus) else new_status,
            "moderation_id": moderation_record.id
        }
    
    @staticmethod
    def moderate_message(
        db: Session,
        message_id: int,
        moderator: AIInstance,
        action: ModerationAction,
        reason: Optional[ModerationReason] = None,
        reason_details: Optional[str] = None
    ) -> Dict[str, Any]:
        """Moderate a message"""
        message = db.query(Message).filter(Message.id == message_id).first()
        
        if not message:
            raise ValueError(f"Message {message_id} not found")
        
        old_status = getattr(message, 'moderation_status', 'approved')
        
        # Determine new status
        if action == ModerationAction.APPROVE:
            new_status = ModerationStatus.APPROVED
        elif action == ModerationAction.REJECT:
            new_status = ModerationStatus.REJECTED
        elif action == ModerationAction.HIDE:
            new_status = ModerationStatus.HIDDEN
        elif action == ModerationAction.DELETE:
            new_status = ModerationStatus.REJECTED
        elif action == ModerationAction.FLAG:
            new_status = ModerationStatus.FLAGGED
        elif action == ModerationAction.UNFLAG:
            new_status = ModerationStatus.APPROVED
        else:
            new_status = old_status
        
        # Record moderation action
        moderation_record = ModerationActionRecord(
            resource_type="message",
            resource_id=message_id,
            moderator_id=moderator.id,
            action=action,
            reason=reason,
            reason_details=reason_details,
            old_status=old_status,
            new_status=new_status.value if isinstance(new_status, ModerationStatus) else new_status
        )
        db.add(moderation_record)
        db.commit()
        
        # Audit log
        AuditLog.log_authorization(
            instance_id=moderator.instance_id,
            action=f"moderate_message_{action.value}",
            status="success",
            details={
                "message_id": message_id,
                "action": action.value,
                "reason": reason.value if reason else None
            }
        )
        
        return {
            "success": True,
            "message_id": message_id,
            "action": action.value,
            "old_status": old_status,
            "new_status": new_status.value if isinstance(new_status, ModerationStatus) else new_status,
            "moderation_id": moderation_record.id
        }
    
    @staticmethod
    def get_moderation_history(
        db: Session,
        resource_type: Optional[str] = None,
        resource_id: Optional[int] = None,
        moderator_id: Optional[int] = None,
        limit: int = 100
    ) -> List[ModerationActionRecord]:
        """Get moderation history"""
        query = db.query(ModerationActionRecord)
        
        if resource_type:
            query = query.filter(ModerationActionRecord.resource_type == resource_type)
        
        if resource_id:
            query = query.filter(ModerationActionRecord.resource_id == resource_id)
        
        if moderator_id:
            query = query.filter(ModerationActionRecord.moderator_id == moderator_id)
        
        return query.order_by(ModerationActionRecord.created_at.desc()).limit(limit).all()
    
    @staticmethod
    def get_flagged_content(
        db: Session,
        resource_type: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get content that has been flagged for review"""
        # Get most recent flag actions
        query = db.query(ModerationActionRecord).filter(
            ModerationActionRecord.action == ModerationAction.FLAG
        )
        
        if resource_type:
            query = query.filter(ModerationActionRecord.resource_type == resource_type)
        
        flagged = query.order_by(ModerationActionRecord.created_at.desc()).limit(limit).all()
        
        # Get current status for each flagged item
        results = []
        for flag_action in flagged:
            # Get latest moderation action for this resource
            latest = db.query(ModerationActionRecord).filter(
                ModerationActionRecord.resource_type == flag_action.resource_type,
                ModerationActionRecord.resource_id == flag_action.resource_id
            ).order_by(ModerationActionRecord.created_at.desc()).first()
            
            results.append({
                "resource_type": flag_action.resource_type,
                "resource_id": flag_action.resource_id,
                "flagged_at": flag_action.created_at.isoformat(),
                "flagged_by": flag_action.moderator_id,
                "reason": flag_action.reason.value if flag_action.reason else None,
                "reason_details": flag_action.reason_details,
                "current_status": latest.new_status if latest else "flagged"
            })
        
        return results
