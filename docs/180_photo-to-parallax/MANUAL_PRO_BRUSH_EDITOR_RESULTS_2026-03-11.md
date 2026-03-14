# Manual Pro Brush Editor Results

Дата: `2026-03-11`

## Что добавлено

В sandbox UI добавлен первый рабочий `hint brush editor`:

- `Closer`
- `Farther`
- `Protect`
- `Erase`

Реализация:

- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/src/App.tsx`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/src/index.css`

## Что это делает

- пользователь рисует прямо по stage;
- strokes сохраняются в состоянии sandbox;
- из strokes собираются proxy hint maps;
- proxy hints сразу влияют на:
  - depth remap preview
  - isolate selection
  - proxy midground split

Это уже не просто overlay, а первый реальный manual correction loop.

## Debug / API

`window.vetkaParallaxLab` расширен:

- `brushMode`
- `brushSize`
- `hintStrokeCount`
- `setBrushMode(mode)`
- `clearManualHints()`

## Проверка

Успешно прошли:

- `npm test`
- `npm run build`
- `./scripts/photo_parallax_review.sh`

Свежий screenshot:

- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/output/review/latest-parallax-review.png`

## Ограничения

- hints пока меняют только proxy depth logic;
- нет сохранения strokes в отдельный `manual_hints.json`;
- нет region grouping;
- нет `Same Layer / Merge Group`.

## Следующий шаг

Следующий правильный шаг:

- `Same Layer / Merge Group`
- region-level grouping поверх brush hints
- затем compare `auto vs manual grouped`
