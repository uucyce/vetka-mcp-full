# Photo-to-Parallax Architecture V1

Дата фиксации: `2026-03-10`

## 1. Product Statement

Инструмент принимает одно изображение и выпускает набор промежуточных ассетов плюс итоговый preview/final render для мягкого photo-to-parallax видео.

## 2. Scope

### В scope для MVP

- single-image pipeline;
- mild camera motion;
- foreground/background separation;
- clean plate;
- optional overscan;
- deterministic preview render;
- исследовательская песочница для автоанализа параметров сцены.
- portrait-grade `depth-first` workflow как базовый продуктовый режим.

### В scope для quality extensions

- guided mask correction через пользовательские подсказки;
- optional pre-depth upscale;
- semantic judge/refiner для сложных сцен;
- future video-consistency auxiliary для sequence mode.
- multi-plate authoring для сложных сцен.

### Out of scope для MVP

- full 3D reconstruction;
- arbitrary large camera movement;
- perfect hair matting;
- complex relighting;
- real-time generative video.

## 3. System Decomposition

### 3.1 Input layer

Вход:

- `source image`
- optional user hints:
  - focus point
  - object priority
  - motion preset
  - `mask_hint.png`
  - depth scribbles:
    - red = closer
    - blue = farther
    - green = ignore/protect
  - optional trimap seed

Выход:

- normalized workspace job directory
- image metadata
- source analysis JSON

### 3.2 Depth stage

Компоненты:

- `PreDepthEnhancer`
- `DepthBackend` interface
- `DepthAnythingV2Backend`
- `DepthProBackend`
- `DepthNormalizer`

Выход:

- `depth_16.png`
- `depth_preview.png`
- `depth_preview_bw.png`
- `depth_stats.json`

### 3.3 Subject extraction stage

Компоненты:

- `CoarseDepthMaskBuilder`
- `MaskRefiner`
- `MaskCleaner`
- `GuidedHintInterpreter`
- `HintToPromptAdapter`

Стратегия:

- coarse mask из depth через polarity-aware `seed-grow`;
- refinement через optional segmentation backend;
- optional user-hint correction через color-mask prompts и trimap seeds;
- winner selection против `coarse_passthrough`;
- postprocess морфологией и connected components.

Выход:

- `subject_mask.png`
- `subject_rgba.png`
- per-layer `PNG + alpha` exports
- `mask_debug.png`

Принятое продуктовое ограничение на `2026-03-13`:

- этот stage считается достаточным для `Portrait Base`;
- для complex scenes он считается только стартовой автоматикой;
- он не должен больше притворяться полной заменой plate decomposition.

### 3.3A Plate decomposition stage

Компоненты:

- `PlateDecomposer`
- `PlateStackBuilder`
- `PlateDepthAssigner`
- `PlateOrderResolver`
- `SpecialCleanPlateBuilder`

Задача:

- превратить одну сцену не в одну глобальную маску, а в `N` осмысленных plate-ов;
- дать каждому plate собственный `rgba`, `clean plate`, `local depth` или depth priority;
- назначить каждому plate положение по `z`;
- поддержать специальные clean plates:
  - `no people`
  - `no trees`
  - и другие object-specific background variants.

Выход:

- `plate_stack.json`
- `plate_01_rgba.png`
- `plate_01_depth.png`
- `plate_01_clean.png`
- future `plate_n_*`

### 3.4 Plate generation stage

Компоненты:

- `CleanPlateBuilder`
- `OverscanPlateBuilder`

Текущий baseline:

- `OpenCV inpaint` как fallback/baseline для `clean_plate`

Quality target:

- `LaMa`

Принятое правило после bake-off:

- `OpenCV inpaint` остаётся в `Base` path;
- `LaMa` идёт в `quality/default-quality` path;
- growth mask для inpaint не фиксируется одной константой и выбирается из candidate range.

Выход:

- `clean_plate.png`
- `overscan_plate.png`
- `plate_debug.json`

Принятое правило после overscan build:

- `overscan_plate` строится не как scaled copy of background, а как отдельный expanded asset;
- source для него: `LaMa clean_plate`;
- canvas expansion задаётся motion-driven overscan contract;
- рядом сохраняется `layout.json`, пригодный для renderer.

### 3.5 Layout stage

Компоненты:

- `ParallaxLayoutPlanner`
- `MotionPresetSelector`

Задача:

- разнести слои по `z`;
- выбрать безопасную амплитуду движения;
- рассчитать требуемый overscan;
- посчитать risk metrics.

Принятое расширение на `2026-03-13`:

- `layout.json` больше не должен мыслиться только как `foreground/background`;
- следующая версия layout должна быть `plate-aware`;
- каждому plate нужен собственный `z`, `parallax strength`, optional local damping.

Выход:

- `layout.json`

### 3.6 Render stage

Компоненты:

- `FFmpegGraphBuilder`
- `PreviewRenderer`
- `FinalRenderer`

Продуктовое правило по частоте кадров:

- default/base preview fps: `25`
- optional smoother preview fps: `30`
- optional high-frame presets:
  - `50`
  - `60`

Текущая продуктовая позиция:

- `25 fps` считается основной базой для большинства preview/export сценариев;
- `30 fps` остаётся доступным как более гладкая опция;
- `50/60 fps` нужны не по умолчанию, а для отдельных кейсов, где важно максимально мягкое движение или последующий монтаж.

Выход:

- `preview.mp4`
- `final.mp4`
- `render_report.json`

### 3.7 Assisted and luxury extensions

Auto Base path:

- `depth -> coarse mask -> conditional SAM 2 -> subject_rgba -> clean_plate -> overscan -> render`

Portrait Base path:

- `source -> global depth -> B/W depth preview -> remap -> isolate -> clean_plate -> overscan -> render`

Multi-Plate path:

- `source -> global depth -> initial isolate -> plate decomposition -> plate-local cleanup -> plate-local depth / z assignment -> camera layout -> render`

Qwen Plate Planner path:

- `source + depth_preview_bw + optional existing plate stack -> semantic decomposition plan -> plate stack proposal`

Manual Pro path:

- пользователь добавляет `mask_hint.png` или depth scribbles;
- цветовые подсказки конвертируются в prompts для `SAM 2`;
- depth и mask могут быть локально переписаны в hinted region;
- optional trimap export улучшает alpha edges.
- следующий шаг:
  - `Same Layer / Merge Group`
- `AI Suggest Overlay`
- `Apply AI Groups`
  - region-level grouping
  - ручной depth remap

AI Assist path:

- optional `Qwen2.5-VL` как semantic judge:
  - интерпретация пользовательской подсказки;
  - object ordering;
  - semantic grouping suggestions;
  - sanity check для foreground/background assignment;
- `Qwen2.5-VL` как `Plate Planner`:
  - recommendation of plate count;
  - semantic plate naming;
  - plate ordering from near to far;
  - suggestion of `special clean plates` such as `no people`, `no trees`;
- optional `Real-ESRGAN` до depth stage как `PreDepthEnhancer`;
- `V-JEPA 2` не входит в ближайший single-image plan и остаётся только future sequence/video R&D.

Ограничения:

- `Qwen2.5-VL` не считается depth backend;
- `Qwen2.5-VL` не считается mask extractor;
- `Qwen2.5-VL` не считается inpaint engine;
- `V-JEPA 2` не считается direct depth estimator или object-grouping engine;
- upscale должен быть optional, потому что он может улучшить края, но также переизобрести текстуры и усложнить mask edges;
- `AI Assist` не должен ломать deterministic `Auto Base` mode.

## 4. Canonical Asset Contract

```json
{
  "job_id": "sample_job",
  "source": {
    "path": "source.png",
    "width": 2560,
    "height": 1440,
    "hint_path": "mask_hint.png"
  },
  "depth": {
    "master_path": "depth_16.png",
    "preview_path": "depth_preview.png",
    "preview_bw_path": "depth_preview_bw.png",
    "backend": "depth-anything-v2-small",
    "pre_enhancer": "real-esrgan-x2"
  },
  "subject": {
    "mask_path": "subject_mask.png",
    "rgba_path": "subject_rgba.png",
    "trimap_path": "subject_trimap.png",
    "layer_exports": [
      { "id": "foreground", "rgba_path": "foreground_rgba.png" },
      { "id": "background", "rgba_path": "background_rgba.png" }
    ],
    "guided_inputs": {
      "hint_colors": ["red", "blue", "green"],
      "prompt_backend": "sam2"
    }
  },
  "plates": {
    "clean_path": "clean_plate.png",
    "overscan_path": "overscan_plate.png"
  },
  "plate_stack": [
    {
      "id": "plate_01",
      "label": "foreground_subject",
      "rgba_path": "plate_01_rgba.png",
      "depth_path": "plate_01_depth.png",
      "clean_path": "plate_01_clean.png",
      "z": 18,
      "role": "foreground"
    }
  ],
  "plate_plan": {
    "planner": "qwen2.5-vl",
    "path": "qwen_plate_plan.json"
  },
  "layout": {
    "layers": [
      { "id": "background", "z": -24 },
      { "id": "foreground", "z": 12 }
    ],
    "camera": {
      "motion_type": "orbit",
      "travel_x_pct": 2.4,
      "travel_y_pct": 1.1,
      "zoom": 1.05,
      "speed": 1.0,
      "duration_sec": 4.0
    }
  },
  "render": {
    "preview_path": "preview.mp4",
    "fps": 25,
    "duration_sec": 4
  },
  "quality_extensions": {
    "mode": "assisted",
    "semantic_judge": "qwen2.5-vl-7b",
    "temporal_aux": null
  }
}
```

Working rule from `2026-03-13`:

- `subject / background` contract remains valid for `Portrait Base`;
- `plate_stack` becomes the canonical extension point for complex scenes.
- `qwen_plate_plan.json` becomes the canonical semantic planning extension for complex scenes.

## 5. Interfaces

### `DepthBackend`

```python
class DepthBackend(Protocol):
    name: str
    def run(self, image_path: str, out_dir: str) -> dict: ...
```

### `MaskRefiner`

```python
class MaskRefiner(Protocol):
    name: str
    def refine(self, image_path: str, coarse_mask_path: str, out_dir: str) -> dict: ...
```

### `PlateBuilder`

```python
class PlateBuilder(Protocol):
    name: str
    def build(self, image_path: str, mask_path: str, out_dir: str, **kwargs) -> dict: ...
```

### `Renderer`

```python
class Renderer(Protocol):
    name: str
    def render(self, layout_json_path: str, out_path: str) -> dict: ...
```

## 6. Execution Modes

### Research mode

- много debug outputs;
- промежуточные PNG;
- risk scores;
- side-by-side comparison;
- удобно для песочницы.

### Production mode

- минимум артефактов;
- быстрый preview;
- только ключевые выходы.

### Assisted mode

- принимает `mask_hint.png` и scribbles;
- строит hinted prompts для `SAM 2`;
- экспортирует `trimap` и guided debug outputs.

### Luxury mode

- включает optional upscale A/B run;
- включает semantic judge/refiner;
- reserve path для future video auxiliary features.

## 7. Risk Gates

Перед render stage пайплайн должен выставлять gate flags:

- `mask_quality_low`
- `overscan_insufficient`
- `cardboard_risk_high`
- `disocclusion_risk_high`
- `motion_too_large_for_two_layers`

Если один из risk gates высокий:

- либо резать motion preset;
- либо рекомендовать `3 layers`;
- либо просить ручную правку mask/plate.

## 8. Sandbox Role

Отдельная песочница нужна не как декоративный preview, а как planning-and-debug lab.

Она должна уметь:

- работать изолированно от основного приложения;
- быстро грузить sample images;
- давать `snapshot()` и JSON state;
- считать overscan/disocclusion/cardboard risk;
- выдавать review screenshot и JSON probe;
- поддерживать `debug.*` в браузере для автономной работы.
- показывать `B/W depth preview` для ручной настройки separation.

## 8.1 UI Direction

UI стоит строить по Resolve-inspired mental model, но проще, с явным делением на:

- `Auto Base`
- `Manual Pro`
- `AI Assist`

Depth controls:

- `Near / Far`
- `Gamma`
- `Auto Contrast`
- `B/W Preview`
- `Use Upscale`

Selection controls:

- `Target Depth`
- `Range`
- `Invert`
- `Hint Overlay`

Cleanup controls:

- `Softness`
- `Expand / Shrink`
- `Filter`
- `Alpha Refine`

Guided controls:

- `Hint Mode`
- `Interpret Hints`
- `Use Semantic Judge`
- `Trimap Export`
- `Same Layer / Merge Group`
- `AI Suggest Overlay`
- `Apply AI Groups`

Algorithmic matte / roto assist:

- `Click Seed`
- `Grow Region`
- `Edge Snap`
- `Protect Edge`
- `Depth B/W Matte View`
- `RGB Matte View`
- `Transparent Color Mask Fill`

Manual Pro first-wave controls:

- `B/W Depth Preview`
- `Near / Far`
- `Gamma`
- `Invert`
- `Target Depth`
- `Range`
- `Closer Brush`
- `Farther Brush`
- `Protect Brush`
- `Stage Tool`: `brush / group`
- `Same Layer / Merge Group` через region boxes

Motion controls:

- `Motion Type`
  - `orbit`
  - `pan`
  - `dolly-in + zoom-out`
  - `dolly-out + zoom-in`
- `Speed`
- `Duration`
- `Preview`

## 9. Recommended MVP Stack

- UI sandbox: `Vite + React`
- local analysis: `Python + Pillow + NumPy`
- render: `ffmpeg`
- depth bake-off targets:
  - `Depth Anything V2 Small`
  - `Depth Pro`
- quality-first coarse path:
  - `Depth Pro`
  - `polarity-aware seed-grow`
- fallback coarse path:
  - `Depth Anything V2 Small`
  - `polarity-aware seed-grow`
- future refine/inpaint:
  - `SAM 2` как `conditional refiner`
  - `OpenCV inpaint` как baseline `clean_plate`
  - `LaMa` как quality-target `clean_plate`

## 9.1 Recommended quality-extension stack

Assisted:

- `SAM 2` для color-hint driven prompts;
- `PyMatting` или trimap-oriented alpha refine;
- `mask_hint.png` как простой пользовательский контракт.

Luxury:

- `Real-ESRGAN` как optional pre-depth enhancer;
- `Qwen2.5-VL-7B` как semantic judge/refiner на Apple Silicon;
- `V-JEPA 2` только для future video-consistency R&D.

## 10. Decision Log

- `2026-03-10`: depth bake-off собран, `Depth Anything V2 Small` и `Depth Pro` прогнаны на sample set.
- `2026-03-11`: global threshold-only coarse masks признаны недостаточными для сложных сцен.
- `2026-03-11`: canonical coarse-mask strategy обновлена до `polarity-aware seed-grow`.
- `2026-03-11`: quality-first backend выбран как `Depth Pro`, fallback/backend for comparison выбран как `Depth Anything V2 Small`.
- `2026-03-11`: следующий обязательный этап после coarse mask — `MaskRefiner`, а не дальнейший подбор глобальных threshold.
- `2026-03-11`: `SAM 2` подключён как refine backend и проверен на sample set.
- `2026-03-11`: refine обновлён до gated-режима:
  - `coarse_passthrough` остаётся обязательным кандидатом;
  - refine winner выбирается сравнением кандидатов, а не применяется безусловно.
- `2026-03-11`: `subject_rgba` собран как первый стабильный export contract.
- `2026-03-11`: `clean_plate` через `OpenCV inpaint` собран как baseline/fallback path.
- `2026-03-11`: для больших дыр подтверждена необходимость `LaMa` или другого более сильного inpaint backend.
- `2026-03-11`: `LaMa` bake-off завершён на `8` кейсах:
  - `8/8` улучшений против baseline по plate score;
  - `OpenCV inpaint` оставлен как fallback;
  - `LaMa` принят как canonical quality-target `clean_plate`.
- `2026-03-11`: overscan stage материализован в реальные артефакты:
  - `overscan_plate.png`
  - `overscan_mask.png`
  - `layout.json`
- `2026-03-11`: recommended overscan теперь переводится в реальные `pad_x/pad_y` и expanded canvas size.
- `2026-03-11`: первый `2-layer ffmpeg renderer` собран:
  - `preview.mp4`
  - `preview_poster.png`
  - `render_report.json`
- `2026-03-11`: render stage подтверждён как рабочий runtime path, но visual quality gate ещё не закрыт.
- `2026-03-11`: visual render gate собран поверх preview stage:
  - `render_review.json`
  - `render_review_sheet.png`
  - `debug_side_by_side.mp4`
  - `render_review_batch_sheet.png`
- `2026-03-11`: `2-layer` признан достаточным не для всех кейсов; нужен ранний `3-layer gate`.
- `2026-03-11`: `safer 2-layer preset` подтверждён как fallback для `caution`, но не как замена `3-layer`.
- `2026-03-11`: `three_layer_plan.json` принят как рабочий контракт между planning stage и `3-layer ffmpeg renderer`.
- `2026-03-11`: `cluster_gap` принят как дополнительный confidence signal для `3-layer` separability.
- `2026-03-11`: user-guided path принят как следующий quality multiplier:
  - `mask_hint.png`
  - color hints
  - `SAM 2` prompted refinement
- `2026-03-11`: optional upscale принят в архитектуру как controlled experiment, а не always-on stage.
- `2026-03-11`: `Qwen2.5-VL` принят только как semantic judge/refiner, не как depth backend.
- `2026-03-11`: `V-JEPA 2` вынесен из ближайшего single-image roadmap; он не нужен для программно заданного motion и остаётся только future sequence/video R&D.
- `2026-03-11`: product plan переформулирован в три режима:
  - `Auto Base`
  - `Manual Pro`
  - `AI Assist`
- `2026-03-11`: первая волна `Manual Pro UI` реализована в sandbox:
  - `B/W Depth Preview`
  - `Depth Remap`
  - `Isolate Depth`
  - `Cleanup`
  - `Mode switch`
- `2026-03-11`: первый region-level `merge group` layer добавлен в sandbox Manual Pro.
- `2026-03-11`: локальный `qwen2.5vl:3b` подключён как первый `AI Assist` semantic suggester.
- `2026-03-11`: `algorithmic matte / roto assist` признан отдельным roadmap track для Manual Pro и agent tooling.
- `2026-03-11`: `Real-ESRGAN x2 -> depth` pilot завершён:
  - default path не улучшился;
  - coarse-mask quality на текущем sample set не выросла;
  - upscale оставлен только как optional luxury experiment.

### Принятые решения

- строить отдельную песочницу, а не сразу интеграцию в основной продукт;
- разделять `clean plate` и `overscan plate`;
- поддержать self-review и browser debug как first-class capabilities;
- хранить архитектуру в терминах `assets + stages + risk gates`;
- разделить систему на `Base`, `Assisted`, `Luxury` paths.

### Открытые решения

- какой depth backend победит bake-off;
- нужен ли `SAM 2` в MVP или достаточно depth-driven coarse mask;
- достаточно ли `2 layers` для основных пользовательских кадров;
- насколько детерминированным должен быть outpaint backend;
- насколько реально помогает более мягкий pre-enhancement path по сравнению с `Real-ESRGAN x2`;
- насколько стабильно `Qwen2.5-VL` интерпретирует пользовательские color hints;
- нужен ли `V-JEPA 2` до появления sequence/video режима.
