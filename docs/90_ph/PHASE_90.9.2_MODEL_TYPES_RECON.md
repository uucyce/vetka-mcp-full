# ФАЗА 90.9.2: ТИПЫ МОДЕЛЕЙ И МАРШРУТИЗАЦИЯ - РАЗВЕДКА

**Статус:** РАЗВЕДКА ЗАВЕРШЕНА
**Дата:** 2026-01-23
**Автор:** Claude Haiku 4.5
**Версия:** 1.0
**Тип:** Аудит архитектуры маршрутизации моделей

---

## EXECUTIVE SUMMARY

VETKA имеет **4 полностью независимых маршрута маршрутизации моделей**, каждый с собственной логикой обнаружения провайдера. Проблема усугубляется тем, что группы чатов имеют более 15+ эндпоинтов только для управления моделями и агентами, что делает систему хрупкой и сложной для поддержки.

### Ключевые метрики
- **Файлы с логикой обнаружения провайдера:** 4
- **Перекрытия логики обнаружения:** 3 различные реализации одного алгоритма
- **Поддерживаемые провайдеры:** 7 (OpenAI, Anthropic, Google/Gemini, Ollama, OpenRouter, xAI, локальные)
- **Эндпоинты для управления моделями:** 11+
- **Критический статус:** ВЫСОКИЙ - риск разрывов при добавлении новых провайдеров

---

## 1. АРХИТЕКТУРА МАРШРУТИЗАЦИИ

```
┌─────────────────────────────────────────────────────────────────────┐
│                    VETKA MODEL ROUTING ARCHITECTURE                 │
└─────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────┐
│層 1: ENTRY POINTS (Входные точки)                             │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  [SOLO CHAT]          [GROUP CHAT]      [MCP TOOLS]    [ORCHESTRATOR] │
│       │                    │                  │              │      │
│  Пользователь        Группа сообщений    MCP клиент    Агенты     │
│  выбирает модель     создана админом     вызывает       работают   │
│       │                    │              tool           вместе    │
└──────────────────┬────────┬───────────────┬───────────────┬──────┘
                   │        │               │               │
┌──────────────────────────────────────────────────────────────────┐
│層 2: ROUTING PATHS (Пути маршрутизации)                       │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  user_message_handler.py    group_message_handler.py           │
│  ↓ detect_provider()        ↓ select_responding_agents()       │
│  ↓ Streaming logic          ↓ Pass model_id to orchestrator   │
│                                                                  │
│                     llm_call_tool.py                            │
│                     ↓ _detect_provider()                        │
│                     ↓ Direct to call_model_v2()               │
│                                                                  │
│                     orchestrator_with_elisya.py                │
│                     ↓ Manual routing (lines 1113-1144)         │
│                     ↓ Task-based routing                       │
│                                                                  │
└──────────────────┬────────────────────────────────────────────┘
                   │
┌──────────────────────────────────────────────────────────────────┐
│層 3: PROVIDER REGISTRY (Центральный реестр)                     │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│          ProviderRegistry.detect_provider()                     │
│          ↓ CANONICAL implementation                            │
│          ↓ Returns: Provider enum                              │
│                                                                  │
│  ┌──────────────────────────────────────────────┐              │
│  │ Supported Providers:                         │              │
│  │ - OPENAI (gpt-4, gpt-4o)                    │              │
│  │ - ANTHROPIC (claude-opus, claude-sonnet)    │              │
│  │ - GOOGLE/GEMINI (gemini-2.0)                │              │
│  │ - OLLAMA (llama3:8b, qwen:7b) - LOCAL       │              │
│  │ - OPENROUTER (aggregator)                   │              │
│  │ - XAI (grok-4) - x.ai / Grok                │              │
│  └──────────────────────────────────────────────┘              │
│                                                                  │
└──────────────────┬────────────────────────────────────────────┘
                   │
┌──────────────────────────────────────────────────────────────────┐
│層 4: PROVIDERS (Конкретные реализации)                         │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  OpenAIProvider      AnthropicProvider    GoogleProvider        │
│  - Native tools      - Native tools       - Native tools        │
│  - API: api.openai   - API: api.anthropic- API: googleapis      │
│                                                                  │
│  OllamaProvider      OpenRouterProvider   XaiProvider           │
│  - Local execution   - Aggregator API     - OpenAI-compatible   │
│  - No external key   - Route to providers - 24h timestamp limit │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘

```

---

## 2. ЧЕТЫРЕ МАРШРУТА МАРШРУТИЗАЦИИ

### МАРШРУТ 1: SOLO CHAT (Одиночный чат)

**Файл:** `/src/api/handlers/user_message_handler.py`
**Точка входа:** `handle_user_message()` (строка 142)

#### Поток

```
1. Пользователь отправляет сообщение
   ↓
2. Проверка requested_model (строка 227)
   - Если есть: detect_provider() → прямой вызов LLM
   - Если нет: select agent chain ['PM', 'Dev', 'QA']
   ↓
3. Прямой вызов LLM (строки 231-590)
   - Ollama? → локальный вызов (строки 247-359)
   - OpenRouter? → streaming с ротацией ключей (строки 372-590)
   - Именованный? → парсинг из @mentions (строки 606-890)
   ↓
4. Streaming поддержка и fallback
   - Попытка 1: streaming
   - Попытка 2: non-streaming (если stream упал)
   - Попытка 3: fallback к другому провайдеру
```

#### Обнаружение провайдера (Solo)

**Функция:** `chat_handler.detect_provider()` (строка 48-86)

```python
# WRAPPER вокруг canonical detect_provider
def detect_provider(model_name: str) -> ModelProvider:
    # Использует ProviderRegistry.detect_provider() - CANONICAL
    canonical_provider = ProviderRegistry.detect_provider(model_name)
    # Преобразует Provider enum в ModelProvider enum
    # Обработка legacy провайдеров (deepseek, groq)
```

**Поддерживаемые форматы:**
- `gpt-4o`, `gpt-4-turbo` → OpenAI
- `claude-opus-4-5`, `claude-sonnet` → Anthropic
- `gemini-2.0-flash` → Google
- `llama3:8b`, `qwen2:7b` → Ollama (LOCAL)
- `x-ai/grok-4`, `xai/grok-4`, `grok-4` → xAI
- `mistral-7b`, `meta-llama/llama-3` → OpenRouter (fallback)

#### Ключевые особенности

- **Управление ключами:** Ротация при 401/402 (строки 384-501)
- **Streaming:** Поддержка для Ollama и OpenRouter
- **Fallback:** Если streaming падает, переход на non-streaming
- **Цена:** Не контролируется (потому что прямой вызов)

---

### МАРШРУТ 2: GROUP CHAT (Групповой чат)

**Файл:** `/src/api/handlers/group_message_handler.py`
**Точка входа:** `handle_group_message()` (строка 501)

#### Поток

```
1. Пользователь отправляет сообщение в группу
   ↓
2. Выбор отвечающих агентов (строка 621)
   - @mention routing? → только указанные агенты
   - Keyword-based? → keyword-matching агенты
   - Default? → админ или первый worker
   ↓
3. Для каждого выбранного агента:
   orchestrator.call_agent(
       agent_type='Dev',
       model_id='openai/gpt-4o',  ← ВОТ ЗДЕСЬ!
       prompt=prompt
   )
   ↓
4. Оркестратор обнаруживает провайдера из model_id
   ↓
5. Использует call_model_v2() с явным Provider enum
```

#### Обнаружение провайдера (Group)

**NO DIRECT DETECTION IN group_message_handler.py**

- Группа создается с `model_id` для каждого участника
- `model_id` уже содержит информацию о провайдере: `"openai/gpt-4o"`, `"ollama/qwen:7b"`
- Обнаружение провайдера **делегируется оркестратору**

#### Ключевые особенности

- **Явная модель на участника:** Каждый агент имеет назначенную модель
- **MCP обработка:** фаза 80.13 - уведомление внешних MCP агентов
- **Умный выбор агентов:** Keyword-based matching (строки 92-208)

---

### МАРШРУТ 3: MCP TOOLS (Внешние MCP инструменты)

**Файл:** `/src/mcp/tools/llm_call_tool.py`
**Класс:** `LLMCallTool.execute()` (строка 136)

#### Поток

```
1. MCP клиент вызывает vetka_call_model tool
   ↓
2. _detect_provider(model_name) (строка 95)
   - ТЕПЕРЬ ИСПОЛЬЗУЕТ canonical detect_provider ✅
   ↓
3. call_model_v2(messages, model, provider, **kwargs)
   ↓
4. registry.get(provider).call()
   - Каждый провайдер вызывает свой call() метод
   ↓
5. Результат возвращается MCP клиенту
```

#### Обнаружение провайдера (MCP)

**Функция:** `LLMCallTool._detect_provider()` (строка 95-111)

```python
# MARKER_90.1.4.1_START: Use canonical detect_provider
def _detect_provider(self, model: str) -> str:
    from src.elisya.provider_registry import ProviderRegistry

    canonical_provider = ProviderRegistry.detect_provider(model)
    return canonical_provider.value  # Возвращает строку
# MARKER_90.1.4.1_END
```

#### Ключевые особенности

- **Прямое использование canonical** - UNIFIED ✅
- **Поддержка tools:** Передаёт tools параметр при поддержке
- **Нормализация имён:** Алиасы для коротких имён (grok → grok-4)
- **Chat streaming:** MARKER_90.4.0 - "Молния" group chat для результатов

---

### МАРШРУТ 4: ORCHESTRATOR (Оркестратор агентов)

**Файл:** `/src/orchestration/orchestrator_with_elisya.py`
**Метод:** `_run_agent_with_elisya_async()` (строка 1094)

#### Поток

```
1. call_agent(agent_type='Dev', model_id='gpt-4o', prompt)
   ↓
2. Обнаружение провайдера (строки 1113-1144)
   - Ручное переопределение: проверка slash-format
     "openai/gpt-4o" → "openai"
     "x-ai/grok-4" → "xai" (с нормализацией)
   ↓
3. ИЛИ Auto-detection: _get_routing_for_task()
   - Анализирует тип задачи из контекста
   - Определяет оптимальный провайдер
   ↓
4. Преобразование в Provider enum (строки 1182-1196)
   ↓
5. _call_llm_with_tools_loop(provider=Provider.OPENAI)
   ↓
6. call_model_v2(provider=Provider.OPENAI)
```

#### Обнаружение провайдера (Orchestrator)

**Функция 1:** Manual override (строки 1113-1144)

```python
if '/' in manual_model:
    real_provider = manual_model.split('/')[0].replace('-', '')
    # "x-ai/grok-4" → "xai"
    # "openai/gpt-4o" → "openai"
    if real_provider == 'xai':
        # Проверить ключ xai, fallback to OpenRouter
```

**Функция 2:** Task-based routing (строка 1147)

```python
routing = self._get_routing_for_task(
    str(state.context or '')[:100],  # Контекст задачи
    agent_type                         # PM/Dev/QA/etc
)
# Возвращает: {'provider': 'openai', 'model': 'gpt-4o'}
```

#### Ключевые особенности

- **Двойная маршрутизация:** Manual override + auto-detection
- **XAI специальная обработка:** Проверка ключей, fallback to OpenRouter
- **Task-aware:** Выбирает провайдера по типу задачи
- **Provider enum:** Явно преобразует в Provider enum перед call_model_v2()

---

## 3. CANONICAL PROVIDER DETECTION

**Файл:** `/src/elisya/provider_registry.py` (строки 786-810)

**MARKER_90.1.4.1_START: CANONICAL detect_provider**

```python
@staticmethod
def detect_provider(model_name: str) -> Provider:
    """
    Обнаруживает провайдера по имени модели.
    FALLBACK - оркестратор должен передавать провайдера явно.

    CANONICAL IMPLEMENTATION - используется везде!
    """
    model_lower = model_name.lower()

    # OpenAI detection
    if model_lower.startswith('openai/') or model_lower.startswith('gpt-'):
        return Provider.OPENAI

    # Anthropic detection
    elif model_lower.startswith('anthropic/') or model_lower.startswith('claude-'):
        return Provider.ANTHROPIC

    # Google detection
    elif model_lower.startswith('google/') or model_lower.startswith('gemini'):
        return Provider.GOOGLE

    # XAI/Grok detection (PHASE 90.1.4.1)
    elif model_lower.startswith('xai/') or model_lower.startswith('x-ai/') \
         or model_lower.startswith('grok'):
        return Provider.XAI

    # Ollama detection (LOCAL)
    elif ':' in model_name or model_lower.startswith('ollama/'):
        return Provider.OLLAMA

    # OpenRouter detection (fallback)
    elif '/' in model_name:
        return Provider.OPENROUTER

    # Default to local
    else:
        return Provider.OLLAMA

# MARKER_90.1.4.1_END
```

### Provider enum

```python
class Provider(Enum):
    """Поддерживаемые провайдеры"""
    OPENAI = "openai"          # GPT models
    ANTHROPIC = "anthropic"    # Claude models
    GOOGLE = "google"          # Gemini (via API)
    GEMINI = "gemini"          # Alias for google (Phase 80.41)
    OLLAMA = "ollama"          # Local models
    OPENROUTER = "openrouter"  # Aggregator
    XAI = "xai"                # x.ai / Grok (Phase 80.35)
```

---

## 4. ПОДДЕРЖИВАЕМЫЕ ПРОВАЙДЕРЫ

### 1. OpenAI (GPT)

**Модели:** `gpt-4o`, `gpt-4-turbo`, `gpt-3.5-turbo`
**Форматы имён:**
- `gpt-4o` (коротко)
- `openai/gpt-4o` (с префиксом)

**Поддержка tools:** ✅ Yes (native)
**API:** https://api.openai.com/v1/chat/completions
**Ключ:** `OPENAI_API_KEY`

**Реализация:** `/src/elisya/provider_registry.py` (строки 93-171)

---

### 2. Anthropic (Claude)

**Модели:** `claude-opus-4-5`, `claude-sonnet-4-5`, `claude-haiku-4-5`
**Форматы имён:**
- `claude-opus-4-5` (коротко)
- `anthropic/claude-opus-4-5` (с префиксом)

**Поддержка tools:** ✅ Yes (native)
**API:** https://api.anthropic.com/v1/messages
**Ключ:** `ANTHROPIC_API_KEY`

**Реализация:** `/src/elisya/provider_registry.py` (строки 174-286)

---

### 3. Google (Gemini)

**Модели:** `gemini-2.0-flash`, `gemini-1.5-pro`, `gemini-1.5-flash`
**Форматы имён:**
- `gemini-2.0-flash` (коротко)
- `google/gemini-2.0-flash` (с префиксом)

**Поддержка tools:** ✅ Yes (native)
**API:** https://generativelanguage.googleapis.com/v1beta/models/.../generateContent
**Ключ:** `GEMINI_API_KEY` (в config.json хранится как "gemini")

**Реализация:** `/src/elisya/provider_registry.py` (строки 289-402)
**Примечание:** Phase 80.41 - alias "gemini" для совместимости с config.json

---

### 4. Ollama (Локальные модели)

**Модели:** `llama3:8b`, `qwen2:7b`, `deepseek-llm:7b`, `mistral:7b`
**Форматы имён:**
- `qwen2:7b` (коротко с тегом)
- `ollama/qwen2:7b` (с префиксом)

**Поддержка tools:** ✅ Yes (but not all models)
**Host:** http://localhost:11434 (по умолчанию)
**Модели БЕЗ tools:**
- deepseek-llm
- llama2
- codellama
- mistral (некоторые версии)
- phi, gemma, orca-mini, vicuna

**Реализация:** `/src/elisya/provider_registry.py` (строки 405-548)
**Особенность:** Phase 80.5 - проверка поддержки tools, retry без tools при ошибке

---

### 5. OpenRouter (Агрегатор)

**Модели:** Любая модель OpenRouter
**Форматы имён:**
- `mistralai/mistral-7b`
- `anthropic/claude-opus`
- `openrouter/...`
- Любой формат с `/` внутри (fallback)

**Поддержка tools:** ❌ Limited
**API:** https://openrouter.ai/api/v1/chat/completions
**Ключ:** `OPENROUTER_API_KEY`

**Реализация:** `/src/elisya/provider_registry.py` (строки 551-620)

---

### 6. xAI (Grok)

**Модели:** `grok-4`, `grok-4v`, `grok-2`
**Форматы имён:**
- `grok-4` (коротко)
- `xai/grok-4` (с префиксом)
- `x-ai/grok-4` (нормализуется в xai)

**Поддержка tools:** ✅ Yes (OpenAI-compatible)
**API:** https://api.x.ai/v1/chat/completions
**Ключ:** `XAI_API_KEY`

**Особенности:**
- Phase 80.35: Интеграция Grok
- Phase 80.37: xai fallback to openrouter when API key not found
- Phase 80.38: xai key detection fix
- Phase 80.39: XaiKeysExhausted exception for 403 errors
- Phase 80.40: Fixed bugs - singleton usage + attribute names

**Реализация:** `/src/elisya/provider_registry.py` (строки 623-726)

---

## 5. УПРАВЛЕНИЕ API КЛЮЧАМИ

**Файл:** `/src/orchestration/services/api_key_service.py`

### APIKeyService

```python
class APIKeyService:
    """Управление API ключами с ротацией и fallback"""

    def get_key(self, provider: str) -> Optional[str]:
        """Получить активный ключ для провайдера"""
        provider_map = {
            'openrouter': ProviderType.OPENROUTER,
            'gemini': ProviderType.GEMINI,
            'google': ProviderType.GEMINI,     # Alias
            'ollama': ProviderType.OLLAMA,
            'xai': ProviderType.XAI,           # x.ai (Grok)
            'openai': ProviderType.OPENAI,
            'anthropic': ProviderType.ANTHROPIC,
            'tavily': ProviderType.TAVILY,
        }
```

**Важное:** Phase 51.3 - ключи загружаются ТОЛЬКО из config.json, не из окружения!

### Ротация ключей

- Phase 80.37: Автоматическое переключение при 401/402 (OpenRouter)
- Phase 80.39: xAI key rotation при 403 + fallback to OpenRouter
- Phase 80.40: Исправления bugs - singleton, правильные имена атрибутов

---

## 6. ГРУППЫ ЧАТ - ЭНДПОИНТЫ И МАРШРУТЫ

### Основные эндпоинты группы

```
POST   /api/groups                          → Создать группу
GET    /api/groups                          → Получить все группы
GET    /api/groups/{group_id}              → Получить конкретную группу
PUT    /api/groups/{group_id}              → Обновить группу
DELETE /api/groups/{group_id}              → Удалить группу

POST   /api/groups/{group_id}/messages     → Отправить сообщение в группу
GET    /api/groups/{group_id}/messages     → История сообщений
POST   /api/groups/{group_id}/settings     → Обновить настройки
```

### Внутренние маршруты (Socket.IO)

```
Socket Event: chat_message
  └─ group_message_handler.handle_group_message()
     ├─ select_responding_agents()  → Выбор агентов
     └─ orchestrator.call_agent()   → Вызов каждого агента
        └─ _run_agent_with_elisya_async()
           └─ Provider detection (4 пути)

Socket Event: group_created
  └─ Обновление клиента со списком групп

Socket Event: agent_response
  └─ Отправка ответа агента клиентам
```

### Управление моделями в группе

**При создании группы:**
```python
{
    "name": "Dev Team",
    "participants": [
        {
            "agent_id": "@Architect",
            "agent_type": "Architect",
            "model_id": "openai/gpt-4o",      # ← Модель назначена здесь
            "display_name": "Architect (GPT 4o)"
        },
        {
            "agent_id": "@Dev",
            "agent_type": "Dev",
            "model_id": "ollama/qwen2:7b",    # ← Модель назначена здесь
            "display_name": "Dev (Qwen 7B)"
        }
    ]
}
```

**При обновлении участника:**
- Изменение `model_id` не требует пересоздания группы
- Новая модель используется сразу же в следующем вызове

---

## 7. ПРОБЛЕМЫ И СЛОЖНОСТЬ

### Проблема 1: НЕСОГЛАСОВАННОСТЬ ОБНАРУЖЕНИЯ ПРОВАЙДЕРА

**Статус:** ЧАСТИЧНО РЕШЕНО (Phase 90.1.4.1) ✅

**Было:**
- `chat_handler.detect_provider()` → ModelProvider enum
- `llm_call_tool._detect_provider()` → provider string
- `orchestrator._run_agent_with_elisya_async()` → inline slash/prefix matching
- `provider_registry.detect_provider()` → Provider enum

**Теперь:**
- ✅ `chat_handler.detect_provider()` - WRAPPER вокруг canonical (строка 48-86)
- ✅ `llm_call_tool._detect_provider()` - использует canonical (строка 95-111)
- ⚠️ `orchestrator` - ВСЁ ЕЩЕ использует inline логику (строки 1113-1144)
- ✅ `provider_registry.detect_provider()` - CANONICAL

**Оставшаяся работа:** Обновить orchestrator для использования canonical detect_provider

---

### Проблема 2: СЛИШКОМ МНОГО ЭНДПОИНТОВ ДЛЯ ГРУППЫ

**Текущее состояние:**

| Назначение | Эндпоинты | Примечание |
|-----------|-----------|-----------|
| CRUD группы | 5 | POST/GET/PUT/DELETE |
| Сообщения | 2 | POST/GET |
| Настройки | 1+ | PUT /settings |
| Участники | ? | Встроено в группе |
| Модели | 0 явных | Управляется через participants |
| MCP обработка | 1+ | Socket event для @mentions |
| Поддержка инструментов | 1+ | Передача tools через orchestrator |

**РИСК:** Добавление нового типа провайдера требует обновления в 4 местах

---

### Проблема 3: AMBIGUOUS MODEL_ID FORMAT

**Текущее состояние:**

```
Возможные форматы:
- "ollama/qwen:7b"      (с префиксом и тегом)
- "qwen:7b"             (без префикса, с тегом)
- "gpt-4o"              (коротко, без префикса)
- "openai/gpt-4o"       (с префиксом)
- "x-ai/grok-4"         (с префиксом, нормализуется в xai)
- "grok-4"              (коротко)
```

**ПРОБЛЕМА:** Парсирование через `split('/')[0]` предполагает slash-format

```python
# orchestrator_with_elisya.py, line 1121
if '/' in manual_model:
    real_provider = manual_model.split('/')[0]
    # Это НЕПРАВИЛЬНО для "claude-opus-4-5" (нет слэша)
```

---

### Проблема 4: XAI KEY DETECTION РАЗБРОСАНА

**Строки кода:**

1. `orchestrator_with_elisya.py` lines 1121-1125
   ```python
   # Проверка ключа xai для fallback
   from src.orchestration.services.api_key_service import APIKeyService
   if not APIKeyService().get_key('xai'):
       real_provider = 'openrouter'
   ```

2. `provider_registry.py` lines 677-706
   ```python
   # Phase 80.39: Handle 403, rotate key, fallback to OpenRouter
   if response.status_code == 403:
       key_manager = get_key_manager()
       # Mark as rate-limited, try next key
       # If all 403, raise XaiKeysExhausted()
   ```

**РИСК:** Две разные стратегии - может быть несогласованное поведение

---

### Проблема 5: TOOL SUPPORT РАЗНООБРАЗНЫЙ

| Провайдер | Поддержка Tools | Примечания |
|-----------|-----------------|-----------|
| OpenAI | ✅ Yes | Native function_calling |
| Anthropic | ✅ Yes | Native tool_use |
| Google | ✅ Yes | functionCall format |
| Ollama | ⚠️ Partial | Не все модели (фаза 80.5) |
| OpenRouter | ❌ Limited | Отключено в коде |
| xAI | ✅ Yes | OpenAI-compatible |

**ПРОБЛЕМА:** Систематически NO UNIFIED WAY для определения поддержки tools перед вызовом

---

## 8. ЗАВИСИМЫЕ ФАЙЛЫ

### Основные файлы маршрутизации

1. **`/src/elisya/provider_registry.py`** (915 строк)
   - CANONICAL Provider enum и detect_provider()
   - BaseProvider interface
   - Все 6+ реализаций провайдеров
   - ProviderRegistry singleton
   - call_model_v2() функция

2. **`/src/orchestration/services/api_key_service.py`** (219 строк)
   - API key management
   - Provider mapping
   - Key rotation interface

3. **`/src/api/handlers/chat_handler.py`** (100+ строк)
   - detect_provider() WRAPPER
   - ModelProvider enum (legacy)

4. **`/src/api/handlers/user_message_handler.py`** (1695 строк)
   - Solo chat routing
   - Direct LLM calls
   - Streaming logic
   - Key rotation for OpenRouter

5. **`/src/api/handlers/group_message_handler.py`** (893 строки)
   - Group chat routing
   - Agent selection
   - MCP @mention handling

6. **`/src/mcp/tools/llm_call_tool.py`** (259 строк)
   - MCP provider detection
   - UNIFIED с canonical (фаза 90.1.4.1)

7. **`/src/orchestration/orchestrator_with_elisya.py`** (2500+ строк)
   - Agent orchestration
   - Manual + auto provider routing
   - Tool support checking

8. **`/src/elisya/model_router_v2.py`** (100+ строк)
   - Task-based routing
   - Complexity-aware model selection
   - Legacy Provider enum (compatibility)

### Связанные файлы

- `/src/utils/unified_key_manager.py` - Ключи и ротация
- `/src/services/group_chat_manager.py` - Управление группами
- `/src/api/routes/` - FastAPI маршруты
- `/main.py` - Инициализация приложения
- `/data/config.json` - Хранилище ключей

### Конфигурационные файлы

- `/data/config.json` - API ключи (openrouter, gemini, xai, openai, anthropic)
- `/data/models_cache.json` - Кэш доступных моделей
- `/data/groups.json` - Сохраненные группы

---

## 9. MARKERS И ФАЗЫ

### PHASE MARKERS

```
MARKER_90.1.4.1_START: CANONICAL detect_provider (Unified)
  - Located in: provider_registry.py, chat_handler.py, llm_call_tool.py
  - Status: IMPLEMENTED ✅
  - Lines: 48-86 (chat_handler), 95-111 (llm_call_tool), 786-810 (provider_registry)

MARKER_90.1.4.2_START: XAI key exhaustion (Fallback to OpenRouter)
  - Located in: provider_registry.py, orchestrator_with_elisya.py
  - Status: IMPLEMENTED ✅
  - Lines: 677-706 (provider_registry - XaiProvider.call()),
           1121-1125 (orchestrator - preliminary check)
  - Phases: 80.35, 80.37, 80.38, 80.39, 80.40

MARKER_90.4.0_START: VETKA chat streaming for call_model
  - Located in: llm_call_tool.py
  - Status: IMPLEMENTED ✅
  - Streams results to "Молния" group chat (ID: 5e2198c2-8b1a-45df-807f-5c73c5496aa8)

MARKER_80.5: Ollama tool support checking
  - Located in: provider_registry.py (OllamaProvider)
  - Status: IMPLEMENTED ✅
  - Models without tools: deepseek-llm, llama2, codellama, mistral, phi, gemma, orca-mini, vicuna
  - Retry logic: if tools error, retry without tools
```

---

## 10. РЕКОМЕНДАЦИИ ПО УПРОЩЕНИЮ

### SHORT TERM (Немедленные действия)

1. **Обновить orchestrator.py** для использования canonical detect_provider
   ```python
   # Вместо inline логики (строки 1113-1144):
   provider = ProviderRegistry.detect_provider(model_id)
   ```

2. **Унифицировать XAI fallback logic**
   - Переместить всю логику в XaiProvider.call()
   - Удалить предварительную проверку из orchestrator

3. **Документировать format model_id**
   - Рекомендация: всегда использовать "provider/model"
   - Пример: "openai/gpt-4o", "ollama/qwen2:7b"

### MEDIUM TERM (1-2 недели)

1. **Refactor group chat endpoints**
   - Консолидировать CRUD операции
   - Явный endpoint для управления моделями
   - Отделить логику выбора агентов от маршрутизации

2. **Implement tool support registry**
   - Base function: can_model_use_tools(provider, model)
   - Фреш-check перед вызовом tools
   - Graceful degradation без tools

3. **Add centralized provider configuration**
   - Единое место для настройки каждого провайдера
   - API endpoints, timeout, retry policies, tool support

### LONG TERM (Архитектурные улучшения)

1. **Plugin architecture for providers**
   - Каждый провайдер - отдельный plugin
   - Hot-reload поддержка
   - Легче добавлять новых провайдеров

2. **Unified model catalog**
   - Единый реестр всех моделей со свойствами
   - Tool support metadata
   - Cost estimates
   - Version tracking

3. **Declarative routing rules**
   - YAML-based routing configuration
   - Multi-criteria selection (cost, latency, capabilities)
   - A/B testing support

---

## ВЫВОДЫ

### ✅ Что хорошо

1. **Canonical detect_provider** ✅ - фаза 90.1.4.1
2. **UNIFIED MCP routing** ✅ - llm_call_tool.py теперь использует canonical
3. **Provider registry pattern** ✅ - чистая архитектура
4. **Tool support checking** ✅ - Phase 80.5 обработка models without tools
5. **XAI fallback mechanism** ✅ - Phase 80.39-80.40

### ⚠️ Что требует внимания

1. **Orchestrator** - всё ещё использует inline логику (строки 1113-1144)
2. **XAI key detection** - разбросана в 2 местах
3. **Model ID format** - слишком много вариантов (с/без префикса, с/без тега)
4. **Слишком много эндпоинтов** - для управления группы нужна консолидация
5. **Tool support** - нет unified way для определения перед вызовом

### 📊 Числовые факты

- **Типов провайдеров:** 7 (OpenAI, Anthropic, Google, Ollama, OpenRouter, xAI, legacy)
- **Файлов с логикой маршрутизации:** 7+
- **Реализаций detect_provider:** 3 (1 canonical + 2 legacy wrappers)
- **Lines of routing code:** 3000+ (spread across files)
- **Фаз маршрутизации:** 4 (Solo, Group, MCP, Orchestrator)
- **API эндпоинтов:** 11+ (только для групп)

---

**Статус документа:** ЗАВЕРШЕНО
**Дата:** 2026-01-23
**Версия:** 1.0
**Следующая фаза:** 90.9.3 - План унификации маршрутизации
