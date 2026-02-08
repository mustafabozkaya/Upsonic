#!/bin/bash
# Quick test script for Docker deployment

echo "🧪 Docker Deployment Test"
echo "========================"
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Test function
test_service() {
    local name=$1
    local url=$2
    local expected_code=${3:-200}
    
    echo -n "Testing $name... "
    response=$(curl -s -o /dev/null -w "%{http_code}" "$url" 2>/dev/null)
    
    if [ "$response" = "$expected_code" ]; then
        echo -e "${GREEN}✅ OK${NC} (HTTP $response)"
        return 0
    else
        echo -e "${RED}❌ FAIL${NC} (HTTP $response, expected $expected_code)"
        return 1
    fi
}

# Test Ollama
echo "1️⃣  Ollama (Host)"
test_service "Ollama API" "http://localhost:11434/api/tags"

# Test Gateway API
echo ""
echo "2️⃣  Gateway API"
test_service "Health Check" "http://localhost:8000/health"

# Test Simple API
echo ""
echo "3️⃣  Simple API"
test_service "Health Check" "http://localhost:8001/health"

# Test Gateway Chat
echo ""
echo "4️⃣  Gateway Chat Endpoint"
response=$(curl -s -X POST "http://localhost:8000/chat" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer dev-key-change-in-production" \
    -d '{"message":"test","user_id":"test"}' \
    -w "%{http_code}" \
    -o /tmp/gateway_response.json 2>/dev/null)

if [ "$response" = "200" ]; then
    echo -e "${GREEN}✅ Chat OK${NC} (HTTP $response)"
    echo "   Response: $(cat /tmp/gateway_response.json | grep -o '"message":"[^"]*"' | cut -d'"' -f4 | head -c 50)"
else
    echo -e "${RED}❌ Chat FAIL${NC} (HTTP $response)"
fi

# Test Simple API Query
echo ""
echo "5️⃣  Simple API Query Endpoint"
response=$(curl -s -X POST "http://localhost:8001/query" \
    -H "Content-Type: application/json" \
    -d '{"user_query":"test","model":"ollama/qwen2.5:7b"}' \
    -w "%{http_code}" \
    -o /tmp/simple_response.json 2>/dev/null)

if [ "$response" = "200" ]; then
    echo -e "${GREEN}✅ Query OK${NC} (HTTP $response)"
else
    echo -e "${RED}❌ Query FAIL${NC} (HTTP $response)"
fi

echo ""
echo "========================"
echo "🎯 Test tamamlandı!"
echo ""
echo "📊 Servisler:"
echo "   Gateway API:  http://localhost:8000/docs"
echo "   Simple API:   http://localhost:8001/docs"
echo "   Streamlit:    http://localhost:8501"
echo "   Gateway UI:   http://localhost:8502"
