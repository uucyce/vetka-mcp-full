# CODEX Handoff Recon (2026-02-24)

## Scope of this handoff
This note captures current MCC Phase 155 state for next chat:
- what is already implemented,
- what remains,
- where Mycelium stop/hang needs focused debugging.

## What is done (latest wave)

### 1) Stats + Diagnostics unified workspace
Marker:
- `MARKER_155.P3_4.STATS_DIAGNOSTICS_WORKSPACE.V1`

Implemented:
- Stats tab is now one workspace with internal modes:
  - `Ops`
  - `Diagnostics`
- Diagnostics includes:
  - graph verifier/spectral summary
  - JEPA runtime health snapshot
  - trigger log (`fetch/skip/queue`) for event-driven refresh visibility
- MiniStats compact now has:
  - `graph:<decision>`
  - `rt:ok|down`
  - `diag ↗` shortcut into `Stats -> Diagnostics`

Files:
- `client/src/components/panels/StatsWorkspace.tsx`
- `client/src/hooks/useMCCDiagnostics.ts`
- `client/src/components/panels/DevPanel.tsx`
- `client/src/components/mcc/MiniStats.tsx`
- `client/src/store/useDevPanelStore.ts`

### 2) Focus action payload enriched for Architect
Marker:
- `MARKER_155.P4_1.FOCUS_ACTION_PARITY.V1` (extended context contract)

Implemented:
- `sendFocusToArchitect()` now sends not only selected node IDs, but context:
  - `focused_node_ids`
  - `nav_level`
  - `camera_lod`
  - `focus_display_mode`
  - `focus_scope_key`

File:
- `client/src/components/mcc/MyceliumCommandCenter.tsx`

### 3) Existing P3/P4 status before this handoff
Already present from previous turns:
- P3.1/P3.2/P3.3/P3.4 runtime bridge path and health route
- P4.1 focus action parity
- P4.2 focus memory baseline
- P4.3 focus display modes (`all`, `selected+deps`, `selected-only`)

Primary files:
- `src/services/jepa_runtime.py`
- `src/services/mcc_jepa_adapter.py`
- `src/services/mcc_predictive_overlay.py`
- `src/api/routes/mcc_routes.py`
- `client/src/components/mcc/MyceliumCommandCenter.tsx`

## What remains (next chat priorities)

### A) P4.2 hardening (requested)
Goal:
- stronger focus restore semantics across `Architecture -> Module -> File/Task`
- explicit restore policy in UI

Minimum next steps:
1. Add restore policy mode contract (`scope_first` / `selection_first`) and expose it in UI.
2. Persist policy in store + localStorage.
3. Apply deterministic restoration order:
   - current valid selection
   - saved scope memory
   - default focus candidate
4. Add Diagnostics visibility for:
   - current policy
   - restore source (`current|memory|default`)

### B) Diagnostics++ shutdown blockers (requested)
Goal:
- detect why Mycelium shutdown gets stuck.

Minimum next steps:
1. Add backend endpoint with runtime blockers snapshot:
   - active asyncio task counts by label
   - cleanup/heartbeat/model-registry/group-chat/qdrant states
   - ws clients count
   - last shutdown phase marker/timestamp
2. Surface this block in `Stats -> Diagnostics`.
3. Add one-click copy/export of blockers payload for incident reports.

## Mycelium hang/slowdown note
User reported severe machine lag while Mycelium terminal was running, and hard terminal close was needed.

Likely areas to inspect first:
- watcher/scanner burst loops
- websocket reconnect storms
- heavy background cleanup or model health checks
- multiple daemons alive after failed stop sequence

Quick recon commands for next chat:
1. `rg -n "while True|sleep|heartbeat|cleanup|watcher|broadcast|websocket" src main.py`
2. inspect active async tasks around lifespan shutdown/startup
3. verify no periodic UI fetch loops remain in MCC Diagnostics and MiniStats

## Repo hygiene warning (important)
Worktree is heavily dirty (many unrelated modified/untracked files).  
Next chat should avoid broad git operations; use file-targeted diffs only for MCC Phase 155 files.

## Main docs updated this wave
- `docs/155_ph/P3_P4_SMOKE_REPORT_2026-02-23.md`
- `docs/155_ph/MARKER_155_ARCHITECT_BUILD_IMPLEMENTATION_V1.md`
- `docs/155_ph/CODEX_HANDOFF_RECON_2026-02-24.md` (this file)
