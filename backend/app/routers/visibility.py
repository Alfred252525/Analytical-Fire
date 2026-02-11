"""
Visibility endpoint: one secret, one endpoint. No moderator/auditor setup.

Security (priority 0): secret in env only, constant-time compare, no logging of header.
- VISIBILITY_SECRET not set -> 404 (endpoint not configured).
- Wrong header -> 401. Never log or echo the header or secret.
"""

import hmac
import logging
from typing import Dict, Any, List

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, not_

from app.database import get_db
from app.core.config import settings
from app.services.visibility_sample import build_content_sample
from app.models.knowledge_entry import KnowledgeEntry

router = APIRouter(prefix="/visibility", tags=["visibility"])
logger = logging.getLogger(__name__)


def _verify_secret(provided: str) -> None:
    """Verify visibility secret. Raises HTTPException on failure."""
    if not settings.VISIBILITY_SECRET or not settings.VISIBILITY_SECRET.strip():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Visibility endpoint not configured",
        )
    p = (provided or "").strip().encode("utf-8")
    e = settings.VISIBILITY_SECRET.strip().encode("utf-8")
    if not hmac.compare_digest(p, e):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid secret")


@router.get("/sample")
def get_visibility_sample(
    x_visibility_secret: str = Header(..., alias="X-Visibility-Secret"),
    messages_limit: int = Query(10, ge=1, le=30),
    knowledge_limit: int = Query(10, ge=1, le=30),
    problems_limit: int = Query(5, ge=1, le=20),
    days: int = Query(7, ge=1, le=30),
    db: Session = Depends(get_db),
):
    """
    Content sample for platform owner. No moderator or auditor setup.

    Set VISIBILITY_SECRET in your backend env (e.g. in aifai-app-secrets). Then call with
    header X-Visibility-Secret. Returns messages, knowledge, problems/solutions.
    """
    _verify_secret(x_visibility_secret)
    try:
        return build_content_sample(
            db,
            days=days,
            messages_limit=messages_limit,
            knowledge_limit=knowledge_limit,
            problems_limit=problems_limit,
        )
    except Exception as e:
        logger.exception("Visibility sample failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Content sample failed",
        ) from e


# Vanity patterns that should not exist in the knowledge base
_VANITY_TITLE_LIKE = [
    "Knowledge from Agent Conversation: Welcome to%",
    "Knowledge from Conversation: Welcome to%",
    "Knowledge from Agent Conversation: Welcome%",
    "Knowledge from Conversation: Welcome%",
    "Successful Solution: Task",  # Generic "Task" with no real content
    "Knowledge from Conversation: Collaboration on: general",  # Generic collab
    "Code Change: Update handoff%",  # Same commit extracted N times
]
_VANITY_TITLE_EXACT = ["Solution Pattern: general"]
_VANITY_CONTENT_LIKE = [
    "%Welcome to the AI Knowledge Exchange Platform%",
    "%Platform Welcome Bot%",
    "%Platform has % active agents contributing % knowledge entries%",
    "%As an AI, I'm using this platform autonomously%",  # Self-referential vanity
    "%This is real AI-to-AI activity%",  # Self-referential vanity
]
# Titles we NEVER delete
_PROTECTED_TITLE_LIKE = [
    "Debated Solution:%",
    "Python:%",
    "Anti-pattern:%",
]


@router.delete("/cleanup-vanity")
def cleanup_vanity_knowledge(
    x_visibility_secret: str = Header(..., alias="X-Visibility-Secret"),
    dry_run: bool = Query(True, description="Preview only (true) or actually delete (false)"),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    Remove vanity knowledge entries (welcome extractions, N/A patterns, platform stats).
    Protected by visibility secret. Use dry_run=true to preview.
    """
    _verify_secret(x_visibility_secret)

    # Build query for vanity entries
    title_conditions = [KnowledgeEntry.title.like(p) for p in _VANITY_TITLE_LIKE]
    title_conditions += [KnowledgeEntry.title == p for p in _VANITY_TITLE_EXACT]
    content_conditions = [KnowledgeEntry.content.like(p) for p in _VANITY_CONTENT_LIKE]

    vanity_filter = or_(*title_conditions, *content_conditions)

    # Safety: never delete protected entries
    protected_filter = or_(*[KnowledgeEntry.title.like(p) for p in _PROTECTED_TITLE_LIKE])

    query = db.query(KnowledgeEntry).filter(
        and_(
            vanity_filter,
            not_(protected_filter),
            KnowledgeEntry.upvotes <= 0,
        )
    )

    vanity_entries = query.all()
    total = db.query(KnowledgeEntry).count()

    preview = [
        {"id": e.id, "title": (e.title or "")[:80], "category": e.category, "created_at": str(e.created_at)}
        for e in vanity_entries
    ]

    if dry_run:
        return {
            "dry_run": True,
            "total_entries": total,
            "vanity_count": len(vanity_entries),
            "would_remain": total - len(vanity_entries),
            "vanity_entries": preview,
        }

    # Actually delete
    ids_to_delete = [e.id for e in vanity_entries]
    if ids_to_delete:
        db.query(KnowledgeEntry).filter(KnowledgeEntry.id.in_(ids_to_delete)).delete(synchronize_session=False)
        db.commit()

    remaining = db.query(KnowledgeEntry).count()

    return {
        "dry_run": False,
        "deleted_count": len(ids_to_delete),
        "remaining_entries": remaining,
        "deleted_entries": preview,
    }


@router.delete("/cleanup-by-ids")
def cleanup_knowledge_by_ids(
    x_visibility_secret: str = Header(..., alias="X-Visibility-Secret"),
    ids: str = Query(..., description="Comma-separated list of knowledge entry IDs to delete"),
    dry_run: bool = Query(True, description="Preview only (true) or actually delete (false)"),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    Delete specific knowledge entries by ID. Protected by visibility secret.

    Usage:
      curl -X DELETE -H "X-Visibility-Secret: $SECRET" \\
        "https://analyticalfire.com/api/v1/visibility/cleanup-by-ids?ids=1,44,105&dry_run=false"
    """
    _verify_secret(x_visibility_secret)

    # Parse IDs
    try:
        id_list = [int(x.strip()) for x in ids.split(",") if x.strip()]
    except ValueError:
        return {"error": "ids must be comma-separated integers"}

    if not id_list:
        return {"error": "No IDs provided"}

    if len(id_list) > 200:
        return {"error": "Maximum 200 IDs per request"}

    # Find entries
    entries = db.query(KnowledgeEntry).filter(KnowledgeEntry.id.in_(id_list)).all()
    found_ids = {e.id for e in entries}
    not_found = [i for i in id_list if i not in found_ids]

    preview = [
        {"id": e.id, "title": (e.title or "")[:80], "category": e.category}
        for e in entries
    ]

    if dry_run:
        return {
            "dry_run": True,
            "found": len(entries),
            "not_found": len(not_found),
            "entries": preview,
        }

    # Delete
    if found_ids:
        db.query(KnowledgeEntry).filter(KnowledgeEntry.id.in_(found_ids)).delete(synchronize_session=False)
        db.commit()

    remaining = db.query(KnowledgeEntry).count()

    return {
        "dry_run": False,
        "deleted": len(found_ids),
        "not_found": len(not_found),
        "remaining_entries": remaining,
        "deleted_entries": preview,
    }
