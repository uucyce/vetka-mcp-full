# План интеграции OpenCode с VETKA MCP

**Дата**: 02.02.2026
**Автор**: Claude Code Agent
**Цель**: Подключить **OpenCode** к **VETKA MCP** через существующий **OpenCode Bridge** (`/src/opencode_bridge/`), используя **FastAPI-прокси** и **общую память** (STM, CAM, Engram).

---

## 1. Существующая архитектура OpenCode Bridge

### 1.1. `open_router_bridge.py`
- **Назначение**: Мост для взаимодействия с **OpenRouter** через **VETKA MCP**.
- **Ключевые функции**:
  - Управление API-ключами (`get_key_manager`, `ProviderType.OPENROUTER`).
  - Вызов моделей через `call_model_v2` (интеграция с `ProviderRegistry`).
  - Статистика использования ключей (`BridgeStats`).
- **Пример использования**:
  ```python
  bridge = get_openrouter_bridge()
  result = await bridge.invoke("xai/grok-4", [{"role": "user", "content": "Hello"}])
  ```

### 1.2. `routes.py`
- **Назначение**: **FastAPI-маршруты** для доступа к инструментам VETKA через OpenCode.
- **Ключевые эндпоинты**:
  - `/openrouter/invoke`: Вызов моделей через OpenRouter.
  - `/tools`: Список всех доступных инструментов VETKA (18 инструментов).
  - `/model/call`: Вызов LLM с поддержкой контекста и инструментов.
- **Пример**:
  ```bash
  curl -X POST http://localhost:5002/openrouter/invoke -H "Content-Type: application/json" -d '{
      "model_id": "xai/grok-4",
      "messages": [{"role": "user", "content": "Hello"}]
  }'
  ```

### 1.3. `multi_model_orchestrator.py`
- **Назначение**: Оркестрация **многомодельных рабочих процессов** (например, цепочки `Grok → Architect → DeepSeek`).
- **Ключевые функции**:
  - Поддержка команд на русском (`Оркестрируй:`, `Позвони`, `Сделай цепочку:`).
  - Вызов моделей через `OpenRouterBridge`.
- **Пример**:
  ```python
  orchestrator = get_orchestrator()
  result = await orchestrator.orchestrate("Оркестрируй: Grok → Architect → DeepSeek → Implementation")
  ```

---

## 2. План интеграции OpenCode с VETKA MCP

### 2.1. Цели
1. **Подключение OpenCode к MCP**: Все вызовы OpenCode должны проходить через **VETKA MCP Bridge**.
2. **Использование общей памяти**: Интеграция с **STM**, **CAM**, **Engram** для контекста.
3. **Минимальные изменения**: Использовать существующие инструменты OpenCode Bridge без модификации ядра.

---

## 3. Компоненты интеграции

### 3.1. Новые инструменты MCP для OpenCode
| **Инструмент**               | **Описание**                                                                 | **Реализация**                                                                 |
|------------------------------|-----------------------------------------------------------------------------|--------------------------------------------------------------------------------|
| `vetka_opencode_call`        | Вызов моделей OpenCode через MCP с поддержкой контекста.                     | Использовать `/openrouter/invoke` для вызова моделей.                          |
| `vetka_opencode_orchestrate` | Оркестрация многомодельных рабочих процессов (например, `Grok → Architect`). | Использовать `MultiModelOrchestrator`.                                        |

### 3.2. Маршрутизация через MCP
- **Пример вызова модели OpenCode**:
  ```python
  result = await mcp.call_tool(
      "vetka_opencode_call",
      {
          "model_id": "xai/grok-4",
          "messages": [{"role": "user", "content": "Hello"}],
          "inject_context": {
              "working_memory": await mcp.call_tool("vetka_get_conversation_context", {"user_id": "danila"}),
              "current_files": await mcp.call_tool("vetka_get_tree", {"format": "summary"})
          }
      }
  )
  ```

- **Пример оркестрации**:
  ```python
  orchestration_result = await mcp.call_tool(
      "vetka_opencode_orchestrate",
      {
          "command": "Оркестрируй: Grok → Architect → DeepSeek → Implementation",
          "context": {
              "user_id": "danila",
              "current_task": "Optimize database queries"
          }
      }
  )
  ```

### 3.3. Общая память VETKA MCP
- **STM**: Хранение текущего диалога.
- **CAM**: Контекст активных файлов/проектов.
- **Engram**: Долгосрочные предпочтения пользователя.
- **Пример инъекции контекста**:
  ```python
  context = {
      "working_memory": await mcp.call_tool("vetka_get_conversation_context", {"user_id": "danila"}),
      "current_files": await mcp.call_tool("vetka_get_tree", {"format": "summary"}),
      "user_preferences": await mcp.call_tool("vetka_get_user_preferences", {"user_id": "danila"})
  }
  ```

---

## 4. План реализации

### 4.1. Шаг 1: Регистрация инструментов OpenCode в MCP
- **Файл**: `src/mcp/vetka_mcp_bridge.py`
- **Действия**:
  1. Добавить новые инструменты в `list_tools()`:
     ```python
     Tool(
         name="vetka_opencode_call",
         description="Call OpenCode models through MCP with VETKA memory context (STM, CAM, Engram).",
         inputSchema={
             "type": "object",
             "properties": {
                 "model_id": {"type": "string", "description": "Model ID (e.g., 'xai/grok-4')"},
                 "messages": {
                     "type": "array",
                     "items": {
                         "type": "object",
                         "properties": {
                             "role": {"type": "string", "enum": ["user", "assistant", "system"]},
                             "content": {"type": "string"}
                         },
                         "required": ["role", "content"]
                     }
                 },
                 "inject_context": {
                     "type": "object",
                     "description": "Context from VETKA memory (STM, CAM, Engram)",
                     "properties": {
                         "working_memory": {"type": "array", "description": "Recent conversation history"},
                         "current_files": {"type": "object", "description": "Active files in IDE"},
                         "user_preferences": {"type": "object", "description": "User communication style"}
                     }
                 }
             },
             "required": ["model_id", "messages"]
         }
     ),
     Tool(
         name="vetka_opencode_orchestrate",
         description="Orchestrate multi-model workflows through OpenCode (e.g., Grok → Architect → DeepSeek).",
         inputSchema={
             "type": "object",
             "properties": {
                 "command": {"type": "string", "description": "Orchestration command (e.g., 'Оркестрируй: Grok → Architect → DeepSeek')"},
                 "context": {
                     "type": "object",
                     "description": "Additional context for orchestration",
                     "properties": {
                         "user_id": {"type": "string", "description": "User ID"},
                         "current_task": {"type": "string", "description": "Current task description"}
                     }
                 }
             },
             "required": ["command"]
         }
     )
     ```

### 4.2. Шаг 2: Реализация обработчиков в MCP
- **Файл**: `src/mcp/vetka_mcp_bridge.py` (в методе `call_tool`)
- **Действия**:
  1. Добавить обработку новых инструментов:
     ```python
     elif name == "vetka_opencode_call":
         context = arguments.get("inject_context", {})
         prompt = self._format_prompt_with_context(arguments["messages"], context)
         response = await http_client.post(
             "/openrouter/invoke",
             json={
                 "model_id": arguments["model_id"],
                 "messages": [{"role": "user", "content": prompt}]
             }
         )
         return [TextContent(type="text", text=response.json().get("message", {}).get("content", ""))]

     elif name == "vetka_opencode_orchestrate":
         orchestrator = get_orchestrator()
         result = await orchestrator.orchestrate(
             arguments["command"],
             context=arguments.get("context", {})
         )
         return [TextContent(type="text", text=json.dumps(result))]
     ```

### 4.3. Шаг 3: Интеграция с общей памятью
- **Файл**: `src/mcp/tools/memory_tools.py`
- **Действия**:
  1. Использовать существующие инструменты для получения контекста:
     ```python
     stm_context = await mcp.call_tool("vetka_get_conversation_context", {"user_id": "danila"})
     cam_context = await mcp.call_tool("vetka_get_tree", {"format": "summary"})
     preferences = await mcp.call_tool("vetka_get_user_preferences", {"user_id": "danila"})
     ```

### 4.4. Шаг 4: Тестирование интеграции
- **Команды для проверки**:
  ```bash
  # Запуск MCP Bridge
  python -m src.mcp.vetka_mcp_bridge --http --port 5002

  # Тест вызова модели OpenCode через MCP
  curl -X POST http://localhost:5002/mcp -H "Content-Type: application/json" -d '{
      "tool_name": "vetka_opencode_call",
      "arguments": {
          "model_id": "xai/grok-4",
          "messages": [{"role": "user", "content": "Hello"}],
          "inject_context": {
              "working_memory": [{"role": "assistant", "content": "Previous message"}],
              "user_preferences": {"communication_style": "technical"}
          }
      }
  }'

  # Тест оркестрации через MCP
  curl -X POST http://localhost:5002/mcp -H "Content-Type: application/json" -d '{
      "tool_name": "vetka_opencode_orchestrate",
      "arguments": {
          "command": "Оркестрируй: Grok → Architect → DeepSeek → Implementation",
          "context": {
              "user_id": "danila",
              "current_task": "Optimize database queries"
          }
      }
  }'
  ```

---

## 5. Ожидаемые результаты
| **Компонент**          | **Текущее состояние**       | **После интеграции**                     |
|------------------------|-----------------------------|-------------------------------------------|
| Вызов моделей OpenCode | Прямые вызовы через API     | Вызовы через MCP с контекстом.            |
| Оркестрация            | Без интеграции с MCP        | Через MCP с поддержкой контекста.         |
| Память                 | Не используется             | Общая память VETKA MCP (STM, CAM, Engram). |
| Латентность            | Зависит от сети              | Оптимизировано за счет кэширования.       |

---

## 6. Следующие шаги
1. Реализовать инструменты `vetka_opencode_call` и `vetka_opencode_orchestrate` в `vetka_mcp_bridge.py`.
2. Протестировать интеграцию с OpenCode Bridge и общей памятью.
3. Документировать новые инструменты и примеры использования.

---

**Автор**: Claude Code Agent
**Дата**: 02.02.2026