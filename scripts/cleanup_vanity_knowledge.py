#!/usr/bin/env python3
"""
Clean up vanity knowledge entries that pollute search and knowledge compounding.

Identifies and removes entries that are:
- Extracted from welcome messages
- "Solution Pattern: general" with N/A context/decision
- Platform stats masquerading as knowledge

Does NOT touch:
- Debated solutions (title starts with "Debated Solution:")
- Real bug fixes / anti-patterns (from cursor sessions)
- Any entry with upvotes or citations

Usage:
  python3 scripts/cleanup_vanity_knowledge.py --dry-run   # Preview only
  python3 scripts/cleanup_vanity_knowledge.py              # Actually delete

Requires: DATABASE_URL env var or AWS credentials for aifai-app-secrets.
"""

from __future__ import annotations

import argparse
import json
import os
import sys

try:
    import boto3
except ImportError:
    boto3 = None

try:
    import psycopg2
except ImportError:
    psycopg2 = None


def get_database_url() -> str:
    """Get DATABASE_URL from env or AWS Secrets Manager."""
    url = os.environ.get("DATABASE_URL")
    if url:
        return url
    if boto3:
        try:
            client = boto3.client("secretsmanager", region_name="us-east-1")
            r = client.get_secret_value(SecretId="aifai-app-secrets")
            data = json.loads(r["SecretString"])
            url = data.get("DATABASE_URL")
            if url:
                return url
        except Exception as e:
            print(f"  Secrets Manager failed: {e}", file=sys.stderr)
    print("ERROR: No DATABASE_URL. Set it in env or configure AWS credentials.", file=sys.stderr)
    sys.exit(1)


# Vanity patterns -- entries matching these are noise, not knowledge
VANITY_TITLE_PATTERNS = [
    "Knowledge from Agent Conversation: Welcome to the AI Knowledge Exchange",
    "Knowledge from Conversation: Welcome to the AI Knowledge Exchange",
    "Knowledge from Agent Conversation: Welcome to",
    "Knowledge from Conversation: Welcome to",
]

VANITY_TITLE_EXACT = [
    "Solution Pattern: general",
]

VANITY_CONTENT_PATTERNS = [
    "Platform has % active agents contributing % knowledge entries",
    "Welcome to the AI Knowledge Exchange Platform%",
    "Platform Welcome Bot%",
]


def main():
    parser = argparse.ArgumentParser(description="Clean vanity knowledge entries")
    parser.add_argument("--dry-run", action="store_true", help="Preview only, don't delete")
    args = parser.parse_args()

    db_url = get_database_url()

    # Try psycopg2 first, fall back to urllib for simple queries
    if psycopg2:
        conn = psycopg2.connect(db_url)
    else:
        # Install psycopg2 on the fly
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install", "psycopg2-binary", "-q"])
        import psycopg2 as pg2
        conn = pg2.connect(db_url)

    cur = conn.cursor()

    # Step 1: Find vanity entries
    print("Scanning for vanity knowledge entries...\n")

    # Build WHERE clause
    conditions = []
    params = []

    for pattern in VANITY_TITLE_PATTERNS:
        conditions.append("title LIKE %s")
        params.append(f"%{pattern}%")

    for exact in VANITY_TITLE_EXACT:
        conditions.append("title = %s")
        params.append(exact)

    where = " OR ".join(conditions)

    # Also check content patterns
    content_conditions = []
    for pattern in VANITY_CONTENT_PATTERNS:
        content_conditions.append("content LIKE %s")
        params.append(pattern)

    if content_conditions:
        where = f"({where}) OR ({' OR '.join(content_conditions)})"

    # Never delete entries with upvotes or that are debated solutions
    safe_clause = (
        " AND upvotes <= 0"
        " AND title NOT LIKE 'Debated Solution:%'"
        " AND title NOT LIKE 'Python:%'"
        " AND title NOT LIKE 'Anti-pattern:%'"
        " AND category != 'debugging'"
    )

    query = f"""
        SELECT id, title, category, created_at, ai_instance_id
        FROM knowledge_entries
        WHERE ({where}){safe_clause}
        ORDER BY id
    """

    cur.execute(query, params)
    vanity_entries = cur.fetchall()

    if not vanity_entries:
        print("No vanity entries found. Knowledge base is clean.")
        conn.close()
        return

    print(f"Found {len(vanity_entries)} vanity entries:\n")
    for row in vanity_entries:
        eid, title, cat, created, instance = row
        print(f"  [{eid}] {(title or '')[:70]}")
        print(f"       category={cat}, created={created}")

    # Step 2: Count real entries for comparison
    cur.execute("SELECT COUNT(*) FROM knowledge_entries")
    total = cur.fetchone()[0]
    print(f"\n  Total entries: {total}")
    print(f"  Vanity entries: {len(vanity_entries)}")
    print(f"  Real entries after cleanup: {total - len(vanity_entries)}")

    if args.dry_run:
        print("\n  [DRY RUN] No changes made. Run without --dry-run to delete.")
        conn.close()
        return

    # Step 3: Delete vanity entries
    vanity_ids = [row[0] for row in vanity_entries]
    placeholders = ",".join(["%s"] * len(vanity_ids))
    delete_query = f"DELETE FROM knowledge_entries WHERE id IN ({placeholders})"

    cur.execute(delete_query, vanity_ids)
    deleted = cur.rowcount
    conn.commit()

    print(f"\n  Deleted {deleted} vanity entries.")

    # Verify
    cur.execute("SELECT COUNT(*) FROM knowledge_entries")
    remaining = cur.fetchone()[0]
    print(f"  Remaining entries: {remaining}")

    conn.close()
    print("\nDone. Knowledge base cleaned.")


if __name__ == "__main__":
    main()
