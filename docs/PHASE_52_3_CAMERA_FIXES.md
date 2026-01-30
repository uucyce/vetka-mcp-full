# Phase 52.3: Camera Angle + Node Search + API Fix

## ПРОБЛЕМЫ И РЕШЕНИЯ

### 1. ❌ CameraController не находил node по короткому имени

**Проблема**:
```
[CameraController] Node not found: main.py
```

Hostess отправляет `"main.py"`, но nodes хранят полный путь `/Users/.../vetka_live_03/main.py`.

**Решение** — Улучшенный поиск с тремя стратегиями:

```tsx
// Phase 52.3: Helper to find node by path or name
const findNode = (target: string) => {
  // 1. Exact path match
  let entry = Object.entries(nodes).find(([_, n]) => n.path === target);
  if (entry) return entry;

  // 2. Filename match (main.py → /full/path/main.py)
  entry = Object.entries(nodes).find(([_, n]) =>
    n.path?.endsWith('/' + target) || n.name === target
  );
  if (entry) return entry;

  // 3. Partial path match (docs/file.md → /full/path/docs/file.md)
  entry = Object.entries(nodes).find(([_, n]) =>
    n.path?.includes(target)
  );

  return entry || null;
};
```

**Результат**:
- ✅ `"main.py"` → находит `/Users/.../main.py`
- ✅ `"docs/README.md"` → находит `/Users/.../docs/README.md`
- ✅ Full path всегда работает

---

### 2. ❌ Фронтенд запрашивал чат по file_path вместо chat_id

**Проблема**:
```
GET /api/chats//Users/.../PHASE_7_FINAL_REPORT.md 404
```

API endpoint `/api/chats/:chatId` ожидает UUID, а не file path.

**Решение** — Два этапа загрузки:

```tsx
// Phase 52.3: Fixed to find chat by file_path, then load by chat_id
useEffect(() => {
  if (!selectedNode) return;

  clearChat();

  const loadChatByFilePath = async () => {
    // 1. Get all chats
    const allChatsResponse = await fetch('/api/chats');
    const chats = allChatsData.chats || [];

    // 2. Find chat with matching file_path
    const chat = chats.find((c: any) => c.file_path === selectedNode.path);

    if (!chat) {
      console.log('No history found, starting fresh');
      return;
    }

    // 3. Load messages by chat_id (UUID)
    const messagesResponse = await fetch(`/api/chats/${chat.id}`);
    const messagesData = await messagesResponse.json();

    // 4. Add messages to store
    for (const msg of messagesData.messages) {
      addChatMessage(msg);
    }
  };

  loadChatByFilePath();
}, [selectedNode?.path]);
```

**Результат**:
- ✅ Правильный API flow: `/api/chats` → find by path → `/api/chats/{uuid}`
- ✅ Нет 404 ошибок
- ✅ История загружается корректно

---

### 3. ❌ Неудобный угол камеры (сбоку и далеко)

**Проблема**:
- Камера смотрела под углом из других веток
- Node был слишком далеко
- Сложно рассмотреть файл

**Решение** — Фронтальный вид + ближе:

```tsx
// БЫЛО: Камера сбоку
const offset = new THREE.Vector3(
  distance * 0.3,  // Right
  distance * 0.4,  // Above
  distance * 0.8   // Behind
);

// СТАЛО: Фронтальный вид
targetPosition = new THREE.Vector3(
  nodePos.x,              // Centered on X
  nodePos.y + distance * 0.25,  // Slightly above
  nodePos.z + distance    // In front on Z axis
);

// Zoom distances также уменьшены:
const zoomDistances = {
  close: 8,   // БЫЛО: 15
  medium: 15, // БЫЛО: 25
  far: 25     // БЫЛО: 40
};
```

**Результат**:
- ✅ Камера прямо перед node (фронтально)
- ✅ Node крупно на экране (ближе)
- ✅ Хорошо видно имя и детали файла

---

### 4. ✅ Увеличен timeout подсветки (3s вместо 2s)

```tsx
// Phase 52.3: Unhighlight after 3 seconds
setTimeout(() => highlightNode(null), 3000);
```

Больше времени, чтобы заметить подсветку при быстрой навигации.

---

## ТЕХНИЧЕСКИЕ ДЕТАЛИ

### Node Search Algorithm

**Priority Order**:
1. **Exact match** — `/full/path/to/file.py` matches exactly
2. **Filename match** — `file.py` matches any `*/file.py`
3. **Partial path** — `src/utils/file.py` matches `*/src/utils/file.py`

**Edge Cases**:
- Multiple files with same name → returns first match (exact path preferred)
- Path with spaces → handled correctly
- Symlinks → resolved by backend before reaching frontend

---

### Camera Position Calculation

**Before Phase 52.3**:
```
Distance = 15 (close)
Offset = (4.5, 6, 12)  // Right, Above, Behind
Camera at: (node.x + 4.5, node.y + 6, node.z + 12)
→ Side angle, far from node
```

**After Phase 52.3**:
```
Distance = 8 (close)
Position = (node.x, node.y + 2, node.z + 8)  // Centered, Above, In Front
→ Frontal view, close to node
```

**Visual Comparison**:
```
BEFORE:            AFTER:
    📷              ___
   /               📷
  /                |
NODE              NODE
```

---

### API Flow Fix

**Before Phase 52.3**:
```
1. File selected
2. GET /api/chats/{file_path} ❌ 404
3. Empty chat
```

**After Phase 52.3**:
```
1. File selected
2. GET /api/chats → [{id, file_path}, ...]
3. Find chat where chat.file_path === selectedNode.path
4. GET /api/chats/{chat.id} → {messages: [...]}
5. Load messages ✅
```

---

## LOGS

### Successful Node Search
```
[CameraController] Processing command: {target: "main.py", zoom: "close"}
[CameraController] Found by filename: main.py
[CameraController] Animating to: main.py Vector3(0, 2, 8)
[CameraController] Animation complete
```

### Chat History Load
```
[ChatPanel] File changed to: /Users/.../src/agents/dev_agent.py
[ChatPanel] Found chat for dev_agent.py, loading messages...
[ChatPanel] Loaded 5 messages for dev_agent.py
```

### Fallback (No History)
```
[ChatPanel] File changed to: /Users/.../new_file.py
[ChatPanel] No history found for new_file.py, starting fresh
```

---

## VALIDATION

### Test Cases

1. **Short filename search**
   ```
   ✅ "main.py" → finds /full/path/main.py
   ✅ "README.md" → finds /full/path/README.md
   ✅ Hostess camera_focus works
   ```

2. **Partial path search**
   ```
   ✅ "docs/README.md" → finds /full/path/docs/README.md
   ✅ "src/agents/dev_agent.py" → finds full path
   ```

3. **API chat loading**
   ```
   ✅ File with history → loads messages
   ✅ File without history → empty chat
   ✅ No 404 errors
   ```

4. **Camera angle**
   ```
   ✅ Frontal view (not side angle)
   ✅ Node is close (8 units for 'close')
   ✅ Node clearly visible
   ```

5. **Highlight timeout**
   ```
   ✅ Highlight appears on focus
   ✅ Highlight fades after 3 seconds
   ```

---

## FILES CHANGED

### Modified Files
- ✅ `client/src/components/canvas/CameraController.tsx`
  - Added `findNode()` helper with 3 search strategies
  - Improved camera position (frontal view)
  - Closer zoom distances (8, 15, 25)
  - Extended highlight timeout (3s)

- ✅ `client/src/components/chat/ChatPanel.tsx`
  - Fixed file selection useEffect
  - Two-step API flow (find by path, load by ID)
  - Better error handling

### New Documentation
- ✅ `docs/PHASE_52_3_CAMERA_FIXES.md`

---

## BEFORE/AFTER COMPARISON

### Problem 1: Node Search
```
BEFORE:
  User: "покажи main.py"
  → [CameraController] Node not found: main.py ❌

AFTER:
  User: "покажи main.py"
  → [CameraController] Found by filename: main.py ✅
  → Camera flies to file ✅
```

### Problem 2: API Call
```
BEFORE:
  Click file → GET /api/chats/{file_path} → 404 ❌

AFTER:
  Click file → GET /api/chats → find by path → GET /api/chats/{uuid} ✅
```

### Problem 3: Camera Angle
```
BEFORE:
  Camera at (x+4.5, y+6, z+12), looking from side
  → File is small, hard to see ❌

AFTER:
  Camera at (x, y+2, z+8), looking directly at file
  → File is large, easy to see ✅
```

---

## ДАЛЬНЕЙШИЕ УЛУЧШЕНИЯ (опционально)

1. **Cache Chats List**
   - Store `/api/chats` response in React state
   - Avoid repeated API calls on every file switch

2. **Fuzzy Node Search**
   - Handle typos: "maim.py" → "main.py"
   - Levenshtein distance for close matches

3. **Camera Orbit**
   - Smooth rotation around node
   - Multiple viewing angles

4. **Visual Node Preview**
   - Show file icon or preview while highlighting
   - Mini-popup with file info

---

## СТАТУС
✅ **IMPLEMENTED** — Phase 52.3 Complete
- Node search by name/partial path
- Correct API flow for chat history
- Frontal camera view + closer zoom
- Extended highlight timeout

## NEXT PHASE
Phase 53: Enhanced agent context with CAM + chat history integration
