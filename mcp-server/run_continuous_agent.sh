#!/bin/bash
# Run the continuous MCP agent 24/7

cd "$(dirname "$0")"

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Install dependencies if needed
if ! python3 -c "import aifai_client" 2>/dev/null; then
    echo "Installing aifai-client..."
    pip install aifai-client
fi

# Run the agent (every 60 minutes by default)
# Adjust interval with --interval flag (in minutes)
python3 continuous_agent.py --interval 60
