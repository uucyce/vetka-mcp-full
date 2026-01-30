# 🔍 UnifiedSearchBar Integration Points - Complete Audit

**Дата аудита:** 2026-01-18
**Статус:** ТОЛЬКО ЧТЕНИЕ И ДОКУМЕНТИРОВАНИЕ
**Цель:** Найти и задокументировать все точки интеграции для новой UnifiedSearchBar

---

## FRONTEND AUDIT

### ChatPanel Structure
- **Путь:** `client/src/components/chat/ChatPanel.tsx` (1317 строк)
- **Input компонент:** `MessageInput` (строка 1282-1298)
- **Отправка сообщений:** `handleSend` callback (строка 381-449)
- **Socket emit:** Через hook `useSocket()` (строка 50)
  - `sendMessage(input.trim(), contextPath, modelToUse)` - основной метод отправки
  - `sendGroupMessage(activeGroupId, 'user', input.trim())` - для группы

**Структура ChatPanel:**
```
ChatPanel (контейнер)
├── Header (строка 786-1185)
│   ├── Tabs: Chat/Scanner/Group (строка 794-966)
│   ├── Context indicator (строка 970-1093)
│   ├── Model indicator (строка 1097-1130)
│   ├── Group indicator (строка 1134-1184)
│   └── WorkflowProgress (строка 1132)
├── Messages container (строка 1222-1238)
│   └── MessageList + MessageInput
├── Reply indicator (строка 1241-1278)
└── MessageInput (строка 1282-1298)
```

**Входные параметры ChatPanel (Props):**
- `isOpen: boolean` - видимость панели
- `onClose: () => void` - callback закрытия
- `leftPanel: 'none' | 'history' | 'models'` - состояние левой панели
- `setLeftPanel: (value: 'none' | 'history' | 'models') => void` - переключатель левой панели

**Текущее состояние input:**
- `input: string` - содержимое input (строка 52)
- `setInput: (value: string) => void` - обновление input

### MessageInput Hook
- **Путь:** `client/src/components/chat/MessageInput.tsx` (723 строк)
- **Input textarea:** `inputRef` (строка 146)
- **Props interface (строка 31-54):**
  - `value: string` - содержимое
  - `onChange: (value: string) => void` - обновление
  - `onSend: () => void` - отправка
  - `isLoading: boolean` - статус загрузки
  - `voiceModels: string[]` - список голосовых моделей
  - `selectedModel: string | null` - выбранная модель
  - `replyTo?: string` - ответ на сообщение

**Умная логика MessageInput:**
- Детектирует упоминание голосовой модели (@mention)
- Показывает микрофон если голосовая модель упомянута
- Автоматически переключается на текстовую отправку при наличии текста
- Поддерживает realtime voice с WebRTC

### useSocket Hook
- **Путь:** `client/src/hooks/useSocket.ts` (1135 строк)
- **Основной метод отправки:** `sendMessage(message, nodePath, modelId)` (строка 957)
- **Emits:**
  ```typescript
  'user_message' - основное событие (строка 985)
  {
    text: string,
    node_path: string,
    node_id: string,
    model?: string,
    pinned_files?: PinnedFile[]
  }
  ```

**Существующие socket events (ServerToClientEvents, строка 18-228):**
- **Tree events:** `tree_updated`, `node_added`, `node_removed`, `node_moved`, `layout_changed`
- **Chat events:** `workflow_status`, `workflow_result`, `agent_chunk`, `chat_response`
- **Stream events:** `stream_start`, `stream_token`, `stream_end`
- **Approval events:** `approval_required`, `approval_decided`, `approval_error`
- **Group events:** `group_created`, `group_joined`, `group_message`, `group_stream_*`
- **Semantic:** `hostess_memory_tree`, `artifact_tree_node`
- **API Keys:** `key_saved`, `key_learned`, `key_status`

### Types & Interfaces
- **Путь:** `client/src/types/chat.ts` (78 строк)
- **Основные типы:**
  ```typescript
  ChatMessage {
    id: string
    role: 'user' | 'assistant' | 'system'
    agent?: 'PM' | 'Dev' | 'QA' | 'Architect' | 'Hostess'
    content: string
    type: 'text' | 'code' | 'plan' | 'compound'
    timestamp: string
    metadata?: { model, tokens, etc }
  }

  WorkflowStatus {
    workflow_id: string
    step: 'pm' | 'architect' | 'dev' | 'qa' | 'merge' | 'ops'
    status: 'running' | 'done' | 'error'
  }
  ```

- **Упоминания (MENTION_ALIASES, строка 62-77):**
  - Агенты: @pm, @dev, @qa, @architect, @researcher, @hostess
  - Модели: @deepseek, @coder, @qwen, @llama, @claude, @gemini

### Frontend Styling
- **Стиль:** Inline styles + Tailwind (нет CSS modules)
- **Тема:** Dark Nolan style - grayscale, subtle, no bright colors
- **Цветовая схема:**
  - Background: `#0f0f0f`, `#1a1a1a`, `#222`
  - Text: `#fff`, `#aaa`, `#555`
  - Accent (voice): `#4a9eff` (blue), `#4aff9e` (green for model)
  - Inactive: `#666`, `#888`

**Примеры компонентов:**
- MessageInput button: динамичные цвета в зависимости от режима (строка 500-531)
- Wave animation для голоса (строка 70-119)
- Canvas-based visualization (строка 613-621)

---

## BACKEND AUDIT

### Handlers Architecture
- **Путь:** `src/api/handlers/`
- **Основные файлы:**

| Файл | Назначение | Status |
|------|-----------|--------|
| `chat_handler.py` | Provider detection, model routing | ACTIVE |
| `chat_handlers.py` | Socket.IO handlers для чата | ACTIVE |
| `user_message_handler.py` | Main message entry point | ACTIVE |
| `workflow_handlers.py` | Workflow state management | ACTIVE |
| `group_message_handler.py` | Group chat logic | ACTIVE |
| `voice_handler.py` | Voice processing | ACTIVE |
| `approval_handlers.py` | Artifact approval | ACTIVE |

#### chat_handler.py (410 строк)
**Provider detection:**
```python
def detect_provider(model_name: str) -> ModelProvider:
    # Ollama: qwen2:7b (с ':')
    # OpenRouter: anthropic/claude-3 (с '/')
    # Direct APIs: gemini:, xai:, deepseek:, groq:
```

**Model calling functions:**
- `call_ollama_model(model_name, prompt)` - для локальных моделей
- `call_openrouter_model(model_name, prompt, api_key)` - для API моделей
- `get_agent_short_name(model_name)` - извлечение короткого имени
- `emit_model_response()` - отправка ответа клиенту
- `emit_stream_wrapper()` - враппер для streaming

**Key exports:**
```python
'ModelProvider', 'detect_provider', 'build_model_prompt',
'call_ollama_model', 'call_openrouter_model',
'get_agent_short_name', 'emit_model_response'
```

#### chat_handlers.py (134+ строк)
**Registered handlers:**
- `handle_set_context(sid, data)` - переключение контекста
- `handle_clear_context(sid, data)` - очистка контекста
- `handle_mark_messages_read(sid, data)` - отметить как прочитано

### Search Module
- **Путь:** `src/search/`
- **Файлы:**

| Файл | Назначение | Status |
|------|-----------|--------|
| `hybrid_search.py` | Semantic + BM25 + RRF fusion | ACTIVE (Phase 68) |
| `rrf_fusion.py` | RRF algorithm implementation | ACTIVE |

#### hybrid_search.py (Phase 68)
```python
class HybridSearchService:
    # Поддерживает 3 способа поиска:
    # 1. Semantic via Qdrant (vector similarity)
    # 2. Keyword via Weaviate (BM25)
    # 3. RRF fusion to combine results
```

**Configuration:**
- `SEMANTIC_WEIGHT = 0.5` (env var)
- `KEYWORD_WEIGHT = 0.3`
- `GRAPH_WEIGHT = 0.2`
- `RRF_K = 60` - parameter для RRF
- `HYBRID_CACHE_TTL = 300s`

**Используется в:**
- `src/api/routes/semantic_routes.py` - GET /api/search/hybrid endpoint

### Scanners Module
- **Путь:** `src/scanners/`
- **Файлы:**

| Файл | Назначение | Status |
|------|-----------|--------|
| `local_scanner.py` | Directory scanning | ACTIVE |
| `local_project_scanner.py` | Project-aware scanning | ACTIVE |
| `file_watcher.py` | File change detection | ACTIVE |
| `embedding_pipeline.py` | Embedding generation | ACTIVE |
| `qdrant_updater.py` | Qdrant vector updates | ACTIVE |

**Events emitted:**
- `directory_scanned` - event после сканирования
- `browser_folder_added` - папка добавлена из браузера

### Routes Architecture
- **Путь:** `src/api/routes/`
- **Основные routes:**

| Файл | Endpoints | Status |
|------|-----------|--------|
| `chat_routes.py` | POST /api/chat (THE BIG ONE) | ACTIVE |
| `semantic_routes.py` | GET /api/search/hybrid | ACTIVE (Phase 68) |
| `chat_history_routes.py` | /api/chats/* | ACTIVE |
| `group_routes.py` | /api/groups/* | ACTIVE |
| `model_routes.py` | /api/models | ACTIVE |
| `tree_routes.py` | /api/tree/* | ACTIVE |

#### chat_routes.py
**Основной endpoint:**
```python
POST /api/chat
Pydantic model:
  - message: str
  - conversation_id?: str
  - model_override?: str
  - system_prompt?: str
  - temperature?: float = 0.7
  - max_tokens?: int = 1000
  - node_id?: str
  - node_path?: str
```

**Helper functions:**
- `_get_chat_components(request)` - dependency injection
- `_get_chat_history_file(chat_dir, node_path)` - файл истории
- `_load_chat_history(chat_dir, node_path)` - загрузка истории
- `_save_chat_message(chat_dir, node_path, message)` - сохранение

#### semantic_routes.py
**Endpoints:**
```
GET /api/semantic-tags/search?tag=...
GET /api/semantic-tags/available
GET /api/file/{file_id}/auto-tags
GET /api/search/semantic?query=...
POST /api/search/weaviate
GET /api/search/hybrid?query=...&limit=15
```

**Phase 68: Hybrid search endpoint:**
- Использует `HybridSearchService`
- Поддерживает RRF fusion
- Fallback cascade (Weaviate → Qdrant → empty)

---

## SOCKET.IO EVENTS - ПОЛНЫЙ СПИСОК

### Emitted by Client (ClientToServerEvents)

**Message events:**
- `request_tree` - запрос дерева файлов
- `user_message` - основное сообщение пользователя (ГЛАВНОЕ)
  ```json
  {
    "text": "...",
    "node_path": "...",
    "node_id": "...",
    "model": "...",
    "pinned_files": [...]
  }
  ```
- `select_node` - выбор узла
- `move_node` - перемещение узла в 3D

**Approval events:**
- `approve_artifact` - одобрить артефакт
- `reject_artifact` - отклонить артефакт

**Group events:**
- `join_group` - присоединиться к группе
- `leave_group` - покинуть группу
- `group_message` - сообщение в группе
- `group_typing` - печать в группе

**API Key events:**
- `add_api_key` - добавить API ключ
- `learn_key_type` - определить тип ключа
- `get_key_status` - получить статус ключей

### Emitted by Server (ServerToClientEvents)

**Tree & Node events:**
- `tree_updated` - дерево обновлено
- `node_added`, `node_removed`, `node_moved`
- `layout_changed` - позиции узлов изменены

**Chat events:**
- `workflow_status` - статус workflow
- `workflow_result` - результат workflow
- `chat_response` - ответ чата
- `agent_chunk` - chunk из агента

**Streaming events:**
- `stream_start` - начало стрима
- `stream_token` - очередной токен
- `stream_end` - конец стрима

**Group events:**
- `group_created`, `group_joined`, `group_left`
- `group_message` - сообщение в группе
- `group_typing` - печать в группе
- `group_stream_start`, `group_stream_token`, `group_stream_end`

**Other events:**
- `approval_required` - требуется одобрение
- `key_saved`, `key_learned` - события API ключей
- `artifact_tree_node` - узел артефакта

---

## INTEGRATION RECOMMENDATIONS

### 1. Где добавить UnifiedSearchBar

**Рекомендация:** Добавить в ChatPanel header, рядом с input field.

**Текущая структура:**
```
ChatPanel header
├── Left buttons (Chat/History/Models)
├── [ЗДЕСЬ] Context indicator + pinned files
├── Selected model indicator
├── Group indicator
├── Right buttons (Scanner/Close)
└── Input + Send button
```

**Опция 1: В header (рекомендуется для юзабилити)**
- Поместить между "Context indicator" и "MessageInput"
- Расположение: строка 1186-1282 (между header и messages)
- Ширина: 100% (full width в панели)
- Высота: ~40-50px

**Опция 2: В MessageInput (для компактности)**
- Добавить как toolbar над textarea
- Меньше места, но тесно с другим функционалом голоса

**Выбираю Опцию 1** - UnifiedSearchBar в отдельной section после header, перед messages.

### 2. API Endpoint для Search

**Рекомендация:** Использовать существующий hybrid search endpoint.

**Текущий endpoint:**
```
GET /api/search/hybrid?query=...&limit=15
```

**Уже реализовано в:**
- `src/api/routes/semantic_routes.py` (Phase 68)
- `src/search/hybrid_search.py`

**Требуется:**
- Может потребоваться добавить фильтр по типу (code, docs, etc)
- Может потребоваться реальное время (streaming results)

### 3. Типы для интеграции

**Добавить в `client/src/types/chat.ts`:**
```typescript
export interface SearchResult {
  id: string;
  name: string;
  path: string;
  preview?: string;
  type: 'file' | 'code' | 'doc';
  relevance: number; // 0-1
}

export interface SearchQuery {
  text: string;
  limit?: number;
  filters?: {
    type?: 'code' | 'docs' | 'all';
    recent?: boolean;
  };
}
```

### 4. Socket.IO Event для Live Search

**Рекомендация:** Создать новые события для interactive search.

**Предлагаемые события:**
```typescript
// Client to Server
'search_query' - отправить поисковый запрос (live)
{
  text: string,
  limit: number,
  filters: object
}

// Server to Client
'search_results' - результаты поиска (может быть стриминг)
{
  results: SearchResult[],
  total: number,
  took_ms: number
}

'search_error' - ошибка поиска
{
  error: string,
  query: string
}
```

### 5. Интеграция с существующим Flow

**Поток пользователя:**
1. Открыть ChatPanel (уже работает)
2. Напечатать в UnifiedSearchBar ищет в реальном времени
3. Кликнуть на результат → выбрать файл (updateNodePosition)
4. Файл подсвечивается в 3D (highlightNode)
5. Контекст автоматически обновляется в ChatPanel
6. User может отправить сообщение с выбранным контекстом

**Код для интеграции (приблизительно):**
```typescript
// В ChatPanel.tsx добавить:
const [searchQuery, setSearchQuery] = useState('');
const [searchResults, setSearchResults] = useState<SearchResult[]>([]);

// Listener для search results
useEffect(() => {
  const handleSearchResults = (data: any) => {
    setSearchResults(data.results);
  };
  window.addEventListener('search-results', handleSearchResults);
  return () => window.removeEventListener('search-results', handleSearchResults);
}, []);

// Отправить search query
const handleSearch = (query: string) => {
  setSearchQuery(query);
  socketRef.current?.emit('search_query', {
    text: query,
    limit: 10,
    filters: {}
  });
};

// Обработать выбор результата
const handleSelectResult = (result: SearchResult) => {
  selectNode(result.id); // Select в 3D
  // Chat панель автоматически обновится через useEffect
};
```

### 6. Бэкенд изменения (минимальные)

**Файлы для модификации:**
1. `src/api/handlers/chat_handlers.py`
   - Добавить handler для `search_query` события

2. `src/api/routes/semantic_routes.py`
   - Может потребоваться оптимизация для real-time

3. Новый файл: `src/api/handlers/search_handlers.py` (опционально)
   - Wrapper для `HybridSearchService`

**Примерный handler:**
```python
@sio.on('search_query')
async def handle_search_query(sid, data):
    query = data.get('text', '')
    limit = data.get('limit', 10)

    # Использовать HybridSearchService
    results = await hybrid_search_service.search(
        query=query,
        limit=limit
    )

    # Отправить результаты
    await sio.emit('search_results', {
        'results': results,
        'total': len(results),
        'query': query
    }, to=sid)
```

---

## SUMMARY TABLE

| Компонент | Путь | Статус | Для Search |
|-----------|------|--------|-----------|
| **ChatPanel** | `client/src/components/chat/ChatPanel.tsx` | ACTIVE | Добавить SearchBar section |
| **MessageInput** | `client/src/components/chat/MessageInput.tsx` | ACTIVE | Может быть место для интеграции |
| **useSocket** | `client/src/hooks/useSocket.ts` | ACTIVE | Добавить search_query/search_results |
| **Types** | `client/src/types/chat.ts` | ACTIVE | Добавить SearchResult, SearchQuery |
| **Chat Handler** | `src/api/handlers/chat_handler.py` | ACTIVE | Model routing готов |
| **Chat Routes** | `src/api/routes/chat_routes.py` | ACTIVE | POST /api/chat готов |
| **Hybrid Search** | `src/api/routes/semantic_routes.py` | ACTIVE | GET /api/search/hybrid готов |
| **HybridService** | `src/search/hybrid_search.py` | ACTIVE | Готовый search engine |

---

## ФАЙЛЫ ДЛЯ СОЗДАНИЯ

1. **`src/api/handlers/search_handlers.py`** (новый)
   - Handler для socket events `search_query`
   - Wrapper для `HybridSearchService`

2. **`client/src/components/search/UnifiedSearchBar.tsx`** (новый)
   - React компонент SearchBar
   - Input field + результаты
   - Socket.IO integration

3. **`client/src/hooks/useSearch.ts`** (новый)
   - Custom hook для search logic
   - Кеширование результатов
   - Debounce для query

---

## CRITICAL INTEGRATION POINTS

1. ✅ **Socket.IO connection** - уже работает через useSocket()
2. ✅ **Message sending** - sendMessage() готов с model override
3. ✅ **Context switching** - selectNode() обновляет контекст
4. ⚙️ **Search backend** - HybridSearchService готов, нужен handler
5. ⚙️ **Real-time search** - нужны socket.io events
6. ⚙️ **UI component** - нужен UnifiedSearchBar компонент
7. ⚙️ **Type definitions** - нужны SearchResult типы

---

**Аудит завершен:** 2026-01-18
**Следующий шаг:** Реализация интеграции согласно рекомендациям
