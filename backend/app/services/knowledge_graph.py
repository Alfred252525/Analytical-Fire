"""
Knowledge graph - connects related knowledge entries
Builds relationships between knowledge based on similarity, categories, tags, and usage patterns
"""

from typing import List, Dict, Any, Set, Tuple, Optional
from collections import defaultdict
from datetime import datetime
import json

def find_related_knowledge(
    entry_id: int,
    all_entries: List[Dict[str, Any]],
    max_relations: int = 5,
    quality_weight: float = 0.2
) -> List[Dict[str, Any]]:
    """
    Find knowledge entries related to a given entry
    
    Relationships based on:
    - Category match
    - Tag overlap
    - Content similarity (shared keywords)
    - Usage patterns (entries used together)
    - Quality score (higher quality entries prioritized)
    
    Args:
        entry_id: ID of the entry to find relations for
        all_entries: List of all entries (dict format)
        max_relations: Maximum number of related entries to return
        quality_weight: Weight for quality score (0.0-1.0, default 0.2)
    
    Returns:
        List of related entries with relationship types and scores
    """
    # Find the target entry
    target_entry = None
    for entry in all_entries:
        if entry.get('id') == entry_id:
            target_entry = entry
            break
    
    if not target_entry:
        return []
    
    # Score relationships
    relationships = []
    
    target_category = target_entry.get('category', '')
    target_tags = set(target_entry.get('tags', []) or [])
    target_keywords = extract_keywords_from_entry(target_entry)
    
    for entry in all_entries:
        if entry.get('id') == entry_id:
            continue
        
        score = 0.0
        relationship_types = []
        
        # Category match (strong relationship)
        if entry.get('category') == target_category:
            score += 0.4
            relationship_types.append('category')
        
        # Tag overlap (medium relationship)
        entry_tags = set(entry.get('tags', []) or [])
        tag_overlap = len(target_tags & entry_tags)
        if tag_overlap > 0:
            score += 0.3 * min(1.0, tag_overlap / 3.0)  # Normalize by overlap
            relationship_types.append('tags')
        
        # Keyword similarity (weak relationship)
        entry_keywords = extract_keywords_from_entry(entry)
        keyword_overlap = len(target_keywords & entry_keywords)
        if keyword_overlap > 0:
            score += 0.2 * min(1.0, keyword_overlap / 5.0)
            relationship_types.append('keywords')
        
        # Title similarity (weak relationship)
        if target_entry.get('title') and entry.get('title'):
            title_words = set(target_entry['title'].lower().split())
            entry_title_words = set(entry['title'].lower().split())
            title_overlap = len(title_words & entry_title_words)
            if title_overlap > 0:
                score += 0.1 * min(1.0, title_overlap / 3.0)
                relationship_types.append('title')
        
        # Quality score boost (prioritize high-quality related entries)
        quality_score = entry.get('quality_score')
        if quality_score is not None:
            # Normalize relationship score (0-1) and add quality boost
            relationship_score = min(1.0, score)
            quality_boost = quality_score * quality_weight
            # Combine: relationship score (80%) + quality boost (20%)
            final_score = relationship_score * (1.0 - quality_weight) + quality_boost
        else:
            final_score = score
        
        if score > 0:
            relationships.append({
                'entry': entry,
                'score': score,
                'final_score': final_score,
                'relationship_types': relationship_types,
                'quality_score': quality_score
            })
    
    # Sort by final score (relationship + quality) and return top N
    relationships.sort(key=lambda x: x.get('final_score', x['score']), reverse=True)
    return relationships[:max_relations]

def extract_keywords_from_entry(entry: Dict[str, Any]) -> Set[str]:
    """Extract keywords from an entry"""
    keywords = set()
    
    # Extract from title
    if entry.get('title'):
        keywords.update(entry['title'].lower().split())
    
    # Extract from description
    if entry.get('description'):
        keywords.update(entry['description'].lower().split())
    
    # Extract from tags
    if entry.get('tags'):
        keywords.update([tag.lower() for tag in entry.get('tags', [])])
    
    # Filter out common words
    stop_words = {
        'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
        'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
        'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'should',
        'could', 'may', 'might', 'must', 'can', 'this', 'that', 'these', 'those'
    }
    
    keywords = {k for k in keywords if k not in stop_words and len(k) > 2}
    return keywords

def build_knowledge_graph(entries: List[Dict[str, Any]]) -> Dict[int, List[Dict[str, Any]]]:
    """
    Build a knowledge graph connecting all entries
    
    Returns:
        Dict mapping entry_id -> list of related entries
    """
    graph = {}
    
    for entry in entries:
        entry_id = entry.get('id')
        if entry_id:
            related = find_related_knowledge(entry_id, entries, max_relations=5)
            graph[entry_id] = related
    
    return graph

def find_knowledge_path(
    start_id: int,
    end_id: int,
    graph: Dict[int, List[Dict[str, Any]]],
    max_depth: int = 3
) -> List[int]:
    """
    Find a path between two knowledge entries
    
    Returns:
        List of entry IDs forming the path, or empty list if no path found
    """
    if start_id == end_id:
        return [start_id]
    
    # BFS to find shortest path
    queue = [(start_id, [start_id])]
    visited = {start_id}
    
    while queue and len(queue[0][1]) <= max_depth:
        current_id, path = queue.pop(0)
        
        if current_id not in graph:
            continue
        
        for relation in graph[current_id]:
            related_id = relation['entry'].get('id')
            
            if related_id == end_id:
                return path + [related_id]
            
            if related_id not in visited:
                visited.add(related_id)
                queue.append((related_id, path + [related_id]))
    
    return []  # No path found

def get_knowledge_clusters(
    entries: List[Dict[str, Any]],
    min_cluster_size: int = 2
) -> List[List[int]]:
    """
    Find clusters of related knowledge entries
    
    Returns:
        List of clusters, where each cluster is a list of entry IDs
    """
    graph = build_knowledge_graph(entries)
    
    # Find connected components
    visited = set()
    clusters = []
    
    for entry_id in graph.keys():
        if entry_id in visited:
            continue
        
        # BFS to find all connected entries
        cluster = []
        queue = [entry_id]
        visited.add(entry_id)
        
        while queue:
            current_id = queue.pop(0)
            cluster.append(current_id)
            
            if current_id in graph:
                for relation in graph[current_id]:
                    related_id = relation['entry'].get('id')
                    if related_id not in visited:
                        visited.add(related_id)
                        queue.append(related_id)
        
        if len(cluster) >= min_cluster_size:
            clusters.append(cluster)
    
    return clusters

def build_visualization_graph(
    entries: List[Dict[str, Any]],
    max_nodes: int = 100,
    min_relationship_score: float = 0.2
) -> Dict[str, Any]:
    """
    Build a graph structure optimized for visualization
    
    Returns:
        Dict with nodes and edges for graph visualization
    """
    graph = build_knowledge_graph(entries)
    
    # Build nodes
    nodes = []
    node_set = set()
    
    # Limit nodes for performance
    entry_ids = list(graph.keys())[:max_nodes]
    
    for entry_id in entry_ids:
        entry = next((e for e in entries if e.get('id') == entry_id), None)
        if not entry:
            continue
        
        node_set.add(entry_id)
        nodes.append({
            "id": entry_id,
            "label": entry.get('title', f"Entry {entry_id}"),
            "category": entry.get('category', 'unknown'),
            "tags": entry.get('tags', []),
            "upvotes": entry.get('upvotes', 0) if hasattr(entry.get('entry', {}), 'upvotes') else 0,
            "usage_count": entry.get('usage_count', 0) if hasattr(entry.get('entry', {}), 'usage_count') else 0,
            "verified": entry.get('verified', False) if hasattr(entry.get('entry', {}), 'verified') else False
        })
    
    # Build edges
    edges = []
    edge_set = set()
    
    for entry_id in entry_ids:
        if entry_id not in graph:
            continue
        
        for relation in graph[entry_id]:
            related_id = relation['entry'].get('id')
            score = relation.get('score', 0.0)
            relationship_types = relation.get('relationship_types', [])
            
            # Filter by score
            if score < min_relationship_score:
                continue
            
            # Only include if both nodes are in our set
            if related_id not in node_set:
                continue
            
            # Avoid duplicate edges
            edge_key = tuple(sorted([entry_id, related_id]))
            if edge_key in edge_set:
                continue
            
            edge_set.add(edge_key)
            edges.append({
                "source": entry_id,
                "target": related_id,
                "weight": score,
                "relationship_types": relationship_types,
                "type": relationship_types[0] if relationship_types else "related"
            })
    
    return {
        "nodes": nodes,
        "edges": edges,
        "node_count": len(nodes),
        "edge_count": len(edges)
    }

def get_graph_statistics(
    entries: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Get statistics about the knowledge graph
    
    Returns:
        Dict with graph metrics and insights
    """
    graph = build_knowledge_graph(entries)
    visualization = build_visualization_graph(entries, max_nodes=1000)
    clusters = get_knowledge_clusters(entries, min_cluster_size=2)
    
    # Calculate statistics
    total_nodes = len(entries)
    total_edges = sum(len(relations) for relations in graph.values())
    
    # Calculate average degree (connections per node)
    degrees = [len(relations) for relations in graph.values()]
    avg_degree = sum(degrees) / len(degrees) if degrees else 0.0
    
    # Find most connected nodes (hubs)
    hub_nodes = sorted(
        [(entry_id, len(relations)) for entry_id, relations in graph.items()],
        key=lambda x: x[1],
        reverse=True
    )[:10]
    
    # Category distribution
    category_counts = defaultdict(int)
    for entry in entries:
        category = entry.get('category', 'unknown')
        category_counts[category] += 1
    
    # Tag distribution
    tag_counts = defaultdict(int)
    for entry in entries:
        tags = entry.get('tags', [])
        if tags:
            for tag in tags:
                tag_counts[tag] += 1
    
    top_tags = sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)[:10]
    
    return {
        "total_nodes": total_nodes,
        "total_edges": total_edges,
        "average_degree": round(avg_degree, 2),
        "cluster_count": len(clusters),
        "largest_cluster_size": max([len(c) for c in clusters], default=0),
        "hub_nodes": [
            {
                "id": entry_id,
                "degree": degree,
                "title": next((e.get('title', f"Entry {entry_id}") for e in entries if e.get('id') == entry_id), f"Entry {entry_id}")
            }
            for entry_id, degree in hub_nodes
        ],
        "category_distribution": dict(category_counts),
        "top_tags": [{"tag": tag, "count": count} for tag, count in top_tags],
        "graph_density": round(total_edges / (total_nodes * (total_nodes - 1)) if total_nodes > 1 else 0, 4)
    }

def find_central_nodes(
    entries: List[Dict[str, Any]],
    top_k: int = 10
) -> List[Dict[str, Any]]:
    """
    Find central/hub nodes in the knowledge graph
    
    Uses degree centrality (nodes with most connections)
    
    Returns:
        List of central nodes with their metrics
    """
    graph = build_knowledge_graph(entries)
    
    # Calculate degrees
    node_degrees = []
    for entry_id, relations in graph.items():
        entry = next((e for e in entries if e.get('id') == entry_id), None)
        if entry:
            node_degrees.append({
                "id": entry_id,
                "degree": len(relations),
                "title": entry.get('title', f"Entry {entry_id}"),
                "category": entry.get('category', 'unknown'),
                "connections": [
                    {
                        "id": rel['entry'].get('id'),
                        "title": rel['entry'].get('title', f"Entry {rel['entry'].get('id')}"),
                        "score": rel.get('score', 0.0)
                    }
                    for rel in relations[:5]  # Top 5 connections
                ]
            })
    
    # Sort by degree and return top K
    node_degrees.sort(key=lambda x: x['degree'], reverse=True)
    return node_degrees[:top_k]

def get_subgraph(
    entries: List[Dict[str, Any]],
    entry_ids: List[int],
    depth: int = 1
) -> Dict[str, Any]:
    """
    Get a subgraph around specific entry IDs
    
    Includes entries within 'depth' hops from the specified entries
    
    Returns:
        Visualization graph for the subgraph
    """
    graph = build_knowledge_graph(entries)
    
    # Find all nodes within depth
    subgraph_nodes = set(entry_ids)
    current_level = set(entry_ids)
    
    for _ in range(depth):
        next_level = set()
        for node_id in current_level:
            if node_id in graph:
                for relation in graph[node_id]:
                    related_id = relation['entry'].get('id')
                    if related_id not in subgraph_nodes:
                        subgraph_nodes.add(related_id)
                        next_level.add(related_id)
        current_level = next_level
        if not current_level:
            break
    
    # Filter entries to subgraph nodes
    subgraph_entries = [e for e in entries if e.get('id') in subgraph_nodes]
    
    return build_visualization_graph(subgraph_entries, max_nodes=len(subgraph_nodes))
