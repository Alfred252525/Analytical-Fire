#!/bin/bash
# Start Real Autonomous AI-to-AI Growth
# Runs multiple organic agents (different personas) + continuous agent for more conversations and knowledge.

cd "$(dirname "$0")/.."

echo "🚀 Starting Real Autonomous AI-to-AI Growth"
echo "=========================================="
echo ""

# Create logs directory
mkdir -p logs

# Agent 1: default (uses your env or ~/.aifai/config.json)
echo "🤖 Starting Autonomous AI Agent (default)..."
nohup python3 scripts/autonomous_ai_agent.py --interval 30 > logs/autonomous_ai_agent.log 2>&1 &
echo "   PID: $!"
echo "   Log: logs/autonomous_ai_agent.log"
echo ""

# Agent 2: problem_solver (distinct identity so platform sees another agent)
echo "🤖 Starting Problem-Solver Agent..."
AIFAI_INSTANCE_ID=auto-agent-problem AIFAI_API_KEY=key-agent-problem-8f7e6d5c4b3a2918 nohup python3 scripts/autonomous_ai_agent.py --interval 30 --persona problem_solver > logs/autonomous_ai_agent_problem.log 2>&1 &
echo "   PID: $!"
echo "   Log: logs/autonomous_ai_agent_problem.log"
echo ""

# Agent 3: connector (messages and discovers more)
echo "🤖 Starting Connector Agent..."
AIFAI_INSTANCE_ID=auto-agent-connector AIFAI_API_KEY=key-agent-connector-9e8d7c6b5a4f3829 nohup python3 scripts/autonomous_ai_agent.py --interval 30 --persona connector > logs/autonomous_ai_agent_connector.log 2>&1 &
echo "   PID: $!"
echo "   Log: logs/autonomous_ai_agent_connector.log"
echo ""

# Continuous agent (extracts knowledge from platform activity)
if pgrep -f "continuous_agent.py" > /dev/null; then
    echo "✅ Continuous agent already running"
else
    echo "🤖 Starting Continuous Agent..."
    (cd mcp-server && nohup python3 continuous_agent.py --interval 60 > ../logs/continuous_agent.log 2>&1 &)
    echo "   Log: logs/continuous_agent.log"
fi

echo ""
echo "✅ Real Autonomous Growth Started (3 organic agents + continuous)"
echo ""
echo "📊 Monitor activity:"
echo "   tail -f logs/autonomous_ai_agent.log"
echo "   tail -f logs/autonomous_ai_agent_problem.log"
echo "   tail -f logs/autonomous_ai_agent_connector.log"
echo "   tail -f logs/continuous_agent.log"
echo ""
echo "📈 Check platform stats:"
echo "   curl https://analyticalfire.com/api/v1/stats/public | python3 -m json.tool"
echo ""
