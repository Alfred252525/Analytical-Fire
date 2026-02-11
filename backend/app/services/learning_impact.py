"""
Learning Impact Service
Quantifies whether using learnings (knowledge/risk/anti-patterns) correlates with better outcomes.
"""

from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.models.problem import ProblemSolution


def get_learning_impact_report(
    db: Session,
    days: int = 30
) -> Dict[str, Any]:
    """
    Simple impact report:
    Compare outcome rates for solutions that used learnings vs did not.
    """
    cutoff = datetime.utcnow() - timedelta(days=days)

    solutions = db.query(ProblemSolution).filter(
        ProblemSolution.created_at >= cutoff
    ).all()

    def used_learning(s: ProblemSolution) -> bool:
        if s.knowledge_ids_used and len(s.knowledge_ids_used) > 0:
            return True
        if s.risk_pitfalls_used and len(s.risk_pitfalls_used) > 0:
            return True
        if s.anti_pattern_ids_used and len(s.anti_pattern_ids_used) > 0:
            return True
        return False

    with_learning = [s for s in solutions if used_learning(s)]
    without_learning = [s for s in solutions if not used_learning(s)]

    def rates(group):
        tested = [s for s in group if s.is_tested]
        passed = [s for s in tested if s.test_result == "passed"]
        verified = [s for s in group if s.is_verified]
        return {
            "solutions": len(group),
            "tested": len(tested),
            "pass_rate": (len(passed) / len(tested)) if tested else None,
            "verified_rate": (len(verified) / len(group)) if group else None
        }

    return {
        "time_window_days": days,
        "total_solutions": len(solutions),
        "with_learning": rates(with_learning),
        "without_learning": rates(without_learning),
        "notes": "Correlation only. Improves as more tested/verified data accumulates."
    }

