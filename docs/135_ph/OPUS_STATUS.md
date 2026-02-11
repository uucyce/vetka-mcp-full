# Phase 135 — Opus Status Report

## Session: 2026-02-11

### Mission
Stabilize Mycelium pipeline: feedback loop, async safety, file writes.

### Completed

#### 1. Feedback Loop Closure (MARKER_135.FB_LOOP)
- **feedback_service.py**: Added `get_feedback_for_architect()` — builds concise summary from past reports
- **agent_pipeline.py**:
  - MARKER_135.FB_LOOP_A: Load feedback before architect call
  - MARKER_135.FB_LOOP_B: Inject feedback into architect's prompt (max 600 chars)
  - MARKER_135.FB_LOOP_C: Generate real improvements from verifier issues, retry counts, tier upgrades

**Proven working**: Architect receives `[FEEDBACK FROM PAST RUNS]` with issues, improvements, patterns.

#### 2. Async Safety Fix (MARKER_135.FIX_ASYNC)
- **llm_call_tool_async.py**: Wrapped `_gather_inject_context` with 5s global timeout + 3s per-section timeouts
- Engram prefs via `run_in_executor` (sync → thread pool)
- Semantic search with asyncio.wait_for timeout

**Root cause**: Sync Qdrant/Ollama calls blocked async event loop → pipeline hung forever.

#### 3. Import Guard (MARKER_135.FIX_IMPORT)
- **services/__init__.py**: try/except for activity_hub import (requires socketio)
- Without this, `from src.services.feedback_service import save_report` failed in CLI/Mycelium context

#### 4. File Write Fixes (MARKER_135.SAFE_DIRS, MARKER_135.FIX_WRITE)
- **agent_pipeline.py**: Expanded safe_dirs from `('src/vetka_out', 'data/vetka_staging', 'data/artifacts')` to `('src/', 'data/', 'tests/')`
- Added forbidden files list: `__init__.py`, `agent_pipeline.py`, `mycelium_mcp_server.py`, `vetka_mcp_bridge.py`
- Added `"// file:"` pattern detection for Qwen-style output (previously only detected ``` fences)

**Proven working**: Pipeline creates real files in `src/utils/`.

#### 5. Stream Emit Fix (MARKER_135.FIX_EMIT)
- **agent_pipeline.py**: `_emit_to_chat()` now accepts both dict and str data

#### 6. Pipeline Breadcrumbs (MARKER_135.BREADCRUMB)
- **mycelium_mcp_server.py**: File-based status tracking at `data/feedback/pipeline_runs/{task_id}.json`
- Writes breadcrumbs: started → pipeline_created → completed/failed

#### 7. Tests
- **test_phase135_feedback_loop.py**: 25 tests covering entire feedback loop
- All 51 DAG + feedback tests passing

### Files Modified

| File | Markers |
|------|---------|
| `src/services/feedback_service.py` | MARKER_135.FB_LOOP |
| `src/orchestration/agent_pipeline.py` | MARKER_135.FB_LOOP_A/B/C, MARKER_135.FIX_SYNC, MARKER_135.SAFE_DIRS, MARKER_135.FIX_WRITE, MARKER_135.FIX_EMIT |
| `src/mcp/tools/llm_call_tool_async.py` | MARKER_135.FIX_ASYNC |
| `src/services/__init__.py` | MARKER_135.FIX_IMPORT |
| `src/mcp/mycelium_mcp_server.py` | MARKER_135.BREADCRUMB |

### Files Created

| File | Purpose |
|------|---------|
| `tests/test_phase135_feedback_loop.py` | 25 tests for feedback loop |
| `docs/135_ph/OPUS_STATUS.md` | This file |

### Pipeline Test Results

| Run | Task | Subtasks | Quality | Duration | Files Written |
|-----|------|----------|---------|----------|---------------|
| A | is_even() | 1/1 | 0.9 | 45.5s | report only |
| B | is_palindrome() | 1/1 | 0.9 | 44.7s | report only |
| C (with feedback) | parse_config() | 4/4 | 0.9 | 109.7s | report only |
| D (safe_dirs fix) | math_helpers.py | 5/5 | 0.9 | 91.6s | ✅ src/utils/math_helpers.py |

### Known Issues

1. **MCP dispatch**: `mycelium_pipeline` dispatch + fire-and-forget may not work reliably (zombie processes, event loop issues). Direct Python execution works. Needs MCP server restart.
2. **Heartbeat disabled**: Autonomous mode not active.

### Coordination Notes

**DO NOT MODIFY** (Opus territory):
- `src/services/feedback_service.py`
- `src/services/__init__.py`
- `src/mcp/tools/llm_call_tool_async.py`
- `src/mcp/mycelium_mcp_server.py`

**Cursor should modify**:
- `src/orchestration/task_board.py` — Pipeline→TaskBoard bridge
- `src/services/dag_aggregator.py` — parse enriched task results
- `client/src/components/mcc/*` — DAG visualization

**Codex should modify**:
- `src/cli/*` — CLI wrapper (isolated)
- `tests/test_vetka_cli.py`, `tests/test_pipeline_runner.py`

---

*Opus Agent | 2026-02-11*
