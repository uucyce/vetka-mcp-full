# Plate Stack Data Model Results

Дата фиксации: `2026-03-13`

## Что сделано

В sandbox введена новая сущность сцены:

- `plate`

Каждый plate теперь мыслится не как временная маска, а как самостоятельный элемент композиции со следующими полями:

- `id`
- `label`
- `role`
- `source`
- `x / y / width / height`
- `z`
- `depthPriority`
- `visible`
- optional `cleanVariant`

Также введён контейнер:

- `PlateStackContract`

```json
{
  "sampleId": "hover-politsia",
  "plates": [
    {
      "id": "plate_01",
      "label": "vehicle",
      "role": "foreground-subject",
      "source": "auto",
      "x": 0.28,
      "y": 0.21,
      "width": 0.50,
      "height": 0.54,
      "z": 26,
      "depthPriority": 0.86,
      "visible": true
    }
  ]
}
```

## Что поддерживается в sandbox

- default sample-specific `plateStack`
- сохранение `plateStack` в `ManualJobState`
- `exportPlateStack()` через `window.vetkaParallaxLab`
- `importPlateStack(payload)` через `window.vetkaParallaxLab`
- debug overlay на сцене для plate boundaries
- debug list / info card для текущего plate stack

## Почему это важно

Это первый шаг к переходу от:

- `global mask thinking`

к:

- `multi-plate scene thinking`

Теперь сложная сцена может развиваться как stack из самостоятельных plate-ов, а не как одна пытающаяся всё объяснить depth-маска.

## Текущее ограничение

Пока decomposition ещё не автоматизирован:

- plate-ы задаются preset-ами на sample level;
- plate stack пока не участвует в renderer как primary layout input;
- это data-model foundation, а не финальный multi-plate workflow.

## Следующий шаг

- сделать `plate stack` primary input для layout planner;
- ввести `plate order / visibility / role editing`;
- начать `plate decomposition` для сложных сцен;
- перевести renderer с `foreground/background` мышления на `plate-aware` layout.
