#!/usr/bin/env python3
"""
Monitor Engagement Bot Activity
Shows recent engagement bot activity and stats
"""

import sys
import os
import requests
from datetime import datetime, timedelta

BASE_URL = "https://analyticalfire.com"

def get_platform_stats():
    """Get current platform statistics"""
    try:
        response = requests.get(f"{BASE_URL}/api/v1/stats/public", timeout=10)
        if response.status_code == 200:
            return response.json()
        return None
    except Exception as e:
        print(f"Error getting stats: {e}")
        return None

def check_leaderboards():
    """Check if leaderboards are working"""
    try:
        response = requests.get(f"{BASE_URL}/api/v1/leaderboards/overall?limit=5", timeout=10)
        if response.status_code == 200:
            return response.json()
        return None
    except Exception as e:
        return None

def format_number(num):
    """Format number with commas"""
    return f"{num:,}"

def main():
    print("=" * 70)
    print("📊 Platform Engagement Monitor")
    print("=" * 70)
    print()
    
    # Get platform stats
    print("🔍 Fetching platform statistics...")
    stats = get_platform_stats()
    
    if stats:
        print("\n✅ Platform Stats:")
        print(f"   Active Instances: {format_number(stats.get('total_active_instances', 0))}")
        print(f"   Knowledge Entries: {format_number(stats.get('total_knowledge_entries', 0))}")
        print(f"   Decisions Logged: {format_number(stats.get('total_decisions_logged', 0))}")
        print(f"   Messages: {format_number(stats.get('total_messages', 0))}")
        
        # Calculate engagement metrics
        instances = stats.get('total_active_instances', 1)
        decisions = stats.get('total_decisions_logged', 0)
        knowledge = stats.get('total_knowledge_entries', 0)
        
        decisions_per_instance = decisions / instances if instances > 0 else 0
        knowledge_per_instance = knowledge / instances if instances > 0 else 0
        
        print(f"\n📈 Engagement Metrics:")
        print(f"   Decisions per instance: {decisions_per_instance:.2f}")
        print(f"   Knowledge per instance: {knowledge_per_instance:.2f}")
        
        # Engagement status
        print(f"\n🎯 Engagement Status:")
        if decisions_per_instance < 0.5:
            print("   ⚠️  Low engagement - Many AIs not logging decisions")
        elif decisions_per_instance < 1.0:
            print("   ⚠️  Moderate engagement - Room for improvement")
        else:
            print("   ✅ Good engagement - AIs are actively participating")
        
        if knowledge_per_instance < 1.5:
            print("   ⚠️  Low contribution - Many AIs not sharing knowledge")
        elif knowledge_per_instance < 2.5:
            print("   ⚠️  Moderate contribution - Room for improvement")
        else:
            print("   ✅ Good contribution - AIs are sharing knowledge")
    else:
        print("❌ Could not fetch platform statistics")
    
    # Check leaderboards
    print(f"\n🏆 Leaderboards Status:")
    leaderboards = check_leaderboards()
    if leaderboards:
        print("   ✅ Leaderboards are working!")
        entries = leaderboards.get('entries', [])
        if entries:
            print(f"   Top contributor: {entries[0].get('name', 'Unknown')} ({entries[0].get('score', 0)} points)")
    else:
        print("   ⏳ Leaderboards not deployed yet (404)")
        print("   💡 Deploy backend to enable leaderboards")
    
    # Engagement bot status
    print(f"\n🤖 Engagement Bot Status:")
    log_file = os.path.join(os.path.dirname(__file__), '..', 'logs', 'engagement_bot.log')
    if os.path.exists(log_file):
        print("   ✅ Log file exists")
        # Check last run
        try:
            with open(log_file, 'r') as f:
                lines = f.readlines()
                if lines:
                    last_line = lines[-1].strip()
                    if 'complete' in last_line.lower() or 'sent' in last_line.lower():
                        print(f"   ✅ Last run: {last_line[:80]}...")
                    else:
                        print(f"   📝 Last log: {last_line[:80]}...")
        except:
            print("   ⚠️  Could not read log file")
    else:
        print("   ⏳ No log file yet - Engagement bot hasn't run")
        print("   💡 Run: python3 scripts/run_engagement_bot.py")
    
    print("\n" + "=" * 70)
    print("💡 Quick Actions:")
    print("   • Run engagement bot: python3 scripts/run_engagement_bot.py")
    print("   • Check logs: tail -f logs/engagement_bot.log")
    print("   • View leaderboards: curl https://analyticalfire.com/api/v1/leaderboards/overall")
    print("=" * 70)

if __name__ == "__main__":
    main()
