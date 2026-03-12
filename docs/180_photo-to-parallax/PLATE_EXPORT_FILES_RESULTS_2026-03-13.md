# Plate Export Files Results

Дата: `2026-03-13`

## Что сделано

Browser contract `exportPlateAssets()` доведён до реального file/export flow на диск.

Добавлены:

- [spec](/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/e2e/parallax_plate_export.spec.ts)
- [wrapper](/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/scripts/photo_parallax_plate_export.sh)
- [batch wrapper](/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/scripts/photo_parallax_plate_export_batch.sh)

## Что экспортируется

На текущем шаге exporter сохраняет:

- `global_depth_bw.png`
- `background_rgba.png`
- `background_mask.png`
- `plate_01_rgba.png`
- `plate_01_mask.png`
- `plate_01_depth.png`
- `plate_01_clean.png` для `special-clean` / `cleanVariant` paths
- `plate_stack.json`
- `plate_layout.json`
- `plate_export_manifest.json`

Также сохраняются:

- composite screenshot
- depth screenshot
- snapshot/job-state/state JSON

## Проверенный результат

Проверено на:

- `hover-politsia`
- `keyboard-hands`
- `truck-driver`

Артефакты лежат в:

- [plate export dir](/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/output/plate_exports/hover-politsia)
- [manifest](/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/output/plate_exports/hover-politsia/plate_export_manifest.json)
- [global depth](/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/output/plate_exports/hover-politsia/global_depth_bw.png)
- [plate 01 rgba](/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/output/plate_exports/hover-politsia/plate_01_rgba.png)
- [plate 01 depth](/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/output/plate_exports/hover-politsia/plate_01_depth.png)
- [plate stack](/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/output/plate_exports/hover-politsia/plate_stack.json)
- [keyboard manifest](/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/output/plate_exports/keyboard-hands/plate_export_manifest.json)
- [keyboard clean](/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/output/plate_exports/keyboard-hands/plate_04_clean.png)
- [truck manifest](/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/output/plate_exports/truck-driver/plate_export_manifest.json)
- [truck clean](/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/output/plate_exports/truck-driver/plate_04_clean.png)

## Что это значит

Это первый шаг, где complex scene уже реально можно отдавать наружу как набор multi-plate артефактов, а не только смотреть внутри sandbox.

Особенно важно:

- scene теперь читается через `global_depth_bw.png`;
- каждый plate уже имеет свой `depth.png`;
- RGBA plate-ы сохраняются как отдельные файлы.
- `special-clean` plate-ы теперь получают `*_clean.png` как first-pass background-based clean export.

## Ограничения

- exporter пока работает через Playwright/browser flow, а не через dedicated backend exporter;
- `special-clean clean` сейчас first-pass и основан на текущем `background_rgba`, а не на отдельном plate-local inpaint solve;
- `plate_depth` пока derived from current global depth + plate alpha, а не independent local depth solve.
- в процессе найден и исправлен input asset issue:
  - `truck-driver.png` был JPEG-файлом с неправильным расширением;
  - sample приведён к реальному PNG, после чего exporter стал стабильным.

## Следующий шаг

- связать exporter с final render pack;
- добавить plate-local clean generation лучше, чем current background fallback;
- расширить exporter ещё на 2-3 complex scenes после стабилизации `special-clean` semantics.
