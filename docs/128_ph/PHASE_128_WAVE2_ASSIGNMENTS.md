# Phase 128 Wave 2: Assignment Distribution

## Date: 2026-02-09
## Commander: Opus

## Wave 1 Status: COMPLETE
- [x] O1: 128.1 Coder Project Awareness (Opus) — 19 tests
- [x] C1: Results Viewer + Apply (Cursor) — commit 32aca6f0
- [x] C2: Result Lifecycle (Cursor) — commit 32aca6f0
- [x] C3: Stats Monitor (Cursor) — previously done
- [x] M1: Marker Audit (Mistral) — pending verification
- [x] G1: MCP Bottleneck Research (Grok) — insights saved
- [x] G2: Diff/Patch Research (Grok) — insights saved

---

## CURSOR — Wave 2 (3 tasks)

### C4: Diff Viewer Component (Priority 1)
**Brief:** `docs/128_ph/CURSOR_BRIEF_128_DIFF_VIEWER.md`
- DiffViewer.tsx — green/red line highlighting
- Toggle: [Full Code] / [Diff View] in results expand
- No external deps — parse unified diff format
- Markers: MARKER_128.4A/B

### C5: Pipeline Trigger from DevPanel (Priority 2)
**Brief:** `docs/128_ph/CURSOR_BRIEF_128_PIPELINE_TRIGGER_UI.md`
- ▶ Run button on pending TaskCards
- Quick-add with dispatch
- Preset selector (Bronze/Silver/Gold)
- Markers: MARKER_128.5A/B/C

### C6: Activity Log Enrichment (Priority 3)
**Brief:** `docs/128_ph/CURSOR_BRIEF_128_ACTIVITY_ENRICH.md`
- Parse activity messages for tool calls, verifier verdicts
- Role icons, confidence bars, progress bars
- Per-task grouping (collapsible)
- Markers: MARKER_128.6A/B/C

---

## MISTRAL — Wave 2 (1 task)

### M2: Marker Placement for 128.4-128.6
**Brief:** `docs/128_ph/MISTRAL_BRIEF_128_WAVE2_MARKERS.md`
- Place diff generation markers in agent_pipeline.py
- Place MCP async markers in vetka_mcp_bridge.py

---

## OPUS — Wave 2

### O2: 128.4 Diff/Patch Generation (backend)
- Implement `generate_unified_diff()` using difflib
- Cache original file content from Scout
- Save `diff_patch` to subtask results
- Endpoint includes diff in results response

### O3: E2E Testing with new prompt
- Run Dragon Silver on pending tasks
- Verify coder uses Zustand (not MobX) after 128.1 fix

---

## GROK — Wave 2

### G3: MCP Layering Deep Dive
Prompt for user to relay:

> @grok Research: How to split vetka_mcp_bridge.py into multiple MCP servers
>
> Current: Single `vetka_mcp_bridge.py` handles ALL 35+ tools.
> Goal: Split into 2-3 MCP servers for parallel operation.
>
> Questions:
> 1. Can one MCP client connect to multiple MCP servers? (check MCP spec)
> 2. How does `.mcp.json` support multiple server entries?
> 3. Which tools should go to which server?
>    - UI tools (camera, viewport, tree) → MCP-UI
>    - Pipeline tools (mycelium, task_board) → MCP-Pipeline
>    - File tools (read, edit, search) → MCP-Files
> 4. How to share state (STM, Qdrant) between servers?
>
> Files: `src/mcp/vetka_mcp_bridge.py`, `.mcp.json`
> Format: JSON with `split_plan`, `shared_state_strategy`, `implementation_steps`
