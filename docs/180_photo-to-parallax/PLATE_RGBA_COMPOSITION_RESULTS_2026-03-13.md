# Plate RGBA Composition Results

Дата: `2026-03-13`

## Что сделано

Sandbox preview переведён с `mask-only plate composition` на `per-plate RGBA composition`.

На предыдущем шаге stage уже использовал:

- `backgroundMaskUrl`
- `plateMaskUrls[]`

Но source image при этом всё ещё оставался общим для background и всех plate plane-ов, а различие шло только через alpha masks.

Теперь `buildPlateCompositeMaps(...)` дополнительно собирает:

- `backgroundRgbaUrl`
- `plateRgbaUrls[]`

из `source image + alpha masks`.

## Как теперь работает preview

### Background

Background plane теперь предпочитает:

- `backgroundRgbaUrl`

и использует `backgroundMaskUrl` только как fallback.

### Plate planes

Каждый renderable plate теперь предпочитает:

- `plateRgbaUrls[plate.id]`

и использует `plateMaskUrls[plate.id] + source image` только как fallback.

## Что это меняет

Это важный технический переход:

- preview больше не является просто `одна картинка + несколько CSS masks`;
- каждый plate уже живёт как самостоятельный RGBA asset в браузерном stage;
- следующая ступень теперь естественная:
  - plate-wise export
  - plate-local cleanup
  - plate-aware render/export outside preview

## Ограничения

- текущие RGBA plate-ы пока синтезированы из:
  - исходного изображения
  - plate alpha mask
- это ещё не:
  - plate-local clean plate
  - независимый plate source file
  - AE-level authored plate

То есть `RGBA composition` уже настоящая по формату, но ещё не финальная по качеству и происхождению.

## Вывод

Шаг `mask-only preview -> per-plate RGBA preview` закрыт.

Следующий шаг по roadmap:

- вывести эти plate-ы в реальный export contract и перейти к `plate-wise PNG + alpha`.
