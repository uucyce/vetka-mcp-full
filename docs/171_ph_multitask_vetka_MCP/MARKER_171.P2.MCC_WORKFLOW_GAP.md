# MARKER_171.P2 — MCC workflow registry & enforcement gap
Date: 2026-03-12
Owner: Codex

## Олимпиада TaskBoard & MCC
- TaskBoard уже реализует историю (`status_history` → `src/orchestration/task_board.py`), proof (pipeline_stats.success + verifier hook + auto-close in `src/services/task_tracker.py` + `src/tools/git_tool.py`), `TaskBoard.auto_complete_by_commit`, и digest/quick-reply сигналы (`src/services/myco_memory_bridge.py` / `src/api/routes/chat_routes.py`). Он предоставляет `active/queued/failed` snapshot, prevents manual reopenings, и даже эмиттирует `task-board-updated` events для MCC/UI. Мультитаск-состав (active agents, claimed/running) уже отслеживается на витрине `MiniStats` и MCC board, поэтому gap лежит не в TaskBoard, а выше.
- MCC/TaskBoard/agent_pipeline связка уже отслеживает `playground` (sandbox) через `ProjectConfig`/`project/init` и `src/services/project_config.py` (disk quota, path guards). Задачи привязываются к workflow (через `_resolve_task_workflow_binding()`, `_select_heuristic_workflow_binding()` и `GET|PUT /api/mcc/tasks/{task_id}/workflow-binding`). Именно это многозадачное ядро у нас работает.

## Что ещё не доведено (MARKER_171.P2.MCC_WORKFLOW_GAP)
1. **Workflow registry (steps + tool budget)**
   - существующий католог возвращает только metadata/metrics (`/api/mcc/workflows`, `_normalize_workflow_catalog_row`). Нет централизованного контракта `workflow_family → {steps, allowed_files, tool_budget, model_policy, artifact_contract, failure_policy}`. Такой регистр нужен, чтобы мультитаск не дублировал recon, не спорил текстом и жёстко выполнял `recon → plan → execute → verify → report` (п.2 в Agent Answer).
2. **Pre-prompt / model sizing enforcement**
   - MiniContext показывает preprompt, и Reflex/`agent_pipeline` знают model profiles, но нет API/registry, который запускает заданную модель и заставляет её проходить step-by-step. Нужен `workflow_contract` (и `router` в MCC) c ограниченным набором tools и stop conditions; при несоблюдении — выставлять `BLOCKED` + reason в TaskBoard/metrics. Это ключ к управлению мультитаском.
3. **Sandbox/project observability + artifact contract**
   - `project_init` создаёт sandbox/tabs, но MCC пока не показывает, какой sandbox связан с конкретным workflow/task_id. Поэтому локальная модель не может сказать “я работаю в worktree X, commit Y”. Также нет стандарта, где лежат `facts.json`, `plan.json`, `patch.diff`, `test-output`. Без артефактов нет “proof” для мультитаска.
4. **Failure policy & verifier bridge**
   - TaskBoard уже имеет tracker и digest, но отсутствует `workflow_contract.failure_policy` (когда остановиться+эскалировать). Это нужно, чтобы мультитаск не повторял recon или забивал контекст. Верефай step должен переводить `task` в `done` только после успешных targeted tests и diff review — MCC/REFLEX должны видеть результат.

## Предложенные шаги
1. Добавить `data/workflow_registry.json` + API `GET /api/mcc/workflow-contract/{family}` и расширить `_resolve_task_workflow_binding`/workflow hint (`/api/mcc/workflow/myco-hint`) чтобы всегда отдавать `steps`, `tool_budget`, `model_policy`, `allowed_files`, `artifact_contract`, `failure_policy`, `sandbox_lock`.
2. Обновить MCC init/state response (`src/api/routes/mcc_routes.py:~420-540`) и фронт `MyceliumCommandCenter` чтобы `projectTabs`/`MiniContext` получали `workflow_contract` + `sandbox_id`. Повесить `workflow_contract` в `_build_workflow_catalog_payload` и фронт `MiniContext` (preprompt preview) — чтобы агент знал, какие модели, prompts и tools доступны для текущей задачи.
3. Использовать `reflex_routes` (`get_model_profile`, `ensure_model_profile`) для enforcement `model_policy` (например `max_params`, `tool_calls_per_phase`). Заставить `agent_pipeline` и MCC router возвратить JSON + human summary по шагам (как у Agent Answer). Если модель не укладывается или tools превышены — сразу `BLOCKED`.
4. Documentировать `artifact contract` (plan/report/patch/test outputs) и failure policy, чтобы Multitask MCC/TaskBoard мог показать “executor завершил `verify` → tests pass → digest updated; если fail — status=failed+reason, queue rebalancing). Можно привязать `feedback_service`/`REFLEX`.

## Маркер/связки
- `MARKER_171.P2.MCC_WORKFLOW_GAP` → doc (этот файл) описывает gap.
- `src/api/routes/mcc_routes.py` → `_build_workflow_catalog_payload`, `_resolve_task_workflow_binding`, `/task workflow binding`, `/project`/`/sandbox` endpoints, `workflow_myco_hint` (логика выбора tools).
- `client/src/components/mcc/MyceliumCommandCenter.tsx` → project tabs, `MiniContext`, `fetchDAG`, `workflow routing`, preprompt preview (уже видна, но нужна binding info). 
- `src/services/project_config.py` → `ProjectConfig.create_new`, `quota`, `sandbox status` (используется для worktree). 
- `src/services/reflex_decay.py`, `reflex_routes.py`, `agent_pipeline.py` → model profile registry, tool enforcement.

## Итог
- TaskBoard уже мультиагентный (status/history/proofs) — gap выше, на уровне workflow registry -> preprompt -> sandbox -> verifier.
- Чтобы канал `Router+Recon+Executor+Verifier` (Agent Answer) заработал, нужно добавить workflow contract, tool budgets, model policy, sandbox observability и artifact contracts, а MCC должен выдавать эти данные напрямую.
- Мультитаск в MCC/TaskBoard уже работает; теперь нужно его “привести под контракт”, чтобы локальные модели не спорили текстом, не дублировали recon и соблюдали preprompt/verify steps по `workflow_contract`.
