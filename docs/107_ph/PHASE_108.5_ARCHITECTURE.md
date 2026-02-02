# Phase 108.5: Group Rename Architecture

## System Flow Diagram

```
┌──────────────────────────────────────────────────────────────────┐
│                         USER INTERACTION                          │
└──────────────────────────────────────────────────────────────────┘
                                 │
                                 │ Click edit icon
                                 ▼
┌──────────────────────────────────────────────────────────────────┐
│                    ChatPanel.tsx (Frontend)                       │
│                                                                   │
│  handleRenameChatFromHeader()                                    │
│  ├─ Check: activeGroupId?                                        │
│  │  ├─ YES: Group chat mode                                      │
│  │  │  ├─ Prompt: "Enter new name for this group"               │
│  │  │  ├─ Validate: not empty, changed                          │
│  │  │  └─ Call: PATCH /api/groups/{activeGroupId}               │
│  │  └─ NO: Regular chat mode                                     │
│  │     └─ Call: PATCH /api/chats/{chatId}                        │
│  └─ Update local state: setCurrentChatInfo()                     │
│                                                                   │
│  MARKER_GROUP_RENAME_UI                                          │
└──────────────────────────────────────────────────────────────────┘
                                 │
                                 │ HTTP PATCH
                                 ▼
┌──────────────────────────────────────────────────────────────────┐
│                   group_routes.py (FastAPI)                       │
│                                                                   │
│  @router.patch("/{group_id}")                                    │
│  async def update_group(group_id, body):                         │
│  ├─ Validate: body.name not empty                                │
│  ├─ Get manager: get_group_chat_manager()                        │
│  ├─ Call: manager.update_group_name(group_id, name)              │
│  ├─ Check: success?                                              │
│  │  ├─ YES: Return {success, group_id, name}                     │
│  │  └─ NO: Raise HTTPException 404                               │
│                                                                   │
│  MARKER_GROUP_RENAME_API                                         │
└──────────────────────────────────────────────────────────────────┘
                                 │
                                 │ Call handler
                                 ▼
┌──────────────────────────────────────────────────────────────────┐
│              group_chat_manager.py (Business Logic)               │
│                                                                   │
│  async def update_group_name(group_id, new_name):                │
│  ├─ Acquire lock: async with self._lock                          │
│  ├─ Get group: self._groups.get(group_id)                        │
│  ├─ Check: group exists?                                         │
│  │  ├─ YES: Continue                                             │
│  │  └─ NO: Return False                                          │
│  ├─ Store old name for logging                                   │
│  ├─ Update: group.name = new_name.strip()                        │
│  ├─ Update: group.last_activity = now()                          │
│  ├─ Persist: await self.save_to_json()                           │
│  ├─ Log: "Renamed group: old -> new"                             │
│  └─ Return: True                                                 │
│                                                                   │
│  MARKER_GROUP_RENAME_HANDLER                                     │
└──────────────────────────────────────────────────────────────────┘
                                 │
                                 │ Persist changes
                                 ▼
┌──────────────────────────────────────────────────────────────────┐
│                    data/groups.json (Storage)                     │
│                                                                   │
│  {                                                                │
│    "groups": {                                                    │
│      "abc-123-xyz": {                                             │
│        "id": "abc-123-xyz",                                       │
│        "name": "New Group Name",  ← Updated atomically           │
│        "description": "...",                                      │
│        "participants": {...},                                     │
│        "messages": [...],                                         │
│        "last_activity": "2026-02-02T12:34:56"  ← Updated         │
│      }                                                            │
│    }                                                              │
│  }                                                                │
│                                                                   │
└──────────────────────────────────────────────────────────────────┘
```

---

## Component Interaction

```
┌─────────────┐        ┌──────────────┐        ┌─────────────────┐
│             │        │              │        │                 │
│  ChatPanel  │───────▶│ FastAPI Route│───────▶│  GroupChat      │
│  (UI Layer) │        │  (API Layer) │        │  Manager        │
│             │        │              │        │  (Logic Layer)  │
└─────────────┘        └──────────────┘        └─────────────────┘
       │                      │                         │
       │                      │                         │
       ▼                      ▼                         ▼
  React State           HTTP Response              groups.json
  (displayName)         (success/error)           (persisted)
```

---

## State Management

### Frontend State
```typescript
// Chat info state (holds display name)
const [currentChatInfo, setCurrentChatInfo] = useState<{
  id: string;
  displayName: string | null;  // ← Group name stored here
  fileName: string;
  contextType: string;  // "group" for group chats
} | null>(null);

// Active group ID (determines if in group mode)
const [activeGroupId, setActiveGroupId] = useState<string | null>(null);
```

### Backend State
```python
# In-memory group object
@dataclass
class Group:
    id: str
    name: str  # ← Updated by update_group_name()
    description: str
    participants: Dict[str, GroupParticipant]
    messages: deque
    last_activity: datetime  # ← Also updated on rename
```

---

## Data Synchronization

### On Group Load (from history)
```
1. Fetch chat from /api/chats/{id}
2. Check: context_type === "group"?
3. YES: Extract group_id from chat data
4. Fetch group details: /api/groups/{group_id}
5. Extract group.name
6. Update currentChatInfo.displayName = group.name
7. Display in header
```

### On Rename
```
1. User clicks edit icon
2. Prompt for new name
3. POST new name to /api/groups/{id}
4. Update backend: groups.json
5. Update frontend: currentChatInfo.displayName
6. Header shows new name immediately
```

### On Reload
```
1. Load group chat from history
2. Fetch current name from /api/groups/{id}
3. Override display_name from chat_history with group.name
4. Ensures latest name is always shown
```

---

## Error Handling

### Frontend
```typescript
try {
  const response = await fetch(`/api/groups/${activeGroupId}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name: newName.trim() })
  });

  if (response.ok) {
    // Success: update local state
    setCurrentChatInfo(prev => prev ? { ...prev, displayName: newName.trim() } : null);
  } else {
    // Error: log to console
    console.error(`[ChatPanel] Error renaming group: ${response.status}`);
  }
} catch (error) {
  // Network error
  console.error('[ChatPanel] Error renaming group:', error);
}
```

### Backend
```python
# Validation
if not body.name or not body.name.strip():
    raise HTTPException(status_code=400, detail="name is required and cannot be empty")

# Not found
if not success:
    raise HTTPException(status_code=404, detail=f"Group {group_id} not found")
```

---

## Concurrency Safety

### Async Lock Protection
```python
async with self._lock:
    # Critical section - only one rename at a time
    group = self._groups.get(group_id)
    if not group:
        return False

    group.name = new_name.strip()
    group.last_activity = datetime.now()

    # Atomic save to disk
    await self.save_to_json()
```

### Benefits
- Prevents race conditions
- Ensures data consistency
- Maintains JSON integrity

---

## Testing Scenarios

### Happy Path
```
1. User clicks edit icon
2. Enters valid name
3. Backend updates successfully
4. Frontend shows new name
5. Reload confirms persistence
```

### Edge Cases
```
1. Empty name → Rejected by backend
2. Whitespace only → Stripped and rejected
3. Same name → No-op (frontend cancels)
4. Group doesn't exist → 404 error
5. Network failure → Caught by try/catch
```

---

## Performance Considerations

### Optimization
- Single API call (PATCH)
- Atomic JSON write (temp file → rename)
- Local state update (no page reload)
- Minimal re-renders (only header affected)

### Latency
- Network: ~10-50ms (local)
- Backend: ~5-10ms (in-memory update)
- Disk write: ~10-20ms (SSD)
- Total: ~25-80ms end-to-end

---

## Comparison: Chat vs Group Rename

| Aspect | Regular Chat | Group Chat |
|--------|--------------|------------|
| **Endpoint** | `/api/chats/{id}` | `/api/groups/{id}` |
| **Method** | PATCH | PATCH |
| **Body Key** | `display_name` | `name` |
| **Manager** | ChatHistoryManager | GroupChatManager |
| **Storage File** | `chat_history.json` | `groups.json` |
| **State Check** | `!activeGroupId` | `activeGroupId` |
| **Field Updated** | `chat.display_name` | `group.name` |
| **Timestamp** | `updated_at` | `last_activity` |

Both use the same UI component and handler function, just branch on `activeGroupId`.

---

## Future Enhancements

1. **Real-time sync:** Broadcast rename to all participants via WebSocket
2. **Audit trail:** Log rename history with timestamps and users
3. **Permissions:** Restrict rename to admin role
4. **Validation:** Check for duplicate names, profanity filter
5. **UI polish:** Inline edit, debounced auto-save
6. **Undo/redo:** Allow reverting recent rename

---

## Summary

Phase 108.5 implements group rename by:
1. Adding PATCH endpoint to group_routes.py
2. Adding update_group_name() to group_chat_manager.py
3. Enhancing handleRenameChatFromHeader() in ChatPanel.tsx

The implementation maintains consistency with existing chat rename, ensures data integrity with async locks, and provides immediate UI feedback with persistence to disk.
