#!/bin/bash
# Test script for LM Studio MCP Proxy (Phase 106h)
# Tests all endpoints and basic functionality

set -e

PROXY_URL="http://localhost:5004"
MCP_URL="http://localhost:5002"

echo "=================================================="
echo "  LM Studio MCP Proxy Test Suite (Phase 106h)"
echo "=================================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test counter
TESTS_RUN=0
TESTS_PASSED=0
TESTS_FAILED=0

# Test function
test_endpoint() {
    local name="$1"
    local method="$2"
    local url="$3"
    local data="$4"
    local expected_status="$5"

    TESTS_RUN=$((TESTS_RUN + 1))
    echo -n "Test $TESTS_RUN: $name ... "

    if [ -z "$data" ]; then
        response=$(curl -s -w "\n%{http_code}" -X "$method" "$url")
    else
        response=$(curl -s -w "\n%{http_code}" -X "$method" "$url" \
            -H "Content-Type: application/json" \
            -d "$data")
    fi

    # Extract status code (last line)
    status=$(echo "$response" | tail -n1)
    body=$(echo "$response" | head -n-1)

    if [ "$status" = "$expected_status" ]; then
        echo -e "${GREEN}PASS${NC} (HTTP $status)"
        TESTS_PASSED=$((TESTS_PASSED + 1))
        return 0
    else
        echo -e "${RED}FAIL${NC} (Expected HTTP $expected_status, got $status)"
        echo "Response: $body"
        TESTS_FAILED=$((TESTS_FAILED + 1))
        return 1
    fi
}

# Prerequisite checks
echo "=== Prerequisite Checks ==="
echo ""

echo -n "Checking MCP server (port 5002) ... "
if curl -s -f "$MCP_URL/health" > /dev/null 2>&1; then
    echo -e "${GREEN}OK${NC}"
else
    echo -e "${YELLOW}WARNING${NC} - MCP server not running"
    echo "Start with: python src/mcp/vetka_mcp_server.py --http --port 5002"
fi

echo -n "Checking proxy server (port 5004) ... "
if curl -s -f "$PROXY_URL/health" > /dev/null 2>&1; then
    echo -e "${GREEN}OK${NC}"
else
    echo -e "${RED}FAIL${NC} - Proxy not running"
    echo "Start with: python src/mcp/lmstudio_proxy.py"
    exit 1
fi

echo -n "Checking LM Studio (port 1234) ... "
if curl -s -f "http://localhost:1234/v1/models" > /dev/null 2>&1; then
    echo -e "${GREEN}OK${NC}"
else
    echo -e "${YELLOW}WARNING${NC} - LM Studio not running"
    echo "Optional: Start LM Studio and load a model"
fi

echo ""
echo "=== Running Tests ==="
echo ""

# Test 1: Root endpoint
test_endpoint \
    "Root endpoint" \
    "GET" \
    "$PROXY_URL/" \
    "" \
    "200"

# Test 2: Health check
test_endpoint \
    "Health check" \
    "GET" \
    "$PROXY_URL/health" \
    "" \
    "200"

# Test 3: Warp config generation
test_endpoint \
    "Warp config generation" \
    "GET" \
    "$PROXY_URL/warp/config" \
    "" \
    "200"

# Test 4: Model list (forwarded to LM Studio)
test_endpoint \
    "Model list (forwarded)" \
    "GET" \
    "$PROXY_URL/v1/models" \
    "" \
    "200"

# Test 5: Chat completion with tools (requires MCP)
test_endpoint \
    "Chat completion request" \
    "POST" \
    "$PROXY_URL/v1/chat/completions" \
    '{
        "model": "test-model",
        "messages": [
            {"role": "user", "content": "Hello"}
        ],
        "max_tokens": 10
    }' \
    "200"

echo ""
echo "=== Test Summary ==="
echo "Tests run:    $TESTS_RUN"
echo -e "Tests passed: ${GREEN}$TESTS_PASSED${NC}"
if [ $TESTS_FAILED -gt 0 ]; then
    echo -e "Tests failed: ${RED}$TESTS_FAILED${NC}"
else
    echo -e "Tests failed: ${GREEN}0${NC}"
fi
echo ""

if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "${GREEN}✓ All tests passed!${NC}"
    exit 0
else
    echo -e "${RED}✗ Some tests failed${NC}"
    exit 1
fi
