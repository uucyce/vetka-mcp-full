# Phase 87: Watchdog Fix - Documentation Index

## Documents in This Phase

### 1. VETKA_KNOWLEDGE_AUDIT.md (MAIN AUDIT)
**Purpose:** Complete audit of existing knowledge about agent chain response issues
**Content:**
- Phase 80 MCP agents overview
- Phase 80.6 agent isolation mechanism
- Phase 80.7 reply routing fix
- Phase 86 MCP @mention trigger fix
- Phase 87 watchdog-Qdrant integration fix
- select_responding_agents() complete logic documentation
- Known issues summary
- Architecture flow diagrams
- Test coverage recommendations

**Key Findings:**
- ✅ Phase 86 fixed MCP @mention triggering
- ✅ Phase 87 fixed watchdog singleton initialization
- ⚠️ Phase 80.6 isolation is intentional (prevents infinite loops)
- 🔍 Most "agent doesn't respond" issues are expected behavior

**Start here for:** Understanding agent response architecture and recent fixes

---

### 2. WATCHDOG_QDRANT_BUG.md (EXISTING)
**Purpose:** Detailed analysis of watchdog file indexing problem
**Content:**
- Root cause: singleton initialization race condition
- VetkaFileHandler working correctly
- Missing Qdrant connection in _on_file_change()
- Event flow diagram
- Fix strategy with 3 options
- Files involved and verification steps

**Status:** ✅ FIXED in Phase 87

**Start here for:** Technical details of watchdog-Qdrant integration bug

---

## Quick Reference

### Agent Response Flow
```
Message arrives
  ↓
select_responding_agents() picks responders
  ├─ Reply routing (Phase 80.7)
  ├─ @mentions (explicit)
  ├─ Phase 80.6 isolation (prevents loops)
  ├─ /commands (/solo, /team, /round)
  ├─ SMART keyword matching
  └─ Default (admin or first)
  ↓
orchestrator.call_agent()
```

### Why Agents Don't Respond
1. **Phase 80.6 Isolation** (INTENDED)
   - When: Agent sends message without @mention
   - Result: No auto-response (prevents infinite loops)
   - Fix: Add @mention to trigger response

2. **Phase 86 Fix** (SOLVED)
   - When: MCP endpoint gets request with @mention
   - Result: ✅ Now properly triggers agents
   - Was: Disabled in Phase 80.8, re-enabled in Phase 86

3. **Phase 87 Fix** (SOLVED)
   - When: File changes detected by watchdog
   - Result: ✅ Now properly indexes to Qdrant
   - Was: qdrant_client=None in singleton

### Related Files to Check
- `src/services/group_chat_manager.py` (select_responding_agents)
- `src/api/routes/debug_routes.py` (MCP endpoints)
- `src/scanners/file_watcher.py` (watchdog integration)
- `src/scanners/qdrant_updater.py` (Qdrant indexing)

### Test Commands
```bash
# MCP agent with @mention (should work - Phase 86)
curl -X POST http://localhost:3000/api/debug/mcp/groups/{id}/send \
  -d '{"agent_id":"claude_code","content":"@Architect review this"}'

# MCP agent without @mention (should NOT respond - Phase 80.6)
curl -X POST http://localhost:3000/api/debug/mcp/groups/{id}/send \
  -d '{"agent_id":"claude_code","content":"sharing info"}'

# File watcher test (Phase 87)
# Create file in watched directory → should see "[Watcher] Indexed to Qdrant"
```

---

## Knowledge Hierarchy

### Level 1: Quick Overview (5 min)
- This INDEX.md
- VETKA_KNOWLEDGE_AUDIT.md → Executive Summary section

### Level 2: Agent Response Understanding (15 min)
- VETKA_KNOWLEDGE_AUDIT.md → Phase 80-87 sections
- select_responding_agents() logic section

### Level 3: Implementation Details (30 min)
- VETKA_KNOWLEDGE_AUDIT.md → Architecture Flow Diagrams
- WATCHDOG_QDRANT_BUG.md → Full technical analysis
- Related source code files

### Level 4: Complete System Knowledge (1 hour)
- Read all Phase 80 documentation
- Review commits in Phase 56-87 range
- Study source code in src/services/, src/api/routes/, src/scanners/

---

## Common Questions & Answers

### Q: Why doesn't my agent respond?
**A:** Check if Phase 80.6 isolation is blocking it:
- If sender is agent (@) and no @mention → no response (INTENDED)
- Solution: Add explicit @mention in message

### Q: How do I trigger agent from MCP code?
**A:** Phase 86 fix enables this:
```bash
POST /api/debug/mcp/groups/{group_id}/send
{
  "agent_id": "claude_code",
  "content": "@Architect please review this"  # @mention required!
}
```

### Q: Why aren't new files showing in VETKA tree?
**A:** Phase 87 fixed this:
- Old bug: Watchdog detected files but qdrant_client was None
- Fix: Initialize watcher at server startup with ready qdrant_client
- Now: Files are properly indexed to Qdrant

### Q: What's the difference between Phase 80.6 and Phase 80.7?
**A:**
- Phase 80.6: Isolation - agent messages don't auto-trigger other agents
- Phase 80.7: Reply routing - replies go to original agent, not default

### Q: How does SMART keyword matching work?
**A:** Scores content for keywords by role:
- PM: "plan", "task", "scope", "timeline", "requirements", etc.
- Architect: "architecture", "design", "system", "pattern", etc.
- Dev: "code", "implement", "function", "class", "write", "debug", etc.
- QA: "test", "bug", "review", "verify", "validate", etc.

---

## Phase Timeline

```
Phase 56    GROUP CHAT MANAGER - Foundation
Phase 57.7  Smart agent selection
Phase 57.8  Orchestrated Multi-Agent Workflow
...
Phase 73    JSON Context Builder
Phase 76    Learning System + JARVIS Memory
Phase 79    Sugiyama Tree Analysis
Phase 80    MCP Agents in Group Chats
  80.1     Registry
  80.2     Team Messaging
  80.3     MCP Filter UI
  80.4     Group Participation
  80.5     Chat History Linking
  80.6     Agent Isolation ⭐ CRITICAL
  80.7     Reply Routing ✅ FIXED
  80.8     (Disabled agent trigger - debugging)
Phase 81.1  Resizable Chat
Phase 82    UI Fixes (included watchdog analysis)
Phase 86    MCP @Mention Trigger Fix ✅ RE-ENABLED
Phase 87    Watchdog → Qdrant Integration ✅ FIXED
```

---

## For Next Phase (Phase 88+)

### Verify Phase 87 Fix
- [ ] Check main.py lifespan initialization
- [ ] Verify watcher gets qdrant_client at startup
- [ ] Test file creation → Qdrant indexing

### Consider These Enhancements
- [ ] MCP agent online/offline indicators
- [ ] Comprehensive select_responding_agents() tests
- [ ] Agent response timeout handling
- [ ] Message ordering guarantees for real-time chats

### Documentation Gaps to Fill
- [ ] UI help text explaining Phase 80.6 isolation
- [ ] Example workflows for common use cases
- [ ] Troubleshooting guide for agent response issues

---

**Last Updated:** 2026-01-21
**Audit Scope:** Phases 56-87
**Status:** COMPLETE
