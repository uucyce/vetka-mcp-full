# Depth Bake-off Results

Дата фиксации: `2026-03-10`

Артефакты запуска:

- summary JSON: `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/output/depth_bakeoff/bakeoff_summary.json`
- outputs root: `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/output/depth_bakeoff`

## 1. Backends

- `depth-anything-v2-small`
  - model: `depth-anything/Depth-Anything-V2-Small-hf`
  - type: relative depth
- `depth-pro`
  - model: `apple/DepthPro-hf`
  - type: metric depth

## 2. Environment Notes

- для bake-off был поднят отдельный `python3.11` venv:
  - `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/.depth-venv`
- `Depth Pro` потребовал `torchvision`;
- Hugging Face download path для `Depth Pro` был нестабилен через xet, поэтому рабочий режим запуска:
  - `HF_HUB_DISABLE_XET=1`

## 3. Runtime Summary

| Backend | Avg ms / image | Min ms | Max ms | Comment |
| --- | ---: | ---: | ---: | --- |
| `Depth Anything V2 Small` | `218.71` | `163.35` | `312.70` | Очень быстрый локальный baseline |
| `Depth Pro` | `5349.62` | `4978.76` | `5586.54` | Примерно в `24.46x` медленнее |

## 4. Output Contract

Для каждого sample/backend теперь сохраняются:

- `depth_master_16.png`
- `depth_preview_minmax.png`
- `depth_preview.png`
  - это `p2-p98` preview
- `report.json`

## 5. First Qualitative Findings

### `Depth Anything V2 Small`

Плюсы:

- быстро отрабатывает на всём sample set;
- preview usable почти сразу;
- даёт достаточно читаемое разделение foreground/background для planning stage.

Минусы:

- как relative depth не даёт естественной метрической шкалы;
- внутренние поверхности местами сглажены сильнее, чем хочется для жёсткого matte.

### `Depth Pro`

Плюсы:

- сильная object silhouette на portrait и vehicle-like forms;
- выглядит многообещающе для boundary-sensitive use cases.

Минусы:

- по умолчанию min-max preview почти бесполезен на широком диапазоне значений;
- без `p2-p98` нормализации metric depth визуально слишком тёмный;
- заметно тяжелее по runtime.

## 6. Concrete Product Implications

1. `p2-p98 normalization` больше не гипотеза, а обязательный этап preview/debug depth.
2. `Depth Anything V2 Small` уже годится как fast default backend для MVP.
3. `Depth Pro` пока выглядит как quality-oriented optional backend, а не как default runtime path.
4. Для следующего шага можно строить coarse mask хотя бы на `Depth Anything V2 Small`, не дожидаясь полного выбора финального winner.

## 7. Preliminary Recommendation

Пока лучший pragmatic split такой:

- default depth backend: `Depth Anything V2 Small`
- high-quality comparison path: `Depth Pro`
- canonical debug preview: `p2-p98`
- master depth storage: `16-bit`

## 8. Next Action

Следующий этап после этого bake-off:

- запустить `coarse mask from depth`
- сравнить `Otsu`, `percentile threshold`, `k-means`
- сохранить `mask_debug.png`
