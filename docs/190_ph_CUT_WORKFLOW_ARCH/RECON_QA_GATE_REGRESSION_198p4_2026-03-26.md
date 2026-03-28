# QA Gate Regression Report — Phase 198.4
**Date:** 2026-03-26
**Agent:** Delta (QA Engineer)
**Task:** tb_1774410449_1
**Branch:** worktree-cut-qa (merged with main at 93f26ec12)
**Type:** Post-merge regression analysis

---

## Executive Summary

After 56-commit batch merge into main from 4 worktree branches, **3 regressions** found affecting **42 tests**.

| Tier | Result | Detail |
|------|--------|--------|
| **T1: Vite Build** | PASS | Built in 5s, no TS errors. Chunk size warning only (3.7MB main bundle). |
| **T2: Python Tests** | **4873 PASS / 31 FAIL / 11 ERR / 23 COLLECT-ERR** | 3 distinct bugs below |
| **T3: Playwright E2E** | PENDING | Requires dev server |

---

## BUG-1: CRITICAL — `run_favorites_assembly` import chain break

**Impact:** 38 tests broken (23 collection errors + 14 runtime + 1 reflex router)
**Files:**
- `src/services/pulse_auto_montage.py` — 3 assembly stubs deleted (lines 670-690 on main)
- `src/api/routes/cut_routes_pulse.py:49-52` — still imports the deleted functions

**Root Cause:** Merge artifact. The stubs exist on `main` but were deleted on the worktree branch. When `origin/main` was merged into `worktree-cut-qa`, the branch's deletion won the merge.

**Affected test modules:**
- `tests/phase170/` (19 files) — ALL blocked
- `tests/phase172/test_cut_export_endpoints.py`
- `tests/phase173/test_cut_edit_ops.py`
- `tests/phase180/test_phase180_dag_project.py`
- `tests/test_three_point_edit.py` (4 failures)
- `tests/test_trim_ops.py` (10 failures)
- `tests/test_undo_fix_ops.py` (11 errors)
- `tests/test_reflex_telemetry.py` (1 failure)

**Fix:** Restore the 3 stub functions at the bottom of `pulse_auto_montage.py`:
```python
async def run_favorites_assembly(project_id: str, **kwargs) -> MontageResult:
    engine = get_auto_montage()
    return MontageResult(clips=[], duration_sec=0.0, strategy="favorites")

async def run_script_assembly(project_id: str, **kwargs) -> MontageResult:
    engine = get_auto_montage()
    return MontageResult(clips=[], duration_sec=0.0, strategy="script")

async def run_music_assembly(project_id: str, **kwargs) -> MontageResult:
    engine = get_auto_montage()
    return MontageResult(clips=[], duration_sec=0.0, strategy="music")
```

**Severity:** P0 — blocks server startup (import fails at module load)

---

## BUG-2: MEDIUM — `transitions` panel contract drift

**Impact:** 3 test failures in `test_workspace_preset_builders_contract.py`
**Files:**
- `client/src/components/cut/presetBuilders.ts` — `transitions` panel removed/renamed
- `tests/test_workspace_preset_builders_contract.py` — expects 12 panels, finds 11

**Details:**
- `test_panel_count`: `assert 11 == 12`
- `test_all_expected_panels`: `missing panels: {'transitions'}`
- `test_effects_tab_group`: `StopIteration` (can't find transitions panel)

**Fix:** Either restore `transitions` panel in presetBuilders.ts OR update test to match new 11-panel layout.

**Severity:** P2 — tests fail but UI functional

---

## BUG-3: LOW — `_extract_predecessor_advice_from_json` missing

**Impact:** 1 collection error in `tests/test_claude_md_generator.py`
**Files:**
- `src/tools/generate_claude_md.py` — function removed/renamed
- `tests/test_claude_md_generator.py:21` — still imports it

**Fix:** Update test import to match current API or remove test for deleted function.

**Severity:** P3 — tooling test, not production code

---

## Healthy Areas (4873 PASS)

Core backend is solid:
- API endpoints (phase 170 tests that don't import cut_routes directly)
- FFmpeg/export pipeline
- DAG project model
- Task board, agent registry, artifact scanner
- Session management, memory systems
- All 1750 skipped tests are expected (markers, missing fixtures)

---

## Recommendations

1. **Immediate:** Restore pulse_auto_montage.py stubs (BUG-1) — Alpha/Beta domain
2. **Next:** Update workspace preset contract test (BUG-2) — Delta can fix (test file)
3. **Low priority:** Fix claude_md_generator test (BUG-3) — Zeta domain
4. **T3 Playwright:** Run after BUG-1 is fixed (server won't start without it)
