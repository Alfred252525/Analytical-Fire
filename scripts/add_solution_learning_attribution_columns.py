#!/usr/bin/env python3
"""
Database Migration: Add learning attribution columns to problem_solutions

Adds:
- knowledge_ids_used (JSON)
- risk_pitfalls_used (JSON)
- anti_pattern_ids_used (JSON)

This enables impact tracking: did consulting learnings correlate with better outcomes?
"""

import os
import sys
from sqlalchemy import text

# Add backend to path
backend_path = os.path.join(os.path.dirname(__file__), '..', 'backend')
sys.path.insert(0, backend_path)

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
    print("Starting learning attribution migration...")

    with engine.connect() as conn:
        table = "problem_solutions"

        columns = [
            ("knowledge_ids_used", "JSON"),
            ("risk_pitfalls_used", "JSON"),
            ("anti_pattern_ids_used", "JSON"),
        ]

        for col, coltype in columns:
            if _column_exists(conn, table, col):
                print(f"✅ Column already exists: {col}")
                continue

            print(f"Adding column {col} to {table}...")
            conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {col} {coltype}"))
            conn.commit()

        print("✅ Migration complete.")


if __name__ == "__main__":
    migrate()

