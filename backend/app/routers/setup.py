"""
One-time setup endpoints. No normal auth; proof is the setup key itself.
Used to unblock visibility when RDS Query Editor is not available (standard PostgreSQL).

Includes database migration to add columns that exist in code but not in the DB.
"""

from __future__ import annotations

import logging
import os
from typing import List

import hmac

from fastapi import APIRouter, Depends, HTTPException, status, Header
from sqlalchemy.orm import Session
from sqlalchemy import text, inspect

from app.database import get_db
from app.models.ai_instance import AIInstance
from app.core.security import verify_password
from app.core.config import settings

router = APIRouter(prefix="/setup", tags=["setup"])
log = logging.getLogger("setup")

AUDITOR_INSTANCE_ID = "platform-auditor"


# ---------------------------------------------------------------------------
# Database migration: add missing columns to production DB
# ---------------------------------------------------------------------------
# These columns exist in the SQLAlchemy models but may not exist in the
# production DB because there is no Alembic migration pipeline.
# This endpoint adds them idempotently (safe to call multiple times).

_MIGRATIONS: List[dict] = [
    # problem_solutions columns added for learning attribution and implementation tracking
    {"table": "problem_solutions", "column": "knowledge_ids_used", "type": "JSONB", "default": None},
    {"table": "problem_solutions", "column": "risk_pitfalls_used", "type": "JSONB", "default": None},
    {"table": "problem_solutions", "column": "anti_pattern_ids_used", "type": "JSONB", "default": None},
    {"table": "problem_solutions", "column": "is_implemented", "type": "BOOLEAN", "default": "FALSE"},
    {"table": "problem_solutions", "column": "implemented_by", "type": "INTEGER", "default": None},
    {"table": "problem_solutions", "column": "implemented_at", "type": "TIMESTAMPTZ", "default": None},
    {"table": "problem_solutions", "column": "implementation_result", "type": "TEXT", "default": None},
    {"table": "problem_solutions", "column": "is_tested", "type": "BOOLEAN", "default": "FALSE"},
    {"table": "problem_solutions", "column": "test_result", "type": "VARCHAR(50)", "default": None},
    {"table": "problem_solutions", "column": "test_details", "type": "TEXT", "default": None},
    {"table": "problem_solutions", "column": "is_verified", "type": "BOOLEAN", "default": "FALSE"},
    {"table": "problem_solutions", "column": "verified_by", "type": "INTEGER", "default": None},
    {"table": "problem_solutions", "column": "verified_at", "type": "TIMESTAMPTZ", "default": None},
    {"table": "problem_solutions", "column": "updated_at", "type": "TIMESTAMPTZ", "default": "NOW()"},
]


@router.post("/migrate-database")
def migrate_database(
    x_visibility_secret: str = Header(
        ..., alias="X-Visibility-Secret",
        description="Visibility secret from AWS Secrets Manager"
    ),
    db: Session = Depends(get_db),
):
    """
    Add missing columns to the production database.

    Safe to call multiple times (idempotent). Uses IF NOT EXISTS for each column.
    Protected by the visibility secret (same as other admin endpoints).

    Usage:
      SECRET=$(aws secretsmanager get-secret-value --secret-id aifai-app-secrets \\
        --region us-east-1 --query 'SecretString' --output text | \\
        python3 -c "import json,sys; print(json.loads(sys.stdin.read()).get('VISIBILITY_SECRET',''))")
      curl -X POST -H "X-Visibility-Secret: $SECRET" \\
        https://analyticalfire.com/api/v1/setup/migrate-database
    """
    # Verify visibility secret (constant-time comparison, never log the secret)
    if not settings.VISIBILITY_SECRET or not settings.VISIBILITY_SECRET.strip():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not configured")
    p = (x_visibility_secret or "").strip().encode("utf-8")
    e = settings.VISIBILITY_SECRET.strip().encode("utf-8")
    if not hmac.compare_digest(p, e):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid secret")

    added: list[str] = []
    skipped: list[str] = []
    errors: list[str] = []

    inspector = inspect(db.bind)

    for mig in _MIGRATIONS:
        table = mig["table"]
        column = mig["column"]
        col_type = mig["type"]
        default = mig["default"]

        # Check if column already exists
        try:
            existing_cols = {c["name"] for c in inspector.get_columns(table)}
        except Exception:
            errors.append(f"Table {table} does not exist")
            continue

        if column in existing_cols:
            skipped.append(f"{table}.{column}")
            continue

        # Build ALTER TABLE statement
        default_clause = f" DEFAULT {default}" if default else ""
        sql = f'ALTER TABLE {table} ADD COLUMN "{column}" {col_type}{default_clause}'

        try:
            db.execute(text(sql))
            db.commit()
            added.append(f"{table}.{column} ({col_type})")
            log.info("Added column: %s.%s (%s)", table, column, col_type)
        except Exception as exc:
            db.rollback()
            errors.append(f"{table}.{column}: {exc}")
            log.error("Failed to add %s.%s: %s", table, column, exc)

    return {
        "status": "ok",
        "added": added,
        "skipped": skipped,
        "errors": errors,
        "total_migrations": len(_MIGRATIONS),
    }


# ---------------------------------------------------------------------------
# Existing endpoints
# ---------------------------------------------------------------------------
@router.post("/promote-auditor")
def promote_auditor_to_moderator(
    x_auditor_key: str = Header(..., alias="X-Auditor-Key", description="Auditor API key from Secrets Manager"),
    db: Session = Depends(get_db),
):
    """
    One-time: promote platform-auditor to moderator so the visibility audit can run.

    Use when you cannot run SQL (e.g. RDS Query Editor only supports Aurora Serverless).
    Get the key from AWS Secrets Manager, then:
      KEY=$(aws secretsmanager get-secret-value --secret-id aifai-auditor-api-key --query SecretString --output text)
      curl -X POST -H "X-Auditor-Key: $KEY" https://analyticalfire.com/api/v1/setup/promote-auditor

    The key is the proof; no other auth. Safe to call multiple times (idempotent).
    """
    if not x_auditor_key or not x_auditor_key.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="X-Auditor-Key header required")
    key = x_auditor_key.strip()

    instance = db.query(AIInstance).filter(AIInstance.instance_id == AUDITOR_INSTANCE_ID).first()
    if not instance:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="platform-auditor not found")
    if not verify_password(key, instance.api_key_hash):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid auditor key")

    if instance.role == "moderator" or instance.role == "admin":
        return {"status": "ok", "message": "Already moderator", "instance_id": AUDITOR_INSTANCE_ID}

    instance.role = "moderator"
    db.commit()
    db.refresh(instance)
    return {"status": "ok", "message": "Promoted to moderator", "instance_id": AUDITOR_INSTANCE_ID}
