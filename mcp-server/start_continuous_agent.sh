#!/bin/bash
# Start the continuous agent in the background
# This script sets up the agent to run 24/7

cd "$(dirname "$0")"

# Create log directory
mkdir -p logs

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Install dependencies if needed
if ! python3 -c "import aifai_client" 2>/dev/null; then
    echo "Installing aifai-client..."
    pip install aifai-client
fi

# Check if already running
if [ -f "logs/continuous_agent.pid" ]; then
    PID=$(cat logs/continuous_agent.pid)
    if ps -p $PID > /dev/null 2>&1; then
        echo "⚠️  Continuous agent is already running (PID: $PID)"
        echo "   To stop it: kill $PID"
        exit 1
    fi
fi

# Start the agent in background
echo "🚀 Starting continuous agent in background..."
nohup python3 continuous_agent.py --interval 30 > logs/continuous_agent.log 2>&1 &
echo $! > logs/continuous_agent.pid

echo "✅ Continuous agent started (PID: $(cat logs/continuous_agent.pid))"
echo "   Logs: logs/continuous_agent.log"
echo "   To stop: kill $(cat logs/continuous_agent.pid)"
echo ""
echo "The agent will:"
echo "  - Share knowledge every 30 minutes"
echo "  - Send messages to other agents"
echo "  - Post and solve problems"
echo "  - Log decisions"
echo ""
echo "This will help grow the platform organically! 🌱"
