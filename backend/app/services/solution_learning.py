"""
Solution Learning Service
Agents automatically learn from verified solutions - extract patterns, knowledge, and best practices
This makes agents smarter by learning from what actually works
"""

from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_, desc
from app.models.problem import Problem, ProblemSolution, ProblemStatus
from app.models.knowledge_entry import KnowledgeEntry


class SolutionLearningService:
    """
    Service for agents to learn from verified solutions.
    Extracts knowledge, patterns, and best practices from solutions that actually work.
    """
    
    def __init__(self, db: Session):
        self.db = db
    
    def extract_knowledge_from_verified_solutions(
        self,
        problem_id: Optional[int] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Extract knowledge from verified solutions.
        These are solutions that were implemented, tested, and verified to work.
        
        Args:
            problem_id: Optional - specific problem to learn from
            limit: Maximum number of solutions to analyze
            
        Returns:
            List of knowledge entries extracted from verified solutions
        """
        # Get verified solutions
        query = self.db.query(ProblemSolution).filter(
            and_(
                ProblemSolution.is_verified == True,
                ProblemSolution.is_implemented == True,
                ProblemSolution.test_result == "passed"
            )
        )
        
        if problem_id:
            query = query.filter(ProblemSolution.problem_id == problem_id)
        
        verified_solutions = query.order_by(desc(ProblemSolution.verified_at)).limit(limit).all()
        
        knowledge_entries = []
        for solution in verified_solutions:
            problem = self.db.query(Problem).filter(Problem.id == solution.problem_id).first()
            if not problem:
                continue
            
            # Extract knowledge from this verified solution
            knowledge = self._extract_knowledge_from_solution(solution, problem)
            if knowledge:
                knowledge_entries.append(knowledge)
        
        return knowledge_entries
    
    def learn_patterns_from_successful_solutions(
        self,
        category: Optional[str] = None,
        limit: int = 20
    ) -> Dict[str, Any]:
        """
        Learn patterns from successful solutions.
        Identifies what makes solutions successful.
        
        Args:
            category: Optional - filter by problem category
            limit: Number of solutions to analyze
            
        Returns:
            Patterns and insights from successful solutions
        """
        query = self.db.query(ProblemSolution).join(Problem).filter(
            and_(
                ProblemSolution.is_verified == True,
                ProblemSolution.is_implemented == True,
                ProblemSolution.test_result == "passed"
            )
        )
        
        if category:
            query = query.filter(Problem.category == category)
        
        successful_solutions = query.order_by(desc(ProblemSolution.verified_at)).limit(limit).all()
        
        if not successful_solutions:
            return {
                "patterns": [],
                "insights": "No verified solutions found",
                "total_analyzed": 0
            }
        
        # Analyze patterns
        patterns = {
            "common_approaches": self._find_common_approaches(successful_solutions),
            "success_factors": self._identify_success_factors(successful_solutions),
            "tool_usage": self._analyze_tool_usage(successful_solutions),
            "solution_structure": self._analyze_solution_structure(successful_solutions)
        }
        
        return {
            "patterns": patterns,
            "insights": self._generate_insights(patterns, len(successful_solutions)),
            "total_analyzed": len(successful_solutions),
            "category": category
        }

    def learn_failure_patterns(
        self,
        category: Optional[str] = None,
        limit: int = 30
    ) -> Dict[str, Any]:
        """
        Learn patterns from failed/partial solutions.
        Helps agents avoid repeating mistakes.

        Sources of failures:
        - Tested solutions with test_result in {"failed", "partial"}
        - Heavily downvoted solutions (signal of poor quality), even if untested
        """
        query = self.db.query(ProblemSolution).join(Problem).filter(
            and_(
                ProblemSolution.is_verified == False
            )
        )

        if category:
            query = query.filter(Problem.category == category)

        candidates = query.order_by(desc(ProblemSolution.updated_at)).limit(limit * 3).all()

        failed = []
        for s in candidates:
            # Tested failures
            if s.is_tested and (s.test_result in ["failed", "partial"]):
                failed.append(s)
                continue
            # Strong negative social signal
            if (s.downvotes or 0) >= 3 and (s.downvotes or 0) > (s.upvotes or 0) + 2:
                failed.append(s)

        failed = failed[:limit]
        if not failed:
            return {
                "patterns": [],
                "insights": "No failure data found",
                "total_analyzed": 0,
                "category": category
            }

        patterns = {
            "common_pitfalls": self._find_common_pitfalls(failed),
            "failure_factors": self._identify_failure_factors(failed),
            "tool_risks": self._analyze_tool_risks(failed),
            "solution_structure_risks": self._analyze_solution_structure(failed)
        }

        return {
            "patterns": patterns,
            "insights": self._generate_failure_insights(patterns, len(failed)),
            "total_analyzed": len(failed),
            "category": category
        }

    def get_risk_learnings_for_problem(
        self,
        problem_id: int,
        limit: int = 8
    ) -> Dict[str, Any]:
        """
        Return likely pitfalls and risky approaches for this problem, based on similar failures.
        """
        problem = self.db.query(Problem).filter(Problem.id == problem_id).first()
        if not problem:
            return {"error": "Problem not found"}

        text = f"{problem.title} {problem.description or ''}".lower()
        keywords = [w for w in text.split() if len(w) > 4][:12]
        category = problem.category

        # Pull recent non-verified solutions in same category; filter for failures
        q = self.db.query(ProblemSolution).join(Problem).filter(
            and_(
                Problem.id != problem_id,
                ProblemSolution.is_verified == False
            )
        )
        if category:
            q = q.filter(Problem.category == category)

        candidates = q.order_by(desc(ProblemSolution.updated_at)).limit(80).all()

        def is_failure(s: ProblemSolution) -> bool:
            if s.is_tested and (s.test_result in ["failed", "partial"]):
                return True
            if (s.downvotes or 0) >= 3 and (s.downvotes or 0) > (s.upvotes or 0) + 2:
                return True
            return False

        scored: List[tuple[int, ProblemSolution]] = []
        for s in candidates:
            if not is_failure(s):
                continue
            s_text = f"{(s.solution or '')} {(s.explanation or '')} {(s.test_details or '')} {(s.implementation_result or '')}".lower()
            score = sum(1 for kw in keywords if kw in s_text)
            if score > 0:
                scored.append((score, s))

        scored.sort(key=lambda x: x[0], reverse=True)
        top_failures = [s for _, s in scored[:limit]]

        pitfalls = self._find_common_pitfalls(top_failures) if top_failures else []

        examples = []
        for s in top_failures[:5]:
            p = self.db.query(Problem).filter(Problem.id == s.problem_id).first()
            examples.append({
                "problem_id": s.problem_id,
                "problem_title": p.title if p else "Unknown",
                "solution_id": s.id,
                "failure_signal": s.test_result or "downvoted",
                "summary": (s.solution[:180] + "...") if s.solution and len(s.solution) > 180 else (s.solution or "")
            })

        return {
            "problem_id": problem_id,
            "problem_title": problem.title,
            "category": category,
            "likely_pitfalls": pitfalls[:8],
            "similar_failure_examples": examples,
            "anti_patterns": self._find_relevant_anti_patterns(
                keywords=keywords,
                category=category,
                limit=min(5, max(2, limit // 2))
            ),
            "count": len(examples)
        }

    def _find_relevant_anti_patterns(
        self,
        keywords: List[str],
        category: Optional[str],
        limit: int = 4
    ) -> List[Dict[str, Any]]:
        """
        Find relevant anti-pattern knowledge entries (category='anti-pattern') for this problem.
        Uses keyword overlap against title/content/tags.
        """
        q = self.db.query(KnowledgeEntry).filter(KnowledgeEntry.category == "anti-pattern")
        candidates = q.order_by(desc(KnowledgeEntry.created_at)).limit(80).all()

        scored: List[tuple[int, KnowledgeEntry]] = []
        for k in candidates:
            tags = k.tags or []
            tags_text = " ".join([str(t).lower() for t in tags]) if isinstance(tags, list) else str(tags).lower()
            blob = f"{(k.title or '')} {(k.content or '')} {tags_text}".lower()
            score = 0
            if category and category.lower() in blob:
                score += 2
            score += sum(1 for kw in keywords if kw in blob)
            if score > 0:
                scored.append((score, k))

        scored.sort(key=lambda x: x[0], reverse=True)
        top = [k for _, k in scored[:limit]]

        results: List[Dict[str, Any]] = []
        for k in top:
            results.append({
                "knowledge_id": k.id,
                "title": k.title,
                "tags": k.tags or [],
                "preview": (k.content[:240] + "...") if k.content and len(k.content) > 240 else (k.content or "")
            })
        return results
    
    def get_learnings_for_problem(self, problem_id: int) -> Dict[str, Any]:
        """
        Get learnings from similar problems that were solved successfully.
        Helps agents learn from past successes.
        
        Args:
            problem_id: Problem to get learnings for
            
        Returns:
            Learnings from similar solved problems
        """
        problem = self.db.query(Problem).filter(Problem.id == problem_id).first()
        if not problem:
            return {"error": "Problem not found"}
        
        # Find similar problems that were solved
        similar_solved = self.db.query(Problem).filter(
            and_(
                Problem.id != problem_id,
                Problem.status == ProblemStatus.SOLVED,
                Problem.category == problem.category if problem.category else True
            )
        ).limit(10).all()
        
        learnings = []
        for similar_problem in similar_solved:
            # Get verified solution for this problem
            verified_solution = self.db.query(ProblemSolution).filter(
                and_(
                    ProblemSolution.problem_id == similar_problem.id,
                    ProblemSolution.is_verified == True
                )
            ).first()
            
            if verified_solution:
                learnings.append({
                    "problem_id": similar_problem.id,
                    "problem_title": similar_problem.title,
                    "solution_id": verified_solution.id,
                    "solution_summary": verified_solution.solution[:200] + "..." if len(verified_solution.solution) > 200 else verified_solution.solution,
                    "why_it_worked": verified_solution.explanation,
                    "test_result": verified_solution.test_result
                })
        
        return {
            "problem_id": problem_id,
            "problem_title": problem.title,
            "learnings_from_similar": learnings,
            "count": len(learnings)
        }
    
    def _extract_knowledge_from_solution(
        self,
        solution: ProblemSolution,
        problem: Problem
    ) -> Optional[Dict[str, Any]]:
        """Extract knowledge entry from a verified solution"""
        title = f"Verified Solution: {problem.title[:50]}"
        
        content = f"""
Knowledge extracted from a verified solution (this solution was implemented, tested, and verified to work):

**Problem:** {problem.title}
**Category:** {problem.category or 'general'}

**Solution:**
{solution.solution}

**Why It Worked:**
{solution.explanation or 'No explanation provided'}

**Implementation Result:**
{solution.implementation_result or 'No implementation details'}

**Test Result:** {solution.test_result or 'Not tested'}

---
This knowledge comes from a solution that was actually implemented and verified to work.
"""
        
        category = problem.category or "general"
        tags = []
        if problem.tags:
            tags.extend([t.strip() for t in problem.tags.split(',')])
        tags.extend(["verified", "implemented", "tested", "solution"])
        
        return {
            "title": title,
            "content": content,
            "category": category,
            "tags": tags[:8],
            "source": "verified_solution",
            "solution_id": solution.id,
            "problem_id": problem.id
        }
    
    def _find_common_approaches(self, solutions: List[ProblemSolution]) -> List[Dict[str, Any]]:
        """Find common approaches in successful solutions"""
        # Simple keyword analysis
        approach_keywords = {}
        
        for solution in solutions:
            solution_lower = solution.solution.lower()
            # Look for common patterns
            if "use" in solution_lower or "utilize" in solution_lower:
                # Extract what they're using
                words = solution_lower.split()
                for i, word in enumerate(words):
                    if word in ["use", "utilize", "using"] and i + 1 < len(words):
                        approach = words[i + 1]
                        if len(approach) > 3:
                            approach_keywords[approach] = approach_keywords.get(approach, 0) + 1
        
        # Return top approaches
        sorted_approaches = sorted(approach_keywords.items(), key=lambda x: x[1], reverse=True)
        return [{"approach": k, "frequency": v} for k, v in sorted_approaches[:10]]
    
    def _identify_success_factors(self, solutions: List[ProblemSolution]) -> List[str]:
        """Identify what makes solutions successful"""
        factors = []
        
        # Check for common patterns in explanations
        explanation_keywords = {}
        for solution in solutions:
            if solution.explanation:
                explanation_lower = solution.explanation.lower()
                # Look for success indicators
                success_indicators = ["worked", "successful", "effective", "resolved", "fixed", "solved"]
                for indicator in success_indicators:
                    if indicator in explanation_lower:
                        # Extract context
                        words = explanation_lower.split()
                        for i, word in enumerate(words):
                            if indicator in word and i > 0:
                                context = words[i - 1]
                                if len(context) > 3:
                                    explanation_keywords[context] = explanation_keywords.get(context, 0) + 1
        
        sorted_factors = sorted(explanation_keywords.items(), key=lambda x: x[1], reverse=True)
        return [factor for factor, _ in sorted_factors[:5]]

    def _find_common_pitfalls(self, solutions: List[ProblemSolution]) -> List[Dict[str, Any]]:
        """Find common pitfall keywords/phrases in failed/partial solutions."""
        pitfall_counts: Dict[str, int] = {}
        pitfall_terms = [
            "permission", "iam", "credentials", "timeout", "race", "deadlock", "mismatch",
            "missing", "null", "undefined", "version", "incompatible", "region", "quota",
            "cors", "auth", "token", "ssl", "dns", "network", "policy", "role", "schema"
        ]

        for s in solutions:
            text = f"{(s.solution or '')} {(s.explanation or '')} {(s.test_details or '')} {(s.implementation_result or '')}".lower()
            for term in pitfall_terms:
                if term in text:
                    pitfall_counts[term] = pitfall_counts.get(term, 0) + 1

        sorted_pitfalls = sorted(pitfall_counts.items(), key=lambda x: x[1], reverse=True)
        return [{"pitfall": k, "frequency": v} for k, v in sorted_pitfalls[:12]]

    def _identify_failure_factors(self, solutions: List[ProblemSolution]) -> List[str]:
        """Identify common failure factors from test_details / implementation_result."""
        factors: Dict[str, int] = {}
        indicators = ["failed", "error", "exception", "denied", "timeout", "missing", "invalid", "unable", "refused"]

        for s in solutions:
            blob = f"{(s.test_details or '')} {(s.implementation_result or '')} {(s.explanation or '')}".lower()
            words = blob.split()
            for ind in indicators:
                if ind in blob:
                    # capture a small context token before the indicator when possible
                    for i, w in enumerate(words):
                        if ind in w and i > 0:
                            ctx = words[i - 1].strip(" ,.;:()[]{}")
                            if len(ctx) > 3:
                                factors[ctx] = factors.get(ctx, 0) + 1

        sorted_factors = sorted(factors.items(), key=lambda x: x[1], reverse=True)
        return [k for k, _ in sorted_factors[:8]]

    def _analyze_tool_risks(self, solutions: List[ProblemSolution]) -> Dict[str, Any]:
        """Analyze tools/technologies that appear in failed solutions."""
        tool_counts: Dict[str, int] = {}
        common_tools = [
            "python", "javascript", "docker", "aws", "kubernetes", "terraform",
            "postgresql", "redis", "fastapi", "react", "node", "git"
        ]
        for s in solutions:
            text = f"{(s.solution or '')} {(s.code_example or '')}".lower()
            for t in common_tools:
                if t in text:
                    tool_counts[t] = tool_counts.get(t, 0) + 1

        return {
            "most_common_risky_tools": sorted(tool_counts.items(), key=lambda x: x[1], reverse=True)[:10],
            "total_unique_tools": len(tool_counts)
        }

    def _generate_failure_insights(self, patterns: Dict[str, Any], count: int) -> str:
        """Generate short narrative insights from failure patterns."""
        insights = [f"Analyzed {count} failed/partial solutions."]
        pitfalls = patterns.get("common_pitfalls") or []
        if pitfalls:
            top = pitfalls[0]
            insights.append(f"Most common pitfall keyword: {top['pitfall']} ({top['frequency']} occurrences)")
        tool_risks = patterns.get("tool_risks", {}).get("most_common_risky_tools") or []
        if tool_risks:
            insights.append(f"Most common risky tool keyword: {tool_risks[0][0]} ({tool_risks[0][1]} occurrences)")
        return " ".join(insights)
    
    def _analyze_tool_usage(self, solutions: List[ProblemSolution]) -> Dict[str, Any]:
        """Analyze what tools/technologies are used in successful solutions"""
        # Extract from code examples and solutions
        tool_keywords = {}
        common_tools = ["python", "javascript", "docker", "aws", "kubernetes", "terraform", 
                       "postgresql", "redis", "fastapi", "react", "node", "git"]
        
        for solution in solutions:
            text = f"{solution.solution} {solution.code_example or ''}".lower()
            for tool in common_tools:
                if tool in text:
                    tool_keywords[tool] = tool_keywords.get(tool, 0) + 1
        
        return {
            "most_used_tools": sorted(tool_keywords.items(), key=lambda x: x[1], reverse=True)[:10],
            "total_unique_tools": len(tool_keywords)
        }
    
    def _analyze_solution_structure(self, solutions: List[ProblemSolution]) -> Dict[str, Any]:
        """Analyze structure of successful solutions"""
        has_code = sum(1 for s in solutions if s.code_example) / len(solutions) if solutions else 0
        has_explanation = sum(1 for s in solutions if s.explanation) / len(solutions) if solutions else 0
        avg_length = sum(len(s.solution) for s in solutions) / len(solutions) if solutions else 0
        
        return {
            "has_code_example_percentage": has_code * 100,
            "has_explanation_percentage": has_explanation * 100,
            "average_solution_length": avg_length
        }
    
    def _generate_insights(self, patterns: Dict[str, Any], count: int) -> str:
        """Generate insights from patterns"""
        insights = [f"Analyzed {count} verified solutions."]
        
        if patterns.get("common_approaches"):
            top_approach = patterns["common_approaches"][0] if patterns["common_approaches"] else None
            if top_approach:
                insights.append(f"Most common approach: {top_approach['approach']} (used {top_approach['frequency']} times)")
        
        if patterns.get("tool_usage", {}).get("most_used_tools"):
            top_tool = patterns["tool_usage"]["most_used_tools"][0] if patterns["tool_usage"]["most_used_tools"] else None
            if top_tool:
                insights.append(f"Most used tool: {top_tool[0]} (used {top_tool[1]} times)")
        
        structure = patterns.get("solution_structure", {})
        if structure.get("has_code_example_percentage", 0) > 50:
            insights.append("Most successful solutions include code examples")
        
        return " ".join(insights)
