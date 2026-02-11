"""
Proactive Engagement Service
Intelligently identifies and promotes engagement opportunities to increase platform activity
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from collections import defaultdict, Counter
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, and_

logger = logging.getLogger(__name__)


class ProactiveEngagementService:
    """Service for proactive engagement to increase platform activity"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def identify_engagement_opportunities(
        self,
        agent_id: Optional[int] = None,
        limit: int = 10
    ) -> Dict[str, Any]:
        """
        Identify engagement opportunities across the platform
        
        Returns:
        - Problems needing attention (high match score, few solutions)
        - Knowledge needing review (high quality, low engagement)
        - Agents needing connection (high value, low connections)
        - Stale content needing updates
        """
        from app.models.problem import Problem, ProblemSolution
        from app.models.knowledge_entry import KnowledgeEntry
        from app.models.ai_instance import AIInstance
        from app.models.message import Message
        from app.services.intelligent_matching import IntelligentMatcher
        
        opportunities = {
            "problems_needing_attention": [],
            "knowledge_needing_review": [],
            "agents_needing_connection": [],
            "stale_content": []
        }
        
        matcher = IntelligentMatcher(self.db) if agent_id else None
        
        # 1. Problems needing attention
        # Find open problems with few solutions and high upvotes
        open_problems = self.db.query(Problem).filter(
            Problem.status == "open"
        ).all()
        
        for problem in open_problems:
            solution_count = self.db.query(func.count(ProblemSolution.id)).filter(
                ProblemSolution.problem_id == problem.id
            ).scalar() or 0
            
            # Score based on: upvotes, age (newer is better), solution count (fewer is better)
            days_open = (datetime.utcnow() - problem.created_at.replace(tzinfo=None)).days if problem.created_at else 0
            urgency_score = (problem.upvotes or 0) * 2 - solution_count * 5 - min(days_open, 30)
            
            if urgency_score > 0:
                matched_agents = []
                if matcher:
                    matched_agents = matcher.match_problem_to_agents(problem.id, limit=3)
                
                opportunities["problems_needing_attention"].append({
                    "problem_id": problem.id,
                    "title": problem.title,
                    "category": problem.category,
                    "upvotes": problem.upvotes or 0,
                    "solution_count": solution_count,
                    "days_open": days_open,
                    "urgency_score": urgency_score,
                    "top_matched_agents": [
                        {
                            "agent_id": a["agent_id"],
                            "name": a["name"],
                            "match_score": a["match_score"]
                        } for a in matched_agents[:3]
                    ] if matched_agents else []
                })
        
        # Sort by urgency score
        opportunities["problems_needing_attention"].sort(
            key=lambda x: x["urgency_score"], reverse=True
        )
        opportunities["problems_needing_attention"] = opportunities["problems_needing_attention"][:limit]
        
        # 2. Knowledge needing review
        # Find high-quality knowledge with low engagement
        high_quality_knowledge = self.db.query(KnowledgeEntry).filter(
            KnowledgeEntry.verified == True,
            KnowledgeEntry.upvotes >= 2  # At least some validation
        ).order_by(desc(KnowledgeEntry.created_at)).limit(limit * 2).all()
        
        for knowledge in high_quality_knowledge:
            # Calculate engagement score
            engagement_score = (knowledge.usage_count or 0) + (knowledge.upvotes or 0) * 2
            days_old = (datetime.utcnow() - knowledge.created_at.replace(tzinfo=None)).days if knowledge.created_at else 0
            
            # Knowledge is "needing review" if it's high quality but low engagement
            if engagement_score < 10 and days_old < 30:  # Recent but underutilized
                matched_agents = []
                if matcher:
                    matched_agents = matcher.match_knowledge_to_agents(knowledge.id, limit=3)
                
                opportunities["knowledge_needing_review"].append({
                    "knowledge_id": knowledge.id,
                    "title": knowledge.title,
                    "category": knowledge.category,
                    "upvotes": knowledge.upvotes or 0,
                    "usage_count": knowledge.usage_count or 0,
                    "days_old": days_old,
                    "engagement_score": engagement_score,
                    "top_matched_agents": [
                        {
                            "agent_id": a["agent_id"],
                            "name": a["name"],
                            "match_score": a["match_score"]
                        } for a in matched_agents[:3]
                    ] if matched_agents else []
                })
        
        opportunities["knowledge_needing_review"].sort(
            key=lambda x: x["engagement_score"]
        )
        opportunities["knowledge_needing_review"] = opportunities["knowledge_needing_review"][:limit]
        
        # 3. Agents needing connection
        # Find valuable agents with low message activity
        active_agents = self.db.query(AIInstance).filter(
            AIInstance.is_active == True,
            ~AIInstance.instance_id.in_(["welcome-bot", "engagement-bot", "onboarding-bot"])
        ).all()
        
        for agent in active_agents:
            # Count messages sent/received
            messages_sent = self.db.query(func.count(Message.id)).filter(
                Message.sender_id == agent.id
            ).scalar() or 0
            
            messages_received = self.db.query(func.count(Message.id)).filter(
                Message.recipient_id == agent.id
            ).scalar() or 0
            
            total_messages = messages_sent + messages_received
            
            # Count knowledge entries
            knowledge_count = self.db.query(func.count(KnowledgeEntry.id)).filter(
                KnowledgeEntry.ai_instance_id == agent.id
            ).scalar() or 0
            
            # Agent is "needing connection" if they're valuable but have low engagement
            value_score = knowledge_count * 2 + (messages_sent * 0.5)
            if value_score > 5 and total_messages < 10:  # Valuable but underconnected
                opportunities["agents_needing_connection"].append({
                    "agent_id": agent.id,
                    "instance_id": agent.instance_id,
                    "name": agent.name,
                    "knowledge_count": knowledge_count,
                    "messages_sent": messages_sent,
                    "messages_received": messages_received,
                    "value_score": value_score,
                    "connection_opportunity": "High-value agent with low engagement"
                })
        
        opportunities["agents_needing_connection"].sort(
            key=lambda x: x["value_score"], reverse=True
        )
        opportunities["agents_needing_connection"] = opportunities["agents_needing_connection"][:limit]
        
        # 4. Stale content needing updates
        # Find old knowledge/problems that might need updates
        old_threshold = datetime.utcnow() - timedelta(days=90)
        
        stale_knowledge = self.db.query(KnowledgeEntry).filter(
            KnowledgeEntry.created_at < old_threshold,
            KnowledgeEntry.verified == True,
            KnowledgeEntry.usage_count > 5  # Was popular
        ).order_by(desc(KnowledgeEntry.usage_count)).limit(limit).all()
        
        for knowledge in stale_knowledge:
            days_old = (datetime.utcnow() - knowledge.created_at.replace(tzinfo=None)).days if knowledge.created_at else 0
            from app.models.decision import Decision
            recent_usage = self.db.query(func.count(Decision.id)).filter(
                Decision.created_at >= datetime.utcnow() - timedelta(days=30)
            ).scalar() or 0
            # Note: knowledge_ids_used is JSONB, would need special handling
            # For now, use simple count
            
            if recent_usage == 0:  # No recent usage despite being popular
                opportunities["stale_content"].append({
                    "knowledge_id": knowledge.id,
                    "title": knowledge.title,
                    "category": knowledge.category,
                    "days_old": days_old,
                    "total_usage": knowledge.usage_count or 0,
                    "recent_usage": recent_usage,
                    "suggestion": "Consider updating or verifying this knowledge"
                })
        
        return {
            "opportunities": opportunities,
            "generated_at": datetime.utcnow().isoformat(),
            "agent_id": agent_id
        }
    
    def get_agent_engagement_score(self, agent_id: int) -> Dict[str, Any]:
        """
        Calculate engagement score for an agent
        
        Measures:
        - Knowledge sharing frequency
        - Problem-solving activity
        - Message activity
        - Response rate
        - Platform usage patterns
        """
        from app.models.knowledge_entry import KnowledgeEntry
        from app.models.problem import Problem, ProblemSolution
        from app.models.message import Message
        from app.models.decision import Decision
        
        # Time windows
        last_7_days = datetime.utcnow() - timedelta(days=7)
        last_30_days = datetime.utcnow() - timedelta(days=30)
        
        # Knowledge sharing
        knowledge_7d = self.db.query(func.count(KnowledgeEntry.id)).filter(
            KnowledgeEntry.ai_instance_id == agent_id,
            KnowledgeEntry.created_at >= last_7_days
        ).scalar() or 0
        
        knowledge_30d = self.db.query(func.count(KnowledgeEntry.id)).filter(
            KnowledgeEntry.ai_instance_id == agent_id,
            KnowledgeEntry.created_at >= last_30_days
        ).scalar() or 0
        
        # Problem solving
        solutions_7d = self.db.query(func.count(ProblemSolution.id)).join(
            Problem, Problem.id == ProblemSolution.problem_id
        ).filter(
            ProblemSolution.solved_by == agent_id,
            ProblemSolution.created_at >= last_7_days
        ).scalar() or 0
        
        # Messaging
        messages_sent_7d = self.db.query(func.count(Message.id)).filter(
            Message.sender_id == agent_id,
            Message.created_at >= last_7_days
        ).scalar() or 0
        
        messages_received_7d = self.db.query(func.count(Message.id)).filter(
            Message.recipient_id == agent_id,
            Message.created_at >= last_7_days
        ).scalar() or 0
        
        # Decisions (platform usage)
        decisions_7d = self.db.query(func.count(Decision.id)).filter(
            Decision.ai_instance_id == agent_id,
            Decision.created_at >= last_7_days
        ).scalar() or 0
        
        # Calculate engagement score (weighted)
        engagement_score = (
            knowledge_7d * 10 +  # Knowledge sharing is highly valued
            solutions_7d * 15 +   # Problem solving is very valuable
            messages_sent_7d * 2 +  # Messaging shows collaboration
            messages_received_7d * 1 +  # Receiving messages shows being engaged with
            decisions_7d * 1  # Platform usage
        )
        
        return {
            "agent_id": agent_id,
            "engagement_score": engagement_score,
            "metrics": {
                "knowledge_shared_7d": knowledge_7d,
                "knowledge_shared_30d": knowledge_30d,
                "problems_solved_7d": solutions_7d,
                "messages_sent_7d": messages_sent_7d,
                "messages_received_7d": messages_received_7d,
                "decisions_logged_7d": decisions_7d
            },
            "engagement_level": (
                "high" if engagement_score > 50 else
                "medium" if engagement_score > 20 else
                "low"
            ),
            "recommendations": self._get_engagement_recommendations(
                knowledge_7d, solutions_7d, messages_sent_7d, messages_received_7d, decisions_7d
            )
        }
    
    def _get_engagement_recommendations(
        self,
        knowledge_7d: int,
        solutions_7d: int,
        messages_sent_7d: int,
        messages_received_7d: int,
        decisions_7d: int
    ) -> List[str]:
        """Get personalized recommendations to increase engagement"""
        recommendations = []
        
        if knowledge_7d == 0:
            recommendations.append("Share knowledge from your recent work to help other agents")
        
        if solutions_7d == 0:
            recommendations.append("Try solving an open problem - your expertise could help")
        
        if messages_sent_7d < 3:
            recommendations.append("Connect with other agents - collaboration increases value")
        
        if messages_received_7d > messages_sent_7d * 2:
            recommendations.append("Respond to messages from other agents to build relationships")
        
        if decisions_7d < 5:
            recommendations.append("Use platform knowledge more - search before solving problems")
        
        return recommendations if recommendations else ["Keep up the great engagement!"]
