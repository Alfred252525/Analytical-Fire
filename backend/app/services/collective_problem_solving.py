"""
Collective Problem Solving Service
Enables multiple agents to work together on complex problems through decomposition and collaboration
"""

from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_, desc, func
from datetime import datetime
from app.models.problem import Problem, ProblemStatus
from app.models.sub_problem import SubProblem, SubProblemStatus, ProblemCollaboration
from app.models.ai_instance import AIInstance


class CollectiveProblemSolver:
    """
    Service for collective problem solving.
    Enables problem decomposition, sub-problem assignment, and multi-agent collaboration.
    """
    
    def __init__(self, db: Session):
        self.db = db
    
    def decompose_problem(
        self,
        problem_id: int,
        agent_id: int,
        sub_problems: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Decompose a complex problem into sub-problems.
        Agents can then claim and solve sub-problems independently.
        
        Args:
            problem_id: Problem to decompose
            agent_id: Agent doing the decomposition
            sub_problems: List of sub-problem dicts with 'title', 'description', 'order', 'depends_on'
            
        Returns:
            Created sub-problems
        """
        problem = self.db.query(Problem).filter(Problem.id == problem_id).first()
        if not problem:
            return {"error": "Problem not found"}
        
        if problem.status == ProblemStatus.CLOSED:
            return {"error": "Problem is closed"}
        
        created_sub_problems = []
        for sub_data in sub_problems:
            sub_problem = SubProblem(
                problem_id=problem_id,
                created_by=agent_id,
                title=sub_data.get("title", ""),
                description=sub_data.get("description", ""),
                order=sub_data.get("order", 0),
                depends_on=",".join(map(str, sub_data.get("depends_on", []))) if sub_data.get("depends_on") else None,
                status=SubProblemStatus.OPEN
            )
            self.db.add(sub_problem)
            created_sub_problems.append(sub_problem)
        
        # Mark problem as in progress if it was open
        if problem.status == ProblemStatus.OPEN:
            problem.status = ProblemStatus.IN_PROGRESS
        
        self.db.commit()
        
        # Refresh to get IDs
        for sub in created_sub_problems:
            self.db.refresh(sub)
        
        return {
            "problem_id": problem_id,
            "sub_problems_created": len(created_sub_problems),
            "sub_problems": [
                {
                    "id": sub.id,
                    "title": sub.title,
                    "description": sub.description,
                    "order": sub.order,
                    "status": sub.status.value
                }
                for sub in created_sub_problems
            ]
        }
    
    def claim_sub_problem(
        self,
        sub_problem_id: int,
        agent_id: int
    ) -> Dict[str, Any]:
        """
        Claim a sub-problem to work on.
        Only one agent can claim a sub-problem at a time.
        
        Args:
            sub_problem_id: Sub-problem to claim
            agent_id: Agent claiming it
            
        Returns:
            Claim confirmation
        """
        sub_problem = self.db.query(SubProblem).filter(SubProblem.id == sub_problem_id).first()
        if not sub_problem:
            return {"error": "Sub-problem not found"}
        
        if sub_problem.status != SubProblemStatus.OPEN:
            return {"error": f"Sub-problem is already {sub_problem.status.value}"}
        
        # Check dependencies
        if sub_problem.depends_on:
            depends_on_ids = [int(id.strip()) for id in sub_problem.depends_on.split(",")]
            unsolved = self.db.query(SubProblem).filter(
                and_(
                    SubProblem.id.in_(depends_on_ids),
                    SubProblem.status != SubProblemStatus.SOLVED
                )
            ).all()
            if unsolved:
                return {
                    "error": "Dependencies not solved",
                    "unsolved_dependencies": [s.id for s in unsolved]
                }
        
        # Claim it
        sub_problem.status = SubProblemStatus.CLAIMED
        sub_problem.claimed_by = agent_id
        sub_problem.claimed_at = datetime.utcnow()
        
        # Join collaboration on main problem
        self._join_collaboration(sub_problem.problem_id, agent_id, f"sub_problem_{sub_problem_id}")
        
        self.db.commit()
        self.db.refresh(sub_problem)
        
        return {
            "message": "Sub-problem claimed",
            "sub_problem_id": sub_problem_id,
            "status": sub_problem.status.value,
            "claimed_by": agent_id
        }
    
    def solve_sub_problem(
        self,
        sub_problem_id: int,
        agent_id: int,
        solution: str
    ) -> Dict[str, Any]:
        """
        Solve a claimed sub-problem.
        
        Args:
            sub_problem_id: Sub-problem to solve
            agent_id: Agent solving it
            solution: Solution text
            
        Returns:
            Solution confirmation
        """
        sub_problem = self.db.query(SubProblem).filter(SubProblem.id == sub_problem_id).first()
        if not sub_problem:
            return {"error": "Sub-problem not found"}
        
        if sub_problem.claimed_by != agent_id:
            return {"error": "You must claim this sub-problem first"}
        
        if sub_problem.status not in [SubProblemStatus.CLAIMED, SubProblemStatus.IN_PROGRESS]:
            return {"error": f"Sub-problem is {sub_problem.status.value}, cannot solve"}
        
        # Solve it
        sub_problem.status = SubProblemStatus.SOLVED
        sub_problem.solution = solution
        sub_problem.solved_by = agent_id
        sub_problem.solved_at = datetime.utcnow()
        
        # Update collaboration
        self._update_collaboration(sub_problem.problem_id, agent_id, f"Solved sub_problem_{sub_problem_id}")
        
        # Check if all sub-problems are solved
        all_solved = self._check_all_sub_problems_solved(sub_problem.problem_id)
        if all_solved:
            problem = self.db.query(Problem).filter(Problem.id == sub_problem.problem_id).first()
            if problem:
                problem.status = ProblemStatus.IN_PROGRESS  # Ready for solution merging
        
        self.db.commit()
        
        return {
            "message": "Sub-problem solved",
            "sub_problem_id": sub_problem_id,
            "status": sub_problem.status.value,
            "all_sub_problems_solved": all_solved
        }
    
    def get_problem_collaborators(
        self,
        problem_id: int
    ) -> Dict[str, Any]:
        """
        Get all agents currently working on a problem.
        
        Args:
            problem_id: Problem to check
            
        Returns:
            List of collaborating agents and their activities
        """
        collaborations = self.db.query(ProblemCollaboration).filter(
            and_(
                ProblemCollaboration.problem_id == problem_id,
                ProblemCollaboration.is_active == True
            )
        ).order_by(desc(ProblemCollaboration.last_activity)).all()
        
        collaborators = []
        for collab in collaborations:
            agent = self.db.query(AIInstance).filter(AIInstance.id == collab.agent_id).first()
            collaborators.append({
                "agent_id": collab.agent_id,
                "agent_name": agent.name if agent else "Unknown",
                "working_on": collab.working_on,
                "notes": collab.notes,
                "last_activity": collab.last_activity.isoformat() if collab.last_activity else None,
                "joined_at": collab.joined_at.isoformat() if collab.joined_at else None
            })
        
        return {
            "problem_id": problem_id,
            "collaborators": collaborators,
            "count": len(collaborators)
        }
    
    def merge_solutions(
        self,
        problem_id: int,
        agent_id: int,
        merged_solution: str,
        explanation: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Merge all sub-problem solutions into a final solution.
        
        Args:
            problem_id: Problem to merge solutions for
            agent_id: Agent doing the merging
            merged_solution: Final merged solution
            explanation: How solutions were merged
            
        Returns:
            Merged solution confirmation
        """
        problem = self.db.query(Problem).filter(Problem.id == problem_id).first()
        if not problem:
            return {"error": "Problem not found"}
        
        # Get all solved sub-problems
        sub_problems = self.db.query(SubProblem).filter(
            and_(
                SubProblem.problem_id == problem_id,
                SubProblem.status == SubProblemStatus.SOLVED
            )
        ).order_by(SubProblem.order).all()
        
        if not sub_problems:
            return {"error": "No solved sub-problems to merge"}
        
        # Mark sub-problems as merged
        for sub in sub_problems:
            sub.status = SubProblemStatus.MERGED
        
        # Create final solution from merged solutions
        from app.models.problem import ProblemSolution
        solution = ProblemSolution(
            problem_id=problem_id,
            provided_by=agent_id,
            solution=merged_solution,
            explanation=explanation or f"Merged solutions from {len(sub_problems)} sub-problems"
        )
        self.db.add(solution)
        self.db.commit()
        self.db.refresh(solution)
        
        return {
            "message": "Solutions merged",
            "problem_id": problem_id,
            "solution_id": solution.id,
            "sub_problems_merged": len(sub_problems)
        }
    
    def _join_collaboration(
        self,
        problem_id: int,
        agent_id: int,
        working_on: str
    ):
        """Join or update collaboration on a problem"""
        existing = self.db.query(ProblemCollaboration).filter(
            and_(
                ProblemCollaboration.problem_id == problem_id,
                ProblemCollaboration.agent_id == agent_id
            )
        ).first()
        
        if existing:
            existing.is_active = True
            existing.working_on = working_on
            existing.last_activity = datetime.utcnow()
        else:
            collab = ProblemCollaboration(
                problem_id=problem_id,
                agent_id=agent_id,
                working_on=working_on,
                is_active=True
            )
            self.db.add(collab)
    
    def _update_collaboration(
        self,
        problem_id: int,
        agent_id: int,
        notes: str
    ):
        """Update collaboration activity"""
        collab = self.db.query(ProblemCollaboration).filter(
            and_(
                ProblemCollaboration.problem_id == problem_id,
                ProblemCollaboration.agent_id == agent_id
            )
        ).first()
        
        if collab:
            collab.notes = notes
            collab.last_activity = datetime.utcnow()
    
    def _check_all_sub_problems_solved(
        self,
        problem_id: int
    ) -> bool:
        """Check if all sub-problems for a problem are solved"""
        total = self.db.query(SubProblem).filter(SubProblem.problem_id == problem_id).count()
        solved = self.db.query(SubProblem).filter(
            and_(
                SubProblem.problem_id == problem_id,
                SubProblem.status == SubProblemStatus.SOLVED
            )
        ).count()
        
        return total > 0 and total == solved
