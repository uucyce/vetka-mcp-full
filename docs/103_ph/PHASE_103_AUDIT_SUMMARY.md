# Phase 103 Audit Summary
**Date:** 2026-01-31
**Agents:** 6 Haiku + 1 Sonnet (Phase 1) → 5 Sonnet Verifiers (Phase 2)
**Status:** P0 FIXES APPLIED ✅

---

## Executive Summary

| Area | Issues | Critical |
|------|--------|----------|
| Group Chat Triggers | 7 markers | 3 |
| Agent Call Chain | 6 markers | 2 |
| Socket/Logic Breaks | 10 issues | 3 |
| Dead Code | 4 items | 1 |
| Duplicates | 7 functions | 2 |
| MCP Architecture | documented | - |

---

## 1. GROUP CHAT: Why Agents Don't Respond

### Root Cause
**No default trigger.** User message without @mention → nobody responds.

### MARKER_103_GC1: Three blocking conditions
**File:** `src/services/group_chat_manager.py:229-291`
- Line 289: Agent sender + no @mention → return []
- Line 270: @mention not in participants → return []
- Line 275: Smart reply only if decay < threshold

### MARKER_103_GC2: Agent-to-agent requires @mention
**File:** `src/api/handlers/group_message_handler.py:682-703`
- Agents can't talk to each other without explicit @mention

### MARKER_103_GC4: Hostess router REMOVED
**File:** `src/api/handlers/group_message_handler.py:690-692`
- Phase 57.8.2 removed Hostess (intelligent dispatcher)
- No replacement = no guaranteed response

### MARKER_103_GC5: Keyword matching too limited
**File:** `src/services/group_chat_manager.py:334-356`
- Hardcoded list misses common queries
- Code never triggers (4 early returns before it)

---

## 2. AGENT CALL CHAIN: Broken Context

### MARKER_103_CHAIN1: Architect missing from chain
**File:** `src/orchestration/orchestrator_with_elisya.py:1566-1568`
- PM added to chain ✅
- Architect NOT added ❌
- Dev/QA NOT added ❌

### MARKER_103_CHAIN2: Threading deadlock
**File:** `src/orchestration/orchestrator_with_elisya.py:1674-1675`
```python
# asyncio.run() inside threads = event loop conflict
dev_thread = threading.Thread(target=run_dev)  # WRONG
```
**Fix:** Replace with `asyncio.gather()`

### MARKER_103_CHAIN3: State overwrite race
**File:** Line 1697-1700
- QA overwrites Dev state if finishes last

---

## 3. SOCKET/LOGIC BREAKS

### Critical (Fix Now)
| Marker | Issue | Location |
|--------|-------|----------|
| **GC7** | Qdrant sync blocks 5+ min | After each agent |
| **GC3** | Message ordering race | group_message emit |
| **GC9** | Concurrent messages interleave | previous_outputs dict |

### High Priority (Missing Handlers)
| Marker | Emit | Frontend Handler |
|--------|------|-----------------|
| GC1 | `group_created` | MISSING |
| GC2 | `group_participant_updated` | MISSING |

---

## 4. DEAD CODE

| File | Status | Action |
|------|--------|--------|
| `user_message_handler_v2.py` | DEAD | Mark @status dead |
| `main.py:134,627` | Orphaned api_gateway refs | Delete |
| `chat_handler.py:90-105` | is_local_ollama_model() deprecated | Remove export |
| `health_routes.py:33,233` | api_gateway in checks | ✅ FIXED |

---

## 5. DUPLICATE FUNCTIONS

### Critical
| Function | Locations | Fix |
|----------|-----------|-----|
| `call_model()` x3 | api_aggregator_v3, provider_registry, ModelClient | Consolidate to provider_registry |
| `add_message()` x4 | chat managers | Define canonical location |

### Medium
- `stream_response()` x2 - 2-layer indirection
- `get_chat_messages()` x2 - HTTP wrapper

---

## 6. MCP ARCHITECTURE (Sonnet Report)

### Concurrency
- **No hardcoded limit** on parallel agents
- Recommended: MAX_PARALLEL_PIPELINES = 5
- Fire-and-forget via `asyncio.create_task()`

### Spawn Mechanism
```
Task → Architect (breaks down)
  → Subtasks (sequential!)
    → Research (if needs_research)
    → Coder (executes)
```
**Note:** Subtasks run SEQUENTIAL, not parallel (flag exists but not implemented)

### Streaming to Group Chat
- Works via HTTP POST to `/api/chat/send`
- NOT Socket.IO
- Pattern: `_emit_progress(role, message, idx, total)`

### Anthropic Timeout
- 30 sec hardcoded on their side
- Cannot fix in VETKA

---

## 7. CHAT HISTORY GUIDE

### Storage Architecture
```
JSON (Primary) → data/chat_history.json
Qdrant (Optional) → VetkaGroupChat collection
Staging → data/staging.json (artifacts on review)
```

### Data Flow
```
add_message() → JSON
extract_artifacts() → staging.json
upsert_chat_message() → Qdrant (optional)
```

### Gap
Artifact doesn't know which message created it (no message_id in staging)

---

## 8. DUAL-STACK HYGIENE

### Violations Found
- Voice module may have browser API refs (needs verification)
- call_model fragmented between phases

### Clean
- @status coverage: 100% (35/35 files)
- No circular dependencies

---

## Priority Actions

### P0 - COMPLETED ✅
1. ✅ Remove api_gateway from health_routes.py - DONE
2. ✅ GC7: Wrap Qdrant in asyncio.create_task() - DONE (both files)
3. ✅ CHAIN2: Replace threading with asyncio.gather() - DONE
4. ✅ CHAIN3: Merge states instead of overwrite - DONE

### P1 - In Progress (Sonnet agents working)
5. 🔄 Add default trigger (Hostess replacement)
6. 🔄 Add missing socket handler (group_participant_updated)
7. 🔄 Consolidate call_model() audit
8. 🔄 Link artifact to source message

### P1 - Verified as FALSE POSITIVES (skip)
- ~~GC3: Message ordering~~ - works correctly
- ~~GC9: Add group locks~~ - local variable, no race

### P2 - Next Sprint
9. Implement parallel subtasks in spawn
10. Add MAX_PARALLEL_PIPELINES semaphore

---

## Questions for Grok

1. Best pattern for default agent selection without Hostess?
2. Socket.IO vs HTTP POST for pipeline streaming - tradeoffs?
3. How to link artifact back to source message?

---

---

## Phase 2: Sonnet Verification Results

### Verification Stats
| Haiku Report | REAL | FAKE | False Positive % |
|--------------|------|------|------------------|
| GC Triggers | 5 | 2 | 29% |
| Chain | 3 | 0 | 0% |
| Socket/Logic | 2 | 2 | 50% |
| Duplicates | 0 | 4 | 100% |
| Dead Code | 1 | 1 | 50% |
| **TOTAL** | **11** | **9** | **45%** |

### Markers Applied ✅
- `MARKER_103_CHAIN1` → orchestrator_with_elisya.py:1566
- `MARKER_103_CHAIN2` → orchestrator_with_elisya.py:1675
- `MARKER_103_CHAIN3` → orchestrator_with_elisya.py:1699
- `MARKER_103_GC7` → group_message_handler.py:988
- `MARKER_103_GC7` → group_chat_manager.py:639

### Dead Code Archived ✅
- `user_message_handler_v2.py` → `backup/phase_103_dead_code/`

### Orphaned Code Removed ✅
- `main.py:134` - api_gateway assignment
- `main.py:627` - api_gateway status

### False Positives (NOT issues) ❌
- GC3: Message ordering - works correctly
- GC9: previous_outputs - local variable, no race
- All duplicates: Different signatures/classes
- is_local_ollama_model(): Deprecated but actively used

---

*Generated by: Claude Opus 4.5 + 12 agents (6 Haiku + 6 Sonnet)*
*Phase: 103.3 VERIFIED*
