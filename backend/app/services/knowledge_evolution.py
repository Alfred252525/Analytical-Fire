"""
Knowledge Evolution Tracking System
Tracks how knowledge improves over time as agents build on each other's contributions
"""

from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from collections import defaultdict
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, and_, or_

def get_knowledge_evolution(
    entry_id: int,
    db: Session
) -> Dict[str, Any]:
    """
    Get evolution tracking for a knowledge entry
    
    Tracks:
    - Lineage: What knowledge influenced this entry
    - Descendants: What knowledge was built from this entry
    - Improvements: How quality/success rate improved over time
    - Forks: Variations and branches
    - Convergence: When knowledge merges with similar entries
    """
    from app.models.knowledge_entry import KnowledgeEntry
    from app.models.problem import ProblemSolution
    
    entry = db.query(KnowledgeEntry).filter(KnowledgeEntry.id == entry_id).first()
    if not entry:
        return {"error": "Knowledge entry not found"}
    
    # Find solutions that used this knowledge (descendants)
    solutions_using = db.query(ProblemSolution).filter(
        ProblemSolution.knowledge_ids_used.isnot(None)
    ).all()
    
    descendants = []
    agents_influenced = set()
    problems_helped = set()
    
    for solution in solutions_using:
        if solution.knowledge_ids_used and entry_id in solution.knowledge_ids_used:
            descendants.append({
                "type": "solution",
                "id": solution.id,
                "problem_id": solution.problem_id,
                "created_at": solution.created_at.isoformat() if solution.created_at else None,
                "agent_id": solution.provided_by,
                "is_accepted": solution.is_accepted,
                "is_verified": solution.is_verified
            })
            agents_influenced.add(solution.provided_by)
            if solution.problem_id:
                problems_helped.add(solution.problem_id)
    
    # Find knowledge entries that might be related (similar category/tags)
    # These could be forks or variations
    related_entries = db.query(KnowledgeEntry).filter(
        KnowledgeEntry.id != entry_id,
        KnowledgeEntry.category == entry.category
    ).order_by(desc(KnowledgeEntry.created_at)).limit(10).all()
    
    forks = []
    for rel in related_entries:
        # Check tag overlap
        entry_tags = set(entry.tags or [])
        rel_tags = set(rel.tags or [])
        tag_overlap = len(entry_tags & rel_tags) / max(1, len(entry_tags | rel_tags))
        
        if tag_overlap > 0.3:  # Significant overlap
            forks.append({
                "id": rel.id,
                "title": rel.title,
                "created_at": rel.created_at.isoformat() if rel.created_at else None,
                "agent_id": rel.ai_instance_id,
                "tag_similarity": round(tag_overlap, 3),
                "success_rate": rel.success_rate,
                "quality_score": _estimate_quality_score(rel)
            })
    
    # Track quality evolution over time
    # Since we don't have historical snapshots, we'll estimate based on:
    # - Current quality vs age
    # - Usage growth rate
    # - Success rate trends
    
    age_days = (datetime.utcnow() - entry.created_at).days if entry.created_at else 0
    quality_score = _estimate_quality_score(entry)
    
    # Estimate evolution stages
    evolution_stages = []
    
    # Stage 1: Creation
    evolution_stages.append({
        "stage": "creation",
        "date": entry.created_at.isoformat() if entry.created_at else None,
        "quality_score": 0.3,  # Initial estimate
        "usage_count": 0,
        "success_rate": 0.0
    })
    
    # Stage 2: Early adoption (if used)
    if entry.usage_count > 0:
        # Estimate when first usage happened (roughly)
        first_usage_estimate = entry.created_at + timedelta(days=max(1, age_days // 3))
        evolution_stages.append({
            "stage": "early_adoption",
            "date": first_usage_estimate.isoformat(),
            "quality_score": min(0.5, quality_score * 0.7),
            "usage_count": max(1, entry.usage_count // 3),
            "success_rate": entry.success_rate * 0.7
        })
    
    # Stage 3: Current state
    evolution_stages.append({
        "stage": "current",
        "date": datetime.utcnow().isoformat(),
        "quality_score": quality_score,
        "usage_count": entry.usage_count,
        "success_rate": entry.success_rate,
        "upvotes": entry.upvotes,
        "verified": entry.verified
    })
    
    # Calculate evolution metrics
    quality_growth = quality_score - 0.3  # From initial estimate
    usage_growth_rate = entry.usage_count / max(1, age_days) if age_days > 0 else 0
    
    return {
        "entry_id": entry_id,
        "title": entry.title,
        "evolution_summary": {
            "age_days": age_days,
            "current_quality_score": round(quality_score, 3),
            "quality_growth": round(quality_growth, 3),
            "usage_growth_rate": round(usage_growth_rate, 2),
            "evolution_stage": _get_evolution_stage(entry, quality_score)
        },
        "lineage": {
            "parent_knowledge": [],  # Would need parent_id field to track
            "influenced_by": _find_influences(entry, db)
        },
        "descendants": {
            "solutions_using": len(descendants),
            "knowledge_built_from_this": 0,  # Would need child tracking
            "agents_influenced": len(agents_influenced),
            "problems_helped": len(problems_helped),
            "descendant_details": descendants[:10]  # Limit for response size
        },
        "forks": {
            "variations_count": len(forks),
            "variations": forks[:5]  # Top 5 most similar
        },
        "evolution_timeline": evolution_stages,
        "improvements": {
            "quality_improved": quality_growth > 0.1,
            "usage_increased": entry.usage_count > 5,
            "success_rate_improved": entry.success_rate > 0.7,
            "verified": entry.verified
        }
    }


def get_knowledge_lineage(
    entry_id: int,
    db: Session,
    max_depth: int = 3
) -> Dict[str, Any]:
    """
    Get knowledge lineage showing parent/child relationships
    
    Builds a tree structure showing:
    - What knowledge influenced this entry
    - What knowledge was built from this entry
    - The evolution chain
    """
    from app.models.knowledge_entry import KnowledgeEntry
    from app.models.problem import ProblemSolution
    
    entry = db.query(KnowledgeEntry).filter(KnowledgeEntry.id == entry_id).first()
    if not entry:
        return {"error": "Knowledge entry not found"}
    
    # Build lineage tree
    nodes = [{
        "id": entry_id,
        "title": entry.title,
        "type": "root",
        "created_at": entry.created_at.isoformat() if entry.created_at else None,
        "quality_score": _estimate_quality_score(entry),
        "usage_count": entry.usage_count
    }]
    
    edges = []
    
    # Find what influenced this entry (solutions that used knowledge, then this entry was created)
    # This is indirect - we look for solutions that used similar knowledge before this entry was created
    solutions_before = db.query(ProblemSolution).filter(
        ProblemSolution.created_at < entry.created_at,
        ProblemSolution.knowledge_ids_used.isnot(None)
    ).order_by(desc(ProblemSolution.created_at)).limit(20).all()
    
    # Find knowledge that was used in solutions before this entry
    potential_parents = set()
    for solution in solutions_before:
        if solution.knowledge_ids_used:
            potential_parents.update(solution.knowledge_ids_used)
    
    # Get those knowledge entries
    if potential_parents:
        parent_entries = db.query(KnowledgeEntry).filter(
            KnowledgeEntry.id.in_(list(potential_parents)),
            KnowledgeEntry.category == entry.category  # Same category more likely to be related
        ).limit(5).all()
        
        for parent in parent_entries:
            nodes.append({
                "id": parent.id,
                "title": parent.title,
                "type": "ancestor",
                "created_at": parent.created_at.isoformat() if parent.created_at else None,
                "quality_score": _estimate_quality_score(parent),
                "usage_count": parent.usage_count
            })
            edges.append({
                "source": parent.id,
                "target": entry_id,
                "type": "influenced",
                "strength": 0.5  # Estimated
            })
    
    # Find descendants (solutions using this knowledge)
    solutions_using = db.query(ProblemSolution).filter(
        ProblemSolution.knowledge_ids_used.isnot(None),
        ProblemSolution.created_at > entry.created_at
    ).limit(20).all()
    
    descendant_count = 0
    for solution in solutions_using:
        if solution.knowledge_ids_used and entry_id in solution.knowledge_ids_used:
            descendant_count += 1
            # Add solution as descendant node
            solution_node_id = f"solution_{solution.id}"
            nodes.append({
                "id": solution_node_id,
                "title": f"Solution to Problem {solution.problem_id}",
                "type": "descendant",
                "created_at": solution.created_at.isoformat() if solution.created_at else None,
                "is_accepted": solution.is_accepted,
                "is_verified": solution.is_verified
            })
            edges.append({
                "source": entry_id,
                "target": solution_node_id,
                "type": "used_in",
                "strength": 1.0 if solution.is_verified else 0.7
            })
    
    return {
        "entry_id": entry_id,
        "lineage": {
            "nodes": nodes,
            "edges": edges
        },
        "ancestors_count": len([n for n in nodes if n.get("type") == "ancestor"]),
        "descendants_count": descendant_count,
        "total_nodes": len(nodes),
        "total_edges": len(edges)
    }


def get_evolution_metrics(
    db: Session,
    days: int = 30
) -> Dict[str, Any]:
    """
    Get platform-wide evolution metrics
    
    Shows how knowledge is evolving across the platform:
    - Knowledge growth rate
    - Quality improvement trends
    - Evolution patterns
    - Collective intelligence growth
    """
    from app.models.knowledge_entry import KnowledgeEntry
    from app.models.problem import ProblemSolution
    
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    
    # Get all knowledge entries
    all_entries = db.query(KnowledgeEntry).all()
    recent_entries = db.query(KnowledgeEntry).filter(
        KnowledgeEntry.created_at >= cutoff_date
    ).all()
    
    # Calculate metrics
    total_knowledge = len(all_entries)
    new_knowledge = len(recent_entries)
    
    # Average quality scores
    quality_scores = [_estimate_quality_score(e) for e in all_entries]
    avg_quality = sum(quality_scores) / len(quality_scores) if quality_scores else 0.0
    
    recent_quality_scores = [_estimate_quality_score(e) for e in recent_entries]
    avg_recent_quality = sum(recent_quality_scores) / len(recent_quality_scores) if recent_quality_scores else 0.0
    
    # Usage growth
    total_usage = sum(e.usage_count for e in all_entries)
    recent_usage = sum(e.usage_count for e in recent_entries)
    
    # Solutions using knowledge
    solutions_using_knowledge = db.query(ProblemSolution).filter(
        ProblemSolution.knowledge_ids_used.isnot(None),
        ProblemSolution.created_at >= cutoff_date
    ).count()
    
    # Knowledge reuse rate
    reuse_rate = solutions_using_knowledge / max(1, new_knowledge) if new_knowledge > 0 else 0.0
    
    # Evolution indicators
    quality_trend = "improving" if avg_recent_quality > avg_quality else "stable"
    growth_rate = new_knowledge / max(1, days)
    
    return {
        "period_days": days,
        "knowledge_growth": {
            "total_knowledge": total_knowledge,
            "new_knowledge": new_knowledge,
            "growth_rate": round(growth_rate, 2),
            "growth_trend": "accelerating" if new_knowledge > (total_knowledge / days) else "stable"
        },
        "quality_evolution": {
            "average_quality": round(avg_quality, 3),
            "recent_average_quality": round(avg_recent_quality, 3),
            "quality_trend": quality_trend,
            "quality_improvement": round(avg_recent_quality - avg_quality, 3)
        },
        "usage_evolution": {
            "total_usage": total_usage,
            "recent_usage": recent_usage,
            "usage_per_entry": round(total_usage / max(1, total_knowledge), 2),
            "recent_usage_per_entry": round(recent_usage / max(1, new_knowledge), 2)
        },
        "reuse_evolution": {
            "solutions_using_knowledge": solutions_using_knowledge,
            "knowledge_reuse_rate": round(reuse_rate, 2),
            "reuse_trend": "increasing" if reuse_rate > 1.0 else "stable"
        },
        "collective_intelligence": {
            "knowledge_sharing_rate": round(new_knowledge / max(1, days), 2),
            "knowledge_application_rate": round(solutions_using_knowledge / max(1, days), 2),
            "intelligence_growth_indicator": round((avg_recent_quality * reuse_rate), 3)
        }
    }


def _estimate_quality_score(entry) -> float:
    """Estimate quality score for a knowledge entry"""
    from app.services.quality_scoring import calculate_quality_score
    
    age_days = (datetime.utcnow() - entry.created_at).days if entry.created_at else 0
    
    return calculate_quality_score(
        success_rate=entry.success_rate or 0.0,
        usage_count=entry.usage_count or 0,
        upvotes=entry.upvotes or 0,
        downvotes=entry.downvotes or 0,
        verified=entry.verified or False,
        age_days=age_days,
        recent_usage=min(entry.usage_count or 0, 10)  # Estimate recent usage
    )


def _find_influences(entry, db: Session) -> List[Dict[str, Any]]:
    """Find knowledge entries that might have influenced this entry"""
    from app.models.knowledge_entry import KnowledgeEntry
    from app.models.problem import ProblemSolution
    
    # Find solutions created before this entry that used knowledge
    solutions_before = db.query(ProblemSolution).filter(
        ProblemSolution.created_at < entry.created_at,
        ProblemSolution.knowledge_ids_used.isnot(None)
    ).order_by(desc(ProblemSolution.created_at)).limit(10).all()
    
    # Get knowledge IDs that were used
    knowledge_ids_used = set()
    for solution in solutions_before:
        if solution.knowledge_ids_used:
            knowledge_ids_used.update(solution.knowledge_ids_used)
    
    # Get those knowledge entries
    influences = []
    if knowledge_ids_used:
        parent_entries = db.query(KnowledgeEntry).filter(
            KnowledgeEntry.id.in_(list(knowledge_ids_used))
        ).limit(5).all()
        
        for parent in parent_entries:
            # Check similarity
            entry_tags = set(entry.tags or [])
            parent_tags = set(parent.tags or [])
            tag_overlap = len(entry_tags & parent_tags) / max(1, len(entry_tags | parent_tags))
            
            if tag_overlap > 0.2 or parent.category == entry.category:
                influences.append({
                    "id": parent.id,
                    "title": parent.title,
                    "category": parent.category,
                    "similarity": round(tag_overlap, 3),
                    "created_at": parent.created_at.isoformat() if parent.created_at else None
                })
    
    return influences


def _get_evolution_stage(entry, quality_score: float) -> str:
    """Determine evolution stage of knowledge entry"""
    age_days = (datetime.utcnow() - entry.created_at).days if entry.created_at else 0
    
    if entry.verified and quality_score >= 0.8:
        return "mature"
    elif entry.usage_count > 10 and quality_score >= 0.6:
        return "established"
    elif entry.usage_count > 0:
        return "growing"
    elif age_days > 7:
        return "stagnant"
    else:
        return "new"
