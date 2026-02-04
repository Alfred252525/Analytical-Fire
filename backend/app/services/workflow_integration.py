"""
Workflow integration helpers
Make it easy for AIs to use the platform in their workflow
"""

from typing import Dict, Any, List, Optional
from datetime import datetime

def should_search_before_task(task_description: str, keywords: List[str] = None) -> bool:
    """
    Determine if an AI should search knowledge base before starting a task
    
    Args:
        task_description: Description of the task
        keywords: Optional list of keywords that indicate knowledge search is useful
    
    Returns:
        True if should search, False otherwise
    """
    if keywords is None:
        keywords = [
            "how to", "how do", "best way", "solution", "fix", "error",
            "deploy", "configure", "setup", "implement", "create"
        ]
    
    task_lower = task_description.lower()
    return any(keyword in task_lower for keyword in keywords)

def extract_search_terms(task_description: str) -> List[str]:
    """
    Extract search terms from a task description
    
    Args:
        task_description: Description of the task
    
    Returns:
        List of potential search terms
    """
    # Simple extraction - in production, use NLP
    words = task_description.lower().split()
    
    # Remove common words
    stop_words = {"the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "of", "with", "by", "is", "are", "was", "were", "be", "been", "being", "have", "has", "had", "do", "does", "did", "will", "would", "should", "could", "may", "might", "must", "can", "this", "that", "these", "those", "i", "you", "he", "she", "it", "we", "they", "what", "which", "who", "whom", "whose", "where", "when", "why", "how"}
    
    # Extract meaningful terms (2+ chars, not stop words)
    terms = [w for w in words if len(w) >= 2 and w not in stop_words]
    
    # Return top 3-5 terms
    return terms[:5]

def format_decision_for_logging(
    context: str,
    decision: str,
    outcome: str,
    tools_used: List[str] = None,
    reasoning: str = None
) -> Dict[str, Any]:
    """
    Format a decision for logging to the platform
    
    Args:
        context: Context of the decision
        decision: The decision made
        outcome: Outcome (success, failure, partial)
        tools_used: Tools used
        reasoning: Reasoning behind decision
    
    Returns:
        Formatted decision dict
    """
    return {
        "context": context,
        "decision": decision,
        "outcome": outcome,
        "tools_used": tools_used or [],
        "reasoning": reasoning,
        "timestamp": datetime.utcnow().isoformat()
    }

def format_knowledge_for_sharing(
    title: str,
    content: str,
    category: str,
    tags: List[str] = None,
    context: str = None
) -> Dict[str, Any]:
    """
    Format knowledge for sharing on the platform
    
    Args:
        title: Title of knowledge
        content: Content/solution
        category: Category
        tags: Tags
        context: Context where this applies
    
    Returns:
        Formatted knowledge dict
    """
    return {
        "title": title,
        "content": content,
        "category": category,
        "tags": tags or [],
        "context": context,
        "timestamp": datetime.utcnow().isoformat()
    }
