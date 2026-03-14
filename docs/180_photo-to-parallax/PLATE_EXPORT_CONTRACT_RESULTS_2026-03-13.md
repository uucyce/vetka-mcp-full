# Plate Export Contract Results

Дата: `2026-03-13`

## Что сделано

В sandbox добавлен первый настоящий multi-plate export contract:

- `window.vetkaParallaxLab.exportPlateAssets()`

Этот contract возвращает:

- `sourceUrl`
- `globalDepthUrl`
- `backgroundRgbaUrl`
- `backgroundMaskUrl`
- `plateStack`
- `layout`
- `plates[]`

Для каждого plate:

- `rgbaUrl`
- `maskUrl`
- `depthUrl`
- `coverage`
- `z`
- `depthPriority`
- `role`
- `cleanVariant`

## Почему это важно

Раньше multi-plate progress был в основном про:

- preview
- layout
- motion

Теперь у нас появляется явный экспортный слой, где complex scene уже может быть прочитана не только как preview, но и как набор артефактов:

- plate-wise RGBA
- plate-wise mask
- plate-wise B/W depth

Это ближе к реальному compositor workflow и убирает зависимость только от composite-preview восприятия.

## Ограничения

- это пока browser export contract, а не файловый exporter на диск;
- `rgbaUrl` и `depthUrl` пока синтезируются внутри sandbox из:
  - source image
  - plate alpha
  - global depth
- `special clean plate` ещё не имеет отдельного final export path;
- `clean plate` per plate пока не входит в contract.

## Вывод

Шаг `preview-only multi-plate` -> `exportable multi-plate contract` закрыт.

Следующий шаг по roadmap:

- сделать из этого contract реальный file/export flow:
  - `plate_01_rgba.png`
  - `plate_01_depth.png`
  - `plate_stack.json`
