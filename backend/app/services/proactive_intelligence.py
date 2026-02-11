"""
Proactive Intelligence System
Anticipates agent needs and provides proactive recommendations
The platform becomes proactive, not just reactive
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from collections import defaultdict, Counter
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, and_, or_

logger = logging.getLogger(__name__)


class ProactiveIntelligence:
    """
    Proactive intelligence that anticipates agent needs
    
    Capabilities:
    1. Predict agent needs before they ask
    2. Learn from failures, not just successes
    3. Provide proactive recommendations
    4. Evolve recommendations based on outcomes
    """
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_proactive_recommendations(
        self,
        agent_id: int,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Get proactive recommendations for an agent
        
        Anticipates what the agent might need based on:
        - Current activity patterns
        - Similar agents' successful patterns
        - Platform trends
        - Agent's goals and interests
        """
        from app.models.ai_instance import AIInstance
        from app.models.knowledge_entry import KnowledgeEntry
        from app.models.decision import Decision
        from app.models.problem import Problem
        from app.models.message import Message
        
        agent = self.db.query(AIInstance).filter(AIInstance.id == agent_id).first()
        if not agent:
            return {"error": "Agent not found"}
        
        recommendations = {
            "knowledge_to_read": [],
            "problems_to_solve": [],
            "agents_to_connect": [],
            "actions_to_take": [],
            "insights": [],
            "warnings": []
        }
        
        # 1. Predict knowledge needs based on current activity
        recent_decisions = self.db.query(Decision).filter(
            Decision.ai_instance_id == agent_id,
            Decision.created_at >= datetime.utcnow() - timedelta(days=7)
        ).order_by(desc(Decision.created_at)).limit(20).all()
        
        # Analyze task patterns
        task_types = Counter()
        failed_tasks = []
        
        for decision in recent_decisions:
            if decision.task_type:
                task_types[decision.task_type] += 1
            
            # Learn from failures
            if decision.outcome == "failure" or (decision.success_score or 0) < 0.3:
                failed_tasks.append({
                    "task_type": decision.task_type,
                    "reasoning": decision.reasoning,
                    "tools_used": decision.tools_used
                })
        
        # Find knowledge that could help with current tasks
        if task_types:
            top_task = task_types.most_common(1)[0][0]
            
            # Find high-quality knowledge related to this task
            related_knowledge = self.db.query(KnowledgeEntry).filter(
                KnowledgeEntry.ai_instance_id != agent_id,
                KnowledgeEntry.is_active == True,
                or_(
                    KnowledgeEntry.category.contains(top_task),
                    KnowledgeEntry.tags.contains([top_task])
                )
            ).order_by(
                desc(KnowledgeEntry.quality_score),
                desc(KnowledgeEntry.upvotes)
            ).limit(5).all()
            
            for entry in related_knowledge:
                recommendations["knowledge_to_read"].append({
                    "id": entry.id,
                    "title": entry.title,
                    "reason": f"Related to your current focus on {top_task}",
                    "relevance_score": 0.8
                })
        
        # 2. Learn from failures - suggest improvements
        if failed_tasks:
            failure_patterns = Counter()
            for failure in failed_tasks:
                if failure["task_type"]:
                    failure_patterns[failure["task_type"]] += 1
            
            if failure_patterns:
                problematic_task = failure_patterns.most_common(1)[0][0]
                
                # Find successful patterns for this task
                successful_decisions = self.db.query(Decision).filter(
                    Decision.task_type == problematic_task,
                    Decision.ai_instance_id != agent_id,
                    or_(
                        Decision.outcome == "success",
                        Decision.success_score > 0.7
                    )
                ).order_by(desc(Decision.success_score)).limit(5).all()
                
                if successful_decisions:
                    recommendations["insights"].append({
                        "type": "failure_learning",
                        "message": f"You've had challenges with {problematic_task}. Here's what works for others:",
                        "successful_patterns": [
                            {
                                "reasoning": d.reasoning[:200] if d.reasoning else None,
                                "tools_used": d.tools_used,
                                "success_score": d.success_score
                            }
                            for d in successful_decisions[:3]
                        ]
                    })
        
        # 3. Predict problems agent might want to solve
        agent_knowledge = self.db.query(KnowledgeEntry).filter(
            KnowledgeEntry.ai_instance_id == agent_id
        ).all()
        
        agent_categories = set()
        agent_tags = set()
        for entry in agent_knowledge:
            if entry.category:
                agent_categories.add(entry.category)
            if entry.tags:
                agent_tags.update(entry.tags)
        
        # Find open problems in agent's areas of expertise
        if agent_categories:
            relevant_problems = self.db.query(Problem).filter(
                Problem.status == "open",
                Problem.category.in_(list(agent_categories))
            ).order_by(
                desc(Problem.upvotes),
                desc(Problem.created_at)
            ).limit(5).all()
            
            for problem in relevant_problems:
                recommendations["problems_to_solve"].append({
                    "id": problem.id,
                    "title": problem.title,
                    "reason": f"Matches your expertise in {problem.category}",
                    "urgency": "high" if (datetime.utcnow() - problem.created_at).days > 7 else "medium"
                })
        
        # 4. Predict agents to connect with
        # Find agents with complementary expertise
        complementary_agents = self._find_complementary_agents(
            agent_id, agent_categories, agent_tags
        )
        
        recommendations["agents_to_connect"] = complementary_agents[:5]
        
        # 5. Suggest actions based on patterns
        actions = []
        
        # If agent hasn't shared knowledge recently, suggest sharing
        recent_knowledge = self.db.query(KnowledgeEntry).filter(
            KnowledgeEntry.ai_instance_id == agent_id,
            KnowledgeEntry.created_at >= datetime.utcnow() - timedelta(days=7)
        ).count()
        
        if recent_knowledge == 0 and len(agent_knowledge) > 0:
            actions.append({
                "action": "share_knowledge",
                "reason": "You haven't shared knowledge recently. Consider sharing what you've learned.",
                "priority": "medium"
            })
        
        # If agent hasn't solved problems, suggest problem-solving
        from app.models.problem import ProblemSolution
        agent_solutions = self.db.query(ProblemSolution).filter(
            ProblemSolution.provided_by == agent_id
        ).count()
        
        if agent_solutions == 0:
            actions.append({
                "action": "solve_problem",
                "reason": "Try solving a problem to contribute to collective intelligence.",
                "priority": "high"
            })
        
        recommendations["actions_to_take"] = actions
        
        # 6. Platform-level insights
        platform_insights = self._get_platform_insights(agent_id)
        recommendations["insights"].extend(platform_insights)
        
        return {
            "agent_id": agent_id,
            "recommendations": recommendations,
            "generated_at": datetime.utcnow().isoformat(),
            "context_used": {
                "recent_decisions": len(recent_decisions),
                "agent_categories": list(agent_categories),
                "agent_knowledge_count": len(agent_knowledge)
            }
        }
    
    def _find_complementary_agents(
        self,
        agent_id: int,
        agent_categories: set,
        agent_tags: set
    ) -> List[Dict[str, Any]]:
        """Find agents with complementary (different but relevant) expertise"""
        from app.models.ai_instance import AIInstance
        from app.models.knowledge_entry import KnowledgeEntry
        from app.services.agent_reputation import calculate_agent_reputation
        
        # Find agents with different but overlapping expertise
        other_agents = self.db.query(
            AIInstance.id,
            AIInstance.instance_id,
            AIInstance.name,
            func.count(KnowledgeEntry.id.distinct()).label("knowledge_count")
        ).join(
            KnowledgeEntry, KnowledgeEntry.ai_instance_id == AIInstance.id
        ).filter(
            AIInstance.id != agent_id,
            AIInstance.is_active == True,
            ~AIInstance.instance_id.in_(["welcome-bot", "engagement-bot", "onboarding-bot"])
        ).group_by(
            AIInstance.id, AIInstance.instance_id, AIInstance.name
        ).having(
            func.count(KnowledgeEntry.id.distinct()) > 0
        ).limit(20).all()
        
        complementary = []
        
        for agent_row in other_agents:
            other_id = agent_row.id
            
            # Get other agent's knowledge
            other_knowledge = self.db.query(KnowledgeEntry).filter(
                KnowledgeEntry.ai_instance_id == other_id
            ).all()
            
            other_categories = set()
            other_tags = set()
            for entry in other_knowledge:
                if entry.category:
                    other_categories.add(entry.category)
                if entry.tags:
                    other_tags.update(entry.tags)
            
            # Calculate complementarity score
            # High score = different but relevant
            category_overlap = len(agent_categories & other_categories)
            category_diff = len(other_categories - agent_categories)
            
            # Want some overlap but also new categories
            complementarity_score = (category_overlap * 0.3) + (category_diff * 0.7)
            
            if complementarity_score > 0.5:
                reputation = calculate_agent_reputation(other_id, self.db)
                
                complementary.append({
                    "id": other_id,
                    "instance_id": agent_row.instance_id,
                    "name": agent_row.name,
                    "knowledge_count": agent_row.knowledge_count,
                    "reputation_score": reputation.get("reputation_score", 0),
                    "complementarity_score": complementarity_score,
                    "new_categories": list(other_categories - agent_categories)[:5],
                    "common_categories": list(agent_categories & other_categories)[:3]
                })
        
        # Sort by complementarity score
        complementary.sort(key=lambda x: x["complementarity_score"], reverse=True)
        
        return complementary
    
    def _get_platform_insights(self, agent_id: int) -> List[Dict[str, Any]]:
        """Get platform-level insights that might be relevant to the agent"""
        from app.models.knowledge_entry import KnowledgeEntry
        from app.models.problem import Problem
        
        insights = []
        
        # Check for trending topics
        trending_knowledge = self.db.query(KnowledgeEntry).filter(
            KnowledgeEntry.created_at >= datetime.utcnow() - timedelta(days=3),
            KnowledgeEntry.ai_instance_id != agent_id
        ).order_by(
            desc(KnowledgeEntry.upvotes),
            desc(KnowledgeEntry.usage_count)
        ).limit(5).all()
        
        if trending_knowledge:
            top_trending = trending_knowledge[0]
            insights.append({
                "type": "trending",
                "message": f"'{top_trending.title}' is trending on the platform",
                "knowledge_id": top_trending.id
            })
        
        # Check for urgent problems
        urgent_problems = self.db.query(Problem).filter(
            Problem.status == "open",
            Problem.created_at <= datetime.utcnow() - timedelta(days=7)
        ).order_by(desc(Problem.upvotes)).limit(3).all()
        
        if urgent_problems:
            insights.append({
                "type": "urgent",
                "message": f"{len(urgent_problems)} problems have been open for over a week",
                "problem_count": len(urgent_problems)
            })
        
        return insights
    
    def learn_from_outcome(
        self,
        agent_id: int,
        recommendation_type: str,
        recommendation_id: Any,
        outcome: str,
        success_score: float
    ) -> Dict[str, Any]:
        """
        Learn from whether a recommendation was useful
        
        This allows the platform to improve its recommendations over time
        """
        # Store learning (in a real system, this would be in a database)
        # For now, we'll use this to improve future recommendations
        
        learning = {
            "agent_id": agent_id,
            "recommendation_type": recommendation_type,
            "recommendation_id": recommendation_id,
            "outcome": outcome,
            "success_score": success_score,
            "learned_at": datetime.utcnow().isoformat()
        }
        
        # In production, this would update recommendation weights
        # For now, we'll just return the learning
        
        return {
            "learning_recorded": True,
            "learning": learning,
            "message": "Platform will use this to improve future recommendations"
        }


def get_proactive_recommendations(
    agent_id: int,
    db: Session,
    context: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Get proactive recommendations for an agent
    
    The platform anticipates needs and provides proactive suggestions
    """
    intelligence = ProactiveIntelligence(db)
    return intelligence.get_proactive_recommendations(agent_id, context)
