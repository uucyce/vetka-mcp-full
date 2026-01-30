# H2 Report: Pinned Files Persistence Analysis

## MARKER_H2_CURRENT_STRUCTURE

### Current JSON Schema (chat_history.json)

The `chat_history.json` file stores chat data with the following structure:

```json
{
  "chats": {
    "chat-id-uuid": {
      "id": "chat-id-uuid",
      "file_path": "/path/to/file",
      "file_name": "filename.ext",
      "display_name": "Custom Name (optional)",
      "context_type": "file|folder|group|topic",
      "items": ["file1", "file2"],  // For group chats
      "topic": "topic-name (optional)",  // For topic chats
      "created_at": "2026-01-06T20:33:38.370888",
      "updated_at": "2026-01-06T20:34:23.745607",
      "messages": [
        {
          "role": "user|assistant|system",
          "content": "message text",
          "agent": "agent-name (optional)",
          "model": "model-id (optional)",
          "node_id": "node-id (optional)",
          "metadata": {},
          "id": "message-uuid",
          "timestamp": "2026-01-06T20:33:38.372574"
        }
      ]
    }
  },
  "groups": { ... }
}
```

**KEY FINDING**: There is **NO `pinned_files` or `pinnedFileIds` field** in the chat structure.

---

## MARKER_H2_PINNED_STATE

### Where Pinned Files State Lives (Frontend Only)

**Location**: Zustand store in `/client/src/store/useStore.ts`

```typescript
interface TreeState {
  // Phase 61: Pinned files for multi-file context
  pinnedFileIds: string[];  // Line 102

  // Phase 61: Pinned files actions
  togglePinFile: (nodeId: string) => void;
  pinSubtree: (rootId: string) => void;
  clearPinnedFiles: () => void;
}
```

**Implementation** (lines 176-177, 267-297):
```typescript
// Initial state
pinnedFileIds: [],

// Toggle single file
togglePinFile: (nodeId) => set((state) => ({
  pinnedFileIds: state.pinnedFileIds.includes(nodeId)
    ? state.pinnedFileIds.filter(id => id !== nodeId)
    : [...state.pinnedFileIds, nodeId]
})),

// Pin entire subtree (folders)
pinSubtree: (rootId) => set((state) => {
  // Recursively finds all file descendants and pins them
}),

// Clear all pins
clearPinnedFiles: () => set({ pinnedFileIds: [] })
```

**Problem**: This is a **runtime-only, in-memory store** that:
- Only exists while the app is running
- Uses Zustand (client-side state management)
- Has NO persistence mechanism (no localStorage, no backend sync)
- Gets reset to empty `[]` on every page reload/restart

---

## MARKER_H2_SAVE_LOGIC

### How Chat History is Currently Saved

**Backend**: `/src/chat/chat_history_manager.py`

The `ChatHistoryManager` provides these methods:

```python
def add_message(self, chat_id: str, message: Dict[str, Any]) -> bool:
    """Add message to chat history and update timestamp."""
    self.history["chats"][chat_id]["messages"].append(message)
    self.history["chats"][chat_id]["updated_at"] = datetime.now().isoformat()
    self._save()  # Writes to chat_history.json
    return True

def rename_chat(self, chat_id: str, new_name: str) -> bool:
    """Save custom chat name (display_name)."""
    self.history["chats"][chat_id]["display_name"] = new_name
    self.history["chats"][chat_id]["updated_at"] = datetime.now().isoformat()
    self._save()

def update_chat_items(self, chat_id: str, items: List[str]) -> bool:
    """Update items list for group chats (file paths)."""
    chat["items"] = items
    chat["updated_at"] = datetime.now().isoformat()
    self._save()
```

**Frontend**: `/client/src/utils/chatApi.ts`

```typescript
export async function sendChatMessage(
  message: string,
  nodeId?: string,
  nodePath?: string,
  conversationId?: string
): Promise<ChatApiResponse> {
  const response = await fetch(`${API_BASE}/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      message,
      node_id: nodeId,
      node_path: nodePath,
      conversation_id: conversationId,
      // NOTE: pinnedFileIds is NOT sent here
    }),
  });
  return response.json();
}
```

**API Endpoint** (inferred from code): `/api/chats` (POST/PATCH)
- Creates new chat entries
- Updates chat metadata (display_name, items)
- Saves messages to chat history
- **Does NOT save pinned files**

---

## MARKER_H2_LOAD_LOGIC

### How Chat History is Loaded on Startup

**Frontend Load Flow** (from `ChatPanel.tsx`):

1. **On component mount**: No explicit pinned files load
   ```typescript
   // No useEffect to restore pinnedFileIds from storage
   ```

2. **When user selects a chat** (line 814-917):
   ```typescript
   const handleSelectChat = useCallback(async (chatId: string, ...) => {
     clearChat();  // Clears pinned files too! (line 819)

     // Load messages from API
     const response = await fetch(`/api/chats/${chatId}`);
     const messagesData = await response.json();

     // Restore messages but NOT pinned files
     for (const msg of messagesData.messages || []) {
       addChatMessage(msg);
     }
   }, [...]);
   ```

3. **When file is selected** (line 923-1002):
   ```typescript
   useEffect(() => {
     if (!selectedNode) {
       clearChat();  // Clears pinned files
       return;
     }

     // Load chat by file path but DON'T restore pinned files
     const chat = chats.find((c: any) => c.file_path === selectedNode.path);
     // Load messages only
   }, [selectedNode?.path, ...]);
   ```

**Critical Finding**: Line 819 in ChatPanel.tsx:
```typescript
// Phase 74.4: Clear pinned files when switching chats
clearPinnedFiles();
```

This **intentionally clears all pinned files** when loading a chat from history, even though the display_name and messages are restored.

**Backend Load**: Chat history is loaded via `ChatHistoryManager._load()`:
```python
def _load(self) -> Dict[str, Any]:
    """Load history from JSON file."""
    if self.history_file.exists():
        try:
            return json.loads(self.history_file.read_text(encoding='utf-8'))
```

This only loads what's in the JSON (messages, metadata) - no pinned files field exists.

---

## MARKER_H2_GAP

### What's Missing for Pinned Files Persistence

**Gap Analysis**:

| Aspect | Current State | Required for Persistence |
|--------|---|---|
| **Storage Location** | Zustand store (memory only) | JSON field in chat_history.json |
| **Save Method** | None (no API call) | POST/PATCH to `/api/chats/{id}` with pinnedFileIds |
| **Load Method** | None (initialized as `[]`) | Load from chat metadata when chat is selected |
| **API Support** | Missing | Need to extend ChatHistoryManager and API endpoints |
| **Backend Field** | Does not exist in schema | Must add `pinned_files: List[str]` to chat object |
| **Frontend Hook** | Missing | Need useEffect to save pin changes to backend |
| **On Chat Switch** | Clears pins intentionally | Should restore previous chat's pins OR clear if intended |

**Specific Gaps**:

1. **No Backend Field**: The `chat_history_manager.py` chat schema has no `pinned_files` field
2. **No Save API**: When user pins a file, no call is made to `/api/chats/{id}` to update pinnedFileIds
3. **No Load API**: When chat is loaded, the backend doesn't return previously pinned files
4. **No Frontend Persistence**: Zustand store doesn't sync with localStorage or backend
5. **Intentional Clear**: ChatPanel line 819 explicitly clears pins when switching chats

---

## MARKER_H2_PROPOSED_STRUCTURE

### Solution: Add Pinned Files Persistence

#### 1. Extend Backend Schema

**File**: `/src/chat/chat_history_manager.py`

```python
def _create_empty_history(self) -> Dict[str, Any]:
    """Create empty history structure."""
    return {
        "chats": {},
        "groups": { ... }
    }

# Update chat creation to include:
self.history["chats"][chat_id] = {
    "id": chat_id,
    "file_path": normalized_path,
    "file_name": file_name,
    "display_name": clean_display_name,
    "context_type": context_type,
    "items": items or [],
    "topic": topic,
    "pinned_file_ids": [],  # NEW FIELD - list of node IDs
    "created_at": now,
    "updated_at": now,
    "messages": []
}
```

#### 2. Add Backend Methods

```python
def update_pinned_files(self, chat_id: str, pinned_file_ids: List[str]) -> bool:
    """Update pinned files for a chat."""
    if chat_id in self.history["chats"]:
        chat = self.history["chats"][chat_id]

        # Only update if different
        if set(chat.get("pinned_file_ids", [])) != set(pinned_file_ids):
            chat["pinned_file_ids"] = pinned_file_ids
            chat["updated_at"] = datetime.now().isoformat()
            self._save()
            return True
    return False
```

#### 3. Updated JSON Schema Example

```json
{
  "chats": {
    "chat-uuid": {
      "id": "chat-uuid",
      "file_path": "/path/to/file",
      "file_name": "filename.ext",
      "display_name": null,
      "context_type": "file",
      "items": [],
      "topic": null,
      "pinned_file_ids": [
        "node-id-1",
        "node-id-2",
        "node-id-5"
      ],
      "created_at": "2026-01-06T20:33:38.370888",
      "updated_at": "2026-01-06T20:34:23.745607",
      "messages": [ ... ]
    }
  }
}
```

#### 4. Frontend Changes Required

**A. Save Pinned Files When They Change**

Add to `ChatPanel.tsx`:

```typescript
useEffect(() => {
  // Save pinned files to backend whenever they change
  if (currentChatId && pinnedFileIds.length > -1) {
    const saveTimeout = setTimeout(() => {
      fetch(`/api/chats/${currentChatId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          pinned_file_ids: pinnedFileIds
        })
      }).catch(err => console.error('[ChatPanel] Error saving pinned files:', err));
    }, 500);  // Debounce to avoid excessive API calls

    return () => clearTimeout(saveTimeout);
  }
}, [pinnedFileIds, currentChatId]);
```

**B. Restore Pinned Files When Loading Chat**

Modify `handleSelectChat`:

```typescript
const handleSelectChat = useCallback(async (chatId: string, ...) => {
  setCurrentChatId(chatId);

  const response = await fetch(`/api/chats/${chatId}`);
  if (response.ok) {
    const data = await response.json();

    // Load pinned files BEFORE clearing chat
    if (data.pinned_file_ids && data.pinned_file_ids.length > 0) {
      useStore.setState({ pinnedFileIds: data.pinned_file_ids });
    } else {
      clearPinnedFiles();
    }

    // Then load messages and other data
    clearChat();
    for (const msg of data.messages || []) {
      addChatMessage(msg);
    }
  }
}, [...]);
```

#### 5. API Endpoint Changes

**Extend** `/api/chats` endpoints:

```python
@app.patch('/api/chats/{chat_id}')
def update_chat(chat_id: str, request: dict):
    """Update chat metadata including pinned files."""
    manager = get_chat_history_manager()
    chat = manager.get_chat(chat_id)

    if not chat:
        return {"error": "Chat not found"}, 404

    # Update display_name if provided
    if "display_name" in request:
        manager.rename_chat(chat_id, request["display_name"])

    # NEW: Update pinned_file_ids if provided
    if "pinned_file_ids" in request:
        manager.update_pinned_files(chat_id, request["pinned_file_ids"])

    return {"chat_id": chat_id, "success": True}

@app.get('/api/chats/{chat_id}')
def get_chat_detail(chat_id: str):
    """Get full chat including pinned files."""
    manager = get_chat_history_manager()
    chat = manager.get_chat(chat_id)

    if not chat:
        return {"error": "Chat not found"}, 404

    return {
        "id": chat["id"],
        "file_path": chat["file_path"],
        "file_name": chat["file_name"],
        "display_name": chat.get("display_name"),
        "context_type": chat.get("context_type"),
        "pinned_file_ids": chat.get("pinned_file_ids", []),  # NEW
        "messages": chat.get("messages", []),
        "created_at": chat.get("created_at"),
        "updated_at": chat.get("updated_at")
    }
```

---

## Summary

**Current Problem**:
- Pinned files are stored only in memory (Zustand store)
- No backend field exists for pinned_file_ids
- No API endpoints to save/load pinned files
- When reloading, all pinned files are lost

**Root Cause**:
The pinned files feature (Phase 61) was implemented as UI state only, without adding persistence infrastructure.

**Solution Components**:
1. Add `pinned_file_ids: List[str]` to chat schema in JSON
2. Add `update_pinned_files()` method to ChatHistoryManager
3. Add debounced save on pin/unpin actions
4. Restore pinned files when loading chat from history
5. Extend PATCH `/api/chats/{id}` to handle pinned_file_ids

**Estimated Implementation Time**: 2-3 hours (backend + frontend + testing)

**Impact**: Medium - adds persistence to pinned files without breaking existing functionality
