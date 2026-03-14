# PHASE 164 — MYCO + Architect UI Instruction Coverage Recon (2026-03-07)

Status: `RECON+markers` complete.  
Protocol step: `REPORT` (waiting explicit `GO` before `IMPL NARROW`).

## 0) Input Scope (from user)
1. Провести полный аудит всех UI окон/кнопок MCC (кроме DEV панели) и проверить: умеет ли MYCO объяснить "что делать" для каждого элемента.
2. Синхронизировать это знание на два уровня архитектора:
- Project Architect (`tab/playground`)
- Task Architect (task-level)
3. Поддержать общий кодовый базис (MYCO + Architects), но с role-aware расхождением поведения.

## 1) Linked Previous Roadmaps / Contracts
- [PHASE_162_MYCO_HELPER_ARCH_PLAN_2026-03-05.md](/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/docs/162_ph_MCC_MYCO_HELPER/PHASE_162_MYCO_HELPER_ARCH_PLAN_2026-03-05.md)
- [PHASE_162_P4_P5_RUNTIME_SCENARIO_MATRIX_IMPL_REPORT_2026-03-07.md](/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/docs/162_ph_MCC_MYCO_HELPER/PHASE_162_P4_P5_RUNTIME_SCENARIO_MATRIX_IMPL_REPORT_2026-03-07.md)
- [PHASE_162_P4_P3_MYCELIUM_CAPABILITY_RAG_IMPL_REPORT_2026-03-07.md](/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/docs/162_ph_MCC_MYCO_HELPER/PHASE_162_P4_P3_MYCELIUM_CAPABILITY_RAG_IMPL_REPORT_2026-03-07.md)
- [MYCO_AGENT_INSTRUCTIONS_GUIDE_V1_2026-03-06.md](/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/docs/161_ph_MCC_TRM/MYCO_AGENT_INSTRUCTIONS_GUIDE_V1_2026-03-06.md)
- [MYCO_SVG_ICON_GUIDE_V1.md](/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/docs/163_ph_myco_VETKA_help/MYCO_SVG_ICON_GUIDE_V1.md)
- [IMPL_MYCELIUM_STREAM_TO_CONTEXT.md](/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/docs/174_ph/IMPL_MYCELIUM_STREAM_TO_CONTEXT.md)
- [MYCO_HELP_RULES_LIBRARY_V1.md](/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/docs/162_ph_MCC_MYCO_HELPER/MYCO_HELP_RULES_LIBRARY_V1.md)
- [MYCO_CONTEXT_PAYLOAD_CONTRACT_V1.md](/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/docs/162_ph_MCC_MYCO_HELPER/MYCO_CONTEXT_PAYLOAD_CONTRACT_V1.md)
- [MARKER_155_MCC_ARCHITECTURE_REDUX.md](/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/docs/154_ph/MARKER_155_MCC_ARCHITECTURE_REDUX.md)
- [CODEX_UNIFIED_DAG_MASTER_PLAN.md](/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/docs/155_ph/CODEX_UNIFIED_DAG_MASTER_PLAN.md)

## 2) UI Surface Map (non-DEV)
### 2.1 Core Windows
- `MiniTasks` (`windowId=tasks`): active task, run/start, heartbeat control.
- `MiniChat` (`windowId=chat`): architect chat + MYCO mode + quick context roundtrip.
- `MiniStats` (`windowId=stats`): scope metrics + reinforcement diagnostics.
- `MiniBalance` (`windowId=balance`): selected key/provider/model accounting.
- `MiniContext` (`windowId=context`): node/task/agent/file context + model/preprompt controls.
- `MiniWindowDock`: collapsed window restore, includes MYCO restore animation path.

### 2.2 Graph Interaction Surfaces
- DAG canvas (`DAGView`): select, double-click drill, inline workflow unfold.
- Context menus (`DAGContextMenu`): canvas/node/edge actions (add/update/delete/link/anchor).
- Task overlay nodes (`task_overlay_*`) and workflow inline nodes (`wf_*`, `rd_*`).

### 2.3 Top Bar Surfaces
- MYCO avatar + top hint capsule (`helperMode=off`).
- Project tabs row (`project`, `+project`).
- Window title `MYCELIUM`.

## 3) Coverage Matrix (Current)
Legend: `OK` = stable; `PARTIAL` = есть, но неполно; `GAP` = отсутствует/несвязано.

1. Top MYCO hint for node/task/workflow states: `PARTIAL`
- Есть сценарии drill/workflow/agent.
- Нет полного каталога "кнопка/действие/ожидаемый результат" по каждому UI элементу.

2. Chat MYCO contextual guidance: `PARTIAL`
- Есть proactive context changes.
- Недостаточно глубины для полного operator guide по всем контролам.

3. Architect parity (project vs task): `GAP`
- Нет явного единого role-aware instruction-core с разделением уровней.
- Сейчас много логики в MYCO ветке, архитекторы не гарантированно наследуют тот же capability-map.

4. UI-element-to-guidance traceability: `GAP`
- Нет детального документа "UI element -> intent -> next action -> allowed tools".

5. Context payload sufficiency for role-specific coaching: `PARTIAL`
- Пейлоад богатый (`nav_level`, `node_kind`, `task_drill_state`, `workflow_family`, etc).
- Не хватает нормализации в единый state key для shared MYCO/Architect instruction retrieval.

## 4) Root Cause Summary
1. Инструкции есть, но сейчас распределены по нескольким файлам и не сведены в детальную UI-карту.
2. Proactive слой построен вокруг `buildMycoReply(...)`, но без полного action-catalog на каждую кнопку/окно.
3. Architect path и MYCO path не используют общий детальный "role-aware instruction core" как единый контракт.

## 5) Markers (Phase 164)
1. `MARKER_164.P0.UI_SURFACE_FULL_MAP.V1`
2. `MARKER_164.P0.MYCO_UI_ACTION_CATALOG.V1`
3. `MARKER_164.P0.MYCO_UI_COVERAGE_MATRIX.V1`
4. `MARKER_164.P1.SHARED_ROLE_AWARE_INSTRUCTION_CORE.V1`
5. `MARKER_164.P1.PROJECT_ARCH_GUIDANCE_BIND.V1`
6. `MARKER_164.P1.TASK_ARCH_GUIDANCE_BIND.V1`
7. `MARKER_164.P1.CONTEXT_TOOLS_HINT_INJECTION.V1`
8. `MARKER_164.P2.NODE_SUBNODE_AGENT_ROLE_PLAYBOOK.V1`
9. `MARKER_164.P2.WORKFLOW_SWITCH_GUIDE_MATRIX.V1`
10. `MARKER_164.P2.RUN_RETRY_TRIGGER_GUIDE_MATRIX.V1`
11. `MARKER_164.P3.PROACTIVE_RULE_ENGINE_STATE_NORMALIZATION.V1`
12. `MARKER_164.P3.NOISE_GUARD_AND_DEDUPE_POLICY.V1`

## 6) Narrow Implementation Plan (pending GO)
### 164-P0 (docs/contracts only)
1. Собрать полный UI inventory (окна, кнопки, контекстные меню, hot-actions).
2. Для каждого элемента добавить:
- purpose
- prerequisites
- user action
- system reaction
- MYCO short hint
- Architect detailed hint (project/task variants)
- allowed tools/skills

### 164-P1 (shared instruction core)
1. Вынести общий instruction-core в shared структуру (`base + role overlays`).
2. Подключить к:
- `helper_myco`
- `architect` project-level
- `architect` task-level
3. Добавить role-aware retrieval key normalization.

### 164-P2 (scenario depth)
1. Node/subnode/agent detailed scenario pack.
2. Workflow family matrix (Dragon/Titan/G3/Ralph/Custom) как guidance overlays.
3. Run/retry/heartbeat guidance synchronization with Tasks/Context/Stats.

### 164-P3 (proactive hardening)
1. Dedupe and priority policy for proactive messages.
2. Strict gating by `navLevel + drillState + nodeKind + role`.
3. Prevent roadmap fallback hints when workflow already open.

### 164-P6
Delegated to another agent (icon/avatar animation track). Excluded from this roadmap branch.
Future implementation for this delegated track must conform to `MYCO_SVG_ICON_GUIDE_V1.md`.

### 164-P7
Linked downstream dependency: stream/reflex events must surface inside node Context/Stream surfaces, not only in DevPanel/mini log.
Future implementation for this track must conform to `IMPL_MYCELIUM_STREAM_TO_CONTEXT.md`.
Reason: MYCO/Architect guidance quality depends on rich node-local activity visibility, especially reflex metadata and pipeline progress context.

## 7) Verification Plan (pending GO)
1. Contract tests for UI coverage matrix completeness.
2. Prompt/retrieval tests for role overlays (MYCO vs Project Architect vs Task Architect).
3. Scenario tests (roadmap->workflow->agent->run/retry) for proactive correctness.
4. Regression tests: no helper leakage in architect-only mode.

## 8) Gate
`REPORT` delivered.

Next protocol step: `WAIT GO`.
