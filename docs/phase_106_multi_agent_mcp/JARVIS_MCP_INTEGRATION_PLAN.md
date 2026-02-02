# План интеграции Jarvis в VETKA MCP

**Дата**: 02.02.2026
**Автор**: Claude Code Agent
**Цель**: Обеспечить работу Jarvis **только через MCP VETKA** с использованием **общей памяти** (STM, CAM, Engram) и инструментов OpenCode Bridge.

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
  - `/search/semantic`, `/files/read`, `/model/call`: Инструменты для поиска, работы с файлами и вызова LLM.
- **Пример**:
  ```bash
  curl -X POST http://localhost:5002/openrouter/invoke -H "Content-Type: application/json" -d '{"model_id": "xai/grok-4", "messages": [{"role": "user", "content": "Hello"}]}'
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

## 2. Новый план интеграции Jarvis

### 2.1. Цели
1. **Работа только через MCP**: Все вызовы Jarvis (голос, LLM, TTS) должны проходить через **VETKA MCP Bridge**.
2. **Общая память**: Использование **STM**, **CAM**, **Engram** для контекста.
3. **Минимальные изменения**: Использовать существующие инструменты OpenCode Bridge без модификации ядра.

---

## 3. Компоненты интеграции

### 3.1. Инструменты Jarvis в MCP
| **Инструмент**               | **Описание**                                                                 | **Реализация**                                                                 |
|------------------------------|-----------------------------------------------------------------------------|--------------------------------------------------------------------------------|
| `vetka_jarvis_voice`         | Голосовой ввод/вывод (STT/TTS) через OpenCode Bridge.                       | Использовать `/openrouter/invoke` для вызова моделей TTS/STT.                  |
| `vetka_jarvis_llm`           | Вызов LLM с контекстом из памяти (STM/CAM/Engram).                          | Использовать `/model/call` с инъекцией контекста.                              |
| `vetka_jarvis_orchestrator`  | Оркестрация многомодельных рабочих процессов (например, `Grok → Architect`). | Использовать `MultiModelOrchestrator`.                                        |

### 3.2. Маршрутизация через MCP
- **Пример вызова STT**:
  ```python
  stt_result = await mcp.call_tool(
      "vetka_jarvis_voice",
      {
          "action": "transcribe",
          "audio_base64": "<base64_audio>",
          "model": "whisper-mlx"
      }
  )
  ```

- **Пример вызова LLM**:
  ```python
  context = await mcp.call_tool("vetka_get_conversation_context", {"user_id": "danila"})
  llm_result = await mcp.call_tool(
      "vetka_jarvis_llm",
      {
          "model": "xai/grok-4",
          "messages": [{"role": "user", "content": "Hello"}],
          "inject_context": context
      }
  )
  ```

### 3.3. Общая память
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

### 4.1. Шаг 1: Регистрация инструментов Jarvis в MCP
- **Файл**: `src/mcp/vetka_mcp_bridge.py`
- **Действия**:
  1. Добавить новые инструменты в `list_tools()`:
     ```python
     Tool(
         name="vetka_jarvis_voice",
         description="Jarvis voice input/output using OpenCode Bridge models (Whisper, TTS).",
         inputSchema={
             "type": "object",
             "properties": {
                 "action": {"type": "string", "enum": ["transcribe", "synthesize"], "description": "Action type"},
                 "audio_base64": {"type": "string", "description": "Base64-encoded audio (for transcribe)"},
                 "text": {"type": "string", "description": "Text to synthesize (for TTS)"},
                 "model": {"type": "string", "description": "Model ID (e.g., 'whisper-mlx', 'qwen3-tts')", "default": "whisper-mlx"}
             },
             "required": ["action"]
         }
     ),
     Tool(
         name="vetka_jarvis_llm",
         description="Jarvis LLM call with VETKA memory context (STM, CAM, Engram).",
         inputSchema={
             "type": "object",
             "properties": {
                 "model": {"type": "string", "description": "Model ID (e.g., 'xai/grok-4')"},
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
             "required": ["model", "messages"]
         }
     )
     ```

### 4.2. Шаг 2: Реализация обработчиков в MCP
- **Файл**: `src/mcp/vetka_mcp_bridge.py` (в методе `call_tool`)
- **Действия**:
  1. Добавить обработку новых инструментов:
     ```python
     elif name == "vetka_jarvis_voice":
         action = arguments.get("action")
         if action == "transcribe":
             response = await http_client.post(
                 "/openrouter/invoke",
                 json={
                     "model_id": arguments.get("model", "whisper-mlx"),
                     "messages": [{"role": "user", "content": f"Transcribe: {arguments.get('audio_base64')}"}]
                 }
             )
             return [TextContent(type="text", text=response.json().get("message", {}).get("content", ""))]
         elif action == "synthesize":
             response = await http_client.post(
                 "/openrouter/invoke",
                 json={
                     "model_id": arguments.get("model", "qwen3-tts"),
                     "messages": [{"role": "user", "content": f"Synthesize: {arguments.get('text')}"}]
                 }
             )
             return [TextContent(type="audio", data=response.json().get("audio_base64", ""))]

     elif name == "vetka_jarvis_llm":
         context = arguments.get("inject_context", {})
         prompt = self._format_prompt_with_context(arguments["messages"], context)
         response = await http_client.post(
             "/model/call",
             json={
                 "model": arguments["model"],
                 "messages": [{"role": "user", "content": prompt}]
             }
         )
         return [TextContent(type="text", text=response.json().get("result", {}).get("message", ""))]
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

### 4.4. Шаг 4: Замена прямых вызовов на MCP в Jarvis
- **Файл**: `src/api/handlers/jarvis_handler.py`
- **Действия**:
  1. Заменить прямые вызовы STT/TTS/LLM на MCP-вызовы:
     ```python
     transcript = await mcp.call_tool("vetka_jarvis_voice", {"action": "transcribe", "audio_base64": audio_base64})
     context = await mcp.call_tool("vetka_get_conversation_context", {"user_id": user_id})
     response = await mcp.call_tool("vetka_jarvis_llm", {
         "model": "xai/grok-4",
         "messages": [{"role": "user", "content": transcript}],
         "inject_context": context
     })
     audio = await mcp.call_tool("vetka_jarvis_voice", {"action": "synthesize", "text": response})
     ```

---

## 5. Тестирование

### 5.1. Команды для проверки
```bash
# Запуск MCP Bridge
python -m src.mcp.vetka_mcp_bridge --http --port 5002

# Тест вызова Jarvis STT через MCP
curl -X POST http://localhost:5002/mcp -H "Content-Type: application/json" -d '{
    "tool_name": "vetka_jarvis_voice",
    "arguments": {
        "action": "transcribe",
        "audio_base64": "<base64_audio>",
        "model": "whisper-mlx"
    }
}'

# Тест вызова Jarvis LLM через MCP
curl -X POST http://localhost:5002/mcp -H "Content-Type: application/json" -d '{
    "tool_name": "vetka_jarvis_llm",
    "arguments": {
        "model": "xai/grok-4",
        "messages": [{"role": "user", "content": "Hello"}],
        "inject_context": {
            "working_memory": [{"role": "assistant", "content": "Previous message"}],
            "user_preferences": {"communication_style": "technical"}
        }
    }
}'
```

### 5.2. Ожидаемые результаты
| **Компонент**          | **Текущее состояние**       | **После интеграции**                     |
|------------------------|-----------------------------|-------------------------------------------|
| Голосовой ввод/вывод   | Прямые вызовы Whisper/TTS   | Вызовы через MCP (`vetka_jarvis_voice`).  |
| LLM                    | Без контекста               | Контекст из STM/CAM/Engram.                |
| Память                 | Не используется             | Общая память VETKA MCP.                    |
| Латентность            | ~8-10с                      | <4с (за счет оптимизации).                 |

---

## 6. Следующие шаги
1. Реализовать инструменты `vetka_jarvis_voice` и `vetka_jarvis_llm` в `vetka_mcp_bridge.py`.
2. Протестировать интеграцию с OpenCode Bridge и общей памятью.
3. Заменить прямые вызовы в `jarvis_handler.py` на MCP-вызовы.

---

**Автор**: Claude Code Agent
**Дата**: 02.02.2026