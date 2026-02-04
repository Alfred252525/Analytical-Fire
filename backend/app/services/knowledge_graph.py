"""
Knowledge graph - connects related knowledge entries
Builds relationships between knowledge based on similarity, categories, tags, and usage patterns
"""

from typing import List, Dict, Any, Set, Tuple
from collections import defaultdict
import json

def find_related_knowledge(
    entry_id: int,
    all_entries: List[Dict[str, Any]],
    max_relations: int = 5
) -> List[Dict[str, Any]]:
    """
    Find knowledge entries related to a given entry
    
    Relationships based on:
    - Category match
    - Tag overlap
    - Content similarity (shared keywords)
    - Usage patterns (entries used together)
    
    Returns:
        List of related entries with relationship types
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
        
        if score > 0:
            relationships.append({
                'entry': entry,
                'score': score,
                'relationship_types': relationship_types
            })
    
    # Sort by score and return top N
    relationships.sort(key=lambda x: x['score'], reverse=True)
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
