# Camera Safe And Plate Risk Results

Дата: `2026-03-14`

## Что сделано

Введён первый `camera-safe` contract для `Multi-Plate` path.

Реализация:

- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/src/App.tsx`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/scripts/photo_parallax_render_preview_multiplate.py`

Теперь `plate_layout.json` содержит:

- `cameraSafe`
- `transitions[]`
- per-plate `risk`

## Что именно появилось в contract

### Per-plate risk

Для каждого plate:

- `plateCoverage`
- `recommendedOverscanPct`
- `minSafeOverscanPct`
- `disocclusionRisk`
- `cameraSafe`

### Camera-safe summary

На уровне layout:

- `cameraSafe.ok`
- `cameraSafe.recommendedOverscanPct`
- `cameraSafe.minSafeOverscanPct`
- `cameraSafe.highestDisocclusionRisk`
- `cameraSafe.worstTransitionRisk`
- `cameraSafe.riskyPlateIds[]`
- `cameraSafe.warning`

### Plate transitions

Для соседних visible plate-ов:

- `fromId`
- `toId`
- `overlapArea`
- `zGap`
- `transitionRisk`
- `cameraSafe`

## Результат на gated multi-plate sample set

Артефакты:

- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/output/render_preview_multiplate_qwen_gated/render_preview_multiplate_summary.json`

### `hover-politsia`

- routing: `multi-plate`
- `cameraSafe.ok = false`
- `recommendedOverscanPct = 26.07`
- `minSafeOverscanPct = 20.09`
- `highestDisocclusionRisk = 42.16`
- `worstTransitionRisk = 36.94`
- warning:
  - `overscan below plate-safe minimum`

### `keyboard-hands`

- routing: `multi-plate`
- `cameraSafe.ok = false`
- `recommendedOverscanPct = 25.88`
- `minSafeOverscanPct = 19.93`
- `highestDisocclusionRisk = 43.57`
- `worstTransitionRisk = 46.34`
- warning:
  - `overscan below plate-safe minimum`

### `truck-driver`

- routing: `multi-plate`
- `cameraSafe.ok = false`
- `recommendedOverscanPct = 25.64`
- `minSafeOverscanPct = 19.74`
- `highestDisocclusionRisk = 44.68`
- `worstTransitionRisk = 58.80`
- warning:
  - `overscan below plate-safe minimum`

Практически это самый интересный кейс:

- `truck-driver` уже даёт not only overscan pressure, но и явный risky transition между соседними plate-ами.

## Product вывод

Теперь `Multi-Plate` может предупреждать не только whole-frame эвристикой, а через:

- plate-local disocclusion risk;
- transition risk между plate-ами;
- явный `cameraSafe` verdict.

Это уже ближе к реальной операторской логике:

- scene может быть формально разложена на plate-ы,
- но всё равно быть unsafe для выбранного camera move.

## Ограничение

Это ещё first-pass risk model:

- risk считается по `box + z + parallax strength + overscan`, а не по настоящему 3D geometry;
- transition risk пока adjacency-based, не full visibility graph.

## Следующий шаг

Следующий правильный шаг по roadmap:

- ввести `auto-warning` и motion suggestion из `cameraSafe`;
- затем начать plate-specific blur / atmosphere / degradation controls уже поверх camera-safe verdict.
