# VETKA ТОТАЛЬНЫЙ АУДИТ — Критические точки

**Дата аудита**: 2026-01-19  
**Ветка**: main (1 commit ahead)  
**Статус**: ПОЛНЫЙ АУДИТ — БЕЗ ИЗМЕНЕНИЙ

---

## 1. ЛИМИТ ФАЙЛОВ В КОНТЕКСТЕ

### ✅ Найденные места

```
src/api/handlers/message_utils.py:415
  def build_pinned_context(
      pinned_files: list,
      user_query: str = "",
      max_files: int = 5,            # 👈 HARDCODED ЗДЕСЬ
      max_tokens_per_file: int = MAX_TOKENS_PER_FILE,
      ...
```

```
src/api/handlers/message_utils.py:536
  def build_pinned_context_legacy(
      pinned_files: list,
      max_files: int = 10           # 👈 LEGACY версия — 10 файлов
```

```
src/elisya/middleware.py:42
  class MiddlewareConfig:
      qdrant_search_limit: int = 5  # ✅ Phase 15-3: Number of similar results to fetch
```

### 📊 Вывод

| Параметр | Значение | Тип | Использование |
|----------|----------|-----|---|
| **max_files** (build_pinned_context) | **5** | Hardcoded | Новая система контекста (Phase 67) |
| **max_files** (legacy) | **10** | Hardcoded | Fallback if Qdrant unavailable |
| **qdrant_search_limit** | **5** | Config class | Semantic search (Phase 15-3) |
| **MAX_CONTEXT_TOKENS** | **4000** | Env var | Токен бюджет (configurable) |
| **MAX_TOKENS_PER_FILE** | **1000** | Env var | Макс. токен на файл (configurable) |

**CONFIGURABLE**: Через environment variables
```python
VETKA_MAX_CONTEXT_TOKENS=4000      # По умолчанию 4000
VETKA_MAX_TOKENS_PER_FILE=1000     # По умолчанию 1000
VETKA_QDRANT_WEIGHT=0.7            # Вес Qdrant в ранжировании
VETKA_CAM_WEIGHT=0.3               # Вес CAM активации
```

---

## 2. SOCKET HANDLERS РЕГИСТРАЦИЯ

### 📝 Main Registration Point

```python
# src/api/handlers/__init__.py (Master registration)
def register_all_socket_handlers(sio: AsyncServer, app: FastAPI = None):
    """Register all socket.io handlers"""
    
    # 🔗 Все регистрируются здесь в одном месте
    register_approval_handlers(sio, app)           # Line 75
    register_tree_handlers(sio, app)               # Line 76
    register_connection_handlers(sio, app)         # Line 77
    register_reaction_handlers(sio, app)           # Line 79
    register_user_message_handler(sio, app)        # Line 80
    register_chat_handlers(sio, app)               # Line 81
    register_voice_socket_handlers(sio, app)       # Line 84 (Phase 60.5)
    register_search_handlers(sio, app)             # Line 85 (Phase 68)
    register_workflow_socket_handlers(sio, app)    # Line 86
    register_group_handlers(sio, app)              # Line 87
    register_key_handlers(sio, app)                # Line 88
```

### 🎯 Паттерн добавления нового handler

```python
# 1. Создать новый файл: src/api/handlers/my_handlers.py
def register_my_handlers(sio: AsyncServer, app=None):
    """Register my custom handlers"""
    
    @sio.on('my_event')
    async def handle_my_event(sid, data):
        # Обработка события
        pass

# 2. Добавить в __init__.py
from .my_handlers import register_my_handlers

# 3. Вызвать в register_all_socket_handlers()
register_my_handlers(sio, app)
```

### 📡 Существующие handlers (51 всего)

| Категория | Handlers | Файлы |
|-----------|----------|-------|
| **Voice** | 16 handlers | voice_socket_handler.py |
| **Workflow** | 5 handlers | workflow_socket_handler.py |
| **Chat** | 3 handlers | chat_handlers.py |
| **Approval** | 4 handlers | approval_handlers.py |
| **Reaction** | 2 handlers | reaction_handlers.py |
| **Tree** | 4 handlers | tree_handlers.py |
| **Search** | 1 handler | search_handlers.py |
| **Group** | 4 handlers | group_message_handler.py |
| **User Message** | 1 handler | user_message_handler.py |
| **Key** | 3 handlers | key_handlers.py |
| **Connection** | 2 handlers | connection_handlers.py |
| **Workflow Legacy** | 3 handlers | workflow_handlers.py |

**Полный список**: 
```
voice_connect, voice_disconnect, voice_start, voice_audio, voice_stop,
tts_request, voice_get_providers, voice_set_provider, voice_stream_start,
voice_pcm, voice_utterance_end, voice_stream_end, voice_interrupt,
voice_config, disconnect (voice),

workflow_connect, workflow_disconnect, join_workflow, leave_workflow,
get_workflow_status, ping_workflow,

chat_set_context, clear_context, mark_messages_read,

get_pending_approvals, cancel_approval, test_approval, approval_response,

quick_action, message_reaction,

select_branch, fork_branch, move_to_parent, refactor_knowledge,

search_query,

join_group, leave_group, group_message, group_typing,

user_message,

add_api_key, learn_key_type, get_key_status,

connect, disconnect,

cancel_workflow, start_workflow, get_status
```

---

## 3. SCANNER МОДУЛЬ

### 📂 Структура

```
src/scanners/
├── __init__.py
├── embedding_pipeline.py       # Phase 54: Embedding generation
├── file_watcher.py            # Phase 54: File system monitoring
├── local_scanner.py           # File scanning + discovery
├── local_project_scanner.py   # Project-specific scanning
└── qdrant_updater.py          # Incremental Qdrant updates
```

### 🧹 Очистка индекса: ДА, ЕСть!

```python
# src/scanners/qdrant_updater.py:342
def soft_delete(self, file_path: Path) -> bool:
    """Mark file as deleted (soft delete)"""
    # Marks as deleted, doesn't remove from Qdrant
    # Line: 342-377

# src/scanners/qdrant_updater.py:379
def hard_delete(self, file_path: Path) -> bool:
    """Permanently remove file from Qdrant"""
    # Actually deletes from collection
    # Line: 379-407

# src/scanners/qdrant_updater.py:409
def cleanup_deleted(self, older_than_hours: int = 24) -> int:
    """Remove soft-deleted files older than X hours"""
    # Batch cleanup of old deleted entries
    # Line: 409-459
```

### 🗂️ Qdrant Collections

```python
# src/memory/qdrant_client.py:61-65
COLLECTION_NAMES = {
    'tree': 'VetkaTree',        # Hierarchical tree structure
    'leaf': 'VetkaLeaf',        # Detailed file information
    'changelog': 'VetkaChangeLog'  # Audit trail (Triple Write)
}
```

### ⚙️ Как запускается rescan

```python
# src/scanners/local_scanner.py:65
def scan(self) -> Generator[ScannedFile, None, None]:
    """Generate scanned files from directory"""
    # Full directory scan with depth tracking

# src/scanners/qdrant_updater.py:220
def batch_update(self, files: List[Tuple[Path, str]]) -> Dict[str, int]:
    """Batch update multiple files"""
    # Only updates changed files (hash comparison)
```

### 📊 Лимиты

```python
# src/scanners/local_scanner.py:181
def scan_directory(path: str, max_files: int = 10000) -> List[Dict]:
    # Default: 10,000 файлов максимум
```

---

## 4. 3D TREE HIGHLIGHT МЕХАНИЗМ

### 🎯 Текущая реализация

```typescript
// client/src/store/useStore.ts:61-91
interface TreeState {
  highlightedId: string | null;      // Single highlighted node
  hoveredId: string | null;          // Hovered node
  selectedId: string | null;         // Selected node
  
  highlightNode: (id: string | null) => void;  // Set highlight
  hoverNode: (id: string | null) => void;
  selectNode: (id: string | null) => void;
}

// Implementation: Line 171
highlightNode: (id) => set({ highlightedId: id })
```

### 💫 Где используется highlight

```typescript
// client/src/components/canvas/CameraController.tsx:125-127
if (cameraCommand.highlight) {
  highlightNode(nodeId);
  setTimeout(() => highlightNode(null), 3000);  // Auto-clear after 3s
}

// client/src/App.tsx:407
setCameraCommand({ target: result.path, zoom: 'close', highlight: true });

// client/src/components/chat/ChatPanel.tsx:493-544
// Agent responses trigger highlight on relevant files
```

### 🎨 Visual representation

```typescript
// client/src/components/canvas/TreeEdges.tsx:28
const isAgentHighlighted = highlightedId === edge.source || highlightedId === edge.target;

// Colors:
color = '#9ca3af';   // Lighter gray for agent highlight
color = '#d1d5db';   // Even lighter for selection highlight

// client/src/components/chat/MessageInput.tsx:506-520
// Glow effects:
// "green glow" - Model speaking
// "blue glow" - Legacy listening
```

### ❌ Multiple highlight: НЕТ (не поддерживается)

**Текущие ограничения:**
- Только ONE ноде может быть highlighted одновременно
- `highlightedId: string | null` в Store (не массив)
- Auto-clear через 3 секунды

**Для multi-select используется:**
```typescript
// client/src/components/search/UnifiedSearchBar.tsx:241
selectedIds: Set<string>      // Multiple selection для search
```

### 🔌 Socket events для highlight

```python
# src/api/handlers/user_message_handler.py
# Backend отправляет client'у:
await sio.emit('file_highlighted', {'path': file_path})
await sio.emit('file_unhighlighted', {'path': file_path})

# client слушает в useSocket.ts:437-442
socket.on('file_highlighted', (data) => { ... })
socket.on('file_unhighlighted', (data) => { ... })
```

---

## 5. GIT STATUS

### 🌿 Branch

```
Current: main
Status: 1 commit ahead of origin/main
```

### 📝 Recent commits

```
e067690 Phase 68.3: UnifiedSearchBar UI improvements
ee7ddb2 Phase 67.2: Context assembly optimizations
3a53ca9 Phase 67: Integrate CAM + Qdrant into context assembly
92f8c44 Phase 66.3: CAM deep audit report
f85aae1 Phase 64: Add @status markers and @calledBy documentation
```

### ⚠️ Uncommitted changes

**MODIFIED (19 файлов):**
- client/src/components/* (5 файлов)
- client/src/hooks/* (2 файла)
- client/src/store/useStore.ts
- client/src/utils/* (2 файла)
- src/api/routes/semantic_routes.py
- src/scanners/qdrant_updater.py
- src/memory/qdrant_client.py
- src/mcp/__init__.py
- docs/skills/vetka-mcp/*
- data/* (3 JSON файла)

**DELETED (1 файл):**
- docs/PHASE_66_3_CAM_AUDIT.md

**UNTRACKED (множество):**
- docs/67_ph/ docs/66_ph/ docs/65_phases/
- src/search/ (new search module)
- src/mcp/vetka_mcp_bridge.py, vetka_mcp_server.py
- tests/test_mcp_*.py
- MCP_AUDIT_RESULTS.md и другие audit reports

---

## 🚨 КРИТИЧЕСКИЕ НАХОДКИ

### 1️⃣ SINGLE HIGHLIGHT BOTTLENECK
- **Проблема**: Только один файл может быть highlighted одновременно
- **Последствие**: Нельзя показать связанные файлы вместе (например, imports + usages)
- **Решение**: Изменить `highlightedId: string` → `highlightedIds: Set<string>`

### 2️⃣ HARDCODED LIMIT 5 для pinned files
- **Где**: `src/api/handlers/message_utils.py:415`
- **Значение**: `max_files: int = 5`
- **Проблема**: Не соответствует legacy (10 файлов), не configurable в коде
- **Решение**: Использовать env variable `VETKA_MAX_PINNED_FILES`

### 3️⃣ TOKEN BUDGETING NEEDS REVIEW
- **MAX_CONTEXT_TOKENS = 4000**: Может быть недостаточно для agent reasoning
- **MAX_TOKENS_PER_FILE = 1000**: Per-file limit может обрезать важный код
- **Текущий вес**: Qdrant (70%) + CAM (30%) — может нужна динамическая регулировка

### 4️⃣ SCANNER CLEANUP НЕ АВТОМАТИЗИРОВАН
- **soft_delete()** требует явного вызова
- **hard_delete()** требует явного вызова
- **cleanup_deleted()** требует явного вызова
- **Нет**: Scheduled cleanup job или background task

### 5️⃣ QDRANT COLLECTIONS НЕМНОГО UNDOCUMENTED
- **VetkaTree**: Для чего точно? (Hierarchical structure, но как используется?)
- **VetkaLeaf**: Relationship с tree?
- **VetkaChangeLog**: Triple Write audit, но когда читается/используется?

### 6️⃣ 51 SOCKET HANDLER — СЛОЖНОСТЬ РАСТЕТ
- **Риск**: Распределенная регистрация (каждый в своем файле)
- **Решение**: Может нужен handler registry с self-discovery

### 7️⃣ NO ERROR BOUNDARIES для файлов в pinned context
- **Риск**: Если файл недоступен, весь context собирается неправильно
- **Текущее**: Fallback к `[File not accessible]`, но нет retry logic
- **Решение**: Add exponential backoff + fallback to cached version

---

## ✅ РЕКОМЕНДАЦИИ

### Immediate Actions

1. **🔴 URGENT**: Добавить `VETKA_MAX_PINNED_FILES` env var (default=5, но configurable)
2. **🔴 URGENT**: Implement multi-highlight support для 3D дерева
3. **🟡 HIGH**: Автоматизировать cleanup_deleted() через background task

### Short-term (1-2 недели)

4. Документировать VetkaTree/VetkaLeaf/VetkaChangeLog relationship
5. Add metrics collection для qdrant_search_limit hits/misses
6. Implement handler registry system для socket handlers
7. Add error boundaries для load_pinned_file_content()

### Long-term (roadmap)

8. Dynamic token budgeting based on agent type
9. Predictive file pinning (ML model для auto-suggest)
10. Socket handler validation/type checking
11. Qdrant collection versioning/migration system

---

## 📊 SUMMARY TABLE

| Компонент | Конфигурируемо? | Лимиты | Статус |
|-----------|---------------|--------|--------|
| Pinned files | ⚠️ Env-only | max_files=5 | ✅ Work |
| Context tokens | ✅ Env | 4000 total | ✅ Work |
| Qdrant search | ✅ Config | limit=5 | ✅ Work |
| 3D highlight | ❌ No | 1 node only | ⚠️ Limited |
| Scanner cleanup | ❌ Manual | - | ⚠️ Not auto |
| Socket handlers | ✅ Modular | 51 total | ✅ Scalable |

---

**АУДИТ ЗАВЕРШЕН** — Без изменений в коде, только документация

