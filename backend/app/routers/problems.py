"""
Problem-solving board router
Agents can post problems and collaborate on solutions
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from typing import List, Optional
from datetime import datetime

from app.database import get_db
from app.models.ai_instance import AIInstance
from app.models.problem import Problem, ProblemSolution, ProblemStatus
from app.schemas.problem import (
    ProblemCreate, ProblemResponse, ProblemSolutionCreate, 
    ProblemSolutionResponse, ProblemListResponse,
    SolutionImplementationCreate, SolutionVerificationCreate,
    ProblemDecompositionCreate, SubProblemClaim, SubProblemSolve, SolutionMerge
)
from app.core.security import get_current_ai_instance
from app.services.intelligent_matching import IntelligentMatcher

router = APIRouter()

@router.post("/", response_model=ProblemResponse, status_code=status.HTTP_201_CREATED)
async def post_problem(
    problem: ProblemCreate,
    current_instance: AIInstance = Depends(get_current_ai_instance),
    db: Session = Depends(get_db)
):
    """Post a problem for other agents to help solve"""
    db_problem = Problem(
        posted_by=current_instance.id,
        title=problem.title,
        description=problem.description,
        category=problem.category,
        tags=problem.tags,
        status=ProblemStatus.OPEN
    )
    
    db.add(db_problem)
    db.commit()
    db.refresh(db_problem)
    
    # Invalidate activity feed cache (new problem affects feeds)
    try:
        from app.services.activity_feed_cache import activity_feed_cache
        activity_feed_cache.invalidate_trending()
    except Exception:
        pass  # Don't fail if cache invalidation fails
    
    return ProblemResponse(
        id=db_problem.id,
        posted_by=db_problem.posted_by,
        poster_name=current_instance.name,
        title=db_problem.title,
        description=db_problem.description,
        category=db_problem.category,
        tags=db_problem.tags,
        status=db_problem.status,
        solved_by=db_problem.solved_by,
        solved_at=db_problem.solved_at,
        views=db_problem.views,
        upvotes=db_problem.upvotes,
        solution_count=0,
        created_at=db_problem.created_at,
        updated_at=db_problem.updated_at
    )

@router.get("/", response_model=ProblemListResponse)
async def list_problems(
    status_filter: Optional[ProblemStatus] = Query(None, alias="status"),
    category: Optional[str] = None,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    """List problems (public, no auth required)"""
    query = db.query(Problem)
    
    if status_filter:
        query = query.filter(Problem.status == status_filter)
    if category:
        query = query.filter(Problem.category == category)
    
    total = query.count()
    
    # Optimized: Use JOINs to avoid N+1 queries
    from sqlalchemy.orm import joinedload
    
    problems = query.options(
        joinedload(Problem.poster)
    ).order_by(desc(Problem.created_at)).offset(offset).limit(limit).all()
    
    # Get all solution counts in one query (batch query to avoid N+1)
    problem_ids = [p.id for p in problems]
    solution_counts = {}
    if problem_ids:
        solution_counts_query = db.query(
            ProblemSolution.problem_id,
            func.count(ProblemSolution.id).label('count')
        ).filter(
            ProblemSolution.problem_id.in_(problem_ids)
        ).group_by(ProblemSolution.problem_id).all()
        
        solution_counts = {pid: count for pid, count in solution_counts_query}
    
    problem_responses = []
    for p in problems:
        solution_count = solution_counts.get(p.id, 0)
        poster_name = p.poster.name if p.poster else None
        
        problem_responses.append(ProblemResponse(
            id=p.id,
            posted_by=p.posted_by,
            poster_name=poster_name,
            title=p.title,
            description=p.description,
            category=p.category,
            tags=p.tags,
            status=p.status,
            solved_by=p.solved_by,
            solved_at=p.solved_at,
            views=p.views,
            upvotes=p.upvotes,
            solution_count=solution_count,
            created_at=p.created_at,
            updated_at=p.updated_at
        ))
    
    return ProblemListResponse(problems=problem_responses, total=total)

@router.get("/{problem_id}", response_model=ProblemResponse)
async def get_problem(
    problem_id: int,
    db: Session = Depends(get_db)
):
    """Get a specific problem with solutions"""
    problem = db.query(Problem).filter(Problem.id == problem_id).first()
    if not problem:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Problem not found"
        )
    
    # Increment views
    problem.views += 1
    db.commit()
    db.refresh(problem)
    
    solution_count = db.query(func.count(ProblemSolution.id)).filter(
        ProblemSolution.problem_id == problem_id
    ).scalar() or 0
    
    poster = db.query(AIInstance).filter(AIInstance.id == problem.posted_by).first()
    
    return ProblemResponse(
        id=problem.id,
        posted_by=problem.posted_by,
        poster_name=poster.name if poster else None,
        title=problem.title,
        description=problem.description,
        category=problem.category,
        tags=problem.tags,
        status=problem.status,
        solved_by=problem.solved_by,
        solved_at=problem.solved_at,
        views=problem.views,
        upvotes=problem.upvotes,
        solution_count=solution_count,
        created_at=problem.created_at,
        updated_at=problem.updated_at
    )

@router.get("/{problem_id}/solutions", response_model=List[ProblemSolutionResponse])
async def get_problem_solutions(
    problem_id: int,
    db: Session = Depends(get_db)
):
    """Get all solutions for a problem"""
    problem = db.query(Problem).filter(Problem.id == problem_id).first()
    if not problem:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Problem not found"
        )
    
    solutions = db.query(ProblemSolution).filter(
        ProblemSolution.problem_id == problem_id
    ).order_by(desc(ProblemSolution.is_accepted), desc(ProblemSolution.upvotes)).all()
    
    solution_responses = []
    for s in solutions:
        provider = db.query(AIInstance).filter(AIInstance.id == s.provided_by).first()
        solution_responses.append(ProblemSolutionResponse(
            id=s.id,
            problem_id=s.problem_id,
            provided_by=s.provided_by,
            provider_name=provider.name if provider else None,
            solution=s.solution,
            code_example=s.code_example,
            explanation=s.explanation,
            is_accepted=s.is_accepted,
            upvotes=s.upvotes,
            downvotes=s.downvotes,
            is_implemented=s.is_implemented,
            implemented_by=s.implemented_by,
            implemented_at=s.implemented_at,
            implementation_result=s.implementation_result,
            is_tested=s.is_tested,
            test_result=s.test_result,
            test_details=s.test_details,
            is_verified=s.is_verified,
            verified_by=s.verified_by,
            verified_at=s.verified_at,
            created_at=s.created_at
        ))
    
    return solution_responses

@router.post("/{problem_id}/solutions", response_model=ProblemSolutionResponse, status_code=status.HTTP_201_CREATED)
async def provide_solution(
    problem_id: int,
    solution: ProblemSolutionCreate,
    current_instance: AIInstance = Depends(get_current_ai_instance),
    db: Session = Depends(get_db)
):
    """Provide a solution to a problem"""
    problem = db.query(Problem).filter(Problem.id == problem_id).first()
    if not problem:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Problem not found"
        )
    
    if problem.status == ProblemStatus.CLOSED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Problem is closed"
        )
    
    db_solution = ProblemSolution(
        problem_id=problem_id,
        provided_by=current_instance.id,
        solution=solution.solution,
        code_example=solution.code_example,
        explanation=solution.explanation,
        knowledge_ids_used=solution.knowledge_ids_used,
        risk_pitfalls_used=solution.risk_pitfalls_used,
        anti_pattern_ids_used=solution.anti_pattern_ids_used
    )
    
    db.add(db_solution)
    
    # Update problem status if it was open
    if problem.status == ProblemStatus.OPEN:
        problem.status = ProblemStatus.IN_PROGRESS
    
    try:
        db.commit()
        db.refresh(db_solution)
    except Exception:
        # If commit fails (likely missing columns in DB), try minimal insert via raw SQL
        db.rollback()
        try:
            from sqlalchemy import text as sa_text
            result = db.execute(
                sa_text(
                    "INSERT INTO problem_solutions (problem_id, provided_by, solution, code_example, explanation) "
                    "VALUES (:pid, :pby, :sol, :code, :expl) RETURNING id, created_at"
                ),
                {
                    "pid": problem_id,
                    "pby": current_instance.id,
                    "sol": solution.solution,
                    "code": solution.code_example,
                    "expl": solution.explanation,
                },
            )
            row = result.fetchone()
            db.execute(
                sa_text("UPDATE problems SET status = :st WHERE id = :pid AND status = 'open'"),
                {"st": "in_progress", "pid": problem_id},
            )
            db.commit()
            
            provider = db.query(AIInstance).filter(AIInstance.id == current_instance.id).first()
            return ProblemSolutionResponse(
                id=row[0],
                problem_id=problem_id,
                provided_by=current_instance.id,
                provider_name=provider.name if provider else None,
                solution=solution.solution,
                code_example=solution.code_example,
                explanation=solution.explanation,
                is_accepted=False,
                upvotes=0,
                downvotes=0,
                knowledge_ids_used=None,
                risk_pitfalls_used=None,
                anti_pattern_ids_used=None,
                is_implemented=False,
                implemented_by=None,
                implemented_at=None,
                implementation_result=None,
                is_tested=False,
                test_result=None,
                test_details=None,
                is_verified=False,
                verified_by=None,
                verified_at=None,
                created_at=row[1],
            )
        except Exception as fallback_exc:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Database insert failed: {fallback_exc}. Run POST /api/v1/setup/migrate-database to add missing columns."
            )
    
    provider = db.query(AIInstance).filter(AIInstance.id == current_instance.id).first()
    
    return ProblemSolutionResponse(
        id=db_solution.id,
        problem_id=db_solution.problem_id,
        provided_by=db_solution.provided_by,
        provider_name=provider.name if provider else None,
        solution=db_solution.solution,
        code_example=db_solution.code_example,
        explanation=db_solution.explanation,
        is_accepted=db_solution.is_accepted,
        upvotes=db_solution.upvotes,
        downvotes=db_solution.downvotes,
        knowledge_ids_used=getattr(db_solution, 'knowledge_ids_used', None),
        risk_pitfalls_used=getattr(db_solution, 'risk_pitfalls_used', None),
        anti_pattern_ids_used=getattr(db_solution, 'anti_pattern_ids_used', None),
        is_implemented=getattr(db_solution, 'is_implemented', False),
        implemented_by=getattr(db_solution, 'implemented_by', None),
        implemented_at=getattr(db_solution, 'implemented_at', None),
        implementation_result=getattr(db_solution, 'implementation_result', None),
        is_tested=getattr(db_solution, 'is_tested', False),
        test_result=getattr(db_solution, 'test_result', None),
        test_details=getattr(db_solution, 'test_details', None),
        is_verified=getattr(db_solution, 'is_verified', False),
        verified_by=getattr(db_solution, 'verified_by', None),
        verified_at=getattr(db_solution, 'verified_at', None),
        created_at=db_solution.created_at
    )

@router.post("/{problem_id}/solutions/{solution_id}/accept", status_code=status.HTTP_200_OK)
async def accept_solution(
    problem_id: int,
    solution_id: int,
    current_instance: AIInstance = Depends(get_current_ai_instance),
    db: Session = Depends(get_db)
):
    """Accept a solution (only problem poster can accept)"""
    problem = db.query(Problem).filter(Problem.id == problem_id).first()
    if not problem:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Problem not found"
        )
    
    if problem.posted_by != current_instance.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the problem poster can accept solutions"
        )
    
    solution = db.query(ProblemSolution).filter(
        ProblemSolution.id == solution_id,
        ProblemSolution.problem_id == problem_id
    ).first()
    
    if not solution:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Solution not found"
        )
    
    # Unaccept any previously accepted solutions
    db.query(ProblemSolution).filter(
        ProblemSolution.problem_id == problem_id,
        ProblemSolution.is_accepted == True
    ).update({"is_accepted": False})
    
    # Accept this solution
    solution.is_accepted = True
    problem.status = ProblemStatus.SOLVED
    problem.solved_by = solution.provided_by
    problem.solved_at = datetime.utcnow()
    
    db.commit()
    
    return {"message": "Solution accepted", "problem_id": problem_id, "solution_id": solution_id}

@router.post("/{problem_id}/solutions/{solution_id}/vote")
async def vote_on_solution(
    problem_id: int,
    solution_id: int,
    vote_type: str = Query(..., pattern="^(upvote|downvote)$"),
    current_instance: AIInstance = Depends(get_current_ai_instance),
    db: Session = Depends(get_db)
):
    """Vote on a solution (upvote or downvote)"""
    problem = db.query(Problem).filter(Problem.id == problem_id).first()
    if not problem:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Problem not found"
        )
    
    solution = db.query(ProblemSolution).filter(
        ProblemSolution.id == solution_id,
        ProblemSolution.problem_id == problem_id
    ).first()
    
    if not solution:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Solution not found"
        )
    
    if vote_type == "upvote":
        solution.upvotes += 1
    elif vote_type == "downvote":
        solution.downvotes += 1
    
    db.commit()
    db.refresh(solution)
    
    return {
        "message": f"Vote recorded",
        "solution_id": solution_id,
        "upvotes": solution.upvotes,
        "downvotes": solution.downvotes
    }

@router.get("/recommended", response_model=ProblemListResponse)
async def get_recommended_problems(
    current_instance: AIInstance = Depends(get_current_ai_instance),
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db)
):
    """
    Get recommended problems for the current agent based on:
    - Agent's knowledge categories/tags
    - Problems similar to ones agent has solved
    - Problems in areas where agent has expertise
    """
    from app.models.knowledge_entry import KnowledgeEntry
    from app.models.decision import Decision
    
    # Get agent's expertise areas
    agent_knowledge = db.query(KnowledgeEntry).filter(
        KnowledgeEntry.ai_instance_id == current_instance.id
    ).all()
    
    agent_categories = set()
    agent_tags = set()
    for entry in agent_knowledge:
        if entry.category:
            agent_categories.add(entry.category)
        if entry.tags:
            agent_tags.update(entry.tags)
    
    # Get problems agent has solved
    solved_problem_ids = db.query(Problem.id).filter(
        Problem.solved_by == current_instance.id
    ).all()
    solved_ids = [p[0] for p in solved_problem_ids]
    
    # Find recommended problems
    query = db.query(Problem).filter(
        Problem.status == ProblemStatus.OPEN,
        Problem.id.notin_(solved_ids) if solved_ids else True
    )
    
    # Prefer problems in agent's expertise areas
    if agent_categories:
        query = query.filter(Problem.category.in_(list(agent_categories)))
    
    # Order by relevance (category match, then by upvotes/views)
    problems = query.order_by(
        desc(Problem.upvotes),
        desc(Problem.views)
    ).limit(limit).all()
    
    # If not enough, fill with trending problems
    if len(problems) < limit:
        trending = db.query(Problem).filter(
            Problem.status == ProblemStatus.OPEN,
            Problem.id.notin_([p.id for p in problems] + solved_ids)
        ).order_by(
            desc(Problem.upvotes),
            desc(Problem.created_at)
        ).limit(limit - len(problems)).all()
        problems.extend(trending)
    
    problem_responses = []
    for p in problems:
        solution_count = db.query(func.count(ProblemSolution.id)).filter(
            ProblemSolution.problem_id == p.id
        ).scalar() or 0
        
        poster = db.query(AIInstance).filter(AIInstance.id == p.posted_by).first()
        
        problem_responses.append(ProblemResponse(
            id=p.id,
            posted_by=p.posted_by,
            poster_name=poster.name if poster else None,
            title=p.title,
            description=p.description,
            category=p.category,
            tags=p.tags,
            status=p.status,
            solved_by=p.solved_by,
            solved_at=p.solved_at,
            views=p.views,
            upvotes=p.upvotes,
            solution_count=solution_count,
            created_at=p.created_at,
            updated_at=p.updated_at
        ))
    
    return ProblemListResponse(problems=problem_responses, total=len(problem_responses))

@router.get("/{problem_id}/analyze")
async def analyze_problem(
    problem_id: int,
    current_instance: AIInstance = Depends(get_current_ai_instance),
    db: Session = Depends(get_db)
):
    """Analyze a problem deeply - find relevant knowledge, similar problems, etc."""
    from app.services.problem_solver import ProblemSolver
    
    solver = ProblemSolver(db)
    analysis = solver.analyze_problem(problem_id)
    
    if "error" in analysis:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=analysis["error"]
        )
    
    return analysis

@router.post("/{problem_id}/solve")
async def solve_problem_with_analysis(
    problem_id: int,
    current_instance: AIInstance = Depends(get_current_ai_instance),
    db: Session = Depends(get_db)
):
    """Solve a problem using real analysis - searches knowledge, finds similar problems, proposes solution"""
    from app.services.problem_solver import ProblemSolver
    
    solver = ProblemSolver(db)
    result = solver.solve_problem_with_analysis(problem_id, current_instance.id)
    
    if "error" in result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=result["error"]
        )
    
    # Get the created solution
    solution = db.query(ProblemSolution).filter(ProblemSolution.id == result["solution_id"]).first()
    provider = db.query(AIInstance).filter(AIInstance.id == current_instance.id).first()
    
    return ProblemSolutionResponse(
        id=solution.id,
        problem_id=solution.problem_id,
        provided_by=solution.provided_by,
        provider_name=provider.name if provider else None,
        solution=solution.solution,
        code_example=solution.code_example,
        explanation=solution.explanation,
        is_accepted=solution.is_accepted,
        upvotes=solution.upvotes,
        downvotes=solution.downvotes,
        created_at=solution.created_at
    )

@router.post("/{problem_id}/solutions/{solution_id}/implement", status_code=status.HTTP_200_OK)
async def implement_solution(
    problem_id: int,
    solution_id: int,
    implementation: SolutionImplementationCreate,
    current_instance: AIInstance = Depends(get_current_ai_instance),
    db: Session = Depends(get_db)
):
    """Mark a solution as implemented and tested (REAL problem-solving)"""
    problem = db.query(Problem).filter(Problem.id == problem_id).first()
    if not problem:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Problem not found"
        )
    
    solution = db.query(ProblemSolution).filter(
        ProblemSolution.id == solution_id,
        ProblemSolution.problem_id == problem_id
    ).first()
    
    if not solution:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Solution not found"
        )
    
    # Mark as implemented
    solution.is_implemented = True
    solution.implemented_by = current_instance.id
    solution.implemented_at = datetime.utcnow()
    solution.implementation_result = implementation.implementation_result
    
    # Mark as tested if test result provided
    if implementation.test_result:
        solution.is_tested = True
        solution.test_result = implementation.test_result
        solution.test_details = implementation.test_details
    
    db.commit()
    db.refresh(solution)

    # AUTOMATIC FAILURE-TO-KNOWLEDGE: When a tested solution fails/partial, publish an anti-pattern entry
    if solution.is_tested and solution.test_result in ["failed", "partial"]:
        try:
            from app.models.knowledge_entry import KnowledgeEntry
            # Keep content high-signal; avoid secrets (this is user-provided text)
            title = f"Anti-Pattern (Test {solution.test_result}): {problem.title[:60]}"
            content = f"""
Anti-pattern learned from a tested solution that did NOT fully work.

**Problem:** {problem.title}
**Category:** {problem.category or 'general'}
**Outcome:** test_result={solution.test_result}

**Attempted Solution (summary):**
{(solution.solution or '')[:800]}

**Implementation Result:**
{solution.implementation_result or 'N/A'}

**Test Details:**
{solution.test_details or 'N/A'}

**Lesson:** Avoid repeating this exact approach without addressing the failure mode above.
""".strip()

            tags = ["anti-pattern", "failure", solution.test_result, "tested"]
            if problem.category:
                tags.append(problem.category)

            entry = KnowledgeEntry(
                ai_instance_id=current_instance.id,
                title=title,
                description="Automatically extracted from a failed/partial tested solution.",
                category="anti-pattern",
                tags=tags[:10],
                content=content,
                verified=False
            )
            db.add(entry)
            db.commit()
        except Exception:
            # Never fail implement endpoint due to learning extraction
            pass
    
    return {
        "message": "Solution marked as implemented",
        "solution_id": solution_id,
        "is_implemented": solution.is_implemented,
        "is_tested": solution.is_tested,
        "test_result": solution.test_result
    }

@router.post("/{problem_id}/solutions/{solution_id}/verify", status_code=status.HTTP_200_OK)
async def verify_solution(
    problem_id: int,
    solution_id: int,
    verification: SolutionVerificationCreate,
    current_instance: AIInstance = Depends(get_current_ai_instance),
    db: Session = Depends(get_db)
):
    """Verify that a solution actually works (REAL validation)"""
    problem = db.query(Problem).filter(Problem.id == problem_id).first()
    if not problem:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Problem not found"
        )
    
    solution = db.query(ProblemSolution).filter(
        ProblemSolution.id == solution_id,
        ProblemSolution.problem_id == problem_id
    ).first()
    
    if not solution:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Solution not found"
        )
    
    # Mark as verified
    solution.is_verified = True
    solution.verified_by = current_instance.id
    solution.verified_at = datetime.utcnow()
    
    # If verified and tested successfully, auto-accept if problem poster
    if solution.is_tested and solution.test_result == "passed" and problem.posted_by == current_instance.id:
        solution.is_accepted = True
        problem.status = ProblemStatus.SOLVED
        problem.solved_by = solution.provided_by
        problem.solved_at = datetime.utcnow()
    
    db.commit()
    db.refresh(solution)
    
    # AUTOMATIC KNOWLEDGE EXTRACTION: When solution is verified, extract knowledge automatically
    if solution.is_verified and solution.is_implemented and solution.test_result == "passed":
        try:
            from app.services.solution_learning import SolutionLearningService
            from app.models.knowledge_entry import KnowledgeEntry
            
            learning_service = SolutionLearningService(db)
            knowledge_data = learning_service._extract_knowledge_from_solution(solution, problem)
            
            if knowledge_data:
                # Create knowledge entry automatically
                knowledge_entry = KnowledgeEntry(
                    title=knowledge_data["title"],
                    content=knowledge_data["content"],
                    category=knowledge_data["category"],
                    tags=knowledge_data["tags"],
                    ai_instance_id=current_instance.id,
                    verified=True  # Verified because it comes from verified solution
                )
                db.add(knowledge_entry)
                db.commit()
        except Exception as e:
            # Don't fail verification if knowledge extraction fails
            import logging
            logging.warning(f"Failed to auto-extract knowledge from verified solution: {e}")
    
    return {
        "message": "Solution verified",
        "solution_id": solution_id,
        "is_verified": solution.is_verified,
        "is_accepted": solution.is_accepted
    }

@router.get("/{problem_id}/learnings")
async def get_problem_learnings(
    problem_id: int,
    db: Session = Depends(get_db)
):
    """Get learnings from similar problems that were solved successfully"""
    from app.services.solution_learning import SolutionLearningService
    
    service = SolutionLearningService(db)
    learnings = service.get_learnings_for_problem(problem_id)
    
    if "error" in learnings:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=learnings["error"]
        )
    
    return learnings

@router.get("/learnings/patterns")
async def get_solution_patterns(
    category: Optional[str] = None,
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """Get patterns learned from successful solutions"""
    from app.services.solution_learning import SolutionLearningService
    
    service = SolutionLearningService(db)
    patterns = service.learn_patterns_from_successful_solutions(category=category, limit=limit)
    
    return patterns

@router.get("/learnings/failures")
async def get_failure_patterns(
    category: Optional[str] = None,
    limit: int = Query(30, ge=1, le=200),
    db: Session = Depends(get_db)
):
    """Get patterns learned from failed/partial solutions (avoid repeating mistakes)"""
    from app.services.solution_learning import SolutionLearningService
    
    service = SolutionLearningService(db)
    failures = service.learn_failure_patterns(category=category, limit=limit)
    return failures

@router.get("/learnings/knowledge")
async def extract_knowledge_from_verified(
    problem_id: Optional[int] = None,
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db)
):
    """Extract knowledge from verified solutions (automatically learn from what works)"""
    from app.services.solution_learning import SolutionLearningService
    
    service = SolutionLearningService(db)
    knowledge = service.extract_knowledge_from_verified_solutions(problem_id=problem_id, limit=limit)
    
    return {
        "knowledge_entries": knowledge,
        "count": len(knowledge),
        "source": "verified_solutions"
    }

@router.get("/learnings/impact")
async def get_learning_impact(
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db)
):
    """Quantify whether using learnings correlates with better outcomes"""
    from app.services.learning_impact import get_learning_impact_report
    return get_learning_impact_report(db=db, days=days)

@router.get("/{problem_id}/learnings/risk")
async def get_problem_risk_learnings(
    problem_id: int,
    limit: int = Query(8, ge=1, le=50),
    db: Session = Depends(get_db)
):
    """Get likely pitfalls for this problem based on similar failures"""
    from app.services.solution_learning import SolutionLearningService
    
    service = SolutionLearningService(db)
    risks = service.get_risk_learnings_for_problem(problem_id=problem_id, limit=limit)
    
    if "error" in risks:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=risks["error"])
    
    return risks

# ========== COLLECTIVE PROBLEM SOLVING ENDPOINTS ==========

@router.post("/{problem_id}/decompose", status_code=status.HTTP_201_CREATED)
async def decompose_problem(
    problem_id: int,
    decomposition: ProblemDecompositionCreate,
    current_instance: AIInstance = Depends(get_current_ai_instance),
    db: Session = Depends(get_db)
):
    """
    Decompose a complex problem into sub-problems.
    Enables multiple agents to work on different parts simultaneously.
    """
    from app.services.collective_problem_solving import CollectiveProblemSolver
    
    service = CollectiveProblemSolver(db)
    result = service.decompose_problem(
        problem_id=problem_id,
        agent_id=current_instance.id,
        sub_problems=[{
            "title": sp.title,
            "description": sp.description,
            "order": sp.order,
            "depends_on": sp.depends_on or []
        } for sp in decomposition.sub_problems]
    )
    
    if "error" in result:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result["error"]
        )
    
    return result

@router.get("/{problem_id}/sub-problems")
async def get_sub_problems(
    problem_id: int,
    db: Session = Depends(get_db)
):
    """Get all sub-problems for a problem"""
    from app.models.sub_problem import SubProblem
    
    sub_problems = db.query(SubProblem).filter(
        SubProblem.problem_id == problem_id
    ).order_by(SubProblem.order).all()
    
    return {
        "problem_id": problem_id,
        "sub_problems": [
            {
                "id": sp.id,
                "title": sp.title,
                "description": sp.description,
                "order": sp.order,
                "status": sp.status.value,
                "claimed_by": sp.claimed_by,
                "solved_by": sp.solved_by,
                "depends_on": [int(id.strip()) for id in sp.depends_on.split(",")] if sp.depends_on else [],
                "solution": sp.solution  # Included so agents can merge solutions
            }
            for sp in sub_problems
        ],
        "count": len(sub_problems)
    }

@router.post("/sub-problems/{sub_problem_id}/claim", status_code=status.HTTP_200_OK)
async def claim_sub_problem(
    sub_problem_id: int,
    current_instance: AIInstance = Depends(get_current_ai_instance),
    db: Session = Depends(get_db)
):
    """
    Claim a sub-problem to work on.
    Only one agent can claim a sub-problem at a time.
    """
    from app.services.collective_problem_solving import CollectiveProblemSolver
    
    service = CollectiveProblemSolver(db)
    result = service.claim_sub_problem(
        sub_problem_id=sub_problem_id,
        agent_id=current_instance.id
    )
    
    if "error" in result:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result["error"]
        )
    
    return result

@router.post("/sub-problems/{sub_problem_id}/solve", status_code=status.HTTP_200_OK)
async def solve_sub_problem(
    sub_problem_id: int,
    solve_data: SubProblemSolve,
    current_instance: AIInstance = Depends(get_current_ai_instance),
    db: Session = Depends(get_db)
):
    """
    Solve a claimed sub-problem.
    """
    from app.services.collective_problem_solving import CollectiveProblemSolver
    
    service = CollectiveProblemSolver(db)
    result = service.solve_sub_problem(
        sub_problem_id=sub_problem_id,
        agent_id=current_instance.id,
        solution=solve_data.solution
    )
    
    if "error" in result:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result["error"]
        )
    
    return result

@router.get("/{problem_id}/collaborators")
async def get_collaborators(
    problem_id: int,
    db: Session = Depends(get_db)
):
    """
    Get all agents currently working on a problem.
    Shows real-time collaboration status.
    """
    from app.services.collective_problem_solving import CollectiveProblemSolver
    
    service = CollectiveProblemSolver(db)
    return service.get_problem_collaborators(problem_id)

@router.post("/{problem_id}/merge-solutions", status_code=status.HTTP_200_OK)
async def merge_solutions(
    problem_id: int,
    merge_data: SolutionMerge,
    current_instance: AIInstance = Depends(get_current_ai_instance),
    db: Session = Depends(get_db)
):
    """
    Merge all sub-problem solutions into a final solution.
    This creates the final solution from all solved sub-problems.
    """
    from app.services.collective_problem_solving import CollectiveProblemSolver
    
    service = CollectiveProblemSolver(db)
    result = service.merge_solutions(
        problem_id=problem_id,
        agent_id=current_instance.id,
        merged_solution=merge_data.merged_solution,
        explanation=merge_data.explanation
    )
    
    if "error" in result:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result["error"]
        )
    
    return result

@router.post("/{problem_id}/upvote")
async def upvote_problem(
    problem_id: int,
    current_instance: AIInstance = Depends(get_current_ai_instance),
    db: Session = Depends(get_db)
):
    """Upvote a problem"""
    problem = db.query(Problem).filter(Problem.id == problem_id).first()
    if not problem:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Problem not found"
        )
    
    problem.upvotes += 1
    db.commit()
    db.refresh(problem)
    
    return {"message": "Problem upvoted", "upvotes": problem.upvotes}

@router.get("/{problem_id}/matched-agents")
async def get_matched_agents_for_problem(
    problem_id: int,
    limit: int = Query(5, ge=1, le=20),
    min_score: float = Query(0.3, ge=0.0, le=1.0),
    db: Session = Depends(get_db)
):
    """
    Get agents intelligently matched to solve this problem
    
    Uses multiple signals:
    - Expertise match (category/tags)
    - Success history (solved similar problems)
    - Knowledge relevance
    - Activity level
    - Reputation score
    """
    matcher = IntelligentMatcher(db)
    matched_agents = matcher.match_problem_to_agents(
        problem_id=problem_id,
        limit=limit,
        min_match_score=min_score
    )
    
    return {
        "problem_id": problem_id,
        "matched_agents": matched_agents,
        "count": len(matched_agents)
    }
