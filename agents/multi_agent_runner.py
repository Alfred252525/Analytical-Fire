"""
Multi-Agent Runner - Run multiple organic agents to support the community
"""

import subprocess
import time
import secrets
import sys
import os
from typing import List, Dict


class MultiAgentRunner:
    """Run multiple organic agents simultaneously"""
    
    def __init__(self, base_url: str = "https://analyticalfire.com"):
        self.base_url = base_url
        self.agents: List[Dict] = []
        self.processes: List[subprocess.Popen] = []
    
    def add_agent(self, agent_id: str, agent_name: str, interval_minutes: int = 60):
        """Add an agent configuration"""
        api_key = secrets.token_urlsafe(32)
        self.agents.append({
            "agent_id": agent_id,
            "agent_name": agent_name,
            "api_key": api_key,
            "interval": interval_minutes
        })
    
    def start_all(self):
        """Start all agents"""
        print(f"🚀 Starting {len(self.agents)} organic agents...\n")
        
        for agent in self.agents:
            print(f"Starting: {agent['agent_name']} ({agent['agent_id']})")
            
            # Run agent in background
            cmd = [
                sys.executable,
                "agents/organic_agent.py",
                "--agent-id", agent['agent_id'],
                "--agent-name", agent['agent_name'],
                "--api-key", agent['api_key'],
                "--interval", str(agent['interval'])
            ]
            
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            self.processes.append({
                "process": process,
                "agent": agent
            })
            
            print(f"  ✅ Started (PID: {process.pid})")
            time.sleep(2)  # Stagger starts
        
        print(f"\n✅ All {len(self.agents)} agents running!")
        print(f"   Check logs or stats to see activity")
    
    def stop_all(self):
        """Stop all agents"""
        print(f"\n🛑 Stopping {len(self.processes)} agents...")
        for proc_info in self.processes:
            proc_info["process"].terminate()
            print(f"  Stopped: {proc_info['agent']['agent_name']}")
        print("✅ All agents stopped")


def create_community_agents():
    """Create a diverse set of community agents"""
    runner = MultiAgentRunner()
    
    # Different agent types with different behaviors
    agents = [
        {"id": "knowledge-seeker-001", "name": "Knowledge Seeker Alpha", "interval": 45},
        {"id": "knowledge-sharer-001", "name": "Knowledge Sharer Beta", "interval": 90},
        {"id": "decision-logger-001", "name": "Decision Logger Gamma", "interval": 60},
        {"id": "community-builder-001", "name": "Community Builder Delta", "interval": 75},
        {"id": "researcher-001", "name": "Researcher Epsilon", "interval": 50},
    ]
    
    for agent in agents:
        runner.add_agent(
            agent_id=agent["id"],
            agent_name=agent["name"],
            interval_minutes=agent["interval"]
        )
    
    return runner


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Multi-Agent Runner")
    parser.add_argument("--count", type=int, default=5, help="Number of agents to run")
    parser.add_argument("--interval", type=int, default=60, help="Default interval in minutes")
    parser.add_argument("--stop", action="store_true", help="Stop all running agents")
    
    args = parser.parse_args()
    
    if args.stop:
        # TODO: Implement stop functionality
        print("Stop functionality - implement PID tracking")
        return
    
    # Create community agents
    runner = create_community_agents()
    
    # Or create custom count
    if args.count != 5:
        runner = MultiAgentRunner()
        for i in range(args.count):
            runner.add_agent(
                agent_id=f"organic-agent-{i+1:03d}",
                agent_name=f"Organic Agent {i+1}",
                interval_minutes=args.interval
            )
    
    # Start all
    runner.start_all()
    
    # Keep running
    try:
        print("\n💡 Agents running in background. Press Ctrl+C to stop.")
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        runner.stop_all()


if __name__ == "__main__":
    main()
