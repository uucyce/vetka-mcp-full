# Handoff — Local Qwen + Workflow REFLEX Enforcement

Date: 2026-03-14
Owner handoff: next agent (fresh chat)
Status: P6.2-P6.10 implemented, tests green on targeted suites

## 1) Что уже сделано

### A. Live local Qwen behavior (P6.2-P6.5)

- Подтвержден живой tool-behavior локальной Qwen через guarded tests:
  - repo search -> read
  - ownership claim/update через task board
  - remembered workflow recall
  - read/edit/test chain без рекурсивного LLM path
- Ключевой live файл:
  - `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/tests/test_phase173_p6_local_qwen_live_behavior.py`

### B. MYCELIUM presets + contracts (P6.6-P6.7)

- Добавлены и зафиксированы local presets:
  - `patchchain_localguys`
  - `ownership_localguys`
- Контракты доступны через MCC workflow-contract и operator-method surfaces.
- Ключевые файлы:
  - `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/data/templates/workflows/patchchain_localguys.json`
  - `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/data/templates/workflows/ownership_localguys.json`
  - `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/api/routes/mcc_routes.py`

### C. Import boundary fix for MCC route tests

- `src.api` и `src.api.routes` переведены на lazy router loading, чтобы импорт `mcc_routes` не тянул весь API стек.
- Файлы:
  - `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/api/__init__.py`
  - `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/api/routes/__init__.py`

### D. Workflow REFLEX boundary audit (P6.8)

- Зафиксирован и тестами закреплен путь:
  - `mycelium_execute_workflow` -> `vetka_execute_workflow` -> orchestrator/pipeline
- Audit тест:
  - `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/tests/test_phase173_mycelium_workflow_reflex_audit.py`

### E. Workflow-entry REFLEX enforcement parity (P6.9)

- В orchestrator добавлен preflight helper на входе в tool loop:
  - `maybe_apply_reflex_to_direct_tools(...)`
- Это убрало разрыв между direct path и workflow-entry path.
- Файл:
  - `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/orchestration/orchestrator_with_elisya.py`

### F. Contract metadata threaded into workflow runtime (P6.10)

- Протянут `workflow_family` в `mycelium_execute_workflow` и `vetka_execute_workflow`.
- На уровне workflow tool добавлен resolver контрактной runtime metadata:
  - `write_opt_ins`
  - `direct_allowed_tools`
  - `expected_sequence`
  - `reflex_policy`
- Эти данные подаются в orchestrator preflight context.
- Файлы:
  - `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/mcp/mycelium_mcp_server.py`
  - `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/mcp/tools/workflow_tools.py`
  - `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/orchestration/orchestrator_with_elisya.py`

## 2) Что делать следующему агенту

1. Добавить live e2e probe для `mycelium_execute_workflow` с `workflow_family="ownership_localguys"`.
   - Цель: подтвердить contract-specific preflight на полном workflow path, а не только static/audit assertions.
2. Протянуть contract-specific tool-surface enforcement в workflow path (не только `write_opt_ins`, но и точечное ограничение schemas по workflow policy).
3. Добавить telemetry в workflow result/debug API:
   - `reflex_preflight_applied`
   - `workflow_family`
   - `write_opt_ins_effective`
   - `tools_before/tools_after`.
4. Уточнить поведение для non-ollama providers (сейчас preflight helper применяет фильтрацию только на `provider_name=ollama`).

## 3) Проблемы и как не наступить снова

### Problem A: неверная сигнатура preflight helper

- Ошибка: попытка вызвать `maybe_apply_reflex_to_direct_tools` как старый helper с `subtask/phase/role` параметрами.
- Симптом: preflight quietly skipped в `try/except`.
- Как избежать:
  - всегда вызывать helper только через сигнатуру:
    - `arguments=...`
    - `messages=...`
    - `tools=...`
    - `provider_name=...`

### Problem B: provider detection в неправильном порядке

- Если вызывать preflight до определения `provider`, helper не знает текущий provider gate.
- Правильный порядок:
  1) определить `provider`
  2) выполнить REFLEX preflight
  3) выполнить `call_model_v2`

### Problem C: несоответствие contract-level vs runtime-level

- Контракт был в MCC, но до runtime не доходил в workflow path.
- Исправлено через `workflow_family` + runtime metadata resolver в workflow tool.
- Не удалять этот канал, иначе снова будет advisory-only поведение.

### Problem D: нестабильный `vetka_session_init`

- Текущее состояние: падает с `cannot access local variable 'json' where it is not associated with a value`.
- Рекомендация: не блокировать работу на этом шаге; использовать file-based context и targeted tests.

### Problem E: ложные ожидания на `TaskBoard.update_task`

- Метод возвращает `bool`, не dict.
- В live tests проверять `is True`, а не `result["success"]`.

## 4) Какие тесты уже green

### Non-live

```bash
python -m pytest tests/test_phase173_mycelium_workflow_reflex_audit.py tests/test_phase173_mcc_route_import_boundary.py tests/test_phase173_mycelium_local_patch_contract_isolated.py tests/mcc/test_mcc_workflow_contract_contract.py tests/mcc/test_mcc_localguys_run_contract.py -q
```

Result:
- `37 passed, 1 warning`

### Live guarded ownership slice

```bash
RUN_LOCAL_QWEN_BEHAVIOR_TESTS=1 python -m pytest tests/test_phase173_p6_local_qwen_live_behavior.py -k "ownership_preset" -q
```

Result:
- `2 passed, 4 deselected, 1 warning`

### Full guarded live suite (last known)

```bash
RUN_LOCAL_QWEN_BEHAVIOR_TESTS=1 python -m pytest tests/test_phase173_p6_local_qwen_live_behavior.py -q
```

Result:
- `6 passed, 1 warning`

## 5) Commit boundary / slice boundary

- Последняя известная формальная граница из прошлого handoff:
  - `9fdc09985` — `Add REFLEX tools for MCC Playwright seeding`
- Текущий P6.8-P6.10 слой находится в рабочем дереве; перед делегацией следующему агенту желательно сделать отдельный commit boundary для:
  - workflow-entry preflight parity
  - workflow_family runtime metadata threading
  - updated audit + roadmap markers.

## 6) Ссылки на roadmap и архитектуру

- Roadmap (активный):
  - `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/docs/172_vetka_tools/PHASE_173_REFLEX_ACTIVE_ROADMAP_2026-03-11.md`
- REFLEX architecture blueprint:
  - `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/docs/172_vetka_tools/REFLEX_ARCHITECTURE_BLUEPRINT_2026-03-10.md`
- Tool memory architecture:
  - `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/docs/172_vetka_tools/REFLEX_TOOL_MEMORY_ARCHITECTURE_2026-03-13.md`
- Local models playbook (MYCELIUM):
  - `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/docs/172_vetka_tools/LOCAL_MODELS_PLAYBOOK_FOR_MYCELIUM_2026-03-13.md`

## 7) Markers summary

- `MARKER_173.P6.LIVE_LOCAL_QWEN_BEHAVIOR`
- `MARKER_173.P6.MYCELIUM_LOCAL_PATCH_PRESET`
- `MARKER_173.P6.MYCELIUM_LOCAL_OWNERSHIP_PRESET`
- `MARKER_173.P6.MYCELIUM_WORKFLOW_REFLEX_AUDIT`
- `MARKER_173.P6.P9`
- `MARKER_173.P6.P10`
