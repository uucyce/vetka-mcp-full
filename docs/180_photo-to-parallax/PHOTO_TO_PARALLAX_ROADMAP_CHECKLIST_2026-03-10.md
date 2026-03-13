# Photo-to-Parallax Roadmap and Checklist

Дата фиксации: `2026-03-10`

## Phase 0. Research Baseline

- [x] Сформулировать pipeline как product flow, а не как isolated depth task.
- [x] Разделить `clean plate` и `overscan plate`.
- [x] Выделить главные backend-кандидаты по depth.
- [x] Спроектировать отдельную песочницу.
- [x] Добавить self-review инструменты первого уровня.
- [x] Зафиксировать, что текущий `depth-first` pipeline считается базовым portrait workflow, а не универсальным решением для всех сцен.

## Phase 1. Input and Source Analysis

- [x] Собрать sample set для исследований.
- [x] Добавить офлайн-анализатор входных изображений.
- [ ] Ввести оценку пригодности изображения для mild parallax.
- [ ] Добавить автоподбор motion preset на основе source analysis.
- [x] Зафиксировать контракт `mask_hint.png` для guided mode.

Подшаги:

- [ ] измерить edge density и contrast на 20-30 реальных кадрах;
- [ ] определить cutoffs для `safe`, `caution`, `high risk`.
- [x] зафиксировать цветовую легенду:
  - red = closer
  - blue = farther
  - green = protect/ignore

## Phase 2. Depth Bake-off

- [x] Поднять `Depth Anything V2 Small`.
- [x] Поднять `Depth Pro`.
- [x] Прогнать оба backend на sample set.
- [x] Сравнить:
  - границы;
  - стабильность foreground separation;
  - скорость;
  - удобство упаковки.
- [x] Зафиксировать quality-first baseline и fallback.

Подшаги:

- [x] сохранить master depth в 16-bit;
- [x] протестировать `p2-p98` normalization;
- [x] сравнить Otsu vs percentile threshold vs k-means.
- [x] добавить dedicated `B/W depth preview` для ручной отстройки layer separation в sandbox UI.
- [ ] добавить export depth map в `grayscale PNG` как canonical multi-export output.
- [x] проверить optional `Real-ESRGAN x2` как pre-depth enhancer.
- [ ] сравнить `native depth` vs `upscaled->depth` на 8-12 сценах.

Решение на `2026-03-11` после upscale pilot:

- `Real-ESRGAN x2` не принят как default pre-depth stage;
- локальный рост depth-edge metrics не дал роста coarse-mask quality на текущем sample set;
- upscale остаётся только в `Luxury` track и только как manual experiment.

## Phase 3. Mask Pipeline

- [x] Реализовать coarse mask из depth.
- [x] Добавить morphology cleanup.
- [x] Добавить optional mask refinement backend.
- [x] Сравнить результат на сложных контурах.

Подшаги:

- [x] выбрать схему `dilate/erode/close/open`;
- [x] ввести mask quality score;
- [x] добавить экспорт `mask_debug.png`.
- [x] добавить `focus/context prior` в scoring.
- [x] добавить `seed-grow` стратегию.
- [x] добавить explicit edge-quality metric.
- [x] проверить `SAM 2` как refine stage.
- [x] ввести `coarse_passthrough` как обязательный refine fallback.
- [x] ввести prompt families для `SAM 2`.
- [x] добавить guided prompts из `mask_hint.png`.
- [x] добавить trimap export из guided masks.
- [x] сравнить `base SAM 2` vs `hinted SAM 2`.

Решение на `2026-03-11`:

- quality-first coarse backend: `Depth Pro`;
- fallback/backend for comparison: `Depth Anything V2 Small`;
- canonical coarse strategy: `polarity-aware seed-grow`.
- canonical refine strategy: `conditional SAM 2 refine` c winner selection против `coarse_passthrough`.

Решение на `2026-03-11` после refine bake-off:

- `Depth Anything V2 Small + conditional SAM 2` выигрывает на `3/4` samples;
- `Depth Pro + conditional SAM 2` выигрывает на `1/4` samples;
- refine нельзя считать always-on;
- лучший pipeline теперь условный, а не линейный:
  - `coarse -> refine candidates -> compare with passthrough -> choose winner`.

## Phase 4. Plate Generation

- [x] Реализовать baseline `clean plate`.
- [x] Реализовать `overscan plate`.
- [ ] Ввести отдельные quality metrics для каждого.

Подшаги:

- [x] собрать `subject_rgba` export contract;
- [x] собрать baseline `clean_plate` через OpenCV inpaint bake-off;
- [x] добавить multi-export каждого слоя в `PNG + alpha`;
- [x] поднять `LaMa` как quality-target backend для `clean_plate`;
- [x] проверить LaMa на больших масках;
- [ ] решить, нужен ли второй backend для outpaint;
- [x] научиться считать минимальный required overscan по motion preset.
- [ ] проверить, улучшают ли guided masks качество clean-plate вырезания до `LaMa`.

Решение на `2026-03-11` после subject/plate baseline:

- `subject_rgba` уже считается стабильным артефактом;
- `clean_plate` через OpenCV inpaint принят как fallback/baseline;
- `drone-portrait` и крупные foreground slabs подтверждают, что quality path должен идти в `LaMa`, а не в дальнейший тюнинг OpenCV.

Решение на `2026-03-11` после `LaMa` bake-off:

- `LaMa` выиграл у `OpenCV inpaint` на `8/8` текущих кейсах;
- `OpenCV inpaint` остаётся fallback/backend для base mode;
- `LaMa` принят как canonical quality-target для `clean_plate`;
- hole-mask dilation нельзя фиксировать одной константой, candidate search `11/21/31` пока сохраняется.

Решение на `2026-03-11` после overscan build:

- `overscan_plate` собран как отдельный stage поверх `LaMa clean_plate`;
- `layout.json` теперь считается рабочим контрактом для render step;
- recommended overscan переводится в реальные `pad_x/pad_y`, а не остаётся только UI-эвристикой;
- на текущем sample set не появилось оснований добавлять второй seeding backend поверх `LaMa`.

## Phase 4A. Assisted Controls

- [ ] Ввести `mask_hint.png` в canonical asset contract.
- [x] Ввести `mask_hint.png` в canonical asset contract.
- [x] Добавить guided mode в sandbox UI.
- [x] Конвертировать color hints в prompts для `SAM 2`.
- [x] Добавить compare mode:
  - base result
  - hinted result
  - coarse passthrough
- [x] Экспортировать `subject_trimap.png`.

Подшаги:

- [x] определить минимальный набор hint actions:
  - closer
  - farther
  - protect
- [x] добавить overlay preview для hints;
- [x] сохранить hinted debug sheet;
- [x] ввести отдельный `guided_gain_score`.
- [ ] добавить paint/editor слой для реального рисования hints в UI.

## Phase 4B. Manual Pro

- [x] Добавить `B/W Depth Preview` в UI.
- [x] Добавить ручной `Depth Remap`:
  - `Near`
  - `Far`
  - `Gamma`
  - `Invert`
- [x] Подать в `B/W Depth Preview` реальный baked depth там, где он уже есть.
- [x] Добавить `Layer Selection` controls:
  - `Target Depth`
  - `Range`
  - `Foreground Bias`
  - `Background Bias`
- [ ] Добавить hint-editor:
  - [x] `Closer Brush`
  - [x] `Farther Brush`
  - [x] `Protect Brush`
  - [x] `Erase Hint`
- [x] Добавить `Same Layer / Merge Group` как главный контроль против semantic mis-split.

Подшаги:

- [x] сделать region-level grouping поверх текущего pixel split;
- [x] ввести сохранение `manual_hints.json`;
- [x] проверить `Closer / Farther` как depth-paint поверх реального baked depth;
- [ ] сохранить compare `auto vs manual`.
- [x] сохранить compare `manual vs ai`.
- [ ] сохранить compare `raw depth render vs edited depth render`.

Решение на `2026-03-13` после AE reference workflow review:

- текущий `Manual Pro + depth-first` path замораживается как `Portrait Base`;
- этот path считается успешной базой для:
  - portrait
  - simple object
  - mild two-layer parallax;
- для complex scene он больше не считается конечной целью, а только стартовой автоматикой перед plate decomposition.

## Phase 5. Layout and Motion

- [x] Зафиксировать canonical `layout.json`.
- [x] Реализовать `2-layer` renderer.
- [x] Добавить `3-layer` режим.
- [x] Ввести risk gate против cardboard effect.
- [x] Добавить motion type presets:
  - `orbit`
  - `pan`
  - `dolly-in + zoom-out`
  - `dolly-out + zoom-in`
- [x] Добавить параметры `speed` и `duration`.
- [x] Зафиксировать продуктовый fps baseline:
  - `25 fps` как default
  - `30 fps` как optional smoother preset
  - `50/60 fps` как high-frame presets

Подшаги:

- [ ] подобрать safe presets для portrait/wide/street scenes;
  - baseline reduced-motion fallback для `caution` и `needs_3_layer` уже собран;
- [ ] пересобрать motion presets под новый fps policy:
  - default `25 fps`
  - optional `30 fps`
  - optional `50/60 fps`
- [ ] ввести ограничители по travel amplitude;
- [ ] ввести auto-warning при недостаточном overscan.
- [x] добавить preview `depth B/W mode` в UI для настройки separation.
- [ ] задокументировать Resolve-inspired simplified controls для motion и depth.

Решение на `2026-03-13`:

- `25 fps output / 50 fps internal / tmix 3` принят как текущий canonical preview render policy;
- motion baseline больше не считается blocker для portrait path;
- основной новый риск смещён с motion на `scene decomposition`.

## Phase 5A. Portrait Base Freeze

- [x] Зафиксировать текущий portrait workflow как product baseline.
- [ ] Собрать `Portrait Base` preset pack:
  - portrait
  - close-up object
  - mild tabletop
- [ ] Свести UI для этого режима к короткому пути:
  - import
  - depth
  - isolate
  - camera
  - export
- [ ] Зафиксировать набор canonical outputs для portrait mode.

Portrait Base canonical path:

- `source -> global depth -> B/W depth preview -> remap -> isolate -> clean plate -> overscan -> render`

## Phase 5B. Multi-Plate Authoring

- [x] Ввести новую сущность `plate` как базовый building block для complex scenes.
- [ ] Спроектировать `plate decomposition` stage.
- [x] Ввести `Qwen Plate Planner` как semantic planning layer поверх global depth.
- [x] Ввести `plate-local depth` или `depth priority` для каждого plate.
- [x] Ввести `plate z-position` как отдельный layout contract.
- [ ] Разделить `global depth` и `plate-local depth`.
- [ ] Добавить `special cleanup plates`:
  - `no people`
  - `no trees`
  - другие object-specific clean plates
- [ ] Научиться экспортировать `N` plate-ов, а не только `foreground/background`.
- [x] Добавить `plate stack` в UI.
- [x] Ввести `plate order` и `plate visibility` как first-class controls.
- [x] Перевести live preview на `per-plate RGBA composition`.

Подшаги:

- [ ] определить minimal `plate` contract:
  - `id`
  - `label`
  - `rgba_path`
  - `clean_path`
  - `depth_path`
  - `z`
  - `role`
- [ ] определить initial plate families:
  - foreground subject
  - secondary subject
  - environment mid
  - background far
  - special clean plate
- [x] определить minimal `qwen_plate_plan.json` contract:
  - `recommended_plate_count`
  - `plates[]`
  - `special_clean_plates[]`
  - `notes[]`
- [x] заставить `Qwen` возвращать JSON, а не prose.
- [x] подключить `source + depth_preview_bw.png` как минимальный input pair для planner.
- [x] определить sanitizing gate для planner output.
- [x] определить, когда scene должна маршрутизироваться в `Multi-Plate` mode вместо `Portrait Base`.
- [ ] собрать plate-oriented sample set из сложных сцен.
- [x] ввести compare `2-layer base vs multi-plate`.
- [x] ввести compare `manual multiplate vs qwen multiplate`.

Решение на `2026-03-13`:

- после разбора AE reference workflow подтверждено, что сложные сцены делаются не через одну глобальную маску, а через осознанную декомпозицию на plate-ы;
- следующий главный продуктовый шаг это не “ещё лучше одна depth map”, а `multi-plate authoring`.
- `Qwen2.5-VL` подтверждён как правильный кандидат не для маскирования, а для semantic plate planning.

## Phase 5C. Plate-Specific Camera Layout

- [x] Научиться считать motion не только от `foreground/background`, а от `plate stack`.
- [x] Ввести plate-specific amplitude damping.
- [x] Ввести plate-specific parallax strength.
- [ ] Ввести plate-specific blur / atmosphere / degradation controls.
- [x] Ввести per-plate overscan risk.

Подшаги:

- [x] сделать `layout.json` plate-aware;
- [x] заменить прямоугольные proxy plate preview на mask-based plate composition;
- [x] перевести stage preview c `mask-only` на `background_rgba + plate_rgba[]`;
- [x] добавить `camera-safe` validation для plate stack;
- [x] считать disocclusion risk по plate transitions, а не только по whole-frame mask.

## Phase 6. Render and Export

- [x] Собрать preview render через `ffmpeg`.
- [ ] Собрать final render presets.
- [x] Добавить side-by-side debug render.
- [ ] Добавить multi-export пакета артефактов.
  - layer-level exports и compare renders уже собраны в sandbox;

Подшаги:

- [ ] проверить alpha handling;
- [ ] проверить mp4/h264 baseline preset;
- [x] добавить JSON render report.
- [ ] экспортировать:
  - `depth_16.png`
  - `depth_preview_bw.png`
  - `foreground_rgba.png`
  - `midground_rgba.png`
  - `background_far_rgba.png`
  - `subject_rgba.png`
  - `subject_trimap.png`
  - `foreground_rgba.png`
  - `background_rgba.png`
  - future mid-layers as separate `PNG + alpha`.

## Phase 6A. Multi-Plate Export Pack

- [x] Собрать первый export pack для complex scenes.
- [x] Добавить first-pass plate-wise `PNG + alpha`.
- [x] Добавить sandbox export contract для plate-wise `PNG + alpha`.
- [x] Добавить sandbox export contract для plate-wise local depth exports.
- [x] Добавить first-pass export `clean plate` для каждого special plate.
- [x] Добавить export `plate_stack.json`.

Подшаги:

- [x] `plate_01_rgba.png`
- [x] `plate_01_depth.png`
- [x] `plate_01_clean.png`
- [x] `plate_stack.json`

## Phase 6B. Multi-Plate Final Render

- [x] Связать export pack с final render path.
- [x] Собрать первый `preview_multiplate.mp4`.
- [x] Проверить `multiplate` render минимум на `3` complex scenes.

Подшаги:

- [x] читать render не из sandbox state, а из exported plate assets;
- [x] использовать `plate_layout.json` как camera/layout input;
- [x] сохранить `preview_multiplate_report.json`;
- [x] собрать compare `2-layer base vs multi-plate final render` для первых complex scenes.
- [x] расширить multiplate render на `special-clean` aware comp decisions.
- [ ] `camera_layout.json`
- [ ] `preview_multiplate.mp4`

## Phase 6B. Semantic and Luxury Stack

### P6A.1

- локальный `qwen2.5vl:3b` подключён как первый `AI Assist` semantic suggester;
- введён `ai_assist_suggestions/*.json` contract;
- sandbox UI умеет показывать overlay и применять accepted AI groups в `Merge Groups`;
- geometry suggestions проходят через sanitizing gate и fallback, а не применяются напрямую.


- [x] Прототипировать `Qwen2.5-VL` как semantic judge/refiner.
- [x] Прототипировать `Qwen2.5-VL` как `Plate Planner`.
- [ ] Проверить стабильность интерпретации color hints.
- [x] Ввести JSON contract для semantic guidance.
- [x] Ввести JSON contract для `qwen_plate_plan.json`.
- [x] Ввести hidden apply path из `qwen_plate_plan.json` в `plateStack`.
- [ ] Прототипировать `V-JEPA 2` только как future temporal auxiliary.

Подшаги:

- [ ] определить, какие ошибки реально может ловить `Qwen2.5-VL`:
  - перепутанный foreground/background
  - object ordering
  - multiple salient objects
- [x] определить, какие scene planning задачи реально может закрывать `Qwen2.5-VL`:
  - plate count
  - plate naming
  - near/far ordering
  - special clean plate recommendation
- [ ] не пускать semantic judge напрямую в final mask без compare gate;
- [x] не пускать `Qwen Plate Planner` напрямую в final mask / final render без deterministic validation;
- [x] ввести `proposal quality gate` для `Qwen plate plan`:
  - keep current stack
  - enrich current stack
  - replace current stack
- [x] прогнать `gate-aware qwen flow`:
  - `manual -> gate -> export -> render -> compare`
  - подтверждено на `3/3` complex scenes
- [x] отложить `V-JEPA 2` до появления sequence/video режима;
- [ ] зафиксировать это как luxury track, а не MVP dependency.

Решение на `2026-03-11` после просмотра preview:

- `V-JEPA 2` не нужен для программно заданного motion;
- ближайший `AI Assist` path должен строиться вокруг semantic grouping, а не temporal smoothing;
- первым кандидатом остаётся `Qwen2.5-VL`, а не `V-JEPA 2`.
- `Qwen2.5-VL` должен развиваться прежде всего как `scene decomposition planner`, а не как попытка заменить segmentation/inpaint.
- raw `Qwen Plate Planner` не должен идти в export/render;
- в final path должен использоваться только `gated_plate_stack`.

## Phase 6B. Algorithmic Matte and Roto Assist

- [x] Спроектировать `algorithmic matte` режим как общий инструмент для человека и агента.
- [x] Добавить `click-to-grow` / `roto-style` region picking вместо только brush/box interaction.
- [x] Ввести два preview-режима маски:
  - `depth map B/W`
  - `RGB / color matte`
- [x] Добавить прозрачную color-mask заливку краёв по клику в духе Photoshop / After Effects roto workflow.
- [x] Поддержать agent-driven matte edits через тот же контракт.
- [x] Экспортировать отдельный `algorithmic_matte.json` contract.
- [x] Собрать compare-runner `brush/group` vs `algorithmic matte` на preset-сценах.

Подшаги:

- [ ] определить единый asset contract для matte-state:
  - [x] `manual_hints.json`
  - [x] `group_boxes.json`
  - `algorithmic_matte.json`
- [x] добавить repeatable compare outputs:
  - `brush_group_selection.png`
  - `algorithmic_matte_selection.png`
  - `compare_summary.json`
- [x] определить grow/cut heuristics:
  - click seed
  - region grow
  - edge snap
  - protect edge
- [ ] решить, как matte view синхронизируется между `B/W depth` и `RGB matte`.
- [ ] не смешивать этот режим с clean plate inpaint; это отдельный mask/matte stage.

## Phase 6C. Internal Edge Cleanup

- [x] Добавить internal `RGB contour snap + feather cleanup` поверх layered mask.
- [x] Добавить sample-level compare sheets до и после contour snap.
- [x] Добавить internal gate `layered-base` vs `contour-snapped`.
- [ ] Проверить gate на расширенном sample set 8-12 сцен.
  - текущий coverage уже расширен до `6` сцен, включая `drone-portrait`, `punk-rooftop`, `truck-driver`.

Подшаги:

- [x] экспортировать `selection_mask_before_snap.png`;
- [x] экспортировать `selection_mask_contour_snapped.png`;
- [x] экспортировать `selection_mask_internal_final.png`;
- [x] не добавлять новый пользовательский control ради contour snap;
- [ ] научиться предсказывать случаи, где contour snap не нужен или вреден.

Решение на `2026-03-12` после object-selection review:

- `RGB contour snap` не должен считаться главным quality signal;
- object cohesion важнее локального edge delta;
- следующий gate должен выбирать mask variant по `whole object as one layer`, а не только по contour cleanup.

## Phase 6D. Object Selection Quality

- [x] Добавить internal scorer для вопроса `выделен ли целый объект как единый слой`.
- [x] Сравнить `before-ai` vs `after-ai` vs `internal-final`.
- [x] Зафиксировать, что edge cleanup не равен object quality.
- [x] Добавить internal `objectness gate` как первичный выборщик mask variant.
- [ ] Подчинить `AI blend` и `contour snap` objectness-scoring, а не наоборот.

Подшаги:

- [x] описать sample-level target boxes и background leak zones;
- [x] считать:
  - target coverage
  - target hit ratio
  - fragmentation
  - spill
  - coverage balance
- [x] собрать compare sheets для variant review;
- [ ] расширить scorer до 8-12 сцен;
  - текущий scorer уже прогнан на `6` сценах;
- [ ] выбрать canonical order:
- [x] выбрать canonical order:
  - objectness gate
  - edge cleanup
  - clean plate

## Product Modes

UX guardrail:

- [x] Зафиксировать, что новые research controls не должны автоматически попадать в итоговый продуктовый UI.
- [x] Держать advanced compare/gate/debug как internal tooling, пока не доказана их продуктовая необходимость.

- [ ] Зафиксировать canonical policy для:
  - `Auto Base`
  - `Manual Pro`
  - `AI Assist`
- [x] Перенести mode switch в sandbox UI.
- [ ] Научить UI сохранять выбранный mode в job state.

Подшаги:

- [ ] `Auto Base`:
  - deterministic preview and exports
- [ ] `Manual Pro`:
  - [x] hints
  - [x] remap
  - [x] merge groups
  - [x] save/load manual state
- [ ] `AI Assist`:
  - [x] semantic suggestions
  - [x] accept/reject/blend compare flow
  - [x] promote accepted AI suggestions into saved matte/group state
  - [x] add quality gate for `AI blend` acceptance
  - [x] keep this gate internal unless it proves necessary for end-user control
- [ ] Internal postprocess:
  - [x] contour snap review
  - [x] contour snap gate
  - [ ] auto-enable heuristic on larger scene set
 - [ ] Object selection:
   - [x] object selection scorer
   - [ ] objectness-first gate

## Phase 7. Sandbox Hardening

- [x] Создать отдельный sandbox project.
- [x] Добавить browser debug API.
- [x] Добавить Playwright review probe.
- [x] Добавить wrapper review script.
- [ ] Добавить regression snapshots на 3-5 sample scenes.
- [x] Добавить batch review report.

## MVP Exit Criteria

- [x] Quality-first backend и fallback выбраны по результатам bake-off.
- [ ] На sample set строятся `subject_mask`, `clean_plate`, `overscan_plate`.
- [x] На sample set строятся `subject_mask`, `clean_plate`, `overscan_plate`.
- [ ] На mild camera motion финальный preview выглядит устойчиво.
  Runtime renderer и review gate уже есть, но visual acceptance закрыта только частично:
  - `two_layer_ok`: `2`
  - `caution`: `3`
  - `needs_3_layer`: `3`
- [ ] Sandbox выдаёт repeatable screenshot и JSON snapshot.
- [ ] Есть documented risk gates и fallback behavior.

## Quality Extension Exit Criteria

- [x] Guided mode даёт measurable gain хотя бы на части сложных сцен.
- [ ] Optional upscale не ухудшает majority case.
- [ ] Semantic judge не ломает deterministic base mode.
- [ ] Luxury stack может быть отключён целиком без потери base workflow.

## Anti-goals

- [ ] не превращать MVP в full compositor;
- [ ] не зависеть от одного fixed threshold;
- [ ] не смешивать clean plate и overscan в один неясный шаг;
- [ ] не обещать large-camera-move quality на двух слоях.
