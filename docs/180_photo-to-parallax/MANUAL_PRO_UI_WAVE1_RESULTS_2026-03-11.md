# Manual Pro UI Wave 1 Results

Дата: `2026-03-11`

## Что реализовано

Sandbox UI получил первую рабочую волну `Manual Pro` controls в:

- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/src/App.tsx`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/src/index.css`

Добавлены:

- `Preview Mode`
  - `composite`
  - `depth`
  - `selection`
- `Mode`
  - `auto`
  - `safe`
  - `3-layer`
- `Invert Depth`
- `Near Limit`
- `Far Limit`
- `Gamma`
- `Target Depth`
- `Range`
- `Foreground Bias`
- `Background Bias`
- `Softness`
- `Expand / Shrink`
- `Post-Filter`
- `Blur`

## Как это работает сейчас

- UI использует `proxy depth field`, а не production depth map.
- foreground split теперь строится не из одной fixed ellipse-маски, а из remapped proxy depth + isolate band.
- `depth preview` показывает `B/W` карту.
- `selection preview` показывает isolate overlay.
- `3-layer mode` показывает proxy midground plane поверх background и foreground.

## Debug / API

`window.vetkaParallaxLab` расширен:

- `manual` возвращается в `getState()`
- `setPreviewMode(mode)`
- `setRenderMode(mode)`

## Проверка

Успешно прошли:

- `npm test`
- `npm run build`
- `./scripts/photo_parallax_review.sh`

Свежие review artifacts:

- screenshot:
  - `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/output/review/latest-parallax-review.png`
- snapshot:
  - `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/output/review/latest-parallax-review.json`

## Ограничения

- это пока `proxy depth UI`, не настоящий depth-backed correction UI;
- нет ручного рисования hints;
- нет `Same Layer / Merge Group`;
- mode switch пока меняет sandbox behaviour, но не product job policy.

## Следующий шаг

Следующий правильный шаг:

- добавить `Closer / Farther / Protect` brush editor;
- потом добавить `Same Layer / Merge Group`;
- после этого связывать `Manual Pro` с реальными artifacts, а не только с proxy preview.
