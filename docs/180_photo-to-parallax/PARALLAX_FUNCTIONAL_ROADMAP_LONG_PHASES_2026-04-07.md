# Parallax Functional Roadmap Long Phases

Дата фиксации: `2026-04-07`
Статус: `canonical functional roadmap after UI detour`

## 1. Purpose

Этот документ фиксирует новый главный приоритет для `photo-to-parallax`.

Главная коррекция:

- перестать считать UI-polish главным путём к результату;
- перестать тратить фазы на endless cleanup кнопок и secondary panels;
- считать целевым продуктом не красивый playground, а рабочий инструмент для Паши и CUT.

На этом этапе интерфейс считается secondary shell.

Главный вопрос теперь не:

- `насколько clean выглядит surface`

А:

- `можем ли мы уже отдавать полезный production artifact`

## 2. Canonical Product Goal

Ближайший реальный продукт это не native plugin для After Effects.

Ближайший реальный продукт это:

- `AE-friendly package`
- или `headless pipeline + AE import script`
- или `prepared After Effects project`

Нативный `AE effect/plugin` на текущем этапе считается слишком дорогим по stack complexity, host API, packaging и debug cost.

Практический shipping target:

- source image
- depth map
- extracted RGBA layers
- clean plates behind removed objects
- depth / z ordering metadata
- optional motion presets
- AE-friendly export structure

## 3. Product Priority Order

Новый порядок приоритетов:

1. `Depth as standalone useful tool`
2. `Layer extraction without box-looking masks`
3. `Background repair / clean plates / hole fill`
4. `Parallax scene assembly`
5. `Motion presets without mandatory UI`
6. `AE package / import workflow`
7. `UI cleanup and design`

UI остаётся только как debug and operator helper surface.

## 4. What Already Exists

По состоянию на `2026-04-07` уже зафиксированы следующие сильные базы:

- global depth pipeline существует и уже имеет отдельную ценность;
- object-centric / plate-centric направление уже введено в архитектуру;
- viewer-first reset и stage-object path уже были доведены в `main`;
- `object -> layer authority` частично доведён:
  - object authority carried through layout/export contracts;
  - cleanup flow уже привязывался к authoritative object layers;
  - matte / brush edits уже привязывались к `targetPlateId`;
- special-clean / clean-plate логика уже существует как продуктовая линия, а не как абстрактная идея;
- AE reference workflow уже разобран и подтверждает правильность `multi-plate + clean plate + camera move` модели.

Это означает:

- мы уже не в research-zero;
- мы уже не строим идею с нуля;
- главный риск теперь не отсутствие концепции, а недоведённость extraction/export chain.

## 5. New Invariants

С этого момента нельзя снова скатиться в приоритет кнопок над функцией.

Новые инварианты:

- ни одна UI-задача не может блокировать functional shipment;
- если feature можно отдать через CLI/script/package раньше UI, выбирается CLI/script/package;
- `Depth` считается отдельным shipping-capable tool;
- `plate extraction` оценивается по качеству plate outputs, а не по красоте object inspector;
- `clean plate` оценивается по реальному repair quality, а не по richness cleanup controls;
- motion может быть shipped без keyframe UI;
- `AE package` приоритетнее `AE plugin`.

## 6. Long Phases

### Phase A — Depth Tool Shipping

Цель:

- сделать `depth map` отдельным полезным инструментом для Паши и CUT.

Definition of done:

- deterministic depth generation for supported inputs;
- stable saved artifact;
- preview/export parity;
- predictable file output for downstream tools.

Minimum deliverables:

- depth image export;
- depth metadata if needed;
- simple CLI/script entrypoint;
- one or more verified example outputs.

Почему это важно:

- даже без full parallax depth уже полезен;
- это самый зрелый кусок текущего продукта;
- это отдельная победа, даже если extraction ещё не perfect.

### Phase A2 — Layer Extraction Shipping

Цель:

- получать semantically useful layers, а не box-looking masks.

Definition of done:

- extracted layers are visually plate-like;
- object boundaries are not obviously square/bbox-shaped;
- output is usable in compositing;
- export chain is deterministic.

Сюда входят:

- explicit layer extraction;
- semantic/object plate routing;
- object authority;
- export of RGBA plates;
- basic z/depth ordering metadata.

Current likely blockers:

- extractor source drift;
- routing/export mismatches;
- remaining special-clean/export inconsistencies.

### Phase A3 — Clean Plate / Hole Fill Shipping

Цель:

- не просто вырезать объект, а восстанавливать сцену за ним.

Definition of done:

- clean plate artifacts exist per needed target;
- repaired background is visually usable;
- special-clean outputs are distinct per target when scene requires it;
- output can be dropped into AE without manual patching becoming mandatory.

Это критический shipping gate.

Если `A2 + A3` устойчивы, инструмент уже можно отправлять Паше как production-helpful package даже без финального UI.

### Phase B — Parallax Scene Assembly

Цель:

- превратить depth + plates + clean plates в осмысленную parallax scene.

Definition of done:

- scene can be assembled into ordered layers;
- relative object distance follows depth/z model;
- lens/focal thinking is explicit enough to control scene behavior;
- result is not just static plates, but a coherent parallax layout.

Сюда входят:

- plate-local depth / z assignment;
- plate-aware layout;
- lens hints or focal presets;
- camera-safe checks.

### Phase C — Motion Presets Without UI Dependency

Цель:

- дать Паше usable motion without waiting for timeline/keyframe UI.

Definition of done:

- a few canonical move types exist;
- speed/intensity can be controlled;
- motion can be generated headlessly;
- output is renderable or exportable into AE-ready form.

На этом этапе не обязательны:

- full keyframe editor;
- interactive camera UI;
- timeline polish.

Достаточно:

- push-in / push-out
- pan / orbit-like drift
- subtle handheld/parallax drift
- speed controls
- preset system

### Phase D — AE Package

Цель:

- отдать Паше не raw folder chaos, а минимально упакованный AE-friendly result.

Definition of done:

- export layout is deterministic;
- names are readable;
- layer ordering is explicit;
- AE import is easy.

Возможные формы:

1. `AE-friendly folder package`
2. `JSON + import script`
3. `prepared After Effects project`

Предпочтительный practical path:

- сначала `AE-friendly package + import script`;
- только потом, если cost приемлем, `prepared .aep workflow`.

### Phase E — Thin Operator Shell

Цель:

- только после shipping pipeline вернуть UI к supporting role.

Правильный scope:

- debug and preview shell;
- manual overrides for hard scenes;
- operator-facing review surface.

Неправильный scope:

- endless button cleanup as main workstream;
- decorative panel refactors before shipment;
- rebuilding pro-app UX ahead of functional export.

## 7. Deferred Work

Сознательно откладывается:

- native After Effects effect/plugin;
- rich keyframe UI;
- full camera timeline editor;
- deep design-system polish;
- repeated button cleanup without direct impact on output quality.

Эти темы не запрещены навсегда.

Они просто не могут быть главной осью следующих фаз.

## 8. Recommended Execution Order

Практический execution order теперь такой:

1. verify current `Depth` shipping readiness
2. close extractor/source/export drift
3. close special-clean / distinct clean-plate generation
4. make deterministic headless export package
5. add motion presets
6. add AE-friendly packaging/import
7. only then return to UI consolidation

## 9. Practical Question For Every New Task

Перед каждой новой задачей нужно задавать только один вопрос:

- `Это приближает нас к shipping depth / layers / clean plates / parallax / motion / AE package?`

Если ответ:

- `да` — задача входит в canonical roadmap;
- `нет` — задача secondary и не должна съедать фазу.

## 10. Canonical Near-Term MVP

Ближайший реальный MVP для Паши:

- one image in
- depth map out
- extracted layer pack out
- clean plates out
- ordered parallax scene data out
- optional motion preset render or AE import package out

Это уже считается настоящим продуктом.

Даже если UI ещё rough.
