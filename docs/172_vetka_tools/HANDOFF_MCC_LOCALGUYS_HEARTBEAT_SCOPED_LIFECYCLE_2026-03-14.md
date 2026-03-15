# Handoff — MCC Localguys Scoped Heartbeat + Lifecycle Bridge

Date: 2026-03-14

Marker: `MARKER_173.P6.LOCALGUYS.HEARTBEAT_SCOPED_BRIDGE`

## 1) Цель среза

Сделать localguys-команды управляемыми в рантайме через единый мост:

1. `scripts/localguys.py` шлет lifecycle signals (`used_tools`, `write_attempts`, `turn_increment`, telemetry).
2. Heartbeat читает run + `runtime_guard`.
3. При idle/stalled heartbeat действует по policy: `nudge` или постановка continuation/resume task.
4. Heartbeat поддерживает уровни профиля: global -> project -> workflow -> task.

## 2) Фактический статус по кодовой базе (recon)

Ниже уже реализовано:

- `src/api/routes/debug_routes.py`
  - persisted heartbeat config расширен полями:
    - `profile_mode`, `project_id`, `workflow_family`, `task_id`
    - `localguys_enabled`, `localguys_idle_sec`, `localguys_action`
  - `GET/POST /api/debug/heartbeat/settings` возвращает и принимает эти поля.

- `src/orchestration/mycelium_heartbeat.py`
  - добавлена загрузка heartbeat config из `data/heartbeat_config.json`
  - добавлен scoped-фильтр задач:
    - `_task_matches_heartbeat_profile(...)`
  - добавлен localguys runtime loop:
    - `_process_localguys_heartbeat(...)`
    - stale detection по `updated_at` + `localguys_idle_sec`
    - чтение runtime snapshot (`run`, `runtime_guard`)
    - action policy:
      - `nudge`
      - `resume_task`
      - `auto` (первый idle = nudge, повторный = resume)
  - результаты localguys включены в `heartbeat_tick` payload:
    - `checked`, `stalled`, `nudged`, `resumed`.

- `scripts/localguys.py`
  - добавлен `signal_localguys_run(...)` (PATCH `/api/mcc/localguys-runs/{run_id}`)
  - добавлен CLI subcommand `localguys signal ...`
  - прокидываются lifecycle метрики и runtime telemetry.

- `client/src/store/useMCCStore.ts`
  - heartbeat type/state расширен полями профиля + localguys policy.

- `client/src/components/mcc/HeartbeatChip.tsx`
  - добавлен UI scope selector (`global/project/workflow/task`)
  - выводится localguys policy summary (`action`, `idle`).

## 3) Что дополнительно подтверждено тестами

Таргетные suites:

```bash
python -m pytest tests/test_heartbeat_daemon.py tests/test_phase177_localguys_operator_tool.py -q
```

Result: `13 passed`.

Примечание по фиксам тестов:
- устранена timezone-зависимость в stalled-check;
- в fake HTTP for localguys поправлен порядок роутинга, чтобы `PATCH /localguys-runs/{id}` не перехватывался generic веткой.

## 4) Открытые задачи для следующего чата (implementation plan)

### P1. Авто-сигналы из operator loop (главный пробел)

Сейчас есть `localguys signal`, но операторский цикл должен слать его автоматически на каждом turn/step.

Сделать:
- интегрировать `signal_localguys_run(...)` в live operator loop;
- слать сигнал после каждого tool execution и после перехода шага;
- отдельно слать финальный сигнал в `done/failed`.

DoD:
- run metadata в MCC обновляется без ручного CLI вызова.

### P2. Многоуровневый heartbeat runtime профиль

Сейчас профиль уже есть в конфиге и фильтре задач, нужно дожать UX + контракт:

- добавить в UI явное отображение effective scope key:
  - `global`
  - `project:<id>`
  - `workflow:<family>@<project>`
  - `task:<id>`
- добавить в tick result/debug запись `effective_profile`.

DoD:
- по каждому режиму видно, какие localguys-задачи реально попали под heartbeat.

Status update (2026-03-14, follow-up):
- `effective_profile` добавлен в heartbeat payload:
  - `src/orchestration/mycelium_heartbeat.py`:
    - helper `_effective_heartbeat_profile(...)`
    - `heartbeat_tick` теперь возвращает top-level `effective_profile`
    - `localguys` секция tick payload теперь включает `effective_profile`
    - `localguys.results[]` содержит `effective_profile_key`
- `src/api/routes/debug_routes.py`:
  - `GET/POST /api/debug/heartbeat/settings` теперь возвращают `effective_profile`
- `client/src/components/mcc/HeartbeatChip.tsx`:
  - scope label теперь предпочитает backend `effective_profile.key`
  - формат workflow scope приведен к `workflow:<family>@<project>`
- Regression:
  - `python -m pytest tests/test_heartbeat_daemon.py tests/test_phase177_localguys_operator_tool.py -q`
  - результат: `13 passed`

### P3. Continuation/resume policy hardening

Сейчас resume создается с dedupe по `task_origin/parent/run tag`. Нужно усилить:

- TTL/attempt limit для resume задач (чтобы не спамить бесконечно);
- escalation path после N idle cycles;
- явный `resume_reason` в созданной задаче.

DoD:
- при длительном idle контур остается управляемым, без бесконечного queue growth.

### P4. Observability/ops слой

- добавить в debug/status endpoint heartbeat counters по scope;
- логировать `runtime_guard` snapshot hash/summary;
- вывести в MCC мини-таймлайн последних heartbeat actions по конкретному run.

DoD:
- по одному run можно быстро понять: почему был nudge/resume и по какой policy.

## 5) Риски и ограничения

- `vetka_session_init` сейчас падает с MCP ошибкой `cannot access local variable 'json'...`, поэтому handoff опирается на file/code recon + tests.
- В рабочем дереве много сторонних изменений; этот срез не должен их переписывать.
- В проде возможна дрожь времени/часовых поясов: stalled логика должна оставаться UTC-safe.

## 6) Стартовый чеклист для свежего чата

1. Проверить актуальность `scripts/localguys.py` и реально ли loop вызывает `signal_localguys_run`.
2. Прогнать smoke:
   - `python -m pytest tests/test_heartbeat_daemon.py tests/test_phase177_localguys_operator_tool.py -q`
3. Реализовать P1 (auto lifecycle signals), потом P2.
4. После каждого шага — обновить этот handoff или создать `STATUS` в той же phase-папке.
