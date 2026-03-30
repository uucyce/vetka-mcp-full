# Parallax Roadmap RC1 Completion And Layered Bakeoff

Дата фиксации: `2026-03-19`

## 1. Purpose

Этот roadmap заменяет старое чтение backlog через TaskBoard для текущего этапа.

Он нужен как operational plan для двух связанных целей:

- довести текущий `RC1` путь от `caution` к максимально стабильному `pass`;
- встроить `Qwen-Image-Layered` как альтернативный decomposition backend внутри gated pipeline, не ломая release path.

Жёсткая интерпретация:

- `export success` и `batch pass` считаются только engineering readiness;
- они не считаются достаточным основанием для product deploy;
- release hardening закрыт только тогда, когда export path не подменяет depth-first сущность продукта.

## 2. Planning Mode For Current Phase

Пока TaskBoard мигрирует на `SQLite`, этот документ считается главным execution plan для `parallax`.

Правило:

- planning идёт по этому roadmap;
- source of truth по архитектуре идёт через `PARALLAX_ARCHITECTURE_RELEASE_V1_2026-03-18.md`;
- continuity идёт через `HANDOFF_TO_FRESH_CHAT_RC1_2026-03-19.md`;
- contract changes сначала отражаются в `photo_parallax_playground/CONTRACTS_V1.md`.

Дополнительная continuity note после `2026-03-29`:

- product-facing UI reset и pro-app mental model correction зафиксированы в `PARALLAX_PRODUCT_UI_RESET_PROJECT_2026-03-29.md`;
- viewer-first refactor остаётся валидным, но теперь должен оцениваться не только по структуре, а по operator readability against pro-tool references.

## 3. Current State

На момент `2026-03-19`:

- release backlog `RC1` закрыт;
- canonical smoke path работает;
- current verdict = `pass`;
- factual batch profile:
  - `pass = 3`
  - `caution = 0`
  - `fail = 0`
- latest completion result:
  - export/layout path auto-applies `cameraSafe.suggestion` for risky scenes
  - `plate_layout.json` stores requested vs effective motion in `cameraSafe.adjustment`
  - current canonical set completes with `attempts = 1`

Canonical smoke command:

```bash
bash /Users/danilagulin/Documents/VETKA_Project/vetka_live_03/scripts/photo_parallax_qwen_gated_multiplate_flow.sh \
  hover-politsia keyboard-hands truck-driver
```

Canonical artifacts:

- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/output/render_compare_qwen_gated_multiplate/gated_batch_qa_summary.json`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/output/render_compare_qwen_gated_multiplate/regression_quality_summary.json`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/output/render_compare_qwen_gated_multiplate/render_compare_qwen_multiplate_summary.json`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/output/render_compare_qwen_gated_multiplate/compare_batch_sheet.png`

## 4. North Star

Нужна система с двумя дорожками:

1. `Release path`
- deterministic;
- contract-frozen;
- gated;
- repeatable by smoke.

2. `Alternative layered backend`
- experimental but measurable;
- работает через adapter;
- сравнивается против release path;
- может встраиваться в тот же gated pipeline без прямой замены release logic.

И дополнительное жёсткое правило:

- technical `pass` не считается достаточным без visual acceptance против known-good baseline.
- successful export не считается признаком того, что “всё готово”.

## 5. Execution Tracks

Работа делится на четыре трека:

### Track A. RC1 Completion

Цель:

- убрать текущие release blockers;
- перевести статус из `caution` в `pass` там, где это возможно без unsafe policy drift.

### Track B. Release Hardening

Цель:

- сделать smoke repeatable;
- убрать скрытые anti-flake причины;
- зафиксировать diagnostics и acceptance rules.
- вернуть visual acceptance как обязательную часть release evaluation.
- отделить `export readiness` от `product readiness` в явном виде.

Текущий supporting tool:

- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/scripts/photo_parallax_build_visual_acceptance_pack.py`
- он собирает:
  - `visual_acceptance_summary.json`
  - `visual_acceptance_checklist.md`
  из `review`, `plate export`, `render summary` и `compare summary` артефактов.

### Track C. Layered Backend Bakeoff

Цель:

- интегрировать `Qwen-Image-Layered` как compare/backend lane;
- не трогать current release path как default.
- держать открытой future comparative lane для candidate matting backends, если они понадобятся для cleanup/refinement:
  - `SAM 2 + PyMatting`
  - `BiRefNet`
  - `RMBG`

Важно:

- это не принятый стек;
- это candidate lane для последующего recon на наших hard samples;
- сравнение должно идти как controlled bakeoff, а не как silent roadmap pivot.

### Track D. Refactor And Separation

Цель:

- продолжить снижать зависимость от большого `App.tsx`;
- отделить orchestration/adapters от UI without behavior drift.

## 6. Ordered Roadmap

Порядок исполнения строгий:

1. `Track A` уже закрыт на текущем canonical set.
2. Затем зафиксировать `Track B`.
3. После этого открыть `Track C`.
4. `Track D` делать только так, чтобы он не тормозил `A/B/C`.

## 7. Track A — RC1 Completion

### A1. Pinpoint Current Caution Logic

Что сделать:

- проверить точные правила `cameraSafe` и `cameraSafeOk`;
- отделить policy blockers от purely numeric blockers;
- выписать, что именно делает sample `caution`.

Главные места:

- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/src/lib/plateLayout.ts`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/src/lib/metrics.ts`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/src/App.tsx`

Done criteria:

- по каждому canonical sample есть короткое объяснение, почему он не `pass`;
- понятно, это tuning issue или policy issue.

### A2. Auto-Apply Or Semi-Auto-Apply Camera-Safe Suggestion

Что сделать:

- использовать `cameraSafe.suggestion` не только как debug output;
- подставлять tighter travel и/или safer overscan до export/render;
- оставить traceable evidence, какой adjustment был применён.

Минимальный результат:

- если scene считается risky, pipeline не только предупреждает, а пытается уйти в safer preset автоматически.

Done criteria:

- в artifacts видно исходное и итоговое safe-adjusted решение;
- на canonical smoke уменьшается число `camera-safe` cautions.

### A3. Scene-Specific Motion Caps

Что сделать:

- ввести caps по travel amplitude для difficult scenes;
- опираться на snapshot/risk metrics, а не на ручной guess;
- не ломать current preset structure `quality/web/social`.

Done criteria:

- для wide/background-heavy сцен travel становится предсказуемо безопаснее;
- не появляется новый visual collapse на portrait-like scenes.

### A4. Overscan Policy Tightening

Что сделать:

- проверить минимумы overscan, из-за которых `cameraSafeOk` чаще всего падает;
- решить, где нужен policy shift, а где достаточно preprocessing/tuning;
- не допустить фальшивого `pass` через ослабление safety semantics.

Done criteria:

- `cameraSafeOk` становится достижимым на canonical set или документируется, почему нет;
- если policy меняется, это явно отражено в contracts/docs.

### A5. RC1 Re-Smoke

Что сделать:

- прогнать canonical smoke после каждого meaningful safety change;
- сравнить старые и новые summaries;
- не принимать subjective “looks better” без artifact delta.

Done criteria:

- новый smoke produce linked artifacts;
- есть чёткий delta-report:
  - previous caution reasons
  - current caution/pass reasons

Status on `2026-03-19`:

- completed on canonical set;
- batch summaries now show `pass = 3`, `caution = 0`, `fail = 0`.

## 8. Track B — Release Hardening

### B1. Readiness Retry Audit

Что сделать:

- разобраться, почему readiness иногда требует больше одного poll;
- отделить normal async latency от real flaky behavior;
- если нужно, сделать deterministic retry budget и clearer diagnostics.

Главные evidence files:

- `plate_export_readiness_diagnostics.json`
- `gated_batch_qa_summary.json`

Done criteria:

- readiness behavior объясним и стабилен;
- `attempts > 1` либо исчезает, либо перестаёт считаться ambiguous blocker при корректной готовности.

### B2. Aggregation Logic Audit

Что сделать:

- найти код/script, который собирает batch-level `overall_status`;
- проверить, не живёт ли финальный verdict policy вне playground без документации;
- выровнять docs с реальной aggregation logic.

Done criteria:

- известно, где exactly рождается `overall_status`;
- verdict logic документирована и воспроизводима.

### B3. Regression Pack Hard Freeze

Что сделать:

- зафиксировать, какие artifacts обязательны для acceptance;
- проверить, что evidence paths не дрейфуют;
- убрать implicit assumptions из runbook.

Done criteria:

- RC1 acceptance опирается на фиксированный список JSON/PNG артефактов;
- новый чат может проверить состояние без восстановления длинной истории.

### B4. Acceptance Policy

Что сделать:

- явно определить, что считается release-grade `pass`;
- отдельно определить, когда допустим `caution`;
- отделить engineering caution от product caution.

Done criteria:

- есть короткая policy-table в docs;
- команда понимает, надо ли добиваться `3/3 pass` или допустим controlled `caution`.

### B5. Visual Regression Gate

Что сделать:

- зафиксировать March 12 success path как visual baseline;
- перестать смешивать `review` artifacts и `render_preview_multiplate` artifacts как будто это один и тот же success class;
- добавить explicit review question:
  - виден ли layered parallax space,
  - или картинка выглядит как proxy/focus cutout.

Baseline references:

- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/output/review`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/output/layered_edit_flow`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/output/custom_renders`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/docs/180_photo-to-parallax/PARALLAX_VISUAL_FORENSIC_2026-03-19.md`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/docs/180_photo-to-parallax/PARALLAX_LAYER_SPACE_RECOVERY_PLAN_2026-03-19.md`

Done criteria:

- есть documented visual baseline;
- current render path проверяется не только JSON verdict, но и against visual regression questions;
- oval/proxy cutout look считается blocker, даже если batch summary = `pass`.

### B6. Camera Geometry Recovery

Что сделать:

- перевести renderer с heuristic motion на camera-based model;
- привязать `distance / lens / mm / FOV` к явным формулами, а не к тюнингу на глаз;
- калибровать поведение against AE reference project.

Canonical reference:

- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/docs/180_photo-to-parallax/PARALLAX_CAMERA_GEOMETRY_AND_LENS_RESEARCH_2026-03-19.md`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/docs/180_photo-to-parallax/PAVEL_AE_REFERENCE_WORKFLOW_2026-03-13.md`

Связанные задачи:

- `tb_1773892185_4` — camera-based parallax model
- `tb_1773892186_5` — focal length / lens calibration against AE

Done criteria:

- renderer использует explicit camera parameters;
- depth участвует в motion как `depth -> Z -> projection displacement`;
- lens behavior и distance math больше не живут как undocumented heuristics.

## 9. Track C — Qwen-Image-Layered Bakeoff

### C1. Adapter-First Integration

Что сделать:

- не встраивать `Qwen-Image-Layered` прямо в final stack;
- завести adapter:
  - `model layers -> normalized layer candidates -> draft plate families -> draft plateStack`

Ожидаемые outputs:

- `draft_plate_stack.json`
- `layer_rgba/*.png`
- `layer_order_candidates.json`
- `layer_coverages.json`

Done criteria:

- model output можно сравнивать с current gated stack на одинаковых сценах.

### C2. Controlled Bakeoff Set

Что сделать:

- выбрать `3-6` complex scenes;
- прогнать layered output side-by-side против current stack;
- не смешивать bakeoff samples с release smoke verdict без отдельной метки.
- если cleanup quality снова станет bottleneck, завести отдельный sub-lane для matting candidates:
  - `SAM 2 + PyMatting`
  - `BiRefNet`
  - `RMBG`
  и сравнивать их только на сложных cleanup/alpha cases, а не объявлять заменой default path заранее.

Done criteria:

- для каждого sample есть compare evidence;
- понятно, где layered model выигрывает, а где дробит сцену слишком мелко.

### C3. Structural Gate For Layered Draft

Что сделать:

- ввести structural validation до render:
  - layer count sanity
  - fragmentation checks
  - order sanity
  - merge/downsample hints

Done criteria:

- layered draft не проходит в compare/render без базовой структурной валидации;
- noisy outputs не маскируются как success.

### C4. Gated Pipeline Hook

Что сделать:

- подключить layered draft как optional upstream backend в тот же gated pipeline;
- current release backend оставить default;
- сравнивать adapter output через existing compare/summaries.

Done criteria:

- `Qwen-Image-Layered` существует как alternative lane inside gated pipeline;
- release path не зависит от него.

### C5. Go/No-Go Decision

Что сделать:

- принять решение только после evidence:
  - improves object separation
  - reduces decomposition pain
  - does not explode fragmentation

Done criteria:

- зафиксировано одно из решений:
  - `keep as bakeoff-only`
  - `promote to optional draft backend`
  - `drop`

## 10. Track D — Refactor And Separation

### D1. App.tsx Orchestration Extraction

Что сделать:

- вынести оставшуюся release-critical orchestration logic из `App.tsx`;
- сохранить UI-facing API стабильным.

Первый кандидат на extraction:

- export/orchestration helpers
- debug/export API wiring
- backend adapter wiring

Done criteria:

- `App.tsx` перестаёт быть главным bottleneck for release-path edits;
- tests/build остаются зелёными.

### D2. Shared Service Boundaries

Что сделать:

- отделить:
  - safety/risk policy
  - plate contract building
  - bakeoff adapter logic
  - smoke summary helpers

Done criteria:

- future backend work не требует лезть в UI orchestration каждый раз.

## 11. Verification Matrix

Каждый meaningful change должен проверяться на четырёх уровнях:

### Level 1. Unit

- `npm test`
- targeted tests around `src/lib/plateLayout.ts`
- targeted tests around extracted services/adapters

### Level 2. Build

- `npm run build`

### Level 3. Smoke

- canonical RC1 smoke command

### Level 4. Artifact Review

- `gated_batch_qa_summary.json`
- `regression_quality_summary.json`
- `render_compare_qwen_multiplate_summary.json`
- `compare_batch_sheet.png`

### Level 5. Visual Review

- compare current `render_preview_multiplate*` outputs against March 12 review/custom baseline;
- проверить, что visible space is layered, not center-cut proxy motion;
- отдельно проверять:
  - whole-object coherence
  - background independence
  - absence of obvious oval/box cutout behavior

Правило:

- change не считается завершённым, если есть code diff, но нет artifact-level proof.
- release hardening не считается завершённым, если есть technical `pass`, но visual regression unresolved.

## 12. Exit Criteria

### Exit For RC1 Completion Phase

Фаза считается завершённой, когда:

- caution root causes разобраны и либо устранены, либо явно признаны policy decisions;
- canonical smoke стабилен;
- release verdict logic документирована;
- artifacts repeatable;
- roadmap не зависит от TaskBoard.

### Exit For Layered Bakeoff Phase

Bakeoff считается завершённым, когда:

- `Qwen-Image-Layered` встроен как optional alternative lane;
- adapter outputs и compare evidence существуют;
- принято `GO/NO GO` решение о дальнейшем использовании.

## 13. Immediate Next Actions

Следующий practical sequence:

1. Задокументировать batch aggregation logic для `overall_status`.
2. Зафиксировать acceptance policy теперь, когда canonical set вышел в `pass`.
3. Вернуть visual regression gate относительно March 12 success path.
4. Запустить `layer-space recovery` и вернуть upstream decomposition в центр системы.
5. Проверить, не держится ли `pass` на слишком synthetic/proxy-like layer generation.
6. После этого открыть adapter-first track для `Qwen-Image-Layered`.
7. Когда дойдём до cleanup/backend recon, отдельно оценить candidate matting lane (`SAM 2 + PyMatting`, `BiRefNet`, `RMBG`) на hard alpha samples без преждевременного выбора победителя.

## 14. Fresh Chat Rule

Если новый чат открывается в середине этой фазы, стартовать так:

1. `HANDOFF_TO_FRESH_CHAT_RC1_2026-03-19.md`
2. `PARALLAX_ARCHITECTURE_RELEASE_V1_2026-03-18.md`
3. `RELEASE_NOTES_V1_RC1_2026-03-19.md`
4. `PARALLAX_ROADMAP_RC1_COMPLETION_AND_LAYERED_BAKEOFF_2026-03-19.md`

Короткий prompt:

```text
Прочитай HANDOFF_TO_FRESH_CHAT_RC1_2026-03-19.md и продолжим parallax от текущего RC1 state. Текущий release backlog закрыт, canonical smoke работает, verdict = pass. Работаем без TaskBoard до завершения SQLite migration: сначала фиксируем release hardening и verdict policy, затем встраиваем Qwen-Image-Layered как alternative backend в gated pipeline и прогоняем bakeoff/tests.
```
