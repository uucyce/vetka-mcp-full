# PHASE 164 — P0 UI Surface Full Map (2026-03-07)

Status: `IMPL NARROW` (doc-contract only)  
Marker: `MARKER_164.P0.UI_SURFACE_FULL_MAP.V1`

Scope: all MCC runtime UI surfaces, excluding DEV panel.

## 1) Top Bar
1. `project tabs` (`vetka_live_*`, `+ project`)
2. `MYCO top avatar` (visible when helper mode is `off`)
3. `MYCO top hint capsule` (passive/proactive short instruction)
4. `window shell title` (`MYCELIUM`)
5. `window control` (expand/open button in top-right)

## 2) Floating Mini Windows
1. `MiniTasks` (`windowId=tasks`)
2. `MiniChat` (`windowId=chat`)
3. `MiniStats` (`windowId=stats`)
4. `MiniBalance` (`windowId=balance`)
5. `MiniContext` (`windowId=context`)

## 3) Window Dock
1. Collapsed window buttons (`MiniWindowDock`)
2. Restore behavior per window
3. Chat restore special-case for active MYCO animation trigger

## 4) DAG Canvas Interaction
1. Node click/select
2. Multi-select focus set
3. Double-click drill-in
4. Enter key drill-in
5. Inline workflow unfold (`wf_*`, `rd_*`)
6. Task overlay nodes (`task_overlay_*`)

## 5) Context Menus
1. Canvas menu:
- add node (`task`, `agent`, `condition`, `parallel`, `loop`, `transform`, `group`)
2. Node menu:
- `Create Task Here`
- `Approve Suggested Anchor`
- `Duplicate`
- `Delete`
3. Edge menu:
- `Delete Edge`

## 6) MiniTasks Surface Inventory
1. Active task row
2. `start` action button
3. `stop` action button
4. Task list rows (select)
5. Heartbeat controls:
- `on/off`
- interval preset (`10m`, `30m`, `1h`, `4h`, `1d`)

## 7) MiniChat Surface Inventory
1. Architect header mode (`helperMode=off`)
2. MYCO header mode (`helperMode!=off`)
3. MYCO icon button in chat header (toggle off/on cycle)
4. Model chip / preset label
5. Input box (`Ask...` / `Ask MYCO...`)
6. Send button
7. Compact last-answer area
8. Expanded conversation stream
9. MYCO bubble style for helper messages

## 8) MiniContext Surface Inventory
1. Compact context summary fields:
- level/source/kind/status/role/model/path
2. Expanded project context pane
3. Expanded task context pane
4. Expanded agent context pane
5. Agent model binder section (`save`)
6. Agent preprompt preview section
7. File preview section
8. Node/workflow stream/artifact section

## 9) MiniStats Surface Inventory
1. Core counters (`runs`, `success`, `avg`, `cost`)
2. Scope subtitle (project/task/agent/file/node)
3. Contextual status line
4. Diagnostics micro-line (`wf`, `graph`, retry/diag chips)
5. Prefetch reinforcement diagnostics view

## 10) MiniBalance Surface Inventory
1. Selected key/provider summary
2. Key balance/cost/tokens/calls rows
3. Favorite toggle (`★`)
4. Key switch interaction
5. Expanded full balances panel

## 11) Global Feedback Channels
1. Top MYCO hint channel (when helper off)
2. Chat MYCO message channel (when helper on)
3. Toast container for action errors/info
4. Bottom drill hint fallback (legacy location, should be superseded by top MYCO hint)

## 12) Contract Note
This map is canonical input for:
1. `MARKER_164.P0.MYCO_UI_ACTION_CATALOG.V1`
2. `MARKER_164.P0.MYCO_UI_COVERAGE_MATRIX.V1`
3. upcoming shared role-aware core (`MARKER_164.P1.*`)
