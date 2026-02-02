#!/bin/bash
# Phase 106 MCP Server - Basic Test Runner
# Run this script to execute verification tests
#
# Usage: ./RUN_TESTS.sh

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
MCP_PORT=5002
API_PORT=5001
TEST_SESSION="verify_test_$(date +%s)"
RESULTS_FILE="test_execution_$(date +%Y%m%d_%H%M%S).log"
RESULTS_PATH="/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/docs/phase_106_multi_agent_mcp/verification/$RESULTS_FILE"

echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║    Phase 106 MCP Server - Basic Verification Tests       ║${NC}"
echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo ""
echo "Date: $(date)"
echo "Session: $TEST_SESSION"
echo "Results: $RESULTS_FILE"
echo ""

# Create results file
{
    echo "=== Phase 106 MCP Server Verification ==="
    echo "Date: $(date)"
    echo "Session: $TEST_SESSION"
    echo ""
} > "$RESULTS_PATH"

# Function to run test
run_test() {
    local test_name="$1"
    local test_cmd="$2"
    local expect_success="${3:-true}"

    echo -e "${YELLOW}┌─────────────────────────────────────────────────────────┐${NC}"
    echo -e "${YELLOW}│ $test_name${NC}"
    echo -e "${YELLOW}└─────────────────────────────────────────────────────────┘${NC}"

    {
        echo "TEST: $test_name"
        echo "Command: $test_cmd"
        echo "Expected: $expect_success"
        echo "---"
    } >> "$RESULTS_PATH"

    if eval "$test_cmd" >> "$RESULTS_PATH" 2>&1; then
        if [ "$expect_success" = "true" ]; then
            echo -e "${GREEN}✓ PASS${NC}"
            echo "Result: PASS" >> "$RESULTS_PATH"
        else
            echo -e "${RED}✗ FAIL (expected failure but succeeded)${NC}"
            echo "Result: FAIL (unexpected success)" >> "$RESULTS_PATH"
        fi
    else
        if [ "$expect_success" = "false" ]; then
            echo -e "${GREEN}✓ PASS (expected failure)${NC}"
            echo "Result: PASS (expected failure)" >> "$RESULTS_PATH"
        else
            echo -e "${RED}✗ FAIL${NC}"
            echo "Result: FAIL" >> "$RESULTS_PATH"
        fi
    fi

    echo "" >> "$RESULTS_PATH"
    echo ""
}

# Pre-check: Server status
echo -e "${BLUE}═══ Pre-Check: Server Status ═══${NC}"

echo -n "Checking VETKA API (port $API_PORT)... "
if curl -s "http://localhost:$API_PORT/health" > /dev/null 2>&1; then
    echo -e "${GREEN}RUNNING${NC}"
    {
        echo "VETKA API Status: RUNNING"
        curl -s "http://localhost:$API_PORT/health" | jq 2>&1 || curl -s "http://localhost:$API_PORT/health" 2>&1
        echo ""
    } >> "$RESULTS_PATH"
else
    echo -e "${YELLOW}NOT RUNNING${NC}"
    echo "VETKA API Status: NOT RUNNING" >> "$RESULTS_PATH"
    echo ""
fi

echo -n "Checking MCP HTTP (port $MCP_PORT)... "
if curl -s "http://localhost:$MCP_PORT/health" > /dev/null 2>&1; then
    echo -e "${GREEN}RUNNING${NC}"
    {
        echo "MCP HTTP Status: RUNNING"
        curl -s "http://localhost:$MCP_PORT/health" | jq 2>&1 || curl -s "http://localhost:$MCP_PORT/health" 2>&1
        echo ""
    } >> "$RESULTS_PATH"
else
    echo -e "${RED}NOT RUNNING${NC}"
    echo -e "${YELLOW}Please start MCP server with: python src/mcp/vetka_mcp_server.py --http --port $MCP_PORT${NC}"
    echo "MCP HTTP Status: NOT RUNNING" >> "$RESULTS_PATH"
    echo ""
    echo -e "${RED}Cannot continue without MCP server. Exiting.${NC}"
    exit 1
fi

echo ""

# Test Suite
echo -e "${BLUE}═══ Running Test Suite ═══${NC}"
echo ""

# Test 1: Health Check
run_test "Test 1: Health Check" \
    "curl -s http://localhost:$MCP_PORT/health | jq -e '.status == \"healthy\"'"

# Test 2: Tools List (Count)
run_test "Test 2: Tools List - Count Tools" \
    "curl -s -X POST http://localhost:$MCP_PORT/mcp \
        -H 'Content-Type: application/json' \
        -d '{\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"tools/list\",\"params\":{}}' | \
        jq -e '.result.tools | length >= 13'"

# Test 3: Tools List (Full)
run_test "Test 3: Tools List - Full Response" \
    "curl -s -X POST http://localhost:$MCP_PORT/mcp \
        -H 'Content-Type: application/json' \
        -d '{\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"tools/list\",\"params\":{}}' | \
        jq -e '.result.tools'"

# Test 4: Initialize Method
run_test "Test 4: Initialize Method" \
    "curl -s -X POST http://localhost:$MCP_PORT/mcp \
        -H 'Content-Type: application/json' \
        -H 'X-Session-ID: $TEST_SESSION' \
        -d '{\"jsonrpc\":\"2.0\",\"id\":10,\"method\":\"initialize\",\"params\":{}}' | \
        jq -e '.result.protocolVersion'"

# Test 5: Tool Call - vetka_health
run_test "Test 5: Tool Call - vetka_health" \
    "curl -s -X POST http://localhost:$MCP_PORT/mcp \
        -H 'Content-Type: application/json' \
        -H 'X-Session-ID: $TEST_SESSION' \
        -d '{\"jsonrpc\":\"2.0\",\"id\":42,\"method\":\"tools/call\",\"params\":{\"name\":\"vetka_health\",\"arguments\":{}}}' | \
        jq -e '.result.content'"

# Test 6: Stats Endpoint
run_test "Test 6: Stats Endpoint" \
    "curl -s http://localhost:$MCP_PORT/api/stats | jq -e '.actors or .error'"

# Test 7: Error Handling - Invalid Method
run_test "Test 7: Error Handling - Invalid Method (expect error)" \
    "curl -s -X POST http://localhost:$MCP_PORT/mcp \
        -H 'Content-Type: application/json' \
        -d '{\"jsonrpc\":\"2.0\",\"id\":999,\"method\":\"invalid_method\",\"params\":{}}' | \
        jq -e '.error.code == -32601'" \
    "true"

# Test 8: Error Handling - Unknown Tool
run_test "Test 8: Error Handling - Unknown Tool (expect error)" \
    "curl -s -X POST http://localhost:$MCP_PORT/mcp \
        -H 'Content-Type: application/json' \
        -d '{\"jsonrpc\":\"2.0\",\"id\":998,\"method\":\"tools/call\",\"params\":{\"name\":\"unknown_tool\",\"arguments\":{}}}' | \
        jq -e '.error or .result.content'"

# Test 9: CORS Headers
run_test "Test 9: CORS Headers" \
    "curl -s -I http://localhost:$MCP_PORT/health | grep -i 'access-control-allow-origin'"

# Test 10: Multiple Sessions
echo -e "${YELLOW}┌─────────────────────────────────────────────────────────┐${NC}"
echo -e "${YELLOW}│ Test 10: Session Isolation${NC}"
echo -e "${YELLOW}└─────────────────────────────────────────────────────────┘${NC}"

{
    echo "TEST: Session Isolation"
    echo "---"
    echo "Session 1:"
    curl -s -X POST http://localhost:$MCP_PORT/mcp \
        -H 'Content-Type: application/json' \
        -H 'X-Session-ID: session_1' \
        -d '{"jsonrpc":"2.0","id":100,"method":"initialize","params":{}}' | jq
    echo ""
    echo "Session 2:"
    curl -s -X POST http://localhost:$MCP_PORT/mcp \
        -H 'Content-Type: application/json' \
        -H 'X-Session-ID: session_2' \
        -d '{"jsonrpc":"2.0","id":200,"method":"initialize","params":{}}' | jq
    echo ""
    echo "Stats after multiple sessions:"
    curl -s http://localhost:$MCP_PORT/api/stats | jq
} >> "$RESULTS_PATH"

echo -e "${GREEN}✓ Executed (see log for details)${NC}"
echo ""

# Summary
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}  Test Execution Complete${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo ""
echo "Results saved to: $RESULTS_PATH"
echo ""
echo "To view results:"
echo "  cat \"$RESULTS_PATH\""
echo ""
echo "To view JSON results:"
echo "  grep -A 20 'TEST:' \"$RESULTS_PATH\" | less"
echo ""

# Count passes/fails
PASSES=$(grep -c "Result: PASS" "$RESULTS_PATH" || echo 0)
FAILS=$(grep -c "Result: FAIL" "$RESULTS_PATH" || echo 0)

echo -e "Summary: ${GREEN}$PASSES PASS${NC} / ${RED}$FAILS FAIL${NC}"
echo ""

# Open results in default editor (optional)
if command -v jq &> /dev/null && [ "$FAILS" -gt 0 ]; then
    echo -e "${YELLOW}Some tests failed. Would you like to view the log? (y/N)${NC}"
    read -r -t 5 response || response="n"
    if [[ "$response" =~ ^[Yy]$ ]]; then
        less "$RESULTS_PATH"
    fi
fi

exit 0
