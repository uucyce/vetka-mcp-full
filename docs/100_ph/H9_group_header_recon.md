# H9: Group Chat Header Reconnaissance Report

**Objective:** Investigate how group chat header/title works and compare with solo chat implementation.

**Date:** 2026-01-29
**Phase:** Haiku-9 (H9)
**Status:** Complete

---

## Executive Summary

Group chat headers have **minimal visual representation** compared to solo chats. While solo chats display an editable header with context type icons and clear naming, group chats rely on:

1. A `currentChatInfo` object stored after group creation (not fetched later)
2. A separate "Group Active" status bar below the search bar
3. No dedicated header area showing the group name
4. No visible editing UI for group names in the main header

**Key Finding:** Group names ARE editable (via API) but there's NO UI to trigger the edit. The header renaming feature only works for solo chats.

---

## Architecture Overview

### Data Flow

```
Frontend (Chat Creation)
  └─> Group created with name
      └─> setCurrentChatInfo({ displayName: name, contextType: 'group', ... })
          └─> Stored in state (NOT persistent fetch)
              └─> Displays in header if currentChatInfo exists
```

### Storage Locations

1. **Frontend State:** `currentChatInfo` in ChatPanel.tsx
2. **Backend:** `/data/groups.json` (name field)
3. **API:** `GET /api/groups/{group_id}` returns full group object with name

---

## Group Chat Header Implementation

### Current UI Flow

#### 1. Header Creation (ChatPanel.tsx lines 1869-1956)

**Location:** `ChatPanel.tsx:1869-1956` - Conditional chat name header

```typescript
{(activeTab === 'chat' || activeTab === 'group') && currentChatInfo &&
 !(currentChatInfo.contextType === 'file' && pinnedFileIds.length > 0) && (
  <div style={{...}}>
    {/* Header section with name, edit icon, close icon */}
    <div onClick={handleRenameChatFromHeader}>
      {/* Context-type icon (shows group icon for groups) */}
      {currentChatInfo.contextType === 'group' ? (
        <svg>/* group icon */</svg>
      ) : ...}

      {/* Chat name - displays group name here */}
      <span>{currentChatInfo.displayName || currentChatInfo.fileName}</span>

      {/* Edit icon (pencil) */}
      {/* Close icon (X) */}
    </div>
  </div>
)}
```

**Key Points:**
- Displays when `currentChatInfo` exists AND tab is 'chat' or 'group'
- Shows group icon for `contextType === 'group'`
- Displays group name from `currentChatInfo.displayName`
- Has edit and close icons (visual cues)
- Click handler: `handleRenameChatFromHeader`

#### 2. Group Info Initialization (ChatPanel.tsx lines 626-631)

**When group is created:**

```typescript
setCurrentChatInfo({
  id: chatData.chat_id,
  displayName: name,        // Group name passed to creation
  fileName: 'unknown',
  contextType: 'group'
});
```

**CRITICAL ISSUE:** `displayName` is set ONCE at creation and never updated from backend.

#### 3. Group Active Status Bar (ChatPanel.tsx lines 1754-1843)

When `activeGroupId` is set, a separate status bar appears:

```
[dot] Group Active | Use @role to mention | [copy] uuid... | [Leave]
```

This bar shows:
- Green dot indicator
- "Group Active" label
- Instructions to use @role
- Group UUID (copyable)
- Leave button

**Issue:** No group NAME displayed here—only UUID prefix.

---

## Solo Chat vs Group Chat Comparison

| Feature | Solo Chat | Group Chat | Gap |
|---------|-----------|-----------|-----|
| **Header Display** | Yes, with name | Yes, with name | Same ✓ |
| **Header Icon** | File/Folder/Topic | Group users icon | Same ✓ |
| **Header Editability** | Yes (click to rename) | Click works BUT... | ⚠️ See below |
| **Edit UI Trigger** | `handleRenameChatFromHeader()` | `handleRenameChatFromHeader()` | Same handler |
| **Persistent Name** | Saved to `/api/chats/{id}` | Saved to `/api/groups/{id}` (NAME field) | Different endpoints |
| **Name Refresh** | Refetched if needed | Never refetched | **Missing fetch** |
| **Validation** | Optional (not required) | Required (can't be empty) | More strict |

---

## Edit Functionality Analysis

### handleRenameChatFromHeader (ChatPanel.tsx lines 790-816)

```typescript
const handleRenameChatFromHeader = useCallback(() => {
  if (!currentChatInfo) return;

  const currentName = currentChatInfo.displayName || currentChatInfo.fileName;
  const newName = prompt('Rename chat:', currentName);

  if (newName && newName !== currentName) {
    const response = await fetch(`/api/chats/${currentChatInfo.id}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ display_name: newName })
    });

    if (response.ok) {
      setCurrentChatInfo(prev => prev ? { ...prev, displayName: newName.trim() } : null);
    }
  }
}, [currentChatInfo]);
```

### Critical Bug for Group Chats

1. Uses **`/api/chats/{id}`** endpoint (chat history, not groups)
2. Should use **`/api/groups/{group_id}`** for actual group name change
3. `currentChatInfo.id` is the **chat history ID**, not the group ID
4. Frontend stores `activeGroupId` separately (not in `currentChatInfo`)

**Result:** Editing group name via header updates ONLY the chat history display name, NOT the actual group name in `groups.json`.

### Correct Implementation Would Need

```typescript
// For groups:
const endpoint = currentChatInfo.contextType === 'group'
  ? `/api/groups/${activeGroupId}`  // Needs access to activeGroupId
  : `/api/chats/${currentChatInfo.id}`;
```

---

## Group Name Storage & Retrieval

### Backend Structure (groups.json)

```json
{
  "groups": {
    "5e2198c2-8b1a-45df-807f-5c73c5496aa8": {
      "id": "5e2198c2-8b1a-45df-807f-5c73c5496aa8",
      "name": "MCP Dev",           // <-- GROUP NAME
      "description": "Group chat with 3 agents",
      "admin_id": "@Architect",
      "participants": { ... }
    }
  }
}
```

### API Endpoints

**GET /api/groups/{group_id}** (group_routes.py:92-101)
- Returns: `{ 'group': group.to_dict() }`
- Includes: `name`, `description`, `admin_id`, `participants`, `messages`

**PATCH /api/groups/{group_id}** - NOT IMPLEMENTED
- Missing endpoint to update group name/description
- Should support: `{ "name": "New Name", "description": "..." }`

### Frontend Fetch (ChatPanel.tsx lines 399-430)

When `activeGroupId` changes:

```typescript
useEffect(() => {
  if (!activeGroupId) {
    setCurrentGroupParticipants([]);
    return;
  }

  const controller = new AbortController();

  const fetchGroup = async () => {
    const response = await fetch(`/api/groups/${activeGroupId}`);
    const data = await response.json();
    setCurrentGroupParticipants(Object.values(data.group.participants));
  };

  fetchGroup();
  return () => controller.abort();
}, [activeGroupId]);
```

**Issue:** Fetches participants but IGNORES the group name!
- Should also update `currentChatInfo` with latest group name
- Currently: name only set at creation (line 626-631)

---

## UX Comparison: Header Areas

### Solo Chat Header (1 area)
```
┌─────────────────────────────────┐
│ [icon] Chat Name  [edit] [close] │  ← Editable here
├─────────────────────────────────┤
│ [pinned files...]               │
├─────────────────────────────────┤
```

### Group Chat Header (3 areas + confusion)
```
┌─────────────────────────────────┐
│ [icon] Group Name [edit] [close] │  ← Header (editable but broken)
├─────────────────────────────────┤
│ [green·] Group Active | ... | [Leave] │  ← Status bar (no edit)
├─────────────────────────────────┤
│ [pinned files...]               │
├─────────────────────────────────┤
```

**UX Issues:**
1. Two places show group info: header + status bar (redundant)
2. Status bar shows UUID instead of group name
3. Edit via header doesn't work correctly for groups
4. No UI to change description
5. No indication that name can be edited

---

## Editing Workflow Issues

### Current (Broken)

1. User clicks group name in header
2. Prompt appears with current name
3. User enters new name
4. POST to `/api/chats/{chat_id}` (wrong endpoint)
5. Only chat history name updated
6. Actual group name unchanged
7. Next group fetch still shows old name from backend

### Needed (Fixed)

1. User clicks group name in header
2. Check if `contextType === 'group'`
3. Use `activeGroupId` to get actual group ID
4. POST to `/api/groups/{group_id}` with new name
5. Update both:
   - Group name in backend (groups.json)
   - `currentChatInfo.displayName` in frontend
6. Show success/error feedback

---

## Missing Components

### 1. Group Name Update Endpoint
- File: `src/api/routes/group_routes.py`
- Need: PATCH endpoint to update group name/description
- Current: Only has participant management

```python
# MISSING:
@router.patch("/{group_id}")
async def update_group(group_id: str, body: UpdateGroupRequest):
    """Update group name and description."""
    # Update groups.json
    # Broadcast update to all members via WebSocket
    pass
```

### 2. Frontend Group Edit UI
- File: `ChatPanel.tsx:790-816`
- Need: Conditional endpoint selection based on context type
- Need: Pass `activeGroupId` to handler

```typescript
// NEEDED:
const handleRenameChatFromHeader = useCallback(() => {
  if (currentChatInfo?.contextType === 'group' && activeGroupId) {
    // Use group endpoint with activeGroupId
  } else {
    // Use chat endpoint
  }
}, [currentChatInfo, activeGroupId]);
```

### 3. Name Persistence on Rejoin
- After leaving/rejoining group
- Name should be fetched fresh from backend
- Currently: Lost until page reload

---

## Group Name Editing Functionality Status

### ✓ Working
- Group creation with name
- Display name in header
- Header UI (click to edit)
- Name storage in backend (groups.json)
- API to fetch group name (`GET /api/groups/{id}`)

### ✗ Broken
- Editing group name via header (wrong endpoint)
- Persisting name edits (no backend endpoint)
- Name refresh on rejoin (not fetched)
- Name displayed in status bar (shows UUID instead)

### ✗ Missing
- PATCH endpoint for group updates
- UI feedback for edit success/failure
- Description editing UI
- Name validation (required, length limits)

---

## Comparison Matrix: Implementation Completeness

| Aspect | Solo Chat | Group Chat | Status |
|--------|-----------|-----------|--------|
| Display name in header | ✓ | ✓ | Complete |
| Edit UI visible | ✓ | ✓ | Complete |
| Edit handler exists | ✓ | ✓ | Partial (broken for groups) |
| Correct endpoint | ✓ | ✗ | Needs fix |
| Backend persistence | ✓ | ✓ | Complete |
| Name refresh on load | ✓ (chat fetch) | ✗ | Missing |
| Update endpoint | ✓ (`/api/chats`) | ✗ (missing) | Needs implementation |
| Error handling | ✓ | ✓ | Complete |

---

## Recommendations

### Immediate Fixes (Phase H10)

1. **Add Group PATCH endpoint**
   - Location: `src/api/routes/group_routes.py`
   - Implement: Update group name and description
   - Validation: Name required, max 255 chars

2. **Fix Frontend Edit Handler**
   - Location: `ChatPanel.tsx:790-816`
   - Add: Conditional endpoint selection
   - Pass: `activeGroupId` to handler
   - Update: `currentChatInfo` correctly

3. **Refresh Group Name on Fetch**
   - Location: `ChatPanel.tsx:399-430` (fetch group effect)
   - Add: Update `currentChatInfo.displayName` with fetched name
   - Ensures: Name always matches backend

### Medium-term Improvements (Phase H11-H12)

1. **Dedicated Group Settings Panel**
   - Replace header editing with dedicated UI
   - Allow editing: name, description, permissions
   - Show member list and roles
   - Current: GroupCreatorPanel in edit mode (close but not perfect)

2. **Enhanced Status Bar**
   - Show group name instead of UUID
   - Option to view/edit from status bar
   - Member count indicator
   - Last activity timestamp

3. **WebSocket Broadcast**
   - Notify all members when group name changes
   - Real-time sync across sessions
   - Update UI for all connected clients

---

## Files Involved

### Frontend
- `/client/src/components/chat/ChatPanel.tsx` - Main header rendering + edit handler
- `/client/src/components/chat/GroupCreatorPanel.tsx` - Group creation and editing
- `/client/src/store/useStore.ts` - Group state (if exists)

### Backend
- `/src/api/routes/group_routes.py` - API endpoints (missing PATCH)
- `/src/services/group_chat_manager.py` - Group management logic
- `/src/api/handlers/group_message_handler.py` - Message routing
- `/data/groups.json` - Persistent storage

---

## Code References

### Line Ranges

| Component | File | Lines | Purpose |
|-----------|------|-------|---------|
| Header render | ChatPanel.tsx | 1869-1956 | Display group name |
| Edit handler | ChatPanel.tsx | 790-816 | Handle name changes |
| Group init | ChatPanel.tsx | 626-631 | Set initial name |
| Status bar | ChatPanel.tsx | 1754-1843 | Show group active status |
| Group fetch | ChatPanel.tsx | 399-430 | Load group participants |
| Creator panel | GroupCreatorPanel.tsx | 142-174 | Load group in edit mode |
| Edit API | GroupCreatorPanel.tsx | 177-224 | Update participants |

---

## Summary Table

| Aspect | Solo Chat | Group Chat | Issue Level |
|--------|-----------|-----------|-------------|
| Visual representation | Rich header with icon | Same as solo | OK ✓ |
| Name editability | Works perfectly | Broken | HIGH 🔴 |
| Name persistence | Per-chat backend | Per-group backend | OK ✓ |
| Status indication | None needed | UUID only | MEDIUM 🟡 |
| Refresh on rejoin | Yes | No | MEDIUM 🟡 |
| Dedicated UI | None (header only) | GroupCreatorPanel | MEDIUM 🟡 |
| Error feedback | Yes | Yes | OK ✓ |

---

## Next Steps

1. **Implement PATCH /api/groups/{id}** endpoint
2. **Fix ChatPanel edit handler** to use correct endpoint for groups
3. **Add name refresh** when group info is fetched
4. **Update status bar** to show group name not UUID
5. **Add UI tests** to verify edit flow works end-to-end

---

**Report Generated:** 2026-01-29
**Mission:** H9 Complete
**Status:** Ready for H10 implementation phase
