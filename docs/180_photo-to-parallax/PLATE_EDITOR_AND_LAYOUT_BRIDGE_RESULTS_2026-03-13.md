# Plate Editor And Layout Bridge Results

Дата фиксации: `2026-03-13`

## Что сделано

В sandbox добавлен первый рабочий `plate editor`:

- `move up / down`
- `z+ / z-`
- `hide / show`

Редактор работает поверх `plateStack` и доступен в debug layer.

## Что изменилось в модели

`plateStack` теперь не только хранится, но и влияет на layout-derived snapshot:

- `visibleRenderablePlates`
- `plateZSpan`
- `layoutMotion.layerCount`
- `layoutMotion.layerGapPx`

То есть snapshot уже не считает сцену только как абстрактный `foreground/background`, а начинает учитывать реальный stack видимых plate-ов.

## Что изменилось практически

Даже без переписывания renderer `plate-aware` bridge уже дал эффект:

- `cardboard risk` в review стал ниже на complex scene, потому что effective layer count теперь берётся из `plateStack`;
- `plateStack` стал editable, а не только экспортируемым JSON contract.

## Чего ещё нет

- renderer пока не рисует каждый plate как отдельный реальный слой;
- `layout.json` ещё не собирается целиком из `plateStack`;
- это bridge layer, а не финальный multi-plate render engine.

## Следующий шаг

- сделать `layout.json` plate-aware;
- добавить явный `plate order / z / visibility` control surface в sandbox вне debug-only карточки;
- перевести renderer на `plateStack` как основной layout input.
