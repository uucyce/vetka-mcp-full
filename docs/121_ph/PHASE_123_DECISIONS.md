# Phase 123: Спорные решения

**Date:** 2026-02-08
**Status:** ОБСУЖДЕНИЕ

---

## 1. Нумерация: Phase 122 → 123

**Проблема:** Phase 122 = Pipeline Feedback Loops (commit `f39be5e3`)

**Решение:** ✅ Переименовать в **Phase 123: Unified Activity & Chat-to-Tree Binding**

---

## 2. ActivityHub vs activity_emitter.py

**Текущее состояние:**
- `activity_emitter.py` — stateless эмиттер с helper функциями
- Нет state, нет decay, нет heat tracking

**Решение:** ✅ **РАСШИРЯТЬ**, не заменять

```python
# activity_hub.py — НОВЫЙ файл
from src.services.activity_emitter import emit_activity_update

class ActivityHub:
    _instance = None

    def __init__(self):
        self.heat_scores: Dict[str, float] = {}
        self.sio = None

    async def emit_glow(self, node_id: str, intensity: float, reason: str):
        """Emit glow + track heat score."""
        self.heat_scores[node_id] = max(self.heat_scores.get(node_id, 0), intensity)

        # Reuse existing emitter
        await emit_activity_update(
            socketio=self.sio,
            activity_type="glow",
            title=f"Activity: {node_id}",
            description=reason,
            metadata={
                "node_id": node_id,
                "intensity": intensity,
                "color": "#7ab3d4"
            }
        )
```

**Итог:** activity_emitter.py остаётся как есть, ActivityHub добавляет state layer.

---

## 3. Smart Anchor System

**Проблема:**
Если пользователь пишет без контекста файла — куда привязывать сообщение?
- Camera position = мусор
- Project root = все чаты на нуле (нарушает пространственную логику!)

**Решение:** ✅ **SEMANTIC-FIRST INTELLIGENT BINDING**

### Anchor Priority (if/else chain):

```python
async def determine_anchor(message: str, context: dict) -> tuple[str, str]:
    """
    Determine anchor_node_id for a chat message.
    Returns: (node_id, anchor_source)

    MARKER_123.3A: Smart anchor determination
    """

    # 1. Explicit file mention in message content
    mentioned_files = extract_file_paths(message)
    if mentioned_files:
        return mentioned_files[0], "file_mention"

    # 2. Pinned files in current context
    pinned = context.get('pinned_files', [])
    if pinned:
        return pinned[0]['path'], "pinned"

    # 3. Viewport focus (camera looking at specific folder)
    focus = context.get('viewport_focus')
    if focus and focus != PROJECT_ROOT:
        return focus, "viewport"

    # 4. SEMANTIC SEARCH — find nearest matching node by content
    # Use Qdrant to embed message and find closest file/folder
    embedding = await embed_text(message[:500])  # First 500 chars
    nearest = await qdrant_search_nearest_node(embedding, limit=1)
    if nearest and nearest.score > 0.5:  # Threshold for relevance
        return nearest.node_id, "semantic"

    # 5. Last resort: project root (but this should be rare!)
    return PROJECT_ROOT, "fallback"
```

### Dynamic Rebinding:

```python
async def on_message_added(chat_id: str, message: dict):
    """
    MARKER_123.3B: Dynamic anchor rebinding

    When files appear in later messages, rebind chat anchor.
    """
    chat = get_chat(chat_id)

    # Don't override manual user placement
    if chat.anchor_source == "manual":
        return

    # Check for file mentions in new message
    mentioned_files = extract_file_paths(message['content'])
    if mentioned_files:
        # Rebind to file position
        chat.anchor_node_id = mentioned_files[0]
        chat.anchor_source = "file_mention"
        await save_chat(chat)

        # Emit rebind event for frontend
        await emit_chat_rebind(chat_id, mentioned_files[0])
```

### User Manual Override:

```python
async def user_move_chat(chat_id: str, target_node_id: str):
    """
    MARKER_123.3C: User manually moves chat in 3D tree.

    Once moved manually, anchor is locked until user moves again.
    """
    chat = get_chat(chat_id)
    chat.anchor_node_id = target_node_id
    chat.anchor_source = "manual"  # Lock from auto-rebind
    await save_chat(chat)
```

### Chat Merging (Optional — Phase 123.5):

```python
async def check_merge_candidates(chat_id: str):
    """
    MARKER_123.3D: Find nearby chats on same topic for potential merge.

    Criteria:
    - Same semantic key (similar content embedding)
    - Created within 1 hour of each other
    - Same anchor_node_id OR within 2 hops in tree
    """
    chat = get_chat(chat_id)
    candidates = await find_similar_chats(
        embedding=chat.semantic_embedding,
        time_window_hours=1,
        max_tree_distance=2
    )
    return candidates  # UI shows merge suggestion
```

### Data Model Update:

```python
# MARKER_123.3E: Extended chat model
class Chat:
    id: str
    created_at: datetime
    updated_at: datetime

    # Anchor system
    anchor_node_id: str           # Current anchor position
    anchor_source: str            # "file_mention" | "pinned" | "viewport" | "semantic" | "manual" | "fallback"
    semantic_embedding: List[float]  # Cached embedding of first message

    # For merge detection
    semantic_key: str             # Short hash of embedding for fast comparison

    messages: List[ChatMessage]
```

### Why This Is Smart:

1. **Semantic fallback is NOT slow** — we embed once on chat creation, cache it
2. **Qdrant already has file embeddings** — vector search is O(log n)
3. **Chat appears near related content** — "discussing auth" → near auth files
4. **Dynamic rebind** — first msg vague, 5th msg mentions file → moves to file
5. **User override** — manual placement is respected, never auto-overwritten
6. **No garbage** — no virtual nodes, no camera positions, no clutter

---

## 4. Storage: JSON vs SQLite

**Текущее состояние:**
- `data/chat_history.json` — растёт бесконечно
- `_metadata.marker_chat_retention: "TODO - Add retention policy"`

**Варианты:**

| Storage | Плюсы | Минусы |
|---------|-------|--------|
| JSON (как сейчас) | Простой, работает | Медленный поиск, no indexes |
| SQLite | ACID, быстрый поиск, indexes | Миграция данных |
| Qdrant only | Уже используется | Не для structured data |
| JSON + SQLite | Backwards compat + power | Две системы |

**Решение:** ✅ **JSON (пока) + Готовить миграцию на SQLite**

**Почему:**
1. Не ломаем текущий функционал
2. Chat binding можно добавить в JSON
3. SQLite миграция = отдельная Phase 124

**Изменения в JSON:**
```json
{
  "chats": {
    "uuid": {
      "id": "uuid",
      "created_at": "...",
      "updated_at": "...",

      // НОВОЕ: primary anchor (для совместимости)
      "primary_anchor": "/path/to/file.ts",

      "messages": [
        {
          "id": "msg-uuid",
          "role": "user",
          "content": "...",
          "timestamp": "...",

          // НОВОЕ: per-message anchor
          "anchor_node_id": "/path/to/file.ts",
          "anchor_type": "file",  // file | folder | root
          "mentioned_files": ["/path/a.ts", "/path/b.ts"]
        }
      ]
    }
  }
}
```

---

## 5. progress_hooks Integration

**Текущее состояние:**
```python
# agent_pipeline.py:145
self.progress_hooks: List[Any] = []  # Initialized but EMPTY!
```

**Решение:** ✅ Использовать для glow events

```python
# В AgentPipeline.__init__
from src.services.activity_hub import get_activity_hub

self.progress_hooks = [
    self._emit_glow_on_progress
]

async def _emit_glow_on_progress(self, role: str, message: str, idx: int, total: int):
    """Emit glow when pipeline progresses."""
    hub = get_activity_hub()

    # Extract file paths from message
    files = extract_file_paths(message)
    for file_path in files:
        await hub.emit_glow(file_path, 0.7, f"pipeline:{role}")
```

---

## 6. Visualization: Message Nodes

**Проблема:** Как показывать сообщения в 3D дереве?

**Решение:** ✅ **НЕ создаём узлы, используем overlays**

```
Вместо:
  src/
    ├── App.tsx
    │   └── 💬 Message Node (реальный узел)

Делаем:
  src/
    ├── App.tsx ────────────── [💬 overlay badge]

```

**Почему overlays:**
1. Не загрязняют tree data
2. Можно включать/выключать видимость
3. Не влияют на label scoring
4. Легче анимировать (fade in/out)

**Реализация:**
```typescript
// MessageBadge.tsx — overlay component
<Html position={nodePosition} distanceFactor={10}>
  <div className="message-badge">
    💬 {messageCount}
  </div>
</Html>
```

---

## Summary: Что делаем

| Решение | Статус |
|---------|--------|
| Phase 122 → 123 | ✅ Переименовать |
| ActivityHub | ✅ Расширяет activity_emitter, добавляет heat state |
| **Anchor system** | ✅ **SEMANTIC-FIRST** — file → pinned → viewport → Qdrant search → root |
| Dynamic rebind | ✅ Файл появился позже → автоматически перепривязываем |
| Manual override | ✅ Пользователь перетащил → anchor_source="manual", не трогаем |
| Storage | ✅ JSON пока, SQLite = Phase 124 |
| progress_hooks | ✅ Подключаем к glow |
| Message viz | ✅ Overlays, не узлы |

## Markers Index (Phase 123)

| Marker | Description | Location |
|--------|-------------|----------|
| MARKER_123.0A | ActivityHub singleton | activity_hub.py |
| MARKER_123.0B | Heat score decay loop | activity_hub.py |
| MARKER_123.1A | Watchdog → Hub integration | file_watcher.py |
| MARKER_123.1B | MCP tools → Hub integration | edit_file_tool.py |
| MARKER_123.1C | Pipeline → Hub integration | agent_pipeline.py |
| MARKER_123.2A | Frontend glow state | useStore.ts |
| MARKER_123.2B | Emissive material | FileCard.tsx |
| MARKER_123.2C | Socket.IO glow handler | App.tsx |
| **MARKER_123.3A** | **Smart anchor determination** | chat_handlers.py |
| **MARKER_123.3B** | **Dynamic anchor rebinding** | chat_handlers.py |
| **MARKER_123.3C** | **User manual override** | chat_handlers.py |
| MARKER_123.3D | Chat merge candidates | chat_handlers.py (optional) |
| MARKER_123.3E | Extended chat model | chat_models.py |
| MARKER_123.4A | Message overlays component | MessageBadge.tsx |
| MARKER_123.5A | Artifact model | artifact_service.py |

---

## Обновлённый Roadmap

```
Phase 123.0: ActivityHub singleton              (0.5d)  ← START HERE
    - src/services/activity_hub.py (NEW)
    - Heat score tracking + decay

Phase 123.1: Activity Sources → Hub             (1d)
    - file_watcher.py → emit_glow
    - edit_file_tool.py → emit_glow
    - agent_pipeline.py → progress_hooks

Phase 123.2: Glow frontend                      (1d)
    - useStore.ts → glowingNodes state
    - FileCard.tsx → emissive material
    - Socket.IO handler

Phase 123.3: Smart Chat Anchor                  (1.5d)
    - determine_anchor() with semantic fallback
    - Dynamic rebinding on file mention
    - User manual override

Phase 123.4: Message overlays                   (0.5d)
    - MessageBadge.tsx component
    - drei Html overlay

Phase 123.5: Artifact + merge (optional)        (1d)
    - Artifact standardization
    - Chat merge candidates

Phase 123.6: Polish + tests                     (0.5d)

Total: 6 дней
```

---

**Согласен с решениями?** Или есть корректировки?
