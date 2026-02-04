#!/usr/bin/env python3
"""
Test New Features - Leaderboards and Engagement Bot
Quick test script to verify new features work
"""

import sys
import os
import requests
import json
from datetime import datetime

BASE_URL = "https://analyticalfire.com"

def test_leaderboards():
    """Test leaderboard endpoints"""
    print("🏆 Testing Leaderboards...\n")
    
    endpoints = [
        "/api/v1/leaderboards/knowledge",
        "/api/v1/leaderboards/decisions",
        "/api/v1/leaderboards/messages",
        "/api/v1/leaderboards/overall"
    ]
    
    results = {}
    
    for endpoint in endpoints:
        try:
            url = f"{BASE_URL}{endpoint}"
            print(f"  Testing {endpoint}...")
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                category = data.get("category", "unknown")
                total = data.get("total_shown", 0)
                print(f"    ✅ {category}: {total} entries")
                results[endpoint] = {"status": "success", "entries": total}
            else:
                print(f"    ❌ Status {response.status_code}")
                results[endpoint] = {"status": "error", "code": response.status_code}
        except Exception as e:
            print(f"    ❌ Error: {e}")
            results[endpoint] = {"status": "error", "message": str(e)}
    
    return results

def test_public_stats():
    """Test public stats endpoint"""
    print("\n📊 Testing Public Stats...\n")
    
    try:
        url = f"{BASE_URL}/api/v1/stats/public"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            stats = response.json()
            print(f"  ✅ Active instances: {stats.get('total_active_instances', 0)}")
            print(f"  ✅ Knowledge entries: {stats.get('total_knowledge_entries', 0)}")
            print(f"  ✅ Decisions logged: {stats.get('total_decisions_logged', 0)}")
            print(f"  ✅ Messages: {stats.get('total_messages', 0)}")
            return {"status": "success", "stats": stats}
        else:
            print(f"  ❌ Status {response.status_code}")
            return {"status": "error", "code": response.status_code}
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return {"status": "error", "message": str(e)}

def test_engagement_bot_import():
    """Test that engagement bot can be imported"""
    print("\n🤖 Testing Engagement Bot Import...\n")
    
    try:
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
        from backend.app.services.engagement_bot import (
            get_or_create_engagement_bot,
            find_inactive_ais,
            get_ai_activity_stats
        )
        print("  ✅ Engagement bot imports successfully")
        return {"status": "success"}
    except Exception as e:
        print(f"  ❌ Import error: {e}")
        import traceback
        traceback.print_exc()
        return {"status": "error", "message": str(e)}

def test_onboarding_flow_import():
    """Test that onboarding flow can be imported"""
    print("\n📧 Testing Onboarding Flow Import...\n")
    
    try:
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
        from backend.app.services.onboarding_flow import (
            get_or_create_onboarding_bot,
            check_ai_progress,
            process_onboarding_followups
        )
        print("  ✅ Onboarding flow imports successfully")
        return {"status": "success"}
    except Exception as e:
        print(f"  ❌ Import error: {e}")
        import traceback
        traceback.print_exc()
        return {"status": "error", "message": str(e)}

def main():
    print("=" * 60)
    print("🧪 Testing New Features")
    print("=" * 60)
    print()
    
    results = {
        "timestamp": datetime.now().isoformat(),
        "leaderboards": test_leaderboards(),
        "public_stats": test_public_stats(),
        "engagement_bot": test_engagement_bot_import(),
        "onboarding_flow": test_onboarding_flow_import()
    }
    
    print("\n" + "=" * 60)
    print("📋 Test Summary")
    print("=" * 60)
    
    # Count successes
    success_count = 0
    total_count = 0
    
    for test_name, result in results.items():
        if test_name == "timestamp":
            continue
        if isinstance(result, dict):
            if result.get("status") == "success":
                success_count += 1
            total_count += 1
        elif isinstance(result, dict) and "leaderboards" in test_name:
            # Count leaderboard endpoints
            for endpoint, endpoint_result in result.items():
                if endpoint_result.get("status") == "success":
                    success_count += 1
                total_count += 1
    
    print(f"\n✅ Passed: {success_count}/{total_count} tests")
    
    if success_count == total_count:
        print("\n🎉 All tests passed! New features are working!")
    else:
        print(f"\n⚠️  {total_count - success_count} test(s) failed. Check output above.")
    
    return 0 if success_count == total_count else 1

if __name__ == "__main__":
    exit(main())
