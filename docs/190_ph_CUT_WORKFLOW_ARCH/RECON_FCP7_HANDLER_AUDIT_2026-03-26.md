# RECON: FCP7 Handler Audit — 82/82 Actions Verified
**Date:** 2026-03-26
**Agent:** Epsilon QA | **Branch:** `claude/cut-qa-2`
**Method:** Sonnet code analysis agents + manual test verification

---

## Summary

| Metric | Value |
|--------|-------|
| Total CutHotkeyAction entries | **82** |
| REAL handlers | **82** (100%) |
| STUB handlers | **0** |
| MISSING handlers | **0** |
| Key collisions fixed | **1** (Premiere `rollTool` 'n' → 'Shift+n') |
| Test failures fixed | **5** (stale assertions + regex bugs) |
| New tasks filed | **2** (MenuBar label mismatch + synthetic event anti-pattern) |

---

## Fixes Committed This Session

| Commit | Description |
|--------|-------------|
| `837bc254` | fix: Premiere rollTool 'n' → 'Shift+n' (collision with toggleSnap) |
| `9c86a752` | test: update Premiere rollTool assertion |
| `f711dbb7` | fix: test_hotkey_wiring.py — add 21 missing actions + TS drift-detection test |
| `75ad25d9` | fix: test_split_at_playhead — align with CTRLV_FIX design decision (Cmd+k) |
| `40a681e4` | fix: hotkey regression tests — rollTool Shift+n + ACTION_SCOPE regex |
| `ec522731` | fix: FCP7 scanner regex — handle double-quoted bindings (extractClip) |

---

## Semantic Issues Found (all handlers REAL but with caveats)

### 1. markClip uses legacy setters — MEDIUM
`markClip` (X key) calls `setMarkIn()`/`setMarkOut()` which mirror to `sourceMarkIn/Out`.
FCP7 behavior: X should set sequence marks to clip boundaries when focused on timeline.
Store has `setSequenceMarkIn()`/`setSequenceMarkOut()` but they're not called here.
**Owner:** Alpha (editing domain)

### 2. Dead useThreePointEdit import — LOW
`useThreePointEdit` hook is instantiated (line 103) and listed in useMemo deps (line 935),
but `threePointInsert`/`threePointOverwrite` are never called. Both `insertEdit` and
`overwriteEdit` use fully inline local-first logic instead. Dead weight.
**Owner:** Alpha (editing domain)

### 3. superimpose doesn't create V2 track — LOW
When only one video lane exists, clip is placed on V1 instead of creating V2.
FCP7 behavior: superimpose creates a new track if needed.
**Owner:** Alpha (editing domain)

### 4. slipTool cycling diverges from FCP7 — INFO
`slipTool` (Y) toggles between 'slip' and 'slide'. FCP7 uses SS/SSS double/triple-press
cycling which isn't feasible in web. Current cycling design is intentional.
**Status:** Accepted deviation — documented in CUT_HOTKEY_ARCHITECTURE.md

### 5. MenuBar shortcut labels don't match presets — HIGH
- Snap: shows 'S', actual key is 'N'
- Speed/Duration: shows '⌘R', actual key is '⌘J'
- Clear In/Out: shows '⌥X' (correct for FCP7, wrong for Premiere)
- Play In/Out: shows '⇧\' (correct for Premiere, wrong for FCP7)
**Filed:** `tb_1774483293_1` → Gamma

### 6. MenuBar synthetic KeyboardEvent anti-pattern — MEDIUM
Undo/Redo/Marker/Insert/Replace dispatch synthetic events to `document`
instead of calling store directly. Fragile — breaks if hotkey listener is disabled.
**Filed:** `tb_1774483324_1` → Gamma

### 7. Escape double-handling — LOW
When menu is open, Escape fires both `escapeContext` (clears selection, resets tool)
AND the MenuBar close handler. User loses selection just from closing a menu.
**Owner:** Gamma (UX domain)

---

## Test Health After This Session

| Test File | Before | After |
|-----------|--------|-------|
| test_fcp7_hotkey_mapping.py | 23 pass, 2 fail | **25 pass** |
| test_hotkey_wiring.py | 11 pass (stale) | **12 pass** (82 actions synced + drift guard) |
| test_hotkey_regression_alpha_changes.py | 78 pass, 2 fail | **80 pass** |
| test_fcp7_auto_compliance_scanner.py | 10 pass, 2 fail | **12 pass** |
| **Total hotkey tests** | **122 pass, 6 fail** | **129 pass, 0 fail** |

---

## Pre-existing Failures (Not Caused By This Session)

The remaining 60 failures in the full suite are pre-existing:
- `tests/phase170/` — backend API tests (server not running)
- `tests/phase172/` — export endpoint tests (server not running)
- `test_agent_registry.py` — YAML loading issues
- `test_performance_baseline.py` — requires live server
- Others: environment-dependent tests

---

## Store Methods — All Verified Present

Every store method called by handlers exists and is implemented in `useCutEditorStore.ts`:
`togglePlay`, `pause`, `seek`, `seekSource`, `applyTimelineOps`, `selectAllClips`,
`copyClips`, `cutClips`, `pasteClips`, `liftClip`, `extractClip`, `closeGap`,
`extendEdit`, `splitEditLCut`, `splitEditJCut`, `addDefaultTransition`, `setActiveTool`,
`cycleTrackHeights`, `getKeyframeTimes`, `addKeyframe`, `toggleRecordMode`,
`toggleLinkedSelection`, `toggleSnap`, `setShowSpeedControl`, `setViewMode`,
`setFocusedPanel`, `setMarkers`, `clearSelection`, `setSourceMedia`, `setMarkIn`,
`setMarkOut`, `setSourceMarkIn`, `setSourceMarkOut`, `setSequenceMarkIn`,
`setSequenceMarkOut`, `setPlaybackRate`, `setShuttleSpeed`, `setZoom`, `setLanes`
