# Parallax Release Notes V1 RC1

Дата: `2026-03-19`

## Scope

`RC1` фиксирует release-ready sandbox path для `photo_parallax_playground` без интеграции в основной UI VETKA.

Важно:

- успешный `export/render` не считается достаточным признаком product readiness;
- `RC1 pass` означает, что текущий sandbox/export pipeline технически стабилен на canonical smoke;
- `RC1 pass` не означает, что layered spatial parallax quality уже подтверждена как deploy-grade product truth.

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
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/output/render_compare_qwen_gated_multiplate/visual_acceptance_summary.json`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/output/render_compare_qwen_gated_multiplate/visual_acceptance_checklist.md`

## Current RC1 Verdict

- batch status: `pass`
- current count profile: `pass=3`, `caution=0`, `fail=0`

Этот verdict нужно читать узко:

- он подтверждает export readiness и smoke repeatability;
- он не закрывает visual acceptance сам по себе;
- он не даёт автоматического `ready to deploy`.

What changed to reach `pass`:

- export/layout path now auto-applies `cameraSafe.suggestion` for risky scenes before final contract/render generation;
- `plate_layout.json` records both requested and effective motion via `cameraSafe.adjustment`;
- canonical smoke now finishes with `attempts=1` across the current sample set.

## What Changed Recently

- `v1.3`: final render presets and preset-aware render summaries
- `v1.4`: regression quality pack with evidence links
- `v1.5`: release-critical layout/export builders extracted from `App.tsx` into `src/lib/plateLayout.ts`
- `v1.6`: camera-safe auto-adjusted export motion plus traceable requested/effective motion in `plate_layout.json`
- `v1.7`: visual acceptance pack builder added to keep `product truth` separate from `export pass`

## Known Limits

- TaskBoard hard-close still depends on `pipeline_success`; current fallback flow uses `done_worktree`
- `Qwen-Image-Layered` is still not integrated as an alternative backend yet
- release is sandbox-grade, not product-integrated
- current release docs require a separate visual acceptance gate so export success does not replace depth-first product truth
