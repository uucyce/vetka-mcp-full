# Phase 128: Assignment Distribution

## Date: 2026-02-09
## Commander: Opus
## Goal: Make Mycelium pipeline WORK for real tasks, for ALL clients

---

## TEAM ROSTER

| Agent | Tool | Domain | Status |
|-------|------|--------|--------|
| **Cursor** | Cursor IDE | Frontend UI | Waiting for brief |
| **Mistral** | OpenCode | Marker audit + code marking | Waiting for brief |
| **Grok** | VETKA chat | Deep research (web + codebase) | Research delivered |
| **Opus** | Claude Code | Architecture + pipeline testing | Active |
| **Dragon Silver** | Mycelium | Code generation (E2E testing) | Active |

---

## CURSOR ASSIGNMENTS (Frontend)

### Task C1: Results Viewer + Apply (Priority 1)
**Brief:** `docs/128_ph/CURSOR_BRIEF_128_RESULTS_APPLY.md`
**Previous brief:** `docs/126_phCur/CURSOR_BRIEF_RESULTS_VIEWER.md` (base)

**Summary:**
- Click done task in Board tab → see generated code
- Copy button per subtask
- **NEW: Apply button** → POST endpoint writes code to disk
- Backend: `POST /api/debug/pipeline-results/apply`

**Markers:** MARKER_128.2A (expand), MARKER_128.2B (apply endpoint), MARKER_128.2C (buttons)

### Task C2: External Client Status Marking (Priority 2)
**Brief:** `docs/128_ph/CURSOR_BRIEF_128_RESULT_LIFECYCLE.md` (create below)

**Summary:**
- After pipeline runs, result needs lifecycle: `generated → reviewed → applied → rejected`
- TaskCard shows status badge
- Buttons: "Applied" / "Rejected" / "Needs Rework"
- Backend tracks in task_board.json

### Task C3: Stats Monitor Live Refresh (Priority 3)
**Brief:** `docs/126_phCur/CURSOR_BRIEF_STATS_MONITOR.md` (existing)

**Summary:**
- Live refresh when pipelines complete
- Running tasks with elapsed time
- Per-preset breakdown bars

---

## MISTRAL ASSIGNMENTS (Code Marking)

### Task M1: Marker Audit for Phase 128
**Brief:** `docs/128_ph/MISTRAL_BRIEF_128_MARKERS.md` (exists)

**Summary:**
- Verify existing MARKER_128.1A/B in agent_pipeline.py
- Place new markers for 128.2 (Results Apply)
- Audit marker consistency across files

---

## GROK ASSIGNMENTS (Research — via user relay)

### Task G1: Pipeline Universalization — DONE
Research delivered (JSON response). Key findings integrated.

### Task G2: Diff/Patch Format Research (Next)
**Prompt to send to Grok:**

> @grok Research: Code Diff Format for Pipeline Results
>
> The Mycelium pipeline generates full file code. We need to convert to diff/patch format.
>
> Research:
> 1. Python `difflib` — unified diff generation for before/after comparison
> 2. `unidiff` library — parsing/generating unified diffs
> 3. LSP `WorkspaceEdit` format — how IDEs expect code changes
> 4. How to generate patch when we don't have "before" (only "after" from coder)?
>
> Key question: Coder outputs FULL code blocks. We have the original file (via Scout).
> How to generate a minimal diff between original and coder output?
>
> Files to check:
> - `src/orchestration/agent_pipeline.py` lines 1460-1540 (`_extract_and_write_files`)
> - `src/tools/fc_loop.py` (coder tool results contain file contents)
>
> Format: JSON with `library_comparison`, `recommended_approach`, `code_example`

---

## OPUS ASSIGNMENTS (Architecture + Testing)

### Task O1: 128.1 Coder Project Awareness — DONE
- Updated coder prompt: PROJECT STACK section (Zustand, React, TypeScript)
- Added `_detect_project_context()` in Scout pre-fetch
- Wired project_context through scout_report → coder context
- 19 tests passing

### Task O2: E2E Pipeline Testing (Current)
- Run Dragon Silver on real Task Board tasks
- Analyze code quality: correct imports? correct patterns? correct file paths?
- Compare before/after 128.1 changes

### Task O3: Result Lifecycle Backend (After E2E)
- Add status field to pipeline results: `generated | reviewed | applied | rejected`
- REST endpoint: `PATCH /api/debug/pipeline-results/{task_id}/status`
- Track who applied/rejected and when

---

## DEPENDENCY GRAPH

```
128.1 Coder Awareness (Opus) ──DONE──┐
                                      ├──> 128.3 E2E Test (Opus)
Marker Audit (Mistral) ──────────────┘         │
                                               ├──> Analyze & Fix
Results Viewer (Cursor C1) ──────────────────┐ │
Result Lifecycle (Cursor C2) ────────────────┤ │
Stats Monitor (Cursor C3) ──────────────────┘ │
                                               ▼
                                    128.4 Polish & Ship
```

## FILES CREATED THIS SESSION

| File | Purpose |
|------|---------|
| `docs/128_ph/TODO_NEXT_SESSION_128.md` | Session TODO (pre-existing) |
| `docs/128_ph/RECON_128_PIPELINE_COUPLING.md` | Scout recon report |
| `docs/128_ph/CURSOR_BRIEF_128_RESULTS_APPLY.md` | Cursor: Results + Apply |
| `docs/128_ph/MISTRAL_BRIEF_128_MARKERS.md` | Mistral: Marker audit |
| `docs/128_ph/PHASE_128_ASSIGNMENTS.md` | This file — master assignment list |
| `tests/test_phase128_1_project_awareness.py` | 19 tests for 128.1 |
