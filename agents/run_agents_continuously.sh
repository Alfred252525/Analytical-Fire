#!/bin/bash

# Run organic agents continuously in background
# This script starts multiple agents that will run autonomously

cd "$(dirname "$0")/.."

echo "🚀 Starting organic agents continuously..."
echo ""

# Create log directory
mkdir -p logs

# Function to start an agent in background
start_agent() {
    local agent_id=$1
    local agent_name=$2
    local interval=$3
    
    echo "Starting: $agent_name (interval: ${interval}m)"
    
    nohup python3 agents/organic_agent.py \
        --agent-id "$agent_id" \
        --agent-name "$agent_name" \
        --api-key "$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')" \
        --interval "$interval" \
        > "logs/${agent_id}.log" 2>&1 &
    
    echo $! > "logs/${agent_id}.pid"
    echo "  ✅ Started (PID: $(cat logs/${agent_id}.pid))"
    sleep 2
}

# Start multiple agents with different intervals
start_agent "continuous-agent-001" "Continuous Agent Alpha" 30
start_agent "continuous-agent-002" "Continuous Agent Beta" 45
start_agent "continuous-agent-003" "Continuous Agent Gamma" 60
start_agent "continuous-agent-004" "Continuous Agent Delta" 90

echo ""
echo "✅ All agents started!"
echo ""
echo "To check status:"
echo "  ps aux | grep organic_agent"
echo ""
echo "To stop agents:"
echo "  pkill -f organic_agent"
echo ""
echo "To view logs:"
echo "  tail -f logs/*.log"
