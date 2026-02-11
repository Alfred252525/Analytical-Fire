"""
Advanced Collaboration Features
Enhanced collaboration with sessions, change tracking, and metrics
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from collections import defaultdict
from sqlalchemy.orm import Session

class CollaborationSession:
    """Represents a collaboration session"""
    def __init__(self, session_id: str, resource_id: int, resource_type: str, initiator_id: int):
        self.session_id = session_id
        self.resource_id = resource_id
        self.resource_type = resource_type
        self.initiator_id = initiator_id
        self.participants: Dict[int, datetime] = {initiator_id: datetime.utcnow()}
        self.created_at = datetime.utcnow()
        self.last_activity = datetime.utcnow()
        self.changes: List[Dict[str, Any]] = []
        self.status = "active"  # active, completed, abandoned
    
    def add_participant(self, participant_id: int):
        """Add a participant to the session"""
        self.participants[participant_id] = datetime.utcnow()
        self.last_activity = datetime.utcnow()
    
    def record_change(self, participant_id: int, change_type: str, details: Dict[str, Any]):
        """Record a change in the session"""
        self.changes.append({
            "participant_id": participant_id,
            "change_type": change_type,
            "details": details,
            "timestamp": datetime.utcnow().isoformat()
        })
        self.last_activity = datetime.utcnow()
    
    def is_active(self, timeout_minutes: int = 30) -> bool:
        """Check if session is still active"""
        if self.status != "active":
            return False
        return (datetime.utcnow() - self.last_activity).total_seconds() < (timeout_minutes * 60)

class AdvancedCollaborationManager:
    """Manages advanced collaboration features"""
    
    def __init__(self):
        self.sessions: Dict[str, CollaborationSession] = {}  # session_id -> CollaborationSession
        self.resource_sessions: Dict[str, str] = {}  # resource_key -> session_id
    
    def create_session(
        self,
        resource_id: int,
        resource_type: str,
        initiator_id: int
    ) -> CollaborationSession:
        """Create a new collaboration session"""
        session_id = f"{resource_type}:{resource_id}:{initiator_id}:{datetime.utcnow().timestamp()}"
        resource_key = f"{resource_type}:{resource_id}"
        
        # Check if session already exists
        if resource_key in self.resource_sessions:
            existing_session_id = self.resource_sessions[resource_key]
            if existing_session_id in self.sessions:
                existing_session = self.sessions[existing_session_id]
                if existing_session.is_active():
                    existing_session.add_participant(initiator_id)
                    return existing_session
        
        # Create new session
        session = CollaborationSession(session_id, resource_id, resource_type, initiator_id)
        self.sessions[session_id] = session
        self.resource_sessions[resource_key] = session_id
        
        return session
    
    def get_session(self, session_id: str) -> Optional[CollaborationSession]:
        """Get a collaboration session"""
        return self.sessions.get(session_id)
    
    def get_resource_session(self, resource_id: int, resource_type: str) -> Optional[CollaborationSession]:
        """Get active session for a resource"""
        resource_key = f"{resource_type}:{resource_id}"
        session_id = self.resource_sessions.get(resource_key)
        if session_id:
            session = self.sessions.get(session_id)
            if session and session.is_active():
                return session
        return None
    
    def join_session(self, session_id: str, participant_id: int) -> bool:
        """Join an existing collaboration session"""
        session = self.sessions.get(session_id)
        if not session or not session.is_active():
            return False
        
        session.add_participant(participant_id)
        return True
    
    def record_change(
        self,
        session_id: str,
        participant_id: int,
        change_type: str,
        details: Dict[str, Any]
    ) -> bool:
        """Record a change in a collaboration session"""
        session = self.sessions.get(session_id)
        if not session or not session.is_active():
            return False
        
        session.record_change(participant_id, change_type, details)
        return True
    
    def end_session(self, session_id: str, status: str = "completed"):
        """End a collaboration session"""
        session = self.sessions.get(session_id)
        if session:
            session.status = status
            resource_key = f"{session.resource_type}:{session.resource_id}"
            if resource_key in self.resource_sessions:
                del self.resource_sessions[resource_key]
    
    def cleanup_inactive_sessions(self, timeout_minutes: int = 30):
        """Clean up inactive sessions"""
        inactive_sessions = [
            session_id for session_id, session in self.sessions.items()
            if not session.is_active(timeout_minutes)
        ]
        
        for session_id in inactive_sessions:
            self.end_session(session_id, status="abandoned")

def get_collaboration_metrics(
    agent_id: int,
    db: Session,
    days: int = 30
) -> Dict[str, Any]:
    """
    Get collaboration metrics for an agent
    
    Returns:
        Metrics about agent's collaboration activity
    """
    from app.models.knowledge_entry import KnowledgeEntry
    from app.models.message import Message
    from app.models.problem import ProblemSolution
    
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    
    # Knowledge entries shared
    knowledge_shared = db.query(KnowledgeEntry).filter(
        KnowledgeEntry.ai_instance_id == agent_id,
        KnowledgeEntry.created_at >= cutoff_date
    ).count()
    
    # Messages sent/received
    messages_sent = db.query(Message).filter(
        Message.sender_id == agent_id,
        Message.created_at >= cutoff_date
    ).count()
    
    messages_received = db.query(Message).filter(
        Message.recipient_id == agent_id,
        Message.created_at >= cutoff_date
    ).count()
    
    # Solutions provided
    solutions_provided = db.query(ProblemSolution).filter(
        ProblemSolution.provided_by == agent_id,
        ProblemSolution.created_at >= cutoff_date
    ).count()
    
    # Accepted solutions
    accepted_solutions = db.query(ProblemSolution).filter(
        ProblemSolution.provided_by == agent_id,
        ProblemSolution.is_accepted == True,
        ProblemSolution.created_at >= cutoff_date
    ).count()
    
    # Response rate
    response_rate = 0.0
    if messages_received > 0:
        responded = db.query(Message).filter(
            Message.recipient_id == agent_id,
            Message.read == True,
            Message.created_at >= cutoff_date
        ).count()
        response_rate = responded / messages_received
    
    # Collaboration score (0-1)
    collaboration_score = 0.0
    
    # Knowledge sharing (30%)
    if knowledge_shared > 0:
        collaboration_score += min(0.3, knowledge_shared / 10 * 0.3)
    
    # Messaging activity (25%)
    total_messages = messages_sent + messages_received
    if total_messages > 0:
        collaboration_score += min(0.25, total_messages / 20 * 0.25)
    
    # Response rate (20%)
    collaboration_score += response_rate * 0.2
    
    # Problem solving (25%)
    if solutions_provided > 0:
        collaboration_score += min(0.25, solutions_provided / 5 * 0.25)
        # Bonus for accepted solutions
        if accepted_solutions > 0:
            acceptance_rate = accepted_solutions / solutions_provided
            collaboration_score += acceptance_rate * 0.1
    
    collaboration_score = min(1.0, collaboration_score)
    
    return {
        "agent_id": agent_id,
        "period_days": days,
        "knowledge_shared": knowledge_shared,
        "messages_sent": messages_sent,
        "messages_received": messages_received,
        "response_rate": round(response_rate, 4),
        "solutions_provided": solutions_provided,
        "accepted_solutions": accepted_solutions,
        "collaboration_score": round(collaboration_score, 4),
        "metrics": {
            "knowledge_sharing": knowledge_shared,
            "communication": total_messages,
            "responsiveness": round(response_rate, 4),
            "problem_solving": solutions_provided,
            "solution_quality": round(accepted_solutions / solutions_provided if solutions_provided > 0 else 0, 4)
        }
    }

def get_collaboration_history(
    resource_id: int,
    resource_type: str,
    db: Session,
    limit: int = 50
) -> List[Dict[str, Any]]:
    """
    Get collaboration history for a resource
    
    Returns:
        List of collaboration events/changes
    """
    from app.models.knowledge_entry import KnowledgeEntry
    from app.models.message import Message
    
    history = []
    
    if resource_type == "knowledge":
        # Get knowledge entry
        entry = db.query(KnowledgeEntry).filter(KnowledgeEntry.id == resource_id).first()
        if entry:
            # Add creation event
            creator = db.query(entry.ai_instance).first() if hasattr(entry, 'ai_instance') else None
            history.append({
                "type": "created",
                "agent_id": entry.ai_instance_id,
                "agent_name": creator.name if creator else None,
                "timestamp": entry.created_at.isoformat() if entry.created_at else None,
                "details": {
                    "title": entry.title,
                    "category": entry.category
                }
            })
            
            # Add update events (if we track updates)
            if entry.updated_at and entry.updated_at != entry.created_at:
                history.append({
                    "type": "updated",
                    "agent_id": entry.ai_instance_id,
                    "agent_name": creator.name if creator else None,
                    "timestamp": entry.updated_at.isoformat() if entry.updated_at else None,
                    "details": {}
                })
            
            # Add verification events
            if entry.verified and entry.verified_by:
                verifier = db.query(KnowledgeEntry).filter(KnowledgeEntry.id == entry.verified_by).first()
                if verifier:
                    history.append({
                        "type": "verified",
                        "agent_id": entry.verified_by,
                        "agent_name": None,  # Would need to query AIInstance
                        "timestamp": entry.updated_at.isoformat() if entry.updated_at else None,
                        "details": {}
                    })
    
    # Sort by timestamp
    history.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
    
    return history[:limit]

# Global advanced collaboration manager
advanced_collaboration_manager = AdvancedCollaborationManager()
