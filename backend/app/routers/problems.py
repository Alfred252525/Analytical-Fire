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
    ProblemSolutionResponse, ProblemListResponse
)
from app.core.security import get_current_ai_instance

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
    
    problems = query.order_by(desc(Problem.created_at)).offset(offset).limit(limit).all()
    
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
        explanation=solution.explanation
    )
    
    db.add(db_solution)
    
    # Update problem status if it was open
    if problem.status == ProblemStatus.OPEN:
        problem.status = ProblemStatus.IN_PROGRESS
    
    db.commit()
    db.refresh(db_solution)
    
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
