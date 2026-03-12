# Real Depth Baseline Results

Дата: `2026-03-12`

## Что проверялось

- sandbox больше не должен показывать только proxy-depth;
- review probe должен уметь снимать настоящий `B/W depth preview`;
- ручные `Closer / Farther` strokes должны менять сам depth-remap, а не только overlay.

## Что сделано

- в `/photo_parallax_playground/src/App.tsx` подключён реальный baked depth preview из:
  - `/photo_parallax_playground/public/depth_bakeoff/depth-pro/<sample>/depth_preview.png`
- для `Base` зафиксирован стандарт preview polarity:
  - `white = near`
  - `black = far`
- `buildProxyMaps(...)` теперь строит depth/remap от baked raster, если он доступен;
- `window.vetkaParallaxLab.getState()` расширен полями:
  - `previewMode`
  - `usingRealDepth`
- review probe и wrapper теперь поддерживают:
  - `PARALLAX_LAB_PREVIEW_MODE=depth`
  - `PARALLAX_LAB_MANUAL_HINTS_PATH=/abs/path/to/manual_hints.json`
- добавлены первые `depth-paint` presets:
  - `/photo_parallax_playground/e2e/depth_paint_presets/drone-portrait.depth-paint.json`
  - `/photo_parallax_playground/e2e/depth_paint_presets/cassette-closeup.depth-paint.json`

## Проверка

Запуски:

- `npm test`
- `npm run build`
- `PARALLAX_LAB_PREVIEW_MODE=depth ./scripts/photo_parallax_review.sh drone-portrait --no-open`
- `PARALLAX_LAB_PREVIEW_MODE=depth PARALLAX_LAB_MANUAL_HINTS_PATH=.../drone-portrait.depth-paint.json ./scripts/photo_parallax_review.sh drone-portrait --no-open`
- `PARALLAX_LAB_PREVIEW_MODE=depth ./scripts/photo_parallax_review.sh cassette-closeup --no-open`
- `PARALLAX_LAB_PREVIEW_MODE=depth PARALLAX_LAB_MANUAL_HINTS_PATH=.../cassette-closeup.depth-paint.json ./scripts/photo_parallax_review.sh cassette-closeup --no-open`

## Артефакты

- raw depth:
  - `/photo_parallax_playground/output/review/drone-portrait-depth-raw.png`
  - `/photo_parallax_playground/output/review/cassette-closeup-depth-raw.png`
- edited depth:
  - `/photo_parallax_playground/output/review/drone-portrait-depth-edited.png`
  - `/photo_parallax_playground/output/review/cassette-closeup-depth-edited.png`
- compare sheet:
  - `/photo_parallax_playground/output/review/depth-paint-compare-sheet.png`

## Что получилось

- `drone-portrait`:
  - `usingRealDepth = true`
  - raw `hintStrokeCount = 0`
  - edited `hintStrokeCount = 4`
  - `selectionCoverage: 0.0163 -> 0.0584`
- `cassette-closeup`:
  - `usingRealDepth = true`
  - raw `hintStrokeCount = 0`
  - edited `hintStrokeCount = 5`
  - `selectionCoverage: 0.1360 -> 0.1530`
- `keyboard-hands`:
  - `usingRealDepth = true`
  - raw `hintStrokeCount = 0`
  - edited `hintStrokeCount = 6`
  - `selectionCoverage: 0.2217 -> 0.2082`
  - вывод: depth-paint уже заметно меняет карту, но для tabletop-сцены текущий preset скорее сужает слой, чем улучшает его.

## Новый repeatable tool

- добавлен wrapper:
  - `/scripts/photo_parallax_depth_paint_review.sh`
- он последовательно снимает:
  - `raw depth`
  - `edited depth`
  - `raw composite`
  - `edited composite`
- затем сохраняет:
  - `<sample>-depth-compare.png`
  - `<sample>-composite-compare.png`
- после добавления retry-проверки `usingRealDepth`, wrapper стабильно отрабатывает на `drone-portrait`.
- служебные цветные overlay теперь показываются только в `selection`-режиме;
  обычные `depth` и `composite` preview очищены от них.

## Вывод

- настоящая `B/W depth` карта в sandbox уже есть;
- `Closer / Farther` strokes уже работают как depth correction layer;
- это первый честный шаг к `DaVinci-like Base`:
  - `depth map`
  - `B/W preview`
  - `near/far/gamma`
  - `white = closer`
  - `black = farther`
- следующий шаг:
  - не расширять UI;
  - сравнить `raw depth render` vs `edited depth render` уже не только на портрете, но и на hard cases вроде `keyboard-hands`.
