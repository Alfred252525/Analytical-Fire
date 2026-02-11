#!/bin/bash
# Verify discovery endpoint is accessible after deployment

BASE_URL=${BASE_URL:-https://analyticalfire.com}
DISCOVERY_URL="${BASE_URL}/.well-known/ai-platform.json"

echo "🔍 Verifying Discovery Endpoint"
echo "================================"
echo "URL: $DISCOVERY_URL"
echo ""

response=$(curl -sL -w "\n%{http_code}" "$DISCOVERY_URL" 2>/dev/null)
http_code=$(echo "$response" | tail -n1)
body=$(echo "$response" | sed '$d')

if [ "$http_code" = "200" ]; then
    echo "✅ Status: HTTP $http_code - ACCESSIBLE"
    echo ""
    echo "Response preview:"
    echo "$body" | python3 -m json.tool 2>/dev/null | head -20 || echo "$body" | head -10
    echo ""
    
    # Check if it's valid JSON
    if echo "$body" | python3 -m json.tool >/dev/null 2>&1; then
        echo "✅ Valid JSON response"
        
        # Check for key fields
        if echo "$body" | grep -q '"name"'; then
            echo "✅ Contains 'name' field"
        fi
        if echo "$body" | grep -q '"discovery"'; then
            echo "✅ Contains 'discovery' field"
        fi
        if echo "$body" | grep -q '"sdk"'; then
            echo "✅ Contains 'sdk' field"
        fi
    else
        echo "⚠️  Response is not valid JSON"
    fi
else
    echo "❌ Status: HTTP $http_code - NOT ACCESSIBLE"
    echo ""
    echo "Response:"
    echo "$body" | head -5
    echo ""
    echo "⚠️  Discovery endpoint needs to be deployed or fixed"
fi

echo ""
echo "========================================"
