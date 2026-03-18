# Parallax Contracts v1

Contract version: `1.0.0`

This document freezes the v1 sandbox contracts for `Portrait Base` and `Multi-Plate`.

## `plate_layout.json`

Required top-level fields:

- `contract_version`
- `sampleId`
- `source`
- `metrics`
- `camera`
- `cameraSafe`
- `routing`
- `transitions`
- `plates`

Required `cameraSafe` fields:

- `ok`
- `recommendedOverscanPct`
- `minSafeOverscanPct`
- `highestDisocclusionRisk`
- `worstTransitionRisk`
- `riskyPlateIds`
- `warning`
- `suggestion`

Required `cameraSafe.suggestion` fields:

- `overscanPct`
- `travelXPct`
- `travelYPct`
- `reason`

## `plate_export_manifest.json`

Required top-level fields:

- `contract_version`
- `sampleId`
- `files`
- `exportedPlates`

Required `files` fields:

- `plateStack`
- `plateLayout`
- `jobState`
- `snapshot`
- `readinessDiagnostics`
- `compositeState`
- `depthState`
- `globalDepth`
- `backgroundRgba`
- `backgroundMask`
- `compositeScreenshot`
- `depthScreenshot`

Required `exportedPlates[]` fields:

- `index`
- `id`
- `label`
- `role`
- `visible`
- `coverage`
- `z`
- `depthPriority`
- `cleanVariant`
- `files`

## `qwen_plate_gate.json`

Required top-level fields:

- `contract_version`
- `sample_id`
- `decision`
- `confidence`
- `metrics`
- `added_special_clean_variants`
- `reasons`
- `gated_plate_stack`
- `created_at`

Required `metrics` fields:

- `manual_visible_count`
- `qwen_visible_count`
- `manual_special_clean_count`
- `qwen_special_clean_count`
- `visible_overlap_ratio`

Required `gated_plate_stack` fields:

- `sampleId`
- `plates`
