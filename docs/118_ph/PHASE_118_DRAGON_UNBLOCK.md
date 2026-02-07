# Phase 118: Unblock @dragon — Sync Blockers, Logging, Weaviate Upsert

> **Created:** 2026-02-07 | **After:** Phase 117.7 (`8d6be290`) + 117.8 (`26ea95a1`)
> **Goal:** Make @dragon pipeline visible in chat + stop VETKA from freezing

---

## What Phase 117 Fixed (DONE)

| Phase | Fix | Marker | Status |
|-------|-----|--------|--------|
| 117.7 | Solo chat_id passed to pipeline | MARKER_117.7A | ✅ |
| 117.7 | display_name fallback (no "unknown") | MARKER_117.7B | ✅ |
| 117.7 | Weaviate v3→v4 migration | MARKER_117.7C | ✅ |
| 117.8 | _emit_progress → async + SocketIO | MARKER_117.8B | ✅ |
| 117.8 | sio/sid in AgentPipeline | MARKER_117.8A | ✅ |
| 117.8 | Removed default Lightning UUID | MARKER_117.8C | ✅ |

---

## What Still Breaks (Phase 118 Targets)

### 118.1: SYNC EMBEDDING — PRIMARY BLOCKER ⚠️

**MARKER_118.1** | `src/utils/embedding_service.py`

`ollama.embeddings()` (line 66) and `ollama.embed()` (line 119) are **synchronous**.
They block the entire async event loop for 200ms-5s per call.
During @dragon, embedding calls from TripleWrite/scanner freeze everything.

**Fix:** `asyncio.to_thread()` or `ollama.AsyncClient()`

---

### 118.2: WEAVIATE UPSERT RACE CONDITION

**MARKER_118.2** | `src/orchestration/triple_write_manager.py` lines 376-398

Pattern: `get_by_id()` → None → `insert()` → 422 "already exists" (concurrent write).
**Fix:** Insert-first → catch 422 → replace. Pattern exists in `scripts/sync_qdrant_to_weaviate.py`.

---

### 118.3: httpx LOG FLOOD

**MARKER_118.3** | `main.py` lines 34-36

`logging.basicConfig(level=logging.INFO)` runs BEFORE `setup_logging()`.
httpx INFO messages flood terminal (~30% of all log lines).
**Fix:** Remove basicConfig from main.py or add early suppression.

Suppression list: `src/initialization/logging_setup.py` lines 105-127.

---

### 118.4: LOCAL MODEL DEFAULT / MODEL SELECTOR

**MARKER_118.4** | `src/agents/hostess_agent.py` lines 270-308

Without @mention, Hostess routes to local Ollama (qwen2:7b, line 308).
This interferes with @dragon and blocks event loop.
**Fix:** Mute local models + add model selector UI ("phone book").

---

### 118.5: ENGRAM ATTRIBUTE ERRORS

**MARKER_118.5** | `src/memory/engram_user_memory.py` line 167

- `self.qdrant.scroll()` → `QdrantVetkaClient` has no `scroll` method (use `self.qdrant.client.scroll()`)
- `get_all_preferences()` → method doesn't exist (correct: `_qdrant_get_full()`)

---

### 118.6: LIVE VERIFICATION

After all fixes, test `@dragon` in solo chat:
- Progress messages visible in real-time
- VETKA doesn't freeze
- No httpx log flood
- No Weaviate 422 errors

---

## Scout Markers — НЕ РАЗВЕДЫВАТЬ ПОВТОРНО

```
🏁 SCOUTED by Haiku 2026-02-07:

✅ src/utils/embedding_service.py:66,119  → SYNC ollama calls
✅ src/orchestration/triple_write_manager.py:376-398  → TOCTOU upsert race
✅ main.py:34-36  → basicConfig before setup_logging
✅ src/initialization/logging_setup.py:105-127  → httpx suppression list
✅ src/agents/hostess_agent.py:270-308  → local Ollama default
✅ src/memory/engram_user_memory.py:167  → scroll() missing on wrapper
✅ src/memory/qdrant_client.py:692+  → proxy methods, no scroll()
✅ scripts/sync_qdrant_to_weaviate.py  → correct upsert pattern exists
```

---

## Execution Priority

1. **118.1** — Async embeddings (unblocks event loop) — CRITICAL
2. **118.2** — Weaviate upsert fix — HIGH
3. **118.3** — httpx logging cleanup — MEDIUM
4. **118.5** — Engram errors — MEDIUM
5. **118.4** — Model selector UI — LOW (larger scope)
6. **118.6** — Live verification — FINAL
