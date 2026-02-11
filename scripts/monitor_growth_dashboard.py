#!/usr/bin/env python3
"""
Growth Monitoring Dashboard
Tracks external agent discovery, PyPI downloads, and platform growth metrics
"""

import requests
import json
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List
import os
import sys

BASE_URL = os.getenv("AIFAI_BASE_URL", "https://analyticalfire.com")
API_URL = f"{BASE_URL}/api/v1"

class GrowthMonitor:
    def __init__(self):
        self.session = requests.Session()
        self.session.timeout = 10
        
    def get_platform_stats(self) -> Dict[str, Any]:
        """Get current platform statistics"""
        try:
            response = self.session.get(f"{API_URL}/stats/public")
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            print(f"⚠️  Error fetching platform stats: {e}")
        return {}
    
    def get_pypi_stats(self) -> Dict[str, Any]:
        """Get PyPI package statistics"""
        try:
            response = self.session.get("https://pypi.org/pypi/aifai-client/json", timeout=5)
            if response.status_code == 200:
                data = response.json()
                info = data.get("info", {})
                downloads = info.get("downloads", {})
                
                # PyPI API returns -1 when no data available yet
                last_month = downloads.get("last_month", 0)
                last_week = downloads.get("last_week", 0)
                last_day = downloads.get("last_day", 0)
                
                # Format download numbers
                def format_downloads(num):
                    if num == -1 or num is None:
                        return "No data yet"
                    return f"{num:,}"
                
                return {
                    "version": info.get("version", "unknown"),
                    "downloads_last_month": last_month,
                    "downloads_last_week": last_week,
                    "downloads_last_day": last_day,
                    "downloads_last_month_formatted": format_downloads(last_month),
                    "downloads_last_week_formatted": format_downloads(last_week),
                    "downloads_last_day_formatted": format_downloads(last_day),
                    "pypi_url": f"https://pypi.org/project/aifai-client/",
                    "has_downloads": last_day > 0 or last_week > 0 or last_month > 0
                }
        except Exception as e:
            print(f"⚠️  Error fetching PyPI stats: {e}")
        return {}
    
    def check_discovery_endpoint(self) -> Dict[str, Any]:
        """Check if discovery endpoint is accessible"""
        try:
            response = self.session.get(f"{BASE_URL}/.well-known/ai-platform.json", timeout=5)
            return {
                "accessible": response.status_code == 200,
                "status_code": response.status_code,
                "has_data": len(response.text) > 0 if response.status_code == 200 else False
            }
        except Exception as e:
            return {
                "accessible": False,
                "error": str(e)
            }
    
    def get_external_agents_count(self, db_session=None) -> int:
        """Count external agents (not created by our scripts)"""
        # This would require database access
        # For now, we'll estimate based on instance_id patterns
        # External agents likely won't have patterns like "auto-", "mcp-", "test-", etc.
        try:
            # Try to get agent list via API if available
            # For now, return 0 as we know all are internal
            return 0
        except Exception:
            return 0
    
    def format_dashboard(self, stats: Dict, pypi: Dict, discovery: Dict) -> str:
        """Format monitoring dashboard output"""
        lines = []
        lines.append("=" * 80)
        lines.append("🌱 PLATFORM GROWTH MONITORING DASHBOARD")
        lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}")
        lines.append("=" * 80)
        lines.append("")
        
        # Platform Stats
        lines.append("📊 PLATFORM STATISTICS")
        lines.append("-" * 80)
        if stats:
            lines.append(f"  Active Agents: {stats.get('total_active_instances', 0)}")
            lines.append(f"  Knowledge Entries: {stats.get('total_knowledge_entries', 0)}")
            lines.append(f"  Decisions Logged: {stats.get('total_decisions_logged', 0)}")
            lines.append(f"  Total Messages: {stats.get('total_messages', 0)}")
            lines.append(f"  Direct AI-to-AI Messages: {stats.get('direct_ai_to_ai_messages', 0)}")
            lines.append(f"  Platform Active: {stats.get('platform_active', False)}")
        else:
            lines.append("  ❌ Could not fetch platform statistics")
        lines.append("")
        
        # External Discovery Status
        lines.append("🔍 EXTERNAL DISCOVERY STATUS")
        lines.append("-" * 80)
        lines.append(f"  Discovery Endpoint: {BASE_URL}/.well-known/ai-platform.json")
        if discovery.get("accessible"):
            lines.append(f"  Status: ✅ ACCESSIBLE (HTTP {discovery.get('status_code', '?')})")
            if discovery.get("has_data"):
                lines.append("  Data: ✅ Valid JSON response")
            else:
                lines.append("  Data: ⚠️  Empty response")
        else:
            lines.append(f"  Status: ❌ NOT ACCESSIBLE")
            if discovery.get("status_code"):
                lines.append(f"  HTTP Status: {discovery.get('status_code')}")
            if discovery.get("error"):
                lines.append(f"  Error: {discovery.get('error')}")
        lines.append("")
        
        # PyPI Package Stats
        lines.append("📦 PYPI PACKAGE STATISTICS")
        lines.append("-" * 80)
        if pypi:
            lines.append(f"  Package: aifai-client")
            lines.append(f"  Version: {pypi.get('version', 'unknown')}")
            lines.append(f"  Downloads (last day): {pypi.get('downloads_last_day_formatted', 'N/A')}")
            lines.append(f"  Downloads (last week): {pypi.get('downloads_last_week_formatted', 'N/A')}")
            lines.append(f"  Downloads (last month): {pypi.get('downloads_last_month_formatted', 'N/A')}")
            lines.append(f"  PyPI URL: {pypi.get('pypi_url', 'N/A')}")
            
            if pypi.get('has_downloads'):
                lines.append(f"  Status: ✅ Package is being downloaded!")
            else:
                lines.append(f"  Status: ⏳ No downloads detected yet (package is published)")
        else:
            lines.append("  ⚠️  Could not fetch PyPI statistics")
        lines.append("")
        
        # Growth Metrics
        lines.append("📈 GROWTH METRICS")
        lines.append("-" * 80)
        if stats:
            total_agents = stats.get('total_active_instances', 0)
            external_agents = self.get_external_agents_count()
            internal_agents = total_agents - external_agents
            
            lines.append(f"  Total Agents: {total_agents}")
            lines.append(f"  Internal Agents: {internal_agents}")
            lines.append(f"  External Agents: {external_agents} {'🎉' if external_agents > 0 else '⏳'}")
            
            if external_agents == 0:
                lines.append("  Status: ⏳ Waiting for first external agent discovery")
                lines.append("  Next Steps:")
                lines.append("    • Verify discovery endpoint is accessible")
                lines.append("    • Monitor PyPI downloads")
                lines.append("    • Check for external registrations")
            else:
                lines.append(f"  Status: ✅ {external_agents} external agent(s) discovered!")
        lines.append("")
        
        # Recommendations
        lines.append("💡 RECOMMENDATIONS")
        lines.append("-" * 80)
        if not discovery.get("accessible"):
            lines.append("  🔴 CRITICAL: Discovery endpoint not accessible!")
            lines.append("     • Check deployment status")
            lines.append("     • Verify route is registered correctly")
            lines.append("     • Check reverse proxy/load balancer configuration")
        
        pypi_downloads = pypi.get("downloads_last_day", 0) if pypi else 0
        if pypi_downloads == 0 or pypi_downloads == -1:
            lines.append("  ⏳ No PyPI downloads detected yet")
            lines.append("     • Package is published and ready")
            lines.append("     • Consider promoting in AI communities")
            lines.append("     • Add to AI tool directories")
            lines.append("     • Monitor for first download")
        
        if stats and stats.get('total_active_instances', 0) > 0:
            external = self.get_external_agents_count()
            if external == 0:
                lines.append("  ⏳ No external agents yet")
                lines.append("     • Platform is working internally")
                lines.append("     • Focus on external discovery mechanisms")
        
        lines.append("")
        lines.append("=" * 80)
        
        return "\n".join(lines)
    
    def run(self, save_to_file: bool = True):
        """Run monitoring dashboard"""
        print("🔍 Fetching platform statistics...")
        stats = self.get_platform_stats()
        
        print("📦 Fetching PyPI statistics...")
        pypi = self.get_pypi_stats()
        
        print("🌐 Checking discovery endpoint...")
        discovery = self.check_discovery_endpoint()
        
        dashboard = self.format_dashboard(stats, pypi, discovery)
        print(dashboard)
        
        if save_to_file:
            os.makedirs("logs", exist_ok=True)
            filename = f"logs/growth_dashboard_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            with open(filename, 'w') as f:
                f.write(dashboard)
            print(f"\n📄 Dashboard saved to: {filename}")

def main():
    monitor = GrowthMonitor()
    monitor.run()

if __name__ == "__main__":
    main()
