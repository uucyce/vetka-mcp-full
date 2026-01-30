# H8 Reconnaissance: Group Chat Pinned Files Support

**Objective:** Verify if pinned files work in group chat mode
**Date:** 2026-01-29
**Status:** VERIFICATION COMPLETE

---

## Executive Summary

**FINDING: Group chat does NOT currently support pinned files.**

Pinned files are fully implemented and working in **solo chat mode** (Phase 100.2), but the architecture has not been extended to group chat. The two systems use fundamentally different data storage patterns, and no bridges exist to support shared pinned files in group contexts.

---

## Architecture Comparison

### Solo Chat (WORKING)

**Frontend Store:**
- **Location:** `client/src/store/useStore.ts`
- **State:** `pinnedFileIds` (array of node IDs)
- **Auto-save:** YES - saves whenever state changes
- **API:** `PUT /api/chats/{chat_id}/pinned`

**Backend Storage:**
- **Location:** `src/chat/chat_history_manager.py`
- **Data Model:** Each chat has `pinned_file_ids: List[str]` field
- **Persistence:** `data/chat_history.json`
- **Implementation:** ChatHistoryManager methods:
  - `update_pinned_files(chat_id, pinned_file_ids)` - saves pins
  - `get_pinned_files(chat_id)` - retrieves pins on chat load

**API Routes:**
- **Location:** `src/api/routes/chat_history_routes.py`
- **PUT /api/chats/{chat_id}/pinned** - Update pinned files (PinnedFilesRequest)
- **GET /api/chats/{chat_id}/pinned** - Get pinned files for chat

**Frontend Integration:**
- **Location:** `client/src/components/chat/ChatPanel.tsx`
- **Load:** `loadPinnedFiles(currentChatId)` on chat selection (line 832-837)
- **Save:** `savePinnedFiles(currentChatId, pinnedFileIds)` on state change (line 936)
- **UI:** Renders pinned files in context sidebar (lines 1960-2074)

**Data Flow:**
```
User pins file → Zustand state updates → useEffect triggers
→ savePinnedFiles() → PUT /api/chats/{chat_id}/pinned
→ ChatHistoryManager.update_pinned_files()
→ Saved to chat_history.json
```

---

### Group Chat (NOT IMPLEMENTED)

**Frontend State:**
- **Location:** `client/src/components/chat/GroupCreatorPanel.tsx`
- **State:** NO pinned file support
- **UI:** No pinned context display for groups

**Backend Data Model:**
- **Location:** `src/services/group_chat_manager.py`
- **Group Class Fields:**
  - `id`, `name`, `description`
  - `admin_id`, `participants`, `messages`
  - `shared_context`, `project_id`
  - `created_at`, `last_activity`
  - `last_responder_id`, `last_responder_decay`
  - **MISSING:** `pinned_file_ids`

**Persistence:**
- **Location:** `data/groups.json`
- **Structure:** Stores group metadata but NO `pinned_file_ids` field
- **Implementation:** GroupChatManager.save_to_json() (lines 826-873)

**API Routes:**
- **Location:** `src/api/routes/group_routes.py`
- **Available endpoints:**
  - `GET /api/groups` - List all groups
  - `POST /api/groups` - Create group
  - `GET /api/groups/{group_id}` - Get group
  - `POST /api/groups/{group_id}/participants` - Add participant
  - `PATCH /api/groups/{group_id}/participants/{agent_id}/model` - Update model
  - `PATCH /api/groups/{group_id}/participants/{agent_id}/role` - Update role
  - `GET /api/groups/{group_id}/messages` - Get messages
  - `POST /api/groups/{group_id}/messages` - Send message
  - `POST /api/groups/{group_id}/tasks` - Assign task
  - **MISSING:** Pinned file endpoints

**Frontend Integration:**
- **Location:** `client/src/components/chat/ChatPanel.tsx`
- **Current:** No special handling for group pinned files
- **Group-specific:**
  - Condition: `activeTab === 'group'` (line 1960)
  - But no `pinnedFileIds` display for groups
  - Rendering blocked by: No backend support

---

## Gap Analysis

| Component | Solo Chat | Group Chat | Status |
|-----------|-----------|-----------|--------|
| **Frontend Store** | pinnedFileIds ✅ | None ❌ | Needs implementation |
| **Backend Field** | pinned_file_ids ✅ | None ❌ | Needs addition to Group class |
| **Save API** | /api/chats/{id}/pinned ✅ | None ❌ | Needs creation |
| **Load API** | /api/chats/{id}/pinned ✅ | None ❌ | Needs creation |
| **Manager Method** | update_pinned_files() ✅ | None ❌ | Needs implementation |
| **Manager Method** | get_pinned_files() ✅ | None ❌ | Needs implementation |
| **Persistence** | chat_history.json ✅ | groups.json ❌ | Needs schema update |
| **UI Display** | ChatPanel ✅ | ChatPanel needs work ❌ | Needs enhancement |

---

## Detailed Findings

### Backend Architecture Mismatch

**Solo Chat:**
```python
# src/chat/chat_history_manager.py - Line 197
"pinned_file_ids": [],  # Phase 100.2: Persistent pinned files
```

**Group Chat:**
```python
# src/services/group_chat_manager.py - Lines 90-105
@dataclass
class Group:
    id: str
    name: str
    description: str = ""
    admin_id: str = ""
    participants: Dict[str, GroupParticipant] = field(default_factory=dict)
    messages: deque = field(default_factory=lambda: deque(maxlen=1000))
    shared_context: Dict[str, Any] = field(default_factory=dict)
    project_id: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    last_activity: datetime = field(default_factory=datetime.now)
    last_responder_id: Optional[str] = None
    last_responder_decay: int = 0
    # NO pinned_file_ids FIELD
```

### Storage Pattern Difference

**Solo Chat Persistence:**
- File: `data/chat_history.json`
- Each chat object contains full pin list
- Handled by ChatHistoryManager singleton

**Group Chat Persistence:**
- File: `data/groups.json`
- Group object lacks pin storage
- Handled by GroupChatManager singleton

### API Endpoint Gap

No endpoints exist in `src/api/routes/group_routes.py` for:
- `PUT /api/groups/{group_id}/pinned` - Save pins
- `GET /api/groups/{group_id}/pinned` - Load pins

---

## Current Frontend Behavior

**When User Switches to Group Chat:**

```typescript
// Line 1960 in ChatPanel.tsx
{(activeTab === 'chat' || activeTab === 'group') && pinnedFileIds.length > 0 && (
```

This condition SHOULD show pinned files for groups, but:
1. `pinnedFileIds` refers to solo chat Zustand state
2. No separate group pinned state exists
3. Result: Pins are NOT displayed/managed for group chats

---

## Recommendations for Alignment

### Phase 1: Backend (2-3 hours)

1. **Update Group data model:**
   ```python
   # src/services/group_chat_manager.py
   @dataclass
   class Group:
       # ... existing fields ...
       pinned_file_ids: List[str] = field(default_factory=list)
   ```

2. **Add GroupChatManager methods:**
   ```python
   def update_pinned_files(self, group_id: str, pinned_file_ids: List[str]) -> bool
   def get_pinned_files(self, group_id: str) -> List[str]
   ```

3. **Update persistence in save_to_json():**
   ```python
   'pinned_file_ids': group.pinned_file_ids,  # Add to groups_data dict
   ```

4. **Update load_from_json():**
   ```python
   pinned_file_ids=group_dict.get('pinned_file_ids', []),
   ```

5. **Add API routes:**
   ```python
   # src/api/routes/group_routes.py
   @router.put("/{group_id}/pinned")
   async def update_group_pinned_files(group_id: str, body: PinnedFilesRequest)

   @router.get("/{group_id}/pinned")
   async def get_group_pinned_files(group_id: str)
   ```

### Phase 2: Frontend (1-2 hours)

1. **Separate pinned state for groups:**
   ```typescript
   // client/src/store/useStore.ts
   groupPinnedFileIds: string[] = []
   setGroupPinnedFileIds: (ids: string[]) => void
   ```

2. **Add group pin API functions:**
   ```typescript
   // client/src/utils/chatApi.ts
   export async function saveGroupPinnedFiles(groupId, ids)
   export async function loadGroupPinnedFiles(groupId)
   ```

3. **Update ChatPanel for group context:**
   - Load group pins on group selection
   - Save on changes
   - Separate UI state for group vs solo pins

4. **UI: Display group pins in context sidebar**
   ```typescript
   const activePinnedFiles = activeTab === 'group' ? groupPinnedFileIds : pinnedFileIds
   ```

### Phase 3: Testing (1 hour)

- Unit tests for GroupChatManager pin methods
- Integration tests for API endpoints
- Frontend tests for pin persistence across reload
- Verify solo chat pins still work

---

## Risk Assessment

**Low Risk Implementation:**
- Mirrors existing solo chat pattern
- No breaking changes to group chat structure
- Backward compatible: old groups.json loads fine with empty pinned list

**Potential Issues:**
- None identified if implementation follows solo chat model

---

## Files Affected (Implementation Plan)

**Backend Changes:**
1. `src/services/group_chat_manager.py` - Add field + methods
2. `src/api/routes/group_routes.py` - Add pin endpoints
3. `data/groups.json` - Schema update (auto on first save)

**Frontend Changes:**
1. `client/src/store/useStore.ts` - Add groupPinnedFileIds state
2. `client/src/utils/chatApi.ts` - Add group pin functions
3. `client/src/components/chat/ChatPanel.tsx` - Update logic for groups

**Tests:**
1. `tests/test_group_pins.py` - Backend unit tests
2. `client/src/__tests__/groupPins.test.ts` - Frontend tests

---

## Conclusion

**Pinned files in group chat are currently not supported** due to missing:
1. Backend storage field in Group model
2. Manager methods for pin operations
3. API endpoints
4. Frontend state management for group pins

The implementation is straightforward because it can replicate the working solo chat pattern. **Estimated effort: 4-6 hours total** to bring group chat to parity with solo chat pins.

**Recommendation:** Implement as part of Phase 100.3 enhancement since Phase 100.2 (solo pins) is already complete and working.

---

## References

- Solo Chat Pins: Phase 100.2 (Working)
- Group Chat Manager: `src/services/group_chat_manager.py`
- Chat History Manager: `src/chat/chat_history_manager.py`
- API Routes: `src/api/routes/group_routes.py`, `src/api/routes/chat_history_routes.py`
- Frontend: `client/src/components/chat/ChatPanel.tsx`
