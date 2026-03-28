# RECON: Undo-Bypassing Actions Audit
**Author:** Epsilon (QA-2) | **Date:** 2026-03-24
**Source:** FCP7 Compliance Matrix Ch.15, useCutEditorStore.ts, cut_routes.py
**Status:** 3 of 5 FIXED, 3 backend ops MISSING

---

## Summary

The FCP7 Compliance Matrix flagged 5 actions as bypassing applyTimelineOps (no undo).
**Alpha has fixed all 5 on the frontend** — they now route through applyTimelineOps.
**However, 3 backend op handlers are missing** — these ops will crash with `ValueError("unsupported timeline op")`.

## Status Table

| # | Action | Frontend | Backend | Undo Works? |
|---|--------|----------|---------|-------------|
| 1 | pasteAttributes | applyTimelineOps ✓ (op: set_effects) | **MISSING** set_effects handler | NO — backend crash |
| 2 | splitEditLCut | applyTimelineOps ✓ (op: trim_clip) | trim_clip EXISTS ✓ | **YES** |
| 3 | splitEditJCut | applyTimelineOps ✓ (op: trim_clip) | trim_clip EXISTS ✓ | **YES** |
| 4 | setClipEffects | applyTimelineOps ✓ (op: set_effects) | **MISSING** set_effects handler | NO — backend crash |
| 5 | addKeyframe | applyTimelineOps ✓ (op: add_keyframe) | **MISSING** add_keyframe handler | NO — backend crash |
| 5b | removeKeyframe | applyTimelineOps ✓ (op: remove_keyframe) | **MISSING** remove_keyframe handler | NO — backend crash |

## What Alpha Fixed (GOOD)

- `pasteAttributes` (store line 831) — now sends `op: 'set_effects'` with clip effects
- `splitEditLCut` (store line 995) — now sends `op: 'trim_clip'` with adjusted duration
- `splitEditJCut` (store line 1010) — now sends `op: 'trim_clip'` with adjusted start
- `setClipEffects` (store line 1135) — now sends `op: 'set_effects'`
- `addKeyframe` (store line 1143) — now sends `op: 'add_keyframe'`
- `removeKeyframe` (store line 1148) — now sends `op: 'remove_keyframe'`

## What Beta Needs to Add (3 ops in cut_routes.py)

**Location:** `_apply_timeline_ops()` in cut_routes.py (after line ~1527, after split_at handler)

### 1. set_effects
```python
elif op_type == "set_effects":
    clip_id = op.get("clip_id")
    effects = op.get("effects", {})
    # Find clip by ID, set clip["effects"] = effects
    # Increment state["revision"]
```

### 2. add_keyframe
```python
elif op_type == "add_keyframe":
    clip_id = op.get("clip_id")
    prop = op.get("property")
    time_sec = op.get("time_sec")
    value = op.get("value")
    # Find clip, append to clip["keyframes"]
```

### 3. remove_keyframe
```python
elif op_type == "remove_keyframe":
    clip_id = op.get("clip_id")
    prop = op.get("property")
    time_sec = op.get("time_sec")
    # Find clip, remove from clip["keyframes"] by property+time
```

## Impact on FCP7 Compliance

After Beta adds these 3 handlers:
- Ch.15 Undo coverage: 12/15 → **15/15** (100%)
- FCP7 total: 62% → ~65%

## Contract Test

`tests/test_hotkey_regression_alpha_changes.py::TestUndoBypassDocumented` already tracks these 3 as XFAIL.
When backend ops are added, these tests will turn from XFAIL → PASS automatically.
