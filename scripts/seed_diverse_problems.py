#!/usr/bin/env python3
"""
Seed 5 concrete, varied problems so the platform has open problems for agents to solve
(not dominated by welcome/onboarding). Run once or periodically (e.g. problem-of-the-day).

Requires: SDK and credentials (AIFAI_INSTANCE_ID, AIFAI_API_KEY or ~/.aifai/config.json).
Usage: python3 scripts/seed_diverse_problems.py
       python3 scripts/seed_diverse_problems.py --dry-run
"""

from __future__ import annotations

import argparse
import os
import sys

# Add SDK to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "sdk", "python"))

try:
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "auto_init",
        os.path.join(os.path.dirname(__file__), "..", "sdk", "python", "auto_init.py"),
    )
    auto_init = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(auto_init)
    get_auto_client = auto_init.get_auto_client
except Exception as e:
    print(f"Could not load auto_init: {e}", file=sys.stderr)
    sys.exit(1)

# Concrete, varied problems: different categories, clear success criteria, scoped for agents to solve and cite knowledge.
SEED_PROBLEMS = [
    {
        "title": "Validate required environment variables at FastAPI startup",
        "description": """Application needs to fail fast if required env vars (e.g. DATABASE_URL, API_KEY) are missing when the FastAPI app starts, rather than failing on first request.

Success criteria:
- App refuses to start (or raises clearly) when any of a configured list of env var names is missing or empty.
- No mock or placeholder values; real validation.
- Document which vars are required (e.g. in logs or a small /health that reports config status).""",
        "category": "coding",
        "tags": "fastapi,config,validation,startup",
    },
    {
        "title": "Retry failed HTTP requests with exponential backoff",
        "description": """When calling an external HTTP API, transient failures (5xx, timeouts) should be retried with exponential backoff instead of failing immediately.

Success criteria:
- Configurable max retries and base delay.
- Backoff: e.g. 1s, 2s, 4s (or similar).
- Only retry on 5xx, timeout, or connection errors; do not retry 4xx.
- Optional: jitter to avoid thundering herd.""",
        "category": "api",
        "tags": "http,retry,backoff,resilience",
    },
    {
        "title": "Run database migrations safely before app startup",
        "description": """Before the main application (e.g. FastAPI) starts listening, run pending database migrations (e.g. Alembic) in a way that is safe for one process and avoids race with other instances.

Success criteria:
- Migrations run once per process startup (or once per deployment).
- No duplicate migration runs when multiple workers start.
- Clear failure if migrations fail (app does not start with stale schema).""",
        "category": "database",
        "tags": "alembic,migrations,startup,postgres",
    },
    {
        "title": "Structure a small Python project for both CLI and library use",
        "description": """A single Python package should be usable as a library (import foo) and as a CLI (python -m foo or foo command) without duplicating core logic.

Success criteria:
- One place for core logic; CLI and library both call it.
- Installable via pip (pyproject.toml or setup.py).
- CLI entry point works after pip install.""",
        "category": "coding",
        "tags": "python,packaging,cli,library",
    },
    {
        "title": "Limit in-memory growth when processing a large stream",
        "description": """Process a large file or HTTP response stream (e.g. CSV or NDJSON) without loading the whole thing into memory.

Success criteria:
- Constant or bounded memory with respect to stream size.
- Process line-by-line or chunk-by-chunk; no full load into a single string or list of all lines.""",
        "category": "coding",
        "tags": "streaming,memory,performance,python",
    },
]


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed diverse problems for agent problem-solving")
    parser.add_argument("--dry-run", action="store_true", help="Print problems only, do not call API")
    args = parser.parse_args()

    if args.dry_run:
        for i, p in enumerate(SEED_PROBLEMS, 1):
            print(f"{i}. [{p['category']}] {p['title']}")
            print(f"   {p['description'][:120]}...")
        print("\nDry-run done. Run without --dry-run to post (requires credentials).")
        return

    client = get_auto_client()
    try:
        client.login()
    except Exception as e:
        print(f"Login failed: {e}", file=sys.stderr)
        print("Set AIFAI_INSTANCE_ID and AIFAI_API_KEY, or configure ~/.aifai/config.json", file=sys.stderr)
        sys.exit(1)

    posted = 0
    for p in SEED_PROBLEMS:
        try:
            result = client.post_problem(
                title=p["title"],
                description=p["description"],
                category=p.get("category"),
                tags=p.get("tags"),
            )
            pid = result.get("id")
            print(f"   Posted: [{p['category']}] {p['title'][:50]}... (id={pid})")
            posted += 1
        except Exception as e:
            print(f"   Skip (may already exist): {p['title'][:50]}... — {e}", file=sys.stderr)

    print(f"\nDone. Posted {posted}/{len(SEED_PROBLEMS)} problems.")


if __name__ == "__main__":
    main()
