# Upscale Depth Bake-off Results

Дата фиксации: `2026-03-11`

## Что тестировалось

Сравнение:

- `native image -> depth -> coarse mask`
- `Real-ESRGAN x2 -> depth -> coarse mask`

Backends:

- `Depth Anything V2 Small`
- `Depth Pro`

Sample set:

- `cassette-closeup`
- `keyboard-hands`
- `drone-portrait`
- `hover-politsia`

Артефакты лежат в:

- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/output/upscale_depth_bakeoff`

Основной summary:

- [upscale_depth_bakeoff_summary.json](/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/output/upscale_depth_bakeoff/upscale_depth_bakeoff_summary.json)

## Что измерялось

- `mask_best_score` как наиболее product-relevant coarse-separation metric;
- `depth_edge_alignment` как proxy для локальной sharpness depth edges;
- `focus_separation` как proxy для depth separation в интересующей области.

## Главный вывод

`Real-ESRGAN x2` на текущем sample set не оправдал себя как default pre-depth stage.

Почему:

- на `Depth Anything V2 Small`:
  - `avg_mask_delta = -0.13889`
  - `mask_improved = 0/4`
  - `mask_degraded = 1/4`
- на `Depth Pro`:
  - `avg_mask_delta = -0.12129`
  - `mask_improved = 0/4`
  - `mask_degraded = 2/4`

При этом:

- `Depth Pro` получил `depth_edges_improved = 3/4`
- `Depth Anything V2 Small` получил `depth_edges_improved = 1/4`

То есть upscale иногда улучшает локальные depth edges, но это не конвертируется в лучший coarse mask.

## Где это видно сильнее всего

Негативные кейсы:

- `Depth Anything V2 Small / drone-portrait`
  - `mask_delta = -0.54058`
- `Depth Pro / keyboard-hands`
  - `mask_delta = -0.32445`
- `Depth Pro / drone-portrait`
  - `mask_delta = -0.08279`

Почти нейтральные кейсы:

- `Depth Anything V2 Small / cassette-closeup`
  - `mask_delta = +0.00259`
- `Depth Anything V2 Small / hover-politsia`
  - `mask_delta = +0.00657`
- `Depth Pro / hover-politsia`
  - edge alignment вырос, но mask score почти не изменился.

## Практический вывод

На текущей базе:

- `Real-ESRGAN x2` не должен включаться `always-on`;
- он остаётся только `optional luxury experiment`;
- decision gate должен смотреть на downstream mask quality, а не на “картинка стала резче”.

## Runtime вывод

- `Real-ESRGAN` в текущем Apple Silicon sandbox показал нестабильное поведение на `mps` для крупных кадров;
- для воспроизводимого batch-run безопаснее считать его offline-stage, а не interactive-stage;
- `Depth Pro + upscaled full-res mask search` уже находится в очень дорогом режиме.

## Что делать дальше

1. Не включать upscale в default pipeline.
2. Оставить его как manual/advanced toggle.
3. Если возвращаться к нему снова, то только после:
   - расширения sample set до `8-12` сцен;
   - появления реальных user-edited hints;
   - теста не только `x2`, но и более мягкого pre-enhancement пути.

## Источники

- `Real-ESRGAN` repo: [github.com/xinntao/Real-ESRGAN](https://github.com/xinntao/Real-ESRGAN)
- `RealESRGAN_x2plus` release weights: [github.com/xinntao/Real-ESRGAN/releases/download/v0.2.1/RealESRGAN_x2plus.pth](https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.1/RealESRGAN_x2plus.pth)
