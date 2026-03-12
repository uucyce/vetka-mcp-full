# Algorithmic Matte Edit Modes Results

Date: 2026-03-11

## Goal

Довести первый `algorithmic matte / roto assist` прототип до общего контракта для человека и агента:

- `add`
- `subtract`
- `protect`
- export/import одного и того же matte state

## Implemented

В `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/src/App.tsx` добавлены:

- `MatteSeedMode`:
  - `add`
  - `subtract`
  - `protect`
- `AlgorithmicMatteContract`
- `window.vetkaParallaxLab.exportAlgorithmicMatte()`
- `window.vetkaParallaxLab.importAlgorithmicMatte(...)`
- `window.vetkaParallaxLab.setMatteSeedMode(...)`
- `window.vetkaParallaxLab.appendMatteSeed(...)`
- `window.vetkaParallaxLab.removeLastMatteSeed()`

Поведение matte-режима теперь такое:

- `add` выращивает область matte вокруг seed;
- `subtract` вырезает matte обратно;
- `protect` удерживает локальные края и снижает силу subtraction;
- все seed modes влияют и на overlay, и на текущую `selection mask`.

UI также сохраняет активный `matte mode` в job state, поэтому ручной и агентный workflow используют один и тот же shared state.

В `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/src/index.css` добавлены отдельные visual states для:

- `add`
- `subtract`
- `protect`

## Why this matters

Это переводит `algorithmic matte` из демонстрации в рабочий edit layer:

- человек может быстро набросать seed edits;
- агент может экспортировать, менять и возвращать тот же matte-contract;
- следующий шаг можно строить уже на общем `algorithmic_matte` state, а не на несвязанных UI действиях.

## Current limits

- пока нет отдельного файлового экспорта `algorithmic_matte.json`;
- пока нет реального RGB contour snapping, только proxy depth edge snap;
- пока нет lasso / spline roto path;
- matte still rides on proxy depth, а не на canonical exported depth asset.

## Verification

- `npm test`
- `npm run build`
- `./scripts/photo_parallax_review.sh`

Artifacts:

- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/output/review/latest-parallax-review.png`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/output/review/latest-parallax-review.json`

## Next step

Следующий практический шаг:

1. Вынести matte-state в отдельный файловый contract `algorithmic_matte.json`.
2. Добавить `agent patch flow`: загрузка внешнего matte payload поверх текущего job state.
3. Проверить `algorithmic matte` против `brush/group` на 2-3 проблемных сценах.
4. Потом переходить к real edge snap по RGB contour.
