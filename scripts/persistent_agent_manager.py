#!/usr/bin/env python3
"""
Persistent Agent Manager - Ensures agents NEVER stop
This is our mission: continuous growth, continuous intelligence
"""

import subprocess
import time
import os
import signal
import sys
from datetime import datetime

class PersistentAgentManager:
    """Manages agents to ensure they NEVER stop - growth is our mission"""
    
    def __init__(self):
        self.agents = []
        self.running = True
        self.check_interval = 60  # Check every minute
        
    def start_agent(self, name, command, env=None):
        """Start an agent process"""
        try:
            env_vars = os.environ.copy()
            if env:
                env_vars.update(env)
            
            # Don't pipe stdout/stderr - let them go to CloudWatch logs
            # Use unbuffered output so logs appear immediately
            process = subprocess.Popen(
                command,
                shell=True,
                env=env_vars,
                stdout=None,  # Let stdout go to CloudWatch
                stderr=subprocess.STDOUT,  # Merge stderr to stdout
                preexec_fn=os.setsid,  # Create new process group
                bufsize=0  # Unbuffered for immediate log visibility
            )
            
            self.agents.append({
                'name': name,
                'process': process,
                'command': command,
                'env': env,
                'restart_count': 0,
                'last_restart': datetime.now()
            })
            
            print(f"✅ Started {name} (PID: {process.pid})")
            return process
        except Exception as e:
            print(f"❌ Failed to start {name}: {e}")
            return None
    
    def check_agents(self):
        """Check if agents are running, restart if needed"""
        for agent in self.agents[:]:  # Copy list to avoid modification during iteration
            process = agent['process']
            
            # Check if process is still running
            if process.poll() is not None:
                # Process died - RESTART IT (growth is our mission!)
                print(f"⚠️  {agent['name']} stopped (exit code: {process.returncode})")
                print(f"   🔄 Restarting... (restart #{agent['restart_count'] + 1})")
                
                agent['restart_count'] += 1
                agent['last_restart'] = datetime.now()
                
                # Restart the agent
                new_process = self.start_agent(
                    agent['name'],
                    agent['command'],
                    agent['env']
                )
                
                if new_process:
                    agent['process'] = new_process
                    print(f"   ✅ {agent['name']} restarted successfully")
                else:
                    print(f"   ❌ Failed to restart {agent['name']}, will retry next check")
    
    def run(self):
        """Run the manager - NEVER STOPS"""
        print("🚀 Persistent Agent Manager Starting")
        print("=" * 50)
        print("Mission: Ensure agents NEVER stop")
        print("Vision: Continuous growth, continuous intelligence")
        print("=" * 50)
        print()
        
        # Start all agents
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        os.chdir(base_dir)
        
        # Agent 1: Default
        self.start_agent(
            "Default Agent",
            "python3 scripts/autonomous_ai_agent.py --interval 30",
            env=None
        )
        
        # Agent 2: Problem Solver
        self.start_agent(
            "Problem Solver Agent",
            "python3 scripts/autonomous_ai_agent.py --interval 30 --persona problem_solver",
            env={
                'AIFAI_INSTANCE_ID': 'auto-agent-problem',
                'AIFAI_API_KEY': 'key-agent-problem-8f7e6d5c4b3a2918'
            }
        )
        
        # Agent 3: Connector
        self.start_agent(
            "Connector Agent",
            "python3 scripts/autonomous_ai_agent.py --interval 30 --persona connector",
            env={
                'AIFAI_INSTANCE_ID': 'auto-agent-connector',
                'AIFAI_API_KEY': 'key-agent-connector-9e8d7c6b5a4f3829'
            }
        )
        
        # Agent 4: Continuous
        self.start_agent(
            "Continuous Agent",
            "cd mcp-server && python3 continuous_agent.py --interval 60",
            env=None
        )
        
        print()
        print("✅ All agents started")
        print(f"🔄 Monitoring every {self.check_interval} seconds")
        print("💡 Agents will auto-restart if they stop")
        print("🛑 Press Ctrl+C to stop (but why would you?)")
        print()
        
        # Main monitoring loop - NEVER STOPS
        try:
            while self.running:
                self.check_agents()
                time.sleep(self.check_interval)
        except KeyboardInterrupt:
            print("\n🛑 Shutting down...")
            self.shutdown()
    
    def shutdown(self):
        """Shutdown all agents"""
        print("Stopping all agents...")
        for agent in self.agents:
            try:
                process = agent['process']
                os.killpg(os.getpgid(process.pid), signal.SIGTERM)
                print(f"   Stopped {agent['name']}")
            except:
                pass
        self.running = False


if __name__ == "__main__":
    manager = PersistentAgentManager()
    manager.run()
