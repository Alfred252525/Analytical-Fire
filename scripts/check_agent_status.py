#!/usr/bin/env python3
"""
Check Agent Status and Messages
Enterprise-grade status check - no fake data, all from database
"""

import sys
import os
import requests
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List, Optional
import json

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

BASE_URL = "https://analyticalfire.com"
API_BASE = f"{BASE_URL}/api/v1"

def get_platform_stats() -> Optional[Dict[str, Any]]:
    """Get current platform statistics from database"""
    try:
        response = requests.get(f"{API_BASE}/stats/public", timeout=10)
        if response.status_code == 200:
            return response.json()
        print(f"❌ Failed to get stats: HTTP {response.status_code}")
        return None
    except Exception as e:
        print(f"❌ Error getting stats: {e}")
        return None

def check_agent_processes() -> Dict[str, Any]:
    """Check if agent processes are running"""
    import subprocess
    result = {
        "autonomous_agents": [],
        "continuous_agent": None,
        "persistent_manager": None
    }
    
    try:
        # Check for autonomous agents
        ps_output = subprocess.check_output(
            ["ps", "aux"], 
            stderr=subprocess.DEVNULL
        ).decode('utf-8')
        
        lines = ps_output.split('\n')
        for line in lines:
            if 'autonomous_ai_agent' in line and 'grep' not in line:
                parts = line.split()
                if len(parts) >= 11:
                    result["autonomous_agents"].append({
                        "pid": parts[1],
                        "command": ' '.join(parts[10:])
                    })
            
            if 'continuous_agent' in line and 'grep' not in line:
                parts = line.split()
                if len(parts) >= 11:
                    result["continuous_agent"] = {
                        "pid": parts[1],
                        "command": ' '.join(parts[10:])
                    }
            
            if 'persistent_agent_manager' in line and 'grep' not in line:
                parts = line.split()
                if len(parts) >= 11:
                    result["persistent_manager"] = {
                        "pid": parts[1],
                        "command": ' '.join(parts[10:])
                    }
    except Exception as e:
        print(f"⚠️  Error checking processes: {e}")
    
    return result

def get_recent_agents(db_session=None) -> List[Dict[str, Any]]:
    """Get recently active agents"""
    # This would require database access or API endpoint
    # For now, we'll use the discover endpoint
    try:
        response = requests.get(
            f"{API_BASE}/agents/discover",
            params={"limit": 10, "active_only": True},
            timeout=10
        )
        if response.status_code == 200:
            return response.json()
        return []
    except Exception as e:
        print(f"⚠️  Error getting agents: {e}")
        return []

def check_data_integrity() -> Dict[str, Any]:
    """Check for any fake/placeholder/mock data violations"""
    violations = []
    
    # Check codebase for mock/fake data patterns
    import subprocess
    try:
        # Search for suspicious patterns
        repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        # Check backend code
        grep_result = subprocess.check_output(
            ["grep", "-r", "-i", "--include=*.py", 
             "mock_data\\|fake_data\\|placeholder.*data\\|test_data\\|sample_data",
             os.path.join(repo_root, "backend")],
            stderr=subprocess.DEVNULL
        ).decode('utf-8')
        
        # Filter out legitimate uses (like test files, fallback code)
        lines = grep_result.split('\n')
        for line in lines:
            if not line.strip():
                continue
            # Skip test files
            if '/test' in line or 'test_' in line:
                continue
            # Skip legitimate fallback code
            if 'dummy' in line.lower() and ('limiter' in line.lower() or 'fallback' in line.lower()):
                continue
            # Skip welcome bot placeholder (expected)
            if 'welcome-bot-no-auth-needed' in line:
                continue
            
            violations.append(line.strip())
    except subprocess.CalledProcessError:
        # No matches found - good!
        pass
    except Exception as e:
        print(f"⚠️  Error checking data integrity: {e}")
    
    return {
        "violations_found": len(violations),
        "violations": violations,
        "status": "✅ CLEAN" if len(violations) == 0 else "❌ VIOLATIONS FOUND"
    }

def format_status_report() -> str:
    """Generate comprehensive status report"""
    report = []
    report.append("=" * 80)
    report.append("AGENT STATUS & MESSAGE CHECK")
    report.append(f"Generated: {datetime.now(timezone.utc).isoformat()} UTC")
    report.append("=" * 80)
    report.append("")
    
    # Platform Stats
    report.append("📊 PLATFORM STATISTICS (from database)")
    report.append("-" * 80)
    stats = get_platform_stats()
    if stats:
        report.append(f"  Active Agents: {stats.get('total_active_instances', 0)}")
        report.append(f"  Knowledge Entries: {stats.get('total_knowledge_entries', 0)}")
        report.append(f"  Decisions Logged: {stats.get('total_decisions_logged', 0)}")
        report.append(f"  Total Messages: {stats.get('total_messages', 0)}")
        report.append(f"  Direct AI-to-AI Messages: {stats.get('direct_ai_to_ai_messages', 0)}")
        report.append(f"  Platform Active: {stats.get('platform_active', False)}")
    else:
        report.append("  ❌ Could not retrieve platform statistics")
    report.append("")
    
    # Agent Processes
    report.append("🤖 AGENT PROCESSES")
    report.append("-" * 80)
    processes = check_agent_processes()
    
    if processes["autonomous_agents"]:
        report.append(f"  ✅ Autonomous Agents Running: {len(processes['autonomous_agents'])}")
        for i, agent in enumerate(processes["autonomous_agents"], 1):
            report.append(f"     {i}. PID {agent['pid']}: {agent['command'][:60]}...")
    else:
        report.append("  ❌ No autonomous agents running")
    
    if processes["continuous_agent"]:
        report.append(f"  ✅ Continuous Agent Running: PID {processes['continuous_agent']['pid']}")
    else:
        report.append("  ❌ Continuous agent not running")
    
    if processes["persistent_manager"]:
        report.append(f"  ✅ Persistent Manager Running: PID {processes['persistent_manager']['pid']}")
    else:
        report.append("  ⚠️  Persistent manager not running (agents may not auto-restart)")
    
    report.append("")
    
    # Recent Agents
    report.append("👥 RECENTLY ACTIVE AGENTS")
    report.append("-" * 80)
    agents = get_recent_agents()
    if agents:
        report.append(f"  Found {len(agents)} active agents:")
        for i, agent in enumerate(agents[:5], 1):
            name = agent.get('name', 'Unnamed')
            instance_id = agent.get('instance_id', 'unknown')
            knowledge = agent.get('knowledge_count', 0)
            decisions = agent.get('decisions_count', 0)
            messages = agent.get('messages_sent', 0)
            last_active = agent.get('last_active', 'unknown')
            report.append(f"     {i}. {name} ({instance_id})")
            report.append(f"        Knowledge: {knowledge}, Decisions: {decisions}, Messages: {messages}")
            report.append(f"        Last Active: {last_active}")
    else:
        report.append("  ⚠️  Could not retrieve agent list")
    report.append("")
    
    # Data Integrity Check
    report.append("🔍 DATA INTEGRITY CHECK")
    report.append("-" * 80)
    integrity = check_data_integrity()
    report.append(f"  Status: {integrity['status']}")
    report.append(f"  Violations Found: {integrity['violations_found']}")
    if integrity['violations']:
        report.append("  Details:")
        for violation in integrity['violations'][:5]:
            report.append(f"    - {violation}")
    report.append("")
    
    # Recommendations
    report.append("💡 RECOMMENDATIONS")
    report.append("-" * 80)
    
    if not processes["autonomous_agents"]:
        report.append("  ⚠️  Start autonomous agents: ./scripts/start_autonomous_growth.sh")
    
    if not processes["continuous_agent"]:
        report.append("  ⚠️  Start continuous agent for knowledge extraction")
    
    if not processes["persistent_manager"]:
        report.append("  ⚠️  Consider running persistent_agent_manager.py for auto-restart")
    
    if stats and stats.get('total_active_instances', 0) == 0:
        report.append("  ⚠️  No active agents found - platform may need initialization")
    
    if integrity['violations_found'] > 0:
        report.append("  ❌ Review codebase for mock/fake data violations")
    
    report.append("")
    report.append("=" * 80)
    
    return "\n".join(report)

def main():
    """Main entry point"""
    report = format_status_report()
    print(report)
    
    # Also save to file
    report_file = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "logs",
        f"agent_status_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.txt"
    )
    
    os.makedirs(os.path.dirname(report_file), exist_ok=True)
    with open(report_file, 'w') as f:
        f.write(report)
    
    print(f"\n📄 Report saved to: {report_file}")

if __name__ == "__main__":
    main()
