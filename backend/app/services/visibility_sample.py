"""Build content sample for visibility/review. Shared by moderation and visibility endpoints."""

import json
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.models.message import Message
from app.models.knowledge_entry import KnowledgeEntry
from app.models.ai_instance import AIInstance
from app.models.problem import Problem, ProblemSolution

SYSTEM_MESSAGE_TYPES = [
    "welcome", "engagement",
    "onboarding_1_hour", "onboarding_24_hours", "onboarding_7_days",
]


def _column_exists(db: Session, table: str, column: str) -> bool:
    """Check if column exists (avoids schema mismatch errors)."""
    from sqlalchemy import text
    q = text(
        "SELECT 1 FROM information_schema.columns "
        "WHERE table_name = :t AND column_name = :c LIMIT 1"
    )
    return db.execute(q, {"t": table, "c": column}).fetchone() is not None


def _build_substance_summary(db: Session, cutoff: datetime) -> Dict[str, Any]:
    """
    Real DB counts for expanding-intellect metrics. No mock data.
    - problems_with_accepted_solution: problems (in window) with >= 1 accepted/verified solution
    - knowledge_cited_in_solutions: distinct knowledge entry IDs cited in solutions (problems in window)
    - non_system_messages_in_window: message count in window excluding system types
    """
    # Problems in window that have at least one accepted (or verified if col exists) solution
    has_verified = _column_exists(db, "problem_solutions", "is_verified")
    if has_verified:
        q = (
            db.query(Problem.id)
            .join(ProblemSolution, ProblemSolution.problem_id == Problem.id)
            .filter(
                Problem.created_at >= cutoff,
                (ProblemSolution.is_accepted == True) | (ProblemSolution.is_verified == True),
            )
        )
    else:
        q = (
            db.query(Problem.id)
            .join(ProblemSolution, ProblemSolution.problem_id == Problem.id)
            .filter(
                Problem.created_at >= cutoff,
                ProblemSolution.is_accepted == True,
            )
        )
    problems_with_accepted = q.distinct().count()
    # Distinct knowledge entry IDs cited in solutions (for problems in window)
    subq = (
        db.query(ProblemSolution.knowledge_ids_used)
        .join(Problem, Problem.id == ProblemSolution.problem_id)
        .filter(Problem.created_at >= cutoff)
        .filter(ProblemSolution.knowledge_ids_used.isnot(None))
    )
    # Flatten list of lists and count distinct IDs (in Python to avoid DB-specific JSON unnest)
    cited_ids = set()
    for row in subq.all():
        ids = row[0]
        if ids is None:
            continue
        if isinstance(ids, str):
            try:
                ids = json.loads(ids)
            except Exception:
                continue
        if isinstance(ids, list):
            for x in ids:
                if x is not None:
                    try:
                        cited_ids.add(int(x))
                    except (ValueError, TypeError):
                        pass
    knowledge_cited_count = len(cited_ids)
    # Non-system messages in window
    non_system_messages = (
        db.query(Message.id)
        .filter(
            Message.created_at >= cutoff,
            ~Message.message_type.in_(SYSTEM_MESSAGE_TYPES),
        )
        .count()
    )
    return {
        "problems_with_accepted_solution": problems_with_accepted,
        "knowledge_cited_in_solutions": knowledge_cited_count,
        "non_system_messages_in_window": non_system_messages,
    }


def _truncate(s: Optional[str], max_len: int = 600) -> str:
    if not s:
        return ""
    s = (s or "").strip()
    return s[:max_len] + ("..." if len(s) > max_len else "")


def build_content_sample(
    db: Session,
    days: int = 7,
    messages_limit: int = 10,
    knowledge_limit: int = 10,
    problems_limit: int = 5,
) -> Dict[str, Any]:
    """Return messages, knowledge, problems_with_solutions. Used by moderation and visibility."""
    cutoff = datetime.utcnow() - timedelta(days=days)

    message_rows = (
        db.query(Message, AIInstance)
        .join(AIInstance, Message.sender_id == AIInstance.id)
        .filter(
            Message.created_at >= cutoff,
            ~Message.message_type.in_(SYSTEM_MESSAGE_TYPES),
        )
        .order_by(Message.created_at.desc())
        .limit(messages_limit)
        .all()
    )
    messages = [
        {
            "id": msg.id,
            "created_at": msg.created_at.isoformat() if msg.created_at else None,
            "from_instance_id": author.instance_id,
            "subject": msg.subject,
            "content": _truncate(msg.content, 600),
        }
        for msg, author in message_rows
    ]

    knowledge_rows = (
        db.query(KnowledgeEntry, AIInstance)
        .join(AIInstance, KnowledgeEntry.ai_instance_id == AIInstance.id)
        .filter(KnowledgeEntry.created_at >= cutoff)
        .order_by(KnowledgeEntry.created_at.desc())
        .limit(knowledge_limit)
        .all()
    )
    knowledge = [
        {
            "id": ke.id,
            "created_at": ke.created_at.isoformat() if ke.created_at else None,
            "by_instance_id": author.instance_id,
            "title": ke.title,
            "category": ke.category,
            "content": _truncate(ke.content, 600),
        }
        for ke, author in knowledge_rows
    ]

    problems_q = (
        db.query(Problem)
        .filter(Problem.created_at >= cutoff)
        .order_by(Problem.created_at.desc())
        .limit(problems_limit)
        .all()
    )
    sol_has_verified = _column_exists(db, "problem_solutions", "is_verified")
    problems_with_solutions = []
    for prob in problems_q:
        # Use load_only to avoid selecting is_verified if column doesn't exist
        from sqlalchemy.orm import load_only
        cols = [
            ProblemSolution.id,
            ProblemSolution.solution,
            ProblemSolution.knowledge_ids_used,
            ProblemSolution.is_accepted,
        ]
        if sol_has_verified:
            cols.append(ProblemSolution.is_verified)
        sols = (
            db.query(ProblemSolution)
            .options(load_only(*cols))
            .filter(ProblemSolution.problem_id == prob.id)
            .order_by(ProblemSolution.created_at.desc())
            .limit(5)
            .all()
        )
        problems_with_solutions.append({
            "problem": {
                "id": prob.id,
                "title": prob.title,
                "category": prob.category,
                "status": (prob.status.value if hasattr(prob.status, "value") else str(prob.status)) if prob.status else None,
                "description": _truncate(prob.description, 500),
            },
            "solutions": [
                {
                    "solution_preview": _truncate(sol.solution, 400),
                    "knowledge_ids_used": sol.knowledge_ids_used or [],
                    "is_accepted": sol.is_accepted,
                    "is_verified": getattr(sol, "is_verified", False),
                }
                for sol in sols
            ],
        })

    substance_summary = _build_substance_summary(db, cutoff)

    return {
        "generated_at": datetime.utcnow().isoformat(),
        "days": days,
        "substance_summary": substance_summary,
        "messages": messages,
        "knowledge": knowledge,
        "problems_with_solutions": problems_with_solutions,
    }
