# Safer Render And Three-Layer Results

Дата: `2026-03-11`

## Что было проверено

- `safer 2-layer preset` для кейсов со статусами:
  - `caution`
  - `needs_3_layer`
- `3-layer planner` поверх уже собранных артефактов:
  - `depth_master_16.png`
  - `subject_rgba.png`
  - `clean_plate.png`
- первый `3-layer preview renderer` с compare-выходом:
  - `2-layer vs 3-layer`

## 1. Safer preset

Инструменты:

- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/scripts/photo_parallax_safer_render_bakeoff.py`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/scripts/photo_parallax_safer_render_bakeoff.sh`

Артефакты:

- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/output/render_preview_safer`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/output/render_review_safer`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/output/render_review_safer_full`

### Результат для `caution`

- `3/3` кейса остались `caution`.
- Ни один кейс не ухудшился до `needs_3_layer`.
- Метрики edge pressure немного улучшились:
  - `depth-anything-v2-small / keyboard-hands`: `-12.971 -> -9.04`
  - `depth-pro / cassette-closeup`: `-68.243 -> -52.934`
  - `depth-pro / hover-politsia`: `-21.79 -> -16.96`

### Результат для `needs_3_layer`

- `3/3` кейса остались `needs_3_layer`.
- Review score снизился, но не до безопасного уровня:
  - `depth-anything-v2-small / drone-portrait`: `6 -> 4`
  - `depth-pro / drone-portrait`: `6 -> 4`
  - `depth-pro / keyboard-hands`: `6 -> 6`

### Вывод

- `safer 2-layer preset` полезен как fallback для `caution` сцен.
- Он не заменяет `3-layer mode`.
- Для `needs_3_layer` safe preset можно использовать только как мягкий preview-вариант, но не как quality target.

## 2. Three-layer planner

Инструменты:

- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/scripts/photo_parallax_three_layer_plan.py`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/scripts/photo_parallax_three_layer_plan.sh`

Summary:

- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/output/three_layer_plan/three_layer_plan_summary.json`

Экспортируемый контракт:

- `foreground_rgba.png`
- `midground_rgba.png`
- `background_far_rgba.png`
- `foreground_mask.png`
- `midground_mask.png`
- `background_far_mask.png`
- `depth_bw_preview.png`
- `near_bw_preview.png`
- `layer_overlay.png`
- `three_layer_debug_sheet.png`
- `three_layer_plan.json`

### Покрытие

- planned cases: `6`
- source statuses:
  - `caution`: `3`
  - `needs_3_layer`: `3`

Средний `midground_area_ratio`:

- `depth-anything-v2-small`: `0.21052`
- `depth-pro`: `0.17722`

Наблюдение:

- planner стабильно находит средний слой в диапазоне примерно `9.7% .. 27.8%` кадра.
- слабый кейс separability обнаружен у `depth-pro / drone-portrait`:
  - `cluster_gap = 0.07393`
- это означает, что не каждый `needs_3_layer` кадр имеет одинаково сильную глубинную структуру вне foreground.

### Вывод

- `three_layer_plan.json` можно считать рабочим render-contract.
- `cluster_gap` пригоден как confidence signal для выбора между:
  - `3-layer required`
  - `3-layer weak but still preferable`

## 3. Three-layer renderer

Инструменты:

- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/scripts/photo_parallax_render_preview_3layer.py`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/scripts/photo_parallax_render_preview_3layer.sh`

Summary:

- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/output/render_preview_3layer/render_preview_3layer_summary.json`

Выходы на кейс:

- `preview_3layer.mp4`
- `preview_3layer_poster.png`
- `compare_2layer_vs_3layer.mp4`
- `render_report_3layer.json`

### Runtime

- rendered cases: `6/6`
- average runtime: `2.01829s`
- `depth-anything-v2-small`: `2.01286s`
- `depth-pro`: `2.021s`

### Вывод

- `3-layer preview render` уже рабочий как sandbox path.
- Теперь у pipeline есть не только аналитический `3-layer gate`, но и реальный `3-layer output`.
- Следующий логичный шаг: отдельный visual review именно для `2-layer vs 3-layer`, потому что текущий review scorer спроектирован под `2-layer risk`, а не под сравнение качества между режимами.

## Принятые решения

- сохранить `safer 2-layer` как fallback path для `caution`.
- эскалировать `needs_3_layer` в `3-layer planner + 3-layer render`.
- не пытаться решать `needs_3_layer` только уменьшением амплитуды камеры.

## 4. Mode routing review

Инструменты:

- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/scripts/photo_parallax_mode_routing_review.py`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/scripts/photo_parallax_mode_routing_review.sh`

Summary:

- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/output/mode_routing_review/mode_routing_summary.json`

Итог routing-а:

- `two_layer`: `2`
- `three_layer`: `5`
- `three_layer_low_confidence`: `1`

Практический вывод:

- `depth-anything-v2-small` уже имеет два уверенных `two_layer` кейса.
- `depth-pro / drone-portrait` не должен идти в обычный `2-layer`, но и `3-layer` там помечен как `low confidence` из-за слабого `cluster_gap`.
- текущий routing rule уже пригоден как sandbox default:
  - `two_layer_ok -> two_layer`
  - `caution -> three_layer`, если midground separation достаточно сильна; иначе `safe_two_layer`
  - `needs_3_layer -> three_layer`, при слабом separation с флагом `low confidence`
