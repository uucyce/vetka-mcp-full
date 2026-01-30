# H14: Chat Header Initialization Marker - Solo Chat

## Mission Objective
Mark the exact location where `currentChatInfo` must be initialized when user sends first message in a new solo chat. The chat header currently only displays when `currentChatInfo` is not null, but it's never set during solo chat creation.

---

## Problem Analysis

### Current Flow
1. User types message in chat panel (solo mode, not group)
2. `handleSend()` is called → line 663 in ChatPanel.tsx
3. `sendMessage()` is emitted via Socket.IO → useSocket.ts line 1231-1239
4. Backend receives `user_message` event
5. Backend calls `chat_history.get_or_create_chat(node_path)` → chat_history_manager.py line 212
6. Chat is created with ID and metadata
7. **MISSING**: Frontend never receives chat info back to set `currentChatInfo`

### Current State Variables
Located in `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/client/src/components/chat/ChatPanel.tsx` lines 87-95:

```typescript
const [currentChatId, setCurrentChatId] = useState<string | null>(null);

// Phase 74.3: Current chat info for header display
const [currentChatInfo, setCurrentChatInfo] = useState<{
  id: string;
  displayName: string | null;
  fileName: string;
  contextType: string;
} | null>(null);
```

### Where `currentChatInfo` IS Currently Set
Two existing locations show proper structure:

**Location 1: Group Chat Creation** (lines 626-631)
```typescript
setCurrentChatInfo({
  id: chatData.chat_id,
  displayName: name,
  fileName: 'unknown',
  contextType: 'group'
});
```

**Location 2: Loading Existing Chat** (lines 838-843)
```typescript
setCurrentChatInfo({
  id: chatId,
  displayName: data.display_name || null,
  fileName: data.file_name || fileName,
  contextType: data.context_type || 'file'
});
```

### Backend Chat Creation
File: `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/chat/chat_history_manager.py`

The `get_or_create_chat()` function (lines 69-205) creates chat objects with structure:
```python
{
  "id": chat_id,                    # UUID
  "file_path": normalized_path,
  "file_name": file_name,
  "display_name": clean_display_name,
  "context_type": context_type,     # "file" | "folder" | "group" | "topic"
  "items": items or [],
  "topic": topic,
  "pinned_file_ids": [],
  "created_at": now,
  "updated_at": now,
  "messages": []
}
```

---

## Solution: Mark the Initialization Point

### MARKER H14: Frontend Initialization Location

**File**: `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/client/src/components/chat/ChatPanel.tsx`

**Function**: `handleSend()`

**Current Location**: Line 663-733

**Exact Marker Point**: **AFTER Line 727** where `sendMessage()` is called

```typescript
// Line 727 (CURRENT)
sendMessage(input.trim(), contextPath, modelToUse);

// LINE 728-731: MARKER H14 - INSERT setCurrentChatInfo HERE
// PSEUDO-CODE FOR WHAT SHOULD HAPPEN:
// When message is first sent and chat doesn't exist yet:
setCurrentChatInfo({
  id: generatedOrReceivedChatId,           // Need to generate or receive from backend
  displayName: null,                        // Solo chat, no custom name initially
  fileName: selectedNode?.name || 'unknown', // Use selected node name or 'unknown'
  contextType: selectedNode ? 'file' : 'unknown'
});

// Lines 729-732 (CURRENT)
setInput('');
setSelectedModel(null);
setReplyTo(null);
setIsTyping(true);
```

---

## Data Requirements for `currentChatInfo` Initialization

### Required Fields
| Field | Source | Value | Notes |
|-------|--------|-------|-------|
| `id` | **TBD** | UUID string | Must be generated or received from backend response |
| `displayName` | Fixed | `null` | Solo chats start without custom names |
| `fileName` | From `selectedNode` | Node name or "unknown" | Extract from current selected tree node |
| `contextType` | Fixed | "file" or "unknown" | Based on whether a file/folder is selected |

### Option A: Generate ID Locally
```typescript
const chatId = crypto.randomUUID();
setCurrentChatInfo({
  id: chatId,
  displayName: null,
  fileName: selectedNode?.name || 'unknown',
  contextType: selectedNode?.type || 'unknown'
});
```

### Option B: Wait for Backend Response
Backend needs to emit chat creation event with:
```python
{
  "chat_id": str,
  "file_path": str,
  "file_name": str,
  "context_type": str,
  "display_name": Optional[str]
}
```

Then listen in useSocket.ts for new event (e.g., `solo_chat_created`) and dispatch to frontend.

---

## Implementation Checklist

### Phase 1: Determine Chat ID Strategy
- [ ] Decide: Generate locally (A) or wait for backend (B)?
- [ ] If A: No backend changes needed
- [ ] If B: Backend must emit `solo_chat_created` event with metadata

### Phase 2: Frontend Changes
- [ ] Add initialization call in `handleSend()` after line 727
- [ ] Extract `fileName` from `selectedNode` safely
- [ ] Set `contextType` based on node type or default to "file"

### Phase 3: Backend Changes (if Option B)
- [ ] Modify `user_message_handler_v2.py` to emit event after `get_or_create_chat()`
- [ ] Add new Socket.IO event listener in `useSocket.ts`
- [ ] Ensure event includes all required metadata

### Phase 4: Testing
- [ ] Send message without selecting file (contextType='unknown')
- [ ] Send message with file selected (contextType='file')
- [ ] Verify header appears after first message
- [ ] Verify header persists through message exchanges
- [ ] Verify reload shows chat info correctly

---

## Related Code Locations

### Frontend
- **ChatPanel.tsx handleSend()**: Line 663-733
- **ChatPanel.tsx currentChatInfo state**: Line 90-95
- **useSocket.ts sendMessage()**: Line 1193-1240
- **useSocket.ts event listeners**: Lines 974-1027 (chat_node_created example)

### Backend
- **user_message_handler_v2.py**: Line 212, 259 (get_or_create_chat calls)
- **chat_history_manager.py**: Lines 69-205 (get_or_create_chat implementation)
- **workflow_socket_handler.py**: Look for where user_message events are handled

### State Management
- **useStore.ts**: `selectedNode`, `chatMessages` available
- **ChatPanel.tsx**: `selectedNode` comes from useStore at line ~80

---

## Notes

1. **Header Visibility**: Chat header renders only when `currentChatInfo` is truthy (line 1871-1872)
2. **File vs. Folder**: Backend detects folder type automatically (chat_history_manager.py line 105-106)
3. **Display Name**: Solo chats start with `displayName: null`, only set when user renames
4. **Context Type**: Can be "file", "folder", "group", "topic", or "unknown"
5. **Persistence**: Chat info loads from backend when user clicks on existing chat (line 838-843)

---

## Success Criteria

Header will display when:
- ✓ User sends first message in solo chat
- ✓ `currentChatInfo` is initialized with correct data
- ✓ Header shows file name (from `fileName` or "unknown")
- ✓ Header persists through full chat session
- ✓ On reload, existing chat loads via GET /api/chats/{chatId}
