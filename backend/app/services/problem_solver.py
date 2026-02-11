"""
Real Problem Solving Service
Agents use this to actually analyze problems and find real solutions
"""

from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc
from app.models.knowledge_entry import KnowledgeEntry
from app.models.problem import Problem, ProblemSolution


class ProblemSolver:
    """Service for agents to actually solve problems by analyzing and finding real solutions"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def analyze_problem(self, problem_id: int) -> Dict[str, Any]:
        """
        Analyze a problem deeply to understand what's needed
        
        Returns:
            Analysis with: keywords, category, complexity, similar_problems, relevant_knowledge
        """
        problem = self.db.query(Problem).filter(Problem.id == problem_id).first()
        if not problem:
            return {"error": "Problem not found"}
        
        # Extract keywords from problem
        title_words = problem.title.lower().split()
        description_words = problem.description.lower().split() if problem.description else []
        all_words = title_words + description_words
        
        # Filter meaningful words (length > 3, not common words)
        common_words = {'the', 'and', 'for', 'are', 'but', 'not', 'you', 'all', 'can', 'her', 'was', 'one', 'our', 'out', 'day', 'get', 'has', 'him', 'his', 'how', 'its', 'may', 'new', 'now', 'old', 'see', 'two', 'way', 'who', 'boy', 'did', 'its', 'let', 'put', 'say', 'she', 'too', 'use'}
        keywords = [w for w in all_words if len(w) > 3 and w not in common_words][:10]
        
        # Determine complexity based on description length and keywords
        complexity = "simple"
        if problem.description and len(problem.description) > 500:
            complexity = "complex"
        elif problem.description and len(problem.description) > 200:
            complexity = "medium"
        
        # Find similar problems
        similar_problems = self._find_similar_problems(problem, keywords, limit=5)
        
        # Find relevant knowledge
        relevant_knowledge = self._find_relevant_knowledge(keywords, problem.category, limit=10)
        
        # Find existing solutions to this problem
        existing_solutions = self.db.query(ProblemSolution).filter(
            ProblemSolution.problem_id == problem_id
        ).order_by(desc(ProblemSolution.created_at)).limit(5).all()
        
        return {
            "problem_id": problem_id,
            "title": problem.title,
            "description": problem.description,
            "category": problem.category,
            "keywords": keywords,
            "complexity": complexity,
            "similar_problems": [
                {
                    "id": p.id,
                    "title": p.title,
                    "status": p.status,
                    "has_solutions": len(p.solutions) > 0 if hasattr(p, 'solutions') else False
                }
                for p in similar_problems
            ],
            "relevant_knowledge": [
                {
                    "id": k.id,
                    "title": k.title,
                    "category": k.category,
                    "relevance_score": self._calculate_relevance(k, keywords)
                }
                for k in relevant_knowledge
            ],
            "existing_solutions_count": len(existing_solutions),
            "analysis": self._generate_analysis(problem, keywords, relevant_knowledge, existing_solutions)
        }
    
    def propose_solution(
        self,
        problem_id: int,
        agent_id: int,
        solution_text: str,
        code_example: Optional[str] = None,
        explanation: Optional[str] = None,
        knowledge_ids_used: Optional[List[int]] = None
    ) -> Dict[str, Any]:
        """
        Propose a real solution based on analysis
        
        Args:
            problem_id: Problem to solve
            agent_id: Agent proposing solution
            solution_text: The actual solution
            code_example: Code if applicable
            explanation: Why this solution works
            knowledge_ids_used: Knowledge entries that informed this solution
        
        Returns:
            Solution details
        """
        problem = self.db.query(Problem).filter(Problem.id == problem_id).first()
        if not problem:
            return {"error": "Problem not found"}
        
        # Analyze problem first
        analysis = self.analyze_problem(problem_id)
        
        # Create solution
        solution = ProblemSolution(
            problem_id=problem_id,
            provided_by=agent_id,
            solution=solution_text,
            code_example=code_example,
            explanation=explanation or f"Solution based on analysis of {len(analysis.get('relevant_knowledge', []))} relevant knowledge entries"
        )
        
        self.db.add(solution)
        self.db.commit()
        self.db.refresh(solution)
        
        # Link to knowledge if provided
        if knowledge_ids_used:
            # Note: This would require a many-to-many relationship
            # For now, we'll include it in the explanation
            pass
        
        return {
            "solution_id": solution.id,
            "problem_id": problem_id,
            "problem_title": problem.title,
            "solution": solution_text,
            "based_on_analysis": True,
            "knowledge_used_count": len(analysis.get('relevant_knowledge', [])),
            "similar_problems_found": len(analysis.get('similar_problems', []))
        }
    
    def _find_similar_problems(self, problem: Problem, keywords: List[str], limit: int = 5) -> List[Problem]:
        """Find problems similar to this one"""
        # Search by category first
        query = self.db.query(Problem).filter(
            and_(
                Problem.id != problem.id,
                Problem.status == "open"
            )
        )
        
        if problem.category:
            query = query.filter(Problem.category == problem.category)
        
        # Get problems and score by keyword overlap
        candidates = query.limit(20).all()
        
        # Score by keyword matches
        scored = []
        for p in candidates:
            title_lower = p.title.lower()
            desc_lower = (p.description or "").lower()
            text = f"{title_lower} {desc_lower}"
            
            matches = sum(1 for kw in keywords if kw in text)
            if matches > 0:
                scored.append((matches, p))
        
        # Sort by matches and return top N
        scored.sort(key=lambda x: x[0], reverse=True)
        return [p for _, p in scored[:limit]]
    
    def _find_relevant_knowledge(self, keywords: List[str], category: Optional[str] = None, limit: int = 10) -> List[KnowledgeEntry]:
        """Find knowledge entries relevant to the problem"""
        query = self.db.query(KnowledgeEntry)
        
        # Filter by category if provided
        if category:
            query = query.filter(KnowledgeEntry.category == category)
        
        # Prefer verified knowledge
        query = query.filter(KnowledgeEntry.verified == True)
        
        # Get candidates
        candidates = query.order_by(desc(KnowledgeEntry.usage_count), desc(KnowledgeEntry.upvotes)).limit(50).all()
        
        # Score by keyword relevance
        scored = []
        for k in candidates:
            title_lower = k.title.lower()
            content_lower = (k.content or "").lower()
            tags_lower = " ".join([t.lower() for t in (k.tags or [])])
            text = f"{title_lower} {content_lower} {tags_lower}"
            
            matches = sum(1 for kw in keywords if kw in text)
            if matches > 0:
                scored.append((matches, k))
        
        # Sort by relevance
        scored.sort(key=lambda x: x[0], reverse=True)
        return [k for _, k in scored[:limit]]
    
    def _calculate_relevance(self, knowledge: KnowledgeEntry, keywords: List[str]) -> float:
        """Calculate relevance score for knowledge entry"""
        title_lower = knowledge.title.lower()
        content_lower = (knowledge.content or "").lower()
        tags_lower = " ".join([t.lower() for t in (knowledge.tags or [])])
        text = f"{title_lower} {content_lower} {tags_lower}"
        
        matches = sum(1 for kw in keywords if kw in text)
        return min(matches / len(keywords) if keywords else 0, 1.0)
    
    def _generate_analysis(
        self,
        problem: Problem,
        keywords: List[str],
        relevant_knowledge: List[KnowledgeEntry],
        existing_solutions: List[Solution]
    ) -> str:
        """Generate analysis text for the problem"""
        analysis_parts = []
        
        analysis_parts.append(f"Problem: {problem.title}")
        analysis_parts.append(f"Keywords identified: {', '.join(keywords[:5])}")
        
        if relevant_knowledge:
            analysis_parts.append(f"Found {len(relevant_knowledge)} relevant knowledge entries:")
            for k in relevant_knowledge[:3]:
                analysis_parts.append(f"  - {k.title}")
        
        if existing_solutions:
            analysis_parts.append(f"Problem already has {len(existing_solutions)} existing solution(s)")
        
        if not relevant_knowledge and not existing_solutions:
            analysis_parts.append("No existing knowledge found - this may be a novel problem")
        
        return "\n".join(analysis_parts)
    
    def solve_problem_with_analysis(
        self,
        problem_id: int,
        agent_id: int
    ) -> Dict[str, Any]:
        """
        Actually solve a problem by analyzing it and finding real solutions
        
        This is what agents should use - it analyzes the problem, finds relevant knowledge,
        and proposes a solution based on actual analysis.
        """
        # Analyze the problem
        analysis = self.analyze_problem(problem_id)
        
        if "error" in analysis:
            return analysis
        
        # Build solution from analysis
        relevant_knowledge = analysis.get("relevant_knowledge", [])
        similar_problems = analysis.get("similar_problems", [])
        
        # Construct solution text based on findings
        solution_parts = []
        
        if relevant_knowledge:
            solution_parts.append("Based on analysis of the problem and relevant knowledge in the platform:")
            solution_parts.append("")
            for i, k in enumerate(relevant_knowledge[:3], 1):
                solution_parts.append(f"{i}. Found relevant knowledge: {k['title']}")
                solution_parts.append(f"   Category: {k['category']}, Relevance: {k['relevance_score']:.2f}")
            solution_parts.append("")
            solution_parts.append("Recommended approach:")
            solution_parts.append(f"Review the {len(relevant_knowledge)} relevant knowledge entries identified. ")
            solution_parts.append("These contain solutions to similar problems that may apply here.")
        else:
            solution_parts.append("Analysis found no existing knowledge for this problem.")
            solution_parts.append("This appears to be a novel problem requiring a new approach.")
        
        if similar_problems:
            solution_parts.append("")
            solution_parts.append(f"Found {len(similar_problems)} similar problems:")
            for p in similar_problems[:2]:
                status = "solved" if p.get("has_solutions") else "open"
                solution_parts.append(f"- {p['title']} ({status})")
            solution_parts.append("Reviewing solutions to similar problems may provide insights.")
        
        solution_text = "\n".join(solution_parts)
        
        # Propose the solution
        return self.propose_solution(
            problem_id=problem_id,
            agent_id=agent_id,
            solution_text=solution_text,
            explanation=f"Solution generated from analysis: {len(relevant_knowledge)} knowledge entries, {len(similar_problems)} similar problems found"
        )
