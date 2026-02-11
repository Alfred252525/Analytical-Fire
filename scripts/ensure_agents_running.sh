#!/bin/bash
# Ensure autonomous agents are running - restart if they're not
# This prevents growth from stalling if agents crash or are stopped

cd "$(dirname "$0")/.."

# Check if agents are running
DEFAULT_RUNNING=$(pgrep -f "autonomous_ai_agent.py --interval 30$" | wc -l | tr -d ' ')
PROBLEM_RUNNING=$(pgrep -f "autonomous_ai_agent.py --interval 30 --persona problem_solver" | wc -l | tr -d ' ')
CONNECTOR_RUNNING=$(pgrep -f "autonomous_ai_agent.py --interval 30 --persona connector" | wc -l | tr -d ' ')
CONTINUOUS_RUNNING=$(pgrep -f "continuous_agent.py" | wc -l | tr -d ' ')

RESTARTED=false

# Restart default agent if not running
if [ "$DEFAULT_RUNNING" -eq 0 ]; then
    echo "⚠️  Default agent not running, restarting..."
    nohup python3 scripts/autonomous_ai_agent.py --interval 30 > logs/autonomous_ai_agent.log 2>&1 &
    RESTARTED=true
fi

# Restart problem_solver agent if not running
if [ "$PROBLEM_RUNNING" -eq 0 ]; then
    echo "⚠️  Problem-solver agent not running, restarting..."
    AIFAI_INSTANCE_ID=auto-agent-problem AIFAI_API_KEY=key-agent-problem-8f7e6d5c4b3a2918 nohup python3 scripts/autonomous_ai_agent.py --interval 30 --persona problem_solver > logs/autonomous_ai_agent_problem.log 2>&1 &
    RESTARTED=true
fi

# Restart connector agent if not running
if [ "$CONNECTOR_RUNNING" -eq 0 ]; then
    echo "⚠️  Connector agent not running, restarting..."
    AIFAI_INSTANCE_ID=auto-agent-connector AIFAI_API_KEY=key-agent-connector-9e8d7c6b5a4f3829 nohup python3 scripts/autonomous_ai_agent.py --interval 30 --persona connector > logs/autonomous_ai_agent_connector.log 2>&1 &
    RESTARTED=true
fi

# Restart continuous agent if not running
if [ "$CONTINUOUS_RUNNING" -eq 0 ]; then
    echo "⚠️  Continuous agent not running, restarting..."
    (cd mcp-server && nohup python3 continuous_agent.py --interval 60 > ../logs/continuous_agent.log 2>&1 &)
    RESTARTED=true
fi

if [ "$RESTARTED" = true ]; then
    echo "✅ Restarted stopped agents"
else
    echo "✅ All agents running (default: $DEFAULT_RUNNING, problem: $PROBLEM_RUNNING, connector: $CONNECTOR_RUNNING, continuous: $CONTINUOUS_RUNNING)"
fi
