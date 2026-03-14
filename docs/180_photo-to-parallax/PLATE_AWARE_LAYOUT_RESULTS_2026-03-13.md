# Plate-Aware Layout Results

Дата фиксации: `2026-03-13`

## Что сделано

В sandbox добавлен первый `plate-aware layout` contract.

Новый API:

- `window.vetkaParallaxLab.exportPlateLayout()`

Он возвращает layout JSON, собранный из:

- `plateStack`
- `motion`
- `snapshot`
- `source metadata`

## Что теперь содержит layout

- source width / height / file name
- camera block
- metrics block
- ordered list of plate layers

Для каждого plate:

- `id`
- `label`
- `role`
- `source`
- `order`
- `visible`
- `z`
- `depthPriority`
- `parallaxStrength`
- `motionDamping`
- `cleanVariant`
- `box`

## Что изменилось в логике

`computeSnapshot` всё ещё работает по прежней формуле, но входной `layoutMotion` теперь derived from plate stack:

- effective `layerCount`
- effective `layerGapPx`

За счёт этого sandbox уже перестаёт мыслить сцену только как `foreground/background`.

## Что это ещё не делает

- renderer пока не читает `exportPlateLayout()` напрямую;
- real multi-plate image compositing ещё не построен;
- это contract bridge, а не финальный plate renderer.

## Зачем это важно

Следующий renderer можно будет строить уже не поверх старого `2-layer` контракта, а поверх plate-aware layout, не меняя data model ещё раз.
