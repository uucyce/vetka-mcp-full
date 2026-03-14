# PHASE 155E — Regression Recon: Missing Edges + Sticky Context Menu (2026-03-04)

Protocol: `RECON + markers -> REPORT` after user re-verified failure on full restart (all 3 servers).

## 1) User-verified failure state

1. After full restart, roadmap still appears fragmented (many expected links missing).
2. Right-click context behavior still feels sticky/non-reset.
3. Requirement: strict hygiene log for attempted fixes that did not resolve production behavior.

## 2) Hygiene log — what was tried and what did not work

### Attempt A (previous hotfix, now marked insufficient)

1. Force grandma roadmap to `focusDisplayMode='all'`.
2. Add inline persist fallback for unprefixed node IDs.
3. Close context menu in selection handlers (`node select`, `edge select`, `level-aware transitions`).

Result:
- Unit tests passed.
- Real UI (user verification after restart) still failed.
- Status: **INSUFFICIENT** (kept as non-destructive guard, but not root-cause fix).

Marker:
- `MARKER_155E.REGRESSION.FAILED_HOTFIX_NOTED.V2`

### Attempt B (regression introduced, rolled back)

1. Added transition effect that always closed context menu on selection/drill deps.
2. Added global `document.contextmenu` close handler.
3. Left bottom `FooterActionBar` visible in grandma UI.

Result:
- Right-click became effectively unusable (menu closed immediately after open).
- Visual contract broken (persistent hardcoded bottom actions appeared).
- Status: **FAILED + ROLLED BACK**.

Marker:
- `MARKER_155E.REGRESSION.FAILED_CONTEXT_AUTOCLOSE_ROLLBACK.V1`

### Attempt C (over-aggressive roadmap source gating, partially rolled back)

1. Added strict “unhealthy condensed -> skip source” behavior.
2. On fetch errors, roadmap state could be cleared to empty canvas.

Result:
- In unstable moments user saw fully blank canvas.
- Status: **PARTIAL FAIL + FIXED**.

Fix:
1. Never clear last-known-good roadmap snapshot in `catch`.
2. If condensed is unhealthy, use best available condensed payload instead of empty skip.
3. Keep tree/data and legacy fallbacks as lower priority, not destructive reset.

## 3) Full recon findings (code-grounded)

### Finding F1 — roadmap source can be sparse by contract

`useRoadmapDAG` source priority was:
1. `/api/mcc/graph/build-design`
2. `/api/mcc/graph/condensed`
3. `/api/tree/data`
4. legacy `/api/mcc/roadmap`

Problem:
- The first non-empty source was accepted even if graph topology was too sparse for grandma UX (many nodes with too few connecting edges).
- In condensed path, source preferred `l2_overview` over full `l2`, which can be too compact for “truth view”.

Impact:
- Visual symptom exactly matches user screenshot: isolated nodes + perceived lost links.

### Finding F2 — context menu target can outlive graph mutation

Even with handler-level closes, target lifecycle still depended on interaction path.
If graph snapshot changed (drill/source refresh), menu target could stay stale.

Impact:
- “Sticky” right-click actions / ghost menu state.

### Finding F3 — roadmap can be overridden by debug source payload path

In `MyceliumCommandCenter`, roadmap data path used:
`sourceModeRoadmapGraph || versionRoadmapGraph || roadmap`.

Problem:
- This override could apply outside debug UX and replace roadmap truth with sparse source-mode payload.

Impact:
- Persistent sparse tree even when base roadmap hook is healthy.

## 4) Markers for current recon cycle

1. `MARKER_155E.REGRESSION.ROADMAP_SOURCE_DENSITY_GUARD.V1`
2. `MARKER_155E.REGRESSION.CONDENSED_L2_PREFERENCE_OVER_OVERVIEW.V1`
3. `MARKER_155E.REGRESSION.CONTEXT_MENU_GRAPH_VALIDATION_RESET.V1`
4. `MARKER_155E.REGRESSION.DEBUG_SOURCE_OVERRIDE_GUARD.V1`
5. `MARKER_155E.REGRESSION.GRANDMA_NO_PERSISTENT_FOOTER_ACTIONS.V1`

## 5) Narrow implementation applied now

### I1 — Roadmap source density guard

File: `client/src/hooks/useRoadmapDAG.ts`

- Added `hasReadableTopology(nodes, edges)` health check.
- Build-design path now:
  - prefers `design_graph` only when healthy,
  - otherwise falls back to `runtime_graph.l2` when healthy,
  - otherwise continues to next source.

### I2 — Prefer full `l2` over `l2_overview` in condensed path

File: `client/src/hooks/useRoadmapDAG.ts`

- Source arbitration now prefers `l2` when healthy.
- Uses `l2_overview` only as fallback (or when `l2` is unavailable/unhealthy).

### I3 — Context menu stale-target reset by graph validity

File: `client/src/components/mcc/MyceliumCommandCenter.tsx`

- Added effect that closes context menu if target node/edge is no longer present in `graphForView` snapshot.

### I4 — Global right-click close outside menu

File: `client/src/components/mcc/DAGContextMenu.tsx`

- **Rolled back** (caused right-click break in real UI).

### I5 — Debug-only source override for roadmap graph

File: `client/src/components/mcc/MyceliumCommandCenter.tsx`

- `versionRoadmapGraph` and `sourceModeRoadmapGraph` now gated by `debugMode`.
- Grandma mode always uses roadmap truth source from `useRoadmapDAG`.

### I6 — Remove persistent bottom action bar in grandma canvas

File: `client/src/components/mcc/MyceliumCommandCenter.tsx`

- Removed always-visible `FooterActionBar` from canvas.
- Restored contract: persistent UI is mini-windows only.

### I7 — Non-destructive roadmap fallback (anti-black-canvas)

File: `client/src/hooks/useRoadmapDAG.ts`

- Added build/condensed fallback selection even when health checks fail.
- Preserved last-known-good roadmap graph on fetch error (no forced empty reset).

## 6) Verification status

Automated:
- To run after patch: targeted phase tests + regression tests.

Manual:
- Pending user re-check in real UI after patch.

## 7) If still failing after this patch

Next recon markers:
1. `MARKER_155E.REGRESSION.API_PAYLOAD_EDGE_COUNT_DIFF.V1`
2. `MARKER_155E.REGRESSION.ROADMAP_OVERLAY_MUTATION_TRACE.V1`
3. `MARKER_155E.REGRESSION.DAGVIEW_CONTEXT_EVENT_TRACE.V1`

Next steps:
1. Log raw edge counts per source (`build-design`, `condensed:l2`, `tree`) in runtime toast/debug snapshot.
2. Capture `graphForView` before/after task overlay sync to detect edge drops.
3. Add deterministic UI-level repro test for menu close on repeated right-click + drill transition.

## 8) Current status (post-fix check)

User confirmation in UI: tree vectors returned and hardcoded bottom bar removed.

Verified:
1. Right-click no longer auto-closes immediately (rollback of faulty transition auto-close).
2. Grandma canvas now shows mini-window-only persistent UI.
3. Roadmap source arbitration avoids sparse condensed payloads by falling through to richer source path.
