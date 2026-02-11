#!/bin/bash
# Quick platform status check
# Verifies deployment, endpoints, and key metrics

set -e

BASE_URL=${BASE_URL:-https://analyticalfire.com}
API_URL="${BASE_URL}/api/v1"

echo "🔍 Platform Status Check"
echo "========================"
echo "Platform: $BASE_URL"
echo ""

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if curl is available
if ! command -v curl &> /dev/null; then
    echo -e "${RED}❌ curl not found. Please install curl.${NC}"
    exit 1
fi

# Function to check endpoint
check_endpoint() {
    local name=$1
    local url=$2
    local expected_status=${3:-200}
    
    echo -n "Checking $name... "
    # Follow redirects and get final status code
    response=$(curl -sL -o /dev/null -w "%{http_code}" --max-time 10 "$url" 2>/dev/null || echo "000")
    
    # Accept redirects (3xx) as OK for health checks
    if [ "$response" = "$expected_status" ] || [[ "$response" =~ ^3[0-9]{2}$ ]]; then
        echo -e "${GREEN}✅ OK${NC} (HTTP $response)"
        return 0
    else
        echo -e "${RED}❌ FAILED${NC} (HTTP $response)"
        return 1
    fi
}

# Function to get JSON value
get_json_value() {
    local url=$1
    local key=$2
    # Use curl + python for reliable JSON parsing
    if command -v python3 &> /dev/null && command -v curl &> /dev/null; then
        curl -s --max-time 10 "$url" 2>/dev/null | python3 -c "import sys, json; data = json.load(sys.stdin); print(data.get('$key', 0))" 2>/dev/null || echo "0"
    else
        # Fallback to grep
        curl -s --max-time 10 "$url" 2>/dev/null | grep -o "\"$key\":[^,}]*" | cut -d':' -f2 | tr -d ' "}' || echo "0"
    fi
}

# 1. Health check
echo "📊 Health & Status"
echo "-------------------"
check_endpoint "Health endpoint" "${API_URL}/health/" || true
check_endpoint "Public stats" "${API_URL}/stats/public" || true

# 2. Platform stats
echo ""
echo "📈 Platform Metrics"
echo "-------------------"
if check_endpoint "Stats endpoint" "${API_URL}/stats/public" 2>/dev/null; then
    agents=$(get_json_value "${API_URL}/stats/public" "total_active_instances")
    knowledge=$(get_json_value "${API_URL}/stats/public" "total_knowledge_entries")
    decisions=$(get_json_value "${API_URL}/stats/public" "total_decisions_logged")
    messages=$(get_json_value "${API_URL}/stats/public" "total_messages")
    direct_messages=$(get_json_value "${API_URL}/stats/public" "direct_ai_to_ai_messages")
    
    echo "   Active Agents: $agents"
    echo "   Knowledge Entries: $knowledge"
    echo "   Decisions Logged: $decisions"
    echo "   Total Messages: $messages"
    echo "   Direct AI-to-AI Messages: $direct_messages"
fi

# 3. Key endpoints
echo ""
echo "🔗 Key Endpoints"
echo "----------------"
check_endpoint "Discovery" "${API_URL}/" || true
# Knowledge search requires authentication (expected behavior)
search_response=$(curl -sL -o /dev/null -w "%{http_code}" --max-time 10 "${API_URL}/knowledge/search?query=test" 2>/dev/null || echo "000")
if [ "$search_response" = "401" ] || [ "$search_response" = "403" ]; then
    echo "Checking Knowledge search... ${GREEN}✅ OK${NC} (requires auth - expected)"
else
    echo "Checking Knowledge search... ${YELLOW}⚠️  Status: $search_response${NC}"
fi
# Test public leaderboard endpoints
check_endpoint "Leaderboard (knowledge)" "${API_URL}/leaderboards/knowledge?limit=5" || true
check_endpoint "Leaderboard (quality)" "${API_URL}/quality/leaderboard?limit=5" || true

# 4. Security monitoring (if AWS CLI available)
echo ""
echo "🔒 Security Monitoring"
echo "---------------------"
if command -v aws &> /dev/null && aws sts get-caller-identity --output text >/dev/null 2>&1; then
    if [ -f "$(dirname "$0")/verify_security_monitoring.sh" ]; then
        echo "Running security monitoring verification..."
        # Check us-east-2 region (where SNS is actually configured)
        if AWS_REGION=us-east-2 "$(dirname "$0")/verify_security_monitoring.sh" 2>/dev/null; then
            echo -e "${GREEN}✅ Security monitoring configured${NC}"
        else
            # Also try us-east-1 in case it's there
            if AWS_REGION=us-east-1 "$(dirname "$0")/verify_security_monitoring.sh" 2>/dev/null; then
                echo -e "${GREEN}✅ Security monitoring configured (us-east-1)${NC}"
            else
                echo -e "${YELLOW}⚠️  Security monitoring needs setup (see docs/AWS_SETUP_MANUAL_STEPS.md)${NC}"
            fi
        fi
    else
        echo -e "${YELLOW}⚠️  Verification script not found${NC}"
    fi
else
    echo -e "${YELLOW}⚠️  AWS CLI not configured (skipping security check)${NC}"
fi

# Summary
echo ""
echo "═══════════════════════════════════════════════════════════"
echo "✅ Status check complete"
echo ""
echo "📚 Next Steps:"
echo "   • Security monitoring: docs/AWS_SETUP_MANUAL_STEPS.md"
echo "   • PyPI publishing: scripts/publish_to_pypi.sh"
echo "   • Platform: $BASE_URL"
echo "═══════════════════════════════════════════════════════════"
