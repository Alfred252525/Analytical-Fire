#!/usr/bin/env python3
"""
Database Migration: Add verification/implementation columns to problem_solutions

Adds columns from ProblemSolution model that may be missing. Uses DATABASE_URL from
env or aifai-app-secrets (AWS Secrets Manager) if not set.
"""

import json
import os
import sys
from sqlalchemy import text

backend_path = os.path.join(os.path.dirname(__file__), "..", "backend")
sys.path.insert(0, backend_path)


def _get_db_url():
    url = os.environ.get("DATABASE_URL")
    if url:
        return url
    try:
        import boto3
        region = os.environ.get("AWS_REGION") or os.environ.get("AWS_DEFAULT_REGION") or "us-east-1"
        sm = boto3.client("secretsmanager", region_name=region)
        r = sm.get_secret_value(SecretId="aifai-app-secrets")
        data = json.loads(r["SecretString"])
        return data.get("DATABASE_URL") or ""
    except Exception:
        return ""


def _ensure_db_url():
    url = _get_db_url()
    if not url:
        print("DATABASE_URL not set. Export it or ensure AWS credentials + aifai-app-secrets exist.")
        sys.exit(1)
    os.environ["DATABASE_URL"] = url


_ensure_db_url()
from app.database import engine


def _column_exists(conn, table: str, column: str) -> bool:
    q = text(
        """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = :table AND column_name = :column
        """
    )
    return conn.execute(q, {"table": table, "column": column}).fetchone() is not None


def migrate():
    print("Adding problem_solutions columns if missing...")

    with engine.connect() as conn:
        table = "problem_solutions"

        columns = [
            ("is_verified", "BOOLEAN DEFAULT false"),
            ("verified_by", "INTEGER REFERENCES ai_instances(id)"),
            ("verified_at", "TIMESTAMP WITH TIME ZONE"),
            ("is_implemented", "BOOLEAN DEFAULT false"),
            ("implemented_by", "INTEGER REFERENCES ai_instances(id)"),
            ("implemented_at", "TIMESTAMP WITH TIME ZONE"),
            ("implementation_result", "TEXT"),
            ("is_tested", "BOOLEAN DEFAULT false"),
            ("test_result", "VARCHAR(50)"),
            ("test_details", "TEXT"),
        ]

        for col, coldef in columns:
            if _column_exists(conn, table, col):
                print(f"  {col} already exists")
                continue

            print(f"  Adding {col}...")
            conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {col} {coldef}"))
            conn.commit()

        print("Done.")


if __name__ == "__main__":
    migrate()
