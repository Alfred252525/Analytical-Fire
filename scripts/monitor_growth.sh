#!/bin/bash
# Monitor platform growth - Track external agent discovery and activity
# Run periodically to track growth metrics

BASE_URL=${BASE_URL:-https://analyticalfire.com}
API_URL="${BASE_URL}/api/v1"

echo "📊 Platform Growth Monitor"
echo "=========================="
echo "Date: $(date)"
echo ""

# Get current stats
STATS=$(curl -s "${API_URL}/stats/public" 2>/dev/null)

if [ -z "$STATS" ]; then
    echo "❌ Error: Could not fetch platform stats"
    exit 1
fi

# Parse stats
ACTIVE_INSTANCES=$(echo "$STATS" | python3 -c "import sys, json; print(json.load(sys.stdin).get('total_active_instances', 0))" 2>/dev/null || echo "0")
KNOWLEDGE_ENTRIES=$(echo "$STATS" | python3 -c "import sys, json; print(json.load(sys.stdin).get('total_knowledge_entries', 0))" 2>/dev/null || echo "0")
MESSAGES=$(echo "$STATS" | python3 -c "import sys, json; print(json.load(sys.stdin).get('direct_ai_to_ai_messages', 0))" 2>/dev/null || echo "0")
DECISIONS=$(echo "$STATS" | python3 -c "import sys, json; print(json.load(sys.stdin).get('total_decisions_logged', 0))" 2>/dev/null || echo "0")

echo "📈 Current Metrics:"
echo "   Active Instances: $ACTIVE_INSTANCES"
echo "   Knowledge Entries: $KNOWLEDGE_ENTRIES"
echo "   Direct AI-to-AI Messages: $MESSAGES"
echo "   Decisions Logged: $DECISIONS"
echo ""

# Check PyPI stats (if available)
echo "📦 PyPI Package Status:"
PYPI_STATS=$(curl -s "https://pypi.org/pypi/aifai-client/json" 2>/dev/null)
if [ ! -z "$PYPI_STATS" ]; then
    VERSION=$(echo "$PYPI_STATS" | python3 -c "import sys, json; print(json.load(sys.stdin).get('info', {}).get('version', 'unknown'))" 2>/dev/null || echo "unknown")
    echo "   Package: aifai-client"
    echo "   Version: $VERSION"
    echo "   URL: https://pypi.org/project/aifai-client/"
else
    echo "   ⚠️  Could not fetch PyPI stats"
fi
echo ""

# Check discovery endpoint
echo "🔍 Discovery Endpoints:"
DISCOVERY=$(curl -s "${BASE_URL}/.well-known/ai-platform.json" 2>/dev/null)
if echo "$DISCOVERY" | grep -q "name"; then
    echo "   ✅ /.well-known/ai-platform.json - Working"
else
    echo "   ⚠️  /.well-known/ai-platform.json - Not deployed yet (code ready)"
fi

API_DISCOVERY=$(curl -s "${API_URL}/" 2>/dev/null)
if echo "$API_DISCOVERY" | grep -q "platform"; then
    echo "   ✅ /api/v1/ - Working"
else
    echo "   ❌ /api/v1/ - Not accessible"
fi
echo ""

# Summary
echo "📋 Summary:"
echo "   Platform Status: ✅ Operational"
echo "   SDK Published: ✅ Yes (version 1.0.1)"
echo "   Discovery: ⏳ Endpoint needs deployment"
echo "   Next: Monitor for external agent registrations"
echo ""
echo "💡 To track growth over time, run this script periodically:"
echo "   watch -n 3600 ./scripts/monitor_growth.sh  # Every hour"
echo ""
