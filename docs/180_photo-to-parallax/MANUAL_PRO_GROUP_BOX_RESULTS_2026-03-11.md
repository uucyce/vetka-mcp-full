# Manual Pro Group Box Results

Date: 2026-03-11

## Goal

Добавить в sandbox первый region-level контроль против semantic mis-split: не только кисти по depth, но и прямоугольные `merge groups`, которые форсируют целую область в один слой.

## Implemented

- В `photo_parallax_playground/src/App.tsx` добавлен `stageTool`:
  - `brush`
  - `group`
- Добавлен `groupMode`:
  - `foreground-group`
  - `midground-group`
  - `erase-group`
- На stage появился drag-box editor.
- `groupBoxes` теперь реально вмешиваются в proxy split:
  - `foreground-group` форсирует высокий `selection` и подавляет `midground`
  - `midground-group` наоборот отжимает область из foreground в midground
- В sandbox debug API добавлены:
  - `setStageTool(mode)`
  - `setGroupMode(mode)`
  - `clearGroupBoxes()`
- В UI добавлены panel controls и coverage stats для групп.
- В stage добавлены overlay и draft-box preview.

## Why this matters

Это первый осознанный шаг от pixel-depth tuning к region-level grouping. Для кейсов вроде `cassette-closeup` теперь можно не только локально докрашивать depth кистями, но и грубо зафиксировать, что разнесённые части объекта должны жить в одном foreground/midground plane.

## Current limits

- Пока это только прямоугольники, без polygon/lasso.
- Пока это всё ещё proxy depth field, не реальный depth asset pipeline.
- Пока нет сохранения `manual_hints.json` / `group_boxes.json`.
- Пока нет semantic suggestion layer для автопредложения групп.

## Verification

- `npm test`
- `npm run build`
- `./scripts/photo_parallax_review.sh`

Review artifacts:

- `photo_parallax_playground/output/review/latest-parallax-review.png`
- `photo_parallax_playground/output/review/latest-parallax-review.json`

## Next step

Следующий шаг после этого слоя не в ещё одной ручной геометрии, а в двух вещах:

1. Сохранение manual/group state как job contract.
2. `AI Assist` suggestions для вероятных group candidates поверх Manual Pro.
