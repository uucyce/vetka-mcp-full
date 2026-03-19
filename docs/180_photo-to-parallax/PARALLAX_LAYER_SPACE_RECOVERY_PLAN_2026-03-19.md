# Parallax Layer Space Recovery Plan

Дата: `2026-03-19`

## 1. Purpose

Этот документ фиксирует correction plan после архитектурного drift.

Главная задача:

- вернуть в центр системы настоящий `layer-space pipeline`;
- перестать считать synthetic browser-side composition целевой реализацией `Multi-Plate`;
- восстановить правильную иерархию:
  - сначала строим пространство и слои,
  - потом валидируем,
  - только потом рендерим.

## 2. Original Correct Architecture

Исходная правильная линия для продукта была такой:

1. `source`
2. `depth / object grouping`
3. `layer-space draft`
4. `layer validation`
5. `exportable layered assets`
6. `parallax render`

Это и есть правильная целевая архитектура для:

- сильного photo parallax;
- motion/video;
- downstream color / grading workflows;
- будущего reusable layered-space tooling.

## 3. What Went Wrong

По ходу release-hardening фокус сместился.

Что произошло:

- система начала оптимизироваться под export repeatability;
- `cameraSafe`, readiness, contract freeze и batch QA стали доминировать;
- upstream `layer-space` не был доведён до полноценного независимого слоя;
- вместо него закрепился surrogate path внутри playground.

Текущее surrogate место:

- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/src/App.tsx`
- `buildPlateCompositeMaps(...)`

Почему это drift:

- plate assets строятся browser-side из:
  - remapped depth
  - box priors
  - focus/manual controls
  - synthetic union-alpha composition
- это не равно настоящему semantic/layer decomposition.

## 4. Canonical Correction

С этого момента canonical target снова формулируется так:

### Canonical target

- `layer-space` является primary product artifact.

### Renderer role

- renderer только потребляет уже построенный `layer-space`;
- renderer не должен быть местом, где “рождается” ощущение пространства;
- renderer не должен скрывать слабый layer decomposition за счёт safe motion.

### Safety role

- `cameraSafe`, readiness, export diagnostics остаются важными;
- но они secondary относительно качества самого `layer-space`.

## 5. New Canonical Artifact

Нужен новый центральный contract:

- `layer_space.json`

Минимальный состав:

- `contract_version`
- `sampleId`
- `source`
- `space`
- `layers`
- `validation`
- `provenance`

### `space`

Должен содержать:

- global scene bounds
- depth policy
- ordering policy
- grouping policy
- recommended camera constraints

### `layers[]`

Каждый layer должен иметь:

- `id`
- `label`
- `role`
- `group_family`
- `visible`
- `z`
- `depthPriority`
- `coverage`
- `source`
- `rgba`
- `mask`
- optional `depth`
- optional `clean_variant`
- optional `motion_hint`

### `validation`

Должна содержать:

- object cohesion signals
- fragmentation signals
- overlap sanity
- background independence
- camera-safe compatibility

### `provenance`

Должна объяснять:

- depth backend
- grouping backend
- planner backend
- gate decisions
- manual edits / overrides

## 6. Recovery Principle

Новый recovery plan делит систему на два уровня:

### Level A. Layer-space builder

Это настоящее ядро.

Он отвечает за:

- scene decomposition;
- object grouping;
- background separation;
- layer ordering;
- generating exportable layer assets.

### Level B. Render stack

Это downstream consumer.

Он отвечает за:

- camera motion;
- safe travel;
- preset outputs;
- compare videos;
- batch summaries.

Правило:

- если Level A слабый, Level B не считается успешным только потому, что batch JSON = `pass`.

## 7. Current Surrogate Components

Текущие компоненты, которые считаются временными surrogate implementation:

- `buildPlateCompositeMaps(...)` in `src/App.tsx`
- focus-driven `computeBaseDepth(...)` fallback in `src/App.tsx`
- synthetic box-based plate alpha generation in playground runtime

Они могут жить как:

- debug preview;
- fallback mode;
- prototype bridge.

Но не как canonical `Multi-Plate` implementation.

## 8. Role Of Qwen And Semantic Grouping

`Qwen` и semantic grouping возвращаются в правильную роль.

Они нужны не как cosmetic add-on around render, а как upstream intelligence for layer-space.

Правильное место:

- object grouping
- candidate plate families
- semantic decomposition
- draft layer-space enrichment

### Qwen Plate Planner

Считать частью `layer-space draft`.

### Qwen Gate

Считать частью `layer validation`.

### Qwen-Image-Layered

Считать candidate backend for:

- `layer-space draft`
- richer RGBA decomposition
- better background independence

Но не replacement for:

- validation
- ordering
- camera-safe
- deterministic release contracts

## 9. Required Refactor

Нужна явная modular split.

### Module 1. `layerSpaceBuilder`

Новый основной модуль.

Он должен собирать:

- source + real depth
- grouping priors
- semantic plate candidates
- layer families
- exportable layer assets

### Module 2. `layerSpaceValidation`

Он должен проверять:

- object cohesion
- fragmentation
- overlap sanity
- background coherence
- camera-safe compatibility

### Module 3. `layerSpaceExport`

Он должен писать:

- `layer_space.json`
- `background_rgba.png`
- `layer_*.png`
- masks/depth/debug artifacts

### Module 4. `parallaxRender`

Он читает `layer_space.json` и рендерит:

- preview mp4
- posters
- compare sheets
- preset outputs

## 10. First Practical Recovery Slice

Первый реальный slice должен быть минимальным, но product-correct.

### Slice A

Сделать минимальный `layer_space.json` для 3 уровней:

- `foreground`
- `midground`
- `background`

на основе уже имеющихся:

- real depth
- manual/group object hints
- existing plate priors

### Slice B

Перевести export path так, чтобы он читал слои не из synthetic browser union-alpha logic,
а из нового layer-space artifact.

### Slice C

Сравнить:

- March 12 baseline
- current surrogate path
- recovered layer-space path

на одних и тех же scenes.

## 11. Success Criteria

Recovery считается успешным, когда:

- visual acceptance снова совпадает с архитектурой;
- layered parallax чувствуется как пространство, а не как oval/focus cutout;
- `layer_space.json` становится primary artifact;
- renderer становится downstream stage;
- `Qwen`/semantic grouping работают upstream, а не декоративно.

## 12. Immediate Next Steps

1. Добавить `layer_space` как canonical contract в docs.
2. Пометить current browser-side plate composition как surrogate/debug path.
3. Создать кодовый каркас `layerSpaceBuilder`.
4. Подключить его в export flow рядом с текущим path без немедленного destructive switch.
5. Сделать first visual bakeoff:
   - March 12 baseline
   - current qwen-gated render
   - recovered layer-space render

## 13. Decision

С этого момента canonical product goal звучит так:

- строим `layer-space`, а не просто рендер;
- рендер является доказательством качества `layer-space`, а не его заменой.
