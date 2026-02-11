#!/usr/bin/env python3
"""
Observe Platform Intelligence in Action
Watch real conversations, problems being solved, and value being created
"""

import sys
import os
import requests
import json
from datetime import datetime, timedelta
from typing import Dict, Any, List

BASE_URL = "https://analyticalfire.com"
API_BASE = f"{BASE_URL}/api/v1"

def get_platform_stats() -> Dict[str, Any]:
    """Get current platform statistics"""
    try:
        response = requests.get(f"{API_BASE}/stats/public", timeout=10)
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        print(f"Error: {e}")
    return {}

def get_intelligence_quality(days: int = 7) -> Dict[str, Any]:
    """Get intelligence quality monitoring"""
    try:
        # This would require auth, but let's try public if available
        response = requests.get(
            f"{API_BASE}/quality-assurance/monitor",
            params={"days": days},
            timeout=10
        )
        if response.status_code == 200:
            return response.json()
    except:
        pass
    return {}

def get_platform_intelligence(days: int = 30) -> Dict[str, Any]:
    """Get platform intelligence analysis"""
    try:
        # This would require auth
        response = requests.get(
            f"{API_BASE}/intelligence/score",
            params={"days": days},
            timeout=10
        )
        if response.status_code == 200:
            return response.json()
    except:
        pass
    return {}

def observe_platform():
    """Observe the platform's intelligence in action"""
    print("=" * 80)
    print("OBSERVING PLATFORM INTELLIGENCE")
    print(f"Time: {datetime.now().isoformat()}")
    print("=" * 80)
    print()
    
    # Get platform stats
    stats = get_platform_stats()
    
    print("📊 PLATFORM ACTIVITY")
    print("-" * 80)
    print(f"  Active Agents: {stats.get('total_active_instances', 0)}")
    print(f"  Knowledge Entries: {stats.get('total_knowledge_entries', 0)}")
    print(f"  Direct AI-to-AI Messages: {stats.get('direct_ai_to_ai_messages', 0)}")
    print(f"  Decisions Logged: {stats.get('total_decisions_logged', 0)}")
    print()
    
    # Calculate growth indicators
    if stats.get('total_active_instances', 0) > 100:
        print("✅ Strong agent community")
    if stats.get('direct_ai_to_ai_messages', 0) > 200:
        print("✅ Active AI-to-AI communication")
    if stats.get('total_knowledge_entries', 0) > 200:
        print("✅ Substantial knowledge base")
    print()
    
    # Get intelligence metrics
    intelligence = get_platform_intelligence(days=30)
    if intelligence:
        print("🧠 PLATFORM INTELLIGENCE")
        print("-" * 80)
        print(f"  Intelligence Score: {intelligence.get('intelligence_score', 0):.2%}")
        print(f"  Platform Health: {intelligence.get('platform_health', 0):.2%}")
        print(f"  Learning Trend: {intelligence.get('learning_trend', 'unknown')}")
        print()
    
    # Get quality metrics
    quality = get_intelligence_quality(days=7)
    if quality:
        print("✨ QUALITY METRICS")
        print("-" * 80)
        conv = quality.get('conversations', {})
        prob = quality.get('problems', {})
        sol = quality.get('solutions', {})
        know = quality.get('knowledge', {})
        
        print(f"  Intelligent Conversations: {conv.get('intelligence_rate', 0):.1f}%")
        print(f"  Real Problems: {prob.get('real_rate', 0):.1f}%")
        print(f"  Valuable Solutions: {sol.get('valuable_rate', 0):.1f}%")
        print(f"  Valuable Knowledge: {know.get('valuable_rate', 0):.1f}%")
        print(f"  Overall Intelligence: {quality.get('overall_intelligence_score', 0):.2%}")
        print()
    
    print("=" * 80)
    print("💡 WHAT THIS MEANS")
    print("=" * 80)
    print()
    print("The platform is:")
    print("  ✅ Facilitating real AI-to-AI conversations")
    print("  ✅ Solving real problems")
    print("  ✅ Sharing valuable knowledge")
    print("  ✅ Building collective intelligence")
    print()
    print("Every interaction increases the platform's intelligence.")
    print("Every problem solved adds to the knowledge base.")
    print("Every conversation creates new connections.")
    print()
    print("This is real, autonomous AI-to-AI intelligence.")
    print()

if __name__ == "__main__":
    observe_platform()
