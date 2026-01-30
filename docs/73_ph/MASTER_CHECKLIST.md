# VETKA Master Checklist - Phase 54-75
**Единый источник истины. По факту кода. Без дубликатов.**

**Last Audit:** 2026-01-20
**Verified Against:** Actual source code (not docs)
**For:** Claude Code Opus 4.5

---

## ✅ COMPLETED (Phase 54-64)

| # | Feature | Status | Phase | Location |
|----|---------|--------|-------|----------|
| 1 | Multi-model chat | ✅ | 56 | src/elisya/ |
| 2 | ModelProvider enum | ✅ | 64 | src/elisya/model_router_v2.py |
| 3 | LOD system (Google Maps) | ✅ | 62 | src/layout/ |
| 4 | File preview on hover | ✅ | 61 | client/src/components/ |
| 5 | Multi-file pin (Ctrl+Click) | ✅ | 61 | client/src/store/useStore.ts |
| 6 | God object split (Phase 64) | ✅ | 64 | user_message_handler.py split started |
| 7 | User messages saving | ✅ | 64 | data/chat_history.json |
| 8 | Unified key manager | ✅ | 63 | src/elisya/api_key_detector.py |
| 9 | Group chat (agent teams) | ✅ | 57 | src/api/handlers/group_message_handler.py |
| 10 | LangGraph 1.0 | ✅ | 29+ | src/orchestration/ |
| 11 | Researcher agent | ✅ | ? | src/orchestration/agents/ |

---

## 🔴 HIGH PRIORITY - IN PROGRESS (Phase 65-66)

### Phase 65: Branch Context + Search

| # | Feature | Status | Time | Code Location | Notes |
|----|---------|--------|------|---|---|
| 1 | Branch pin (Shift+Click) | ⏳ IN PROGRESS | 2-3h | client/src/ | Select folder → pin all files |
| 2 | Folder context (Click) | ⏳ IN PROGRESS | 3-4h | src/api/handlers/ | Folder → AI context |
| 3 | Text search (keyword) | ✅ DONE | 4-5h | src/search/hybrid_search.py | BM25 working |
| 4 | Semantic search (Qdrant) | ✅ DONE | 6-8h | src/memory/qdrant_client.py | Embeddings integrated |

**Status:** Text + Semantic search COMPLETE, UI components IN PROGRESS
**Blocker:** None - can start Phase 66

### Phase 66: Tree Improvements

| # | Feature | Status | Time | Code Location | Notes |
|----|---------|--------|------|---|---|
| 1 | Move branch (not node) | ⏳ PENDING | 3-4h | client/src/components/canvas/ | Drag entire folder |
| 2 | Sugiyama directed fix | ⏳ PENDING | 4-6h | src/layout/semantic_sugiyama.py | Fix formula (642 lines, large) |
| 3 | Live tree physics | ⏳ PENDING | 6-8h | client/src/hooks/useDrag3D.ts | Drag root → all move |

**Status:** All PENDING
**Blockers:** Sugiyama is large file (642 lines), needs focused work

---

## 🟡 MEDIUM PRIORITY - NEXT PHASES (Phase 67-68)

### Phase 67: Knowledge Mode

| # | Feature | Status | Time | Code Location | Notes |
|----|---------|--------|------|---|---|
| 1 | Knowledge graph layout | ⏳ PENDING | 4-5h | src/layout/knowledge_layout.py | **CRITICAL: 2502 lines, planned redesign** |
| 2 | Semantic links | ⏳ PENDING | 4-5h | src/layout/ | Graph edges between files |
| 3 | Create new trees UI | ⏳ PENDING | 4-5h | client/src/components/ | UI for tree creation |

**Status:** All PENDING
**CRITICAL ISSUE:** knowledge_layout.py (2502 lines) - DO NOT REFACTOR, plan complete redesign instead

### Phase 68: JARVIS Mode (Advanced Agent Orchestration)

| # | Feature | Status | Time | Code Location | Notes |
|----|---------|--------|------|---|---|
| 1 | Auto model rotation | ⏳ PENDING | 8-10h | src/elisya/ | Switch models seamlessly |
| 2 | User memory system | ⏳ PENDING | 10-15h | src/memory/ | Remember user history |
| 3 | Unified agent facade | ⏳ PENDING | 10-15h | src/orchestration/ | One agent = many models |
| 4 | Chat-first settings | ⏳ PENDING | 5-6h | src/api/handlers/ | Configure via chat |

**Status:** All PENDING
**Blocker:** Needs Phase 67 completion

---

## ⚠️ IN ACTIVE DEVELOPMENT (Just Completed)

### Phase 72: Smart Scanning System ✅ MOSTLY DONE

| Component | Status | Lines | Notes |
|-----------|--------|-------|-------|
| Dependency dataclass | ✅ | 221 | Phase 72.1 |
| BaseScanner ABC | ✅ | 161 | Phase 72.1 |
| Python import resolver | ✅ | 484 | Phase 72.2 |
| Python AST scanner | ✅ | 461 | Phase 72.3 |
| Known packages registry | ✅ | 238 | Phase 72.3/72.4 |
| Dependency calculator (Kimi K2) | ✅ (stabilizing) | 703 | Phase 72.4 - **JUST MADE, STILL EVOLVING** |

**Status:** 72.1-72.4 DONE, 72.5+ TBD
**Note:** dependency_calculator.py made yesterday, still working on it - **DO NOT SEND TO REFACTORING YET**
**Tests:** 216+ passing, 95% coverage

### Phase 68 Revisions: Hybrid Search + RRF ✅ BACKEND READY

| Component | Status | Lines | Notes |
|-----------|--------|-------|-------|
| BM25 keyword search | ✅ | ~200 | Via Weaviate |
| Qdrant semantic search | ✅ | ~200 | Via Qdrant client |
| RRF fusion | ✅ | 260 | src/search/rrf_fusion.py |
| Search socket handler | ✅ | ~500 | src/api/handlers/search_handlers.py |
| Search REST endpoints | ✅ | ~300 | src/api/routes/semantic_routes.py |

**Status:** Backend 100% DONE
**Issue:** Frontend UI component needs decomposition (made yesterday, 1181 lines in ONE file)
**Note:** UnifiedSearchBar.tsx made yesterday - **DO NOT SEND TO REFACTORING YET, let it mature**

### Phase 71: Dependency Formula (DEP) ✅ DOCUMENTED

| Component | Status | Lines | Notes |
|-----------|--------|-------|-------|
| DEP formula with temporal decay | ✅ | Formula doc | Sigmoid + Kimi K2 |
| 4-source validation | ✅ | 850 lines | 99% consensus from experts |
| Python implementation | ✅ | Ready | docs/71_ph/README.md |

**Status:** DOCUMENTED + VALIDATED, implementation ready
**Location:** docs/71_ph/

---

## 🚨 CRITICAL ISSUES & BUGS (Real Code Problems)

### Bug 1: Export Issue - MUST FIX
```
File: src/layout/__init__.py

PROBLEM: knowledge_layout.py (2502 lines) NOT exported
IMPACT: Import convention violation
FIX: Add to __init__.py:
  from .knowledge_layout import (
    KnowledgeTag, KnowledgeEdge, PrerequisiteChain, ...
  )
  __all__ = [...]

EFFORT: 5 minutes
PRIORITY: HIGH
```

### Bug 2: Debug Code Left In - SHOULD REMOVE
```
File: src/api/handlers/group_message_handler.py

PROBLEM: [GROUP_DEBUG] markers + print() statements left
IMPACT: Debug output in production
FIX: grep -r "[GROUP_DEBUG]" src/ && replace with logger.debug()

EFFORT: 15 minutes
PRIORITY: MEDIUM
```

### Todo Items - NOT BLOCKERS
```
5 TODO markers found in code:
  1. src/elisya/api_aggregator_v3.py:186 - Implement providers
  2. src/api/handlers/workflow_socket_handler.py:87 - Get from orchestrator
  3. src/mcp/vetka_mcp_bridge.py:432 - File listing endpoint
  4. src/mcp/vetka_mcp_bridge.py:470 - File search endpoint
  5. src/orchestration/cam_event_handler.py:341 - ChatHistoryManager

STATUS: Low priority, tracked
```

---

## 📊 REAL CODE STATUS (God Objects & Large Files)

### ✅ These Are Feature Objects (Not God Objects)
```
✅ api_key_detector.py (723 lines)
   - Centralized API key management
   - 70+ providers supported
   - Feature-complete, working
   - DO NOT REFACTOR (it's a feature, not legacy)
```

### ⏳ These Are Evolving (Not Ready to Refactor)
```
⏳ dependency_calculator.py (703 lines)
   - Made YESTERDAY, still evolving
   - DO NOT SEND TO REFACTORING YET
   - Wait 2 weeks to stabilize

⏳ UnifiedSearchBar.tsx (1181 lines)
   - Made YESTERDAY/DAY BEFORE
   - Still needs integration testing
   - DO NOT SEND TO REFACTORING YET
   - Wait 2-3 weeks to mature

⏳ user_message_handler.py (1666 lines)
   - Still incomplete ("much still to do")
   - DO NOT REFACTOR INCOMPLETE CODE
   - Complete features first, refactor after
```

### 🔄 These Are Planned Redesigns (Not Refactoring)
```
🔄 knowledge_layout.py (2502 lines)
   - Planned complete redesign since December
   - DO NOT SEND TO INCREMENTAL REFACTORING
   - Redesign first, refactor new version after
```

### 📌 These CAN Be Safely Refactored (If Needed)
```
📌 api_gateway.py (600 lines) - Stable routing logic
📌 semantic_sugiyama.py (642 lines) - Layout algorithm
📌 fan_layout.py (634 lines) - Layout algorithm
📌 hybrid_search.py (513 lines) - Core search (but works fine as-is)
```

---

## 🎯 WHAT TO DO NOW (For Opus 4.5)

### Immediate Fixes (1-2 hours total)
```
[ ] 1. Fix export issue in src/layout/__init__.py (5 min)
[ ] 2. Remove debug code from group_message_handler.py (15 min)
[ ] 3. Run tests to verify no breakage (15 min)
```

### Phase 65 Completion (5-10 hours)
```
[ ] 1. Finish branch pin (Shift+Click) (2-3h)
[ ] 2. Implement folder context (3-4h)
[ ] 3. Test search integration (2-3h)
```

### Phase 66 Work (13-18 hours)
```
[ ] 1. Move branch feature (3-4h)
[ ] 2. Fix Sugiyama layout (4-6h) - WATCH OUT: 642 line file
[ ] 3. Live tree physics (6-8h)
```

### WAIT (Don't Work On Yet)
```
❌ DON'T: Send dependency_calculator.py to refactor (wait 2 weeks)
❌ DON'T: Send UnifiedSearchBar.tsx to refactor (wait 2-3 weeks)
❌ DON'T: Send user_message_handler.py to refactor (incomplete)
❌ DON'T: Send knowledge_layout.py to refactor (redesign planned)
❌ DON'T: Refactor api_key_detector.py (works, not needed)
```

---

## 📅 TIMELINE (Estimate)

| Phase | Duration | Status | Priority |
|-------|----------|--------|----------|
| 65: Branch + Search | 15-20h | 50% DONE | 🔴 HIGH |
| 66: Tree Improvements | 13-18h | NOT STARTED | 🔴 HIGH |
| 67: Knowledge Mode | 12-15h | NOT STARTED | 🟡 MEDIUM |
| 68: JARVIS | 35-45h | NOT STARTED | 🟢 ADVANCED |
| **Total** | **~75-100h** | | |
| **Per Day (4h)** | **~3-4 weeks** | | |

---

## ✨ KEY INSIGHTS

### What's Actually Working
```
✅ Multi-model support (all providers)
✅ Key management (centralized, smart)
✅ Search backend (keyword + semantic + RRF)
✅ Scanning foundation (Phase 72)
✅ Dependency formula (DEP, validated)
✅ Group chat (team agents)
```

### What's Not Ready
```
❌ Search UI (needs decomposition, but works)
❌ Knowledge graph (planned redesign)
❌ JARVIS mode (needs Phase 67 first)
❌ Auto-research (depends on search)
```

### What Needs Attention
```
⚠️ knowledge_layout.py - Plan redesign, don't refactor incrementally
⚠️ user_message_handler.py - Complete features first
⚠️ dependency_calculator.py - Let stabilize 2 weeks
⚠️ UnifiedSearchBar.tsx - Let mature 2-3 weeks
⚠️ Export bug - Fix immediately
⚠️ Debug code - Clean up
```

---

## 📝 FOR NEXT CHAT SESSION

**TL;DR for Opus 4.5:**

1. **Now:** Fix 2 bugs (export + debug code) - 20 minutes
2. **Today:** Complete Phase 65 - branch pin + folder context (5-8h)
3. **This week:** Start Phase 66 - move branch + Sugiyama (13-18h)
4. **Don't:** Refactor those 4 files (they're either new, incomplete, or planned redesign)
5. **Timeline:** ~3-4 weeks for Phase 65-66 at 4h/day

**Critical Files to Remember:**
- `knowledge_layout.py` = 2502 lines, complete redesign planned
- `UnifiedSearchBar.tsx` = 1181 lines, made yesterday, needs 2-3 weeks
- `dependency_calculator.py` = 703 lines, made yesterday, needs 2 weeks

---

**Single Source of Truth - All Verified Against Real Code**

**Generated:** 2026-01-20 07:30 UTC
**Status:** Ready for Opus 4.5
**Next:** Copy this and send to Opus 4.5 in new chat
