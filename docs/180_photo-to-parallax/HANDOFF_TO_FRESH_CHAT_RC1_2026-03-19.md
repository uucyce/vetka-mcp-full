# Parallax Handoff To Fresh Chat RC1

Дата: `2026-03-20`

## 1. Зачем этот handoff

Этот документ нужен как короткая входная точка для следующего чата перед MVP-финишем.

Он фиксирует:

- что сейчас является canonical truth;
- что уже реально работает;
- где именно был найден drift;
- какие грабли уже подтверждены;
- какие задачи открыты на следующий чат;
- в каком порядке продолжать работу без повторного расползания архитектуры.

Критическое правило для следующего чата:

- `export works` и `batch pass` нельзя трактовать как product readiness;
- они подтверждают только engineering readiness;
- product readiness начинается там, где depth-first truth, camera geometry и visual result совпадают.

## 1.1 Update (`2026-03-27`)

После этого handoff был выполнен отдельный fresh-bundle cycle для `hover-politsia`.

Новые canonical docs:

- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/docs/180_photo-to-parallax/PARALLAX_HOVER_POLITSIA_ARTIFACT_PROVENANCE_RECON_2026-03-27.md`

Короткий итог update:

- historical `camera_contract` review bundle действительно был stale relative to the current export root;
- fresh rerender + fresh inspection pack были собраны заново;
- на fresh bundle motion читается не только в steam, но и в vehicle/walker;
- exact old “steam over head” symptom больше нельзя считать proven current-state truth;
- remaining weak point has narrowed to current visual quality / proxy-like semantics / compositor policy, not stale provenance.

If a next agent starts from this handoff, they should treat the `2026-03-27` provenance recon as a required companion doc.

## 2. Что читать первым

Стартовый порядок чтения:

1. `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/docs/180_photo-to-parallax/HANDOFF_TO_FRESH_CHAT_RC1_2026-03-19.md`
2. `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/docs/180_photo-to-parallax/PARALLAX_ROADMAP_RC1_COMPLETION_AND_LAYERED_BAKEOFF_2026-03-19.md`
3. `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/docs/180_photo-to-parallax/PARALLAX_SMART_DEPTH_RECON_2026-03-19.md`
4. `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/docs/180_photo-to-parallax/PARALLAX_VISUAL_FORENSIC_2026-03-19.md`
5. `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/docs/180_photo-to-parallax/PARALLAX_LAYER_SPACE_RECOVERY_PLAN_2026-03-19.md`
6. `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/docs/180_photo-to-parallax/PARALLAX_CAMERA_GEOMETRY_AND_LENS_RESEARCH_2026-03-19.md`
7. `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/docs/180_photo-to-parallax/PAVEL_AE_REFERENCE_WORKFLOW_2026-03-13.md`
8. `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/CONTRACTS_V1.md`

Короткая интерпретация:

- roadmap объясняет порядок работы;
- recon docs объясняют, где именно мы ошиблись;
- camera doc фиксирует новую geometry baseline;
- AE doc нужен как reference truth;
- contracts нужны как runtime/API source of truth.

## 3. Текущее состояние на `2026-03-20`

### Что уже подтверждено

- canonical smoke по release path проходит;
- camera geometry уже поднята в `plate_layout.json`;
- renderer уже умеет читать camera contract из layout;
- `smart depth` path в sandbox жив и это подтверждено recon-ом;
- основная визуальная проблема сейчас не в отсутствии depth, а в том, как downstream render/compositing использует depth и plate semantics.

### Что уже не надо переоткрывать

- вопрос “есть ли у нас умная глубина вообще?” закрыт: да, есть;
- вопрос “надо ли возвращать camera-based model?” закрыт: да, надо, и часть уже внедрена;
- вопрос “можно ли считать export success признаком готового продукта?” закрыт: нет.

### Что осталось незакрытым

- canonical white-near convention ещё не докатана как end-to-end truth на всём наборе артефактов;
- AE calibration против Пашиного проекта ещё открыта;
- atmospheric/compositing semantics для `hover-politsia` ещё не починены;
- visual truth всё ещё отстаёт от promising depth truth.

## 4. Что реально сделано в этом чате

### 4.1 Camera model

Сделано:

- создан canonical research doc:
  - `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/docs/180_photo-to-parallax/PARALLAX_CAMERA_GEOMETRY_AND_LENS_RESEARCH_2026-03-19.md`
- renderer bridge переведён с чистой эвристики к camera-based formula:
  - `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/scripts/photo_parallax_render_preview_multiplate.py`
- camera geometry добавлена в contract:
  - `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/src/lib/plateLayout.ts`
- contract/tests обновлены:
  - `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/src/lib/plateLayout.test.ts`
  - `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/e2e/parallax_plate_export.spec.ts`
  - `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/CONTRACTS_V1.md`

Что это значит:

- runtime уже может брать `camera_geometry.source = layout.camera`;
- мы больше не держим lens/distance полностью в undocumented heuristics.

### 4.2 Smart depth recon

Сделано:

- выпущен strict recon без экстрасенсорики:
  - `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/docs/180_photo-to-parallax/PARALLAX_SMART_DEPTH_RECON_2026-03-19.md`

Главный вывод recon:

- `smart depth` path реально существовал и частично жив;
- drift произошёл не потому, что “магия пропала”, а потому что export/render asset generation ушла в synthetic/surrogate path;
- depth-first preview truth и export/render truth стали разными сущностями.

### 4.3 Visual forensic

Сделано:

- выпущен visual forensic:
  - `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/docs/180_photo-to-parallax/PARALLAX_VISUAL_FORENSIC_2026-03-19.md`

Главный вывод:

- technical `pass` по export/render не гарантирует хороший parallax;
- хороший March baseline нельзя путать с текущим mp4 только потому, что batch summary зелёный.

### 4.4 Depth polarity

Подтверждено recon-ом:

- docs и planner prompt жили как `white = near`;
- а живой baked/runtime/export path для `hover-politsia` фактически жил как `black = near`.

Починено:

- generation переведена на canonical convention:
  - `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/scripts/photo_parallax_depth_bakeoff.py`
- canonical convention теперь:
  - `white = near`
  - `black = far`

Важно:

- это нужно удержать;
- не возвращать обратно ни в bakeoff, ни в UI preview, ни в planner prompt, ни в renderer.

### 4.5 Hover-politsia depth defaults

После white-near switch выяснилось:

- export depth стала слишком выбеливаться из-за старых remap defaults.

Подстроено:

- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/src/App.tsx`

Зафиксировано коммитом:

- `0b5031ff`
- `phase180.7: retune hover-politsia depth defaults after white-near switch [task:tb_1773892185_4]`

Практический смысл:

- depth для `hover-politsia` снова стала правдоподобной “из коробки”;
- это пока не общий solve для всех сцен, а point-fix для важного canonical sample.

### 4.6 Video/image inspection tool

Важно для следующего чата:

- Opus по моему заданию делает/уже внёс sidecar tool, чтобы ИИ мог лучше разбирать видео и изображения;
- related task:
  - `tb_1773972539_3`
- свежий related commit:
  - `a2c9e7c67`
  - `build: video_inspection_pack.py — M1 MVP (scaffold + contact_sheet + motion_diff + inspection.json) [task:tb_1773972539_3]`
- главный файл:
  - `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/scripts/video_inspection_pack.py`

Это не core parallax logic, но очень полезный supporting tool:

- для AI review mp4/gif;
- для contact sheets;
- для frame diffs;
- для объяснения render bugs без бесконечных описаний словами.

## 5. Главные артефакты, на которые смотреть

### Canonical compare/render

- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/output/render_compare_qwen_gated_multiplate/gated_batch_qa_summary.json`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/output/render_compare_qwen_gated_multiplate/regression_quality_summary.json`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/output/render_compare_qwen_gated_multiplate/visual_acceptance_summary.json`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/output/render_compare_qwen_gated_multiplate/visual_acceptance_checklist.md`

### Hover-politsia depth/debug

- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/output/plate_exports_qwen_gated/hover-politsia/global_depth_bw.png`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/output/plate_exports_qwen_gated/hover-politsia/plate_export_depth.png`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/output/plate_exports_qwen_gated/hover-politsia/plate_layout.json`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/output/plate_exports_qwen_gated/hover-politsia/plate_export_depth_state.json`

### Camera-contract render

- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/output/render_preview_multiplate_qwen_gated_camera_contract/hover-politsia/preview_multiplate.mp4`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/output/render_preview_multiplate_qwen_gated_camera_contract/hover-politsia/preview_multiplate.gif`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/output/render_preview_multiplate_qwen_gated_camera_contract/hover-politsia/preview_multiplate_report.json`

### Fresh current-truth bundle (`2026-03-27`)

- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/output/render_preview_multiplate_qwen_gated_camera_contract_fresh_20260327/hover-politsia/preview_multiplate.mp4`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/output/render_preview_multiplate_qwen_gated_camera_contract_fresh_20260327/hover-politsia/preview_multiplate_report.json`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/output/video_inspection/hover-politsia-camera-contract-fresh-20260327/inspection.json`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/output/video_inspection/hover-politsia-camera-contract-fresh-20260327/motion_diff.jpg`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/output/video_inspection/hover-politsia-camera-contract-fresh-20260327/motion_energy.png`

## 6. Текущие задачи на board

### Уже закрыто

- `tb_1773892185_4` — `PARALLAX: Introduce camera-based parallax model`
  - статус: `done_main`
  - commit: `0b5031ff`

### Ещё открыто

- `tb_1773892186_5` — `PARALLAX: Calibrate focal length and lens behavior against AE reference`
  - статус: `pending`
  - canonical docs:
    - `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/docs/180_photo-to-parallax/PARALLAX_CAMERA_GEOMETRY_AND_LENS_RESEARCH_2026-03-19.md`
    - `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/docs/180_photo-to-parallax/PAVEL_AE_REFERENCE_WORKFLOW_2026-03-13.md`

### Что логично добавить/продолжить следующим чатом

1. `tb_1773976439_6` — white-near rollout / verification
- довести canonical `white = near` до полного end-to-end состояния;
- проверить UI depth preview, export depth, planner semantics, renderer semantics на одном языке.

2. `tb_1773976439_7` — hover-politsia atmospheric compositing audit
- разобрать `street steam` / fog / atmospheric layer policy;
- понять, должен ли этот материал жить как hard plate, soft participation или часть vehicle/background composite.

3. `tb_1773892186_5` — AE calibration
- привязать current camera contract к Пашиному AE reference;
- сузить дефолты по `zoomPx`, `zNear`, `zFar`, `motionScale`, `Tx/Ty/Tz`.

4. `tb_1774594729_1` — compare fresh hover-politsia bundle against visual baseline
- идти не от stale-artifact hypothesis, а от current fresh bundle;
- назвать, что уже стало лучше;
- отделить remaining visual weakness from historical false alarms;
- сузить next fix path to compositor policy vs exporter semantics.

5. `tb_1774595847_1` — replace hard-box `environment-mid` semantics and reduce proxy-like authority
- это уже не abstract recon, а конкретный implementation path;
- first probe on `2026-03-27` showed that shaped atmospheric alpha is viable;
- camera tuning is not the first lever for this cycle.

## 7. Грабли, на которые больше не наступать

### Грабля 1. Export success != product success

Самая дорогая ошибка этого цикла:

- увидели, что export и batch QA проходят;
- начали трактовать это как “система готова”.

Правильно:

- export success = engineering signal;
- visual truth = отдельный gate;
- deployment readiness без visual acceptance не объявлять.

### Грабля 2. Не верить docs, если PNG говорит обратное

У нас был прямой semantic split:

- docs/planner говорили `white = near`;
- реальные depth PNG жили как `black = near`.

Правильно:

- проверять pixel values в baked/export artifacts;
- если docs и артефакты спорят, верить артефактам и чинить docs/code.

### Грабля 3. Не считать camera math серебряной пулей

Camera geometry нужна, но она не чинит:

- плохую plate semantics;
- wrong occlusion authority;
- atmospheric cards, которые едут как жёсткие cutout layers.

Правильно:

- optics и compositing policy надо разруливать отдельно.

### Грабля 4. Не возвращаться в `black-near`

Сейчас canonical решение выбрано:

- `white = near`
- `black = far`

Это надо удержать в:

- depth bakeoff generation;
- UI depth preview;
- export depth;
- planner prompt;
- renderer `depth -> Z`.

### Грабля 5. Не путать real depth preview с synthetic export assets

`smart depth` и `exported plates` долгое время были разными truth-ветками.

Правильно:

- явно спрашивать: “это raw/baked depth truth или synthetic export derivative?”
- не делать вывод о продукте только по derived artifacts.

### Грабля 6. Не тащить новую AI-модель, пока живой deterministic bug не закрыт

JEPA, новые multimodal модели, layered backends и прочее полезны, но:

- сначала закрыть deterministic bugs;
- потом открывать новую модель как compare lane;
- не заменять дебаг композитинга скачком в новый black box.

## 8. Что делать первым в следующем чате

Стартовый текст:

```text
Прочитай HANDOFF_TO_FRESH_CHAT_RC1_2026-03-19.md и продолжим parallax от текущего post-RC1 state. У нас уже есть smart-depth recon, visual forensic, camera geometry doc и white-near canonical decision. Export smoke проходит, но MVP ещё блокируется visual truth: нужно довести white-near end-to-end, затем проверить atmospheric compositing на hover-politsia и потом калибровать camera contract против AE reference.
```

После этого порядок действий такой:

1. открыть handoff;
2. открыть roadmap;
3. открыть `PARALLAX_SMART_DEPTH_RECON_2026-03-19.md`;
4. открыть `PARALLAX_CAMERA_GEOMETRY_AND_LENS_RESEARCH_2026-03-19.md`;
5. проверить task `tb_1773892186_5`;
6. продолжать либо с white-near rollout, либо с hover-politsia atmospheric audit.

## 9. Контекст этого чата

На момент handoff чат был близко к auto-compact:

- примерно `220k / 258k` tokens used;
- окно было около `85%`.

То есть этот документ нужен именно для безопасного перехода в следующий чат без повторного выжигания контекста.
