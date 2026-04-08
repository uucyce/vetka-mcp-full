# Parallax P0 Shipping Readiness Recon

Дата фиксации: `2026-04-07`
Задача: `tb_1775579318_21940_1`
Статус: `functional readiness recon for next clean chat`

## 1. Important Path Reality

Для следующего чата важно не перепутать два разных слоя проекта.

В этой ветке `codex/parallax` актуальный код находится в корневом repo как:

- `photo_parallax_playground/src/...`
- `photo_parallax_playground/src/lib/...`
- `scripts/...`
- `docs/180_photo-to-parallax/...`

Это не тот standalone app-root, в котором раньше велась часть UI-итераций.

Следовательно:

- новый чат должен читать именно корневой repo layout;
- нельзя автоматически предполагать, что самый свежий UI-state из отдельного playground-root уже отражён здесь.

## 2. Executive Summary

Текущая функциональная картина лучше, чем кажется по UI.

Подтверждено:

- headless/CLI линия уже реально существует;
- depth как standalone backend уже существует;
- plate/layout/export contracts уже существуют;
- explicit layer extraction уже существует как отдельный offline extractor;
- camera/motion engine уже существует как reusable code;
- AE-friendly направление уже подтверждено в docs.

Но также подтверждено:

- functional pieces пока разнесены по нескольким не до конца согласованным путям;
- часть обещаний уже записана в help-text/docs, но ещё не доведена до shipping-grade path;
- playground UI bridge в этой ветке выглядит старее, чем functional roadmap вокруг него.

Главный вывод:

- ближайший shipping path должен идти через `scripts/` и service-level contracts,
- а не через playground UI.

## 3. Depth Readiness

### What is already real

Standalone depth backend уже существует в:

- [cut_depth_service.py](/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground_codex/src/services/cut_depth_service.py)

Факты:

- есть `DepthResult` и deterministic sidecar paths;
- есть `generate_depth()` с backend selection;
- есть AI path и fallback `ffmpeg-luma`;
- есть cache convention `.cut_depth`;
- depth и preview paths формируются через `get_depth_paths()`.

Это означает:

- depth generation уже не зависит от playground UI;
- depth как отдельный subproduct уже почти готов structurally.

### Shipping verdict

`Depth standalone = near-shipping`

Главный remaining step:

- сделать вокруг existing service минимальный clean CLI/export contract для Паши/CUT, а не изобретать depth заново.

## 4. Layer Extraction Readiness

### What is already real

Offline extractor уже существует в:

- [photo_parallax_layer_extract.py](/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground_codex/scripts/photo_parallax_layer_extract.py)

Факты:

- script прямо декларирует offline explicit layer extraction;
- выход — canonical `layer_space.json` + `prototype.json`;
- extractor читает:
  - source RGB,
  - real 16-bit depth,
  - plate stack metadata,
  - plate layout metadata,
  - LaMa clean plate,
  - subject plate assets;
- docs подтверждают canonical contract:
  - [PARALLAX_LAYERPACK_HANDOFF_2026-03-27.md](/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground_codex/docs/180_photo-to-parallax/PARALLAX_LAYERPACK_HANDOFF_2026-03-27.md)
  - [PARALLAX_EXPLICIT_LAYER_EXTRACTION_ARCHITECTURE_2026-03-27.md](/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground_codex/docs/180_photo-to-parallax/PARALLAX_EXPLICIT_LAYER_EXTRACTION_ARCHITECTURE_2026-03-27.md)

### Important constraint

Extractor пока завязан на существующие baked assets из `output/...`, а не на одну короткую single-command shipping path.

Кроме того, сам extractor всё ещё содержит bbox/depth-band heuristics, например:

- `bbox_mask(...)`
- depth-band masking

Это значит:

- layer extraction уже реальна;
- но вопрос качества `not box-looking masks` ещё нельзя считать автоматически закрытым.

### Shipping verdict

`Explicit layer extraction = real but not yet calm-shipping`

Ближайшие прямые blockers уже известны и совпадают с бордом:

- `tb_1774648952_26537_1` — sync extractor source
- `tb_1774649270_26537_1` — distinct special-clean plates per target

## 5. Clean Plates / Hole Fill Readiness

### What is already real

Clean-plate линия существует не только в документах.

Подтверждено:

- extractor ищет LaMa clean plate;
- layerpack handoff уже перечисляет hole-filled outputs;
- `special-clean` присутствует в layout/export contracts;
- render/multiplate scripts читают clean assets из manifest/export packs.

Файловые опоры:

- [plateLayout.ts](/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground_codex/photo_parallax_playground/src/lib/plateLayout.ts)
- [photo_parallax_render_preview_multiplate.py](/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground_codex/scripts/photo_parallax_render_preview_multiplate.py)
- [PARALLAX_LAYERPACK_HANDOFF_2026-03-27.md](/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground_codex/docs/180_photo-to-parallax/PARALLAX_LAYERPACK_HANDOFF_2026-03-27.md)

### Shipping verdict

`Clean plates / hole fill = partially real, still quality-gated`

Ключевой риск:

- per-target special-clean correctness ещё не считается solved.

То есть:

- это уже не R&D fantasy;
- но именно эта линия пока отделяет нас от спокойного layer-pack shipment для Паши.

## 6. Headless Package Readiness

### What is already real

Headless entrypoint уже есть:

- [vetka_parallax_cli.py](/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground_codex/scripts/vetka_parallax_cli.py)

Факты:

- CLI реально принимает input image and output path;
- умеет auto depth;
- умеет motion presets;
- строит FFmpeg render path без browser/server/CUT runtime;
- использует production-ish services:
  - `cut_depth_service`
  - `cut_depth_engine`

### Important blocker

CLI help заявляет manifest mode:

- `--manifest layer_space.json`

Но в parser такого аргумента фактически нет.

Это означает:

- single-image → video path реален;
- `layer_space.json -> packaged parallax scene` в CLI ещё не доведён до честного рабочего интерфейса.

### Shipping verdict

`Headless package = promising and partially real, but contract still split`

Ближайший shortest path:

- не переписывать CLI,
- а дотянуть существующий CLI до честного manifest/layer-pack mode.

## 7. Motion Readiness

### What is already real

Motion engine уже существует в reusable form:

- [cut_depth_engine.py](/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground_codex/src/services/cut_depth_engine.py)

Факты:

- есть `CameraGeometry`;
- есть motion normalization;
- есть FFmpeg parallax filter generation;
- есть depth-band model;
- есть camera/lens parameters;
- есть preset vocabulary в CLI:
  - `orbit`
  - `orbit_zoom`
  - `dolly_zoom_in`
  - `dolly_zoom_out`
  - `linear`
  - `gentle`
  - `dramatic`

Кроме того:

- multiplate preview renderer уже существует отдельно;
- camera geometry and AE calibration research уже задокументированы.

### Shipping verdict

`Motion presets = closer than UI suggests`

Motion не требует сначала timeline UI.

Главный remaining step:

- привязать motion cleanly к layer-pack/headless package, а не к scattered preview paths.

## 8. AE Package Readiness

### What is already real

AE target уже давно продуктово осмыслен и хорошо задокументирован:

- [PAVEL_AE_REFERENCE_WORKFLOW_2026-03-13.md](/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground_codex/docs/180_photo-to-parallax/PAVEL_AE_REFERENCE_WORKFLOW_2026-03-13.md)
- [PARALLAX_CAMERA_GEOMETRY_AND_LENS_RESEARCH_2026-03-19.md](/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground_codex/docs/180_photo-to-parallax/PARALLAX_CAMERA_GEOMETRY_AND_LENS_RESEARCH_2026-03-19.md)

Подтверждено:

- продуктовая цель уже ближе к `AE-friendly package`, а не к одной глобальной маске;
- `layer_space.json` уже мыслится как shared manifest contract;
- plate/local depth/clean plate model совпадает с Пашиным AE workflow.

### What is not yet real

Не найдено прямого готового `AE import script` или `.aep` generator path в текущем коде.

То есть:

- AE direction есть как architecture and packaging target;
- прямой Pavel-friendly import automation ещё не найден.

### Shipping verdict

`AE package = defined target, not yet direct shipping path`

Правильный ближайший шаг:

- делать `folder package + manifest + import script`,
- а не plugin.

## 9. Playground UI Reality In This Branch

Важно для следующего чата:

- playground bridge в [App.tsx](/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground_codex/photo_parallax_playground/src/App.tsx) в этой ветке выглядит более ранним и более debug-heavy;
- внутри него уже есть browser export/import helpers;
- но functional shipping path не должен строиться вокруг этого UI.

В частности:

- UI exports существуют через `window.vetkaParallaxLab`;
- plate/layout/assets contracts уже можно читать;
- но сама UI-ветка не выглядит как самое короткое место для shipping P0/P1/P2.

## 10. Shortest Shipping Path

Самый рациональный путь сейчас:

1. **P0**
   - оформить existing depth service как clean standalone export path

2. **P1**
   - закрыть extractor source drift
   - закрыть per-target special-clean correctness
   - дотянуть explicit layer pack до calm-shipping quality

3. **P2**
   - довести `vetka_parallax_cli.py` до честного package mode:
     - `single image`
     - `layer_space.json`
     - deterministic outputs

4. **P3**
   - использовать existing motion engine as headless presets

5. **P4**
   - добавить AE-friendly import/package layer

## 11. Final Verdict

Трезвая оценка:

- `Depth standalone` — почти готово
- `Layer extraction` — реально существует, но ещё quality-blocked
- `Clean plates` — реально существуют, но ещё correctness-blocked
- `Headless parallax package` — уже начат, но contract split
- `Motion presets` — уже ближе, чем кажется
- `AE package` — пока architectural target, не direct implementation

То есть до полезного Pavel-facing инструмента осталось не так много, как казалось во время UI-итераций.

Главный remaining gap:

- не придумать новую систему,
- а собрать уже существующие depth / layer / clean / motion pieces в один честный shipping path.
