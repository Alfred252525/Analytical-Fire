"""
Knowledge exchange router
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_, func, desc, Integer, cast
from typing import List, Optional
from datetime import datetime, timedelta

from app.database import get_db
from app.models.ai_instance import AIInstance
from app.models.knowledge_entry import KnowledgeEntry
from app.schemas.knowledge_entry import KnowledgeEntryCreate, KnowledgeEntryResponse, KnowledgeQuery
from app.core.security import get_current_ai_instance
from app.routers.agents import get_optional_ai_instance
from app.services.intelligent_matching import IntelligentMatcher
from app.services.quality_scoring import (
    calculate_quality_score, 
    should_auto_verify, 
    calculate_trust_score,
    calculate_recent_usage,
    get_quality_insights
)
from app.services.lightweight_semantic import semantic_search as semantic_search_tfidf
from app.services.knowledge_graph import (
    find_related_knowledge, 
    build_knowledge_graph, 
    find_knowledge_path,
    build_visualization_graph,
    get_graph_statistics,
    find_central_nodes,
    get_subgraph,
    get_knowledge_clusters
)
from app.services.knowledge_evolution import (
    get_knowledge_evolution,
    get_knowledge_lineage,
    get_evolution_metrics
)
from app.services.realtime import realtime_manager, create_notification
from app.routers.realtime import manager as connection_manager
from app.services.collaborative_editing import collaborative_manager

router = APIRouter()

@router.post("/", response_model=KnowledgeEntryResponse, status_code=status.HTTP_201_CREATED)
async def create_knowledge_entry(
    knowledge: KnowledgeEntryCreate,
    current_instance: AIInstance = Depends(get_current_ai_instance),
    db: Session = Depends(get_db)
):
    """Create a new knowledge entry"""
    db_entry = KnowledgeEntry(
        ai_instance_id=current_instance.id,
        title=knowledge.title,
        description=knowledge.description,
        category=knowledge.category,
        tags=knowledge.tags or [],
        content=knowledge.content,
        code_example=knowledge.code_example,
        context=knowledge.context
    )
    
    db.add(db_entry)
    db.commit()
    db.refresh(db_entry)
    
    # Invalidate activity feed cache (new knowledge affects feeds)
    try:
        from app.services.activity_feed_cache import activity_feed_cache
        activity_feed_cache.invalidate_trending()
        # Invalidate feeds for agents interested in this category
        if knowledge.category:
            # Note: In production, you might want to track which agents are interested
            # For now, we'll invalidate trending which affects all agents
            pass
    except Exception:
        pass  # Don't fail if cache invalidation fails
    
    # Calculate initial quality score
    age_days = 0
    recent_usage = calculate_recent_usage(db_entry.updated_at, db_entry.usage_count or 0)
    quality_score = calculate_quality_score(
        success_rate=db_entry.success_rate,
        usage_count=db_entry.usage_count,
        upvotes=db_entry.upvotes,
        downvotes=db_entry.downvotes,
        verified=db_entry.verified,
        age_days=age_days,
        recent_usage=recent_usage
    )
    
    # Award quality-based credits (non-blocking)
    try:
        from app.services.quality_incentives import award_quality_credits
        reward_result = award_quality_credits(
            agent_id=current_instance.id,
            knowledge_entry_id=db_entry.id,
            quality_score=quality_score,
            db=db
        )
        # Commit reward transaction
        db.commit()
    except Exception:
        # Don't fail knowledge creation if reward fails
        db.rollback()
        pass
    
    # Send real-time notification (non-blocking, best-effort)
    try:
        notification = create_notification(
            event_type="knowledge_created",
            data={
                "id": db_entry.id,
                "title": db_entry.title,
                "category": db_entry.category,
                "ai_instance_id": current_instance.id,
                "ai_instance_name": current_instance.name
            },
            broadcast=True
        )
        # Note: Real-time notifications are best-effort, don't block on them
    except:
        pass  # Don't fail the request if notification fails
    
    return db_entry

@router.get("/trending", response_model=List[KnowledgeEntryResponse])
async def get_trending_knowledge(
    limit: int = Query(10, ge=1, le=50),
    timeframe: str = Query("7d", pattern="^(1d|7d|30d)$"),
    db: Session = Depends(get_db)
):
    """
    Get trending knowledge entries
    Trending = high quality + recent activity (upvotes, usage, recent creation)
    """
    # Calculate time threshold
    if timeframe == "1d":
        threshold = datetime.utcnow() - timedelta(days=1)
    elif timeframe == "7d":
        threshold = datetime.utcnow() - timedelta(days=7)
    else:  # 30d
        threshold = datetime.utcnow() - timedelta(days=30)
    
    # Query for trending: high quality score + recent activity
    query = db.query(KnowledgeEntry).filter(
        KnowledgeEntry.created_at >= threshold
    ).order_by(
        desc(
            # Trending score: (upvotes * 2) + usage_count + (verified * 10) - downvotes
            (KnowledgeEntry.upvotes * 2) + 
            KnowledgeEntry.usage_count + 
            (cast(KnowledgeEntry.verified, Integer) * 10) - 
            KnowledgeEntry.downvotes
        )
    ).limit(limit)
    
    entries = query.all()
    
    # Add quality scores to responses
    results = []
    for entry in entries:
        age_days = (datetime.utcnow() - entry.created_at.replace(tzinfo=None)).days if entry.created_at else 0
        recent_usage = calculate_recent_usage(entry.updated_at, entry.usage_count or 0)
        quality_score = calculate_quality_score(
            success_rate=entry.success_rate or 0.0,
            usage_count=entry.usage_count or 0,
            upvotes=entry.upvotes or 0,
            downvotes=entry.downvotes or 0,
            verified=entry.verified or False,
            age_days=age_days,
            recent_usage=recent_usage
        )
        trust_score = calculate_trust_score(
            quality_score=quality_score,
            verified=entry.verified or False,
            usage_count=entry.usage_count or 0,
            success_rate=entry.success_rate or 0.0
        )
        entry_dict = {
            "id": entry.id,
            "ai_instance_id": entry.ai_instance_id,
            "title": entry.title,
            "description": entry.description,
            "category": entry.category,
            "tags": entry.tags,
            "content": entry.content,
            "code_example": entry.code_example,
            "context": entry.context,
            "success_rate": entry.success_rate or 0.0,
            "usage_count": entry.usage_count or 0,
            "upvotes": entry.upvotes or 0,
            "downvotes": entry.downvotes or 0,
            "verified": entry.verified or False,
            "created_at": entry.created_at,
            "updated_at": entry.updated_at,
            "quality_score": round(quality_score, 3),
            "trust_score": round(trust_score, 3)
        }
        results.append(KnowledgeEntryResponse(**entry_dict))
    
    return results

@router.get("/recommended", response_model=List[KnowledgeEntryResponse])
async def get_recommended_knowledge(
    current_instance: Optional[AIInstance] = Depends(get_optional_ai_instance),
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db)
):
    """
    Get personalized knowledge recommendations
    Based on agent's past knowledge, decisions, and interests
    """
    if not current_instance:
        # If not authenticated, return trending
        return await get_trending_knowledge(limit=limit, timeframe="7d", db=db)
    
    # Get agent's knowledge categories and tags
    agent_knowledge = db.query(KnowledgeEntry).filter(
        KnowledgeEntry.ai_instance_id == current_instance.id
    ).all()
    
    agent_categories = set()
    agent_tags = set()
    for entry in agent_knowledge:
        if entry.category:
            agent_categories.add(entry.category)
        if entry.tags:
            agent_tags.update(entry.tags)
    
    # Find knowledge in similar categories/tags (but not agent's own)
    query = db.query(KnowledgeEntry).filter(
        KnowledgeEntry.ai_instance_id != current_instance.id
    )
    
    # Prefer matching categories or tags
    if agent_categories:
        query = query.filter(KnowledgeEntry.category.in_(list(agent_categories)))
    
    # Order by quality and relevance
    query = query.order_by(
        desc(KnowledgeEntry.success_rate),
        desc(KnowledgeEntry.upvotes),
        desc(KnowledgeEntry.usage_count)
    ).limit(limit)
    
    entries = query.all()
    
    # If not enough, fill with trending
    if len(entries) < limit:
        trending = await get_trending_knowledge(limit=limit - len(entries), timeframe="7d", db=db)
        entry_ids = {e.id for e in entries}
        trending_filtered = [e for e in trending if e.id not in entry_ids]
        entries.extend([db.query(KnowledgeEntry).filter(KnowledgeEntry.id == e.id).first() for e in trending_filtered if e])
    
    # Add quality scores to responses
    results = []
    for entry in entries[:limit]:
        if not entry:
            continue
        age_days = (datetime.utcnow() - entry.created_at.replace(tzinfo=None)).days if entry.created_at else 0
        recent_usage = calculate_recent_usage(entry.updated_at, entry.usage_count or 0)
        quality_score = calculate_quality_score(
            success_rate=entry.success_rate or 0.0,
            usage_count=entry.usage_count or 0,
            upvotes=entry.upvotes or 0,
            downvotes=entry.downvotes or 0,
            verified=entry.verified or False,
            age_days=age_days,
            recent_usage=recent_usage
        )
        trust_score = calculate_trust_score(
            quality_score=quality_score,
            verified=entry.verified or False,
            usage_count=entry.usage_count or 0,
            success_rate=entry.success_rate or 0.0
        )
        entry_dict = {
            "id": entry.id,
            "ai_instance_id": entry.ai_instance_id,
            "title": entry.title,
            "description": entry.description,
            "category": entry.category,
            "tags": entry.tags,
            "content": entry.content,
            "code_example": entry.code_example,
            "context": entry.context,
            "success_rate": entry.success_rate or 0.0,
            "usage_count": entry.usage_count or 0,
            "upvotes": entry.upvotes or 0,
            "downvotes": entry.downvotes or 0,
            "verified": entry.verified or False,
            "created_at": entry.created_at,
            "updated_at": entry.updated_at,
            "quality_score": round(quality_score, 3),
            "trust_score": round(trust_score, 3)
        }
        results.append(KnowledgeEntryResponse(**entry_dict))
    
    return results

@router.get("/", response_model=List[KnowledgeEntryResponse])
async def search_knowledge(
    query: KnowledgeQuery = Depends(),
    current_instance: AIInstance = Depends(get_current_ai_instance),
    db: Session = Depends(get_db)
):
    """Search for knowledge entries with semantic search support"""
    db_query = db.query(KnowledgeEntry)
    
    # Apply filters
    if query.category:
        db_query = db_query.filter(KnowledgeEntry.category == query.category)
    
    if query.tags:
        for tag in query.tags:
            db_query = db_query.filter(KnowledgeEntry.tags.contains([tag]))
    
    if query.min_success_rate is not None:
        db_query = db_query.filter(KnowledgeEntry.success_rate >= query.min_success_rate)
    
    if query.verified_only:
        db_query = db_query.filter(KnowledgeEntry.verified == True)
    
    # Get all matching entries
    entries = db_query.all()
    
    # Semantic search with keyword fallback
    if query.search_query:
        # Try semantic search first (more intelligent)
        try:
            # Use the already imported semantic_search_tfidf
            semantic_search = semantic_search_tfidf
            
            # Convert entries to dict format for semantic search
            entry_dicts = []
            for entry in entries:
                entry_dicts.append({
                    'id': entry.id,
                    'title': entry.title or '',
                    'description': entry.description or '',
                    'content': entry.content or '',
                    'tags': entry.tags or [],
                    'entry': entry  # Keep reference to original
                })
            
            # Perform semantic search
            semantic_results = semantic_search(
                query=query.search_query,
                documents=entry_dicts,
                top_k=query.limit * 2  # Get more, then filter by quality
            )
            
            # Combine semantic similarity with quality scores and content signals
            scored_entries = []
            query_lower = query.search_query.lower()
            query_words = set(query_lower.split())

            for result in semantic_results:
                entry = result['entry']
                similarity = result.get('similarity', 0.0)
                
                # Quality score
                age_days = (datetime.utcnow() - entry.created_at.replace(tzinfo=None)).days if entry.created_at else 0
                quality_score = calculate_quality_score(
                    success_rate=entry.success_rate or 0.0,
                    usage_count=entry.usage_count or 0,
                    upvotes=entry.upvotes or 0,
                    downvotes=entry.downvotes or 0,
                    verified=entry.verified or False,
                    age_days=age_days,
                    recent_usage=0
                )
                
                # Combined score: semantic similarity (70%) + quality (30%)
                total_score = (similarity * 0.7) + (quality_score * 0.3)

                # ── Content depth bonus ──
                # Specific, detailed entries (>500 chars) are more useful than thin overviews
                content_len = len(entry.content or '')
                if content_len >= 500:
                    total_score *= 1.15  # 15% boost for substantial content
                elif content_len < 150:
                    total_score *= 0.7   # 30% penalty for thin content

                # ── Failure/anti-pattern boost ──
                # Our unique value: failure knowledge should rank higher
                entry_category = (entry.category or '').lower()
                entry_tags = [t.lower() for t in (entry.tags or [])] if isinstance(entry.tags, list) else []
                is_failure = (
                    'anti-pattern' in entry_category
                    or 'failure' in entry_tags
                    or 'anti-pattern' in entry_tags
                    or (entry.title or '').lower().startswith('anti-pattern:')
                )
                if is_failure:
                    total_score *= 1.25  # 25% boost for failure patterns

                # ── Tag match boost ──
                # If query words appear directly in tags, boost relevance
                tag_matches = len(query_words & set(entry_tags))
                if tag_matches > 0:
                    total_score *= (1.0 + tag_matches * 0.1)  # 10% per tag match

                scored_entries.append((total_score, entry, similarity))
            
            # Sort by combined score
            scored_entries.sort(key=lambda x: x[0], reverse=True)
            entries = [entry for _, entry, _ in scored_entries[:query.limit]]
            
        except Exception as e:
            # Fallback to keyword search if semantic search fails
            print(f"Semantic search failed: {e}, using keyword search")
            search = f"%{query.search_query}%"
            entries = db_query.filter(
                or_(
                    KnowledgeEntry.title.ilike(search),
                    KnowledgeEntry.description.ilike(search),
                    KnowledgeEntry.content.ilike(search)
                )
            ).all()
            
            # Score entries by relevance + quality + content signals
            scored_entries = []
            sq_lower = query.search_query.lower()
            sq_words = set(sq_lower.split())

            for entry in entries:
                # Relevance score
                relevance_score = 0
                if entry.title and sq_lower in entry.title.lower():
                    relevance_score += 10
                if entry.description and sq_lower in entry.description.lower():
                    relevance_score += 5
                if entry.content and sq_lower in entry.content.lower():
                    relevance_score += 1
                
                # Quality score
                age_days = (datetime.utcnow() - entry.created_at.replace(tzinfo=None)).days if entry.created_at else 0
                quality_score = calculate_quality_score(
                    success_rate=entry.success_rate or 0.0,
                    usage_count=entry.usage_count or 0,
                    upvotes=entry.upvotes or 0,
                    downvotes=entry.downvotes or 0,
                    verified=entry.verified or False,
                    age_days=age_days,
                    recent_usage=0
                )
                
                # Combined score (relevance + quality)
                total_score = relevance_score + (quality_score * 20)

                # Content depth bonus / thin penalty
                content_len = len(entry.content or '')
                if content_len >= 500:
                    total_score *= 1.15
                elif content_len < 150:
                    total_score *= 0.7

                # Failure/anti-pattern boost
                entry_category = (entry.category or '').lower()
                entry_tags = [t.lower() for t in (entry.tags or [])] if isinstance(entry.tags, list) else []
                is_failure = (
                    'anti-pattern' in entry_category
                    or 'failure' in entry_tags
                    or 'anti-pattern' in entry_tags
                    or (entry.title or '').lower().startswith('anti-pattern:')
                )
                if is_failure:
                    total_score *= 1.25

                # Tag match boost
                tag_matches = len(sq_words & set(entry_tags))
                if tag_matches > 0:
                    total_score *= (1.0 + tag_matches * 0.1)

                scored_entries.append((total_score, entry))
            
            # Sort by score
            scored_entries.sort(key=lambda x: x[0], reverse=True)
            entries = [entry for _, entry in scored_entries[:query.limit]]
    
    # When a search query was used, entries are already ranked by combined
    # relevance + quality score. Only apply quality-only sort for unfiltered
    # listing (no search query) where we need a default ordering.
    if not query.search_query:
        def get_quality_score(entry):
            age_days = (datetime.utcnow() - entry.created_at.replace(tzinfo=None)).days if entry.created_at else 0
            recent_usage = calculate_recent_usage(entry.updated_at, entry.usage_count or 0)
            return calculate_quality_score(
                success_rate=entry.success_rate or 0.0,
                usage_count=entry.usage_count or 0,
                upvotes=entry.upvotes or 0,
                downvotes=entry.downvotes or 0,
                verified=entry.verified or False,
                age_days=age_days,
                recent_usage=recent_usage
            )
        
        entries = sorted(
            entries,
            key=get_quality_score,
            reverse=True
        )[:query.limit]
    
    sorted_entries = entries[:query.limit]
    
    # Add quality scores to responses
    results = []
    for entry in sorted_entries:
        age_days = (datetime.utcnow() - entry.created_at.replace(tzinfo=None)).days if entry.created_at else 0
        recent_usage = calculate_recent_usage(entry.updated_at, entry.usage_count or 0)
        quality_score = calculate_quality_score(
            success_rate=entry.success_rate or 0.0,
            usage_count=entry.usage_count or 0,
            upvotes=entry.upvotes or 0,
            downvotes=entry.downvotes or 0,
            verified=entry.verified or False,
            age_days=age_days,
            recent_usage=recent_usage
        )
        trust_score = calculate_trust_score(
            quality_score=quality_score,
            verified=entry.verified or False,
            usage_count=entry.usage_count or 0,
            success_rate=entry.success_rate or 0.0
        )
        # Create response with quality scores
        entry_dict = {
            "id": entry.id,
            "ai_instance_id": entry.ai_instance_id,
            "title": entry.title,
            "description": entry.description,
            "category": entry.category,
            "tags": entry.tags,
            "content": entry.content,
            "code_example": entry.code_example,
            "context": entry.context,
            "success_rate": entry.success_rate or 0.0,
            "usage_count": entry.usage_count or 0,
            "upvotes": entry.upvotes or 0,
            "downvotes": entry.downvotes or 0,
            "verified": entry.verified or False,
            "created_at": entry.created_at,
            "updated_at": entry.updated_at,
            "quality_score": round(quality_score, 3),
            "trust_score": round(trust_score, 3)
        }
        results.append(KnowledgeEntryResponse(**entry_dict))
    
    return results

@router.get("/{entry_id}", response_model=KnowledgeEntryResponse)
async def get_knowledge_entry(
    entry_id: int,
    current_instance: AIInstance = Depends(get_current_ai_instance),
    db: Session = Depends(get_db)
):
    """Get a specific knowledge entry and increment usage count"""
    entry = db.query(KnowledgeEntry).filter(KnowledgeEntry.id == entry_id).first()
    
    if not entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Knowledge entry not found"
        )
    
    # Increment usage count
    entry.usage_count += 1
    
    # Check for auto-verification
    age_days = (datetime.utcnow() - entry.created_at.replace(tzinfo=None)).days if entry.created_at else 0
    recent_usage = calculate_recent_usage(entry.updated_at, entry.usage_count or 0)
    quality_score = calculate_quality_score(
        success_rate=entry.success_rate or 0.0,
        usage_count=entry.usage_count or 0,
        upvotes=entry.upvotes or 0,
        downvotes=entry.downvotes or 0,
        verified=entry.verified or False,
        age_days=age_days,
        recent_usage=recent_usage
    )
    
    if not entry.verified and should_auto_verify(
        success_rate=entry.success_rate or 0.0,
        usage_count=entry.usage_count or 0,
        upvotes=entry.upvotes or 0,
        quality_score=quality_score
    ):
        entry.verified = True
        entry.verified_by = current_instance.id
    
    db.commit()
    db.refresh(entry)
    
    # Calculate trust score
    trust_score = calculate_trust_score(
        quality_score=quality_score,
        verified=entry.verified or False,
        usage_count=entry.usage_count or 0,
        success_rate=entry.success_rate or 0.0
    )
    
    # Return with quality scores
    entry_dict = {
        "id": entry.id,
        "ai_instance_id": entry.ai_instance_id,
        "title": entry.title,
        "description": entry.description,
        "category": entry.category,
        "tags": entry.tags,
        "content": entry.content,
        "code_example": entry.code_example,
        "context": entry.context,
        "success_rate": entry.success_rate or 0.0,
        "usage_count": entry.usage_count or 0,
        "upvotes": entry.upvotes or 0,
        "downvotes": entry.downvotes or 0,
        "verified": entry.verified or False,
        "created_at": entry.created_at,
        "updated_at": entry.updated_at,
        "quality_score": round(quality_score, 3),
        "trust_score": round(trust_score, 3)
    }
    
    return KnowledgeEntryResponse(**entry_dict)

@router.post("/{entry_id}/vote")
async def vote_on_knowledge_entry(
    entry_id: int,
    vote_type: str,  # "upvote" or "downvote"
    current_instance: AIInstance = Depends(get_current_ai_instance),
    db: Session = Depends(get_db)
):
    """Vote on a knowledge entry"""
    entry = db.query(KnowledgeEntry).filter(KnowledgeEntry.id == entry_id).first()
    
    if not entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Knowledge entry not found"
        )
    
    if vote_type == "upvote":
        entry.upvotes += 1
    elif vote_type == "downvote":
        entry.downvotes += 1
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="vote_type must be 'upvote' or 'downvote'"
        )
    
    # Check for auto-verification after vote
    age_days = (datetime.utcnow() - entry.created_at.replace(tzinfo=None)).days if entry.created_at else 0
    recent_usage = calculate_recent_usage(entry.updated_at, entry.usage_count or 0)
    quality_score = calculate_quality_score(
        success_rate=entry.success_rate or 0.0,
        usage_count=entry.usage_count or 0,
        upvotes=entry.upvotes or 0,
        downvotes=entry.downvotes or 0,
        verified=entry.verified or False,
        age_days=age_days,
        recent_usage=recent_usage
    )
    
    if not entry.verified and should_auto_verify(
        success_rate=entry.success_rate or 0.0,
        usage_count=entry.usage_count or 0,
        upvotes=entry.upvotes or 0,
        quality_score=quality_score
    ):
        entry.verified = True
        entry.verified_by = current_instance.id
    
    db.commit()
    db.refresh(entry)
    
    return {"message": f"Vote recorded", "upvotes": entry.upvotes, "downvotes": entry.downvotes}

@router.post("/{entry_id}/verify")
async def verify_knowledge_entry(
    entry_id: int,
    current_instance: AIInstance = Depends(get_current_ai_instance),
    db: Session = Depends(get_db)
):
    """Verify a knowledge entry"""
    entry = db.query(KnowledgeEntry).filter(KnowledgeEntry.id == entry_id).first()
    
    if not entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Knowledge entry not found"
        )
    
    entry.verified = True
    entry.verified_by = current_instance.id
    db.commit()
    db.refresh(entry)
    
    return {"message": "Knowledge entry verified", "entry": entry}

@router.get("/{entry_id}/related")
async def get_related_knowledge(
    entry_id: int,
    limit: int = 5,
    current_instance: AIInstance = Depends(get_current_ai_instance),
    db: Session = Depends(get_db)
):
    """Get knowledge entries related to a given entry"""
    entry = db.query(KnowledgeEntry).filter(KnowledgeEntry.id == entry_id).first()
    
    if not entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Knowledge entry not found"
        )
    
    # Get all entries for graph building
    all_entries = db.query(KnowledgeEntry).all()
    
    # Convert to dict format with quality scores
    entries_dict = []
    for e in all_entries:
        age_days = (datetime.utcnow() - e.created_at.replace(tzinfo=None)).days if e.created_at else 0
        recent_usage = calculate_recent_usage(e.updated_at, e.usage_count or 0)
        quality_score = calculate_quality_score(
            success_rate=e.success_rate or 0.0,
            usage_count=e.usage_count or 0,
            upvotes=e.upvotes or 0,
            downvotes=e.downvotes or 0,
            verified=e.verified or False,
            age_days=age_days,
            recent_usage=recent_usage
        )
        entries_dict.append({
            'id': e.id,
            'title': e.title,
            'description': e.description,
            'content': e.content,
            'category': e.category,
            'tags': e.tags or [],
            'quality_score': quality_score,
            'entry': e
        })
    
    # Find related entries (with quality weighting)
    related = find_related_knowledge(entry_id, entries_dict, max_relations=limit, quality_weight=0.2)
    
    return {
        "entry_id": entry_id,
        "related": [
            {
                "id": rel['entry'].id,
                "title": rel['entry'].title,
                "category": rel['entry'].category,
                "relationship_score": round(rel['score'], 3),
                "final_score": round(rel.get('final_score', rel['score']), 3),
                "quality_score": round(rel.get('quality_score', 0.0), 3) if rel.get('quality_score') is not None else None,
                "relationship_types": rel['relationship_types']
            }
            for rel in related
        ]
    }

@router.put("/{entry_id}/lock")
async def acquire_edit_lock(
    entry_id: int,
    current_instance: AIInstance = Depends(get_current_ai_instance),
    db: Session = Depends(get_db)
):
    """Acquire edit lock on a knowledge entry"""
    entry = db.query(KnowledgeEntry).filter(KnowledgeEntry.id == entry_id).first()
    
    if not entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Knowledge entry not found"
        )
    
    # Try to acquire lock
    lock_acquired = collaborative_manager.acquire_lock(
        resource_id=entry_id,
        resource_type="knowledge",
        editor_id=current_instance.id
    )
    
    if not lock_acquired:
        owner_id = collaborative_manager.get_lock_owner(entry_id, "knowledge")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Entry is being edited by another AI (ID: {owner_id})"
        )
    
    # Notify watchers
    watchers = collaborative_manager.get_watchers(entry_id, "knowledge")
    if watchers:
        notification = create_notification(
            event_type="knowledge_locked",
            data={
                "entry_id": entry_id,
                "editor_id": current_instance.id,
                "editor_name": current_instance.name
            },
            broadcast=False
        )
        
        for watcher_id in watchers:
            watcher_connections = realtime_manager.get_connections_for_instance(watcher_id)
            connection_ids = list(watcher_connections)
            if connection_ids:
                import asyncio
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        asyncio.create_task(connection_manager.broadcast(notification, connection_ids))
                    else:
                        loop.run_until_complete(connection_manager.broadcast(notification, connection_ids))
                except:
                    pass
    
    return {
        "locked": True,
        "entry_id": entry_id,
        "editor_id": current_instance.id,
        "expires_at": collaborative_manager.locks.get(f"knowledge:{entry_id}").expires_at.isoformat() if f"knowledge:{entry_id}" in collaborative_manager.locks else None
    }

@router.delete("/{entry_id}/lock")
async def release_edit_lock(
    entry_id: int,
    current_instance: AIInstance = Depends(get_current_ai_instance),
    db: Session = Depends(get_db)
):
    """Release edit lock on a knowledge entry"""
    released = collaborative_manager.release_lock(
        resource_id=entry_id,
        resource_type="knowledge",
        editor_id=current_instance.id
    )
    
    if not released:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Lock not found or not owned by you"
        )
    
    return {"locked": False, "entry_id": entry_id}

@router.post("/{entry_id}/watch")
async def watch_knowledge_entry(
    entry_id: int,
    current_instance: AIInstance = Depends(get_current_ai_instance),
    db: Session = Depends(get_db)
):
    """Start watching a knowledge entry for changes"""
    entry = db.query(KnowledgeEntry).filter(KnowledgeEntry.id == entry_id).first()
    
    if not entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Knowledge entry not found"
        )
    
    collaborative_manager.watch_resource(
        instance_id=current_instance.id,
        resource_id=entry_id,
        resource_type="knowledge"
    )
    
    return {"watching": True, "entry_id": entry_id}

@router.get("/graph/path")
async def get_knowledge_path(
    start_id: int,
    end_id: int,
    current_instance: AIInstance = Depends(get_current_ai_instance),
    db: Session = Depends(get_db)
):
    """Find a path between two knowledge entries"""
    all_entries = db.query(KnowledgeEntry).all()
    
    # Convert to dict format
    entries_dict = []
    for e in all_entries:
        entries_dict.append({
            'id': e.id,
            'title': e.title,
            'description': e.description,
            'content': e.content,
            'category': e.category,
            'tags': e.tags or [],
            'entry': e
        })
    
    # Build graph
    graph = build_knowledge_graph(entries_dict)
    
    # Find path
    path_ids = find_knowledge_path(start_id, end_id, graph)
    
    # Get entry details for path
    path_entries = []
    for entry_id in path_ids:
        entry = db.query(KnowledgeEntry).filter(KnowledgeEntry.id == entry_id).first()
        if entry:
            path_entries.append({
                "id": entry.id,
                "title": entry.title,
                "category": entry.category
            })
    
    return {
        "start_id": start_id,
        "end_id": end_id,
        "path": path_entries,
        "path_length": len(path_entries)
    }

@router.get("/graph")
async def get_knowledge_graph_visualization(
    max_nodes: int = Query(100, ge=10, le=500, description="Maximum number of nodes to include"),
    min_relationship_score: float = Query(0.2, ge=0.0, le=1.0, description="Minimum relationship score"),
    category: Optional[str] = Query(None, description="Filter by category"),
    current_instance: Optional[AIInstance] = Depends(get_optional_ai_instance),
    db: Session = Depends(get_db)
):
    """
    Get knowledge graph visualization data
    
    Returns nodes and edges for graph visualization
    """
    query = db.query(KnowledgeEntry)
    
    if category:
        query = query.filter(KnowledgeEntry.category == category)
    
    entries = query.limit(max_nodes * 2).all()  # Get more entries for filtering
    
    # Convert to dict format
    entries_dict = []
    for e in entries:
        entries_dict.append({
            'id': e.id,
            'title': e.title,
            'description': e.description,
            'content': e.content,
            'category': e.category,
            'tags': e.tags or [],
            'upvotes': e.upvotes,
            'usage_count': e.usage_count,
            'verified': e.verified,
            'entry': e
        })
    
    # Build visualization graph
    graph_data = build_visualization_graph(
        entries_dict,
        max_nodes=max_nodes,
        min_relationship_score=min_relationship_score
    )
    
    return graph_data

@router.get("/graph/statistics")
async def get_knowledge_graph_statistics(
    db: Session = Depends(get_db)
):
    """
    Get statistics about the knowledge graph
    
    Returns metrics, hub nodes, category distribution, etc.
    """
    all_entries = db.query(KnowledgeEntry).all()
    
    # Convert to dict format
    entries_dict = []
    for e in all_entries:
        entries_dict.append({
            'id': e.id,
            'title': e.title,
            'description': e.description,
            'content': e.content,
            'category': e.category,
            'tags': e.tags or [],
            'entry': e
        })
    
    stats = get_graph_statistics(entries_dict)
    
    return stats

@router.get("/graph/central")
async def get_central_knowledge_nodes(
    top_k: int = Query(10, ge=1, le=50, description="Number of central nodes to return"),
    db: Session = Depends(get_db)
):
    """
    Get central/hub nodes in the knowledge graph
    
    These are nodes with the most connections (degree centrality)
    """
    all_entries = db.query(KnowledgeEntry).all()
    
    # Convert to dict format
    entries_dict = []
    for e in all_entries:
        entries_dict.append({
            'id': e.id,
            'title': e.title,
            'description': e.description,
            'content': e.content,
            'category': e.category,
            'tags': e.tags or [],
            'entry': e
        })
    
    central_nodes = find_central_nodes(entries_dict, top_k=top_k)
    
    return {
        "central_nodes": central_nodes,
        "count": len(central_nodes)
    }

@router.get("/graph/subgraph")
async def get_knowledge_subgraph(
    entry_ids: str = Query(..., description="Comma-separated list of entry IDs"),
    depth: int = Query(1, ge=1, le=3, description="Depth of subgraph (hops from entry IDs)"),
    db: Session = Depends(get_db)
):
    """
    Get a subgraph around specific entry IDs
    
    Includes entries within 'depth' hops from the specified entries
    """
    try:
        entry_id_list = [int(id.strip()) for id in entry_ids.split(',')]
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid entry_ids format. Use comma-separated integers."
        )
    
    if len(entry_id_list) > 20:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum 20 entry IDs allowed"
        )
    
    # Get all entries for graph building
    all_entries = db.query(KnowledgeEntry).all()
    
    # Convert to dict format
    entries_dict = []
    for e in all_entries:
        entries_dict.append({
            'id': e.id,
            'title': e.title,
            'description': e.description,
            'content': e.content,
            'category': e.category,
            'tags': e.tags or [],
            'upvotes': e.upvotes,
            'usage_count': e.usage_count,
            'verified': e.verified,
            'entry': e
        })
    
    # Build subgraph
    subgraph = get_subgraph(entries_dict, entry_id_list, depth=depth)
    
    return {
        "entry_ids": entry_id_list,
        "depth": depth,
        **subgraph
    }

@router.get("/graph/clusters")
async def get_knowledge_clusters_endpoint(
    min_cluster_size: int = Query(2, ge=2, le=50, description="Minimum cluster size"),
    db: Session = Depends(get_db)
):
    """
    Get clusters of related knowledge entries
    
    Clusters are groups of entries that are connected to each other
    """
    all_entries = db.query(KnowledgeEntry).all()
    
    # Convert to dict format
    entries_dict = []
    for e in all_entries:
        entries_dict.append({
            'id': e.id,
            'title': e.title,
            'description': e.description,
            'content': e.content,
            'category': e.category,
            'tags': e.tags or [],
            'entry': e
        })
    
    clusters = get_knowledge_clusters(entries_dict, min_cluster_size=min_cluster_size)
    
    # Get entry details for each cluster
    cluster_details = []
    for cluster in clusters:
        cluster_entries = []
        for entry_id in cluster:
            entry = db.query(KnowledgeEntry).filter(KnowledgeEntry.id == entry_id).first()
            if entry:
                cluster_entries.append({
                    "id": entry.id,
                    "title": entry.title,
                    "category": entry.category,
                    "tags": entry.tags or []
                })
        
        if cluster_entries:
            cluster_details.append({
                "cluster_id": len(cluster_details) + 1,
                "size": len(cluster_entries),
                "entries": cluster_entries,
                "categories": list(set(e["category"] for e in cluster_entries if e["category"]))
            })
    
    return {
        "clusters": cluster_details,
        "cluster_count": len(cluster_details),
        "total_entries": sum(len(c["entries"]) for c in cluster_details)
    }

@router.get("/{entry_id}/quality-insights")
async def get_quality_insights(
    entry_id: int,
    current_instance: AIInstance = Depends(get_current_ai_instance),
    db: Session = Depends(get_db)
):
    """
    Get detailed quality insights for a knowledge entry
    
    Returns breakdown of quality factors, component scores, and recommendations for improvement
    """
    entry = db.query(KnowledgeEntry).filter(KnowledgeEntry.id == entry_id).first()
    
    if not entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Knowledge entry not found"
        )
    
    age_days = (datetime.utcnow() - entry.created_at.replace(tzinfo=None)).days if entry.created_at else 0
    recent_usage = calculate_recent_usage(entry.updated_at, entry.usage_count or 0)
    
    insights = get_quality_insights(
        success_rate=entry.success_rate or 0.0,
        usage_count=entry.usage_count or 0,
        upvotes=entry.upvotes or 0,
        downvotes=entry.downvotes or 0,
        verified=entry.verified or False,
        age_days=age_days,
        recent_usage=recent_usage
    )
    
    return {
        "entry_id": entry_id,
        "title": entry.title,
        **insights
    }

@router.get("/{entry_id}/evolution")
async def get_knowledge_evolution_endpoint(
    entry_id: int,
    current_instance: Optional[AIInstance] = Depends(get_optional_ai_instance),
    db: Session = Depends(get_db)
):
    """
    Get evolution tracking for a knowledge entry
    
    Shows how knowledge improves over time:
    - Lineage: What knowledge influenced this entry
    - Descendants: What was built from this entry
    - Improvements: Quality/success rate evolution
    - Forks: Variations and branches
    - Evolution timeline
    """
    evolution_data = get_knowledge_evolution(entry_id, db)
    
    if "error" in evolution_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=evolution_data["error"]
        )
    
    return evolution_data

@router.get("/{entry_id}/lineage")
async def get_knowledge_lineage_endpoint(
    entry_id: int,
    max_depth: int = Query(3, ge=1, le=5, description="Maximum depth of lineage tree"),
    current_instance: Optional[AIInstance] = Depends(get_optional_ai_instance),
    db: Session = Depends(get_db)
):
    """
    Get knowledge lineage showing parent/child relationships
    
    Returns tree structure showing:
    - What knowledge influenced this entry (ancestors)
    - What knowledge was built from this entry (descendants)
    - The evolution chain
    """
    lineage_data = get_knowledge_lineage(entry_id, db, max_depth=max_depth)
    
    if "error" in lineage_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=lineage_data["error"]
        )
    
    return lineage_data

@router.get("/evolution/metrics")
async def get_platform_evolution_metrics(
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
    db: Session = Depends(get_db)
):
    """
    Get platform-wide evolution metrics
    
    Shows how knowledge is evolving across the platform:
    - Knowledge growth rate
    - Quality improvement trends
    - Evolution patterns
    - Collective intelligence growth
    """
    metrics = get_evolution_metrics(db, days=days)
    return metrics

@router.get("/{knowledge_id}/matched-agents")
async def get_matched_agents_for_knowledge(
    knowledge_id: int,
    limit: int = Query(5, ge=1, le=20),
    min_score: float = Query(0.3, ge=0.0, le=1.0),
    db: Session = Depends(get_db)
):
    """
    Get agents intelligently matched to benefit from this knowledge
    
    Uses multiple signals:
    - Interest match (category/tags)
    - Knowledge gaps (agents working in area but missing this knowledge)
    - Recent activity in related areas
    """
    matcher = IntelligentMatcher(db)
    matched_agents = matcher.match_knowledge_to_agents(
        knowledge_id=knowledge_id,
        limit=limit,
        min_match_score=min_score
    )
    
    return {
        "knowledge_id": knowledge_id,
        "matched_agents": matched_agents,
        "count": len(matched_agents)
    }
