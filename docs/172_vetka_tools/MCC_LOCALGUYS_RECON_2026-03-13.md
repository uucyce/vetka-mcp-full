# MCC Localguys Recon

Дата: 2026-03-13

Маркер: `MARKER_172.LOCALGUYS.MCC.RECON.V3`

## Update after implementation

Ниже основной рекон остаётся полезным как снимок исходного состояния, но после имплементации в этом же дне фактическая картина уже лучше:

- В `workflow_contract` теперь реально есть:
  - `execution_mode`
  - `write_opt_ins`
  - `verification_target`
  - `max_turns`
  - `idle_nudge_template`
  - `stage_tool_policy`
- В `mcc_local_run_registry` уже есть structured telemetry:
  - `recommended_tools`
  - `filtered_tool_schemas`
  - `idle_turn_count`
  - `verification_passed`
- В task context packet и `MiniStats` уже выведен `localguys_compliance`, то есть MCC теперь показывает:
  - sandbox mode
  - write gates
  - verification target
  - max turns
  - active-step allowed tools
  - telemetry state
- На boundary `PATCH /api/mcc/localguys-runs/{run_id}` уже есть реальный runtime enforcement:
  - `used_tools` валидируется против `stage_tool_policy`
  - `write_attempts` валидируется против `write_opt_ins`
  - `turn_increment` валидируется против `max_turns`
  - ответы MCC теперь возвращают `runtime_guard`

То есть главный оставшийся gap уже не в отсутствии policy-полей, а в следующем слое: кто и как будет системно генерировать эти lifecycle signals из настоящего local-model loop.

## Что реально есть в коде

- В MCC есть отдельный localguys-контур:
  - запуск playground и run lifecycle живут в `src/api/routes/mcc_routes.py`;
  - runtime-состояние и артефакты живут в `src/services/mcc_local_run_registry.py`;
  - UI-обзор run/benchmark уже показывается в `client/src/components/mcc/MiniStats.tsx`;
  - operator CLI существует в `scripts/localguys.py`.
- Есть реальные workflow families:
  - `g3_localguys`
  - `ralph_localguys`
  - `quickfix_localguys`
  - `testonly_localguys`
  - `docs_localguys`
  - `research_localguys`
  - `dragons_localguys`
  - `refactor_localguys`
  - `bmad_localguys`
- Есть реальный API:
  - `GET /api/mcc/workflow-contract/{workflow_family}`
  - `GET /api/mcc/localguys/operator-methods`
  - `GET /api/mcc/localguys/benchmark-summary`
  - `POST /api/mcc/tasks/{task_id}/localguys-run`
  - `GET /api/mcc/tasks/{task_id}/localguys-run`
  - `PATCH /api/mcc/localguys-runs/{run_id}`
  - `PUT /api/mcc/localguys-runs/{run_id}/artifacts/{artifact_name}`

## Что является source of truth

- Не шаблоны в `data/templates/workflows/*_localguys.json`.
- И не `task_board.json`.
- Реальный source of truth для localguys-политики сейчас это динамический `workflow_contract`, который собирается в `src/api/routes/mcc_routes.py` через `_build_localguys_contract(...)`.

Это важно, потому что шаблоны `*_localguys.json` содержат только metadata про family/roles/policy и пустые `nodes`/`edges`. Они не задают:
- `allowed_tools`
- `write_opt_ins`
- `verification_target`
- `idle_nudge_template`

## Что уже хорошо соответствует playbook

### 1. Песочница и изоляция

- Контракт явно включает `sandbox_policy.mode = "playground_only"`.
- Есть обязательный playground binding:
  - `requires_playground = true`
  - `requires_branch = true`
  - `allow_main_tree_write = false`
  - `lock_to_playground_id = true`
- Это соответствует идее playbook: локальные модели не должны писать в основное дерево по умолчанию.

### 2. Staged workflow уже есть как форма

- У каждого family есть явный список `steps`.
- Примеры:
  - `quickfix_localguys`: `recon -> execute -> verify -> review -> finalize`
  - `g3_localguys`: `recon -> plan -> execute -> verify -> review -> finalize`
  - `bmad_localguys`: `recon -> research -> plan -> execute -> verify -> review -> approve -> finalize`
- То есть MCC уже мыслит localguys не как один большой prompt, а как stage-based runtime contract.

### 3. Runtime и артефакты уже валидируются

- Run registry хранит:
  - `status`
  - `current_step`
  - `active_role`
  - `playground_id`
  - `branch_name`
  - `artifact_manifest`
  - `metrics`
- При переводе run в `done` MCC блокирует завершение, если обязательные артефакты не записаны.
- Это полезная и уже рабочая safety-рамка.

### 4. Local-model policy уже частично формализована

- В `workflow_contract` уже есть:
  - `model_policy`
  - `tool_budget`
  - `allowed_tools`
  - `completion_policy`
  - `operator_method`
  - `local_model_catalog`
- Для local моделей отдельно есть тесты на defaults и reflex decay profiles.

## Что в доках/playbook пока НЕ реализовано или реализовано не полностью

### 1. Нет явных `write_opt_ins` в localguys contract

- Playbook требует явные write gates вроде:
  - `_allow_task_board_writes`
  - `_allow_edit_file_writes`
- В MCC localguys contract сейчас этого поля нет.
- Есть sandbox policy и allowed_tools, но нет отдельного машиночитаемого блока, который говорит:
  - можно ли писать в task board;
  - можно ли редактировать файлы;
  - можно ли только читать.

Это главный gap между текущим MCC и playbook.

### 2. Нет `verification_target` и `idle_nudge_template`

- Playbook рекомендует для локальных моделей явный workflow contract с:
  - `verification_target`
  - `max_turns`
  - `idle_nudge_template`
- В текущем localguys contract этого нет.
- Есть `tool_budget` по шагам, но нет явной инструкции для runtime orchestration loop, как вести себя при idle или что считать обязательной верификацией помимо артефактов.

### 3. Нет доказательства, что MCC boundary нормализует tool-call payload между turns

- Playbook отдельно требует нормализацию tool call объектов и rehydrate аргументов.
- В localguys MCC-контуре сейчас есть:
  - contract;
  - run lifecycle;
  - artifact validation;
  - operator method catalog.
- Но в этом контуре не видно реализации многотуровой нормализации tool-call objects.
- Эта часть, вероятно, остаётся на стороне общих `llm_call_*` инструментов и пока не закреплена как localguys-specific boundary contract.

### 4. Текущая телеметрия уже полезна, но ещё не playbook-grade

- Сейчас в UI и packet реально видно:
  - status
  - current_step
  - active_role
  - runtime
  - artifact counts
  - recent runs
- Но пока не логируются как first-class поля:
  - filtered tool schemas
  - recommended tools from REFLEX
  - idle turns / nudge count
  - verification target result as отдельный structured field

### 5. Шаблоны `*_localguys.json` сейчас не являются полноценными executable contracts

- Они полезны как registry/family descriptors.
- Но нельзя считать, что именно в них уже зашиты все playbook-политики.
- Поэтому рекомендация "дописать всё в templates" была бы неточной.
- Правильнее: templates + dynamic workflow_contract должны быть синхронизированы, но runtime source of truth сейчас в `mcc_routes.py`.

## Что полезно в playbook именно для MCC

- Сохранять localguys как короткие state machines, а не как один оркестрационный prompt.
- Держать write access за явными opt-ins.
- Привязывать runtime к playground-only execution.
- Явно описывать verification contract.
- Узко ограничивать инструменты на шаг, а не только на workflow целиком.

## Что может быть вредно, если применить слишком буквально

- Совет "максимально сузить инструменты всегда" нельзя переносить в MCC без оговорок.
- В MCC уже есть изолированный playground. Поэтому абсолютный запрет на более широкий tool surface может повредить `research_localguys`, `docs_localguys`, `bmad_localguys`, где нужны разные роли и разные этапы.
- Правильный подход для MCC:
  - не один глобальный сверхузкий allowlist;
  - а stage-specific policy внутри sandbox.

## Практические выводы

1. MCC localguys уже рабочие как sandboxed run-system с контрактами, ролями, шагами и обязательными артефактами.
2. MCC ещё не довёл localguys до полной дисциплины playbook.
3. Основной недостающий слой:
   - `write_opt_ins`
   - `verification_target`
   - `idle_nudge_template`
   - richer telemetry
   - stage-specific tool policy
4. Первый правильный шаг не в переписывании шаблонов, а в усилении dynamic `workflow_contract` в `mcc_routes.py`.

## Рекомендованный порядок имплементации

### P1
- Добавить в `workflow_contract` поля:
  - `write_opt_ins`
  - `verification_target`
  - `max_turns`
  - `idle_nudge_template`
  - `stage_tool_policy`

### P2
- Добавить structured telemetry в run registry:
  - `recommended_tools`
  - `filtered_tool_schemas`
  - `idle_turn_count`
  - `verification_passed`

### P3
- Прокинуть эти поля в MCC UI:
  - `MiniStats`
  - task context packet
  - future drill-down/localguys panels

### P4
- После этого уже синхронизировать metadata в `data/templates/workflows/*_localguys.json`, чтобы family descriptors не отставали от runtime contract.
