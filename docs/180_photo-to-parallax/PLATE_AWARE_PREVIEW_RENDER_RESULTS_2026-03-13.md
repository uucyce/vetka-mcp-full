# Plate-Aware Preview Render Results

Дата фиксации: `2026-03-13`

## Что сделано

Live preview в sandbox переведён с прежней `foreground/background` схемы на `plateStack + exportPlateLayout()`.

Теперь stage preview:

- рендерит background plate как base canvas;
- рендерит каждый visible renderable plate отдельно;
- учитывает:
  - `order`
  - `z`
  - `parallaxStrength`
  - `motionDamping`

## Что это означает

Это первый настоящий `plate-based render path` в sandbox.

Preview больше не опирается только на:

- global foreground mask
- global midground mask

А начинает мыслить сцену как stack plate-ов.

## Ограничение текущего шага

Пока plate-ы в preview ещё rectangular/proxy:

- renderer клипует source image по plate boxes;
- plate boundaries ещё не используют real per-plate RGBA masks;
- результат полезен как bridge и layout preview, но ещё не как финальный quality render.

## Почему шаг всё равно правильный

Следующий renderer теперь будет дорабатываться уже в правильной модели:

- `plate stack`
- `plate-aware layout`
- `plate-specific transforms`

А не на старом двухслойном допущении.
