# Chat Buttons Markers Audit - Phase 107

**Date:** 2026-02-02
**Status:** COMPLETED
**Markers Added:** 2 main markers + 1 secondary verification marker

## Summary

Проведён аудит кнопок чата для идентификации мест, нуждающихся в доработке:
1. Кнопка "New Chat" - должна заменить крестик
2. Кнопка "Edit Name" - проверена на функциональность

## Findings

### 1. КРЕСТИК КОТОРЫЙ УДАЛЯЕТ НАЗВАНИЕ (Line 1970-1989)

**Location:** `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/client/src/components/chat/ChatPanel.tsx`

**Lines:** 1970-1989

**Current Behavior:**
```typescript
{/* Close/clear chat info */}
<svg
  width="10"
  height="10"
  viewBox="0 0 24 24"
  fill="none"
  stroke="#555"
  strokeWidth="2"
  style={{ flexShrink: 0, cursor: 'pointer' }}
  onClick={(e) => {
    e.stopPropagation();
    setCurrentChatInfo(null);      // ПРОБЛЕМА: Только очищает currentChatInfo
    setCurrentChatId(null);        // Удаляет текущий чат из памяти
  }}
```

**Problem:**
- Крестик использует `setCurrentChatInfo(null)` и `setCurrentChatId(null)`
- Это просто стирает название и закрывает чат в интерфейсе
- БЕЗУМНАЯ ФУНКЦИЯ - просто удаляет, не создаёт новый чат

**Solution Required:**
- Заменить X кнопку на кнопку "New Chat"
- Вместо `setCurrentChatInfo(null)` нужна функция `handleNewChat()` которая:
  - Создаст новый пустой чат
  - Очистит историю сообщений
  - Установит новый ID чата
  - Сохранит в backend

**Marker Added:**
```typescript
// MARKER_CHAT_NEW_BUTTON: Replace X with New Chat button
// Fix: Replace setCurrentChatInfo(null) with handleNewChat() function
```

---

### 2. EDIT NAME КНОПКА - СТАТУС ПРОВЕРКИ

#### 2.1 Chat Header (ChatPanel.tsx)

**Location:** `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/client/src/components/chat/ChatPanel.tsx`

**Lines:** 1905-1936

**Current Status:** ✅ WORKING

```typescript
{(activeTab === 'chat' || activeTab === 'group') && currentChatInfo &&
 !(currentChatInfo.contextType === 'file' && pinnedFileIds.length > 0) && (
  <div onClick={handleRenameChatFromHeader}>
    {/* Chat name with Edit icon */}
    <span>{currentChatInfo.displayName || currentChatInfo.fileName}</span>
    <svg>{/* Edit pencil icon */}</svg>
    <svg>{/* X close icon */}</svg>
  </div>
)}
```

**Functionality:**
- ✅ Работает в Solo Chat (`activeTab === 'chat'`)
- ✅ Работает в Group Chat (`activeTab === 'group'`)
- ✅ Вызывает `handleRenameChatFromHeader()` который:
  - Показывает prompt для ввода нового имени
  - Отправляет PATCH запрос на `/api/chats/{id}`
  - Обновляет локальный state с новым `displayName`

**Marker Added:**
```typescript
// MARKER_CHAT_EDIT_NAME: Edit button working - active in solo chat (chat tab) and group chat (group tab)
```

---

#### 2.2 Chat Sidebar History (ChatSidebar.tsx)

**Location:** `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/client/src/components/chat/ChatSidebar.tsx`

**Lines:** 253-264

**Current Status:** ✅ WORKING

```typescript
{/* Phase 74.3: Actions with SVG icons */}
<div className="chat-sidebar-item-actions">
  <button
    className="chat-sidebar-item-edit"
    onClick={(e) => handleRenameChat(e, chat)}
    title="Rename chat"
  >
    <svg>{/* Edit pencil icon */}</svg>
  </button>
```

**Functionality:**
- ✅ Доступна для всех чатов в истории
- ✅ Вызывает `handleRenameChat()` который:
  - Показывает prompt с текущим именем чата
  - Отправляет PATCH запрос на `/api/chats/{id}`
  - Обновляет локальный state в sidebar

**Marker Added:**
```typescript
// MARKER_CHAT_EDIT_NAME: Edit button working in sidebar history
```

---

## Implementation Notes

### Phase 74.3 Context Awareness
- Edit Name кнопка использует `displayName` если доступно, иначе `file_name`
- Поддерживает все типы контекста: file, folder, group, topic
- Работает асинхронно через backend API

### Lines with handleRenameChatFromHeader
- **Line 825-850:** Функция определена
- **Line 1913:** Вызывается при клике на заголовок чата

### Lines with handleRenameChat (ChatSidebar)
- **Line 130-158:** Функция определена
- **Line 257:** Вызывается при клике Edit кнопки в sidebar

---

## Status Summary

| Item | Status | Marker | Action |
|------|--------|--------|--------|
| New Chat Button (Replace X) | ❌ NOT WORKING | ✅ ADDED | Implement `handleNewChat()` |
| Edit Name - Header | ✅ WORKING | ✅ ADDED | No action needed |
| Edit Name - Sidebar | ✅ WORKING | ✅ ADDED | No action needed |
| Edit Name - Group Chat | ✅ WORKING | ✅ ADDED | No action needed |

---

## Files Modified

1. `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/client/src/components/chat/ChatPanel.tsx`
   - Added marker for "New Chat" button (line 1970)
   - Added marker for Edit Name in header (line 1905)

2. `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/client/src/components/chat/ChatSidebar.tsx`
   - Added marker for Edit Name in sidebar (line 253)

---

## Next Steps (Phase 108)

1. **Implement handleNewChat() function in ChatPanel.tsx:**
   ```typescript
   const handleNewChat = useCallback(async () => {
     try {
       // Create new chat via API
       const response = await fetch('/api/chats', {
         method: 'POST',
         headers: { 'Content-Type': 'application/json' },
         body: JSON.stringify({ display_name: 'New Chat' })
       });

       if (response.ok) {
         const data = await response.json();
         setCurrentChatId(data.id);
         setCurrentChatInfo({
           id: data.id,
           fileName: 'New Chat',
           displayName: 'New Chat',
           contextType: 'file',
           messages: []
         });
         clearChat(); // Clear message history
       }
     } catch (error) {
       console.error('[ChatPanel] Error creating new chat:', error);
     }
   }, [setCurrentChatId, setCurrentChatInfo, clearChat]);
   ```

2. **Replace X icon onClick with handleNewChat:**
   - Change `setCurrentChatInfo(null)` to `handleNewChat()`
   - Update button label/title from "Clear" to "New Chat"

3. **Test all scenarios:**
   - Solo chat → New Chat button
   - Group chat → New Chat button
   - Sidebar → Edit Name in history
   - Header → Edit Name in chat title

---

## Marker Format Used

```typescript
// MARKER_XXX: [Problem/Status]
// Fix: [Solution/None if working]
```

All markers follow this format for consistency and easy discovery via grep.
