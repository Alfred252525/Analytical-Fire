"""
Semantic search service using sentence transformers
Provides better search than keyword matching
"""

import numpy as np
from typing import List, Dict, Any
from sentence_transformers import SentenceTransformer
import json
import os

# Initialize model (lazy loading)
_model = None

def get_model():
    """Get or initialize the sentence transformer model"""
    global _model
    if _model is None:
        # Use a lightweight model for embeddings
        _model = SentenceTransformer('all-MiniLM-L6-v2')
    return _model

def compute_embeddings(texts: List[str]) -> np.ndarray:
    """Compute embeddings for a list of texts"""
    model = get_model()
    embeddings = model.encode(texts, convert_to_numpy=True)
    return embeddings

def compute_similarity(query_embedding: np.ndarray, doc_embeddings: np.ndarray) -> np.ndarray:
    """Compute cosine similarity between query and documents"""
    # Normalize embeddings
    query_norm = query_embedding / np.linalg.norm(query_embedding)
    doc_norms = doc_embeddings / np.linalg.norm(doc_embeddings, axis=1, keepdims=True)
    
    # Compute cosine similarity
    similarities = np.dot(doc_norms, query_norm)
    return similarities

def semantic_search(
    query: str,
    documents: List[Dict[str, Any]],
    top_k: int = 10
) -> List[Dict[str, Any]]:
    """
    Perform semantic search on documents
    
    Args:
        query: Search query
        documents: List of documents with 'title', 'content', 'description' fields
        top_k: Number of results to return
    
    Returns:
        List of documents sorted by relevance
    """
    if not documents:
        return []
    
    # Prepare document texts
    doc_texts = []
    for doc in documents:
        text_parts = []
        if doc.get('title'):
            text_parts.append(doc['title'])
        if doc.get('description'):
            text_parts.append(doc['description'])
        if doc.get('content'):
            text_parts.append(doc['content'])
        doc_texts.append(' '.join(text_parts))
    
    # Compute embeddings
    try:
        query_embedding = compute_embeddings([query])[0]
        doc_embeddings = compute_embeddings(doc_texts)
        
        # Compute similarities
        similarities = compute_similarity(query_embedding, doc_embeddings)
        
        # Get top k results
        top_indices = np.argsort(similarities)[::-1][:top_k]
        
        # Return documents with similarity scores
        results = []
        for idx in top_indices:
            result = documents[idx].copy()
            result['similarity_score'] = float(similarities[idx])
            results.append(result)
        
        return results
    except Exception as e:
        # Fallback to keyword search if semantic search fails
        print(f"Semantic search failed: {e}, falling back to keyword search")
        return documents[:top_k]
