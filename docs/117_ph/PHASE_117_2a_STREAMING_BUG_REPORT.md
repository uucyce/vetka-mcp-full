# Phase 117.2a — Dragon/Mycelium Streaming Bug Report

**Дата:** 2026-02-07
**Методология:** Opus (architect) → 9 Haiku scouts → 3 Sonnet verifiers
**Статус:** ✅ ROOT CAUSE НАЙДЕН, готов к имплементации

---

## 🎯 ПРОБЛЕМА

Dragon/Mycelium pipeline (`vetka_mycelium_pipeline`, `vetka_call_model`) отрабатывает (status: done), но **ответы агентов не видны в UI чате** — уходят в /dev/null. В чат попадают только запросы.

---

## 🔍 ROOT CAUSE: 4 уровня потерь

### BUG-A: Несуществующий endpoint (КРИТИЧЕСКИЙ) 🔴

**Файл:** `src/orchestration/agent_pipeline.py:329`
**Проблема:** Pipeline POSTит в `/api/chat/send` — **этого endpoint НЕТ в приложении**.

```python
# agent_pipeline.py:328-336 (ТЕКУЩИЙ — СЛОМАН)
client.post(
    "http://localhost:5001/api/chat/send",  # ← НЕ СУЩЕСТВУЕТ!
    json={
        "group_id": self.chat_id,
        "sender_id": "@pipeline",
        "content": full_message,
        "message_type": "system"
    }
)
```

**Правильный endpoint:** `/api/debug/mcp/groups/{group_id}/send`
**Файл:** `src/api/routes/debug_routes.py:1143`

**Результат:** ВСЕ progress-сообщения pipeline (Architect план, Research, Coder) молча теряются (exception пойман на debug level, line 337).

---

### BUG-B: Fire-and-forget — результат execute() отброшен 🔴

**Файл:** `src/mcp/vetka_mcp_bridge.py:1828-1856`
**Проблема:** MCP bridge запускает pipeline через `asyncio.create_task()` и немедленно возвращает task_id. Возвращаемое значение `pipeline.execute()` — **отброшено**.

```python
# vetka_mcp_bridge.py:1828-1836 (ТЕКУЩИЙ)
async def run_pipeline_background():
    try:
        await pipeline.execute(task, phase_type)  # ← return value DISCARDED!
        logger.info(f"[MCP] Pipeline {task_id} completed")
    except Exception as e:
        logger.error(f"[MCP] Pipeline {task_id} failed: {e}")

asyncio.create_task(run_pipeline_background())  # fire-and-forget

# Line 1856: returns only task_id text to MCP caller
return [TextContent(type="text", text=response_text)]
```

**Результат:** MCP-caller (Claude Code) получает только task_id, никогда не видит результаты. Нет notification о завершении pipeline.

---

### BUG-C: SocketIO emit может молча упасть 🟡

**Файл:** `src/mcp/tools/llm_call_tool.py:289-290`
**Проблема:** `_emit_to_chat()` ловит отсутствие asyncio loop на уровне debug.

```python
# llm_call_tool.py:289-290
except Exception as e:
    logger.debug(f"[LLM_CALL_TOOL] Could not emit to chat (no event loop): {e}")
```

**Результат:** Если LLM-ответ получен в контексте без event loop (например из ThreadPoolExecutor в pipeline), SocketIO emission молча проваливается.

---

### BUG-D: Architect/Researcher результаты НЕ эмитятся 🟡

**Файл:** `src/orchestration/agent_pipeline.py`
**Проблема:** Даже при исправлении endpoint, pipeline НЕ отправляет в чат:
- **Architect plan** (line 811) — сохраняется только в `pipeline_task.results`
- **Researcher context** (line 1182) — передаётся только в `subtask.context`
- **Coder output** (line 945-955) — эмитится условно: `stream_result=True` + `visible_to_user=True`

**Результат:** Пользователь видит в лучшем случае только финальный output Coder, но не план и не research.

---

## 📊 ВЕРИФИКАЦИЯ МАРКЕРОВ

### Sonnet S1 (Emission Chain): Haiku accuracy 95%
| Маркер | Файл | Статус |
|--------|------|--------|
| LIGHTNING_CHAT_ID at line 82 | llm_call_tool.py | ✅ |
| _emit_to_chat() → SocketIO group_message | llm_call_tool.py:241-293 | ✅ |
| _emit_response_to_chat() line 313-325 | llm_call_tool.py | ✅ |
| asyncio silent fail at line 290 | llm_call_tool.py | ✅ |
| No token-level streaming | llm_call_tool.py | ✅ |
| _emit_progress() → HTTP POST | agent_pipeline.py:309-340 | ✅ |
| _emit_stream_event() → HTTP POST | agent_pipeline.py:350-444 | ✅ |
| call_model_v2 non-streaming | provider_registry.py:1467 | ✅ |
| call_model_v2_stream unused by pipeline | provider_registry.py:1675 | ✅ |

### Sonnet S2 (MCP Bridge): Haiku accuracy 100%
| Маркер | Файл | Статус |
|--------|------|--------|
| Pipeline handler lines 1799-1861 | vetka_mcp_bridge.py | ✅ |
| Fire-and-forget asyncio.create_task | vetka_mcp_bridge.py:1836 | ✅ |
| execute() return discarded | vetka_mcp_bridge.py:1830 | ✅ |
| Immediate return with task_id | vetka_mcp_bridge.py:1856 | ✅ |
| Group chat endpoint /api/groups/ | vetka_mcp_bridge.py:1410 | ✅ |
| Offline fallback mcp_message_buffer | vetka_mcp_bridge.py:1452-1471 | ✅ |
| Results stored pipeline_tasks.json | agent_pipeline.py:514-518 | ✅ |

### Sonnet S3 (Frontend): Haiku accuracy 92%
| Маркер | Файл | Статус |
|--------|------|--------|
| SocketIO group_message event | useSocket.ts:123-131 | ✅ |
| Group stream CustomEvent dispatch | useSocket.ts:1007-1032 | ✅ |
| ChatPanel addEventListener | ChatPanel.tsx:246-387 | ✅ |
| HTTP polling fallback 3sec | ChatPanel.tsx:391-454 | ✅ |
| Single MCP Dev group | groups.json | ✅ |
| `/api/chat/send` exists | — | ❌ НЕТ! |
| SocketIO emit on HTTP POST | — | ❌ НЕТ! |

**Общая точность Haiku скаутов: ~96%** — отличный результат.

---

## 🏗️ АРХИТЕКТУРА СТРИМИНГА (ТЕКУЩАЯ — СЛОМАННАЯ)

```
MCP Tool Call (vetka_mycelium_pipeline)
    │
    ▼
vetka_mcp_bridge.py:1799
    │
    ├── asyncio.create_task() ────────── Fire-and-forget!
    │       │
    │       ▼
    │   AgentPipeline.execute()
    │       │
    │       ├── _architect_plan() ──── LLMCallTool → call_model_v2
    │       │     │
    │       │     ├── _emit_to_chat() → SocketIO ──── 🟡 May fail silently (no event loop)
    │       │     └── Plan saved to pipeline_task.results (NOT emitted to chat)
    │       │
    │       ├── _research() ──── LLMCallTool → call_model_v2
    │       │     └── Context saved to subtask.context (NOT emitted to chat)
    │       │
    │       ├── _execute_subtask() ──── LLMCallTool → call_model_v2
    │       │     │
    │       │     ├── _emit_progress() → POST /api/chat/send ──── 🔴 ENDPOINT DOES NOT EXIST!
    │       │     ├── _emit_stream_event() → POST /api/stream/event ── 🔴 LIKELY ALSO MISSING
    │       │     └── Coder result conditionally emitted (if visible_to_user=True)
    │       │
    │       └── _update_task() → pipeline_tasks.json ──── ✅ Saved OK
    │
    └── return TextContent(task_id) ──── MCP caller gets only task_id
```

---

## 🏗️ АРХИТЕКТУРА СТРИМИНГА (ЖЕЛАЕМАЯ)

```
MCP Tool Call (vetka_mycelium_pipeline)
    │
    ▼
vetka_mcp_bridge.py
    │
    ├── asyncio.create_task() ────── Fire-and-forget OK (для MCP это норма)
    │       │
    │       ▼
    │   AgentPipeline.execute()
    │       │
    │       ├── _architect_plan()
    │       │     ├── _emit_to_group_chat() → POST /api/debug/mcp/groups/{id}/send ── ✅ Real endpoint
    │       │     │                                      │
    │       │     │                                      ▼
    │       │     │                          group_chat_manager.send_message()
    │       │     │                                      │
    │       │     │                                      ▼
    │       │     │                          SocketIO emit group_message to room ── ✅ UI receives!
    │       │     └── Plan also emitted with 📋 prefix
    │       │
    │       ├── _research()
    │       │     └── Research summary emitted with 🔍 prefix
    │       │
    │       ├── _execute_subtask()
    │       │     └── Coder result emitted with 💻 prefix
    │       │
    │       ├── _update_task() → pipeline_tasks.json
    │       │
    │       └── _emit_completion() → Final summary with ✅ prefix
    │
    │   On completion:
    │       └── run_pipeline_background() captures result
    │           └── Sends completion notification to group chat
    │
    └── return TextContent(task_id + "poll for results")
```

---

## 🔧 ПЛАН ИМПЛЕМЕНТАЦИИ (Phase 117.2a)

### Шаг 1: Исправить endpoint в agent_pipeline.py (BUG-A)

**Файл:** `src/orchestration/agent_pipeline.py`

1. Заменить URL в `_emit_progress()` (line 329):
   - OLD: `http://localhost:5001/api/chat/send`
   - NEW: `http://localhost:5001/api/debug/mcp/groups/{self.chat_id}/send`

2. Обновить JSON body:
   - OLD: `{"group_id": ..., "sender_id": "@pipeline", ...}`
   - NEW: `{"agent_id": "pipeline", "content": ..., "message_type": "system"}`

3. Аналогично обновить `_emit_stream_event()` (line 370+) если использует тот же endpoint.

### Шаг 2: Добавить emission для Architect/Researcher (BUG-D)

**Файл:** `src/orchestration/agent_pipeline.py`

1. После `_architect_plan()` (line 811): эмитить план в чат с 📋 prefix
2. После `_research()` (line 1182): эмитить summary в чат с 🔍 prefix
3. После каждого subtask: эмитить результат с 💻 prefix

### Шаг 3: Добавить completion notification (BUG-B)

**Файл:** `src/mcp/vetka_mcp_bridge.py`

1. В `run_pipeline_background()` (line 1828): после `execute()` — отправить итоговое сообщение в group chat
2. Сохранить result в переменную (вместо дискарда)
3. Отправить summary в чат: `"✅ Pipeline complete: {summary}"`

### Шаг 4: Улучшить error handling (BUG-C)

**Файл:** `src/mcp/tools/llm_call_tool.py`

1. Line 290: `logger.debug` → `logger.warning`
2. Добавить fallback: если SocketIO emit fail — POST в HTTP endpoint

### Шаг 5 (опционально): Кеш и retry

- Добавить retry queue для failed emissions
- TTL кеш для balance (из BUG-8 backlog)

---

## 📁 ФАЙЛЫ К ИЗМЕНЕНИЮ

| # | Файл | Изменения | Приоритет |
|---|------|-----------|-----------|
| 1 | `src/orchestration/agent_pipeline.py` | BUG-A (endpoint), BUG-D (emit all phases) | P0 |
| 2 | `src/mcp/vetka_mcp_bridge.py` | BUG-B (capture result, notify) | P0 |
| 3 | `src/mcp/tools/llm_call_tool.py` | BUG-C (error handling) | P1 |
| 4 | `tests/test_phase117_2a_streaming.py` | Тесты на все фиксы | P1 |

---

## 📡 GROK RESEARCH (промпт ниже — отправить вручную)

См. секцию в конце документа.

---

## ПРОМПТ ДЛЯ ГРОКА: Pipeline Streaming Best Practices

```
Привет Грок! Нужно системное исследование по теме:

## Задача
Best practices для стриминга результатов из multi-agent pipeline в real-time UI.

## Контекст
В проекте VETKA есть Mycelium Pipeline — multi-agent система (Architect → Researcher → Coder).
Pipeline запускается async (fire-and-forget) из MCP bridge.

Текущие проблемы:
1. Pipeline POSTит progress в НЕСУЩЕСТВУЮЩИЙ endpoint — все сообщения теряются
2. Architect plan и Researcher results не отправляются в UI вообще
3. MCP bridge отбрасывает return value pipeline.execute()
4. SocketIO emit может молча упасть если нет event loop

Стек: Python (asyncio), FastAPI, SocketIO (python-socketio), React (Zustand + SocketIO client)

## Что нужно исследовать:

1. **Паттерны стриминга из async pipeline в WebSocket:**
   - Server-Sent Events (SSE) vs SocketIO vs WebSocket native
   - Как LangChain/LangGraph/CrewAI/AutoGen стримят agent outputs в UI?
   - Message bus pattern (Redis Pub/Sub vs in-memory) для decoupling pipeline от emission

2. **Fire-and-forget + notification:**
   - Как правильно notify клиента о завершении background task?
   - Callback pattern vs polling vs push notification
   - AsyncIO task tracking: `asyncio.create_task()` с callback on done

3. **Reliability:**
   - Message queue для guaranteed delivery (если SocketIO emit fail)
   - Retry с exponential backoff
   - Fallback: HTTP long-polling если WebSocket disconnected
   - Idempotent messages (dedup по ID)

4. **Multi-agent UI patterns:**
   - Как показывать agent "thinking" в real-time (типа ChatGPT "Searching...")
   - Collapsible agent phases (Architect → Research → Code)
   - Progress indicators для multi-step pipelines

5. **Конкретные вопросы по python-socketio:**
   - Как эмитить из sync context (ThreadPoolExecutor) в async SocketIO?
   - `sio.emit()` vs `await sio.emit()` — когда какой?
   - Room management: `sio.enter_room()` / `sio.leave_room()` для group chats
   - Можно ли `sio.emit()` из background asyncio.Task?

6. **LangGraph approach:**
   - LangGraph streaming: как реализован real-time output в LangGraph?
   - Agent state streaming vs final output only
   - Checkpointing pattern для resume

## Формат ответа:
- Таблица сравнения подходов (SSE vs SocketIO vs WS)
- Code snippets для Python (asyncio + SocketIO)
- Ссылки на реализации в open-source проектах
- Рекомендация для нашего стека
```

---

*Phase 117.2a — Dragon Streaming Bug — готов к имплементации после перекура.*
