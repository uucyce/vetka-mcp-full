# BUG TRIAGE REPORT
**Date:** 2026-02-02
**Methodology:** Haiku Recon (4) → Sonnet Verify (3) → Opus Fix

---

## EXECUTIVE SUMMARY

| Bug | Priority | Haiku Finding | Sonnet Verdict | Fix Complexity |
|-----|----------|---------------|----------------|----------------|
| Scroll Button | HIGH | useCallback dep + SVG | useCallback: BUG, SVG: FALSE | LOW |
| Key Search | HIGH | Field mismatch | VERIFIED BUG | LOW |
| Chat Rename | MEDIUM | No verify after save | VERIFIED BUG | LOW |
| API Keys | INFO | Keys exhausted | CONFIRMED | N/A (wait) |

---

## BUG 1: SCROLL BUTTON

### Problem
Стрелка прокрутки чата работает только в одном направлении. Через время перестаёт работать вниз.

### Root Cause (VERIFIED)
**File:** `client/src/components/chat/ChatPanel.tsx:1125`

```typescript
const handleScroll = useCallback(() => {
  // ...
  setIsAtBottom(atBottom);
}, [isAtBottom]);  // ← BUG: циклическая зависимость
```

Проблема:
1. `handleScroll` зависит от `isAtBottom`
2. `handleScroll` меняет `isAtBottom` через `setIsAtBottom`
3. Это пересоздаёт `handleScroll` → useEffect переподписывает listener
4. Race conditions при быстром скролле

### SVG (FALSE POSITIVE)
Haiku ошибся - SVG координаты правильные:
- `points="18 15 12 9 6 15"` = стрелка вверх ^
- `points="6 9 12 15 18 9"` = стрелка вниз v

### Fix
```typescript
// Убрать isAtBottom из зависимостей
const handleScroll = useCallback(() => {
  const container = messagesContainerRef.current;
  if (!container) return;

  const { scrollTop, scrollHeight, clientHeight } = container;
  const atBottom = scrollHeight - scrollTop - clientHeight < 50;

  setIsAtBottom(prev => {
    if (atBottom !== prev) {
      console.log('[ChatPanel] Scroll state changed:', { atBottom });
    }
    return atBottom;
  });
}, []); // ← пустой массив
```

---

## BUG 2: KEY SEARCH / HYBRID SEARCH

### Problem
Keyword search не работает, и как следствие hybrid search тоже сломан.

### Root Cause (VERIFIED)
**File:** `src/memory/weaviate_helper.py`

Field name mismatch между writer и reader:

| Operation | Field Written | Field Read |
|-----------|---------------|------------|
| Writer (triple_write) | `file_path`, `file_name` | - |
| bm25_search | - | `file_path`, `file_name` ✅ |
| hybrid_search | - | `path` ❌ (не существует!) |
| vector_search | - | `path` ❌ (не существует!) |

`bm25_search` работает правильно и конвертирует поля.
`hybrid_search` и `vector_search` ищут поле `path` которого нет в схеме.

### Fix
```python
# weaviate_helper.py line 134-137 (hybrid_search)
# БЫЛО:
content
path
creator
node_type

# ДОЛЖНО БЫТЬ:
content
file_path
file_name
```

```python
# weaviate_helper.py line 178-179 (vector_search)
# БЫЛО:
content
path

# ДОЛЖНО БЫТЬ:
content
file_path
file_name
```

---

## BUG 3: CHAT RENAME

### Problem
Чат можно переименовать, но после reload имя сбрасывается на file_name.

### Root Cause (VERIFIED)
**File:** `client/src/components/chat/ChatPanel.tsx:882-893`

Backend persist работает корректно (VERIFIED).
Проблема на frontend:
1. Если PATCH fails, UI всё равно закрывается (line 893)
2. Нет error feedback для пользователя
3. При reload читается старое имя из backend

```typescript
// Проблемный код
try {
  const response = await fetch(...);
  if (response.ok) {
    // update state
  }
  // NO ELSE - ошибка игнорируется!
} catch (error) {
  console.error('Failed to rename:', error);
}
setIsRenaming(false); // ВСЕГДА закрывает, даже при ошибке
```

### Fix
```typescript
try {
  const response = await fetch(...);
  if (response.ok) {
    // existing success code
    setIsRenaming(false);  // Переместить сюда
  } else {
    const errorData = await response.json();
    console.error('Rename failed:', errorData);
    // Показать ошибку юзеру (toast/alert)
    // НЕ закрывать input - дать попробовать снова
    return;
  }
} catch (error) {
  console.error('Failed to rename:', error);
  // Показать ошибку
  return;
}
// Убрать setIsRenaming(false) отсюда
```

---

## BUG 4: API KEYS (INFO)

### Status
Все OpenRouter FREE ключи в 24h cooldown. Это не баг роутинга - просто квота исчерпана.

### Findings
- 12 FREE keys + 1 PAID key в config.json
- Cooldown: 24 часа после rate limit
- Fallback на Gemini/XAI/Ollama не автоматический

### Recommendation
1. Подождать 24h для cooldown reset
2. Или использовать PAID key вручную
3. Long-term: добавить автоматический fallback на другие providers

---

## AGENT IDs FOR CONTINUATION

| Phase | Agent | ID |
|-------|-------|-----|
| Haiku Scroll | a8b9cf0 | Scroll Button recon |
| Haiku Key | aab885c | Key Search recon |
| Haiku Rename | a29b986 | Chat Rename recon |
| Haiku Keys | aa27f50 | API Keys recon |
| Sonnet Scroll | a0b2da6 | Scroll verify |
| Sonnet Key | ae4321a | Key Search verify |
| Sonnet Rename | afc4f2a | Chat Rename verify |

---

## FIX PRIORITY

1. **BUG 2: Key Search** - HIGH, блокирует поиск
2. **BUG 1: Scroll Button** - HIGH, UX проблема
3. **BUG 3: Chat Rename** - MEDIUM, workaround существует

---

---

## WEAVIATE vs QDRANT SYNC STATUS

### Counts Comparison

| Collection | Qdrant | Weaviate | Status |
|------------|--------|----------|--------|
| VetkaLeaf | **0** | 2474 | ⚠️ MISMATCH |
| vetka_elisya | 1961 | - | ✅ |
| VetkaTree | 1958 | - | ✅ |
| vetka_files | 95 | - | ✅ |

### Analysis
- **Weaviate VetkaLeaf:** 2474 objects (используется для BM25 keyword search)
- **Qdrant VetkaLeaf:** 0 points (пустая!)

Это объясняет проблему:
1. Weaviate используется для keyword/BM25 search → **РАБОТАЕТ** (2474 objects)
2. Qdrant коллекция VetkaLeaf пуста → hybrid может fallback на Qdrant и получать 0 результатов

**Root cause:** Field name mismatch (fixed) + возможно Qdrant VetkaLeaf не синхронизирован с Weaviate.

---

## FIXES APPLIED

| Fix | File | Change |
|-----|------|--------|
| FIX_109.1 | ChatPanel.tsx:1112-1125 | Removed `[isAtBottom]` from useCallback deps |
| FIX_109.1b | ChatPanel.tsx:1131-1145 | Added canScroll state, hide button when no overflow |
| FIX_109.2 | weaviate_helper.py:134,178 | Changed `path` → `file_path`, `file_name` |
| FIX_109.3 | ChatPanel.tsx:882-893 | Added error handling, don't close input on failure |
| FIX_109.3b | ChatPanel.tsx:97,770,855 | Added isSaved tracking, prevent rename of unsaved chats |
| FIX_109.4 | Multiple files | Unified Chat ID system - solo chats like groups for MCP |

### FIX_109.4: Unified Chat ID System (Solo ↔ Group)

**Goal:** Allow MCP to interact with solo chats using the same ID system as groups.

**Files Changed:**
- `client/src/store/useStore.ts` - Added `currentChatId` state
- `client/src/hooks/useSocket.ts` - Pass `chat_id` in `user_message` event
- `client/src/components/chat/ChatPanel.tsx` - Sync chat ID to store
- `src/api/handlers/user_message_handler.py` - Accept `client_chat_id`
- `src/chat/chat_history_manager.py` - Use client-provided `chat_id`

**Flow:**
1. Frontend generates UUID with `crypto.randomUUID()` when starting new chat
2. Stores in `useStore.currentChatId`
3. `useSocket.sendMessage()` passes `chat_id` to backend
4. Backend `get_or_create_chat()` uses this ID instead of generating new one
5. MCP can now access solo chats via unified ID

---

*Report generated by Claude Opus 4.5 (Architect Mode)*
*VETKA Bug Triage Session 2026-02-02*
