# PHASE 150 — DAG-Drives-Pipeline + Sparse Apply
## Updated Roadmap | 2026-02-15

---

## STATUS OVERVIEW

**Phase 150 — DAG-Drives-Pipeline Architecture**

Философия: Pipeline больше не hardcoded Python. Workflow JSON (BMAD) определяет порядок выполнения.
DAG Editor (Phase 144) → Workflow Template → DAG Executor → Real Pipeline.

| Sub-phase | Name | Status | Commits | Tests |
|-----------|------|--------|---------|-------|
| 150.0 | Grok Research (DAG+Pipeline bridge) | ✅ DONE | `4175a227` | — |
| 150.1 | BMAD Template + DAG Executor MVP | ✅ DONE | `31dcba0c` | 21 |
| 150.2 | Playground isolation (FC tools) | ✅ DONE | `7915ae0e` | 6 |
| 150.3a | Wire DAG → real pipeline methods | ✅ DONE | `4e639ef1` | 28 |
| 150.3b | Live DAG streaming (dag_node_update) | ✅ DONE | `9ed6768e` | 7 |
| 150.3c | Sparse Apply (PatchApplier) | ✅ DONE | `2fdadd6f` | 22 |
| 150.4 | PatchApplier → Pipeline integration | ✅ DONE | `af34b83f` | 25 |
| 150.5 | Coder PATCH MODE prompt | ✅ DONE | `af34b83f` | (in 150.4) |
| 150.6 | Structured Agent Streaming | 📋 PLANNED | — | — |
| 150.7 | E2E: DAG Executor + Dragon Silver | 🔥 NEXT | — | — |

**Total Phase 150 tests: 109** (21 + 6 + 28 + 7 + 22 + 25)
**Total project tests: 569+ passing** (14 pre-existing failures)

---

## WHAT WE BUILT (150.0 — 150.3)

### 150.0 — Grok Research
- **File:** `docs/150_ph/GROK_RESEARCH_150_DAG_PIPELINE_BRIDGE.md`
- Research prompt: n8n/ComfyUI execution engines, Playground-as-workspace, BMAD loop wiring
- **File:** `docs/150_ph/stream_GROK.txt`
- Full structured streaming architecture from Grok (agent_stream events, WebSocket control, React panel)

### 150.1 — BMAD Template + DAG Executor MVP
- **File:** `data/templates/bmad_workflow.json` — 11 nodes, 13 edges (1 feedback)
- **File:** `src/orchestration/dag_executor.py` (993 lines)
- DAGExecutor: Kahn's BFS topological sort, node execution engine
- Node types: task, parallel, condition, agent nodes
- Nodes: scout → architect → researcher → coder → measure(parallel: verifier + eval_agent) → adjust(condition) → approval_gate → deploy

### 150.2 — Playground Isolation
- `base_path` parameter flows: DAGExecutor → pipeline._execute_subtask → FC loop → coder tools
- VetkaReadFileTool, VetkaSearchCodeTool — prefix paths with worktree when in playground
- Scout ripgrep searches in worktree directory

### 150.3a — Wire DAG → Real Pipeline
- **Feedback edge exclusion:** edges with `type="feedback"` excluded from adjacency → no cycle in topo sort
- **`_execute_coder()`:** Iterates architect subtasks, calls `pipeline._execute_subtask()` for each
- **`_execute_verifier()`:** Iterates coder results, calls `pipeline._verify_subtask()`, aggregates confidence
- **`_execute_eval()`:** Wired to EvalAgent
- **`_execute_condition_node()`:** Internal retry loop — coder→verify→retry up to max_retries, graceful degradation
- **`_execute_parallel_node()`:** Propagates parent inputs to children, concurrent execution
- **Skip logic:** Feedback edge sources + parallel children skipped in main loop, handled internally

### 150.3b — Live DAG Streaming
- `_emit()` method sends structured `dag_node_update` events
- Dual transport: SocketIO + WebSocket broadcaster
- `_make_output_preview()` — concise output summaries
- Frontend: `useSocket.ts` handles `dag_node_update` event, dispatches `dag-node-update` CustomEvent

### 150.3c — Sparse Apply (PatchApplier)
- **File:** `src/tools/patch_applier.py` (455 lines)
- **Mode 1: Marker Insert** — find marker → INSERT_AFTER/INSERT_BEFORE/REPLACE code. Append-only, safest.
- **Mode 2: Unified Diff** — pure Python diff parser + applier (no git subprocess dependency)
- **Mode 3: Create** — new files with parent directory creation
- **`detect_mode()`** — auto-detect from coder output content
- **`extract_patches()`** — extract patch instructions from mixed output
- Backup system (.bak files before any modification)

---

## WHAT WE BUILT (150.4 — 150.5)

### 150.4 — PatchApplier → Pipeline Integration ✅ DONE (af34b83f)
**Goal:** Dragon uses sparse apply for existing files, full write for new files only.

**What was built:**
- **MARKER_150.4_IMPORT:** `PatchApplier` import with try/except and `PATCH_APPLIER_AVAILABLE` flag
- **MARKER_150.4A:** `_detect_target_files(subtask, base_path)` static method
  - Extracts existing file paths from subtask.context.scout_report (marker_map + relevant_files)
  - Deduplicates, resolves against base_path, returns only files that exist on disk
  - Empty list = CREATE mode, non-empty = PATCH mode
- **MARKER_150.4B:** `_apply_patches(content, subtask)` async method
  - Uses PatchApplier.detect_mode() to identify unified_diff / marker_insert / create
  - Routes to correct apply method, graceful fallback on exception
- **MARKER_150.4C:** Mode detection before user message construction
  - Injects `⚠️ MODE: PATCH` or `MODE: CREATE` into coder's task description
- **MARKER_150.4D:** FC loop post-processing — try PatchApplier first, fallback to extract_and_write
- **MARKER_150.4E:** One-shot post-processing — same pattern

**Files modified:**
- `src/orchestration/agent_pipeline.py` — +169 lines (3 new methods + mode routing)
- `data/templates/pipeline_prompts.json` — coder + verifier prompts updated

**Tests:** 25 in `test_phase150_4_patch_integration.py`

### 150.5 — Coder PATCH MODE Prompt ✅ DONE (af34b83f)
**Goal:** Force coder LLM to output patches instead of full file rewrites.

**What was built:**
- Coder prompt: `## OUTPUT MODES` section with MODE: CREATE and MODE: PATCH
- MODE: PATCH requires unified diff format with 3-line context
- Alternative: MARKER INSERT JSON format for marker-based edits
- Explicit rules: "NEVER rewrite or output the full file content"
- Verifier prompt: patch-awareness — checks diff has proper context, flags >50% removal as severity=major

---

## WHAT'S NEXT (150.6 — 150.7)

### 150.6 — Structured Agent Streaming 📋 PLANNED
**Goal:** Real-time visibility into what Dragon is thinking and doing (Cursor-level transparency).

**Source:** Grok research in `stream_GROK.txt` — full architecture already designed.

**Core concept:** Agent Stream Event Bus
```json
{
  "type": "reasoning" | "tool_call_proposed" | "tool_call_result" | "final_answer",
  "agent_id": "dragon_coder",
  "model": "qwen3-coder",
  "tool_name": "vetka_read_file",
  "tool_args": {"path": "src/main.tsx"},
  "status": "pending" | "executing" | "done"
}
```

**Components:**
1. `_stream_event()` in AgentPipeline — unified event emitter
2. WebSocket `/ws/agent-control` — approve/edit/reject tool calls
3. `AgentStreamPanel.tsx` — React UI with tool call cards + approve/reject buttons

**Dependencies:** Best done AFTER 150.4-150.5 (pipeline changes stabilized)
**Estimated:** 4-6 hours, ~400 LOC (backend + frontend)

### 150.7 — E2E: DAG Executor + Dragon Silver 📋 PLANNED
**Goal:** Full end-to-end test with real Dragon Silver pipeline through DAG Executor.

**Test scenario:**
1. Load BMAD workflow template
2. Create playground
3. Run DAG Executor with Dragon Silver preset
4. Verify: scout → architect → coder (with PATCH MODE) → verifier → condition → promote
5. Check: files created/patched in playground, dag_node_update events emitted

**Expected outcome:**
- New files: created correctly (like HeartbeatChip.tsx)
- Existing files: patched surgically (NOT destructively rewritten)
- Verifier: checks diff, not full file
- Promote: only approved changes reach main

---

## WHAT WE LEARNED (Phase 149-150)

### Dragon Behavior Patterns
| Scenario | Dragon Behavior | Quality | Solution |
|----------|----------------|---------|----------|
| NEW file creation | Excellent | 8/10 | ✅ Keep as-is |
| MODIFY existing file | CATASTROPHIC (deletes 90%+) | 0/10 | 🔥 Sparse Apply (150.4-150.5) |
| Read + understand code | Good with FC loop | 7/10 | ✅ FC tools work |
| Follow marker rails | Good | 7/10 | ✅ MARKER_SCOUT system |

### Architecture Decisions
1. **DAG-Drives-Pipeline** — n8n/ComfyUI pattern validated by Grok research
2. **Feedback edges** — excluded from topo sort, handled internally in condition node
3. **Pure Python diff** — no git subprocess dependency in PatchApplier (portable)
4. **BMAD as fixed template** — customizable later, but BMAD loop is the default
5. **Playground = execution environment** — DAG runs inside worktree, promotes to main

### Phase Numbering Correction
Original roadmap had different numbering. Actual implementation:

| Original Plan | Actual Phase | What Changed |
|---------------|-------------|--------------|
| 150.1 — Live DAG Pipeline Streaming | 150.3b | Moved later, done with DAG wiring |
| 150.2 — Playground ↔ DAG связка | 150.2 (partial) | Playground isolation done, UI badge deferred |
| 150.3 — Coder reads from Worktree | 150.2 | Done together with playground isolation |
| 150.4 — Sparse Apply | 150.3c (PatchApplier) + 150.4 (integration) | Split: tool built, pipeline integration pending |
| 150.5 — BMAD Integration | 150.1 + 150.3a | Template + executor wiring done together |

---

## FILES CREATED / MODIFIED IN PHASE 150

### New Files
| File | Lines | Purpose |
|------|-------|---------|
| `src/orchestration/dag_executor.py` | 993 | DAG Executor — workflow template → execution |
| `src/tools/patch_applier.py` | 455 | Sparse Apply — 3 modes (marker/diff/create) |
| `data/templates/bmad_workflow.json` | ~100 | BMAD workflow template (11 nodes, 13 edges) |
| `tests/test_phase150_3_dag_executor.py` | ~600 | 28 DAG tests + 7 streaming tests |
| `tests/test_phase150_3_sparse_apply.py` | ~500 | 22 PatchApplier tests |
| `docs/150_ph/GROK_RESEARCH_150_DAG_PIPELINE_BRIDGE.md` | 100 | Research prompt for Grok |
| `docs/150_ph/SPARSE_APPLY_DESIGN.md` | 217 | Sparse Apply architecture doc |
| `docs/150_ph/stream_GROK.txt` | 787 | Grok streaming research (full) |

### Modified Files
| File | What Changed |
|------|-------------|
| `client/src/hooks/useSocket.ts` | Added `dag_node_update` event type + handler |

---

## PRIORITY ORDER (What to do next)

### ✅ DONE — "Dragon stops destroying files" (150.4 + 150.5)
1. ~~150.5 Coder PATCH MODE prompt~~ ✅
2. ~~150.4 Pipeline integration~~ ✅
3. **Quick E2E test** — verify Dragon outputs diffs instead of full rewrites (part of 150.7)

### Next — "See what Dragon is thinking" (150.6)
4. **150.6 Structured streaming** — agent_stream events, basic UI panel

### After — "Full autonomous loop" (150.7+)
5. **150.7 E2E with real Dragon** — full BMAD loop through DAG Executor
6. **Playground UI** — create/review/promote playground from frontend (deferred from 150.2)
7. **Approval gate** — wire approval_service.py into DAG (blocks until user approves)

---

## RELATED DOCS

| Doc | Purpose |
|-----|---------|
| `docs/150_ph/SPARSE_APPLY_DESIGN.md` | Original Sparse Apply architecture |
| `docs/150_ph/GROK_RESEARCH_150_DAG_PIPELINE_BRIDGE.md` | Research questions for Grok |
| `docs/150_ph/stream_GROK.txt` | Full Grok research: streaming + control architecture |
| `docs/150_ph/USER_TEST_GUIDE.md` | User test guide — how to run first task |
| `docs/BATTLEFIELD_REPORT_2026_02_14.md` | Day 2 battle report (pre-Phase 150) |

---

*Updated by Opus Commander | Phase 150 | 2026-02-15*
*109 new tests, 4 commits, 1617 LOC (993 DAG + 455 PatchApplier + 169 integration)*
