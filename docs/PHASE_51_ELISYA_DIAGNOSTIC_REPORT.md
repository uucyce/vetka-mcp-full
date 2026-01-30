# Phase 51: Elisya Context Assembly — ДИАГНОСТИКА

**Дата анализа:** 2026-01-07
**Цель:** Выявить где и как собирается контекст для агентов перед вызовом LLM

---

## 📂 [ELISYA_STATUS] Что есть в src/elisya/

```
src/elisya/
├── __init__.py              # Экспорты модулей Elisya
├── api_aggregator_v3.py     # Multi-provider LLM вызовы с фолбэком
├── api_gateway.py           # APIGateway: роутинг между Gemini/OpenRouter/Ollama
├── key_manager.py           # KeyManager: управление API ключами
├── llm_executor_bridge.py   # LLMExecutorBridge: мост между агентами и моделями
├── middleware.py            # ElisyaMiddleware: reframe() + update() контекста
├── model_fetcher.py         # Получение списка доступных моделей
├── model_router_v2.py       # ModelRouter: задача → оптимальная модель
├── semantic_path.py         # SemanticPathGenerator: генерация семантических путей
└── state.py                 # ElisyaState: состояние агента (контекст, LOD, few-shots)
```

**Ключевые компоненты:**
- ✅ **ElisyaMiddleware** (middleware.py) — reframe() для подготовки контекста
- ✅ **ElisyaState** (state.py) — хранит context, raw_context, few_shots, lod_level
- ✅ **ModelRouter** (model_router_v2.py) — выбирает модель по типу задачи
- ✅ **APIGateway** (api_gateway.py) — вызывает LLM через разные провайдеры

---

## 🔍 [CONTEXT_ASSEMBLY] Где собирается контекст

### 1️⃣ **Базовый контекст файла** → `handler_utils.py:48-92`

```python
def sync_get_rich_context(node_path: str) -> Dict[str, Any]:
    """
    Получает содержимое файла и метаданные.

    Returns:
        {
            'file_path': str,
            'file_content': str,  # Содержимое файла (до 8000 символов)
            'file_metadata': {'lines': int, 'size': int},
            'error': str | None
        }
    """
```

**Где используется:**
- `src/api/handlers/user_message_handler.py:207` — Direct model call (PHASE 48.1)
- `src/api/handlers/user_message_handler.py:404` — Agent chain call
- `src/api/handlers/user_message_handler.py:778` — Standard agent flow

### 2️⃣ **Форматирование для агента** → `handler_utils.py:95-127`

```python
def format_context_for_agent(rich_context: Dict, agent_type: str = 'generic') -> str:
    """
    Форматирует контекст файла в строку для LLM промпта.

    Формат:
        FILE: {file_path}
        LINES: {lines} | SIZE: {size} bytes

        CONTENT:
        ```
        {content}
        ```

    Truncates: content > 8000 chars → обрезается
    """
```

### 3️⃣ **Rich Context для Hostess** → `hostess_context_builder.py:38-104`

```python
def build_context(
    message: str,
    file_path: Optional[str] = None,
    conversation_id: Optional[str] = None,
    node_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Собирает полный контекст для Hostess routing решений.

    Включает:
    1. File context (via _get_file_context)
    2. Semantic context (via _get_elisya_context) — related_files, tags, snippets
    3. Conversation history (via _get_conversation_history) — last 5 messages
    4. Context summary (via _build_summary)

    Returns:
        {
            'message': str,
            'file_path': str,
            'node_path': str,
            'file_content': str,
            'file_type': str,
            'file_metadata': dict,
            'related_files': List[str],      # from Elisya
            'semantic_tags': List[str],      # from Elisya
            'knowledge_snippets': List[str], # from Elisya
            'recent_messages': List[dict],   # last 5 from history
            'has_file_context': bool,
            'has_semantic_context': bool,
            'has_history_context': bool,
            'context_summary': str           # human-readable summary
        }
    """
```

**Где используется:**
- ❌ **НЕ ИСПОЛЬЗУЕТСЯ в user_message_handler.py** — Hostess получает только базовый контекст!

### 4️⃣ **ElisyaMiddleware.reframe()** → `middleware.py:72-127`

```python
def reframe(self, state: ElisyaState, agent_type: str):
    """
    Reframe контекста для конкретного агента.

    Steps:
    1. Fetch history from state.semantic_path
    2. Truncate by LOD (Level of Detail)
    3. Add few-shots if available (score > threshold)
    4. Apply semantic tint filter
    5. ✅ Phase 15-3: Fetch similar context from Qdrant
    6. Return reframed state

    LOD Levels:
    - GLOBAL: 500 tokens (минимальный контекст)
    - TREE: 1500 tokens (уровень ветки)
    - LEAF: 3000 tokens (полный контекст агента)
    - FULL: 10000 tokens (вся история)
    """
```

**Где используется:**
- `src/orchestration/orchestrator_with_elisya.py` — оркестратор использует ElisyaMiddleware
- ❌ **НЕ ИСПОЛЬЗУЕТСЯ в user_message_handler.py** — прямые вызовы обходят middleware!

---

## 💬 [CHAT_HISTORY] Как передаётся история

### **Сохранение истории** → `handler_utils.py:134-169`

```python
def save_chat_message(node_path: str, message: Dict[str, Any]) -> None:
    """
    Phase 50: Persistent chat storage via ChatHistoryManager.

    Сохраняет:
    {
        'role': 'user' | 'assistant',
        'content': str,
        'agent': str,
        'model': str,
        'node_id': str,
        'metadata': dict
    }

    Persistence: data/chat_history.json
    """
```

### **Получение истории** → `hostess_context_builder.py:92-99`

```python
if self.memory_manager and conversation_id:
    history = self._get_conversation_history(conversation_id)
    context["recent_messages"] = history[-5:]  # Last 5 messages
```

### ❌ **ПРОБЛЕМА: История НЕ передаётся агентам в user_message_handler.py!**

**Что есть:**
- ✅ История сохраняется после каждого ответа (`save_chat_message`)
- ✅ ChatHistoryManager хранит историю в JSON
- ✅ HostessContextBuilder умеет извлекать историю

**Что отсутствует:**
- ❌ История НЕ загружается перед вызовом агента
- ❌ Агенты получают только текущий `text` без контекста прошлых сообщений
- ❌ ElisyaMiddleware не подключен к user_message_handler

---

## 📄 [FILE_CONTEXT] Как передаётся контекст файла

### **Путь контекста файла:**

```
1. Client отправляет:
   {
       text: "user message",
       node_path: "/path/to/file.py",
       node_id: "node_123"
   }

2. user_message_handler.py:207
   rich_context = sync_get_rich_context(node_path)
   → {'file_path', 'file_content', 'file_metadata', 'error'}

3. user_message_handler.py:211
   context_for_model = format_context_for_agent(rich_context, 'generic')
   → Formatted string для промпта

4. user_message_handler.py:214-222
   model_prompt = f"""You are a helpful AI assistant...

   {context_for_model}

   USER QUESTION: {text}
   """

5. Вызов LLM:
   - Ollama: ollama.chat(messages=[{'role': 'user', 'content': model_prompt}])
   - OpenRouter: httpx.post('/chat/completions', messages=[...])
```

### ✅ **Что работает:**
- Контекст файла корректно загружается через `sync_get_rich_context`
- Форматируется в читаемый вид через `format_context_for_agent`
- Добавляется в промпт перед вопросом пользователя

### ⚠️ **Что можно улучшить:**
- Сейчас контекст файла — просто текст в промпте
- Нет структурированного контекста (AST, imports, dependencies)
- Нет semantic context (related files, knowledge snippets) из Elisya

---

## ⚠️ [GAP_ANALYSIS] Что отсутствует

### 1️⃣ **ElisyaMiddleware НЕ подключен к user_message_handler**

**Текущая схема:**
```
User message → user_message_handler.py
             → sync_get_rich_context(node_path)  # Только файл!
             → format_context_for_agent()
             → model_prompt = f"File: {context}\n\nQuestion: {text}"
             → Ollama/OpenRouter call
```

**Что ДОЛЖНО быть (с ElisyaMiddleware):**
```
User message → user_message_handler.py
             → ElisyaState(raw_context=file_content, semantic_path=node_path)
             → ElisyaMiddleware.reframe(state, agent_type='PM')
                ├── Truncate by LOD level
                ├── Add few-shots examples
                ├── Apply semantic tint
                └── Fetch similar context from Qdrant
             → model_prompt = build_full_prompt(agent='PM', context=state.context, user_text=text)
             → Ollama/OpenRouter call
```

### 2️⃣ **Chat History НЕ передаётся агентам**

**Есть:**
- ✅ `ChatHistoryManager` сохраняет историю
- ✅ `HostessContextBuilder.build_context()` умеет загружать последние 5 сообщений

**Нет:**
- ❌ В `user_message_handler.py` история НЕ загружается
- ❌ Агенты получают только текущий `text`, без контекста диалога
- ❌ Нет механизма передачи `conversation_id` в ElisyaState

**Что нужно добавить:**
```python
# В user_message_handler.py
conversation_id = data.get('conversation_id') or client_id

# Загрузить историю
from src.chat.chat_history_manager import get_chat_history_manager
manager = get_chat_history_manager()
chat_id = manager.get_or_create_chat(node_path)
history = manager.get_messages(chat_id, limit=10)

# Передать в state
state = ElisyaState(
    raw_context=file_content,
    semantic_path=node_path,
    conversation_history=history  # ← NEW!
)
```

### 3️⃣ **Semantic Context (Elisya) НЕ используется**

**ElisyaMiddleware умеет:**
- ✅ Искать похожие контексты через Qdrant (`fetch_similar_context`)
- ✅ Применять semantic tint filter (`_apply_tint_filter`)
- ✅ Добавлять few-shot examples

**Но в user_message_handler.py:**
- ❌ Прямые вызовы обходят ElisyaMiddleware
- ❌ Нет Qdrant поиска похожих файлов
- ❌ Нет few-shot примеров для улучшения качества

### 4️⃣ **Системные промпты агентов НЕ используют rich context**

**Сейчас (role_prompts.py):**
```python
PM_SYSTEM_PROMPT = """You are PM in VETKA AI team.

## YOUR ROLE
- Analyze user requests...
"""

# В user_message_handler: просто concatenation
model_prompt = f"{PM_SYSTEM_PROMPT}\n\n{context_for_model}\n\nUser: {text}"
```

**Что нужно:**
```python
def build_agent_prompt(agent_type: str, elisya_state: ElisyaState, user_text: str) -> str:
    """
    Build full prompt with:
    - System prompt (role-specific)
    - File context (formatted)
    - Conversation history (last N messages)
    - Few-shot examples (if available)
    - Semantic hints (related files, snippets)
    - User question
    """
    system = get_system_prompt(agent_type)

    # Add file context
    if elisya_state.context:
        prompt += f"\n\n## FILE CONTEXT\n{elisya_state.context}"

    # Add conversation history
    if elisya_state.conversation_history:
        prompt += f"\n\n## CONVERSATION HISTORY\n"
        for msg in elisya_state.conversation_history[-5:]:
            prompt += f"{msg['role']}: {msg['content']}\n"

    # Add few-shots
    if elisya_state.few_shots:
        prompt += f"\n\n## EXAMPLES\n"
        for example in elisya_state.few_shots:
            prompt += f"Input: {example.input}\nOutput: {example.output}\n\n"

    # Add user question
    prompt += f"\n\n## USER QUESTION\n{user_text}"

    return prompt
```

### 5️⃣ **BaseAgent.call_llm() НЕ использует rich context**

**Сейчас (base_agent.py:63-154):**
```python
def call_llm(self, prompt: str, context: str = "", max_tokens: int = None) -> str:
    full_prompt = f"{context}\n\n{prompt}" if context else prompt
    # ... вызов OpenRouter/Gemini/Ollama
```

**Проблема:**
- `context` — просто строка, без структуры
- Нет поддержки conversation history
- Нет интеграции с ElisyaMiddleware

**Что нужно:**
```python
def call_llm(self, elisya_state: ElisyaState, user_text: str, max_tokens: int = None) -> str:
    """
    Call LLM with rich context from ElisyaState.

    Args:
        elisya_state: State with context, history, few-shots
        user_text: Current user message
    """
    # Reframe context for this agent type
    reframed_state = self.elisya_middleware.reframe(elisya_state, self.role)

    # Build full prompt
    full_prompt = build_agent_prompt(self.role, reframed_state, user_text)

    # Call LLM
    # ...
```

---

## 📊 ИТОГОВАЯ СХЕМА ТЕКУЩЕЙ АРХИТЕКТУРЫ

### **Что работает (✅):**

```
┌─────────────────────────────────────────────────────┐
│ Client (React)                                      │
│ Sends: { text, node_path, node_id, model }         │
└──────────────────┬──────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────┐
│ user_message_handler.py                             │
│                                                     │
│ 1. Parse @mentions (parse_mentions)                │
│ 2. Get file context (sync_get_rich_context)        │ ✅ Работает
│ 3. Format context (format_context_for_agent)       │ ✅ Работает
│ 4. Build simple prompt:                            │
│    "File: {context}\nUser: {text}"                 │
│ 5. Call LLM (Ollama/OpenRouter)                    │ ✅ Работает
│ 6. Save to chat history (save_chat_message)        │ ✅ Работает
│                                                     │
└──────────────────┬──────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────┐
│ BaseAgent.call_llm()                                │
│ - Simple prompt concatenation                       │ ✅ Работает
│ - Provider routing (OpenRouter/Gemini/Ollama)       │ ✅ Работает
│                                                     │
└─────────────────────────────────────────────────────┘
```

### **Что НЕ используется (❌):**

```
┌─────────────────────────────────────────────────────┐
│ ElisyaMiddleware (src/elisya/middleware.py)         │
│ ❌ reframe() — не вызывается                         │
│ ❌ fetch_similar_context(Qdrant) — не используется   │
│ ❌ LOD truncation — не применяется                   │
│ ❌ Few-shot examples — не добавляются                │
└─────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────┐
│ HostessContextBuilder                               │
│ ❌ build_context() — создаёт rich context            │
│    но Hostess НЕ получает его в user_message_handler│
│ ❌ semantic_tags, related_files — НЕ передаются      │
│ ❌ conversation history — НЕ загружается для агентов │
└─────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────┐
│ ChatHistoryManager                                  │
│ ✅ save_chat_message() — история сохраняется         │
│ ❌ get_messages() — история НЕ загружается в промпт  │
│ ❌ Агенты не видят прошлые сообщения                 │
└─────────────────────────────────────────────────────┘
```

---

## 🎯 РЕКОМЕНДАЦИИ

### **Критично (должно быть в Phase 51):**

1. **Интегрировать ElisyaMiddleware в user_message_handler.py**
   - Создавать `ElisyaState` перед вызовом агента
   - Вызывать `middleware.reframe(state, agent_type)`
   - Использовать `state.context` вместо простого `context_for_model`

2. **Загружать chat history перед вызовом агента**
   - Получать `conversation_id` из клиента
   - Загружать последние 5-10 сообщений через `ChatHistoryManager`
   - Передавать в `ElisyaState.conversation_history`

3. **Создать `build_agent_prompt()` функцию**
   - Объединить system prompt + file context + history + few-shots
   - Использовать структурированный формат, а не простую конкатенацию

### **Важно (можно в Phase 52):**

4. **Подключить Qdrant semantic search**
   - Включить `fetch_similar_context()` в ElisyaMiddleware
   - Добавлять `related_files` и `knowledge_snippets` в контекст

5. **Рефакторить BaseAgent.call_llm()**
   - Изменить сигнатуру: `call_llm(elisya_state, user_text)`
   - Автоматически использовать `middleware.reframe()`

6. **Использовать HostessContextBuilder для Hostess**
   - Передавать rich context в `HostessAgent.process()`
   - Улучшить качество routing решений

---

## 📝 ВЫВОДЫ

### ✅ **Что уже работает:**
- Базовый контекст файла (`sync_get_rich_context`)
- Форматирование для LLM (`format_context_for_agent`)
- Сохранение истории чата (`save_chat_message`)
- Multi-provider LLM вызовы (OpenRouter/Gemini/Ollama)
- Model routing (ModelRouter v2)

### ❌ **Главные проблемы:**
1. **ElisyaMiddleware не подключен** — вся логика reframe/LOD/few-shots не используется
2. **Chat history не загружается** — агенты не видят прошлые сообщения
3. **Semantic context не используется** — Qdrant, related_files игнорируются
4. **Простая конкатенация промптов** — вместо структурированной сборки контекста

### 🎯 **Следующий шаг (Phase 51.1):**
Создать **Context Assembly Pipeline** в `user_message_handler.py`:
```python
def assemble_context_for_agent(
    agent_type: str,
    user_text: str,
    node_path: str,
    conversation_id: str,
    elisya_middleware: ElisyaMiddleware
) -> str:
    """
    Phase 51.1: Full context assembly pipeline.

    Steps:
    1. Load file context
    2. Load chat history
    3. Create ElisyaState
    4. Reframe via middleware
    5. Build structured prompt
    6. Return ready-to-use prompt
    """
```

---

**🚀 Phase 51 Goal:** Интегрировать все существующие компоненты в единый pipeline сборки контекста, чтобы агенты получали полный, структурированный контекст перед каждым вызовом LLM.
