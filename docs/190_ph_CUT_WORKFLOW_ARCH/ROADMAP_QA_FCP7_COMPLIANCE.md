# ROADMAP_QA_FCP7_COMPLIANCE
## Plan: 5/14 GREEN -> 14/14 GREEN on FCP7 Deep Compliance TDD Specs
**Author:** Epsilon (QA-2) | **Date:** 2026-03-22 | **Spec:** `client/e2e/cut_fcp7_deep_compliance_tdd.spec.cjs`

---

## Current State: 5/14 GREEN (36%)

| Status | Count | Tests |
|--------|-------|-------|
| GREEN | 5 | TL1, TL1b, MON1, MON1b, KEYS:Shift-L |
| RED | 4 | TL2, MON2, EDIT1, KEYS:Cmd-K |
| SKIP | 5 | TL2b, TL3, TL3b, TL4, EDIT2, EDIT3 |

---

## Wave 1 — Unblock Cascades (Priority: CRITICAL)

Two root failures gate 9 downstream tests. Fixing them is the highest-leverage move.

### Task 1: FCP7-EDIT1 — Fix razor split race condition
- **ID:** `tb_1774151329_3` | **Assign:** Alpha/Gamma | **Complexity:** Medium
- **Problem:** `beginClipInteraction` (mousedown) fires `applyTimelineOps` + `refreshProjectState` BEFORE `handleClipClick` (click) can do local split. The refresh reloads mocked static data, erasing the split.
- **Fix:** Remove razor early-return in `beginClipInteraction` (TimelineTrackView.tsx ~line 902-908). Let `handleClipClick` handle razor — it does local `setLanes` first, then async backend call.
- **Files:** `TimelineTrackView.tsx`, `CutEditorLayoutV2.tsx`
- **Unblocks:** EDIT1 + KEYS:Cmd-K (direct), EDIT2 + EDIT3 (cascade)
- **Expected result:** 5 GREEN -> 7 GREEN (+2), 2 SKIP unlocked

### Task 2: FCP7-TL2 — Add testid/aria-label to visibility toggle
- **ID:** `tb_1774151298_1` | **Assign:** Alpha/Gamma (or Epsilon data-testid exception) | **Complexity:** Low
- **Problem:** Eye button has `title="Hide track"` but no `aria-label` or `data-testid`. Test queries `[aria-label*="visib"]`.
- **Fix:** Add `data-testid={`cut-lane-visibility-${lane.lane_id}`}` + `aria-label="Toggle visibility"` to the eye button in TimelineTrackView.tsx (~line 1725).
- **Files:** `TimelineTrackView.tsx`
- **Unblocks:** TL2 (direct), TL2b + TL3 + TL3b + TL4 (cascade)
- **Expected result:** 7 GREEN -> 8 GREEN (+1), 4 SKIP unlocked

### Wave 1 Target: 8/14 GREEN (57%)

---

## Wave 2 — Unlock Cascade Tests (Priority: HIGH)

With Wave 1 landed, 6 previously-skipped tests will run. Some will pass, some need features.

### TL2b — Visibility toggle dims track
- **Prediction: AUTO-GREEN** — Store already sets opacity 0.3 on hidden lanes. Once TL2 passes and TL2b runs, it should pass.

### TL3 — Editable timecode field above ruler
- **Prediction: LIKELY RED** — Needs `data-testid="cut-timeline-timecode"` or `input[aria-label*="timecode"]` on the ruler timecode. TimelineTrackView has a ruler but timecode input may be missing or unnamed.
- **Fix if RED:** Add `data-testid="cut-timeline-timecode-display"` to the timecode element near ruler.

### TL3b — Typing timecode navigates playhead
- **Prediction: DEPENDS ON TL3** — If timecode field exists and is wired to `seek()`, this should pass.

### TL4 — Display controls (overlays, waveform toggle)
- **Prediction: LIKELY RED** — Test checks for text "Waveform"/"Overlay"/"Track Height" in timeline panel. These controls may not exist yet.
- **Fix if RED:** Add display controls dropdown/toolbar in timeline panel header.

### EDIT2 — Linked clip names underlined
- **Prediction: RED** — No underline logic exists. New feature needed.
- **Task:** `tb_1774151342_4` (combined with EDIT3)

### EDIT3 — Through edit red triangles
- **Prediction: RED** — No through-edit indicator component exists. New feature needed.
- **Task:** `tb_1774151342_4`

### Wave 2 Target: 10-11/14 GREEN (71-79%)

---

## Wave 3 — Feature Builds (Priority: MEDIUM)

Remaining RED tests that require new UI features, not just testid/wiring fixes.

### Task 3: FCP7-MON2 — Source panel testid + Mark Clip + Match Frame
- **ID:** `tb_1774151309_2` | **Assign:** Gamma (UX) | **Complexity:** Low
- **3 changes:** testid on SourceMonitorPanel, Mark Clip (X) button in transport, Match Frame (F) on both monitors
- **Expected result:** +1 GREEN

### Task 4: FCP7-EDIT2+3 — Linked underlines + through edit triangles
- **ID:** `tb_1774151342_4` | **Assign:** Alpha (Engine) | **Complexity:** Medium
- **2 features:** text-decoration:underline on linked clips, red triangle SVG at through-edit boundaries
- **Expected result:** +2 GREEN

### Wave 3 Target: 13-14/14 GREEN (93-100%)

---

## Dependency Graph

```
Wave 1 (unblock)          Wave 2 (cascade)         Wave 3 (features)

EDIT1 fix ───────────────> EDIT2 (underlines) ──────> tb_1774151342_4
  tb_1774151329_3    |     EDIT3 (triangles) ──────>
                     |
                     └───> KEYS:Cmd-K (auto-fix)

TL2 testid fix ──────────> TL2b (auto-green)
  tb_1774151298_1    |     TL3  (check timecode)
                     |     TL3b (check seek)
                     └───> TL4  (check controls)

MON2 panel+buttons ──────> standalone
  tb_1774151309_2
```

---

## Execution Order (recommended)

| Step | Task | Agent | Est. Impact |
|------|------|-------|-------------|
| 1 | `tb_1774151298_1` TL2 testid | Epsilon (data-testid exception) | +1 GREEN, unlocks 4 |
| 2 | `tb_1774151329_3` EDIT1 razor fix | Alpha | +2 GREEN, unlocks 2 |
| 3 | Run TDD suite — assess unlocked tests | Epsilon | Measure actual state |
| 4 | `tb_1774151309_2` MON2 buttons | Gamma | +1 GREEN |
| 5 | `tb_1774151342_4` EDIT2+3 features | Alpha | +2 GREEN |
| 6 | Fix any remaining TL3/TL4 issues | Gamma | +0-2 GREEN |
| 7 | Final TDD suite run — target 14/14 | Epsilon | Confirm 100% |

---

## Success Criteria

- **14/14 GREEN** on `cut_fcp7_deep_compliance_tdd.spec.cjs`
- **No regressions** in existing 43+ smoke tests
- **All fixes comply** with FCP7 manual references (Ch.6, 7, 9, 39, 40)
- **No emoji/colored icons** — monochrome SVG only (per feedback_no_emoji_icons)
