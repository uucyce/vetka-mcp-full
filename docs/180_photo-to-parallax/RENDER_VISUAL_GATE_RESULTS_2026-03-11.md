# Render Visual Gate Results

Дата прогона: `2026-03-11`

## 1. Что добавлено

Поверх первого `ffmpeg` renderer собран отдельный review layer.

Новые инструменты:

- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/scripts/photo_parallax_render_review.py`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/scripts/photo_parallax_render_review.sh`

Новые артефакты:

- `render_review.json`
- `render_review_sheet.png`
- `debug_side_by_side.mp4`
- `render_review_batch_sheet.png`

Summary:

- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/output/render_review/render_review_summary.json`

Outputs root:

- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/output/render_review`

## 2. Что считается в review gate

Gate пока не является human approval и не претендует на эстетическую истину.

Это heuristic review поверх уже собранных render artifacts:

- foreground coverage;
- border touch ratio маски;
- motion magnitude;
- zoom pressure;
- foreground edge margin по траектории preview;
- simple classification:
  - `two_layer_ok`
  - `caution`
  - `needs_3_layer`

То есть выводы ниже являются inference из артефактов и geometry, а не ручной финальной оценкой.

## 3. Агрегат

Общий итог:

- `two_layer_ok`: `2`
- `caution`: `3`
- `needs_3_layer`: `3`

### `Depth Anything V2 Small`

- entries: `4`
- `two_layer_ok`: `2`
- `caution`: `1`
- `needs_3_layer`: `1`
- avg review score: `2.25`
- avg edge margin: `126.02525px`

### `Depth Pro`

- entries: `4`
- `two_layer_ok`: `0`
- `caution`: `2`
- `needs_3_layer`: `2`
- avg review score: `4.5`
- avg edge margin: `-44.39075px`

## 4. По кейсам

### `two_layer_ok`

- `depth-anything-v2-small / cassette-closeup`
- `depth-anything-v2-small / hover-politsia`

### `caution`

- `depth-anything-v2-small / keyboard-hands`
- `depth-pro / cassette-closeup`
- `depth-pro / hover-politsia`

### `needs_3_layer`

- `depth-anything-v2-small / drone-portrait`
- `depth-pro / drone-portrait`
- `depth-pro / keyboard-hands`

## 5. Что это значит

Главный вывод:

- шаг “renderer exists” закрыт;
- шаг “2-layer preview is broadly safe” не закрыт.

Что видно уже сейчас:

- `Depth Anything V2 Small` выглядит более дружелюбным к текущему `2-layer` render path;
- `Depth Pro` часто даёт более агрессивный foreground extent, из-за чего edge-pressure и `needs_3_layer` срабатывают чаще;
- portrait-heavy и foreground-heavy кейсы остаются основным источником будущего `3-layer` перехода.

## 6. Что именно ломает 2-layer режим

Повторяющиеся причины review flags:

- large foreground coverage;
- foreground edge pressure;
- mask touches frame border;
- zoom pressure на `dolly-out + zoom-in`;
- planar stress для крупных foreground объектов.

Практически это означает:

- если foreground занимает слишком большую часть кадра, простой разнос `FG/BG` уже даёт cardboard risk;
- если bbox foreground упирается в края при motion, даже хороший plate не спасает от неестественного движения.

## 7. Принятое решение

На текущем этапе:

- `2-layer` остаётся нормальным baseline для мягких кейсов;
- нужен ранний `3-layer gate`, а не попытка насильно дотянуть все сцены одним preset;
- этот gate уже можно использовать как operational decision rule.

Текущее правило:

- `two_layer_ok` -> оставаться на текущем preview renderer;
- `caution` -> снижать motion preset или вручную смотреть review sheet;
- `needs_3_layer` -> не считать `2-layer` приемлемым quality path.

## 8. Что дальше

Следующий логичный этап:

1. ввести `3-layer planner`;
2. либо автоматически снижать motion на `caution` кейсах, либо переключать их в safer preset;
3. после этого расширять debug render и final export presets.
