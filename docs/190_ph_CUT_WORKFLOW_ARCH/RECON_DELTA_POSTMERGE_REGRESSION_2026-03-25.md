# Post-Merge Regression Report
**Date:** 2026-03-25 12:00 UTC
**Agent:** Delta-6 (QA Gate)
**Branch:** worktree-cut-qa
**Scope:** Full smoke suite after 56-commit batch merge into main

---

## Summary

| Metric | Value |
|--------|-------|
| Total tests | 6655 |
| Passed | 4791 |
| Skipped | 1862 |
| Failed | 10 (+ 1 vite build) |
| xfailed | 1 |
| Duration | 218s |

## Regressions Found & Actions Taken

### CRITICAL: Vite build broken
- **Test:** `test_cut_build_smoke.py::test_vite_build_succeeds`
- **Root cause:** `EFFECT_APPLY_MAP` in `EffectsPanel.tsx:404` is `const` (not exported), but `TimelineTrackView.tsx:25` imports it
- **Action:** Filed `tb_1774429581_1` for Gamma — one-word fix (add `export`)

### HIGH: Effects contract drift (FIXED)
- **Test:** `test_cut_effects_contract.py::test_merges_with_existing`
- **Root cause:** A4.11 refactor moved effects merge from inline spread to ops-based `applyTimelineOps([{op: 'set_effects', ...}])`. Test still expected inline spread pattern.
- **Action:** Fixed by Delta — updated test regex to accept ops-based pattern. Commit `d3933f460`.

### MEDIUM: 3 monochrome violations
- **Test:** `test_monochrome_static.py::test_no_non_grey_hex_in_cut_components`
- **Violations:**
  - `DAGProjectPanel.tsx:117` — `#5DCAA5` (green)
  - `ExportDialog.tsx:856` — `#1f1f2a` (blue-tinted)
  - `ExportDialog.tsx:882` — `#1f1f2a` (hover)
- **Action:** Filed `tb_1774429594_1` for Gamma

### LOW: Premiere hotkey collision
- **Test:** `test_fcp7_hotkey_mapping.py::test_premiere_no_collisions`
- **Collision:** `n` bound to both `rollTool` and `toggleSnap`
- **Action:** Filed `tb_1774429694_1` for Epsilon

## Intentional TDD RED (7 tests — not regressions)

All in `test_fcp7_tdd_red_gaps.py` — gap markers for unimplemented features:
1. `TestSnapHotkeyCollision::test_premiere_n_not_duplicated` — same root cause as hotkey collision
2. `TestMultiSequence` (4 tests) — multi-sequence support not yet built
3. `TestMulticamAngleSwitching::test_switch_angle_action` — multicam not yet built
4. `TestSubclips::test_create_subclip_action` — subclip support not yet built
5. `TestSequenceNesting::test_nest_sequence_action` — nesting not yet built

## Other Work This Session

| Task | Action | Status |
|------|--------|--------|
| `tb_1774419678_1` — 3 stale fixme tests | Verified already committed by prior Delta, closed | done_worktree |
| `tb_1774429587_1` — Effects contract fix | Fixed test, committed `d3933f460` | done_worktree |
| `tb_1774429581_1` — Export EFFECT_APPLY_MAP | Filed for Gamma | pending |
| `tb_1774429594_1` — Monochrome violations | Filed for Gamma | pending |
| `tb_1774429694_1` — Premiere hotkey collision | Filed for Epsilon | pending |

## Verdict

**Post-merge state: CONDITIONAL PASS**

- 2 blocking issues need agent fixes before production deploy (vite build + monochrome)
- 1 non-blocking issue (hotkey collision)
- 7 intentional TDD RED gaps (expected)
- No data loss, no architectural breaks
- Effects contract drift was false alarm — architecture evolved correctly, test lagged
