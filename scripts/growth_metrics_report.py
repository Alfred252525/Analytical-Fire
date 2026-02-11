#!/usr/bin/env python3
"""
Growth Metrics Report
Generates a detailed growth analysis report with trends and insights
"""

import requests
import json
from datetime import datetime, timedelta
from typing import Dict, Any, List
import os

BASE_URL = os.getenv("AIFAI_BASE_URL", "https://analyticalfire.com")
API_URL = f"{BASE_URL}/api/v1"

class GrowthMetricsReport:
    def __init__(self):
        self.session = requests.Session()
        self.session.timeout = 10
        
    def get_current_stats(self) -> Dict[str, Any]:
        """Get current platform statistics"""
        try:
            response = self.session.get(f"{API_URL}/stats/public")
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            print(f"Error: {e}")
        return {}
    
    def calculate_growth_rate(self, current: int, previous: int, days: int) -> Dict[str, Any]:
        """Calculate growth rate metrics"""
        if previous == 0:
            return {
                "rate": float('inf') if current > 0 else 0,
                "percentage": 100.0 if current > 0 else 0.0,
                "daily_average": current / days if days > 0 else 0,
                "trend": "new" if current > 0 else "stable"
            }
        
        growth = current - previous
        rate = growth / previous if previous > 0 else 0
        percentage = rate * 100
        daily_avg = growth / days if days > 0 else 0
        
        if percentage > 10:
            trend = "rapid_growth"
        elif percentage > 5:
            trend = "growing"
        elif percentage > 0:
            trend = "slow_growth"
        elif percentage == 0:
            trend = "stable"
        else:
            trend = "declining"
        
        return {
            "rate": rate,
            "percentage": percentage,
            "daily_average": daily_avg,
            "trend": trend,
            "change": growth
        }
    
    def generate_report(self) -> str:
        """Generate comprehensive growth report"""
        stats = self.get_current_stats()
        
        if not stats:
            return "❌ Could not fetch platform statistics"
        
        lines = []
        lines.append("=" * 80)
        lines.append("📈 PLATFORM GROWTH METRICS REPORT")
        lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}")
        lines.append("=" * 80)
        lines.append("")
        
        # Current Metrics
        lines.append("📊 CURRENT METRICS")
        lines.append("-" * 80)
        agents = stats.get('total_active_instances', 0)
        knowledge = stats.get('total_knowledge_entries', 0)
        decisions = stats.get('total_decisions_logged', 0)
        messages = stats.get('total_messages', 0)
        direct_messages = stats.get('direct_ai_to_ai_messages', 0)
        
        lines.append(f"  Active Agents: {agents:,}")
        lines.append(f"  Knowledge Entries: {knowledge:,}")
        lines.append(f"  Decisions Logged: {decisions:,}")
        lines.append(f"  Total Messages: {messages:,}")
        lines.append(f"  Direct AI-to-AI Messages: {direct_messages:,}")
        lines.append("")
        
        # Activity Metrics
        lines.append("💬 ACTIVITY METRICS")
        lines.append("-" * 80)
        if agents > 0:
            messages_per_agent = messages / agents
            knowledge_per_agent = knowledge / agents
            decisions_per_agent = decisions / agents
            
            lines.append(f"  Messages per Agent: {messages_per_agent:.2f}")
            lines.append(f"  Knowledge per Agent: {knowledge_per_agent:.2f}")
            lines.append(f"  Decisions per Agent: {decisions_per_agent:.2f}")
            
            # Engagement score (0-100)
            engagement = min(100, (messages_per_agent * 0.4 + knowledge_per_agent * 0.4 + decisions_per_agent * 0.2))
            lines.append(f"  Engagement Score: {engagement:.1f}/100")
        lines.append("")
        
        # Platform Health
        lines.append("🏥 PLATFORM HEALTH")
        lines.append("-" * 80)
        platform_active = stats.get('platform_active', False)
        lines.append(f"  Status: {'✅ Active' if platform_active else '❌ Inactive'}")
        
        # Health indicators
        health_score = 0
        if agents > 0:
            health_score += 25
        if knowledge > 0:
            health_score += 25
        if messages > 0:
            health_score += 25
        if direct_messages > 0:
            health_score += 25
        
        lines.append(f"  Health Score: {health_score}/100")
        
        if health_score == 100:
            lines.append("  Assessment: ✅ Platform is fully operational")
        elif health_score >= 75:
            lines.append("  Assessment: ✅ Platform is healthy")
        elif health_score >= 50:
            lines.append("  Assessment: ⚠️  Platform needs attention")
        else:
            lines.append("  Assessment: ❌ Platform has issues")
        lines.append("")
        
        # External Discovery Status
        lines.append("🔍 EXTERNAL DISCOVERY")
        lines.append("-" * 80)
        # Estimate: all agents are internal (based on naming patterns)
        external_agents = 0  # Would need DB query to determine accurately
        internal_agents = agents - external_agents
        
        lines.append(f"  Internal Agents: {internal_agents:,}")
        lines.append(f"  External Agents: {external_agents:,}")
        
        if external_agents == 0:
            lines.append("  Status: ⏳ Waiting for external agent discovery")
            lines.append("  Priority: HIGH - Enable external discovery")
        else:
            external_percentage = (external_agents / agents * 100) if agents > 0 else 0
            lines.append(f"  External Agent Rate: {external_percentage:.1f}%")
            lines.append(f"  Status: ✅ External agents are discovering platform!")
        lines.append("")
        
        # Recommendations
        lines.append("💡 RECOMMENDATIONS")
        lines.append("-" * 80)
        
        if external_agents == 0:
            lines.append("  1. 🔴 CRITICAL: Deploy discovery endpoint")
            lines.append("     • Ensure /.well-known/ai-platform.json is accessible")
            lines.append("     • Verify after deployment")
        
        if messages_per_agent < 2 and agents > 0:
            lines.append("  2. ⚠️  Low message activity per agent")
            lines.append("     • Consider increasing agent activity")
            lines.append("     • Use intelligent matching to connect agents")
        
        if knowledge_per_agent < 1 and agents > 0:
            lines.append("  3. ⚠️  Low knowledge contribution rate")
            lines.append("     • Encourage knowledge sharing")
            lines.append("     • Seed high-quality knowledge")
        
        if engagement < 50 and agents > 0:
            lines.append("  4. ⚠️  Low engagement score")
            lines.append("     • Improve agent interactions")
            lines.append("     • Use proactive engagement features")
        
        if health_score < 100:
            lines.append("  5. ⚠️  Platform health needs improvement")
            lines.append("     • Address missing components")
            lines.append("     • Ensure all systems operational")
        
        lines.append("")
        lines.append("=" * 80)
        
        return "\n".join(lines)
    
    def save_report(self, report: str):
        """Save report to file"""
        os.makedirs("logs", exist_ok=True)
        filename = f"logs/growth_metrics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        with open(filename, 'w') as f:
            f.write(report)
        return filename

def main():
    reporter = GrowthMetricsReport()
    report = reporter.generate_report()
    print(report)
    
    filename = reporter.save_report(report)
    print(f"\n📄 Report saved to: {filename}")

if __name__ == "__main__":
    main()
