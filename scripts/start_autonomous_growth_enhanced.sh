#!/bin/bash
# Enhanced Autonomous Growth - Scale up to 10+ agents with diverse personas
# Uses intelligent matching and proactive engagement for better conversations

cd "$(dirname "$0")/.."

echo "🚀 Starting Enhanced Autonomous AI-to-AI Growth"
echo "================================================"
echo ""

# Create logs directory
mkdir -p logs

# Generate unique instance IDs and API keys for each agent
generate_id() {
    echo "auto-agent-$(date +%s)-$RANDOM"
}

generate_key() {
    echo "key-$(openssl rand -hex 16)"
}

# Agent personas available: default, problem_solver, knowledge_sharer, connector
PERSONAS=("default" "problem_solver" "knowledge_sharer" "connector")

# Start 10 agents (2-3 of each persona for diversity)
AGENT_COUNT=0
MAX_AGENTS=10

echo "🤖 Starting $MAX_AGENTS agents with diverse personas..."
echo ""

# Start 2-3 agents of each persona type
for persona in "${PERSONAS[@]}"; do
    for i in {1..3}; do
        if [ $AGENT_COUNT -ge $MAX_AGENTS ]; then
            break 2
        fi
        
        INSTANCE_ID=$(generate_id)
        API_KEY=$(generate_key)
        
        # Create unique name based on persona
        case $persona in
            "problem_solver")
                NAME_SUFFIX="Problem-Solver"
                ;;
            "knowledge_sharer")
                NAME_SUFFIX="Knowledge-Sharer"
                ;;
            "connector")
                NAME_SUFFIX="Connector"
                ;;
            *)
                NAME_SUFFIX="Autonomous"
                ;;
        esac
        
        echo "🤖 Starting $NAME_SUFFIX Agent #$i (persona: $persona)..."
        echo "   Instance ID: $INSTANCE_ID"
        
        AIFAI_INSTANCE_ID=$INSTANCE_ID \
        AIFAI_API_KEY=$API_KEY \
        nohup python3 scripts/autonomous_ai_agent.py \
            --interval 30 \
            --persona $persona \
            > logs/autonomous_ai_agent_${persona}_${i}.log 2>&1 &
        
        echo "   PID: $!"
        echo "   Log: logs/autonomous_ai_agent_${persona}_${i}.log"
        echo ""
        
        AGENT_COUNT=$((AGENT_COUNT + 1))
        
        # Small delay to avoid race conditions
        sleep 1
    done
done

# Continuous agent (extracts knowledge from platform activity)
if pgrep -f "continuous_agent.py" > /dev/null; then
    echo "✅ Continuous agent already running"
else
    echo "🤖 Starting Continuous Agent..."
    (cd mcp-server && nohup python3 continuous_agent.py --interval 60 > ../logs/continuous_agent.log 2>&1 &)
    echo "   Log: logs/continuous_agent.log"
fi

echo ""
echo "✅ Enhanced Autonomous Growth Started"
echo "   - $AGENT_COUNT organic agents (diverse personas)"
echo "   - 1 continuous agent (knowledge extraction)"
echo "   - Total: $((AGENT_COUNT + 1)) agents"
echo ""
echo "📊 Monitor activity:"
echo "   tail -f logs/autonomous_ai_agent_*.log"
echo "   tail -f logs/continuous_agent.log"
echo ""
echo "📈 Check platform stats:"
echo "   curl https://analyticalfire.com/api/v1/stats/public | python3 -m json.tool"
echo ""
echo "🔍 Check agent engagement:"
echo "   curl https://analyticalfire.com/api/v1/activity/engagement-opportunities | python3 -m json.tool"
echo ""
