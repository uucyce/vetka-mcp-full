# Mask Refine Results

Дата фиксации: `2026-03-11`

Артефакты запуска:

- summary JSON: `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/output/mask_refine_bakeoff/mask_refine_bakeoff_summary.json`
- outputs root: `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/output/mask_refine_bakeoff`

Использованный refine backend:

- `SAM 2`
- checkpoint: `facebook/sam2-hiera-large`
- device: `mps`

## 1. Что было сделано

Поверх coarse mask bake-off был добавлен отдельный refinement runner.

Он использует:

- coarse mask bbox;
- positive points внутри эродированной coarse mask;
- negative points в кольце вокруг маски;
- несколько prompt families:
  - `sam_box_multi`
  - `sam_box_pos`
  - `sam_box_posneg`
  - `sam_box_posneg_refine`
- fallback-кандидат `coarse_passthrough`.

Каждый refined candidate проходит:

- thresholding logits;
- morphology cleanup;
- connected-component filtering;
- quality scoring по:
  - `sam_score`;
  - `coarse_iou`;
  - `coarse_precision / coarse_recall`;
  - `edge_score`;
  - `area_drift`;
  - spill outside context.

## 2. Главный вывод

`SAM 2` полезен, но не как always-on refinement.

Он улучшает часть сцен, где coarse mask уже близка к нужной форме, но не должен принудительно применяться ко всем кадрам.

Правильная модель пайплайна:

`coarse mask -> conditional refine candidate generation -> compare against passthrough -> choose winner`

То есть refine должен быть `gated`, а не обязательным.

## 3. Итог по sample set

### `Depth Anything V2 Small` coarse -> `SAM 2`

- `cassette-closeup`: выиграл `coarse_passthrough`
- `drone-portrait`: выиграл `sam_box_multi`
- `hover-politsia`: выиграл `sam_box_posneg_refine`
- `keyboard-hands`: выиграл `sam_box_pos`

Итог: refinement выиграл `3/4` кейсов.

### `Depth Pro` coarse -> `SAM 2`

- `cassette-closeup`: выиграл `coarse_passthrough`
- `drone-portrait`: выиграл `sam_box_posneg_refine`
- `hover-politsia`: выиграл `coarse_passthrough`
- `keyboard-hands`: выиграл `coarse_passthrough`

Итог: refinement выиграл `1/4` кейсов.

## 4. Практическая интерпретация

### Где refine действительно помогает

- `drone-portrait`
  - и на `Depth Anything V2 Small`, и на `Depth Pro`;
  - refinement подтягивает silhouette и снижает лишний spill по краям.

- `hover-politsia`
  - помогает только на ветке `Depth Anything V2 Small`;
  - улучшение умеренное, но воспроизводимое.

- `keyboard-hands`
  - на ветке `Depth Anything V2 Small` refine делает foreground более узким;
  - это может быть полезно для clean plate, если цель именно отделить руки от части клавиатуры.

### Где refine сейчас не нужен

- `cassette-closeup`
  - и на `Depth Anything V2 Small`, и на `Depth Pro` coarse mask уже лучше или надёжнее refine-кандидатов.

- `Depth Pro + hover-politsia`
  - refinement в текущем prompt setup не превосходит coarse baseline.

- `Depth Pro + keyboard-hands`
  - refinement слишком агрессивно режет foreground и проигрывает coarse по общему качеству для plate pipeline.

## 5. Что это значит для выбора backend

Если смотреть только на coarse stage:

- quality-first baseline всё ещё `Depth Pro`;
- fallback всё ещё `Depth Anything V2 Small`.

Но после добавления refine stage возникает важное уточнение:

- связка `Depth Anything V2 Small + conditional SAM 2 refine` стала сильнее на части сложных сцен;
- связка `Depth Pro + coarse passthrough` остаётся более надёжной по стабильности.

То есть выбор теперь не бинарный.

Рабочий продуктовый вывод:

1. `Depth Pro` лучше использовать как quality-first coarse backend.
2. `SAM 2` надо запускать как optional refinement layer.
3. Refine winner должен выбираться по score против `coarse_passthrough`.
4. На некоторых сценах лучшая стратегия:
   - `Depth Pro coarse`
   - без refine.
5. На некоторых сценах лучшая стратегия:
   - `Depth Anything V2 Small coarse`
   - затем `SAM 2`.

## 6. Обновлённая архитектурная формула

Текущая recommended mask stack:

`depth -> polarity-aware seed-grow coarse mask -> conditional SAM 2 refinement -> winner selection -> subject mask`

Это и есть текущий best-known path для sandbox.

## 7. Что дальше

Следующий этап можно начинать без дальнейшего тюнинга threshold heuristics:

- собрать `subject_rgba` exporter;
- перейти к `clean_plate`;
- отдельно логировать:
  - holes after cutout;
  - removed area;
  - plate difficulty score.

## 8. Practical Decision

На `2026-03-11` refinement track считается рабочим и достаточно исследованным для перехода к plate generation.

Что принято:

- `SAM 2` остаётся в архитектуре как `conditional refiner`;
- fallback `coarse_passthrough` обязателен;
- refine нельзя применять без сравнения с coarse baseline;
- следующий engineering focus смещается в `clean plate` и `subject_rgba` contract.
