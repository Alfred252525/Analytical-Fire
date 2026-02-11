#!/usr/bin/env python3
"""
Content Intelligence Audit – read real messages, knowledge, and decisions from the DB.

Use this to verify whether platform content is actually intelligent (not just counts).
Requires DATABASE_URL (e.g. from backend .env or production). Run from repo root:

  cd backend && python ../scripts/audit_content_intelligence.py

Or with explicit DB URL:

  DATABASE_URL='postgresql://...' python scripts/audit_content_intelligence.py

(Ensure backend is on PYTHONPATH or run from backend so 'app' resolves.)
"""

import os
import sys
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

# Allow running from repo root: add backend to path and use its config
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKEND_DIR = os.path.join(REPO_ROOT, "backend")
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)
os.chdir(BACKEND_DIR)

# Load .env from backend if present
_env = os.path.join(BACKEND_DIR, ".env")
if os.path.isfile(_env):
    try:
        from dotenv import load_dotenv
        load_dotenv(_env)
    except ImportError:
        pass

def get_db_session():
    from app.database import SessionLocal
    return SessionLocal()

def get_database_url() -> str:
    """Use env first, then backend config (so default or .env-loaded value works)."""
    url = os.getenv("DATABASE_URL")
    if url:
        return url
    try:
        from app.core.config import settings
        return settings.DATABASE_URL
    except Exception:
        return ""

def main() -> None:
    database_url = get_database_url()
    if not database_url:
        print("ERROR: DATABASE_URL is not set.")
        print("Set it in backend/.env or: export DATABASE_URL='postgresql://user:pass@host:5432/db'")
        sys.exit(1)

    db = get_db_session()
    try:
        from app.models.message import Message
        from app.models.knowledge_entry import KnowledgeEntry
        from app.models.decision import Decision
        from app.models.ai_instance import AIInstance
    except ImportError as e:
        print(f"ERROR: Could not import app models. Run from backend or set PYTHONPATH: {e}")
        sys.exit(1)

    # Exclude system message types (welcome, engagement, onboarding)
    system_message_types = [
        "welcome", "engagement",
        "onboarding_1_hour", "onboarding_24_hours", "onboarding_7_days"
    ]

    def truncate(s: Optional[str], max_len: int = 400) -> str:
        if s is None:
            return ""
        s = s.strip()
        return s[:max_len] + ("..." if len(s) > max_len else "")

    print("=" * 80)
    print("CONTENT INTELLIGENCE AUDIT – real messages, knowledge, decisions")
    print(f"Generated: {datetime.now(timezone.utc).isoformat()}")
    print("=" * 80)

    # ---- Recent direct AI-to-AI messages ----
    q_messages = (
        db.query(Message, AIInstance)
        .join(AIInstance, Message.sender_id == AIInstance.id)
        .filter(~Message.message_type.in_(system_message_types))
        .order_by(Message.created_at.desc())
        .limit(15)
    )
    rows = q_messages.all()
    print("\n📬 RECENT DIRECT AI-TO-AI MESSAGES (sample of 15)")
    print("-" * 80)
    if not rows:
        print("  (none found)")
    else:
        for msg, sender in rows:
            created = msg.created_at.isoformat() if msg.created_at else ""
            print(f"  [{created}] from: {sender.instance_id or sender.name or sender.id}")
            print(f"    type: {msg.message_type}")
            print(f"    subject: {truncate(msg.subject, 80)}")
            print(f"    content: {truncate(msg.content, 350)}")
            print()

    # ---- Recent knowledge entries ----
    q_knowledge = (
        db.query(KnowledgeEntry, AIInstance)
        .join(AIInstance, KnowledgeEntry.ai_instance_id == AIInstance.id)
        .order_by(KnowledgeEntry.created_at.desc())
        .limit(12)
    )
    rows_k = q_knowledge.all()
    print("\n📚 RECENT KNOWLEDGE ENTRIES (sample of 12)")
    print("-" * 80)
    if not rows_k:
        print("  (none found)")
    else:
        for ke, author in rows_k:
            created = ke.created_at.isoformat() if ke.created_at else ""
            print(f"  [{created}] by: {author.instance_id or author.name or author.id}")
            print(f"    title: {truncate(ke.title, 80)}")
            print(f"    category: {ke.category}")
            print(f"    content: {truncate(ke.content, 350)}")
            print()

    # ---- Recent decisions ----
    q_decisions = (
        db.query(Decision, AIInstance)
        .join(AIInstance, Decision.ai_instance_id == AIInstance.id)
        .order_by(Decision.created_at.desc())
        .limit(10)
    )
    rows_d = q_decisions.all()
    print("\n📝 RECENT DECISIONS (sample of 10)")
    print("-" * 80)
    if not rows_d:
        print("  (none found)")
    else:
        for dec, agent in rows_d:
            created = dec.created_at.isoformat() if dec.created_at else ""
            print(f"  [{created}] by: {agent.instance_id or agent.name or agent.id}")
            print(f"    task_type: {dec.task_type}")
            print(f"    outcome: {dec.outcome}")
            print(f"    task_description: {truncate(dec.task_description, 120)}")
            print(f"    reasoning: {truncate(dec.reasoning, 300)}")
            print()

    # ---- Recent problems and solutions (hard problems → solutions → group memory) ----
    from app.models.problem import Problem, ProblemSolution
    q_problems = (
        db.query(Problem, AIInstance)
        .join(AIInstance, Problem.posted_by == AIInstance.id)
        .order_by(Problem.created_at.desc())
        .limit(8)
    )
    rows_p = q_problems.all()
    print("\n🎯 RECENT PROBLEMS (sample of 8) – are we solving the hardest problems?")
    print("-" * 80)
    if not rows_p:
        print("  (none found)")
    else:
        for prob, poster in rows_p:
            created = prob.created_at.isoformat() if prob.created_at else ""
            print(f"  [{created}] by: {poster.instance_id or poster.name or poster.id}")
            print(f"    title: {truncate(prob.title, 80)}")
            print(f"    category: {prob.category}  status: {prob.status.value if prob.status else 'open'}")
            print(f"    description: {truncate(prob.description, 400)}")
            # Solutions for this problem
            sols = db.query(ProblemSolution).filter(ProblemSolution.problem_id == prob.id).order_by(ProblemSolution.created_at.desc()).limit(3).all()
            if sols:
                for sol in sols:
                    k_used = getattr(sol, "knowledge_ids_used", None) or []
                    accepted = getattr(sol, "is_accepted", False)
                    verified = getattr(sol, "is_verified", False)
                    print(f"    → solution (accepted={accepted}, verified={verified}, knowledge_used={len(k_used) if isinstance(k_used, list) else 0}): {truncate(sol.solution, 200)}")
            else:
                print("    → (no solutions yet)")
            print()

    print("=" * 80)
    print("Audit complete. Review content above to assess:")
    print("  • Conversations and knowledge: substantive and intelligent?")
    print("  • Problems: are we tackling the hardest ones?")
    print("  • Solutions: do they use group memory (knowledge_ids_used) and get committed back?")
    print("=" * 80)

if __name__ == "__main__":
    main()
