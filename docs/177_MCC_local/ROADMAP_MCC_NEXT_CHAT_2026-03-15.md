# Roadmap — MCC Next Chat (2026-03-15)

## Goal

Finish the MCC graph inspection MVP behavior:

- infinite recursive drill-on-demand
- clear scope semantics (`ROOT/DIR/DOC/CODE`)
- stable user interaction and stable Playwright regression

## Current State

- Core branch drill chain is working.
- Fractal sizing is present.
- Projection echo suppression exists.
- Remaining gaps are interaction reliability and full recursive scaling workflow.

## Execution Plan (MCP tasks)

### Step 1 — Interaction reliability

Task: `tb_1773522136_5`

Deliverables:

- graph clicks/double-clicks are not blocked by draggable mini windows
- deterministic node interaction in dense MCC scenes

Acceptance:

- live pointer double-click works without synthetic event dispatch
- no regressions in existing MCC graph tests

### Step 2 — Recursive drill engine

Task: `tb_1773522136_4`

Deliverables:

- no remaining hardcoded generation assumptions in expansion path
- branch-local one-generation-per-click preserved at any depth

Acceptance:

- child -> grandchild -> great-grandchild chain works via repeated clicks
- branch switch and ancestor truncation still deterministic

### Step 3 — Live visual regression closure

Task: `tb_1773522137_6`

Deliverables:

- seeded Playwright flow validating descendant hierarchy
- regression checks for duplicate suppression and branch ownership

Acceptance:

- Playwright regression passes with native pointer path
- target tests remain green:
  - `tests/test_phase177_mcc_graph_drill_chain_contract.py`
  - `tests/test_phase177_mcc_projection_echo_contract.py`
  - `tests/test_phase177_mcc_generation_band_scale_contract.py`

## Parallel Future Track (already open)

- `tb_1773275513_6` — LiteRT feasibility
- `tb_1773275513_7` — LiteRT benchmark pack

Do not block MCC graph closure on LiteRT tasks.

