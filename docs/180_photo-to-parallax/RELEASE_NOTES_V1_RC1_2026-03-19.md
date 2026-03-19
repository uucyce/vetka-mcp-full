# Parallax Release Notes V1 RC1

Дата: `2026-03-19`

## Scope

`RC1` фиксирует release-ready sandbox path для `photo_parallax_playground` без интеграции в основной UI VETKA.

## What Is Included

- frozen release contracts (`plate_layout`, `plate_export_manifest`, `qwen_plate_gate`);
- gated multi-plate export flow;
- anti-flake readiness diagnostics;
- final render presets:
  - `quality`
  - `web`
  - `social`
- regression quality pack with per-sample `pass/caution/fail`;
- manual vs gated-qwen compare evidence.

## Main Artifacts

- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/output/render_compare_qwen_gated_multiplate/gated_batch_qa_summary.json`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/output/render_compare_qwen_gated_multiplate/regression_quality_summary.json`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/output/render_compare_qwen_gated_multiplate/render_compare_qwen_multiplate_summary.json`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/output/render_compare_qwen_gated_multiplate/compare_batch_sheet.png`

## Current RC1 Verdict

- batch status: `pass`
- current count profile: `pass=3`, `caution=0`, `fail=0`

What changed to reach `pass`:

- export/layout path now auto-applies `cameraSafe.suggestion` for risky scenes before final contract/render generation;
- `plate_layout.json` records both requested and effective motion via `cameraSafe.adjustment`;
- canonical smoke now finishes with `attempts=1` across the current sample set.

## What Changed Recently

- `v1.3`: final render presets and preset-aware render summaries
- `v1.4`: regression quality pack with evidence links
- `v1.5`: release-critical layout/export builders extracted from `App.tsx` into `src/lib/plateLayout.ts`
- `v1.6`: camera-safe auto-adjusted export motion plus traceable requested/effective motion in `plate_layout.json`

## Known Limits

- TaskBoard hard-close still depends on `pipeline_success`; current fallback flow uses `done_worktree`
- `Qwen-Image-Layered` is still not integrated as an alternative backend yet
- release is sandbox-grade, not product-integrated
