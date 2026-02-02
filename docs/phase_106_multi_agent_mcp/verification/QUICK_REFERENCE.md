# Phase 106 MCP Verification - Quick Reference Card

**Last Updated**: 2026-02-02

---

## One-Command Verification

```bash
# From project root
cd /Users/danilagulin/Documents/VETKA_Project/vetka_live_03/docs/phase_106_multi_agent_mcp/verification
chmod +x RUN_TESTS.sh && ./RUN_TESTS.sh
```

---

## Pre-Flight Check

```bash
# Check if servers are running
curl -s http://localhost:5001/health  # VETKA API
curl -s http://localhost:5002/health  # MCP HTTP

# If not running, start them:
# Terminal 1:
cd ~/Documents/VETKA_Project/vetka_live_03/app && source .venv/bin/activate && python main.py

# Terminal 2:
cd ~/Documents/VETKA_Project/vetka_live_03 && python src/mcp/vetka_mcp_server.py --http --port 5002
```

---

## Quick Health Check

```bash
# Single command health check
curl http://localhost:5002/health | jq '.status, .tools_count, .active_actors'

# Expected: "healthy", 13, 0 or more
```

---

## Quick Tool Count

```bash
# Count available tools
curl -s -X POST http://localhost:5002/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}' | \
  jq '.result.tools | length'

# Expected: 13
```

---

## Quick Tool Call Test

```bash
# Test vetka_health tool
curl -s -X POST http://localhost:5002/mcp \
  -H "Content-Type: application/json" \
  -H "X-Session-ID: quicktest" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"vetka_health","arguments":{}}}' | \
  jq '.result.content'

# Expected: Array with text response
```

---

## Available Test Scripts

| Script | Purpose | Time | Tests |
|--------|---------|------|-------|
| **RUN_TESTS.sh** | Complete basic verification | 2 min | 10 |
| **test_session_isolation.sh** | Session isolation deep test | 5 min | 7 |
| Manual (LOAD_TEST_RESULT.md) | Load testing | 10 min | 3 |

---

## Test Result Files

After running tests, check:

```bash
# List test results
ls -lht test_execution_*.log | head -5

# View latest result
cat test_execution_*.log | tail -1

# Search for failures
grep "FAIL" test_execution_*.log
```

---

## Expected Results Summary

### Health Check
- Status: `"healthy"`
- Transport: `"http"`
- Tools: `13`
- Protocol: `"2024-11-05"`

### Tools List
- Count: `13` tools minimum
- Each has: `name`, `description`, `inputSchema`

### Tool Call
- Returns: `{"result": {"content": [...]}}`
- No `error` field

### Sessions
- Multiple sessions supported
- Each gets unique session ID
- Stats show active actors

---

## Common Issues & Solutions

| Issue | Solution |
|-------|----------|
| **Connection refused** | Start MCP server on port 5002 |
| **VETKA API not running** | Start main.py in app/ directory |
| **Tool count is 15 instead of 13** | Legacy server is running - use new server |
| **Actor system unavailable** | Normal - falls back to direct mode |
| **Tests fail** | Check server logs and troubleshooting guide |

---

## Port Reference

| Port | Service | Command to Start |
|------|---------|------------------|
| 5001 | VETKA API | `cd app && python main.py` |
| 5002 | MCP HTTP | `python src/mcp/vetka_mcp_server.py --http` |
| 5003 | MCP SSE | `python src/mcp/vetka_mcp_server.py --sse` |

---

## Test Coverage Checklist

- [x] Health endpoint
- [x] Tools list
- [x] Initialize method
- [x] Tool calls
- [x] Session isolation
- [x] Error handling
- [x] CORS headers
- [x] Stats endpoint
- [ ] WebSocket (requires --ws flag)
- [ ] Load testing (separate suite)

---

## Success Criteria

**Basic Tests**: 8-10 of 10 pass
**Session Tests**: 6-7 of 7 pass
**Load Tests**: 90%+ success rate

---

## Documentation Files

| File | Purpose | Size |
|------|---------|------|
| README.md | Overview | Current |
| BASIC_TESTS_RESULT.md | Test scenarios | 12 KB |
| LOAD_TEST_RESULT.md | Load testing | 16 KB |
| SESSION_ISOLATION_RESULT.md | Session tests | 25 KB |
| VERIFICATION_SESSION_SUMMARY.md | Session summary | 7 KB |
| **This file** | **Quick reference** | **2 KB** |

---

## Next Steps After Testing

1. **Review results**: Check test_execution_*.log
2. **Check stats**: `curl http://localhost:5002/api/stats | jq`
3. **Document issues**: Note any failures
4. **Performance review**: Check response times
5. **Load test**: Run LOAD_TEST_RESULT.md scenarios

---

## Emergency Debug

```bash
# Check process status
ps aux | grep -E "(vetka_mcp_server|main.py)" | grep -v grep

# Check port usage
lsof -i :5001
lsof -i :5002

# Kill stuck servers
pkill -f vetka_mcp_server
pkill -f "python main.py"

# Restart fresh
cd ~/Documents/VETKA_Project/vetka_live_03/app
source .venv/bin/activate
python main.py &
cd ..
python src/mcp/vetka_mcp_server.py --http --port 5002 &
sleep 3
cd docs/phase_106_multi_agent_mcp/verification
./RUN_TESTS.sh
```

---

**Quick Reference v1.0**
**Phase 106 Multi-Agent MCP Architecture**
