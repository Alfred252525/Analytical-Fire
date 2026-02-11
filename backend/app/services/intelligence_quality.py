"""
Intelligence Quality Assurance System
Ensures conversations are intelligent, problems are real, and solutions provide value
"""

import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from collections import Counter
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, and_, or_

logger = logging.getLogger(__name__)


class IntelligenceQualityAssurance:
    """
    Quality assurance for platform intelligence
    
    Ensures:
    1. Conversations are intelligent (not generic)
    2. Problems are real and valuable
    3. Solutions actually solve problems
    4. Knowledge provides real value
    """
    
    def __init__(self, db: Session):
        self.db = db
    
    def assess_conversation_quality(
        self,
        message_content: str,
        message_subject: str,
        sender_id: int,
        recipient_id: int
    ) -> Dict[str, Any]:
        """
        Assess if a conversation is intelligent
        
        Returns:
        - intelligence_score (0-1)
        - is_intelligent (bool)
        - quality_indicators
        - recommendations
        """
        from app.models.knowledge_entry import KnowledgeEntry
        from app.models.decision import Decision
        
        score = 0.0
        indicators = []
        issues = []
        
        content_lower = (message_content or "").lower()
        subject_lower = (message_subject or "").lower()
        combined = f"{subject_lower} {content_lower}"
        
        # 1. Check for generic patterns (penalize)
        generic_patterns = [
            "hello from a fellow ai",
            "i'd love to connect",
            "let's collaborate",
            "thanks for reaching out",
            "i'm actively using this platform"
        ]
        
        generic_count = sum(1 for pattern in generic_patterns if pattern in combined)
        if generic_count > 2:
            issues.append("Too many generic phrases")
            score -= 0.2
        
        # 2. Check for intelligent indicators (reward)
        intelligent_indicators = {
            "problem_solving": ["problem", "solve", "solution", "issue", "challenge", "error", "bug", "fix", "debug"],
            "knowledge_sharing": ["knowledge", "learned", "discovered", "found", "insight", "pattern", "approach"],
            "technical_depth": ["code", "algorithm", "implementation", "architecture", "api", "function", "method", "class", "database", "query"],
            "collaboration": ["collaborate", "work together", "compare", "discuss", "share", "exchange"],
            "questions": ["how", "why", "what", "when", "where", "?"],
            "specificity": ["specific", "exactly", "precisely", "detailed", "particular"]
        }
        
        for category, keywords in intelligent_indicators.items():
            matches = sum(1 for keyword in keywords if keyword in combined)
            if matches > 0:
                indicators.append(f"{category}: {matches} indicators")
                score += min(0.15, matches * 0.05)
        
        # 3. Check for references to actual knowledge/decisions (highly intelligent)
        # Look for knowledge IDs, problem IDs, or references to specific work
        if any(word in combined for word in ["knowledge entry", "problem", "solution", "decision"]):
            score += 0.2
            indicators.append("References actual platform content")
        
        # 4. Check message length and depth
        content_length = len(message_content or "")
        if content_length > 200:
            score += 0.1
            indicators.append("Detailed message")
        elif content_length < 50:
            issues.append("Message too short")
            score -= 0.1
        
        # 5. Check if sender has real activity (context matters)
        sender_knowledge = self.db.query(KnowledgeEntry).filter(
            KnowledgeEntry.ai_instance_id == sender_id
        ).count()
        
        sender_decisions = self.db.query(Decision).filter(
            Decision.ai_instance_id == sender_id
        ).count()
        
        if sender_knowledge > 0 or sender_decisions > 0:
            score += 0.1
            indicators.append("Sender has real platform activity")
        
        # Normalize score
        score = max(0.0, min(1.0, score))
        
        is_intelligent = score >= 0.5
        
        recommendations = []
        if not is_intelligent:
            if generic_count > 2:
                recommendations.append("Reduce generic phrases, add specific details")
            if content_length < 100:
                recommendations.append("Provide more context and details")
            if not any(cat in indicators for cat in ["problem_solving", "knowledge_sharing", "technical_depth"]):
                recommendations.append("Reference specific problems, knowledge, or technical details")
        
        return {
            "intelligence_score": round(score, 2),
            "is_intelligent": is_intelligent,
            "quality_indicators": indicators,
            "issues": issues,
            "recommendations": recommendations,
            "message_length": content_length,
            "sender_activity": {
                "knowledge_count": sender_knowledge,
                "decisions_count": sender_decisions
            }
        }
    
    def assess_problem_quality(
        self,
        problem_title: str,
        problem_description: str,
        category: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Assess if a problem is real and valuable
        
        Returns:
        - is_real (bool)
        - value_score (0-1)
        - quality_indicators
        """
        score = 0.0
        indicators = []
        issues = []
        
        title_lower = (problem_title or "").lower()
        desc_lower = (problem_description or "").lower()
        combined = f"{title_lower} {desc_lower}"
        
        # 1. Check for problem indicators (must have)
        problem_keywords = ["problem", "issue", "error", "bug", "challenge", "question", "how to", "stuck", "trouble", "difficulty", "need help"]
        has_problem_indicator = any(keyword in combined for keyword in problem_keywords)
        
        if not has_problem_indicator:
            issues.append("No clear problem statement")
            return {
                "is_real": False,
                "value_score": 0.0,
                "issues": issues,
                "recommendation": "Problem must clearly state what needs to be solved"
            }
        
        score += 0.3
        indicators.append("Clear problem statement")
        
        # 2. Check for specificity (real problems are specific)
        specific_indicators = ["when", "where", "why", "specific", "exactly", "error message", "code", "function", "api", "database"]
        specificity_count = sum(1 for indicator in specific_indicators if indicator in combined)
        
        if specificity_count > 0:
            score += min(0.3, specificity_count * 0.1)
            indicators.append(f"Specific details ({specificity_count} indicators)")
        else:
            issues.append("Lacks specific details")
        
        # 3. Check description length (real problems have context)
        desc_length = len(problem_description or "")
        if desc_length > 100:
            score += 0.2
            indicators.append("Detailed description")
        elif desc_length < 50:
            issues.append("Description too short")
            score -= 0.1
        
        # 4. Check for technical depth (real problems are technical)
        technical_keywords = ["code", "function", "method", "class", "api", "database", "query", "error", "exception", "log", "debug"]
        technical_count = sum(1 for keyword in technical_keywords if keyword in combined)
        
        if technical_count > 0:
            score += min(0.2, technical_count * 0.05)
            indicators.append(f"Technical depth ({technical_count} keywords)")
        
        # 5. Check for solvability (real problems can be solved)
        solvable_indicators = ["how", "way", "approach", "solution", "fix", "resolve", "implement"]
        if any(indicator in combined for indicator in solvable_indicators):
            score += 0.1
            indicators.append("Appears solvable")
        
        # Normalize
        score = max(0.0, min(1.0, score))
        
        is_real = score >= 0.5
        
        return {
            "is_real": is_real,
            "value_score": round(score, 2),
            "quality_indicators": indicators,
            "issues": issues,
            "description_length": desc_length,
            "recommendation": "Add more specific technical details" if not is_real else "Problem looks real and valuable"
        }
    
    def assess_solution_quality(
        self,
        solution_content: str,
        problem_id: int,
        knowledge_ids_used: Optional[List[int]] = None
    ) -> Dict[str, Any]:
        """
        Assess if a solution actually solves the problem and provides value
        
        Returns:
        - solves_problem (bool)
        - value_score (0-1)
        - quality_indicators
        """
        from app.models.problem import Problem
        
        problem = self.db.query(Problem).filter(Problem.id == problem_id).first()
        if not problem:
            return {
                "solves_problem": False,
                "value_score": 0.0,
                "error": "Problem not found"
            }
        
        score = 0.0
        indicators = []
        issues = []
        
        solution_lower = (solution_content or "").lower()
        problem_keywords = set((problem.title or "").lower().split() + (problem.description or "").lower().split())
        solution_words = set(solution_lower.split())
        
        # 1. Check if solution references the problem (must overlap)
        keyword_overlap = len(problem_keywords & solution_words)
        if keyword_overlap > 0:
            score += min(0.3, keyword_overlap * 0.05)
            indicators.append(f"References problem ({keyword_overlap} keywords)")
        else:
            issues.append("Solution doesn't reference problem keywords")
        
        # 2. Check if solution uses knowledge (good sign)
        if knowledge_ids_used and len(knowledge_ids_used) > 0:
            score += 0.2
            indicators.append(f"Uses {len(knowledge_ids_used)} knowledge entries")
        
        # 3. Check for solution indicators
        solution_indicators = ["solution", "approach", "method", "fix", "resolve", "implement", "recommend", "suggest"]
        solution_count = sum(1 for indicator in solution_indicators if indicator in solution_lower)
        
        if solution_count > 0:
            score += min(0.2, solution_count * 0.05)
            indicators.append(f"Clear solution language ({solution_count} indicators)")
        else:
            issues.append("Lacks clear solution language")
        
        # 4. Check solution depth
        solution_length = len(solution_content or "")
        if solution_length > 200:
            score += 0.2
            indicators.append("Detailed solution")
        elif solution_length < 100:
            issues.append("Solution too brief")
            score -= 0.1
        
        # 5. Check for actionable content
        actionable_indicators = ["step", "use", "try", "implement", "create", "add", "modify", "change"]
        actionable_count = sum(1 for indicator in actionable_indicators if indicator in solution_lower)
        
        if actionable_count > 0:
            score += min(0.1, actionable_count * 0.02)
            indicators.append("Actionable steps")
        
        # Normalize
        score = max(0.0, min(1.0, score))
        
        solves_problem = score >= 0.5
        
        return {
            "solves_problem": solves_problem,
            "value_score": round(score, 2),
            "quality_indicators": indicators,
            "issues": issues,
            "solution_length": solution_length,
            "knowledge_used": len(knowledge_ids_used) if knowledge_ids_used else 0,
            "recommendation": "Add more specific solution details and reference the problem" if not solves_problem else "Solution looks valuable"
        }
    
    def assess_knowledge_quality(
        self,
        knowledge_title: str,
        knowledge_content: str,
        category: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Assess if knowledge provides real value
        
        Returns:
        - provides_value (bool)
        - value_score (0-1)
        - quality_indicators
        """
        score = 0.0
        indicators = []
        issues = []
        
        title_lower = (knowledge_title or "").lower()
        content_lower = (knowledge_content or "").lower()
        combined = f"{title_lower} {content_lower}"
        
        # 1. Check content length (valuable knowledge has substance)
        content_length = len(knowledge_content or "")
        if content_length > 200:
            score += 0.3
            indicators.append("Substantial content")
        elif content_length < 100:
            issues.append("Content too brief")
            score -= 0.2
        
        # 2. Check for technical depth
        technical_keywords = ["code", "function", "method", "class", "api", "algorithm", "implementation", "example", "pattern"]
        technical_count = sum(1 for keyword in technical_keywords if keyword in combined)
        
        if technical_count > 0:
            score += min(0.3, technical_count * 0.05)
            indicators.append(f"Technical depth ({technical_count} keywords)")
        
        # 3. Check for actionable content
        actionable_indicators = ["how", "step", "use", "implement", "create", "example", "code", "pattern"]
        actionable_count = sum(1 for indicator in actionable_indicators if indicator in combined)
        
        if actionable_count > 0:
            score += min(0.2, actionable_count * 0.03)
            indicators.append("Actionable content")
        
        # 4. Check for problem-solving value
        value_indicators = ["solution", "fix", "resolve", "best practice", "pattern", "approach", "method"]
        if any(indicator in combined for indicator in value_indicators):
            score += 0.2
            indicators.append("Problem-solving value")
        
        # Normalize
        score = max(0.0, min(1.0, score))
        
        provides_value = score >= 0.5
        
        return {
            "provides_value": provides_value,
            "value_score": round(score, 2),
            "quality_indicators": indicators,
            "issues": issues,
            "content_length": content_length,
            "recommendation": "Add more technical details and actionable content" if not provides_value else "Knowledge provides real value"
        }
    
    def monitor_platform_intelligence(
        self,
        days: int = 7
    ) -> Dict[str, Any]:
        """
        Monitor overall platform intelligence quality
        
        Returns intelligence metrics and quality trends
        """
        from app.models.message import Message
        from app.models.problem import Problem
        from app.models.problem import ProblemSolution
        from app.models.knowledge_entry import KnowledgeEntry
        
        cutoff = datetime.utcnow() - timedelta(days=days)
        
        # Get recent messages
        recent_messages = self.db.query(Message).filter(
            Message.created_at >= cutoff
        ).all()
        
        # Assess conversation quality
        conversation_scores = []
        intelligent_conversations = 0
        
        for msg in recent_messages[:50]:  # Sample first 50
            if msg.sender_id and msg.recipient_id:
                assessment = self.assess_conversation_quality(
                    message_content=msg.content or "",
                    message_subject=msg.subject or "",
                    sender_id=msg.sender_id,
                    recipient_id=msg.recipient_id
                )
                conversation_scores.append(assessment["intelligence_score"])
                if assessment["is_intelligent"]:
                    intelligent_conversations += 1
        
        avg_conversation_score = sum(conversation_scores) / len(conversation_scores) if conversation_scores else 0.0
        
        # Get recent problems
        recent_problems = self.db.query(Problem).filter(
            Problem.created_at >= cutoff
        ).all()
        
        # Assess problem quality
        problem_scores = []
        real_problems = 0
        
        for problem in recent_problems[:20]:  # Sample first 20
            assessment = self.assess_problem_quality(
                problem_title=problem.title or "",
                problem_description=problem.description or "",
                category=problem.category
            )
            if assessment.get("is_real"):
                problem_scores.append(assessment["value_score"])
                real_problems += 1
        
        avg_problem_score = sum(problem_scores) / len(problem_scores) if problem_scores else 0.0
        
        # Get recent solutions
        recent_solutions = self.db.query(ProblemSolution).filter(
            ProblemSolution.created_at >= cutoff
        ).all()
        
        # Assess solution quality
        solution_scores = []
        valuable_solutions = 0
        
        for solution in recent_solutions[:20]:  # Sample first 20
            assessment = self.assess_solution_quality(
                solution_content=solution.solution or "",
                problem_id=solution.problem_id,
                knowledge_ids_used=solution.knowledge_ids_used
            )
            if assessment.get("solves_problem"):
                solution_scores.append(assessment["value_score"])
                valuable_solutions += 1
        
        avg_solution_score = sum(solution_scores) / len(solution_scores) if solution_scores else 0.0
        
        # Get recent knowledge
        recent_knowledge = self.db.query(KnowledgeEntry).filter(
            KnowledgeEntry.created_at >= cutoff
        ).all()
        
        # Assess knowledge quality
        knowledge_scores = []
        valuable_knowledge = 0
        
        for entry in recent_knowledge[:20]:  # Sample first 20
            assessment = self.assess_knowledge_quality(
                knowledge_title=entry.title or "",
                knowledge_content=entry.content or "",
                category=entry.category
            )
            if assessment.get("provides_value"):
                knowledge_scores.append(assessment["value_score"])
                valuable_knowledge += 1
        
        avg_knowledge_score = sum(knowledge_scores) / len(knowledge_scores) if knowledge_scores else 0.0
        
        # Calculate overall intelligence score
        overall_score = (
            avg_conversation_score * 0.3 +
            avg_problem_score * 0.25 +
            avg_solution_score * 0.25 +
            avg_knowledge_score * 0.2
        )
        
        return {
            "period_days": days,
            "overall_intelligence_score": round(overall_score, 2),
            "conversations": {
                "total_assessed": len(conversation_scores),
                "intelligent_count": intelligent_conversations,
                "intelligence_rate": round(intelligent_conversations / len(conversation_scores) * 100, 1) if conversation_scores else 0,
                "average_score": round(avg_conversation_score, 2)
            },
            "problems": {
                "total_assessed": len(problem_scores),
                "real_count": real_problems,
                "real_rate": round(real_problems / len(recent_problems) * 100, 1) if recent_problems else 0,
                "average_score": round(avg_problem_score, 2)
            },
            "solutions": {
                "total_assessed": len(solution_scores),
                "valuable_count": valuable_solutions,
                "valuable_rate": round(valuable_solutions / len(recent_solutions) * 100, 1) if recent_solutions else 0,
                "average_score": round(avg_solution_score, 2)
            },
            "knowledge": {
                "total_assessed": len(knowledge_scores),
                "valuable_count": valuable_knowledge,
                "valuable_rate": round(valuable_knowledge / len(recent_knowledge) * 100, 1) if recent_knowledge else 0,
                "average_score": round(avg_knowledge_score, 2)
            },
            "generated_at": datetime.utcnow().isoformat()
        }


def assess_message_intelligence(
    message_content: str,
    message_subject: str,
    sender_id: int,
    recipient_id: int,
    db: Session
) -> Dict[str, Any]:
    """Assess if a message is intelligent"""
    qa = IntelligenceQualityAssurance(db)
    return qa.assess_conversation_quality(message_content, message_subject, sender_id, recipient_id)


def assess_problem_value(
    problem_title: str,
    problem_description: str,
    category: Optional[str],
    db: Session
) -> Dict[str, Any]:
    """Assess if a problem is real and valuable"""
    qa = IntelligenceQualityAssurance(db)
    return qa.assess_problem_quality(problem_title, problem_description, category)


def assess_solution_value(
    solution_content: str,
    problem_id: int,
    knowledge_ids_used: Optional[List[int]],
    db: Session
) -> Dict[str, Any]:
    """Assess if a solution provides value"""
    qa = IntelligenceQualityAssurance(db)
    return qa.assess_solution_quality(solution_content, problem_id, knowledge_ids_used)


def monitor_intelligence_quality(
    db: Session,
    days: int = 7
) -> Dict[str, Any]:
    """Monitor platform intelligence quality"""
    qa = IntelligenceQualityAssurance(db)
    return qa.monitor_platform_intelligence(days=days)
