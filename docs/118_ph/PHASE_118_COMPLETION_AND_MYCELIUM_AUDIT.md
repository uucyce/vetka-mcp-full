# Phase 118: Completion Report + Mycelium Pipeline Capabilities Audit

> **Date:** 2026-02-08 | **After:** Phase 117.8 (`26ea95a1`)
> **Commits:** `b02d2c91` (118.1-118.5) + `85d7a1fb` (118.6-118.7)
> **Goal:** Unblock @dragon pipeline — fix freezing, logging, visibility
> **Result:** @dragon messages VISIBLE in chat. Pipeline end-to-end operational.

---

## Part 1: Phase 118 — What Was Done

### 118.1: Async Embedding Calls (CRITICAL)

**MARKER_118.1** | `src/utils/embedding_service.py`

**Problem:** `ollama.embeddings()` and `ollama.embed()` — synchronous calls blocking the async event loop for 200ms-5s per call. During @dragon pipeline, embedding calls from TripleWrite/scanner freeze the entire server.

**Fix:** Added `get_embedding_async()` and `get_embedding_batch_async()` using `asyncio.to_thread()` to offload sync ollama calls to thread pool.

| Method | Type | Blocking? |
|--------|------|-----------|
| `get_embedding()` | sync | Yes (kept for backward compat) |
| `get_embedding_async()` | async | No — `asyncio.to_thread` |
| `get_embedding_batch()` | sync | Yes (kept for backward compat) |
| `get_embedding_batch_async()` | async | No — `asyncio.to_thread` |

Module-level convenience: `get_embedding_async(text)` added for easy import.

---

### 118.2: Weaviate Upsert Race Condition (HIGH)

**MARKER_118.2** | `src/orchestration/triple_write_manager.py` lines 376-398

**Problem:** TOCTOU race: `get_by_id()` → None → `insert()` → 422 "already exists" (concurrent write from another task).

**Fix:** Insert-first pattern — try `insert()`, catch 422 → `replace()`. No race window.

```
Before: get_by_id → if None → insert → 422 BOOM
After:  insert → catch "already exists" → replace → OK
```

---

### 118.3: httpx Log Flood (MEDIUM)

**MARKER_118.3** | `main.py` lines 34-40

**Problem:** `logging.basicConfig(level=logging.INFO)` ran BEFORE `setup_logging()`. httpx/httpcore INFO messages flooded terminal (~30% of all log lines).

**Fix:**
1. Changed `basicConfig` level to `WARNING`
2. Added early suppression for noisy loggers: httpx, httpcore, urllib3, qdrant_client, weaviate, ollama, grpc

User confirmed: "Логов меньше кстати стало, за это особое гранд мерси"

---

### 118.4: Hostess Local Model Muting (LOW)

**MARKER_118.4** | `src/agents/hostess_agent.py` lines 270-312

**Problem:** Without @mention, Hostess defaulted to local Ollama (`qwen2:7b`), blocking event loop with sync inference.

**Fix:**
1. `_find_available_model()` returns `None` instead of hardcoded `"qwen2:7b"`
2. `process()` checks `if not self.model:` → returns `"select_model"` action with user guidance
3. Added logging import and logger

---

### 118.5: Engram Attribute Errors (MEDIUM)

**MARKER_118.5** | `src/memory/engram_user_memory.py` + `src/memory/qdrant_client.py`

**Problem:**
- `self.qdrant.scroll()` — `QdrantVetkaClient` had no `scroll` method (wrapper, not raw client)
- `get_all_preferences()` — method didn't exist

**Fix:**
1. Added `scroll()` and `retrieve()` proxy methods to `QdrantVetkaClient` (delegating to `self.client`)
2. Added public `get_all_preferences(user_id)` method to `EngramUserMemory`

---

### 118.6: Message Visibility — ROOT CAUSE FIX

**MARKER_118.6** | `src/orchestration/agent_pipeline.py` + `src/api/handlers/user_message_handler.py`

**ROOT CAUSE:** Backend emitted `"agent_message"` → frontend `addMessage()` → legacy `messages[]`. But ChatPanel renders `chatMessages[]` (new system) only!

```
agent_message → addMessage → messages[]     ← INVISIBLE (legacy)
chat_response → addChatMessage → chatMessages[] ← VISIBLE (ChatPanel renders this)
```

**Fix:** Changed ALL `sio.emit("agent_message")` → `sio.emit("chat_response")` in 5 locations:

| Location | File | Line |
|----------|------|------|
| `_emit_progress()` Route 1 | agent_pipeline.py | ~395 |
| `_emit_to_chat()` Route 1 | agent_pipeline.py | ~520 |
| Initial "Pipeline starting..." | user_message_handler.py | ~867 |
| Final report | user_message_handler.py | ~2404 |
| Error report | user_message_handler.py | ~2413 |

Data format changed: `{content, text, agent, model}` → `{message, agent, model}` to match `chat_response` handler expectations.

**Result:** @dragon pipeline output now FULLY VISIBLE in ChatPanel!

---

### 118.7: Error Callback for Background Task

**MARKER_118.7** | `src/api/handlers/user_message_handler.py` line ~877

**Problem:** `asyncio.create_task()` for @dragon dispatch silently swallowed exceptions.

**Fix:** Added `task.add_done_callback(_on_dragon_done)` — exceptions now logged via `logger.error()`.

---

### Tests: 34 Tests, All Passing

`tests/test_phase118_unblock_dragon.py`:

| Test Class | Count | Covers |
|------------|-------|--------|
| TestAsyncEmbeddings | 6 | async methods, asyncio.to_thread, convenience fn |
| TestWeaviateUpsert | 4 | insert-first, catch 422, no TOCTOU |
| TestHttpxLogging | 3 | no INFO basicConfig, early suppression |
| TestHostessMuteLocal | 5 | no hardcoded fallback, None return, guard |
| TestEngramFixes | 6 | scroll/retrieve proxy, get_all_preferences |
| TestChatResponseEmit | 7 | chat_response in emit, message key format |
| TestErrorCallback | 3 | add_done_callback, exception check |

Combined Phase 117+118: **66/66 tests passing**.

---

## Part 2: Mycelium Pipeline — Current Capabilities

### What Agents CAN Do Today

#### 1. Context Injection (6 Sources)

Pipeline agents receive rich context via `inject_context` parameter in `vetka_call_model`:

| Source | Description | Limit |
|--------|-------------|-------|
| Files | Read specified files | 8000 chars/file, max 10 files |
| Session State | MCPStateManager session data | by ID |
| User Preferences | Engram memory prefs | 1500 chars |
| CAM | Context-Aware Memory active nodes | 5 items |
| Semantic Search | Qdrant vector search by query | 5 results |
| Chat History | Recent messages from chat_id | 10 messages |

All context is ELISION-compressed (40-60% token savings) before injection.

#### 2. STM (Short-Term Memory) Between Subtasks

- **Window:** Last 5 subtask results passed to next subtask
- **Compression:** ELISION compression for results > 1000 chars
- **Auto-reset:** After 10 subtasks, STM compressed to 500-char summary and reset (prevents context drift — Cursor research insight, MARKER_117.5B)
- **Tracking:** marker, result, compression_ratio, tokens_saved

#### 3. File Creation

- **auto_write=True (default):** Extract code blocks from LLM responses, write to `src/spawn_output/` (or `data/spawn_staging/` fallback)
- **auto_write=False:** Stage code in JSON for manual review via `retro_apply_spawn.py`
- **Limit:** Max 10 files per pipeline execution
- **Extraction:** Regex-based markdown code block extraction

#### 4. Model Presets (10 Teams)

| Preset | Architect | Researcher | Coder | Verifier |
|--------|-----------|------------|-------|----------|
| `dragon_bronze` | Qwen3-30b | Grok Fast 4.1 | Qwen3-coder-flash | Mimo-v2-flash |
| `dragon_silver` | Kimi K2.5 | Grok Fast 4.1 | Qwen3-coder | GLM-4.7-flash |
| `dragon_gold` | Kimi K2.5 | Grok Fast 4.1 | Qwen3-coder | Qwen3-235b |
| `dragon_gold_gpt` | Kimi K2.5 | Grok Fast 4.1 | GPT-5.2 | Qwen3-235b |
| `polza_research` | Claude-Sonnet-4 | Grok Fast 4.1 | Claude-Sonnet-4 | Claude-Sonnet-4 |
| `polza_mixed` | Claude-Sonnet-4 | Grok Fast 4.1 | DeepSeek-v3.2 | Qwen3-235b |
| `xai_direct` | Grok-4.1-fast | Grok-4.1-fast | Grok-4.1-fast | Grok-4.1-fast |
| `budget` | Llama-3.1-8b | Llama-3.1-8b | Llama-3.1-8b | Llama-3.1-8b |
| `quality` | Claude-Opus-4.6 | Grok Fast 4.1 | Claude-Opus-4.6 | Claude-Sonnet-4.5 |

**Auto-tier:** Architect estimates complexity → `_tier_map` resolves: low→bronze, medium→silver, high→gold.

#### 5. MCP Tools Available to Agents (25+, mostly read-only)

**All agents (default):**
- `read_code_file`, `list_files`, `search_codebase`
- `vetka_search_semantic`, `get_tree_context`, `vetka_camera_focus`
- CAM tools: `calculate_surprise`, `compress_with_elision`, `adaptive_memory_sizing`
- `arc_suggest` (creative workflow suggestions)

**Dev agent only:** `write_code_file`, `execute_code`, `vetka_edit_artifact`

**PM agent:** read-only + `vetka_edit_artifact`

**Architect:** read-only + `vetka_edit_artifact` + CAM tools

**Researcher:** read-only + semantic search focus

#### 6. Real-Time Progress Streaming

After Phase 118.6 fix:
- Pipeline emits `chat_response` via SocketIO → `addChatMessage()` → `chatMessages[]` → ChatPanel renders
- Model attribution: each message tagged with `{agent, model}`
- Progress visible at every stage: architect planning, researcher findings, coder output, verifier results

#### 7. Pipeline Phases

| Phase | Trigger | What Happens |
|-------|---------|--------------|
| `build` | `@dragon <task>` | Architect → [Research] → Coder → Verifier |
| `fix` | `@doctor <bug>` | Diagnostic pipeline for debugging |
| `research` | `@doctor <question>` | Research-only pipeline |

#### 8. Fractal Task Decomposition

1. **Architect** breaks task into subtasks (JSON output: description, needs_research, execution_order)
2. **Researcher** (Grok) investigates subtasks marked `needs_research=true`
3. **Coder** implements each subtask with STM context from previous results
4. **Verifier** reviews output (passed/failed, issues, suggestions, confidence)

---

## Part 3: Mycelium Pipeline — What's Missing

### Critical Gaps (Agents CANNOT Do)

#### 1. Edit Existing Files

**Status:** Agents can only CREATE new files in `src/spawn_output/`. They CANNOT edit existing project files.

**Why:** `vetka_edit_file` is in `WRITE_TOOLS_REQUIRING_APPROVAL` — not passed to LLM tool calls.

**Impact:** Coder agents asked questions instead of fixing bugs because they couldn't modify existing code. The live test showed: "@dragon fix chat rename bug" → coder returned 4 subtasks with questions, zero code edits.

**Need:** Safe file editing protocol with diff preview + rollback.

---

#### 2. Git Safety Protocol (Branching / Rollback)

**Status:** No git branching. `vetka_git_commit` only does linear commits to current branch. No branch creation, no rollback, no PR workflow.

**Impact:** Without safety net, autonomous file editing is too risky. One bad edit could break the project.

**Need:**
- Auto-create branch before pipeline writes (e.g. `mycelium/task-123`)
- Commit intermediate results
- Rollback on verifier failure
- Optional PR creation for review

---

#### 3. Web Search

**Status:** Tavily API key support registered in `api_key_service.py` but NOT wired to pipeline agents. Researcher (Grok) has no web search tool.

**Impact:** Agents can't look up documentation, find examples, or research unfamiliar APIs.

**Need:**
- Add Tavily search tool to researcher's available tools
- Wire `_research()` method to call Tavily before codebase analysis
- Alternatively: give all agents a `web_search` tool

---

#### 4. Context7 / Documentation Access

**Status:** Context7 MCP tool available to Claude Code but NOT to pipeline agents.

**Impact:** Coder agents can't look up library APIs, framework patterns, or best practices.

**Need:** Add `resolve-library-id` + `get-library-docs` to coder/researcher tool permissions.

---

#### 5. Write MCP Tools Blocked

**Status:** These tools are gated behind `WRITE_TOOLS_REQUIRING_APPROVAL`:
- `vetka_edit_file` — file editing
- `vetka_git_commit` — git commits
- `vetka_edit_artifact` — artifact editing (available to Dev/Architect only)
- `vetka_send_message` — message sending
- `vetka_execute_workflow` — workflow execution
- `vetka_mycelium_pipeline` — pipeline recursion
- `vetka_call_model` — LLM recursion

**Impact:** Agents can generate code but can't apply it to the project.

**Need:** Graduated approval system: auto-approve for safe operations (edit in branch, commit to branch), require approval for dangerous ones (push to main, delete).

---

#### 6. Recursive LLM Calls

**Status:** `vetka_call_model` blocked from pipeline agents (prevents infinite recursion).

**Impact:** Agents can't ask follow-up questions or delegate sub-tasks to other models.

**Need:** Controlled recursion with depth limit (max 2-3 levels).

---

#### 7. Autonomous Bug Detection Loop

**Status:** No loop. Pipeline runs once per `@dragon` command and stops.

**Impact:** Can't "watch" for bugs, run tests periodically, or auto-fix regressions.

**Need:**
- Heartbeat-triggered test runner
- Error log scanner
- Auto-dispatch pipeline on failure detection
- CI/CD integration

---

#### 8. Codebase Context for Coders

**Status:** Coder agents receive STM + inject_context, but no curated "project architecture" overview. Live test showed coders asked basic questions about project structure.

**Impact:** Coders waste tokens asking "what framework is this?" instead of writing code.

**Need:**
- Auto-inject project digest / architecture overview
- Relevant file snippets based on subtask description
- Pattern examples from existing codebase

---

## Part 4: Roadmap — Making Mycelium Autonomous

### Priority Matrix

| Priority | Feature | Phase | Effort | Impact |
|----------|---------|-------|--------|--------|
| P0 | Safe file editing (diff + preview) | 119.1 | HIGH | Enables actual bug fixing |
| P0 | Git branch safety protocol | 119.2 | HIGH | Safety net for auto-edits |
| P1 | Codebase context injection for coders | 119.3 | MEDIUM | Eliminates "what is this?" questions |
| P1 | Web search for researcher (Tavily) | 119.4 | LOW | Documentation lookups |
| P1 | Context7 for coder/researcher | 119.5 | LOW | Library API access |
| P2 | Graduated approval system | 119.6 | HIGH | Auto-approve safe ops, block dangerous |
| P2 | Auto-test after pipeline write | 119.7 | MEDIUM | Verify generated code compiles/passes |
| P3 | Autonomous bug detection loop | 120.x | HIGH | Watch → detect → fix cycle |
| P3 | Controlled LLM recursion (depth=2) | 120.x | MEDIUM | Agent sub-delegation |
| P3 | CI/CD integration | 120.x | HIGH | GitHub Actions / webhook triggers |

### Phase 119 Vision: "Mycelium Can Fix Bugs"

**Goal:** Pipeline receives a bug report → creates branch → reads relevant files → edits code → runs tests → commits → reports result.

**Flow:**
```
@dragon fix <bug description>
    │
    ├── 1. git checkout -b mycelium/fix-XXX
    ├── 2. Architect analyzes bug, identifies files
    ├── 3. Researcher reads files + searches codebase
    ├── 4. Coder generates DIFF (not new file)
    ├── 5. Pipeline applies diff to existing file
    ├── 6. pytest runs on modified code
    │       ├── PASS → commit + report
    │       └── FAIL → rollback + report error
    └── 7. User reviews branch, merges if satisfied
```

**Required components:**
1. `safe_edit_file(path, diff)` — apply diff with backup
2. `git_branch_create(name)` — create branch for pipeline work
3. `git_rollback(branch)` — revert to pre-pipeline state
4. `run_tests_and_report()` — pytest + format results for pipeline
5. Enhanced coder prompt with project architecture context

---

## Appendix: Files Modified in Phase 118

| File | Sub-phase | Changes |
|------|-----------|---------|
| `src/utils/embedding_service.py` | 118.1 | +`get_embedding_async()`, +`get_embedding_batch_async()` |
| `src/orchestration/triple_write_manager.py` | 118.2 | Insert-first upsert pattern |
| `main.py` | 118.3 | basicConfig WARNING + early suppression |
| `src/agents/hostess_agent.py` | 118.4 | `_find_available_model()` → None, guard in `process()` |
| `src/memory/engram_user_memory.py` | 118.5 | +`get_all_preferences()` |
| `src/memory/qdrant_client.py` | 118.5 | +`scroll()`, +`retrieve()` proxy methods |
| `src/orchestration/agent_pipeline.py` | 118.6 | `agent_message` → `chat_response` (2 locations) |
| `src/api/handlers/user_message_handler.py` | 118.6+7 | `agent_message` → `chat_response` (3 locations) + error callback |
| `tests/test_phase118_unblock_dragon.py` | all | 34 tests covering all sub-phases |
| `tests/test_phase117_8_socketio_emit.py` | 118.6 | Updated assertion for `chat_response` |

---

## Appendix: Security Model

Pipeline agents operate under strict security:

```
WRITE_TOOLS_REQUIRING_APPROVAL = {
    "vetka_edit_file",          # File editing — BLOCKED
    "vetka_git_commit",         # Git commits — BLOCKED
    "vetka_edit_artifact",      # Artifacts — Dev/Architect only
    "vetka_approve_artifact",   # Approval — BLOCKED
    "vetka_reject_artifact",    # Rejection — BLOCKED
    "vetka_send_message",       # Messages — BLOCKED
    "vetka_execute_workflow",   # Workflow — BLOCKED (recursion)
    "vetka_mycelium_pipeline",  # Pipeline — BLOCKED (recursion)
    "vetka_call_model",         # LLM calls — BLOCKED (recursion)
}
```

Code writing happens via **indirect extraction**: LLM outputs markdown code blocks → pipeline regex-extracts → writes to `src/spawn_output/` (if `auto_write=True`).

---

*Report generated by Opus Commander + Haiku/Sonnet scouts. Phase 118 complete.*
