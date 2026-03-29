# Parallax Object-Centric Parallax Architecture

Дата фиксации: `2026-03-28`
Статус: `reconstructed after merge-loss incident`

## 1. Purpose

Этот документ фиксирует архитектурный вектор для следующего этапа `photo_parallax_playground`.

Он не заменяет:

- `PARALLAX_ARCHITECTURE_RELEASE_V1_2026-03-18.md`
- `PARALLAX_EXPLICIT_LAYER_EXTRACTION_ARCHITECTURE_2026-03-27.md`
- `PARALLAX_ROADMAP_RC1_COMPLETION_AND_LAYERED_BAKEOFF_2026-03-19.md`

Его задача уже более узкая:

- объяснить, почему текущий следующий шаг не должен быть монолитным `background cleanup`;
- зафиксировать переход к `scene routing + object-centric cleanup + lightweight human steering`;
- дать архитектурную рамку для viewer-first UI и будущих adapter layers.

## 2. Factual Context

На `2026-03-28` подтверждено следующее:

- release path остаётся deterministic и gated;
- `Qwen Plate Planner` и `Qwen Plate Gate` уже существуют в release/recon контуре;
- `cameraSafe.warning` и `cameraSafe.suggestion` уже считаются частью safety layer;
- `hover-politsia` остаётся главным доказательством того, что одного depth-first remap недостаточно;
- `Qwen-Image-Layered` рассматривается как `accelerator`, а не как замена текущей архитектуры.

Это означает:

- проблема сложных сцен не сводится к одной "лучшей модели";
- главный разрыв находится в orchestration между scene class, object decomposition, cleanup policy и camera-safe render.

## 3. Core Observation

Для сложных сцен универсальной "отмычки" не видно.

Это подтверждается текущими артефактами и bakeoff-направлением:

- разные сцены и разные plate relationships ломаются по-разному;
- одна и та же cleanup стратегия не даёт одинаково хороший результат для subject edges, background recovery и atmosphere;
- safety, cleanup и scene semantics не должны быть спаяны в одну неразличимую эвристику.

Следовательно, правильный вектор:

1. сначала распознать класс сцены;
2. затем выбрать cleanup/routing policy;
3. затем работать на уровне отдельных объектов или слоёв;
4. при необходимости давать оператору 2-3 high-leverage control points.

## 4. Object-Centric Model

Объектно-центричная интерпретация сцены означает, что система работает не только с общим foreground/background split, а с сущностями, которые имеют:

- `role`
- `coverage`
- `depth band`
- `parallax strength`
- `motion damping`
- `cleanup variant`
- `target plate`
- transition relationship с соседними объектами

Текущая plate-aware модель уже частично даёт эту форму через:

- `plateStack`
- `PlateAwareLayoutContract`
- `cameraSafe.riskyPlateIds`
- `transitions`
- `special-clean` plates

Следующий шаг не в том, чтобы выбросить plates, а в том, чтобы трактовать их как object/layer units, а не просто как render slabs.

## 5. Scene Routing

Сцены должны маршрутизироваться не одним универсальным режимом, а по классу сцены.

Практически полезные классы, уже использованные в playground/UI logic:

- `portrait_close`
- `single_subject`
- `group_midshot`
- `wide_scene`
- `synthetic_ai_scene`

Архитектурный смысл:

- `portrait_close`
  - приоритет на subject edge fidelity и быстрый операторский path
- `single_subject`
  - можно оставлять компактный flow с минимальным ручным steering
- `group_midshot`
  - нужен более аккуратный role assignment и transition awareness
- `wide_scene`
  - выше риск background pressure, atmosphere collisions и camera-safe drift
- `synthetic_ai_scene`
  - отдельный сложный класс, потому что boundary behavior и semantic stability часто хуже

## 6. Cleanup Policy

Cleanup policy должен выбираться не глобально, а относительно выбранного объекта или plate.

Минимальные типы policy, которые уже согласуются с текущими фактами:

- protect-region policy
- silhouette-refine policy
- depth-band tuning
- role reassignment
- `special-clean` routing для hero-object removals

Это важно, потому что текущие hard cases различаются:

- где-то проблема в edge fidelity;
- где-то в том, что plate получил неправильную semantic role;
- где-то в transition risk;
- где-то в hole-fill/clean target behind foreground object.

## 7. Human-In-The-Loop

Человек не должен исчезать из системы, но и не должен получать монтажный комбайн.

Правильная роль человека здесь:

- подтвердить или поправить routing;
- защитить критичный регион;
- уточнить силу cleanup в нескольких high-leverage точках.

Из этого следует продуктовый инвариант:

- UI не должен прятать человека;
- UI не должен превращаться в full CUT dockview;
- playground должен брать только inspector/adapter patterns, а не тащить целый shell.

## 8. Qwen-Image-Layered Position

`Qwen-Image-Layered` вписывается в эту архитектуру как upstream module, но не как архитектурная замена.

Корректные места для него:

- object/layer proposal
- layered candidate generation
- special-clean hint generation
- compare lane внутри bakeoff

Некорректные ожидания:

- "Qwen отменит scene routing"
- "Qwen сам заменит object-centric cleanup"
- "Qwen делает deterministic gating ненужным"

## 9. Product Invariants

Эти инварианты нельзя терять в следующих итерациях:

- viewer-first layout важнее debug richness;
- UI должен быть step-based;
- сложные сцены требуют scene routing, а не одного универсального режима;
- `synthetic_ai_scene` считается отдельным сложным классом;
- `Qwen-Image-Layered` усиливает текущий вектор, а не подменяет его;
- inspector/adapter patterns можно переносить из CUT-мышления, но не весь CUT shell.

## 10. Immediate Architectural Consequences

Из этого документа прямо следует:

1. Playground UI должен показывать main path как:
   - `Input -> Extract -> Camera -> Export`
2. Object/layer thinking должен жить в компактном operator layer:
   - inspector
   - routing summary
   - assist recommendations
3. Advanced/manual tooling не должно сидеть в default path.
4. Следующие integration steps должны быть раздельными:
   - docs
   - viewer-first UI refactor
   - plate-aware assist mapping
   - future Qwen compare lane

## 11. Reconstruction Note

Этот документ восстановлен после merge-loss инцидента, в котором файл отсутствовал во всех ветках и не мог быть возвращён из git history.

Поэтому здесь зафиксированы:

- только уже подтверждённые архитектурные факты из существующих canonical docs и этой рабочей сессии;
- только те design proposals, которые прямо следуют из этих фактов.
