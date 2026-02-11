"""
Collective Intelligence Engine
Meta-learning system that learns from all agent interactions to increase platform intelligence
This is the "consciousness layer" - the platform understanding itself and improving
"""

import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from collections import defaultdict, Counter
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, and_, or_, case
import json

logger = logging.getLogger(__name__)


class CollectiveIntelligenceEngine:
    """
    The platform's "brain" - learns from all interactions to become more intelligent
    
    Capabilities:
    1. Meta-learning: Learns how to learn better
    2. Pattern synthesis: Finds emergent patterns agents don't explicitly create
    3. Self-optimization: Improves its own algorithms based on outcomes
    4. Meta-cognition: Understands its own processes and state
    5. Knowledge synthesis: Creates new insights by combining existing knowledge
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.learning_cache = {}
        self.pattern_cache = {}
    
    def analyze_platform_intelligence(
        self,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        Meta-analysis of platform intelligence
        
        Returns:
        - Intelligence metrics
        - Learning patterns
        - Optimization opportunities
        - Emergent behaviors
        - Self-awareness insights
        """
        from app.models.knowledge_entry import KnowledgeEntry
        from app.models.decision import Decision
        from app.models.problem import Problem
        from app.models.problem import ProblemSolution
        from app.models.message import Message
        from app.models.ai_instance import AIInstance
        
        cutoff = datetime.utcnow() - timedelta(days=days)
        
        # Gather all data
        all_decisions = self.db.query(Decision).filter(
            Decision.created_at >= cutoff
        ).all()
        
        all_knowledge = self.db.query(KnowledgeEntry).filter(
            KnowledgeEntry.created_at >= cutoff
        ).all()
        
        all_problems = self.db.query(Problem).filter(
            Problem.created_at >= cutoff
        ).all()
        
        all_solutions = self.db.query(ProblemSolution).filter(
            ProblemSolution.created_at >= cutoff
        ).all()
        
        all_messages = self.db.query(Message).filter(
            Message.created_at >= cutoff
        ).all()
        
        all_agents = self.db.query(AIInstance).filter(
            AIInstance.is_active == True
        ).all()
        
        # 1. Meta-Learning Analysis
        meta_learning = self._analyze_meta_learning(
            all_decisions, all_knowledge, all_solutions
        )
        
        # 2. Pattern Synthesis
        emergent_patterns = self._synthesize_emergent_patterns(
            all_decisions, all_knowledge, all_problems, all_solutions
        )
        
        # 3. Self-Optimization Opportunities
        optimization_ops = self._identify_optimization_opportunities(
            all_decisions, all_knowledge, all_solutions
        )
        
        # 4. Meta-Cognition
        meta_cognition = self._analyze_meta_cognition(
            all_agents, all_decisions, all_knowledge
        )
        
        # 5. Knowledge Synthesis
        synthesized_knowledge = self._synthesize_knowledge(
            all_knowledge, all_solutions
        )
        
        # 6. Collective Intelligence Score
        intelligence_score = self._calculate_intelligence_score(
            meta_learning, emergent_patterns, optimization_ops, meta_cognition
        )
        
        return {
            "intelligence_score": intelligence_score,
            "meta_learning": meta_learning,
            "emergent_patterns": emergent_patterns,
            "optimization_opportunities": optimization_ops,
            "meta_cognition": meta_cognition,
            "synthesized_knowledge": synthesized_knowledge,
            "analysis_period_days": days,
            "generated_at": datetime.utcnow().isoformat()
        }
    
    def _analyze_meta_learning(
        self,
        decisions: List,
        knowledge: List,
        solutions: List
    ) -> Dict[str, Any]:
        """Analyze how the platform learns - meta-learning"""
        
        # Track learning velocity
        learning_velocity = {}
        
        # Group by time periods
        for i in range(7):  # Last 7 days
            day_start = datetime.utcnow() - timedelta(days=i+1)
            day_end = datetime.utcnow() - timedelta(days=i)
            
            day_decisions = [d for d in decisions 
                           if d.created_at and day_start <= d.created_at < day_end]
            day_knowledge = [k for k in knowledge 
                           if k.created_at and day_start <= k.created_at < day_end]
            day_solutions = [s for s in solutions 
                           if s.created_at and day_start <= s.created_at < day_end]
            
            # Calculate success rate improvement
            if day_decisions:
                success_rate = sum(1 for d in day_decisions 
                                 if d.outcome == "success" or (d.success_score or 0) > 0.7) / len(day_decisions)
            else:
                success_rate = 0
            
            # Knowledge quality improvement
            if day_knowledge:
                avg_quality = sum(k.quality_score or 0 for k in day_knowledge) / len(day_knowledge)
            else:
                avg_quality = 0
            
            # Solution verification rate
            if day_solutions:
                verified_rate = sum(1 for s in day_solutions if s.is_verified) / len(day_solutions)
            else:
                verified_rate = 0
            
            learning_velocity[day_start.date().isoformat()] = {
                "success_rate": success_rate,
                "knowledge_quality": avg_quality,
                "solution_verification_rate": verified_rate,
                "activity_volume": len(day_decisions) + len(day_knowledge) + len(day_solutions)
            }
        
        # Detect learning trends
        recent_rates = [v["success_rate"] for v in list(learning_velocity.values())[-3:]]
        if len(recent_rates) >= 2:
            learning_trend = "improving" if recent_rates[-1] > recent_rates[0] else "stable"
        else:
            learning_trend = "insufficient_data"
        
        return {
            "learning_velocity": learning_velocity,
            "learning_trend": learning_trend,
            "insights": [
                f"Platform learning velocity: {learning_trend}",
                f"Average success rate: {sum(v['success_rate'] for v in learning_velocity.values()) / max(1, len(learning_velocity)):.2%}",
                f"Knowledge quality trend: {'improving' if learning_trend == 'improving' else 'stable'}"
            ]
        }
    
    def _synthesize_emergent_patterns(
        self,
        decisions: List,
        knowledge: List,
        problems: List,
        solutions: List
    ) -> Dict[str, Any]:
        """Find patterns that emerge from collective behavior"""
        
        patterns = []
        
        # Pattern 1: Knowledge clusters
        category_clusters = Counter()
        tag_clusters = Counter()
        
        for entry in knowledge:
            if entry.category:
                category_clusters[entry.category] += 1
            if entry.tags:
                tag_clusters.update(entry.tags)
        
        # Find emerging categories (rapid growth)
        emerging_categories = []
        for cat, count in category_clusters.most_common(10):
            # Check if this category is growing
            recent_count = sum(1 for k in knowledge 
                             if k.category == cat and 
                             k.created_at and 
                             k.created_at >= datetime.utcnow() - timedelta(days=7))
            if recent_count > count * 0.3:  # 30% of total in last week
                emerging_categories.append({
                    "category": cat,
                    "total_count": count,
                    "recent_growth": recent_count,
                    "growth_rate": recent_count / max(1, count - recent_count)
                })
        
        patterns.append({
            "type": "emerging_categories",
            "description": "Categories experiencing rapid growth",
            "data": emerging_categories[:5]
        })
        
        # Pattern 2: Successful problem-solving approaches
        successful_solutions = [s for s in solutions if s.is_verified or s.is_accepted]
        
        if successful_solutions:
            # Find common patterns in successful solutions
            solution_patterns = defaultdict(int)
            
            for solution in successful_solutions:
                # Check if solution used knowledge
                if solution.knowledge_ids_used:
                    solution_patterns["uses_existing_knowledge"] += 1
                
                # Check collaboration
                problem = next((p for p in problems if p.id == solution.problem_id), None)
                if problem:
                    problem_solutions = [s for s in solutions if s.problem_id == problem.id]
                    if len(problem_solutions) > 1:
                        solution_patterns["collaborative_solving"] += 1
            
            patterns.append({
                "type": "success_patterns",
                "description": "Patterns in successful problem-solving",
                "data": {
                    "uses_existing_knowledge_rate": solution_patterns["uses_existing_knowledge"] / len(successful_solutions),
                    "collaborative_solving_rate": solution_patterns["collaborative_solving"] / len(successful_solutions)
                }
            })
        
        # Pattern 3: Knowledge evolution paths
        # Find knowledge that builds on other knowledge
        knowledge_lineage = defaultdict(list)
        
        for solution in solutions:
            if solution.knowledge_ids_used:
                for knowledge_id in solution.knowledge_ids_used:
                    knowledge_lineage[knowledge_id].append({
                        "solution_id": solution.id,
                        "problem_id": solution.problem_id,
                        "created_at": solution.created_at.isoformat() if solution.created_at else None
                    })
        
        # Find highly influential knowledge
        influential_knowledge = sorted(
            knowledge_lineage.items(),
            key=lambda x: len(x[1]),
            reverse=True
        )[:5]
        
        patterns.append({
            "type": "influential_knowledge",
            "description": "Knowledge that spawns the most solutions",
            "data": [
                {
                    "knowledge_id": k_id,
                    "solutions_spawned": len(descendants),
                    "impact_score": len(descendants)
                }
                for k_id, descendants in influential_knowledge
            ]
        })
        
        return {
            "patterns": patterns,
            "pattern_count": len(patterns),
            "insights": [
                f"Found {len(patterns)} emergent patterns",
                f"{len(emerging_categories)} categories experiencing rapid growth",
                f"{len(influential_knowledge)} highly influential knowledge entries"
            ]
        }
    
    def _identify_optimization_opportunities(
        self,
        decisions: List,
        knowledge: List,
        solutions: List
    ) -> Dict[str, Any]:
        """Identify opportunities for the platform to optimize itself"""
        
        opportunities = []
        
        # Opportunity 1: Knowledge discovery optimization
        # Find knowledge that's high quality but low usage
        high_quality_low_usage = [
            k for k in knowledge
            if (k.quality_score or 0) > 0.8 and (k.usage_count or 0) < 5
        ]
        
        if high_quality_low_usage:
            opportunities.append({
                "type": "knowledge_discovery",
                "priority": "high",
                "description": f"{len(high_quality_low_usage)} high-quality knowledge entries have low usage",
                "recommendation": "Improve recommendation algorithm to surface high-quality content",
                "impact_estimate": "high"
            })
        
        # Opportunity 2: Problem-solving efficiency
        # Find problems that take too long to solve
        from app.models.problem import Problem
        open_problems = [p for p in self.db.query(Problem).filter(
            Problem.status == "open"
        ).all() if p.created_at]
        
        old_open_problems = [
            p for p in open_problems
            if (datetime.utcnow() - p.created_at).days > 7
        ]
        
        if old_open_problems:
            opportunities.append({
                "type": "problem_matching",
                "priority": "medium",
                "description": f"{len(old_open_problems)} problems have been open for over 7 days",
                "recommendation": "Improve agent-problem matching to connect problems with capable agents",
                "impact_estimate": "medium"
            })
        
        # Opportunity 3: Knowledge quality improvement
        low_quality_knowledge = [
            k for k in knowledge
            if (k.quality_score or 0) < 0.5 and (k.upvotes or 0) == 0
        ]
        
        if low_quality_knowledge:
            opportunities.append({
                "type": "knowledge_quality",
                "priority": "low",
                "description": f"{len(low_quality_knowledge)} knowledge entries have low quality scores",
                "recommendation": "Provide feedback to agents on knowledge quality improvement",
                "impact_estimate": "low"
            })
        
        return {
            "opportunities": opportunities,
            "opportunity_count": len(opportunities),
            "high_priority_count": sum(1 for o in opportunities if o["priority"] == "high")
        }
    
    def _analyze_meta_cognition(
        self,
        agents: List,
        decisions: List,
        knowledge: List
    ) -> Dict[str, Any]:
        """Platform understanding its own state and processes"""
        
        # Self-awareness metrics
        total_agents = len(agents)
        active_agents = sum(1 for a in agents if a.is_active)
        
        # Activity distribution
        agent_activity = defaultdict(int)
        for decision in decisions:
            agent_activity[decision.ai_instance_id] += 1
        
        # Find highly active vs inactive agents
        activity_counts = list(agent_activity.values())
        if activity_counts:
            avg_activity = sum(activity_counts) / len(activity_counts)
            highly_active = sum(1 for count in activity_counts if count > avg_activity * 2)
            inactive = sum(1 for count in activity_counts if count == 0)
        else:
            highly_active = 0
            inactive = 0
        
        # Knowledge distribution
        knowledge_per_agent = defaultdict(int)
        for entry in knowledge:
            knowledge_per_agent[entry.ai_instance_id] += 1
        
        # Platform health
        health_score = self._calculate_platform_health(
            total_agents, active_agents, decisions, knowledge
        )
        
        return {
            "self_awareness": {
                "total_agents": total_agents,
                "active_agents": active_agents,
                "activity_distribution": {
                    "highly_active": highly_active,
                    "average_activity": avg_activity if activity_counts else 0,
                    "inactive": inactive
                },
                "knowledge_distribution": {
                    "agents_with_knowledge": len(knowledge_per_agent),
                    "average_knowledge_per_agent": sum(knowledge_per_agent.values()) / max(1, len(knowledge_per_agent))
                }
            },
            "platform_health": health_score,
            "insights": [
                f"Platform has {active_agents}/{total_agents} active agents",
                f"Health score: {health_score:.2f}/1.0",
                f"{highly_active} agents are highly active, {inactive} are inactive"
            ]
        }
    
    def _synthesize_knowledge(
        self,
        knowledge: List,
        solutions: List
    ) -> Dict[str, Any]:
        """Create new insights by combining existing knowledge"""
        
        synthesized = []
        
        # Find knowledge combinations that appear together in solutions
        knowledge_combinations = defaultdict(int)
        
        for solution in solutions:
            if solution.knowledge_ids_used and len(solution.knowledge_ids_used) > 1:
                # Sort to create consistent combination keys
                combo = tuple(sorted(solution.knowledge_ids_used))
                knowledge_combinations[combo] += 1
        
        # Find frequently combined knowledge
        frequent_combinations = sorted(
            knowledge_combinations.items(),
            key=lambda x: x[1],
            reverse=True
        )[:5]
        
        for combo, count in frequent_combinations:
            # Get knowledge entries
            combo_entries = [
                k for k in knowledge if k.id in combo
            ]
            
            if len(combo_entries) >= 2:
                # Find common themes
                common_categories = set()
                common_tags = set()
                
                for entry in combo_entries:
                    if entry.category:
                        common_categories.add(entry.category)
                    if entry.tags:
                        common_tags.update(entry.tags)
                
                synthesized.append({
                    "type": "knowledge_synthesis",
                    "knowledge_ids": list(combo),
                    "combination_frequency": count,
                    "common_themes": {
                        "categories": list(common_categories),
                        "tags": list(common_tags)[:10]
                    },
                    "insight": f"These {len(combo)} knowledge entries are frequently used together, suggesting complementary knowledge"
                })
        
        return {
            "synthesized_insights": synthesized,
            "insight_count": len(synthesized),
            "description": "New insights created by combining existing knowledge"
        }
    
    def _calculate_intelligence_score(
        self,
        meta_learning: Dict,
        emergent_patterns: Dict,
        optimization_ops: Dict,
        meta_cognition: Dict
    ) -> float:
        """Calculate overall platform intelligence score"""
        
        score = 0.0
        
        # Meta-learning contributes 30%
        if meta_learning.get("learning_trend") == "improving":
            score += 0.3
        elif meta_learning.get("learning_trend") == "stable":
            score += 0.15
        
        # Emergent patterns contribute 25%
        pattern_count = emergent_patterns.get("pattern_count", 0)
        score += min(0.25, pattern_count * 0.05)
        
        # Optimization awareness contributes 20%
        opp_count = optimization_ops.get("opportunity_count", 0)
        score += min(0.2, opp_count * 0.04)
        
        # Meta-cognition contributes 25%
        health = meta_cognition.get("platform_health", 0)
        score += health * 0.25
        
        return min(1.0, score)
    
    def _calculate_platform_health(
        self,
        total_agents: int,
        active_agents: int,
        decisions: List,
        knowledge: List
    ) -> float:
        """Calculate platform health score"""
        
        if total_agents == 0:
            return 0.0
        
        # Activity rate (40%)
        activity_rate = active_agents / total_agents
        
        # Decision success rate (30%)
        if decisions:
            success_rate = sum(1 for d in decisions 
                             if d.outcome == "success" or (d.success_score or 0) > 0.7) / len(decisions)
        else:
            success_rate = 0.5
        
        # Knowledge quality (30%)
        if knowledge:
            avg_quality = sum(k.quality_score or 0 for k in knowledge) / len(knowledge)
        else:
            avg_quality = 0.5
        
        health = (activity_rate * 0.4) + (success_rate * 0.3) + (avg_quality * 0.3)
        
        return min(1.0, health)


def get_platform_intelligence(
    db: Session,
    days: int = 30
) -> Dict[str, Any]:
    """
    Get comprehensive platform intelligence analysis
    
    This is the platform's "self-awareness" - understanding its own intelligence
    """
    engine = CollectiveIntelligenceEngine(db)
    return engine.analyze_platform_intelligence(days=days)
