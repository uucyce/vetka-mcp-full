# MCC Handoff — Phase 177 (2026-03-15)

## Scope

This handoff covers the active MCC thread:

- fractal roadmap drill behavior
- code/document/directory visual semantics
- Playwright-seeded regression path
- projection echo suppression

TaskBoard source of truth for this handoff is MCP (`vetka_task_board`), not direct JSON edits.

## What Is Stable

### Graph drill behavior

- Branch-local chain behavior is in place: top-level click switches branch, descendant click deepens current branch.
- One expand action creates one generation (no eager grandchildren injection).
- Canonical duplicate suppression is active for inline projected descendants.

Primary files:

- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/client/src/components/mcc/MyceliumCommandCenter.tsx`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/client/src/components/mcc/DAGView.tsx`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/client/src/components/mcc/nodes/RoadmapTaskNode.tsx`

### Playwright seed path

- Seed fixture script returns deterministic `project_id` + browser URL.
- MCC standalone route path and init path work with seeded query param.

Primary files:

- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/scripts/mcc_seed_playwright_fixture.py`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/client/src/main.tsx`

### Architecture docs

- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/docs/177_MCC_local/MCC_CODE_CONTEXT_INSPECTION_ARCHITECTURE.md`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/docs/177_MCC_local/MARKER_177_MCC_GENERATION_BAND_RECON.md`

## MCP TaskBoard Checkpoint (authoritative)

Checked via MCP on 2026-03-15.

### Past tasks confirmed closed

- `tb_1773275513_1` — `done`
- `tb_1773275513_2` — `done`
- `tb_1773275513_3` — `done`
- `tb_1773276211_1` — `done`

### Existing future tasks still open

- `tb_1773275513_6` — `pending` (LiteRT feasibility)
- `tb_1773275513_7` — `pending` (LiteRT benchmark pack)

### New future MCC tasks created for next chat

- `tb_1773522136_4` — `pending` — Infinite recursive drill engine
- `tb_1773522136_5` — `pending` — Pointer-safe graph interaction under mini windows
- `tb_1773522137_6` — `pending` — Live Playwright visual regression for descendants

## Regression Pack To Run First In Next Chat

```bash
python -m pytest \
  tests/test_phase177_mcc_graph_node_selector_contract.py \
  tests/test_phase177_mcc_projection_echo_contract.py \
  tests/test_phase177_mcc_playwright_seed_contract.py \
  tests/test_phase177_mcc_router_contract.py \
  tests/test_phase177_mcc_graph_drill_chain_contract.py \
  tests/test_phase177_mcc_code_scope_semantics_contract.py \
  tests/test_phase177_mcc_code_scope_projection_contract.py \
  tests/test_phase177_mcc_fractal_visual_scale_contract.py \
  tests/test_phase177_mcc_generation_band_scale_contract.py -q
```

## Immediate Execution Order

1. `tb_1773522136_5` — remove pointer interception and restore reliable native dblclick hit path.
2. `tb_1773522136_4` — move remaining depth assumptions to recursive on-demand expansion.
3. `tb_1773522137_6` — finalize live Playwright pointer-based regression (no synthetic dispatch).

## MCP Incident Note (session_init / json shadowing)

- Symptom observed in chat tools: `vetka_session_init` failed with `cannot access local variable 'json'...`.
- Root cause in bridge handler:
  - `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/mcp/vetka_mcp_bridge.py`
  - local `import json` inside `elif name == "vetka_task_board"` shadowed function-scope `json`.
- Fix applied:
  - removed local `import json`, rely on module-level import.
  - added regression guard:
    - `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/tests/test_phase178_wave6.py`
    - `test_handler_does_not_shadow_global_json_module`.
- New TaskBoard item created for runtime hardening/restart-smoke:
  - `tb_1773522625_1` (priority P1, phase_type `fix`, tags: `mcp`, `session_init`, `json-shadowing`).
