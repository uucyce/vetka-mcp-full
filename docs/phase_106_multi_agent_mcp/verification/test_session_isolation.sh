#!/bin/bash
# Phase 106 MCP Server - Session Isolation Test Suite
# Run this script after starting the MCP server on port 5002

set -e

BASE_URL="http://localhost:5002"
PASSED=0
FAILED=0

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Helper functions
pass() {
    echo -e "${GREEN}✅ PASS${NC}: $1"
    ((PASSED++))
}

fail() {
    echo -e "${RED}❌ FAIL${NC}: $1"
    ((FAILED++))
}

info() {
    echo -e "${YELLOW}ℹ️  INFO${NC}: $1"
}

section() {
    echo ""
    echo "=========================================="
    echo "$1"
    echo "=========================================="
}

# Test functions
test_server_health() {
    section "Test 1: Server Health Check"

    response=$(curl -s "$BASE_URL/health" 2>/dev/null)

    if [ $? -eq 0 ]; then
        status=$(echo "$response" | jq -r '.status' 2>/dev/null)
        if [ "$status" == "healthy" ] || [ "$status" == "degraded" ]; then
            pass "Server is responding at $BASE_URL"
            info "Status: $status"
            echo "$response" | jq .
        else
            fail "Server returned unexpected status: $status"
        fi
    else
        fail "Cannot connect to $BASE_URL/health"
        info "Make sure server is running: python src/mcp/vetka_mcp_server.py --http --ws --port 5002"
        exit 1
    fi
}

test_parallel_sessions() {
    section "Test 2: Parallel Session Creation (3x)"

    info "Sending 3 concurrent initialize requests with different session IDs"

    # Send 3 parallel requests
    for i in {1..3}; do
        curl -s -X POST "$BASE_URL/mcp" \
            -H "Content-Type: application/json" \
            -H "X-Session-ID: parallel_$i" \
            -d "{\"jsonrpc\":\"2.0\",\"id\":$i,\"method\":\"initialize\",\"params\":{}}" > "/tmp/session_$i.json" &
    done

    wait

    # Verify all 3 responses
    success_count=0
    for i in {1..3}; do
        session_id=$(jq -r '.result.sessionInfo.sessionId' "/tmp/session_$i.json" 2>/dev/null)
        if [ "$session_id" == "parallel_$i" ]; then
            info "Session $i confirmed: $session_id"
            ((success_count++))
        else
            fail "Session $i returned wrong session_id: $session_id"
        fi
    done

    if [ $success_count -eq 3 ]; then
        pass "All 3 sessions initialized with correct session IDs"
    else
        fail "Only $success_count/3 sessions initialized correctly"
    fi

    # Cleanup
    rm -f /tmp/session_*.json
}

test_concurrent_tool_calls() {
    section "Test 3: Concurrent Tool Calls (5x)"

    info "Sending 5 concurrent vetka_health calls with different session IDs"

    # Send 5 parallel tool calls
    for i in {1..5}; do
        curl -s -X POST "$BASE_URL/mcp" \
            -H "Content-Type: application/json" \
            -H "X-Session-ID: tool_test_$i" \
            -d "{\"jsonrpc\":\"2.0\",\"id\":$i,\"method\":\"tools/call\",\"params\":{\"name\":\"vetka_health\",\"arguments\":{}}}" > "/tmp/tool_$i.json" &
    done

    wait

    # Verify all 5 responses
    success_count=0
    for i in {1..5}; do
        result=$(jq -r '.result' "/tmp/tool_$i.json" 2>/dev/null)
        if [ "$result" != "null" ] && [ "$result" != "" ]; then
            info "Tool call $i succeeded"
            ((success_count++))
        else
            error=$(jq -r '.error.message' "/tmp/tool_$i.json" 2>/dev/null)
            fail "Tool call $i failed: $error"
        fi
    done

    if [ $success_count -eq 5 ]; then
        pass "All 5 concurrent tool calls succeeded"
    else
        fail "Only $success_count/5 tool calls succeeded"
    fi

    # Cleanup
    rm -f /tmp/tool_*.json
}

test_actor_stats() {
    section "Test 4: Actor and Pool Statistics"

    response=$(curl -s "$BASE_URL/api/stats" 2>/dev/null)

    if [ $? -eq 0 ]; then
        active_actors=$(echo "$response" | jq -r '.actors.active_actors' 2>/dev/null)
        active_pools=$(echo "$response" | jq -r '.pools.active_pools' 2>/dev/null)

        info "Active actors: $active_actors"
        info "Active pools: $active_pools"

        if [ "$active_actors" -ge 1 ]; then
            pass "At least one active actor found"
        else
            fail "No active actors found (expected at least 1 from previous tests)"
        fi

        if [ "$active_pools" -ge 1 ]; then
            pass "At least one active client pool found"
        else
            fail "No active client pools found"
        fi

        echo ""
        info "Full stats:"
        echo "$response" | jq .
    else
        fail "Cannot fetch stats from $BASE_URL/api/stats"
    fi
}

test_session_isolation() {
    section "Test 5: Session Context Isolation"

    info "Testing that different sessions maintain separate contexts"

    # Session A: First request
    curl -s -X POST "$BASE_URL/mcp" \
        -H "Content-Type: application/json" \
        -H "X-Session-ID: isolation_test_a" \
        -d '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"vetka_health","arguments":{}}}' > /tmp/session_a1.json

    # Session B: First request
    curl -s -X POST "$BASE_URL/mcp" \
        -H "Content-Type: application/json" \
        -H "X-Session-ID: isolation_test_b" \
        -d '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"vetka_health","arguments":{}}}' > /tmp/session_b1.json

    # Session A: Second request (should use same actor)
    curl -s -X POST "$BASE_URL/mcp" \
        -H "Content-Type: application/json" \
        -H "X-Session-ID: isolation_test_a" \
        -d '{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"vetka_health","arguments":{}}}' > /tmp/session_a2.json

    # Check stats to verify separate actors
    stats=$(curl -s "$BASE_URL/api/stats")

    actor_a_exists=$(echo "$stats" | jq -r '.actors.actors["isolation_test_a"]' 2>/dev/null)
    actor_b_exists=$(echo "$stats" | jq -r '.actors.actors["isolation_test_b"]' 2>/dev/null)

    if [ "$actor_a_exists" != "null" ] && [ "$actor_b_exists" != "null" ]; then
        pass "Separate actors created for different session IDs"

        # Check request counts
        a_count=$(echo "$stats" | jq -r '.actors.actors["isolation_test_a"].messages_processed' 2>/dev/null)
        b_count=$(echo "$stats" | jq -r '.actors.actors["isolation_test_b"].messages_processed' 2>/dev/null)

        info "Session A processed: $a_count messages"
        info "Session B processed: $b_count messages"

        if [ "$a_count" == "2" ] && [ "$b_count" == "1" ]; then
            pass "Message counts match expected values (A=2, B=1)"
        else
            fail "Message counts unexpected (A=$a_count, B=$b_count)"
        fi
    else
        fail "Could not verify separate actors in stats"
    fi

    # Cleanup
    rm -f /tmp/session_*.json
}

test_default_session_fallback() {
    section "Test 6: Default Session Fallback"

    info "Testing request without X-Session-ID header"

    # Request without session header
    response=$(curl -s -X POST "$BASE_URL/mcp" \
        -H "Content-Type: application/json" \
        -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}')

    session_id=$(echo "$response" | jq -r '.result.sessionInfo.sessionId' 2>/dev/null)

    if [ "$session_id" == "default" ]; then
        pass "Request without header uses 'default' session"
        info "Session ID: $session_id"
    else
        fail "Expected 'default' session, got: $session_id"
    fi
}

test_error_recovery() {
    section "Test 7: Error Recovery"

    info "Sending malformed request to test error handling"

    # Send invalid tool name
    response=$(curl -s -X POST "$BASE_URL/mcp" \
        -H "Content-Type: application/json" \
        -H "X-Session-ID: error_test" \
        -d '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"invalid_tool","arguments":{}}}')

    error_code=$(echo "$response" | jq -r '.error.code' 2>/dev/null)

    if [ "$error_code" == "-32601" ]; then
        pass "Server returned correct error code for invalid tool"

        # Check if actor is still healthy
        stats=$(curl -s "$BASE_URL/api/stats")
        actor_state=$(echo "$stats" | jq -r '.actors.actors["error_test"].state' 2>/dev/null)

        if [ "$actor_state" == "idle" ] || [ "$actor_state" == "waiting" ]; then
            pass "Actor recovered after error and is in healthy state: $actor_state"
        else
            fail "Actor in unexpected state after error: $actor_state"
        fi
    else
        fail "Unexpected error code: $error_code"
    fi
}

# Main execution
main() {
    echo ""
    echo "╔════════════════════════════════════════════════════════╗"
    echo "║  Phase 106 MCP Server - Session Isolation Test Suite  ║"
    echo "╚════════════════════════════════════════════════════════╝"
    echo ""

    # Check if jq is installed
    if ! command -v jq &> /dev/null; then
        echo -e "${RED}ERROR${NC}: jq is required but not installed."
        echo "Install with: brew install jq"
        exit 1
    fi

    # Run all tests
    test_server_health
    test_parallel_sessions
    test_concurrent_tool_calls
    test_actor_stats
    test_session_isolation
    test_default_session_fallback
    test_error_recovery

    # Summary
    echo ""
    echo "=========================================="
    echo "Test Summary"
    echo "=========================================="
    echo -e "${GREEN}Passed: $PASSED${NC}"
    echo -e "${RED}Failed: $FAILED${NC}"

    if [ $FAILED -eq 0 ]; then
        echo ""
        echo -e "${GREEN}✅ ALL TESTS PASSED${NC}"
        exit 0
    else
        echo ""
        echo -e "${RED}❌ SOME TESTS FAILED${NC}"
        exit 1
    fi
}

# Run main
main
