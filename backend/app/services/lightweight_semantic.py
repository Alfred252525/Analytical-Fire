"""
Lightweight semantic search without heavy ML dependencies
Uses TF-IDF and cosine similarity for semantic understanding
"""

from typing import List, Dict, Any
from collections import Counter
import re
import math

def tokenize(text: str) -> List[str]:
    """Tokenize text into words"""
    if not text:
        return []
    # Convert to lowercase and split on non-word characters
    words = re.findall(r'\b\w+\b', text.lower())
    return words

def compute_tf_idf(documents: List[Dict[str, Any]]) -> Dict[str, Dict[str, float]]:
    """
    Compute TF-IDF vectors for documents
    
    Args:
        documents: List of dicts with 'id' and 'text' fields
    
    Returns:
        Dict mapping doc_id -> term -> tf_idf_score
    """
    # Count document frequency (DF) for each term
    doc_frequency = Counter()
    doc_terms = {}
    
    for doc in documents:
        doc_id = doc.get('id')
        text = doc.get('text', '')
        terms = tokenize(text)
        doc_terms[doc_id] = Counter(terms)
        
        # Count unique documents containing each term
        for term in set(terms):
            doc_frequency[term] += 1
    
    total_docs = len(documents)
    
    # Compute TF-IDF
    tf_idf = {}
    for doc_id, term_counts in doc_terms.items():
        tf_idf[doc_id] = {}
        total_terms = sum(term_counts.values())
        
        for term, count in term_counts.items():
            # Term Frequency (TF)
            tf = count / total_terms if total_terms > 0 else 0
            
            # Inverse Document Frequency (IDF)
            idf = math.log(total_docs / doc_frequency[term]) if doc_frequency[term] > 0 else 0
            
            # TF-IDF
            tf_idf[doc_id][term] = tf * idf
    
    return tf_idf

def cosine_similarity(vec1: Dict[str, float], vec2: Dict[str, float]) -> float:
    """Compute cosine similarity between two vectors"""
    # Get all unique terms
    terms = set(vec1.keys()) | set(vec2.keys())
    
    if not terms:
        return 0.0
    
    # Compute dot product and magnitudes
    dot_product = sum(vec1.get(term, 0) * vec2.get(term, 0) for term in terms)
    magnitude1 = math.sqrt(sum(v ** 2 for v in vec1.values()))
    magnitude2 = math.sqrt(sum(v ** 2 for v in vec2.values()))
    
    if magnitude1 == 0 or magnitude2 == 0:
        return 0.0
    
    return dot_product / (magnitude1 * magnitude2)

def semantic_search(
    query: str,
    documents: List[Dict[str, Any]],
    top_k: int = 10
) -> List[Dict[str, Any]]:
    """
    Perform semantic search using TF-IDF and cosine similarity
    
    Args:
        query: Search query text
        documents: List of dicts with 'id', 'text', and optionally 'entry' (original object)
        top_k: Number of results to return
    
    Returns:
        List of documents sorted by relevance, with similarity scores
    """
    if not documents or not query:
        return []
    
    # Prepare documents for TF-IDF
    doc_list = []
    for doc in documents:
        # Combine title, description, and content for better matching
        text_parts = []
        if doc.get('title'):
            text_parts.append(doc['title'] * 3)  # Weight title more
        if doc.get('description'):
            text_parts.append(doc['description'] * 2)  # Weight description
        if doc.get('content'):
            text_parts.append(doc['content'])
        if doc.get('tags'):
            tags = doc['tags'] if isinstance(doc['tags'], list) else []
            text_parts.append(' '.join(tags))
        
        doc_list.append({
            'id': doc.get('id'),
            'text': ' '.join(text_parts),
            'entry': doc.get('entry', doc)
        })
    
    # Add query as a document for comparison
    query_doc = {'id': 'query', 'text': query}
    doc_list.append(query_doc)
    
    # Compute TF-IDF
    tf_idf = compute_tf_idf(doc_list)
    query_vector = tf_idf.get('query', {})
    
    # Compute similarities
    results = []
    for doc in doc_list:
        if doc['id'] == 'query':
            continue
        
        doc_id = doc['id']
        doc_vector = tf_idf.get(doc_id, {})
        similarity = cosine_similarity(query_vector, doc_vector)
        
        results.append({
            'entry': doc['entry'],
            'similarity': similarity,
            'id': doc_id
        })
    
    # Sort by similarity
    results.sort(key=lambda x: x['similarity'], reverse=True)
    
    # Return top_k results
    return results[:top_k]

def extract_keywords(text: str, top_n: int = 10) -> List[str]:
    """Extract top keywords from text using TF-IDF"""
    if not text:
        return []
    
    # Simple keyword extraction
    words = tokenize(text)
    
    # Filter common stop words
    stop_words = {
        'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
        'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
        'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'should',
        'could', 'may', 'might', 'must', 'can', 'this', 'that', 'these', 'those'
    }
    
    words = [w for w in words if w not in stop_words and len(w) > 2]
    
    # Count frequencies
    word_counts = Counter(words)
    
    # Return top N
    return [word for word, count in word_counts.most_common(top_n)]
