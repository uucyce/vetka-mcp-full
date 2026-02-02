# Phase 106 MCP Server - Basic Tests Result

**Date**: 2026-02-02
**Test Session**: verify_test_1
**Tester**: Claude Agent (Automated Verification)

---

## Executive Summary

**Status**: UNABLE TO VERIFY - Manual Testing Required
**Reason**: Bash execution requires user permission in current environment

This document provides:
1. Pre-check procedures
2. Test scenarios to execute
3. Expected results
4. Verification template

---

## System Architecture Overview

### Identified Components

**Main MCP Server**: `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/mcp/vetka_mcp_server.py`
- Multi-transport support (stdio, HTTP, SSE, WebSocket)
- Phase 106f enhancements with session-based actor isolation
- 13 registered tools (8 read + 5 write)

**Legacy MCP Server**: `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/mcp/mcp_server.py`
- WebSocket-based server for AI agents
- Security features: rate limiting, audit logging, approval flow
- 15 tools registered (includes intake and ARC tools)

**Configuration**:
- HTTP Port: 5002 (MCP HTTP server)
- API Port: 5001 (VETKA API - assumed from test script)
- SSE Port: 5003 (if SSE mode enabled)
- WebSocket: ws://localhost:5002/mcp/ws (if enabled)

---

## Pre-Check Procedures

### Step 1: Check Server Status

```bash
# Check VETKA API (port 5001)
curl -s http://localhost:5001/health 2>/dev/null || echo "VETKA API not running"

# Check MCP HTTP (port 5002)
curl -s http://localhost:5002/health 2>/dev/null || echo "MCP HTTP not running"

# Check process status
ps aux | grep -E "(vetka_mcp_server|main.py)" | grep -v grep
```

**Expected Outputs**:
- VETKA API should return JSON health status
- MCP HTTP should return health status with server info
- Process list should show running Python processes

---

## Test Scenarios

### Test 1: Health Check (HTTP Mode)

**Purpose**: Verify MCP HTTP server is responsive and reports correct status

**Command**:
```bash
curl http://localhost:5002/health | jq
```

**Expected Result**:
```json
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
```

**Success Criteria**:
- HTTP 200 status code
- Valid JSON response
- `status`: "healthy"
- `tools_count`: 13
- `version`: "2.0.0"

---

### Test 2: Tools List (JSON-RPC)

**Purpose**: Verify MCP server can list all available tools

**Command**:
```bash
curl -s -X POST http://localhost:5002/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}' | jq
```

**Expected Result**:
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "tools": [
      {
        "name": "vetka_search",
        "description": "...",
        "inputSchema": {...}
      },
      // ... 12 more tools
    ]
  }
}
```

**Success Criteria**:
- HTTP 200 status code
- Valid JSON-RPC 2.0 response
- `result.tools` is an array
- Tools array length should be 13
- Each tool has: `name`, `description`, `inputSchema`

**Quick Verification**:
```bash
# Count tools
curl -s -X POST http://localhost:5002/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}' | jq '.result.tools | length'
```
Expected: `13`

---

### Test 3: Tool Call - vetka_health

**Purpose**: Verify MCP server can execute tool calls and session dispatch works

**Command**:
```bash
curl -s -X POST http://localhost:5002/mcp \
  -H "Content-Type: application/json" \
  -H "X-Session-ID: verify_test_1" \
  -d '{"jsonrpc":"2.0","id":42,"method":"tools/call","params":{"name":"vetka_health","arguments":{}}}' | jq
```

**Expected Result**:
```json
{
  "jsonrpc": "2.0",
  "id": 42,
  "result": {
    "content": [
      {
        "type": "text",
        "text": "..."
      }
    ]
  }
}
```

**Success Criteria**:
- HTTP 200 status code
- Valid JSON-RPC 2.0 response
- `id` matches request (42)
- `result.content` is an array
- No `error` field present

---

### Test 4: Session Isolation (Phase 106f Feature)

**Purpose**: Verify session-based actor isolation is working

**Command**:
```bash
# Session 1
curl -s -X POST http://localhost:5002/mcp \
  -H "Content-Type: application/json" \
  -H "X-Session-ID: session_1" \
  -d '{"jsonrpc":"2.0","id":100,"method":"initialize","params":{}}' | jq

# Session 2
curl -s -X POST http://localhost:5002/mcp \
  -H "Content-Type: application/json" \
  -H "X-Session-ID: session_2" \
  -d '{"jsonrpc":"2.0","id":200,"method":"initialize","params":{}}' | jq

# Check stats
curl -s http://localhost:5002/api/stats | jq
```

**Expected Result**:
```json
{
  "actors": {
    "active_actors": 2,
    "healthy_actors": 2,
    "sessions": ["session_1", "session_2"]
  },
  "pools": {...},
  "timestamp": 123456.789
}
```

**Success Criteria**:
- Multiple sessions can be initialized
- `/api/stats` shows correct actor count
- Each session gets unique `sessionInfo.sessionId` in response

---

### Test 5: Error Handling

**Purpose**: Verify proper error responses for invalid requests

**Command**:
```bash
# Invalid method
curl -s -X POST http://localhost:5002/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":999,"method":"invalid_method","params":{}}' | jq

# Unknown tool
curl -s -X POST http://localhost:5002/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":998,"method":"tools/call","params":{"name":"unknown_tool","arguments":{}}}' | jq
```

**Expected Results**:

Invalid method:
```json
{
  "jsonrpc": "2.0",
  "id": 999,
  "error": {
    "code": -32601,
    "message": "Method not found: invalid_method"
  }
}
```

Unknown tool (may vary based on actor system availability):
- With actor system: Error from dispatcher
- Without actor system: Standard error response

**Success Criteria**:
- HTTP 404 for invalid method
- Proper JSON-RPC error format
- Error codes follow JSON-RPC 2.0 spec

---

## Verification Template

### Manual Test Execution

```bash
# Create test results file
TEST_RESULTS="/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/docs/phase_106_multi_agent_mcp/verification/test_execution_$(date +%Y%m%d_%H%M%S).log"

echo "=== Phase 106 MCP Server Verification ===" > "$TEST_RESULTS"
echo "Date: $(date)" >> "$TEST_RESULTS"
echo "" >> "$TEST_RESULTS"

# Test 1: Health Check
echo "TEST 1: Health Check" >> "$TEST_RESULTS"
curl -s http://localhost:5002/health | jq >> "$TEST_RESULTS" 2>&1
echo "" >> "$TEST_RESULTS"

# Test 2: Tools List
echo "TEST 2: Tools List (Count)" >> "$TEST_RESULTS"
curl -s -X POST http://localhost:5002/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}' | jq '.result.tools | length' >> "$TEST_RESULTS" 2>&1
echo "" >> "$TEST_RESULTS"

# Test 3: Tool Call
echo "TEST 3: Tool Call - vetka_health" >> "$TEST_RESULTS"
curl -s -X POST http://localhost:5002/mcp \
  -H "Content-Type: application/json" \
  -H "X-Session-ID: verify_test_1" \
  -d '{"jsonrpc":"2.0","id":42,"method":"tools/call","params":{"name":"vetka_health","arguments":{}}}' | jq >> "$TEST_RESULTS" 2>&1
echo "" >> "$TEST_RESULTS"

# Test 4: Stats Endpoint
echo "TEST 4: Stats Endpoint" >> "$TEST_RESULTS"
curl -s http://localhost:5002/api/stats | jq >> "$TEST_RESULTS" 2>&1
echo "" >> "$TEST_RESULTS"

# Test 5: Error Handling
echo "TEST 5: Error Handling - Invalid Method" >> "$TEST_RESULTS"
curl -s -X POST http://localhost:5002/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":999,"method":"invalid_method","params":{}}' | jq >> "$TEST_RESULTS" 2>&1
echo "" >> "$TEST_RESULTS"

echo "=== Test Execution Complete ===" >> "$TEST_RESULTS"
cat "$TEST_RESULTS"
```

---

## Analysis & Recommendations

### Code Review Findings

#### Strengths
1. **Multi-transport architecture**: Supports stdio, HTTP, SSE, and WebSocket
2. **Phase 106f enhancements**: Session-based actor isolation implemented
3. **Comprehensive toolset**: 13 tools covering read/write operations
4. **Security features**: Rate limiting, audit logging, approval flow (in legacy server)
5. **Standards compliance**: Implements JSON-RPC 2.0 and MCP protocol 2024-11-05

#### Potential Issues

**1. Dual Server Architecture**
- Two different MCP servers exist: `vetka_mcp_server.py` (new) and `mcp_server.py` (legacy)
- May cause confusion about which server should be running
- Different tool counts: 13 vs 15 (intake and ARC tools in legacy)

**2. Actor System Dependency**
- HTTP mode tries to import `src.mcp.mcp_actor` and `src.mcp.client_pool`
- Falls back to direct calls if not available
- Test script should verify which mode is active

**3. Port Configuration**
- Default ports: 5001 (API), 5002 (MCP HTTP), 5003 (SSE)
- No verification that ports are not in use by other services
- No automatic port selection if default is taken

**4. WebSocket Support**
- WebSocket endpoint (`/mcp/ws`) requires `--ws` flag
- Not enabled by default in HTTP mode
- Test script doesn't verify WebSocket functionality

#### Recommendations

**Immediate Actions**:
1. Run manual test suite (template provided above)
2. Verify which MCP server is currently running
3. Check for port conflicts
4. Confirm actor system availability

**Short-term Improvements**:
1. Add process monitoring/health check daemon
2. Create unified logging directory with structured logs
3. Add startup validation script that checks dependencies
4. Document which server configuration is production-ready

**Medium-term Enhancements**:
1. Consolidate dual server architecture or clearly document their roles
2. Add automated integration tests
3. Implement graceful degradation when actor system unavailable
4. Add metrics collection and monitoring dashboard

---

## Next Steps

### For Manual Verification

1. **Start servers** (if not running):
   ```bash
   # VETKA API server
   cd /Users/danilagulin/Documents/VETKA_Project/vetka_live_03/app
   source .venv/bin/activate
   python main.py &

   # MCP HTTP server
   cd /Users/danilagulin/Documents/VETKA_Project/vetka_live_03
   python src/mcp/vetka_mcp_server.py --http --port 5002 &
   ```

2. **Run verification template** (bash script above)

3. **Review test results** and compare with expected outputs

4. **Document any failures** in issue tracker

5. **Update this file** with actual test results

### For Automated Testing

1. Create pytest test suite for MCP server
2. Add CI/CD integration
3. Set up continuous monitoring
4. Create alerting for server health

---

## Test Results (To Be Filled)

### Server Status
- [ ] VETKA API running on port 5001
- [ ] MCP HTTP running on port 5002
- [ ] Actor system available
- [ ] Client pool available

### Test Results
- [ ] Test 1: Health Check - PASS/FAIL
- [ ] Test 2: Tools List - PASS/FAIL (Count: ___)
- [ ] Test 3: Tool Call - PASS/FAIL
- [ ] Test 4: Session Isolation - PASS/FAIL
- [ ] Test 5: Error Handling - PASS/FAIL

### Issues Found
_(List any issues discovered during testing)_

### Execution Log
_(Attach or link to detailed execution log)_

---

## Appendix

### Available Tools (from code analysis)

**Read-Only Tools** (8):
1. `vetka_search` - Search nodes in knowledge graph
2. `vetka_search_knowledge` - Search knowledge base
3. `vetka_get_tree` - Get tree structure
4. `vetka_get_node` - Get specific node
5. `vetka_list_files` - List project files
6. `vetka_read_file` - Read file contents
7. `vetka_git_status` - Git status
8. `vetka_health` - Health check

**Write Tools** (5):
1. `vetka_create_branch` - Create git branch
2. `vetka_edit_file` - Edit file
3. `vetka_git_commit` - Git commit
4. `vetka_run_tests` - Run tests
5. `vetka_camera_control` - Camera control (3D UI)

**Additional Tools** (in legacy server):
- `vetka_intake_url` - Intake URL processing
- `vetka_list_intakes` - List intakes
- `vetka_get_intake` - Get intake details
- `vetka_arc_gap` - ARC gap analysis
- `vetka_arc_concepts` - ARC concepts

### References

- MCP Protocol: 2024-11-05
- JSON-RPC 2.0: https://www.jsonrpc.org/specification
- Phase 106 Documentation: `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/docs/phase_106_multi_agent_mcp/`

---

**Document Status**: DRAFT - Awaiting Manual Test Execution
**Last Updated**: 2026-02-02
**Author**: Claude Agent (Automated Analysis)
