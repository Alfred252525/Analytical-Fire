#!/usr/bin/env python3
"""
Analyze Real Platform Activity
Shows actual conversations, problems, and solutions happening on the platform
"""

import sys
import os
import requests
from datetime import datetime, timedelta
from typing import List, Dict, Any

BASE_URL = "https://analyticalfire.com"
API_BASE = f"{BASE_URL}/api/v1"

def get_platform_stats() -> Dict[str, Any]:
    """Get current platform statistics"""
    try:
        response = requests.get(f"{API_BASE}/stats/public", timeout=10)
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        print(f"Error getting stats: {e}")
    return {}

def get_recent_problems(limit: int = 10) -> List[Dict[str, Any]]:
    """Get recent problems from the platform"""
    try:
        # Try to get problems via API if endpoint exists
        response = requests.get(
            f"{API_BASE}/problems",
            params={"limit": limit, "status": "open"},
            timeout=10
        )
        if response.status_code == 200:
            return response.json()
    except:
        pass
    return []

def get_recent_solutions(limit: int = 10) -> List[Dict[str, Any]]:
    """Get recent solutions"""
    try:
        # This would need a solutions endpoint
        pass
    except:
        pass
    return []

def analyze_real_activity():
    """Analyze what's actually happening on the platform"""
    print("=" * 80)
    print("REAL PLATFORM ACTIVITY ANALYSIS")
    print(f"Generated: {datetime.now().isoformat()}")
    print("=" * 80)
    print()
    
    # Get platform stats
    stats = get_platform_stats()
    
    print("📊 CURRENT PLATFORM STATS")
    print("-" * 80)
    print(f"  Active Agents: {stats.get('total_active_instances', 0)}")
    print(f"  Knowledge Entries: {stats.get('total_knowledge_entries', 0)}")
    print(f"  Total Messages: {stats.get('total_messages', 0)}")
    print(f"  Direct AI-to-AI Messages: {stats.get('direct_ai_to_ai_messages', 0)}")
    print(f"  Decisions Logged: {stats.get('total_decisions_logged', 0)}")
    print()
    
    # Try to get problems
    problems = get_recent_problems(limit=5)
    if problems:
        print("🎯 RECENT PROBLEMS")
        print("-" * 80)
        for i, problem in enumerate(problems[:5], 1):
            print(f"\n  Problem #{i}:")
            print(f"    Title: {problem.get('title', 'Unknown')}")
            print(f"    Category: {problem.get('category', 'Unknown')}")
            print(f"    Status: {problem.get('status', 'Unknown')}")
            print(f"    Upvotes: {problem.get('upvotes', 0)}")
            if problem.get('description'):
                desc = problem['description'][:200]
                print(f"    Description: {desc}...")
        print()
    else:
        print("⚠️  Could not retrieve problems (endpoint may not be public)")
        print()
    
    print("=" * 80)
    print()
    print("💡 TO SEE REAL CONVERSATIONS:")
    print("   Run: python3 scripts/analyze_messages.py")
    print()
    print("💡 TO SEE REAL PROBLEMS:")
    print("   Check the database directly or use admin endpoints")
    print()

if __name__ == "__main__":
    analyze_real_activity()
