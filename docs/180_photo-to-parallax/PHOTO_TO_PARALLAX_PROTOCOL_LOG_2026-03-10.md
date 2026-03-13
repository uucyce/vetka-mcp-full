# Photo-to-Parallax Protocol Log

Дата старта: `2026-03-10`

## Выполненные шаги

### P0.1

- создана папка документации `docs/180_photo-to-parallax`;
- зафиксирован product framing для `photo-to-parallax`.

### P0.2

- исследование переразложено по этапам:
  - depth;
  - mask;
  - clean plate;
  - overscan;
  - layout;
  - render.

### P0.3

- выделены depth-кандидаты для bake-off:
  - `Depth Anything V2 Small`
  - `Depth Pro`
- `MiDaS` оставлен как baseline, но не как приоритетный future stack.

### P0.4

- принято решение не интегрировать в основной продукт немедленно;
- создан отдельный sandbox track.

### P0.5

- выбран локальный sample set из пользовательской директории:
  - крупный объект в руках;
  - руки + ретро-клавиатура;
  - широкая уличная сцена с летающим автомобилем;
  - квадратный портрет с выраженным foreground.

### P0.6

- добавлены инструменты self-analysis:
  - browser `debug.*`;
  - review screenshot probe;
  - JSON snapshot;
  - offline asset analyzer.

### P0.7

- собран `sample_analysis_2026-03-10.json`;
- получены первые readiness scores для test images;
- подтверждено, что sample set теперь различается по ожидаемой сложности, а не выглядит одинаково "лёгким".

## Следующие подшаги для протоколирования

### P1. Depth bake-off

- [x] подключить локальный inference runner для `Depth Anything V2 Small`;
- [x] подключить локальный inference runner для `Depth Pro`;
- [x] сохранить side-by-side outputs.

### P1.1

- поднят отдельный `python3.11` venv для depth research;
- добавлены bootstrap и bake-off runner scripts;
- зафиксирован рабочий install path для `Depth Pro`, включая `torchvision`.

### P1.2

- оба backend успешно прогнаны на sample set;
- depth outputs лежат в `photo_parallax_playground/output/depth_bakeoff`;
- runtime difference зафиксирован: `Depth Pro` примерно в `24x` медленнее `Depth Anything V2 Small`.

### P1.3

- подтверждено, что `p2-p98` preview обязателен для metric-like outputs `Depth Pro`;
- min-max preview сохранён как debug reference, но не как основной preview режим.

### P2. Mask track

- [x] провести серию экспериментов по adaptive threshold;
- [x] протоколировать лучшую схему postprocess.

### P2.1

- собран отдельный `mask bake-off` runner;
- добавлены и сравнены схемы:
  - `Otsu`;
  - global `percentile`;
  - `k-means`;
  - `focus-percentile`;
  - `seed-grow`.

### P2.2

- подтверждено, что threshold-only подход недостаточен для wide scenes и tabletop-like depth planes;
- добавлены `focus/context priors`, polarity-aware scoring и penalties за spill за пределы context box.

### P2.3

- текущая canonical coarse-mask strategy зафиксирована как:
  - `depth -> polarity prior -> focus seed -> support grow -> cleanup -> score`;
- `Depth Pro` принят как quality-first coarse-mask baseline;
- `Depth Anything V2 Small` оставлен как fallback/backend для сравнения.

### P2.4

- принято решение не тратить следующий цикл на дальнейший ручной подбор глобальных threshold;
- следующий логичный этап перенесён в `mask refinement`, затем в `clean plate`.

### P3. Plate track

- [ ] измерить реальные дыры после удаления foreground;
- [ ] проверить, хватает ли одного inpaint backend для clean + overscan.

### P2.5

- требуется новый подэтап `P2.R`:
  - coarse mask refinement через `SAM 2` или другой backend;
  - экспорт `subject_rgba`;
  - edge quality scoring.

### P2.R1

- добавлен `SAM 2` bootstrap для отдельной research venv;
- собран отдельный `mask refine bake-off` runner;
- проверен рабочий запуск `facebook/sam2-hiera-large` на `mps`.

### P2.R2

- реализованы prompt families для refinement:
  - `sam_box_multi`;
  - `sam_box_pos`;
  - `sam_box_posneg`;
  - `sam_box_posneg_refine`;
- добавлен обязательный fallback-кандидат `coarse_passthrough`.

### P2.R3

- добавлен explicit edge-quality metric на базе boundary gradient;
- подтверждено, что refine нельзя применять как always-on шаг;
- winner теперь выбирается сравнением refine-кандидатов против coarse baseline.

### P2.R4

- refinement bake-off завершён на sample set;
- `Depth Anything V2 Small + conditional SAM 2` выиграл `3/4` кейсов;
- `Depth Pro + conditional SAM 2` выиграл `1/4` кейсов;
- итоговая стратегия обновлена до:
  - `coarse -> refine candidates -> compare with passthrough -> choose winner`.

### P2.R5

- refinement track признан достаточно исследованным для перехода к plate generation;
- следующий обязательный шаг перенесён в:
  - `subject_rgba`;
  - `clean plate`.

### P3.1

- в roadmap добавлены новые product requirements:
  - `B/W depth preview` для ручной отстройки separation;
  - multi-export depth map и layer PNG + alpha;
  - motion presets:
    - `orbit`;
    - `pan`;
    - `dolly-in + zoom-out`;
    - `dolly-out + zoom-in`;
  - параметры `speed` и `duration`.

### P3.2

- Resolve-inspired UI mental model уточнена как:
  - depth controls;
  - selection controls;
  - cleanup controls;
  - motion controls;
- принято решение упрощать её, а не копировать Resolve 1:1.

### P3.3

- добавлен отдельный `subject/plate` bake-off runner;
- поднят baseline backend через `OpenCV inpaint`;
- собраны артефакты:
  - `subject_rgba`;
  - `subject_preview`;
  - `clean_plate`;
  - `hole_mask`;
  - `hole_overlay`.

### P3.4

- подтверждено, что `subject_rgba` уже можно считать стабильным контрактом;
- `clean_plate` через `Telea / Navier-Stokes` работает как fallback, но не как quality target.

### P3.5

- на `hover-politsia` baseline plate выглядит приемлемо;
- на `cassette-closeup` baseline полезен как rough fallback;
- на `drone-portrait` и крупных foreground slabs baseline недостаточен;
- следующий quality jump перенесён в `LaMa`.

### P3.6

- предложен новый quality framing:
  - `Base`
  - `Assisted`
  - `Luxury`
- принято решение не смешивать эти режимы в один неявный pipeline.

### P3.7

- `mask_hint.png` и цветовые scribbles приняты как следующий guided-control контракт;
- цветовая легенда зафиксирована как:
  - red = closer;
  - blue = farther;
  - green = protect/ignore.

### P3.8

- optional `Real-ESRGAN` принят как кандидат на pre-depth enhancement;
- зафиксировано, что upscale должен идти только через controlled A/B test, а не как always-on этап.

### P3.9

- `Qwen2.5-VL` принят только как semantic judge/refiner;
- зафиксировано, что он не считается depth backend и не должен напрямую заменять mask pipeline.

### P3.10

- `V-JEPA 2` принят как future luxury/video-consistency auxiliary;
- зафиксировано, что он не нужен в core single-image MVP и откладывается до sequence mode.

### P3.11

- реализован synthetic `mask_hint.png` generator для sandbox sample set;
- hints сохраняются в `photo_parallax_playground/public/sample_hints`;
- подтверждён рабочий цветовой контракт:
  - red = closer;
  - blue = farther;
  - green = protect.

### P3.12

- поднят отдельный `LaMa` bootstrap и bake-off runner;
- в sandbox добавлен локальный checkpoint `big-lama.pt`;
- `LaMa` подключён как отдельный plate backend без замены baseline path.

### P3.13

- `LaMa` bake-off завершён на `8` кейсах;
- итоговый счёт против `OpenCV inpaint`: `8/8` улучшений;
- зафиксированы средние runtime:
  - `Depth Anything V2 Small`: `~2.01s`
  - `Depth Pro`: `~1.80s`
- `OpenCV inpaint` оставлен как fallback/base path;
- `LaMa` принят как canonical quality-target для `clean_plate`;
- следующий этап перенесён в:
  - `overscan plate`;
  - guided-mask impact before `LaMa`;
  - первый render preview.

### P3.14

- собран отдельный `overscan` bake-off runner поверх `LaMa clean_plate`;
- введены реальные overscan outputs:
  - `overscan_plate`
  - `overscan_mask`
  - `overscan_seeded`
  - `layout.json`
- recommended overscan из source-analysis переведён в реальные `pad_x / pad_y`;
- текущий overscan path закреплён как:
  - `LaMa clean_plate -> expanded canvas -> LaMa overscan_plate`

### P3.15

- overscan generation прогнана на `8` кейсах;
- `layout.json` признан рабочим контрактом для render stage;
- `reflect` и `edge` seeding не дали измеримого расхождения на текущем sample set;
- следующий обязательный этап перенесён в:
  - `ffmpeg preview renderer`.

### P4.1

- собран первый `2-layer` renderer через `ffmpeg`;
- renderer читает:
  - `subject_rgba`
  - `overscan_plate`
  - `layout.json`
- введены новые outputs:
  - `preview.mp4`
  - `preview_poster.png`
  - `render_report.json`

### P4.2

- preview renderer прогнан на `8` кейсах;
- подтверждён стабильный runtime:
  - `Depth Anything V2 Small`: `~2.31s`
  - `Depth Pro`: `~2.43s`
- подтверждены probe параметры:
  - `4.0s`
  - `24 fps`
  - `96 frames`
- visual quality gate оставлен отдельным следующим шагом.

### P4.3

- добавлен automated render review layer;
- на каждый кейс теперь сохраняются:
  - `render_review_sheet`
  - `debug_side_by_side`
  - `render_review.json`
- собран общий `render_review_batch_sheet`.

### P4.4

- visual review gate прогнан на `8` кейсах;
- aggregate status:
  - `two_layer_ok`: `2`
  - `caution`: `3`
  - `needs_3_layer`: `3`
- подтверждено, что `2-layer` нельзя считать универсальным quality path;
- следующий обязательный шаг перенесён в:
  - `3-layer planner`
  - или safer preset reduction для `caution` сцен.

- `mask refine bake-off` расширен guided prompts из `mask_hint.png`;
- добавлены hinted candidate families:
  - `sam_hint_posneg`;
  - `sam_hint_posneg_refine`;
- добавлены новые debug outputs:
  - `hint_overlay.png`;
  - `guided_refine_debug_sheet.png`.

### P3.13

- completed compare run:
  - `base SAM 2`
  - `hinted SAM 2`
  - `coarse_passthrough`
- guided winners получены на `2/8` synthetic-hint кейсах;
- зафиксировано, что guided mode полезен, но не может считаться always-on.

### P3.14

- `subject/plate` bake-off обновлён до расширенного export contract;
- подтверждён экспорт:
  - `subject_trimap.png`;
  - `foreground_rgba.png`;
  - `background_rgba.png`;
- selected mask family теперь доезжает в plate stage без ручной подмены.

### P3.15

- sandbox UI обновлён до guided overlay mode;
- `mask_hint.png` теперь виден в лаборатории как assisted-contract preview;
- debug API расширен флагом `guidedHintsVisible`;
- `npm test`, `npm run build` и Playwright review probe прошли после UI-изменений.

### P3.16

- поднят `Real-ESRGAN` bootstrap и отдельный upscale-depth bake-off runner;
- добавлен checkpoint path для `RealESRGAN_x2plus`;
- зафиксирован compatibility shim для `torchvision.transforms.functional_tensor`.

### P3.17

- проведён pilot compare:
  - `native -> depth -> mask`
  - `Real-ESRGAN x2 -> depth -> mask`
- pilot прогнан на `4` sample scenes и `2` depth backend.

### P3.18

- на текущем sample set upscale не дал роста coarse-mask quality;
- `Depth Anything V2 Small`:
  - `avg_mask_delta = -0.13889`
  - `mask_improved = 0/4`
- `Depth Pro`:
  - `avg_mask_delta = -0.12129`
  - `mask_improved = 0/4`
- принято решение оставить upscale только в `Luxury` track и не включать его в default path.

### P3.19

- observed runtime issue:
  - `Real-ESRGAN` на `mps` в sandbox ведёт себя нестабильно на крупных кадрах;
  - `Depth Pro + upscaled full-res mask search` подтверждён как очень дорогой batch path.

### P4.1

- проверен `safer 2-layer preset` для flagged render cases;
- для `caution` кейсов safe variant не превратил их в `two_layer_ok`, но улучшил edge pressure;
- для `needs_3_layer` кейсов safe variant не снял необходимость перехода в `3-layer`.

### P4.2

- собран `3-layer planner` поверх:
  - `depth_master_16.png`
  - `subject_rgba.png`
  - `clean_plate.png`
- экспортирован новый контракт:
  - `foreground_rgba.png`
  - `midground_rgba.png`
  - `background_far_rgba.png`
  - `three_layer_plan.json`

### P4.3

- первый `3-layer ffmpeg renderer` собран и прогнан на `6/6` flagged кейсах;
- добавлены compare-артефакты:
  - `preview_3layer.mp4`
  - `compare_2layer_vs_3layer.mp4`
  - `render_report_3layer.json`

### P4.4

- собран `mode routing review` поверх:
  - original render review
  - safer preview summary
  - three-layer plan summary
  - three-layer render summary
- получен первый sandbox routing rule:
  - `two_layer`: `2`
  - `three_layer`: `5`
  - `three_layer_low_confidence`: `1`
- следующий обязательный шаг после этого:
  - отдельный quality scorer именно для `2-layer vs 3-layer`
  - переход от sandbox routing rule к canonical product policy

### P4.5

- собран `mode compare review` как side-by-side просмотрочный слой;
- на каждый кейс теперь есть:
  - `mode_compare_sheet.png`
  - `mode_compare_grid.mp4`
  - `mode_compare_review.json`
- добавлен sandbox `expected_gain_score` для сравнения `2-layer` и `3-layer`:
  - `high`: `5`
  - `medium`: `1`
  - `low`: `2`

### P4.6

- в sandbox UI реализована первая волна `Manual Pro`;
- добавлены реальные control groups:
  - `Preview Mode`
  - `Mode`
  - `Depth Remap`
  - `Isolate Depth`
  - `Cleanup`
- `B/W depth preview` и `selection preview` теперь доступны прямо в stage;
- `window.vetkaParallaxLab` расширен manual-state API.

### P4.7

- в sandbox UI добавлен первый рабочий `hint brush editor`;
- поддержаны brush modes:
  - `closer`
  - `farther`
  - `protect`
  - `erase`
- manual hints уже влияют на proxy depth isolate logic, а не только рисуются как overlay.

### P4. Render track

- [ ] зафиксировать первый canonical ffmpeg graph;
- [ ] сохранить preview samples.

## Правило обновления

Если появляются новые подшаги, они добавляются сюда с новым идентификатором `P*.*` до начала реализации, а после завершения переносятся в раздел выполненных шагов.


### P4.8

- в sandbox UI добавлен первый `merge group` editor поверх stage;
- введены `stageTool` и `groupMode`:
  - `brush` / `group`
  - `foreground-group` / `midground-group` / `erase-group`
- `groupBoxes` подключены к proxy depth isolate logic как region-level override;
- review/build/test прогнаны после добавления group layer;
- следующий шаг после этого: сохранить manual/group state как job contract и начать `AI Assist` suggestions для semantic grouping.


### P6A.1

- локальный `qwen2.5vl:3b` подключён к photo parallax sandbox через отдельный runner;
- введён новый public/output contract: `ai_assist_suggestions/*.json`;
- добавлен `AI Assist` panel в sandbox UI с overlay/apply flow;
- semantic ответы признаны полезными, но box geometry ещё требует sanitizing gate и fallback;
- ближайший следующий шаг: `accept / reject / blend` compare flow между manual groups и AI suggestions.


### P6A.2

- sandbox UI расширен до первого `AI compare` flow:
  - `ai only`
  - `blend`
  - `restore manual`
- следующий roadmap-трек зафиксирован как `algorithmic matte / roto assist`:
  - click-to-grow region picking
  - edge-aware matte expansion
  - dual preview: `depth B/W` и `RGB matte`
- этот matte-режим должен быть общим инструментом и для человека, и для агента.


### P6B.1

- в sandbox добавлен первый `algorithmic matte / roto assist` прототип;
- поддержан новый `stageTool = matte`;
- matte строится от click-seed по proxy depth similarity + spatial grow radius;
- добавлены `RGB` и `depth` matte views;
- matte overlay уже подмешивается в текущую selection mask.


### P6B.2

- `algorithmic matte` расширен до edit modes:
  - `add`
  - `subtract`
  - `protect`
- введён общий `AlgorithmicMatteContract`;
- browser API теперь поддерживает:
  - `exportAlgorithmicMatte()`
  - `importAlgorithmicMatte(...)`
- browser API расширен agent-edit методами:
  - `setMatteSeedMode(...)`
  - `appendMatteSeed(...)`
  - `removeLastMatteSeed()`
- активный `matte mode` сохраняется в job state;
- визуальные состояния seed markers разведены по режимам;
- следующий шаг после этого:
  - отдельный файловый export `algorithmic_matte.json`
  - agent patch flow поверх shared matte contract.


### P6B.3

- добавлен отдельный contract runner для `algorithmic_matte.json`;
- Playwright теперь сохраняет sample-level bundle:
  - `algorithmic_matte.json`
  - `algorithmic_matte_job_state.json`
  - `algorithmic_matte_state.json`
  - `algorithmic_matte_snapshot.json`
  - `algorithmic_matte_selection.png`
- добавлен repeatable compare-runner:
  - `brush/group` vs `algorithmic matte`
  - preset scenes:
    - `cassette-closeup`
    - `keyboard-hands`
    - `hover-politsia`
- `window.vetkaParallaxLab.getState()` расширен proxy metrics для compare JSON;
- текущий вывод:
  - `algorithmic matte` уже рабочий локальный shape editor;
  - `brush/group` остаётся более сильным coarse semantic lock;
  - следующий шаг должен объединять их в layered workflow, а не выбирать один вместо другого.


### P7A.1

- sandbox возвращён к `depth-first` траектории;
- `App.tsx` теперь подключает baked depth raster из `public/depth_bakeoff/depth-pro/<sample>/depth_preview.png`;
- `buildProxyMaps(...)` использует реальный depth, если ассет доступен;
- review probe расширен:
  - `PARALLAX_LAB_PREVIEW_MODE=depth`
  - `PARALLAX_LAB_MANUAL_HINTS_PATH=...`
  - ожидание `usingRealDepth=true` для sample, где baked depth уже положен в `public/`;
- browser debug-state расширен полями:
  - `previewMode`
  - `usingRealDepth`
- собраны первые честные `raw / edited` depth screenshots на baked depth:
  - `drone-portrait`
  - `cassette-closeup`
- добавлены первые `depth-paint presets` как проверка режима:
  - `white = closer`
  - `black = farther`
- текущий вывод:
  - настоящий `B/W depth preview` уже работает;
  - `Closer / Farther` уже меняют сам depth-remap, а не только overlay;
  - следующий обязательный шаг: связать edited depth с новым preview render и сравнить `raw depth render` против `edited depth render`.


### P7A.2

- собран третий контрольный кейс `keyboard-hands` для `depth-first` трека;
- добавлен preset:
  - `/photo_parallax_playground/e2e/depth_paint_presets/keyboard-hands.depth-paint.json`
- сохранены compare-артефакты:
  - `keyboard-hands-depth-compare.png`
  - `keyboard-hands-composite-compare.png`
- добавлен repeatable wrapper:
  - `/scripts/photo_parallax_depth_paint_review.sh`
- wrapper делает 4 последовательных захвата:
  - `raw depth`
  - `edited depth`
  - `raw composite`
  - `edited composite`
- в wrapper добавлен retry по `usingRealDepth`, чтобы не ловить ранний fallback на proxy-depth;
- текущий вывод:
  - `drone-portrait` теперь стабильно проходит как real-depth case;
  - `keyboard-hands` уже показывает не просто “маска стала больше”, а более честную картину:
    depth-paint реально меняет карту, но preset ещё требует ручной доводки под tabletop composition.


### P7A.3

- зафиксировано продуктовое правило по частоте кадров:
  - `25 fps` — основной baseline
  - `30 fps` — optional smoother preset
  - `50/60 fps` — отдельные high-frame presets
- это решение внесено в architecture и roadmap до следующего цикла motion-tuning;
- ближайший motion research должен учитывать уже не абстрактный fps, а именно этот product policy.


### P6B.4

- добавлены отдельные browser contracts:
  - `exportManualHints()` / `importManualHints(...)`
  - `exportGroupBoxes()` / `importGroupBoxes(...)`
- собран отдельный `manual contracts` runner;
- `manual_hints.json` и `group_boxes.json` теперь экспортируются как sample-level artifacts;
- собран первый layered workflow runner:
  - manual hints
  - group lock
  - algorithmic matte
  - `AI blend`
- layered bundle сохранён на preset-сценах:
  - `cassette-closeup`
  - `keyboard-hands`
  - `hover-politsia`
- текущий вывод:
  - layered flow уже жизнеспособен как research workflow;
  - `AI blend` нельзя считать always-positive шагом;
  - дальше нужен явный quality gate `accept / reject / keep-manual`.


### P6B.5

- layered workflow probe расширен до `before AI` / `after AI` screenshots;
- введён первый internal `AI blend gate`:
  - `accept`
  - `reject`
  - `keep-manual`
- gate пока работает как research heuristic по `selectionCoverageDelta`;
- собраны sample-level compare sheets и batch sheet;
- текущая сводка:
  - `accept = 2`
  - `reject = 1`
  - `keep-manual = 0`
- принято отдельное UX-правило:
  - новые compare/gate/debug механики остаются internal tooling и не попадают автоматически в конечный UI.


### P6C.1

- `window.vetkaParallaxLab.exportProxyAssets()` расширен до repeatable raw asset export;
- layered workflow теперь сохраняет:
  - `selection_mask_before_ai.png`
  - `selection_mask_after_ai.png`
  - `selection_overlay_before_ai.png`
  - `selection_overlay_after_ai.png`
  - `depth_before_ai.png`
  - `depth_after_ai.png`
- это зафиксировало входной контракт для postprocess стадий без добавления новых UI-панелей.


### P6C.2

- собран первый internal `RGB contour snap + feather cleanup` review runner;
- review stage пишет:
  - `selection_mask_before_snap.png`
  - `selection_mask_contour_snapped.png`
  - `selection_overlay_before_snap.png`
  - `selection_overlay_contour_snapped.png`
  - `contour_snap_compare_sheet.png`
  - `contour_snap_report.json`
- текущая сводка на preset-сценах:
  - `improved = 3`
  - `neutral = 0`
  - `regressed = 0`
  - `avg boundary score delta = +0.01676`


### P6C.3

- добавлен internal gate между `layered-base` и `contour-snapped`;
- gate принимает contour cleanup только при:
  - `decision = improved`
  - `boundaryScoreDelta >= 0.008`
  - `abs(alphaMeanDelta) <= 0.03`
- gate пишет:
  - `selection_mask_internal_final.png`
  - `selection_overlay_internal_final.png`
  - `contour_snap_gate.json`
  - `contour_snap_gate_summary.json`
- текущее решение:
  - `RGB contour snap` остаётся внутренним quality stage;
  - он не должен появляться как отдельная кнопка в целевом UX.


### P6D.1

- добавлен отдельный internal scorer `whole object as one layer`;
- scorer сравнивает:
  - `before-ai`
  - `after-ai`
  - `internal-final`
- sample-level scoring теперь смотрит не только на edge delta, а на:
  - `target coverage`
  - `target hit ratio`
  - `fragmentation`
  - `background spill`
  - `coverage balance`


### P6D.2

- собран первый `object selection` compare-runner на проблемных сценах:
  - `cassette-closeup`
  - `keyboard-hands`
  - `hover-politsia`
- current summary:
  - `before-ai = 3` winner cases
  - `coherent = 1`
  - `partial = 2`
  - `fragmented = 0`
- важное решение:
  - `edge cleanup` и `object quality` больше не считаются одной и той же метрикой;
  - следующий gate должен быть `objectness-first`, а `contour snap` должен стать secondary stage.


### P6D.3

- добавлен internal `objectness-first gate`;
- gate пишет:
  - `selection_mask_objectness_final.png`
  - `selection_overlay_objectness_final.png`
  - `objectness_gate.json`
  - `objectness_gate_summary.json`
- текущее решение на preset-сценах:
  - `before-ai = 4` winner cases
- новый canonical internal order:
  - `objectness gate`
  - `edge cleanup`
  - `clean plate`


### P6D.4

- добавлен `drone-portrait` как дополнительный portrait control case;
- на нём:
  - `objectness-first` снова выбрал `before-ai`;
  - winner decision = `coherent`;
  - `contour snap` был отклонён internal gate;
- это усилило вывод:
  - portrait-like central subject уже работает лучше;
  - wide/street и tabletop-like сцены остаются основным quality bottleneck.


### P6D.5

- sample set расширен ещё двумя case classes:
  - `punk-rooftop`
  - `truck-driver`
- текущий `objectness-first` срез теперь на `6` сценах:
  - `before-ai = 6`
  - `coherent = 3`
  - `partial = 3`
- новый practical split:
  - `coherent`:
    - `cassette-closeup`
    - `drone-portrait`
    - `punk-rooftop`
  - `partial`:
  - `keyboard-hands`
  - `hover-politsia`
  - `truck-driver`


### P7A.1

- live preview переведён с `rectangular proxy plates` на `mask-based plate composition`;
- в stage теперь реально используются:
  - `backgroundMaskUrl`
  - `plateMaskUrls[]`
  - `plateCoverage[]`
- `plateStack + exportPlateLayout()` теперь влияют не только на motion/layout, но и на alpha composition preview;
- введён coverage gate:
  - plate не попадает в основной preview, если `plateCoverage <= 0.002`;
- на `hover-politsia` review подтверждает, что большие прямоугольные proxy-области ушли из user-facing preview.


### P7A.2

- `buildPlateCompositeMaps(...)` расширен до реального RGBA output:
  - `backgroundRgbaUrl`
  - `plateRgbaUrls[]`
- stage preview теперь предпочитает `RGBA plate assets`, а не `source + mask`;
- `mask-only` path оставлен как fallback, если RGBA asset по какой-то причине не собран;
- продуктово это означает переход от `plate-aware masking` к `plate-aware image composition`.


### P7A.3

- добавлен первый multi-plate export contract:
  - `window.vetkaParallaxLab.exportPlateAssets()`
- contract теперь отдаёт:
  - `globalDepthUrl`
  - `backgroundRgbaUrl`
  - `backgroundMaskUrl`
  - `plateStack`
  - `layout`
  - `plates[]`
- для каждого plate экспортируются:
  - `rgbaUrl`
  - `maskUrl`
  - `depthUrl`
  - `coverage`
  - `z`
  - `depthPriority`
- это первый шаг, где complex scene можно читать через `B/W depth` не только globally, но и plate-wise.


### P7A.4

- browser export contract доведён до file/export flow на диск;
- добавлены:
  - `photo_parallax_playground/e2e/parallax_plate_export.spec.ts`
  - `scripts/photo_parallax_plate_export.sh`
- на `hover-politsia` реально собраны:
  - `global_depth_bw.png`
  - `background_rgba.png`
  - `plate_01_rgba.png`
  - `plate_01_depth.png`
  - `plate_stack.json`
  - `plate_layout.json`
  - `plate_export_manifest.json`
- это первый закрытый шаг, где multi-plate pipeline перестал быть только preview-ориентированным.


### P7A.5

- в complex scene presets добавлены первые `special-clean` plate-ы:
  - `hover-politsia` -> `no vehicle`
  - `keyboard-hands` -> `no hands`
  - `truck-driver` -> `no driver`
- exporter теперь сохраняет `*_clean.png` для `special-clean` / `cleanVariant` plate-ов;
- exporter прогнан на `3` complex scenes:
  - `hover-politsia`
  - `keyboard-hands`
  - `truck-driver`
- в процессе найден input asset bug:
  - `truck-driver.png` фактически был JPEG под неверным расширением;
  - sample перекодирован в реальный PNG, после чего `sourceRasterReady` и exporter стабилизировались.


### P7B.1

- добавлен первый `multiplate` final renderer:
  - `scripts/photo_parallax_render_preview_multiplate.py`
  - `scripts/photo_parallax_render_preview_multiplate.sh`
- renderer читает:
  - `background_rgba.png`
  - `plate_XX_rgba.png`
  - `plate_layout.json`
  - `plate_export_manifest.json`
- собран batch `preview_multiplate.mp4` на `3` complex scenes:
  - `hover-politsia`
  - `keyboard-hands`
  - `truck-driver`
- найден и исправлен scale bridge bug:
  - exported assets были preview-sized;
  - final render initially трактовал их как full-res;
  - введён `asset_scale` bridge по отношению к `layout.source.width`.


### P7B.2

- `multiplate` renderer расширен на `special-clean aware` underlay:
  - hidden `special-clean` / `cleanVariant` plate-ы теперь читаются из `plate_export_manifest.json`;
  - `*_clean.png` подмешиваются как clean underlay до `background_rgba` и visible RGBA plate-ов;
  - report теперь отдельно фиксирует `special_clean_count`.
- updated batch render подтверждён на `3` complex scenes:
  - `hover-politsia`
  - `keyboard-hands`
  - `truck-driver`


### P7B.3

- добавлен compare runner:
  - `scripts/photo_parallax_compare_multiplate.py`
  - `scripts/photo_parallax_compare_multiplate.sh`
- compare artifacts собираются как:
  - `compare_sheet.png`
  - `compare_grid.mp4`
  - `compare_batch_sheet.png`
- compare summary теперь не молча теряет неполные кейсы, а пишет `skipped` с reason;
- текущий статус:
  - `hover-politsia` -> compare собран
  - `keyboard-hands` -> compare собран
  - `truck-driver` -> `skipped`, потому что отсутствует legacy `2-layer` base preview path.


### P7B.4

- введён `plate-local clean routing`:
  - visible plate теперь может иметь собственный `cleanVariant`;
  - hidden `special-clean` plate с тем же `cleanVariant` используется не глобально, а как local underlay перед этим plate;
  - это уже ближе к AE-логике `no vehicle / no hands / no driver`.
- подтверждено на complex scenes:
  - `hover-politsia` -> `routed_clean_count = 1`
  - `keyboard-hands` -> `routed_clean_count = 1`
  - `truck-driver` -> `routed_clean_count = 1`
- `truck-driver` browser export blocker снят:
  - problem source был в hydration path для `sourceRasterReady`;
  - export-spec теперь умеет принудительно гидратировать raster из уже загруженного sample image;
  - `truck-driver` снова проходит `photo_parallax_plate_export.sh`.
- compare для `truck-driver` всё ещё `skipped`, но уже по другой причине:
  - у сцены отсутствует legacy `2-layer` base preview path, а не сам multiplate/export pipeline.


### P7C.1

- добавлен локальный `Qwen Plate Planner`:
  - `scripts/photo_parallax_qwen_plate_plan.py`
  - `scripts/photo_parallax_qwen_plate_plan.sh`
- planner читает:
  - source image
  - `global_depth_bw.png`
  - current `plate_stack.json`
- planner пишет:
  - `output/qwen_plate_plans/<sample>.json`
  - `public/qwen_plate_plans/<sample>.json`
  - `manifest.json`
- planner подтверждён на `3` complex scenes:
  - `hover-politsia`
  - `keyboard-hands`
  - `truck-driver`
- sanitizing слой допилен:
  - `special-clean` дедуплицируются;
  - `cleanVariant` нормализуется в slug;
  - `target_plate` резолвится по semantic label или plate id;
  - `plate_stack_proposal` больше не размазывает один `cleanVariant` по всем visible plate-ам.
- sandbox получил hidden bridge:
  - app подгружает `/qwen_plate_plans/<sample>.json`;
  - в debug panel добавлен блок `Qwen Plate Plan`;
  - proposal можно применить в текущий `plateStack` через hidden action `apply qwen plan`.


### P7C.2

- собран первый end-to-end compare-flow:
  - `manual plate stack -> export -> multiplate render`
  - против `qwen plate plan -> export -> multiplate render`
- exporter теперь умеет опционально применять `Qwen` proposal перед export:
  - `photo_parallax_plate_export.sh <sample> --apply-qwen-plan`
- Qwen export pack пишется отдельно:
  - `photo_parallax_playground/output/plate_exports_qwen/<sample>`
- добавлены инструменты:
  - `scripts/photo_parallax_compare_qwen_multiplate.py`
  - `scripts/photo_parallax_compare_qwen_multiplate.sh`
  - `scripts/photo_parallax_qwen_multiplate_flow.sh`
- compare собран на `3/3` complex scenes:
  - `hover-politsia`
  - `keyboard-hands`
  - `truck-driver`
- текущий вывод:
  - `Qwen Plate Planner` уже полезен как structural proposal layer;
  - он добавляет meaningful `special-clean` варианты вроде `no-people`, `no-vehicle`, `no-keyboard`;
  - но всё ещё не должен автозаменять manual/default stack без gate.


### P7C.3

- добавлен deterministic `Qwen Plate Gate`:
  - `scripts/photo_parallax_qwen_plate_gate.py`
  - `scripts/photo_parallax_qwen_plate_gate.sh`
- gate читает:
  - manual `plate_stack.json`
  - qwen-applied `plate_stack.json`
  - `qwen_plate_plan.json`
- gate пишет:
  - `output/qwen_plate_gates/<sample>.json`
  - `public/qwen_plate_gates/<sample>.json`
  - `manifest.json`
- policy now:
  - `keep-current-stack`
  - `enrich-current-stack`
  - `replace-current-stack`
- текущие решения:
  - `hover-politsia` -> `enrich-current-stack`
  - `keyboard-hands` -> `keep-current-stack`
  - `truck-driver` -> `keep-current-stack`
- sandbox получил hidden bridge:
  - app подгружает `/qwen_plate_gates/<sample>.json`;
  - `Qwen Plate Plan` block показывает decision;
  - можно применить `gated_plate_stack` через hidden action `apply gated stack`.
- residual risk:
  - repeated end-to-end `qwen_multiplate_flow.sh` всё ещё headless-flaky на части сцен из-за browser export orchestration;
  - сам gate считается корректно по уже собранным manual/qwen stack outputs.


### P7C.4

- собран полный gate-aware flow:
  - `manual stack -> Qwen Plate Gate -> gated stack -> export -> multiplate render -> compare`
- добавлен wrapper:
  - `scripts/photo_parallax_qwen_gated_multiplate_flow.sh`
- compare собран на `3/3` complex scenes:
  - `hover-politsia`
  - `keyboard-hands`
  - `truck-driver`
- подтверждено, что:
  - `hover-politsia` идёт как `enrich-current-stack`;
  - `keyboard-hands` и `truck-driver` остаются `keep-current-stack`;
  - raw planner больше не нужен в final render path.
- для browser export orchestration добавлен hardening:
  - export-spec переведён на внешний Playwright polling вместо одной длинной `page.evaluate`;
  - `hydrateSourceRasterFromAsset()` используется как повторяемый fallback;
  - `photo_parallax_plate_export.sh` получил retry policy с `3` попытками и паузой между ними.
- residual risk после hardening:
  - batch path теперь проходит полностью, но orchestration остаётся чувствительным местом и не должен считаться закрытым навсегда;
  - сам product policy уже достаточно стабилен для движения дальше по roadmap.


### P7C.5

- введён первый deterministic routing rule между `Portrait Base` и `Multi-Plate`;
- routing встроен в sandbox contracts:
  - `getState()`
  - `exportPlateLayout()`
- current rule:
  - `multi-plate`, если есть `special-clean` plate;
  - `multi-plate`, если visible renderable plate-ов больше двух;
  - иначе `portrait-base`.
- это даёт первый product-level split без роста пользовательского UI.


### P7C.6

- в `plate_layout.json` введён первый `camera-safe` contract;
- для каждого plate добавлен `risk`:
  - `plateCoverage`
  - `recommendedOverscanPct`
  - `minSafeOverscanPct`
  - `disocclusionRisk`
  - `cameraSafe`
- на уровне layout добавлены:
  - `cameraSafe`
  - `transitions[]`
- `photo_parallax_render_preview_multiplate.py` теперь пишет это и в render report.
- прогон на gated multi-plate set показал:
  - все `3/3` complex scenes сейчас просят больший overscan;
  - `truck-driver` дополнительно даёт самый высокий transition risk.
