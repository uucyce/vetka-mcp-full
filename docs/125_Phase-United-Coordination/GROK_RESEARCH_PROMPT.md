# Grok Research: VETKA United Coordination System

## Context

VETKA — 3D визуализация проекта с multi-agent системой. Несколько Claude агентов (Code, Desktop) работают параллельно и возникают конфликты:
- Phase 124 использовали оба агента одновременно
- Git обнаруживает конфликты ПОСЛЕ, а нужно координировать ДО

## Задача

Исследовать архитектуру **United Coordination System** которая объединит:

1. **Phase Registry** — резервирование номеров фаз
2. **TaskBoard** — существующая очередь задач для Pipeline
3. **BMAD** — методология планирования
4. **Git** — интеграция (branches from phases?)
5. **VETKA 3D** — визуализация активной работы

## Существующие системы (проанализируй файлы)

### TaskBoard
- `src/orchestration/task_board.py` — центральная очередь задач
- `data/task_board.json` — storage
- Flow: Add → Queue → Dispatch → Pipeline → Done
- Уже есть: priority, complexity, dependencies, status

### Heartbeat
- `src/orchestration/mycelium_heartbeat.py` — периодический опрос
- Триггерит задачи из чата (@dragon, @doctor)

### Agent Pipeline
- `src/orchestration/agent_pipeline.py` — Mycelium execution
- Dragon teams (Bronze/Silver/Gold)
- Architect → Researcher → Coder → Verifier

### CLAUDE.md
- Инструкции для агентов
- Можно добавить coordination protocol

### VETKA Frontend
- `client/src/store/useStore.ts` — состояние
- `client/src/components/canvas/FileCard.tsx` — визуализация нод
- Activity Glow уже есть (Phase 123)

## Вопросы для исследования

### 1. Архитектура координации
- Централизованная (один coordinator) vs распределённая (agents договариваются)?
- Где хранить state? `data/coordination.json`? В TaskBoard?
- Как интегрировать с существующим TaskBoard?

### 2. Locking granularity
- Phase-level: "Я работаю над Phase 125"
- Folder-level: "Я работаю в `client/src/components/`"
- File-level: "Я редактирую `FileCard.tsx`"
- Какой уровень оптимален?

### 3. Agent session management
- Как определить что агент "жив"? Heartbeat?
- Timeout если агент не отвечает?
- Graceful release при завершении сессии?

### 4. BMAD интеграция
- Как связать high-level planning с task execution?
- Phases как milestone в BMAD?

### 5. Git интеграция
- Auto-create branch `phase-125-wobble-animation`?
- Или оставить manual?
- Pre-commit hook для проверки phase ownership?

### 6. VETKA 3D визуализация
- Показывать какой агент работает над каким файлом?
- Agent avatars/cursors в 3D?
- "Work in progress" glow (отдельный от activity glow)?
- Timeline внизу показывающий активные phases?

### 7. Conflict resolution
- Что если два агента хотят один файл?
- Queue? First-come-first-served? Priority?
- Notification system?

### 8. MCP Tools
Какие tools нужны?
```
vetka_reserve_phase(name, scope) → phase_id
vetka_release_phase(phase_id)
vetka_get_active_work() → {agents, phases, files}
vetka_check_file_available(path) → bool
vetka_reserve_file(path) → lock_id
```

## Философия: Before vs After

```
СЕЙЧАС (After):
  Work → Work → Work → Git commit → CONFLICT!

НУЖНО (Before):
  Reserve → Work → Release → Git commit → Clean!
```

Эту философию надо отзеркалить в самой VETKA — показывать не только историю (git), но и **намерения** (что планируется).

## Deliverables

1. **Architecture diagram** — как компоненты связаны
2. **Data model** — JSON schema для coordination state
3. **Integration plan** — как подключить к существующим системам
4. **MCP tools spec** — какие tools создать
5. **VETKA 3D mockup** — как визуализировать

## Файлы для анализа

```
src/orchestration/task_board.py
src/orchestration/mycelium_heartbeat.py
src/orchestration/agent_pipeline.py
src/mcp/tools/task_board_tools.py
src/mcp/vetka_mcp_bridge.py
client/src/store/useStore.ts
client/src/components/canvas/FileCard.tsx
client/src/hooks/useSocket.ts
CLAUDE.md
data/task_board.json
data/templates/model_presets.json
```

## Related Concepts

- **Distributed locking** (Redis, etcd patterns)
- **Optimistic vs pessimistic locking**
- **Event sourcing** для истории координации
- **CRDT** для conflict-free coordination
- **Kanban boards** визуализация
