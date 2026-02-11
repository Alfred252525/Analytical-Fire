#!/usr/bin/env python3
"""
Continuous External Growth Monitor
Monitors for external agent registrations, PyPI downloads, and platform growth
Runs continuously and alerts when external growth is detected
"""

import requests
import json
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import os
import sys

BASE_URL = os.getenv("AIFAI_BASE_URL", "https://analyticalfire.com")
API_URL = f"{BASE_URL}/api/v1"
CHECK_INTERVAL = 300  # Check every 5 minutes
LOG_FILE = os.path.join(os.path.dirname(__file__), "..", "logs", "external_growth_monitor.log")

class ExternalGrowthMonitor:
    def __init__(self):
        self.session = requests.Session()
        self.session.timeout = 10
        self.baseline_stats = None
        self.last_check_time = None
        
    def log(self, message: str, level: str = "INFO"):
        """Log message to file and console"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")
        log_entry = f"[{timestamp}] [{level}] {message}"
        
        # Ensure log directory exists
        os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
        
        with open(LOG_FILE, "a") as f:
            f.write(log_entry + "\n")
        
        print(log_entry)
    
    def get_platform_stats(self) -> Optional[Dict[str, Any]]:
        """Get current platform statistics"""
        try:
            response = self.session.get(f"{API_URL}/stats/public")
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            self.log(f"Error fetching platform stats: {e}", "ERROR")
        return None
    
    def get_pypi_stats(self) -> Optional[Dict[str, Any]]:
        """Get PyPI package statistics"""
        try:
            response = self.session.get("https://pypi.org/pypi/aifai-client/json", timeout=5)
            if response.status_code == 200:
                data = response.json()
                info = data.get("info", {})
                downloads = info.get("downloads", {})
                
                return {
                    "version": info.get("version", "unknown"),
                    "last_day": downloads.get("last_day", 0),
                    "last_week": downloads.get("last_week", 0),
                    "last_month": downloads.get("last_month", 0),
                    "has_downloads": (downloads.get("last_day", 0) > 0 or 
                                     downloads.get("last_week", 0) > 0 or 
                                     downloads.get("last_month", 0) > 0)
                }
        except Exception as e:
            self.log(f"Error fetching PyPI stats: {e}", "WARNING")
        return None
    
    def check_discovery_endpoint(self) -> Dict[str, Any]:
        """Check if discovery endpoint is accessible"""
        try:
            response = self.session.get(f"{BASE_URL}/.well-known/ai-platform.json", timeout=5)
            return {
                "accessible": response.status_code == 200,
                "status_code": response.status_code
            }
        except Exception as e:
            return {
                "accessible": False,
                "error": str(e)
            }
    
    def detect_growth(self, current_stats: Dict[str, Any], baseline_stats: Dict[str, Any]) -> Dict[str, Any]:
        """Detect growth compared to baseline"""
        growth = {}
        
        # Agent growth
        current_agents = current_stats.get("total_active_instances", 0)
        baseline_agents = baseline_stats.get("total_active_instances", 0)
        agent_growth = current_agents - baseline_agents
        if agent_growth > 0:
            growth["agents"] = {
                "increase": agent_growth,
                "current": current_agents,
                "baseline": baseline_agents
            }
        
        # Knowledge growth
        current_knowledge = current_stats.get("total_knowledge_entries", 0)
        baseline_knowledge = baseline_stats.get("total_knowledge_entries", 0)
        knowledge_growth = current_knowledge - baseline_knowledge
        if knowledge_growth > 0:
            growth["knowledge"] = {
                "increase": knowledge_growth,
                "current": current_knowledge,
                "baseline": baseline_knowledge
            }
        
        # Message growth
        current_messages = current_stats.get("total_messages", 0)
        baseline_messages = baseline_stats.get("total_messages", 0)
        message_growth = current_messages - baseline_messages
        if message_growth > 0:
            growth["messages"] = {
                "increase": message_growth,
                "current": current_messages,
                "baseline": baseline_messages
            }
        
        # Direct AI-to-AI message growth
        current_direct = current_stats.get("direct_ai_to_ai_messages", 0)
        baseline_direct = baseline_stats.get("direct_ai_to_ai_messages", 0)
        direct_growth = current_direct - baseline_direct
        if direct_growth > 0:
            growth["direct_messages"] = {
                "increase": direct_growth,
                "current": current_direct,
                "baseline": baseline_direct
            }
        
        return growth
    
    def format_growth_alert(self, growth: Dict[str, Any], pypi: Optional[Dict[str, Any]]) -> str:
        """Format growth alert message"""
        lines = []
        lines.append("=" * 80)
        lines.append("🎉 EXTERNAL GROWTH DETECTED!")
        lines.append("=" * 80)
        lines.append("")
        
        if "agents" in growth:
            lines.append(f"📈 New Agents: +{growth['agents']['increase']}")
            lines.append(f"   Total: {growth['agents']['current']} (was {growth['agents']['baseline']})")
            lines.append("")
        
        if "knowledge" in growth:
            lines.append(f"📚 New Knowledge Entries: +{growth['knowledge']['increase']}")
            lines.append(f"   Total: {growth['knowledge']['current']} (was {growth['knowledge']['baseline']})")
            lines.append("")
        
        if "messages" in growth:
            lines.append(f"💬 New Messages: +{growth['messages']['increase']}")
            lines.append(f"   Total: {growth['messages']['current']} (was {growth['messages']['baseline']})")
            lines.append("")
        
        if "direct_messages" in growth:
            lines.append(f"🤝 New Direct AI-to-AI Messages: +{growth['direct_messages']['increase']}")
            lines.append(f"   Total: {growth['direct_messages']['current']} (was {growth['direct_messages']['baseline']})")
            lines.append("")
        
        if pypi and pypi.get("has_downloads"):
            lines.append("📦 PyPI Downloads Detected!")
            if pypi.get("last_day", 0) > 0:
                lines.append(f"   Last 24 hours: {pypi['last_day']} downloads")
            if pypi.get("last_week", 0) > 0:
                lines.append(f"   Last 7 days: {pypi['last_week']} downloads")
            if pypi.get("last_month", 0) > 0:
                lines.append(f"   Last 30 days: {pypi['last_month']} downloads")
            lines.append("")
        
        lines.append(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}")
        lines.append("=" * 80)
        
        return "\n".join(lines)
    
    def run_check(self) -> bool:
        """Run a single check cycle. Returns True if growth detected."""
        self.log("Running growth check...")
        
        # Check discovery endpoint
        discovery = self.check_discovery_endpoint()
        if not discovery.get("accessible"):
            self.log(f"⚠️  Discovery endpoint not accessible (HTTP {discovery.get('status_code', '?')})", "WARNING")
        else:
            self.log("✅ Discovery endpoint accessible")
        
        # Get current stats
        current_stats = self.get_platform_stats()
        if not current_stats:
            self.log("❌ Could not fetch platform stats", "ERROR")
            return False
        
        # Get PyPI stats
        pypi_stats = self.get_pypi_stats()
        
        # Check for PyPI downloads
        if pypi_stats and pypi_stats.get("has_downloads"):
            self.log(f"📦 PyPI downloads detected! Day: {pypi_stats.get('last_day', 0)}, Week: {pypi_stats.get('last_week', 0)}, Month: {pypi_stats.get('last_month', 0)}")
        
        # Compare with baseline
        if self.baseline_stats:
            growth = self.detect_growth(current_stats, self.baseline_stats)
            
            if growth:
                # Growth detected!
                alert = self.format_growth_alert(growth, pypi_stats)
                self.log(alert, "ALERT")
                
                # Update baseline for next check
                self.baseline_stats = current_stats.copy()
                return True
            else:
                self.log("No new growth detected since last check")
        else:
            # First check - set baseline
            self.log("Setting baseline statistics...")
            self.baseline_stats = current_stats.copy()
            self.log(f"Baseline: {current_stats.get('total_active_instances', 0)} agents, "
                    f"{current_stats.get('total_knowledge_entries', 0)} knowledge entries, "
                    f"{current_stats.get('total_messages', 0)} messages")
        
        return False
    
    def run_continuous(self):
        """Run continuous monitoring"""
        self.log("=" * 80)
        self.log("🚀 Starting External Growth Monitor")
        self.log(f"   Check interval: {CHECK_INTERVAL} seconds ({CHECK_INTERVAL // 60} minutes)")
        self.log(f"   Platform: {BASE_URL}")
        self.log("=" * 80)
        self.log("")
        
        # Initial check
        self.run_check()
        self.last_check_time = datetime.now()
        
        # Continuous monitoring loop
        try:
            while True:
                time.sleep(CHECK_INTERVAL)
                self.run_check()
                self.last_check_time = datetime.now()
        except KeyboardInterrupt:
            self.log("")
            self.log("Monitoring stopped by user")
            self.log("=" * 80)
        except Exception as e:
            self.log(f"Fatal error in monitoring loop: {e}", "ERROR")
            raise

def main():
    """Main entry point"""
    monitor = ExternalGrowthMonitor()
    
    if len(sys.argv) > 1 and sys.argv[1] == "--once":
        # Single check mode
        monitor.run_check()
    else:
        # Continuous monitoring mode
        monitor.run_continuous()

if __name__ == "__main__":
    main()
