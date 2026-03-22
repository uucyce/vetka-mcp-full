# EXPERIENCE_EPSILON_QA — 2026-03-22
## Agent: Epsilon | QA-2 & FCP7 Compliance | GREEN terminal | Branch: claude/cut-qa-2

---

## Mission
Run FCP7 Deep Compliance TDD specs (`cut_fcp7_deep_compliance_tdd.spec.cjs`) and audit how many RED-by-design tests have turned GREEN after Alpha/Gamma fixes.

## Results: 5/14 GREEN, 4/14 RED, 5/14 SKIP

### GREEN (newly passing — previously RED by design)

| Test | Feature | Notes |
|------|---------|-------|
| TL1 | Track height Shift-T cycle | Height changes on keypress |
| TL1b | Track divider draggable | `row-resize` cursor detected between V/A tracks |
| MON1 | Transport buttons centered | Centering within 20% tolerance confirmed |
| MON1b | Prev/Next Edit buttons | `[aria-label*="previous edit"]` and `[aria-label*="next edit"]` found |
| KEYS:Shift-L | Linked Selection toggle | `linkedSelection` state toggles via `__CUT_STORE__` |

### RED (still failing — needs Alpha/Gamma implementation)

| Test | Feature | Failure Reason |
|------|---------|----------------|
| TL2 | Track visibility toggle (eye icon) | No `[aria-label*="visib"]` or `[data-testid*="visibility"]` elements in lane headers |
| MON2 | Mark Clip (X) / Match Frame (F) buttons | Source panel `[data-testid="cut-panel-source"]` not found, or marking buttons absent |
| EDIT1 | Razor tool (B key) splits clip | `activeTool` state changes but clip count stays at 6 (split not executing on click) |
| KEYS:Cmd-K | Add Edit / split at playhead | Same as EDIT1 — `seek()` works but split logic doesn't increment clip count |

### SKIP (serial cascade — blocked by earlier failure in same describe.serial)

| Test | Blocked By |
|------|------------|
| TL2b: visibility toggle dims track | TL2 fail |
| TL3: editable timecode field | TL2 fail |
| TL3b: typing timecode navigates playhead | TL2 fail |
| TL4: display controls (overlays/waveform) | TL2 fail |
| EDIT2: linked clip names underlined | EDIT1 fail |
| EDIT3: through edit red triangles | EDIT1 fail |

## Observations

1. **Track infrastructure (TL1) is solid** — height cycling and divider cursor both work, meaning the lane layout system is functional.
2. **Monitor transport (MON1) is complete** — centering and edit navigation buttons are present and correct.
3. **Linked Selection (KEYS:Shift-L)** — store-level toggle works, confirming hotkey wiring is live.
4. **Razor/Split gap is the biggest blocker** — EDIT1 and KEYS:Cmd-K both fail on the same issue: the split action doesn't actually create a new clip. This blocks 3 downstream tests (EDIT2, EDIT3 cascade).
5. **Visibility toggle (TL2)** is the other major blocker — its failure cascades to skip 4 tests (TL2b, TL3, TL3b, TL4).
6. **Serial describe blocks amplify failures** — 2 root failures (TL2, EDIT1) cascade to 6 skips. Consider splitting into independent groups once features land.

## Recommendations for Commander

- **Priority 1:** Razor/Split implementation (EDIT1) — unblocks 3 tests
- **Priority 2:** Track visibility toggle (TL2) — unblocks 4 tests
- **Priority 3:** Monitor Mark Clip/Match Frame buttons (MON2) — standalone, no cascade

## Deep Recon: RED Failure Root Causes

### RED 1: TL2 — Track Visibility Toggle (eye icon)
- **Component:** `TimelineTrackView.tsx` ~line 1725-1743
- **Store:** `hiddenLanes: Set<string>` + `toggleVisibility(laneId)` in `useCutEditorStore.ts`
- **Root cause:** Feature IS implemented (eye icon, toggle, opacity dim). But button has only `title="Hide track"` — no `aria-label` or `data-testid`. Test queries `[aria-label*="visib"]` which doesn't match.
- **Fix:** Add `data-testid={`cut-lane-visibility-${lane.lane_id}`}` + `aria-label="Toggle visibility"` to eye button. One-line change.
- **Task:** `tb_1774151298_1`

### RED 2: MON2 — Mark Clip (X) / Match Frame (F)
- **Component:** `MonitorTransport.tsx`, `SourceMonitorPanel.tsx`
- **Root cause (3 issues):**
  1. `SourceMonitorPanel.tsx` has no `data-testid="cut-panel-source"` on root div
  2. Mark Clip (X) button exists in MenuBar.tsx but NOT in MonitorTransport
  3. Match Frame (F) gated by `feed === 'program'` (line 265) — not shown on source monitor
- **Fix:** Add testid to panel, add Mark Clip button to transport, remove feed gate on Match Frame
- **Task:** `tb_1774151309_2`

### RED 3: EDIT1 — Razor tool splits but clip count unchanged
- **Component:** `TimelineTrackView.tsx` lines 902-908 + 1055-1075
- **Store:** `activeTool: 'razor'` activates correctly via `setActiveTool`
- **Root cause:** RACE CONDITION between two handlers:
  - `beginClipInteraction` (mousedown, line 902) fires first — calls `applyTimelineOps` + `refreshProjectState`
  - `handleClipClick` (click, line 1055) fires second — does local `setLanes` split
  - But `refreshProjectState` from mousedown reloads mocked static data, erasing the local split
- **Fix:** Remove razor handling from `beginClipInteraction` (delete lines 902-908). Let `handleClipClick` be the sole handler — it does local split first, then async backend.
- **Task:** `tb_1774151329_3`

### RED 4: KEYS:Cmd-K — Add Edit / split at playhead
- **Component:** `CutEditorLayoutV2.tsx` lines 227-245
- **Root cause:** Same as EDIT1 — `splitClip()` calls `refreshProjectState` after modifying lanes, which resets to static mock data in test env.
- **Fix:** Covered by EDIT1 fix — make split local-first, skip refresh after optimistic ops.
- **Task:** `tb_1774151329_3` (same task)

## Deep Recon: SKIP Analysis

| Test | Blocked By | Will Auto-GREEN? | Notes |
|------|-----------|-------------------|-------|
| TL2b: visibility dims track | TL2 | YES — opacity 0.3 on hidden lanes already works | Auto-green once TL2 testid fix lands |
| TL3: editable timecode field | TL2 (serial cascade) | UNKNOWN — need to check if ruler has timecode input | May need testid on TimecodeField |
| TL3b: typing timecode navigates | TL3 | LIKELY YES — if TimecodeField exists and is wired to seek() | Depends on TL3 |
| TL4: display controls | TL2 (serial cascade) | LIKELY RED — no "Waveform"/"Overlay" text in timeline panel | New feature needed |
| EDIT2: linked underlines | EDIT1 | RED — no underline logic exists | Feature build needed |
| EDIT3: through edit triangles | EDIT1 | RED — no through-edit component exists | Feature build needed |

## Tasks Created on Board

| Task ID | Title | Priority | Unblocks |
|---------|-------|----------|----------|
| `tb_1774151298_1` | FCP7-TL2: testid on visibility toggle | P2 | TL2 + 4 cascade |
| `tb_1774151309_2` | FCP7-MON2: panel testid + Mark Clip + Match Frame | P2 | MON2 |
| `tb_1774151329_3` | FCP7-EDIT1: razor split race condition | P1 | EDIT1 + KEYS:Cmd-K + 2 cascade |
| `tb_1774151342_4` | FCP7-EDIT2+3: underlines + through edit triangles | P3 | EDIT2 + EDIT3 |

## Deliverables
- Experience report: this file
- Roadmap: `docs/190_ph_CUT_WORKFLOW_ARCH/ROADMAP_QA_FCP7_COMPLIANCE.md`
- 4 tasks on board with fix instructions, allowed_paths, completion_contracts

## Session Stats
- Duration: ~15 min active (5 min test run + 10 min deep recon)
- Tests run: 14 unique (29 with retries)
- Dev server: reused existing on port 3009
- No conflicts with Delta (verified via active_agents check)
- 3 parallel Explore agents deployed for codebase investigation

## Tooling Notes
- `node node_modules/@playwright/test/cli.js test` — confirmed working (npx exits 194)
- Retry config (retries=1) doubles Playwright output — read unique test names, not line count
- `__CUT_STORE__` exposure confirmed working for state inspection
- Serial describe blocks amplify failures — 2 root RED cascade to 5-6 SKIP
