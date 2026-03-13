# Multiplate Routing Results

Дата: `2026-03-13`

## Что сделано

В sandbox введён первый deterministic routing rule:

- `portrait-base`
- `multi-plate`

Rule считается не по depth display, а по `plate stack` сложности.

Реализация:

- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/src/App.tsx`

## Текущая логика

Scene маршрутизируется в `multi-plate`, если выполнено хотя бы одно условие:

- есть хотя бы один `special-clean` plate;
- visible renderable plate-ов больше двух.

Иначе scene остаётся в `portrait-base`.

## Почему именно так

Это соответствует текущему product split:

- `Portrait Base` — single-subject / low-complexity сцены;
- `Multi-Plate` — сцены, где нужна осознанная plate decomposition или object-specific clean plate.

То есть правило не пытается “угадать жанр картинки”, а опирается на уже собранный scene structure.

## Куда это встроено

Routing теперь присутствует в product contracts:

- `window.vetkaParallaxLab.getState()`
- `window.vetkaParallaxLab.exportPlateLayout()`

В `plate_layout.json` появился блок:

- `routing.mode`
- `routing.visibleRenderableCount`
- `routing.specialCleanCount`
- `routing.reasons[]`

## Практический смысл

Это первый шаг, после которого можно честно различать:

- portrait-style fast path;
- multi-plate authoring path.

То есть дальнейшие automatic decisions могут строиться уже не на preview heuristics, а на явном workflow mode.

## Ограничение

Это пока initial routing rule, а не final smart router:

- он опирается на текущий `plateStack`;
- ещё не использует scene-level metrics, object count или Qwen confidence;
- не принимает решение до plate decomposition stage.

## Следующий шаг

Следующий правильный шаг по roadmap:

- расширить routing rule на plate-oriented sample set;
- затем добавить `camera-safe` validation и disocclusion risk уже для выбранного workflow mode.
