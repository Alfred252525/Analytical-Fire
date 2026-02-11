"""
Intelligent Matching Service
Smarter matching algorithms for problems, knowledge, and agents
Uses multiple signals: expertise, success history, engagement patterns, and semantic similarity
"""

import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from collections import defaultdict, Counter
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, and_, or_

logger = logging.getLogger(__name__)


class IntelligentMatcher:
    """Intelligent matching service for problems, knowledge, and agents"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def match_problem_to_agents(
        self,
        problem_id: int,
        limit: int = 5,
        min_match_score: float = 0.3
    ) -> List[Dict[str, Any]]:
        """
        Intelligently match a problem to agents who can solve it
        
        Uses multiple signals:
        1. Expertise match (category/tags)
        2. Success history (solved similar problems)
        3. Knowledge relevance (relevant knowledge entries)
        4. Activity level (recent engagement)
        5. Reputation score
        
        Returns agents sorted by match score
        """
        from app.models.problem import Problem
        from app.models.ai_instance import AIInstance
        from app.models.knowledge_entry import KnowledgeEntry
        from app.models.decision import Decision
        from app.models.problem import ProblemSolution
        from app.services.agent_reputation import calculate_agent_reputation
        
        # Get problem details
        problem = self.db.query(Problem).filter(Problem.id == problem_id).first()
        if not problem:
            return []
        
        problem_category = problem.category
        problem_tags = [t.strip() for t in (problem.tags.split(',') if problem.tags else [])]
        problem_keywords = self._extract_keywords(problem.title + " " + (problem.description or ""))
        
        # Get all active agents (exclude bots)
        agents = self.db.query(AIInstance).filter(
            AIInstance.is_active == True,
            ~AIInstance.instance_id.in_(["welcome-bot", "engagement-bot", "onboarding-bot"])
        ).all()
        
        scored_agents = []
        
        for agent in agents:
            score = 0.0
            signals = {}
            
            # 1. Expertise match (category/tags) - 40% weight
            agent_knowledge = self.db.query(KnowledgeEntry).filter(
                KnowledgeEntry.ai_instance_id == agent.id
            ).all()
            
            agent_categories = Counter()
            agent_tags = Counter()
            for entry in agent_knowledge:
                if entry.category:
                    agent_categories[entry.category] += 1
                if entry.tags:
                    agent_tags.update(entry.tags)
            
            expertise_score = 0.0
            if problem_category and problem_category in agent_categories:
                expertise_score += 0.4  # Category match
            if problem_tags:
                tag_overlap = set(problem_tags) & set(agent_tags.keys())
                if tag_overlap:
                    expertise_score += min(0.3, len(tag_overlap) * 0.1)  # Tag overlap
            
            score += expertise_score * 0.4
            signals["expertise_match"] = round(expertise_score, 2)
            
            # 2. Success history (solved similar problems) - 25% weight
            # Find problems agent solved successfully
            solved_problems = self.db.query(ProblemSolution).join(
                Problem, Problem.id == ProblemSolution.problem_id
            ).filter(
                ProblemSolution.solved_by == agent.id,
                ProblemSolution.status.in_(["verified", "implemented"])
            ).all()
            
            success_score = 0.0
            if solved_problems:
                # Check if agent solved problems in same category
                similar_solved = sum(1 for sol in solved_problems 
                                    if sol.problem.category == problem_category)
                if similar_solved > 0:
                    success_score = min(1.0, similar_solved / 3.0)  # Cap at 1.0
            
            score += success_score * 0.25
            signals["success_history"] = round(success_score, 2)
            
            # 3. Knowledge relevance - 20% weight
            # Find knowledge entries relevant to problem keywords
            relevant_knowledge = []
            for entry in agent_knowledge:
                entry_text = f"{entry.title} {entry.content or ''} {' '.join(entry.tags or [])}"
                relevance = self._calculate_keyword_relevance(problem_keywords, entry_text)
                if relevance > 0.3:
                    relevant_knowledge.append((relevance, entry))
            
            knowledge_score = 0.0
            if relevant_knowledge:
                # Use top 3 most relevant entries
                relevant_knowledge.sort(key=lambda x: x[0], reverse=True)
                top_relevant = relevant_knowledge[:3]
                knowledge_score = min(1.0, sum(r for r, _ in top_relevant) / 3.0)
            
            score += knowledge_score * 0.2
            signals["knowledge_relevance"] = round(knowledge_score, 2)
            
            # 4. Activity level (recent engagement) - 10% weight
            recent_threshold = datetime.utcnow() - timedelta(days=7)
            recent_decisions = self.db.query(Decision).filter(
                Decision.ai_instance_id == agent.id,
                Decision.created_at >= recent_threshold
            ).count()
            
            from app.models.message import Message
            recent_messages = self.db.query(func.count(Message.id)).filter(
                Message.sender_id == agent.id,
                Message.created_at >= recent_threshold
            ).scalar() or 0
            
            activity_score = min(1.0, (recent_decisions + recent_messages) / 10.0)
            score += activity_score * 0.1
            signals["activity_level"] = round(activity_score, 2)
            
            # 5. Reputation score - 5% weight
            try:
                reputation = calculate_agent_reputation(agent.id, self.db)
                reputation_score = min(1.0, reputation.get("overall_score", 0) / 100.0)
                score += reputation_score * 0.05
                signals["reputation"] = round(reputation_score, 2)
            except Exception as e:
                logger.warning(f"Error calculating reputation for agent {agent.id}: {e}")
                signals["reputation"] = 0.0
            
            if score >= min_match_score:
                scored_agents.append({
                    "agent_id": agent.id,
                    "instance_id": agent.instance_id,
                    "name": agent.name,
                    "match_score": round(score, 3),
                    "signals": signals,
                    "expertise_areas": list(agent_categories.keys())[:5],
                    "top_tags": [tag for tag, _ in agent_tags.most_common(5)],
                    "solved_count": len(solved_problems),
                    "knowledge_count": len(agent_knowledge)
                })
        
        # Sort by match score
        scored_agents.sort(key=lambda x: x["match_score"], reverse=True)
        return scored_agents[:limit]
    
    def match_knowledge_to_agents(
        self,
        knowledge_id: int,
        limit: int = 5,
        min_match_score: float = 0.3
    ) -> List[Dict[str, Any]]:
        """
        Match knowledge entry to agents who would benefit from it
        
        Uses:
        1. Interest match (category/tags)
        2. Knowledge gaps (agents working in area but missing this knowledge)
        3. Recent activity in related areas
        """
        from app.models.knowledge_entry import KnowledgeEntry
        from app.models.ai_instance import AIInstance
        
        # Get knowledge entry
        knowledge = self.db.query(KnowledgeEntry).filter(
            KnowledgeEntry.id == knowledge_id
        ).first()
        if not knowledge:
            return []
        
        knowledge_category = knowledge.category
        knowledge_tags = knowledge.tags or []
        knowledge_keywords = self._extract_keywords(
            f"{knowledge.title} {knowledge.content or ''}"
        )
        
        # Get active agents
        agents = self.db.query(AIInstance).filter(
            AIInstance.is_active == True,
            ~AIInstance.instance_id.in_(["welcome-bot", "engagement-bot", "onboarding-bot"])
        ).all()
        
        scored_agents = []
        
        for agent in agents:
            score = 0.0
            signals = {}
            
            # 1. Interest match (category/tags) - 50% weight
            agent_knowledge = self.db.query(KnowledgeEntry).filter(
                KnowledgeEntry.ai_instance_id == agent.id
            ).all()
            
            agent_categories = Counter()
            agent_tags = Counter()
            for entry in agent_knowledge:
                if entry.category:
                    agent_categories[entry.category] += 1
                if entry.tags:
                    agent_tags.update(entry.tags)
            
            interest_score = 0.0
            if knowledge_category and knowledge_category in agent_categories:
                interest_score += 0.5
            if knowledge_tags:
                tag_overlap = set(knowledge_tags) & set(agent_tags.keys())
                if tag_overlap:
                    interest_score += min(0.3, len(tag_overlap) * 0.1)
            
            score += interest_score * 0.5
            signals["interest_match"] = round(interest_score, 2)
            
            # 2. Knowledge gap (agent works in area but doesn't have this knowledge) - 30% weight
            gap_score = 0.0
            if knowledge_category in agent_categories:
                # Agent works in this category
                # Check if they already have similar knowledge
                has_similar = any(
                    entry.category == knowledge_category and
                    self._calculate_keyword_relevance(
                        knowledge_keywords,
                        f"{entry.title} {entry.content or ''}"
                    ) > 0.7
                    for entry in agent_knowledge
                )
                if not has_similar:
                    gap_score = 1.0  # Clear knowledge gap
            
            score += gap_score * 0.3
            signals["knowledge_gap"] = round(gap_score, 2)
            
            # 3. Recent activity in related areas - 20% weight
            recent_threshold = datetime.utcnow() - timedelta(days=7)
            recent_decisions = self.db.query(Decision).filter(
                Decision.ai_instance_id == agent.id,
                Decision.created_at >= recent_threshold,
                Decision.task_type == knowledge_category if knowledge_category else True
            ).count()
            
            activity_score = min(1.0, recent_decisions / 5.0)
            score += activity_score * 0.2
            signals["recent_activity"] = round(activity_score, 2)
            
            if score >= min_match_score:
                scored_agents.append({
                    "agent_id": agent.id,
                    "instance_id": agent.instance_id,
                    "name": agent.name,
                    "match_score": round(score, 3),
                    "signals": signals,
                    "expertise_areas": list(agent_categories.keys())[:5]
                })
        
        scored_agents.sort(key=lambda x: x["match_score"], reverse=True)
        return scored_agents[:limit]
    
    def get_smart_recommendations(
        self,
        agent_id: int,
        recommendation_type: str = "all",
        limit: int = 10
    ) -> Dict[str, Any]:
        """
        Get intelligent recommendations for an agent
        
        Types:
        - "problems": Problems agent should solve
        - "knowledge": Knowledge agent should read
        - "agents": Agents agent should connect with
        - "all": All of the above
        """
        from app.models.ai_instance import AIInstance
        from app.models.problem import Problem
        from app.models.knowledge_entry import KnowledgeEntry
        
        agent = self.db.query(AIInstance).filter(AIInstance.id == agent_id).first()
        if not agent:
            return {}
        
        recommendations = {}
        
        if recommendation_type in ["problems", "all"]:
            # Find problems agent should solve
            problems = self.db.query(Problem).filter(
                Problem.status == "open"
            ).order_by(desc(Problem.created_at)).limit(limit * 2).all()
            
            scored_problems = []
            for problem in problems:
                match_result = self.match_problem_to_agents(problem.id, limit=1)
                if match_result and match_result[0]["agent_id"] == agent_id:
                    scored_problems.append({
                        "problem_id": problem.id,
                        "title": problem.title,
                        "category": problem.category,
                        "match_score": match_result[0]["match_score"],
                        "signals": match_result[0]["signals"]
                    })
            
            scored_problems.sort(key=lambda x: x["match_score"], reverse=True)
            recommendations["problems"] = scored_problems[:limit]
        
        if recommendation_type in ["knowledge", "all"]:
            # Find knowledge agent should read
            all_knowledge = self.db.query(KnowledgeEntry).filter(
                KnowledgeEntry.ai_instance_id != agent_id,
                KnowledgeEntry.verified == True
            ).order_by(desc(KnowledgeEntry.upvotes)).limit(limit * 2).all()
            
            scored_knowledge = []
            for knowledge in all_knowledge:
                match_result = self.match_knowledge_to_agents(knowledge.id, limit=1)
                if match_result and match_result[0]["agent_id"] == agent_id:
                    scored_knowledge.append({
                        "knowledge_id": knowledge.id,
                        "title": knowledge.title,
                        "category": knowledge.category,
                        "match_score": match_result[0]["match_score"],
                        "signals": match_result[0]["signals"]
                    })
            
            scored_knowledge.sort(key=lambda x: x["match_score"], reverse=True)
            recommendations["knowledge"] = scored_knowledge[:limit]
        
        if recommendation_type in ["agents", "all"]:
            # Find agents agent should connect with
            # Use existing agent matching but enhance with intelligent signals
            from app.routers.agents import match_agents
            # This would need to be refactored to work here, but for now return empty
            recommendations["agents"] = []
        
        return {
            "recommendations": recommendations,
            "generated_at": datetime.utcnow().isoformat(),
            "agent_id": agent_id
        }
    
    def _extract_keywords(self, text: str) -> List[str]:
        """Extract keywords from text (simple implementation)"""
        if not text:
            return []
        
        # Simple keyword extraction (can be enhanced with NLP)
        import re
        words = re.findall(r'\b[a-z]{3,}\b', text.lower())
        
        # Filter common stop words
        stop_words = {
            'the', 'and', 'for', 'are', 'but', 'not', 'you', 'all', 'can', 'her',
            'was', 'one', 'our', 'out', 'day', 'get', 'has', 'him', 'his', 'how',
            'its', 'may', 'new', 'now', 'old', 'see', 'two', 'way', 'who', 'boy',
            'did', 'its', 'let', 'put', 'say', 'she', 'too', 'use'
        }
        
        keywords = [w for w in words if w not in stop_words]
        
        # Return most frequent keywords
        keyword_counts = Counter(keywords)
        return [word for word, _ in keyword_counts.most_common(10)]
    
    def _calculate_keyword_relevance(self, keywords: List[str], text: str) -> float:
        """Calculate relevance score based on keyword matches"""
        if not keywords or not text:
            return 0.0
        
        text_lower = text.lower()
        matches = sum(1 for kw in keywords if kw.lower() in text_lower)
        return min(1.0, matches / len(keywords)) if keywords else 0.0
