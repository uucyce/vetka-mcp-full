# Phase 108.5: Group Chat Rename Implementation

**Status:** COMPLETED
**Date:** 2026-02-02
**Issue:** Group chats cannot be renamed after creation

## Problem
Групповые чаты создаются с именем, но нет возможности переименовать их после создания. Обычные чаты имеют функцию переименования через PATCH /api/chats/{id}, но для групп такого endpoint не было.

## Solution Summary
Реализована полная функциональность переименования групповых чатов по аналогии с обычными чатами:
1. Backend API endpoint для обновления имени группы
2. Backend handler для сохранения изменений в groups.json
3. Frontend UI интеграция с существующей кнопкой переименования

---

## Implementation Details

### 1. Backend - API Endpoint
**File:** `/src/api/routes/group_routes.py`
**Marker:** `MARKER_GROUP_RENAME_API`

Added PATCH endpoint after the GET endpoint:

```python
class UpdateGroupRequest(BaseModel):
    name: str


@router.patch("/{group_id}")
async def update_group(group_id: str, body: UpdateGroupRequest):
    """
    Update group name.
    Phase 108.5: Enable group chat renaming.
    """
    if not body.name or not body.name.strip():
        raise HTTPException(status_code=400, detail="name is required and cannot be empty")

    manager = get_group_chat_manager()
    success = await manager.update_group_name(group_id, body.name.strip())

    if not success:
        raise HTTPException(status_code=404, detail=f"Group {group_id} not found")

    return {
        "success": True,
        "group_id": group_id,
        "name": body.name.strip()
    }
```

**Usage:**
```bash
PATCH /api/groups/{group_id}
Content-Type: application/json

{
  "name": "New Group Name"
}
```

**Response:**
```json
{
  "success": true,
  "group_id": "abc-123...",
  "name": "New Group Name"
}
```

---

### 2. Backend - Handler Method
**File:** `/src/services/group_chat_manager.py`
**Marker:** `MARKER_GROUP_RENAME_HANDLER`

Added method after `get_all_groups()`:

```python
async def update_group_name(self, group_id: str, new_name: str) -> bool:
    """
    Update group name.
    Phase 108.5: Enable group chat renaming.

    Args:
        group_id: Group UUID
        new_name: New name for the group

    Returns:
        True if updated successfully, False if group not found
    """
    async with self._lock:
        group = self._groups.get(group_id)
        if not group:
            logger.warning(f"[GroupChat] Cannot rename - group {group_id} not found")
            return False

        old_name = group.name
        group.name = new_name.strip()
        group.last_activity = datetime.now()

        # Save changes to disk
        await self.save_to_json()

        logger.info(f"[GroupChat] Renamed group {group_id}: '{old_name}' -> '{new_name}'")
        return True
```

**Features:**
- Thread-safe with async lock
- Updates `last_activity` timestamp
- Persists to `data/groups.json` atomically
- Logs rename action for audit trail

---

### 3. Frontend - UI Integration
**File:** `/client/src/components/chat/ChatPanel.tsx`
**Marker:** `MARKER_GROUP_RENAME_UI`

Modified existing `handleRenameChatFromHeader` function to support both chat types:

```typescript
const handleRenameChatFromHeader = useCallback(async () => {
  // Phase 108.5: Handle both regular chats and group chats
  if (activeGroupId) {
    // Group chat mode - rename via /api/groups/{id}
    const currentName = currentChatInfo?.displayName || currentChatInfo?.fileName || 'Group Chat';
    const newName = prompt('Enter new name for this group:', currentName);

    if (!newName || newName.trim() === '' || newName.trim() === currentName) {
      return;
    }

    try {
      const response = await fetch(`/api/groups/${activeGroupId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: newName.trim() })
      });

      if (response.ok) {
        setCurrentChatInfo(prev => prev ? { ...prev, displayName: newName.trim() } : null);
        console.log(`[ChatPanel] Phase 108.5: Renamed group to "${newName.trim()}"`);
      } else {
        console.error(`[ChatPanel] Error renaming group: ${response.status}`);
      }
    } catch (error) {
      console.error('[ChatPanel] Error renaming group:', error);
    }
  } else {
    // Regular chat mode (existing code)
    // ...
  }
}, [currentChatInfo, activeGroupId]);
```

**Enhanced group loading** to fetch current name from groups.json:

```typescript
// Phase 108.5: Fetch group details to get current name
try {
  const groupDetailsResponse = await fetch(`/api/groups/${groupId}`);
  if (groupDetailsResponse.ok) {
    const groupDetailsData = await groupDetailsResponse.json();
    const groupName = groupDetailsData.group?.name || data.display_name || 'Group Chat';
    // Update currentChatInfo with actual group name
    setCurrentChatInfo(prev => prev ? { ...prev, displayName: groupName } : prev);
    console.log(`[ChatPanel] Phase 108.5: Loaded group name: "${groupName}"`);
  }
} catch (groupDetailsError) {
  console.error('[ChatPanel] Phase 108.5: Error loading group details:', groupDetailsError);
}
```

**UI Location:**
- Same edit pencil icon in chat header as regular chats
- Located in: Chat header bar > Click on chat name
- Works identically for both chat types

---

## Architecture

### Data Flow

```
User clicks edit icon
    ↓
handleRenameChatFromHeader()
    ↓
Checks: activeGroupId? → Group : Chat
    ↓
PATCH /api/groups/{id} with {name}
    ↓
GroupChatManager.update_group_name()
    ↓
Update Group object + save_to_json()
    ↓
groups.json persisted atomically
    ↓
Response: {success, group_id, name}
    ↓
Update local state: setCurrentChatInfo()
```

### Reference Implementation
Based on working chat rename system:
- **API Reference:** `chat_history_routes.py:245-283` - PATCH /api/chats/{id}
- **Manager Reference:** `chat_history_manager.py` - rename_chat()
- **UI Reference:** `ChatSidebar.tsx:159-186` - handleRenameChat()

---

## Testing

### Manual Test Steps

1. **Create a group chat**
   ```
   - Open Group Creator panel
   - Add 2+ agents
   - Create group with name "Test Group"
   - Verify group appears in chat
   ```

2. **Rename from header**
   ```
   - Click on "Test Group" name in chat header
   - Enter new name: "Renamed Group"
   - Press OK
   - Verify header updates immediately
   ```

3. **Verify persistence**
   ```
   - Reload page
   - Open same group from history
   - Verify name is "Renamed Group"
   - Check data/groups.json for updated name
   ```

4. **Test error cases**
   ```
   - Try empty name → Should reject
   - Try same name → Should cancel
   - Try non-existent group ID → 404 error
   ```

### API Testing
```bash
# Get group ID
curl http://localhost:8000/api/groups | jq '.groups[0].id'

# Rename group
GROUP_ID="<your-group-id>"
curl -X PATCH http://localhost:8000/api/groups/$GROUP_ID \
  -H "Content-Type: application/json" \
  -d '{"name": "New Amazing Name"}'

# Expected response:
# {"success":true,"group_id":"...","name":"New Amazing Name"}

# Verify in groups.json
cat data/groups.json | jq ".groups[\"$GROUP_ID\"].name"
```

---

## Markers for Audit
All code marked with phase-specific markers for easy tracking:

- `MARKER_GROUP_RENAME_API` - API endpoint in group_routes.py
- `MARKER_GROUP_RENAME_HANDLER` - Handler method in group_chat_manager.py
- `MARKER_GROUP_RENAME_UI` - UI logic in ChatPanel.tsx

Search project with:
```bash
rg "MARKER_GROUP_RENAME"
```

---

## Comparison: Chat vs Group Rename

| Feature | Regular Chat | Group Chat |
|---------|-------------|------------|
| Endpoint | PATCH /api/chats/{id} | PATCH /api/groups/{id} |
| Body Key | display_name | name |
| Manager | ChatHistoryManager | GroupChatManager |
| Storage | data/chat_history.json | data/groups.json |
| UI Trigger | handleRenameChatFromHeader (chat mode) | handleRenameChatFromHeader (group mode) |
| State Check | !activeGroupId | activeGroupId |

---

## Future Enhancements

1. **Real-time sync:** Broadcast group rename to all participants via WebSocket
2. **Rename history:** Track rename history in group metadata
3. **Permissions:** Restrict rename to admin role only
4. **Validation:** Check for duplicate group names
5. **UI improvement:** Inline edit instead of prompt dialog

---

## Files Changed

1. `/src/api/routes/group_routes.py` - Added PATCH endpoint
2. `/src/services/group_chat_manager.py` - Added update_group_name()
3. `/client/src/components/chat/ChatPanel.tsx` - Enhanced handleRenameChatFromHeader()
4. `/docs/PHASE_108.5_GROUP_RENAME.md` - This documentation

---

## Success Criteria

- [x] Backend API endpoint accepts group ID and new name
- [x] Backend persists name change to groups.json
- [x] Frontend UI allows clicking header to rename
- [x] Frontend updates display immediately after rename
- [x] Renamed groups load with correct name from history
- [x] Error handling for invalid inputs
- [x] Consistent with existing chat rename UX

---

## Conclusion

Phase 108.5 successfully implements group chat renaming with full parity to regular chat rename functionality. The implementation follows existing patterns, maintains data integrity, and provides a seamless user experience.

**Implementation Time:** ~30 minutes
**Lines Changed:** ~120 lines across 3 files
**Testing Status:** Ready for manual testing
