# MCC AUDIT REPORT — Phase 137

**Date:** 2026-02-11
**Auditor:** Claude Opus 4.5 (Claude Code)
**Scope:** Mycelium Command Center, Heartbeat, Dragon/Titan Pipeline Readiness

---

## EXECUTIVE SUMMARY

MCC infrastructure is ~80% ready. Main blocker: **Heartbeat не работает автоматически** — это не фоновый процесс, а функция которую надо вызывать вручную или через MCP.

**Quick Wins реализованы в этой сессии:**
- [x] `POST /api/debug/heartbeat/tick` — ручной запуск
- [x] Кнопка "TICK NOW" в DevPanel

---

## 1. HEARTBEAT SYSTEM

### 1.1 Архитектура

```
[User] → @dragon task в группе
         ↓
[Heartbeat Tick] — ТРЕБУЕТ РУЧНОГО ВЫЗОВА!
         ↓
[Parse Messages] — находит @dragon/@titan/@doctor
         ↓
[Dispatch Pipeline] — AgentPipeline.execute()
         ↓
[Progress → Chat] — SocketIO events
         ↓
[Artifacts → Disk] — если content > 500 chars
         ↓
[DAG → MCC] — result записывается в task_board.json
```

### 1.2 Проблемы

| Issue | Severity | Status |
|-------|----------|--------|
| Heartbeat не автоматический | HIGH | KNOWN - by design |
| Две системы endpoints (дубликат) | MEDIUM | Documented |
| ON/OFF кнопки — enabled flag не влияет на авто-запуск | LOW | By design |

### 1.3 Endpoints

**Используемые (debug_routes.py):**
```
GET  /api/debug/heartbeat/settings  — получить настройки
POST /api/debug/heartbeat/settings  — обновить enabled/interval
POST /api/debug/heartbeat/tick      — НОВЫЙ: ручной tick (Phase 137)
```

**НЕ зарегистрированные (heartbeat_health.py):**
```
GET  /api/heartbeat/health   — NOT REGISTERED!
GET  /api/heartbeat/config   — NOT REGISTERED!
POST /api/heartbeat/config   — NOT REGISTERED!
```

### 1.4 Конфигурация

**Файл:** `data/heartbeat_config.json`
```json
{
  "enabled": false,
  "interval": 1800,
  "updated_at": "2026-02-10T16:45:00Z"
}
```

**Файл:** `data/heartbeat_state.json`
```json
{
  "last_message_id": "652a0c69-...",
  "last_tick_time": 1770808417,
  "total_ticks": 199,
  "tasks_dispatched": 0
}
```

### 1.5 Триггеры задач

Heartbeat распознает паттерны:
- `@dragon <task>` → preset: dragon_silver (default)
- `@titan <task>` → preset: titan_core
- `@doctor <task>` → phase_type: research
- `@help <task>` → phase_type: research
- `@pipeline <task>` → phase_type: build
- `/task <task>` → phase_type: build
- `/fix <task>` → phase_type: fix
- `/build <task>` → phase_type: build
- `@board <command>` → TaskBoard commands

---

## 2. ARTIFACT PANEL

### 2.1 Backend

| Endpoint | File | Status |
|----------|------|--------|
| `GET /api/debug/artifacts` | debug_routes.py | ✅ Works |
| `GET /api/debug/artifacts/{filename}` | debug_routes.py | ✅ Works |
| `GET /api/approvals/pending` | approval_routes.py | ✅ Works |
| `POST /api/approvals/{id}/approve` | approval_routes.py | ✅ Works |
| `POST /api/approvals/{id}/reject` | approval_routes.py | ✅ Works |

### 2.2 Service

**Файл:** `src/services/disk_artifact_service.py`
- `list_artifacts()` — список артефактов из `artifacts/`
- `create_disk_artifact()` — создание (min 500 chars)
- `read_artifact()` — чтение содержимого

### 2.3 Frontend

**Файл:** `client/src/components/panels/ArtifactViewer.tsx`
- Tabs: Pending / Completed
- Pending: из `/api/approvals/pending`
- Completed: из `/api/debug/artifacts`

### 2.4 Проблема

**Директория `artifacts/` пуста** потому что:
1. Pipelines не запускались
2. Артефакты создаются только если `content.length >= 500`

---

## 3. DRAGON/TITAN READINESS

### 3.1 Presets

**Файл:** `data/templates/model_presets.json`

| Preset | Architect | Researcher | Coder | Verifier | Scout |
|--------|-----------|------------|-------|----------|-------|
| dragon_bronze | qwen3-30b | grok-4.1-fast | qwen3-coder-flash | mimo-v2-flash | mimo-v2-flash |
| dragon_silver | kimi-k2.5 | grok-4.1-fast | qwen3-coder | glm-4.7-flash | glm-4.7-flash |
| dragon_gold | kimi-k2.5 | grok-4.1-fast | qwen3-coder | qwen3-235b | kimi-k2.5 |
| titan_lite | qwen3-30b | grok-4.1-fast | qwen3-coder-flash | claude-haiku | glm-4.7-flash |
| titan_core | gemini-3-pro | grok-4.1-fast | claude-sonnet-4.5 | qwen3-max | kimi-k2.5 |
| titan_prime | claude-opus-4.6 | gpt-5.2-pro | deepseek-r1 | claude-opus-4.6 | gemini-3-pro |

### 3.2 API Keys

**Файл:** `data/config.json`

| Provider | Status | Keys |
|----------|--------|------|
| polza | ✅ | pza_hU0ySd... |
| poe | ✅ | 8 keys |
| xai | ✅ | 6 keys |
| openai | ✅ | 2 keys |
| gemini | ✅ | 3 keys |
| anthropic | ? | not checked |

### 3.3 Pipeline Flow

```
AgentPipeline.execute(task, phase_type)
    ↓
1. Scout: scans codebase for context
    ↓
2. Architect: breaks task into subtasks
    ↓
3. Researcher: investigates unclear parts (if needs_research=true)
    ↓
4. Coder: implements each subtask
    ↓
5. Verifier: reviews results
    ↓
Result → task_board.json["result"]
       → artifacts/ (if large code)
       → Chat (SocketIO streaming)
```

---

## 4. MCP CONFIGURATION

### 4.1 Dual MCP Architecture

**Файл:** `.mcp.json`

| Server | Namespace | Port | Purpose |
|--------|-----------|------|---------|
| vetka | `vetka_*` | 5001 | Fast stateless tools |
| mycelium | `mycelium_*` | 8082 WS | Async pipeline tools |

### 4.2 MYCELIUM Tools

```
mycelium_pipeline        — Run agent pipeline
mycelium_call_model      — Async LLM call
mycelium_task_board      — Manage task queue
mycelium_task_dispatch   — Dispatch tasks
mycelium_heartbeat_tick  — Scan chat for tasks
mycelium_heartbeat_status — Check heartbeat status
```

---

## 5. ENDPOINT WIRING AUDIT

### 5.1 Registered Routes

**Файл:** `src/api/routes/__init__.py`

Total: 26 routers registered

| Router | Prefix | Status |
|--------|--------|--------|
| debug_router | /api/debug | ✅ |
| dag_router | /api/dag | ✅ |
| artifact_router | /api/artifacts | ✅ |
| unified_search_router | /api/search | ✅ |
| heartbeat_health | /api/heartbeat | ❌ NOT REGISTERED |

### 5.2 Missing Registrations

```python
# heartbeat_health.py is NOT imported in __init__.py
# Routes exist but not accessible:
#   /api/heartbeat/health
#   /api/heartbeat/config
```

**Recommendation:** Either register or delete `heartbeat_health.py` (duplicate functionality in debug_routes.py)

---

## 6. GAPS & RECOMMENDATIONS

### 6.1 Critical

| Gap | Impact | Fix |
|-----|--------|-----|
| Heartbeat не автоматический | Dragon/Titan не стартуют автоматом | Use "TICK NOW" button or MCP |

### 6.2 Medium

| Gap | Impact | Fix |
|-----|--------|-----|
| heartbeat_health.py not registered | Confusing duplicate code | Delete or register |
| artifacts/ empty | No visible results | Run pipeline first |

### 6.3 Low

| Gap | Impact | Fix |
|-----|--------|-----|
| DevPanel TypeScript warnings | Linter noise | Fix unused vars |

---

## 7. TESTING CHECKLIST

### 7.1 Manual Heartbeat Test

```bash
# 1. Start backend
cd /Users/danilagulin/Documents/VETKA_Project/vetka_live_03
python -m uvicorn src.main:app --port 5001

# 2. Check health
curl http://localhost:5001/api/health/ready

# 3. Post task to group chat (via UI)
# Message: @dragon simple test - print hello world

# 4. Trigger heartbeat tick
curl -X POST http://localhost:5001/api/debug/heartbeat/tick \
  -H "Content-Type: application/json" \
  -d '{}'

# Expected response:
# {"success":true,"tick":200,"new_messages":1,"tasks_found":1,"tasks_dispatched":1}
```

### 7.2 DevPanel Test

1. Open DevPanel (Cmd+Shift+D)
2. Expand Heartbeat section
3. Click "TICK NOW" button
4. Check alert for tick results
5. Check chat for pipeline progress

### 7.3 Pipeline Test

1. Add task via DevPanel → Task Board → Add
2. Click "Dispatch" on the task
3. Monitor progress in chat
4. Check DAG tab for visualization
5. Check Artifacts tab for outputs

---

## 8. FILES MODIFIED (Phase 137)

### 8.1 Sprint 1 (S1.3-S1.5)

```
client/src/components/search/CommandPalette.tsx   — MARKER_137.S1_3
client/src/components/search/UnifiedSearchBar.tsx — MARKER_137.S1_3
src/services/dag_aggregator.py                    — MARKER_137.S1_4
src/orchestration/task_board.py                   — MARKER_137.S1_4
```

### 8.2 MCC Fixes

```
src/api/routes/debug_routes.py                    — MARKER_137.TICK_NOW
client/src/components/panels/DevPanel.tsx         — MARKER_137.TICK_NOW
client/src/components/jarvis/JarvisWave.tsx       — TypeScript fix
```

---

## 9. NEXT STEPS

1. **Test heartbeat flow** — verify TICK NOW works
2. **Run first Dragon pipeline** — create artifact
3. **Verify DAG visualization** — check task_board.json["result"]
4. **Clean up duplicate code** — heartbeat_health.py decision
5. **Consider auto-heartbeat** — cron/launchd if needed

---

**Report generated:** 2026-02-11T15:XX:XX
**Markers used:** MARKER_137.S1_3, MARKER_137.S1_4, MARKER_137.TICK_NOW
