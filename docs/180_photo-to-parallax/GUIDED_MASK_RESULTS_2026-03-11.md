# Guided Mask Results

Дата фиксации: `2026-03-11`

## Что было сделано

- добавлен контракт `mask_hint.png` для guided mode;
- цветовая легенда зафиксирована как:
  - red = closer
  - blue = farther
  - green = protect
- `photo_parallax_mask_refine_bakeoff.py` расширен hinted prompts для `SAM 2`;
- добавлены:
  - `hint_overlay.png`
  - `guided_refine_debug_sheet.png`
  - hint-aware scoring fields
  - `subject_trimap.png`
  - `foreground_rgba.png`
  - `background_rgba.png`
- для автономной проверки собран synthetic hint generator:
  - `photo_parallax_prepare_sample_hints.py`

## Что проверено

- полный guided refine bake-off на `8` кейсах:
  - `2 backends`
  - `4 samples`
  - `facebook/sam2-hiera-large`
  - `mps`
- полный subject/plate bake-off после guided refine.

## Ключевой результат

Guided path полезен, но не `always-on`.

Итог по winner selection:

- `sam_hint_posneg_refine`: `2/8`
- `sam_box_posneg_refine`: `3/8`
- `sam_box_multi`: `1/8`
- `sam_box_pos`: `1/8`
- `coarse_passthrough`: `1/8`

Hinted winners:

- `depth-anything-v2-small / cassette-closeup`
- `depth-pro / cassette-closeup`

## Вывод

- guided prompts реально работают как quality extension;
- они не вытесняют base path;
- synthetic hints уже дали measurable gain на части кейсов;
- следующий важный шаг не в усложнении scorer, а в проверке на реальных пользовательских hints.

## Ограничения текущего результата

- hints пока synthetic, а не реальные пользовательские scribbles;
- current color contract простой и годится для research, но UI-слой ещё не добавлен;
- `green = protect` пока работает как positive-support region, а не как полноценный editing language.

## Следующий шаг

1. Вынести guided controls в sandbox UI.
2. Добавить real user-authored `mask_hint.png` samples.
3. Проверить gain на реальных сложных сценах.
4. После этого делать `Real-ESRGAN x2 -> depth` bake-off.
