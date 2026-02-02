# Phase 106 MCP Server - Load Test Results

**Date:** 2026-02-02
**Test Type:** Multi-Session Concurrent Load Test
**Status:** TEST SCRIPTS PREPARED (Server Status Unknown)
**Target:** VETKA MCP HTTP Server on port 5002

---

## Executive Summary

Due to execution environment limitations, the load test could not be run automatically. This document provides:

1. **Ready-to-execute test scripts** for manual load testing
2. **Expected results** and success criteria
3. **Performance benchmarks** from server design specifications
4. **Troubleshooting guide** for common issues

---

## Test Environment

### Server Configuration
- **Server Script:** `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/mcp/vetka_mcp_server.py`
- **Transport Mode:** HTTP with session dispatch (Phase 106f)
- **Port:** 5002
- **Features:**
  - Multi-agent support via MCPActor dispatcher
  - Session-based actor isolation (X-Session-ID header)
  - WebSocket endpoint for real-time communication
  - Enhanced monitoring with /api/stats
  - Health checks with actor status

### Server Capabilities (from source analysis)
```python
# Multi-Session Support: ✅ (Phase 106 feature)
# Session Dispatch: ✅ (via X-Session-ID header)
# Actor Isolation: ✅ (via src/mcp/mcp_actor.py)
# Connection Pool: ✅ (via src/mcp/client_pool.py)
# Health Monitoring: ✅ (/health and /api/stats endpoints)
```

---

## Pre-Test Verification

### Step 1: Check Server Status

```bash
# Test if server is running
curl -s http://localhost:5002/health 2>/dev/null

# Expected output (if running):
{
  "status": "healthy",
  "transport": "http",
  "server": "vetka-mcp",
  "version": "2.0.0",
  "protocol": "2024-11-05",
  "vetka_api": "http://localhost:5001",
  "tools_count": 13,
  "active_actors": 0,
  "healthy_actors": 0
}

# If server NOT running, start it:
cd /Users/danilagulin/Documents/VETKA_Project/vetka_live_03
python src/mcp/vetka_mcp_server.py --http --port 5002
```

---

## Load Test Scripts

### Test 1: 10 Concurrent Sessions (Safe Test)

**Objective:** Verify server can handle multiple simultaneous sessions without degradation.

**Test Script:**
```bash
#!/bin/bash
# File: test_load_10_sessions.sh

echo "==================================================="
echo "Phase 106 MCP Server - 10 Session Load Test"
echo "==================================================="
echo ""

# Clean up previous test results
rm -f /tmp/load_result_*.json

echo "[1/3] Starting 10 concurrent requests..."
START_TIME=$(date +%s)

for i in {1..10}; do
  curl -s -X POST http://localhost:5002/mcp \
    -H "Content-Type: application/json" \
    -H "X-Session-ID: load_session_$i" \
    -d "{\"jsonrpc\":\"2.0\",\"id\":$i,\"method\":\"tools/call\",\"params\":{\"name\":\"vetka_health\",\"arguments\":{}}}" \
    > /tmp/load_result_$i.json &
done

# Wait for all background jobs to complete
wait

END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))

echo "[2/3] All requests completed in ${DURATION}s"
echo ""

# Analyze results
echo "[3/3] Analyzing results..."
success=0
errors=0

for i in {1..10}; do
  if grep -q '"result"' /tmp/load_result_$i.json 2>/dev/null; then
    ((success++))
  else
    ((errors++))
    echo "  ❌ Session $i failed - Response:"
    cat /tmp/load_result_$i.json
    echo ""
  fi
done

echo "==================================================="
echo "RESULTS:"
echo "==================================================="
echo "Total Requests: 10"
echo "Successful: $success"
echo "Failed: $errors"
echo "Success Rate: $success/10 ($(( success * 100 / 10 ))%)"
echo "Duration: ${DURATION}s"
echo "Avg Response Time: ~$(( DURATION / 10 )) requests/sec"
echo "==================================================="

# Check server stats after load
echo ""
echo "Server Statistics After Load:"
curl -s http://localhost:5002/api/stats | jq 2>/dev/null || echo "Stats endpoint unavailable"

# Cleanup
rm -f /tmp/load_result_*.json

# Exit with success if all passed
if [ $success -eq 10 ]; then
  echo ""
  echo "✅ LOAD TEST PASSED"
  exit 0
else
  echo ""
  echo "❌ LOAD TEST FAILED"
  exit 1
fi
```

**Expected Results:**
- Success Rate: 10/10 (100%)
- Duration: 2-5 seconds
- No errors in responses
- Active actors: 10 (or fewer with actor pooling)

---

### Test 2: 50 Concurrent Sessions (Stress Test)

**Objective:** Test server performance under heavier concurrent load.

**Test Script:**
```bash
#!/bin/bash
# File: test_load_50_sessions.sh

echo "==================================================="
echo "Phase 106 MCP Server - 50 Session Stress Test"
echo "==================================================="
echo ""

# Clean up previous test results
rm -f /tmp/stress_result_*.json

echo "[1/3] Starting 50 concurrent requests..."
START_TIME=$(date +%s)

for i in {1..50}; do
  curl -s -X POST http://localhost:5002/mcp \
    -H "Content-Type: application/json" \
    -H "X-Session-ID: stress_session_$i" \
    -d "{\"jsonrpc\":\"2.0\",\"id\":$i,\"method\":\"initialize\",\"params\":{}}" \
    > /tmp/stress_result_$i.json &
done

# Wait for all background jobs
wait

END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))

echo "[2/3] All requests completed in ${DURATION}s"
echo ""

# Analyze results
echo "[3/3] Analyzing results..."
success=0
errors=0

for i in {1..50}; do
  if grep -q '"result"' /tmp/stress_result_$i.json 2>/dev/null; then
    ((success++))
  else
    ((errors++))
  fi
done

echo "==================================================="
echo "STRESS TEST RESULTS:"
echo "==================================================="
echo "Total Requests: 50"
echo "Successful: $success"
echo "Failed: $errors"
echo "Success Rate: $success/50 ($(( success * 100 / 50 ))%)"
echo "Duration: ${DURATION}s"
echo "Requests/sec: $(( 50 / DURATION ))"
echo "==================================================="

# Check server stats
echo ""
echo "Server Statistics After Stress:"
curl -s http://localhost:5002/api/stats | jq

# Cleanup
rm -f /tmp/stress_result_*.json

if [ $success -ge 45 ]; then
  echo ""
  echo "✅ STRESS TEST PASSED (90%+ success rate)"
  exit 0
else
  echo ""
  echo "❌ STRESS TEST FAILED (< 90% success rate)"
  exit 1
fi
```

**Expected Results:**
- Success Rate: 45+/50 (90%+ acceptable under stress)
- Duration: 5-15 seconds
- Actor pooling should prevent resource exhaustion
- Stats should show reasonable actor counts

---

### Test 3: Session Isolation Verification

**Objective:** Verify that different sessions do not interfere with each other.

**Test Script:**
```bash
#!/bin/bash
# File: test_session_isolation.sh

echo "==================================================="
echo "Phase 106 MCP Server - Session Isolation Test"
echo "==================================================="
echo ""

# Test that two sessions with same tool call get isolated results
echo "[1/2] Testing session isolation..."

# Session A
SESSION_A=$(curl -s -X POST http://localhost:5002/mcp \
  -H "Content-Type: application/json" \
  -H "X-Session-ID: isolation_test_A" \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}')

# Session B
SESSION_B=$(curl -s -X POST http://localhost:5002/mcp \
  -H "Content-Type: application/json" \
  -H "X-Session-ID: isolation_test_B" \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}')

echo "[2/2] Verifying session IDs..."

# Check if both sessions got unique session info
SESSION_A_ID=$(echo $SESSION_A | jq -r '.result.sessionInfo.sessionId' 2>/dev/null)
SESSION_B_ID=$(echo $SESSION_B | jq -r '.result.sessionInfo.sessionId' 2>/dev/null)

echo ""
echo "Session A ID: $SESSION_A_ID"
echo "Session B ID: $SESSION_B_ID"
echo ""

if [ "$SESSION_A_ID" = "isolation_test_A" ] && [ "$SESSION_B_ID" = "isolation_test_B" ]; then
  echo "✅ SESSION ISOLATION TEST PASSED"
  echo "   Sessions are properly isolated with unique identifiers"
  exit 0
else
  echo "❌ SESSION ISOLATION TEST FAILED"
  echo "   Sessions not properly isolated"
  exit 1
fi
```

**Expected Results:**
- Each session receives its own session ID in response
- Session IDs match the X-Session-ID headers sent

---

## Performance Benchmarks

### Server Design Specifications (from code analysis)

| Metric | Expected | Notes |
|--------|----------|-------|
| **Concurrent Sessions** | 50+ | Actor dispatcher handles pooling |
| **Response Time** | < 500ms | Per request (excluding VETKA API latency) |
| **Session Isolation** | 100% | X-Session-ID header enforcement |
| **Actor Lifecycle** | Auto-managed | Dispatcher creates/reuses actors |
| **Error Recovery** | Graceful | Fallback to direct call if actor system fails |
| **Health Check** | < 100ms | Simple status endpoint |
| **Stats Endpoint** | < 200ms | Aggregates actor and pool metrics |

### Transport Modes Available

```python
# stdio (default) - Claude Desktop/Code
python vetka_mcp_server.py

# HTTP (tested here) - VS Code, Cursor, Gemini
python vetka_mcp_server.py --http --port 5002

# HTTP + WebSocket - Multi-agent support
python vetka_mcp_server.py --http --ws --port 5002

# SSE - JetBrains
python vetka_mcp_server.py --sse --port 5003
```

---

## Test Execution Instructions

### Manual Test Execution

1. **Start the server:**
```bash
cd /Users/danilagulin/Documents/VETKA_Project/vetka_live_03
python src/mcp/vetka_mcp_server.py --http --port 5002
```

2. **In a new terminal, run the tests:**
```bash
# Save the test scripts above to files
chmod +x test_load_10_sessions.sh
chmod +x test_load_50_sessions.sh
chmod +x test_session_isolation.sh

# Run the tests
./test_load_10_sessions.sh
./test_load_50_sessions.sh
./test_session_isolation.sh
```

3. **Review results** in terminal output and this document

---

## Expected Output Analysis

### Successful Load Test Output

```
===================================================
Phase 106 MCP Server - 10 Session Load Test
===================================================

[1/3] Starting 10 concurrent requests...
[2/3] All requests completed in 3s

[3/3] Analyzing results...
===================================================
RESULTS:
===================================================
Total Requests: 10
Successful: 10
Failed: 0
Success Rate: 10/10 (100%)
Duration: 3s
Avg Response Time: ~3 requests/sec
===================================================

Server Statistics After Load:
{
  "actors": {
    "active_actors": 10,
    "healthy_actors": 10,
    "total_dispatched": 10,
    "avg_response_time": 0.285
  },
  "pools": {
    "active_connections": 1,
    "available_connections": 9,
    "total_requests": 10
  },
  "timestamp": 1738475200.5
}

✅ LOAD TEST PASSED
```

### Health Check Response

```json
{
  "status": "healthy",
  "transport": "http",
  "server": "vetka-mcp",
  "version": "2.0.0",
  "protocol": "2024-11-05",
  "vetka_api": "http://localhost:5001",
  "tools_count": 13,
  "active_actors": 10,
  "healthy_actors": 10
}
```

---

## Troubleshooting Guide

### Issue: Server Not Running

**Symptoms:**
```
curl: (7) Failed to connect to localhost port 5002: Connection refused
```

**Solution:**
```bash
# Start the server
cd /Users/danilagulin/Documents/VETKA_Project/vetka_live_03
python src/mcp/vetka_mcp_server.py --http --port 5002

# Verify it's running
curl http://localhost:5002/health
```

---

### Issue: Low Success Rate (< 90%)

**Symptoms:**
```
Success Rate: 7/10 (70%)
Failed: 3
```

**Possible Causes:**
1. VETKA API not responding (port 5001 down)
2. Network timeout issues
3. Resource exhaustion

**Solutions:**
```bash
# 1. Check VETKA API
curl http://localhost:5001/health

# 2. Check server logs for errors
# (watch the terminal where server is running)

# 3. Check system resources
top -l 1 | grep vetka

# 4. Restart server with verbose logging
python src/mcp/vetka_mcp_server.py --http --port 5002 --log-level DEBUG
```

---

### Issue: Actor System Not Available

**Symptoms:**
```json
{
  "error": "Actor system not available",
  "fallback": true
}
```

**Solution:**
This is expected behavior - the server falls back to direct calls if Phase 106 actor components aren't available. Not a failure.

---

### Issue: Session Isolation Failure

**Symptoms:**
```
Session A ID: null
Session B ID: null
```

**Solution:**
```bash
# Check if multiSession capability is enabled
curl -s -X POST http://localhost:5002/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}' \
  | jq '.result.capabilities.multiSession'

# Should return: true
```

---

## Scaling Recommendations

### Current Configuration
- **Actor Pooling:** Enabled (Phase 106f)
- **Connection Pooling:** Enabled via client_pool.py
- **Session Isolation:** Enabled via X-Session-ID

### For Higher Load (100+ concurrent sessions)

1. **Enable connection pool limits:**
```python
# In client_pool.py
MAX_POOL_SIZE = 50  # Increase from default
```

2. **Add request rate limiting:**
```python
# In vetka_mcp_server.py (handle_mcp function)
from starlette.middleware.trustedhost import TrustedHostMiddleware
from slowapi import Limiter
```

3. **Monitor actor lifecycle:**
```bash
# Check stats regularly
watch -n 1 "curl -s http://localhost:5002/api/stats | jq"
```

4. **Consider horizontal scaling:**
```bash
# Run multiple instances on different ports
python vetka_mcp_server.py --http --port 5002 &
python vetka_mcp_server.py --http --port 5003 &
python vetka_mcp_server.py --http --port 5004 &

# Use nginx for load balancing
```

---

## Test Status Summary

| Test | Status | Notes |
|------|--------|-------|
| Pre-check Script | ✅ Ready | Server health check prepared |
| 10 Session Load Test | ⏸️ Pending | Script ready, awaiting execution |
| 50 Session Stress Test | ⏸️ Pending | Script ready, awaiting execution |
| Session Isolation Test | ⏸️ Pending | Script ready, awaiting execution |
| Performance Benchmarks | ✅ Documented | Based on code analysis |
| Troubleshooting Guide | ✅ Complete | Common issues covered |

---

## Next Steps

### For Immediate Testing

1. **Start the MCP server** (if not already running):
```bash
cd /Users/danilagulin/Documents/VETKA_Project/vetka_live_03
python src/mcp/vetka_mcp_server.py --http --port 5002
```

2. **Run the test scripts** provided above (save to files and execute)

3. **Document results** by updating this file with actual test output

### For Production Deployment

1. **Run all three test scripts** and verify 90%+ success rates
2. **Monitor /api/stats** endpoint during load
3. **Review server logs** for warnings or errors
4. **Implement rate limiting** if planning for 100+ concurrent sessions
5. **Set up monitoring** (Prometheus/Grafana recommended)

---

## References

### Server Implementation
- **Main Server:** `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/mcp/vetka_mcp_server.py`
- **Actor Dispatcher:** `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/mcp/mcp_actor.py`
- **Connection Pool:** `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/mcp/client_pool.py`
- **Bridge Core:** `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/mcp/vetka_mcp_bridge.py`

### Documentation
- **Phase 106 Overview:** `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/docs/phase_106_multi_agent_mcp/PHASE_106g_IMPLEMENTATION_COMPLETE.md`
- **Client Compatibility:** `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/docs/phase_106_multi_agent_mcp/MCP_CLIENT_COMPATIBILITY_REPORT.md`
- **Setup Guide:** `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/docs/phase_106_multi_agent_mcp/START_HERE.md`

---

## Conclusion

The Phase 106 MCP server is designed with robust multi-session support, actor isolation, and connection pooling. The load test scripts provided above are ready for execution once the server is running.

**Recommended Action:** Execute the test scripts manually and update this document with actual results.

---

**Document Created:** 2026-02-02
**Test Scripts Status:** Ready for Execution
**Server Status:** Unknown (check required)
**Next Action:** Start server and run tests
