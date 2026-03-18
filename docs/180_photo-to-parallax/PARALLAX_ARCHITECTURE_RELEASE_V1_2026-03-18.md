# Parallax Architecture Release V1

Дата фиксации: `2026-03-18`

## 1. Purpose

Этот документ фиксирует актуальную архитектуру release-трека для `photo_parallax_playground`.

Он не заменяет исторические research-отчеты, а сводит их в один operational source of truth для:

- release planning;
- TaskBoard backlog;
- parallel research tracks;
- финального sandbox RC.

## 2. Source of Truth

Основные документы:

- `PHOTO_TO_PARALLAX_ARCHITECTURE_V1_2026-03-10.md`:
  исторический базовый архитектурный документ.
- `PHOTO_TO_PARALLAX_ROADMAP_CHECKLIST_2026-03-10.md`:
  полный research roadmap, шире чем release-v1.
- `HANDOFF_PHASE_180_2026-03-14.md`:
  краткий operational handoff и последние принятые решения.
- `CONTRACTS_V1.md`:
  зафиксированные export/layout/gate контракты sandbox v1.

Продуктовый смысл:

- `Portrait Base`:
  стабильный depth-first путь для простых сцен.
- `Multi-Plate`:
  основной следующий production track для complex scenes.

## 3. Current System

### 3.1 Runtime path

Текущий runtime path для сложных сцен:

- `source`
- `global depth`
- `initial isolate`
- `plateStack`
- `qwen plate plan`
- `qwen plate gate`
- `gated_plate_stack`
- `plate export`
- `plate-aware layout`
- `multiplate render`
- `compare manual vs gated-qwen`

### 3.2 Stable contracts

На release-v1 зафиксированы:

- `plate_layout.json`
- `plate_export_manifest.json`
- `qwen_plate_gate.json`
- `plate_export_readiness_diagnostics.json`

Все release-значимые контракты должны иметь `contract_version`.

### 3.3 Safety layer

Текущий safety layer состоит из:

- `cameraSafe.warning`
- `cameraSafe.suggestion`
- `readiness diagnostics`
- deterministic `Qwen Gate`

Release-v1 политика:

- raw AI proposal не идёт в final path;
- final path использует только gated stack;
- headless/export stability считается частью архитектуры, а не только tooling.

## 4. What Is Done

Уже operational:

- `Qwen Plate Planner`
- `Qwen Plate Gate`
- `gated multiplate flow`
- `routing: Portrait Base vs Multi-Plate`
- `camera-safe` warning/suggestion
- anti-flake readiness diagnostics
- `truck-driver` gated wrapper stability evidence
- v1 contract freeze for layout/export/gate

## 5. Release Tracks

### Track A. Release Delivery

Цель:

- довести sandbox до `RC1`.

Состав:

- freeze contracts
- stabilize export pipeline
- final render presets
- regression quality gates
- release packaging and runbook

### Track B. Core Refactor

Цель:

- уменьшить риск дальнейших изменений.

Состав:

- split `App.tsx`
- extract layout/risk/export services
- isolate contract builders
- increase unit coverage around release-critical logic

### Track C. Parallel Recon

Цель:

- подготовить следующий evolution path без блокировки release-v1.

Состав:

- recon existing docs and inconsistencies
- recon `Qwen-Image-Layered` as candidate decomposition backend

Правило:

- Recon не должен ломать release-v1 scope.
- Любая новая model integration сначала проходит как compare/backend bakeoff.

## 6. Recommended Next Backend Candidate

`Qwen-Image-Layered` потенциально полезен как:

- layered decomposition backend;
- draft `plateStack` generator;
- candidate source for richer RGBA layers.

Но не как замена:

- `cameraSafe`
- `plate z / depth priority`
- deterministic export contracts
- final render gating

То есть правильное место для него:

- `parallel recon`
- потом `controlled bakeoff`
- потом optional adapter into `plateStack draft`

## 7. Exit Criteria for RC1

`RC1` считается готовым, когда:

- contracts frozen and documented;
- gated export batch repeatable;
- final render presets implemented;
- regression summary exists with pass/caution/fail labels;
- runbook and release notes exist;
- end-to-end smoke run produces linked artifacts.

## 8. Out of Scope for Release V1

Вне release-v1 остаются:

- full plate decomposition redesign;
- complete `global depth` vs `plate-local depth` split;
- plate atmosphere/blur controls;
- full semantic judge expansion;
- `V-JEPA 2` luxury track;
- direct production integration into wider VETKA UI.
