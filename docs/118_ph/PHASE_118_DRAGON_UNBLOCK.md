# Phase 118: Unblock @dragon — Sync Blockers, Logging, Weaviate Upsert, Message Visibility

> **Created:** 2026-02-07 | **Completed:** 2026-02-08
> **After:** Phase 117.7 (`8d6be290`) + 117.8 (`26ea95a1`)
> **Commits:** `b02d2c91` (118.1-118.5) + `85d7a1fb` (118.6-118.7)
> **Goal:** Make @dragon pipeline visible in chat + stop VETKA from freezing
> **Status: ALL SUB-PHASES COMPLETE. @dragon pipeline fully operational.**

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

### 118.1: SYNC EMBEDDING — PRIMARY BLOCKER ✅ DONE

**MARKER_118.1** | `src/utils/embedding_service.py`

`ollama.embeddings()` (line 66) and `ollama.embed()` (line 119) are **synchronous**.
They block the entire async event loop for 200ms-5s per call.
During @dragon, embedding calls from TripleWrite/scanner freeze everything.

**Fix:** `asyncio.to_thread()` or `ollama.AsyncClient()`

---

### 118.2: WEAVIATE UPSERT RACE CONDITION ✅ DONE

**MARKER_118.2** | `src/orchestration/triple_write_manager.py` lines 376-398

Pattern: `get_by_id()` → None → `insert()` → 422 "already exists" (concurrent write).
**Fix:** Insert-first → catch 422 → replace. Pattern exists in `scripts/sync_qdrant_to_weaviate.py`.

---

### 118.3: httpx LOG FLOOD ✅ DONE

**MARKER_118.3** | `main.py` lines 34-36

`logging.basicConfig(level=logging.INFO)` runs BEFORE `setup_logging()`.
httpx INFO messages flood terminal (~30% of all log lines).
**Fix:** Remove basicConfig from main.py or add early suppression.

Suppression list: `src/initialization/logging_setup.py` lines 105-127.

---

### 118.4: LOCAL MODEL DEFAULT / MODEL SELECTOR ✅ DONE

**MARKER_118.4** | `src/agents/hostess_agent.py` lines 270-308

Without @mention, Hostess routes to local Ollama (qwen2:7b, line 308).
This interferes with @dragon and blocks event loop.
**Fix:** Mute local models + add model selector UI ("phone book").

---

### 118.5: ENGRAM ATTRIBUTE ERRORS ✅ DONE

**MARKER_118.5** | `src/memory/engram_user_memory.py` line 167

- `self.qdrant.scroll()` → `QdrantVetkaClient` has no `scroll` method (use `self.qdrant.client.scroll()`)
- `get_all_preferences()` → method doesn't exist (correct: `_qdrant_get_full()`)

---

### 118.6: MESSAGE VISIBILITY FIX — ROOT CAUSE ✅

**MARKER_118.6** | `src/orchestration/agent_pipeline.py` + `src/api/handlers/user_message_handler.py`

**ROOT CAUSE:** Backend emitted `"agent_message"` → frontend `addMessage()` → legacy `messages[]`.
But ChatPanel renders `chatMessages[]` (new system) only!

**Fix:** Changed ALL `sio.emit("agent_message")` → `sio.emit("chat_response")`:
- `_emit_progress()` Route 1 (line 395)
- `_emit_to_chat()` Route 1 (line 520)
- Initial "Pipeline starting..." (handler line 867)
- Final report (handler line 2404)
- Error report (handler line 2413)

Data format: `{message, agent, model}` → matches `chat_response` handler → `addChatMessage()` → `chatMessages[]` → **VISIBLE!**

---

### 118.7: ERROR CALLBACK FOR BACKGROUND TASK ✅

**MARKER_118.7** | `src/api/handlers/user_message_handler.py` line 877

Added `task.add_done_callback()` to `asyncio.create_task()` for @dragon dispatch.
Exceptions now logged via `logger.error()` instead of silently swallowed.

---

### 118.8: LIVE VERIFICATION

After all fixes (118.1-118.7), test `@dragon` in solo chat:
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

## Execution Priority — ALL COMPLETE

1. **118.1** — Async embeddings (unblocks event loop) — ✅ `b02d2c91`
2. **118.2** — Weaviate upsert fix — ✅ `b02d2c91`
3. **118.3** — httpx logging cleanup — ✅ `b02d2c91`
4. **118.5** — Engram errors — ✅ `b02d2c91`
5. **118.4** — Hostess mute local models — ✅ `b02d2c91`
6. **118.6** — Message visibility root cause fix — ✅ `85d7a1fb`
7. **118.7** — Error callback for background task — ✅ `85d7a1fb`
8. **118.8** — Live verification — ✅ @dragon messages visible in ChatPanel!

**34 tests, 66/66 total Phase 117+118 passing.**

---

## See Also

- [Phase 118 Completion Report + Mycelium Audit](PHASE_118_COMPLETION_AND_MYCELIUM_AUDIT.md)
