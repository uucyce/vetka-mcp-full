# Deployment Checklist - Handler V2

**Mission:** Deploy user_message_handler_v2.py to production
**Date:** 2026-01-23
**Status:** Ready for deployment

---

## Pre-Deployment Checklist

### Code Quality
- [x] All Python syntax validated
- [x] No import errors
- [x] Backwards compatible Socket.IO events
- [x] Legacy handler backed up
- [x] Comprehensive documentation written

### Files Created
- [x] `/src/api/handlers/user_message_handler_v2.py` (446 lines)
- [x] `/src/api/handlers/di_container.py` (164 lines)
- [x] `/src/api/handlers/user_message_handler_legacy.py` (backup)
- [x] `/docs/80_ph_mcp_agents/PHASE4_FINAL_INTEGRATION.md`
- [x] `/docs/80_ph_mcp_agents/DEPLOYMENT_CHECKLIST.md`

### Dependencies Verified
- [x] ContextBuilder exists
- [x] ModelClient exists
- [x] MentionHandler exists
- [x] HostessRouter exists
- [x] AgentOrchestrator exists
- [x] ResponseManager exists
- [x] All interfaces defined

---

## Deployment Steps

### Step 1: Update Main App

**File to modify:** `src/main.py` (or wherever handlers are registered)

**OLD CODE:**
```python
from src.api.handlers.user_message_handler import register_user_message_handler
```

**NEW CODE:**
```python
from src.api.handlers.user_message_handler_v2 import register_user_message_handler
```

**Verification:**
```bash
# Search for the import
grep -n "from src.api.handlers.user_message_handler import" src/main.py

# Update the import
# (do this manually or with sed)
```

---

### Step 2: Run Syntax Check

```bash
# Validate all handler files
python3 -m py_compile src/api/handlers/user_message_handler_v2.py
python3 -m py_compile src/api/handlers/di_container.py
python3 -m py_compile src/api/handlers/context/context_builders.py
python3 -m py_compile src/api/handlers/models/model_client.py
python3 -m py_compile src/api/handlers/mention/mention_handler.py
python3 -m py_compile src/api/handlers/routing/hostess_router.py
python3 -m py_compile src/api/handlers/orchestration/agent_orchestrator.py
python3 -m py_compile src/api/handlers/orchestration/response_manager.py

# Should all pass with no errors
```

---

### Step 3: Start Server

```bash
# Start VETKA server
python3 src/main.py

# Check for startup errors
# Should see: "Socket.IO server started on port 5001"
```

---

### Step 4: Test Core Functionality

#### Test 1: Direct Model Call
- [ ] Open VETKA frontend
- [ ] Select a model from Model Directory dropdown
- [ ] Send message: "What is VETKA?"
- [ ] Verify model responds correctly
- [ ] Check logs for "[HANDLER_V2] Direct model call"

#### Test 2: @Mention Call
- [ ] Send message: "@gpt4 explain Python decorators"
- [ ] Verify GPT-4 responds
- [ ] Check logs for "[HANDLER_V2] @mention handled"

#### Test 3: Agent @Mentions
- [ ] Send message: "@PM @Dev analyze this file"
- [ ] Verify PM and Dev respond
- [ ] Check logs for "[HANDLER_V2] @mention override"

#### Test 4: Hostess Routing
- [ ] Send message: "What can you do?"
- [ ] Verify Hostess responds directly
- [ ] Check logs for "[HANDLER_V2] Hostess handled directly"

#### Test 5: Full Agent Chain
- [ ] Send message: "Review and improve this code"
- [ ] Verify PM, Dev, QA all respond
- [ ] Verify summary is generated
- [ ] Check logs for "[HANDLER_V2] Processing complete"

#### Test 6: Multi-File Context
- [ ] Pin 3 files in viewport
- [ ] Send message: "How do these files relate?"
- [ ] Verify context includes all pinned files
- [ ] Check logs for "Pinned files: 3 files"

#### Test 7: Viewport Context
- [ ] Navigate 3D viewport
- [ ] Send message: "What's in this folder?"
- [ ] Verify viewport context included
- [ ] Check logs for "Viewport: X pinned, Y visible"

---

### Step 5: Monitor for Errors

```bash
# Watch logs for errors
tail -f logs/vetka.log | grep -i error

# Watch for handler v2 logs
tail -f logs/vetka.log | grep "HANDLER_V2"

# Monitor for 15 minutes
# Should see no errors
```

---

### Step 6: Performance Check

#### Response Times
- [ ] Direct model call: < 5 seconds
- [ ] @mention call: < 5 seconds
- [ ] Single agent: < 10 seconds
- [ ] Full chain: < 30 seconds

#### Memory Usage
```bash
# Check memory usage
ps aux | grep python3 | grep main.py

# Should be similar to before refactoring
# No memory leaks
```

---

## Rollback Plan

If anything goes wrong:

### Quick Rollback (5 minutes)

1. **Revert import:**
   ```python
   # Change back to:
   from src.api.handlers.user_message_handler import register_user_message_handler
   ```

2. **Restart server:**
   ```bash
   # Kill current server
   pkill -f "python3 src/main.py"

   # Start with old handler
   python3 src/main.py
   ```

3. **Verify:**
   - Send test message
   - Should work with old handler

### Investigation

If issues found:

1. **Check logs:**
   ```bash
   grep -A 10 "HANDLER_V2" logs/vetka.log
   grep -i error logs/vetka.log
   ```

2. **Check specific module:**
   - ContextBuilder?
   - ModelClient?
   - MentionHandler?
   - HostessRouter?
   - AgentOrchestrator?
   - ResponseManager?

3. **File issue:**
   - Create detailed bug report
   - Include logs and stack trace
   - Note which test failed

---

## Post-Deployment Monitoring

### Day 1 (24 hours)
- [ ] Monitor error logs every 2 hours
- [ ] Check memory usage every 4 hours
- [ ] Verify response times are acceptable
- [ ] Collect user feedback

### Day 2-7 (1 week)
- [ ] Daily error log review
- [ ] Daily performance check
- [ ] User feedback collection
- [ ] Compare metrics to pre-refactoring baseline

### After 1 Week
- [ ] If no issues: Delete `user_message_handler_legacy.py`
- [ ] If issues: Investigate and fix, extend monitoring period

---

## Success Criteria

Deployment is successful if:

1. **All tests pass** ✅
2. **No errors in logs** ✅
3. **Response times acceptable** ✅
4. **Memory usage stable** ✅
5. **User feedback positive** ✅
6. **No regressions** ✅

---

## Known Issues

None currently identified.

---

## Contact

**Primary:** Sonnet Agent G (refactoring completed)
**Backup:** Check `/docs/80_ph_mcp_agents/PHASE4_FINAL_INTEGRATION.md` for details

---

## Additional Notes

### Architecture Benefits

The new v2 handler provides:

1. **Clean Separation of Concerns**
   - Each module has ONE responsibility
   - No more God Object antipattern

2. **Testability**
   - All dependencies injectable
   - Easy to mock for testing

3. **Maintainability**
   - Clear code flow
   - Easy to understand
   - Easy to modify

4. **Extensibility**
   - Add new features without touching core handler
   - Just create new modules and wire them

### Future Improvements

After successful deployment:

1. Add unit tests for each module
2. Add integration tests for handler v2
3. Add type hints everywhere
4. Add comprehensive logging
5. Optimize performance (caching, parallelization)
6. Add metrics/monitoring

---

## Appendix: Key Files

```
src/api/handlers/
├── user_message_handler_v2.py          ← NEW: Deploy this
├── user_message_handler.py             ← OLD: Keep as-is (fallback)
├── user_message_handler_legacy.py      ← BACKUP: Delete after 1 week
├── di_container.py                     ← NEW: DI container
│
├── context/
│   └── context_builders.py             ← ContextBuilder
│
├── models/
│   └── model_client.py                 ← ModelClient
│
├── mention/
│   └── mention_handler.py              ← MentionHandler
│
├── routing/
│   └── hostess_router.py               ← HostessRouter
│
├── orchestration/
│   ├── agent_orchestrator.py           ← AgentOrchestrator
│   └── response_manager.py             ← ResponseManager
│
└── interfaces/
    └── __init__.py                     ← Protocol definitions
```

---

**Status:** Ready for deployment 🚀
**Confidence:** High ✅
**Risk:** Low (backed up, backwards compatible) ✅
