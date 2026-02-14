# CODEX BRIEF — Phase 149
## Priority: P0 (BUG-1) → P1 (S1.2) → P2 (Tests)

---

## TASK C-149.1: Fix BUG-1 Scanner Duplicates (CRITICAL)

**Problem:** 3D tree shows 2-3x duplicate files. Scanner/indexer creates multiple entries for same file.

**Investigation steps:**
1. Find scanner code: `src/scanner/` or similar
2. Look for file indexing/Qdrant insertion logic
3. Check if dedup exists — if not, add it
4. Check if watcher triggers re-scan without clearing old entries

**Root cause hypothesis:**
- Watcher detects file change → triggers full re-scan → adds NEW entries without removing OLD
- OR: multiple scanner passes (initial + watcher) create duplicates

**Fix approach:**
- Before insert: check if file already exists in Qdrant by path
- If exists: UPDATE, don't INSERT
- OR: add dedup pass after scan (group by path, keep latest)

**Test:** After fix, query Qdrant for any path — should return exactly 1 result.

**Files to investigate:**
- `src/scanner/` directory
- `src/services/semantic_tagger.py` or similar indexer
- Qdrant insertion logic

**Boundaries:** Do NOT modify `agent_pipeline.py`, `task_board.py`, or any MCP server code.

---

## TASK C-149.2: Complete S1.2 Unified Search Web Provider

**Current state:** 70% done. Stub exists in `src/api/handlers/unified_search.py`.

**What's needed:**
1. Wire `vetka_web_search` (Tavily API) as 'web' source
2. Score normalization: web results scored 0-1 same as code/semantic results
3. Result format: `{ source: "web", title, url, snippet, score }`
4. Timeout: 5s max for web search, don't block other sources
5. Graceful fallback: if Tavily fails, return empty results (not error)

**Files:**
- `src/api/handlers/unified_search.py` — main file to modify
- Check for existing Tavily integration in `src/mcp/tools/` for reference

**Test:** Search for "React hooks" should return web results alongside code results.

---

## TASK C-149.3: E2E Tests for Playground Review Flow (AFTER Dragon lands)

**Wait until:** D-149.1 through D-149.4 are promoted to main.

**Test scenarios:**
1. Create playground → verify worktree exists
2. Run pipeline in playground → verify files created in worktree (not main)
3. Review playground → verify diff returned correctly
4. Promote playground → verify files appear in main codebase
5. Reject playground → verify worktree destroyed

**Files:** `tests/test_phase149_playground_e2e.py` (NEW)

---

## EXECUTION ORDER

1. **C-149.1 FIRST** (P0 — scanner duplicates)
2. **C-149.2 SECOND** (P1 — unified search)
3. **C-149.3 LAST** (P2 — after Dragon work lands)

---

*Brief by Opus Commander | Phase 149*
