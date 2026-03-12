# Mode Compare Review Results

Дата: `2026-03-11`

## Что добавлено

Инструменты:

- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/scripts/photo_parallax_compare_modes.py`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/scripts/photo_parallax_compare_modes.sh`

Артефакты:

- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/output/mode_compare_review/mode_compare_summary.json`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/output/mode_compare_review/mode_compare_batch_sheet.png`

На каждый кейс теперь собираются:

- `mode_compare_sheet.png`
- `mode_compare_grid.mp4`
- `mode_compare_review.json`

Grid-видео собирается как `2x2` коллаж:

- `source`
- `2-layer`
- `safe 2-layer`
- `3-layer`

## Итог по gain buckets

- `high`: `5`
- `medium`: `1`
- `low`: `2`

## Интерпретация

`low`:

- `depth-anything-v2-small / cassette-closeup`
- `depth-anything-v2-small / hover-politsia`

Это совпадает с уже принятым решением: эти кейсы можно оставлять в `two_layer`.

`medium`:

- `depth-pro / drone-portrait`

Этот кейс остаётся специальным:

- `2-layer` плохой
- `3-layer` нужен
- но separability depth-слоя слабая, поэтому routing должен сохранять флаг `low confidence`

`high`:

- `depth-anything-v2-small / drone-portrait`
- `depth-anything-v2-small / keyboard-hands`
- `depth-pro / cassette-closeup`
- `depth-pro / hover-politsia`
- `depth-pro / keyboard-hands`

Для них `3-layer` выглядит как оправданный основной quality path.

## Первые удобные точки просмотра

Смотреть grid-видео:

- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/output/mode_compare_review/depth-anything-v2-small/drone-portrait/mode_compare_grid.mp4`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/output/mode_compare_review/depth-anything-v2-small/keyboard-hands/mode_compare_grid.mp4`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/output/mode_compare_review/depth-pro/cassette-closeup/mode_compare_grid.mp4`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/output/mode_compare_review/depth-pro/drone-portrait/mode_compare_grid.mp4`

Смотреть batch sheet:

- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/output/mode_compare_review/mode_compare_batch_sheet.png`

## Вывод

- compare-review теперь закрывает главный пробел предыдущего цикла: можно смотреть режимы side-by-side, а не только читать summaries.
- текущий `expected_gain_score` годится как sandbox scorer, но ещё не как canonical product metric.
- следующий логичный шаг:
  - собрать `canonical policy` выбора mode;
  - потом перенести это в UI как mode switch + preview picker.
