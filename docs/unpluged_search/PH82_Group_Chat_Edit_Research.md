# Phase 82: Group Chat Editing Research
## Problem Statement: Limited Group Management After Creation

After creating a group in the UI, users can only "Leave" - editing functionality is completely absent:
- Cannot edit group name or description
- Cannot change member roles
- Cannot swap/change model assignments
- Cannot add/remove participants
- No automatic MCP agent registration

**Status:** Reconnaissance complete. Full architecture mapped.

---

## 1. Current Architecture Overview

### 1.1 Component Structure (Frontend)

```
ChatPanel.tsx (main chat container)
├── activeTab state: 'chat' | 'scanner' | 'group'
├── activeGroupId state: string | null (when in active group)
├── GroupCreatorPanel (displayed when activeTab === 'group')
│   ├── Group name input
│   ├── Team roles (PM, Architect, Dev, QA, Researcher)
│   ├── Agent slot system (click to activate, select model)
│   ├── Custom role modal
│   └── Create button → calls handleCreateGroup()
│
└── Active Group Header (displayed when activeGroupId !== null)
    ├── Status: "Group Active | Use @role to mention"
    ├── Leave button (ONLY BUTTON!)
    └── [MISSING] Edit/Settings button
```

**Key File:** `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/client/src/components/chat/ChatPanel.tsx`

### 1.2 Group State Management

#### In-Memory State (ChatPanel)
```typescript
// Lines 87-91 of ChatPanel.tsx
const [modelForGroup, setModelForGroup] = useState<string | null>(null);
const [activeGroupId, setActiveGroupId] = useState<string | null>(null);
const [activeTab, setActiveTab] = useState<'chat' | 'scanner' | 'group'>('chat');
```

#### Persistent Store (useStore)
```typescript
// /src/store/useStore.ts
// Note: No group-specific state in main store!
// Group info comes from API responses only
```

#### Display Info (ChatPanel)
```typescript
// Lines 75-80
const [currentChatInfo, setCurrentChatInfo] = useState<{
  id: string;
  displayName: string | null;
  fileName: string;
  contextType: string;  // 'group', 'file', 'folder', 'topic'
}>(null);
```

**Problem:** When a group is active, `currentChatInfo.contextType = 'group'` but the UI only shows name + Leave button. No edit capabilities exist.

---

## 2. API Endpoints (Backend)

### 2.1 Group Routes Available
**File:** `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/api/routes/group_routes.py`

#### Implemented (Working)
```
POST   /api/groups                      Create group
GET    /api/groups                      List all groups
GET    /api/groups/{group_id}           Get group details
POST   /api/groups/{group_id}/participants
DELETE /api/groups/{group_id}/participants/{agent_id}  Remove participant
GET    /api/groups/{group_id}/messages  Get messages
POST   /api/groups/{group_id}/messages  Send message
POST   /api/groups/{group_id}/tasks     Assign task
```

#### Missing (Needed for UI)
```
PATCH  /api/groups/{group_id}           UPDATE: name, description
PATCH  /api/groups/{group_id}/participants/{agent_id}  UPDATE: role, model
```

### 2.2 Group Data Model
**File:** `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/services/group_chat_manager.py`

```python
@dataclass
class Group:
    id: str
    name: str
    description: str = ""
    admin_id: str = ""
    participants: Dict[str, GroupParticipant]  # agent_id -> participant
    messages: deque  # Bounded to 1000 messages
    shared_context: Dict[str, Any]
    project_id: Optional[str]
    created_at: datetime
    last_activity: datetime

@dataclass
class GroupParticipant:
    agent_id: str              # "@architect", "@rust_dev"
    model_id: str              # "llama-405b"
    role: GroupRole            # Enum: ADMIN, WORKER, REVIEWER, OBSERVER
    display_name: str
    permissions: List[str]     # ["read", "write"]
```

**Key Insight:** All necessary data structures exist - implementation is straightforward.

---

## 3. UI Location Analysis

### 3.1 Group Header (Line 1296-1346 of ChatPanel.tsx)

```typescript
{activeGroupId && (
  <div style={{...}}>
    {/* Status indicator + Leave button */}
    <span>Group Active</span>
    <span>|</span>
    <span>Use @role to mention</span>
    <button onClick={() => leaveGroup()}>Leave</button>
    {/* ← ONLY BUTTON! No Edit/Settings */}
  </div>
)}
```

**Problem Zones:**
1. No settings/edit button
2. No modal/panel for editing
3. No way to access group state after creation

### 3.2 Group Creator Panel (Lines 1571-1590)

```typescript
{activeTab === 'group' && (
  <GroupCreatorPanel
    selectedModel={modelForGroup}
    onCreateGroup={handleCreateGroup}
    {...props}
  />
)}
```

**Where it appears:**
- Only when `activeTab === 'group'`
- Exits to chat mode immediately after group creation
- Cannot be reopened to edit

---

## 4. Message Input Analysis (@shortcuts)

### 4.1 @Mention System
**File:** `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/client/src/components/chat/MessageInput.tsx`

#### MentionPopup Component
- Watches for `@` character in input
- Shows filtered list of group participants (if in group mode)
- Used for @role mentions: `@PM`, `@architect`, etc.
- NOT used for shortcuts or commands

### 4.2 Command Detection in Backend
**File:** `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/services/group_chat_manager.py` (Lines 225-253)

```python
# /solo - route to single agent
if '/solo' in content_lower:
    return [first_available_agent]

# /team or /all - route to all agents
if '/team' in content_lower or '/all' in content_lower:
    return all_agents

# /round or /roundtable - sequential order
if '/round' in content_lower:
    return agents_sorted_by_role
```

**Key Point:** Commands are `/<something>` not `@<something>`. The `@` system is only for mentions in the GroupChatManager, used in `select_responding_agents()`.

### 4.3 @ vs / Command Distinction

| Feature | @ (Mentions) | / (Commands) |
|---------|-------------|------------|
| Purpose | Explicit targeting of agents | Group behavior modes |
| Parsed by | `parse_mentions()` in GroupChatManager | `select_responding_agents()` logic |
| Examples | @PM, @architect, @rust_dev | /solo, /team, /round |
| Response | Only mentioned agents respond | Multiple agents respond |
| Persistence | Stored in message.mentions | Not stored, interpreted per-call |

---

## 5. Backend Group Chat Manager Deep Dive

### 5.1 Group Lifecycle

```
create_group()
    ↓ Creates Group object with admin
    ↓ Stores in self._groups[group_id]
    ↓ Tracks agent-group relationship
    ↓ Saves to data/groups.json

add_participant()
    ↓ Adds to group.participants
    ↓ Updates agent tracking
    ↓ Saves to JSON

send_message()
    ↓ Parses mentions from content
    ↓ Creates GroupMessage
    ↓ Stores in group.messages (deque, max 1000)
    ↓ Saves to JSON
    ↓ Returns message

select_responding_agents()
    ↓ Intelligent routing:
    ↓ 1. Reply routing (if replying to specific agent)
    ↓ 2. @mentions explicit targeting
    ↓ 3. /commands (solo, team, round)
    ↓ 4. SMART keyword detection
    ↓ 5. Default: first available + prefer admin
```

### 5.2 Persistence
**File:** `data/groups.json` - Auto-saved after:
- Group creation
- Message send
- Participant add/remove
- Group cleanup

```json
{
  "groups": {
    "uuid-1": {
      "id": "uuid-1",
      "name": "Code Review Team",
      "description": "...",
      "admin_id": "@PM",
      "participants": {
        "@PM": {...},
        "@Architect": {...},
        "@Dev": {...}
      },
      "messages": [...],
      "created_at": "2026-01-21T...",
      "last_activity": "2026-01-21T..."
    }
  },
  "saved_at": "2026-01-21T..."
}
```

---

## 6. Chat History Integration

### 6.1 Group Chat History
**File:** `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/client/src/components/chat/ChatSidebar.tsx`

When group is created, it's also saved to chat history:

```typescript
// Lines 389-401 of ChatPanel.tsx
const chatResponse = await fetch('/api/chats', {
  method: 'POST',
  body: JSON.stringify({
    display_name: name,        // Group name
    context_type: 'group',     // Flag as group chat
    items: validAgents.map(a => `@${a.role}`),
    group_id: groupId          // Link to GroupChatManager
  })
});
```

**Result:**
- Group appears in left sidebar as chat history
- Can be reopened to load messages
- But NO EDIT capability when reopened

---

## 7. Design Gaps & Implementation Roadmap

### 7.1 Critical Missing Components

| Feature | Location | Status | Impact |
|---------|----------|--------|--------|
| Edit Group Panel | UI component | ❌ Missing | Cannot change name/description |
| Participant Manager | UI component | ❌ Missing | Cannot add/remove/change roles |
| Settings Button | Header (group indicator) | ❌ Missing | Cannot access editing UI |
| PATCH /api/groups/{id} | Backend route | ❌ Missing | Cannot save group edits |
| PATCH participants/{agent_id} | Backend route | ❌ Missing | Cannot change model/role |
| MCP Agent Registration | Backend logic | ❌ Missing | Agents not auto-registered |

### 7.2 Frontend Implementation Path

```
1. Add "Settings" button next to "Leave" button
   └─ Located in ChatPanel.tsx line 1296-1346

2. Create GroupEditorPanel component
   └─ Similar to GroupCreatorPanel
   └─ Show: name, description, participant list with edit controls

3. Add edit modal overlay
   └─ Modal state in ChatPanel
   └─ Triggered by Settings button
   └─ Contains GroupEditorPanel

4. Connect to new backend endpoints
   └─ PATCH /api/groups/{group_id}
   └─ PATCH /api/groups/{group_id}/participants/{agent_id}

5. Update store to track group state
   └─ Consider adding to useStore
   └─ Or fetch fresh on modal open
```

### 7.3 Backend Implementation Path

```
1. Add PATCH endpoint for group metadata
   File: src/api/routes/group_routes.py

   class UpdateGroupRequest(BaseModel):
       name?: str
       description?: str

   @router.patch("/{group_id}")
   async def update_group(group_id: str, body: UpdateGroupRequest):
       # Update group.name, group.description
       # Call manager.update_group()
       # Return updated group.to_dict()

2. Add PATCH endpoint for participant updates

   class UpdateParticipantRequest(BaseModel):
       model_id?: str
       role?: str
       display_name?: str

   @router.patch("/{group_id}/participants/{agent_id}")
   async def update_participant(...):
       # Update participant.model_id, role, display_name
       # Call manager.update_participant()

3. Add methods to GroupChatManager

   async def update_group(group_id: str, updates: dict) -> Group
   async def update_participant(group_id: str, agent_id: str, updates: dict) -> bool

4. MCP Agent Auto-Registration
   └─ When participant is added with agent_id starting with @
   └─ Attempt to register via MCP service
   └─ Store registration status in metadata
```

---

## 8. Socket.IO Events Mapping

### Current Group Events (for reference)

```typescript
// Client-side event listeners (ChatPanel.tsx lines 267-278)
'group-message'       → New message received
'group-stream-start'  → Agent started responding
'group-stream-token'  → Streaming token received
'group-stream-end'    → Agent finished responding
'group-error'         → Group operation error

// Server-side emissions (group_chat_manager.py)
'group_created'       → New group created
'group_joined'        → Participant joined
'group_left'          → Participant left
'task_created'        → Task assigned
```

### New Events Needed

```
'group_updated'       → Group name/description changed
'participant_updated' → Participant role/model changed
'participant_removed' → Participant removed from group
```

---

## 9. Code References Summary

### Frontend Files
1. **ChatPanel.tsx** (main orchestrator)
   - Line 87-91: activeGroupId, modelForGroup state
   - Line 314-441: handleCreateGroup() implementation
   - Line 1296-1346: Active group header (NEEDS EDIT BUTTON)
   - Line 1571-1590: GroupCreatorPanel renderer (EXIT-ONLY)

2. **GroupCreatorPanel.tsx** (model for editor)
   - Slots system for agent assignment
   - Role selection with model validation
   - Perfect reference for GroupEditorPanel

3. **ChatSidebar.tsx**
   - Loads chat history including groups
   - Shows group name in history

### Backend Files
1. **group_routes.py** (missing PATCH endpoints)
   - Current: POST, GET, DELETE only
   - Missing: PATCH for updates

2. **group_chat_manager.py** (core logic)
   - GroupChatManager.create_group() - reference for update method
   - GroupChatManager.add_participant() - use same pattern
   - Full persistence to data/groups.json

3. **group_message_handler.py**
   - Real-time message routing
   - Agent selection logic

---

## 10. Current Behavior vs Expected Behavior

### Current Flow
```
User Creates Group
    ↓ (ChatPanel.handleCreateGroup)
    ↓ POST /api/groups (create)
    ↓ POST /api/groups/{id}/participants (add agents)
    ↓ setActiveGroupId(groupId)
    ↓ Switch to chat tab
    ↓ Show "Group Active | Leave" header
    ↓ [STUCK] Cannot edit anything!
    ↓ User can only: send messages OR leave
```

### Expected Flow (with Phase 82)
```
User Creates Group
    ↓ ...same as above...
    ↓ Show "Group Active | Settings | Leave" header
    ↓ User clicks "Settings"
    ↓ GroupEditorPanel opens
    ├─ Edit name/description
    ├─ Manage participants
    │   ├─ Change agent model
    │   ├─ Change role (admin→worker)
    │   └─ Remove participant
    ├─ Add new participant
    │   ├─ Select unused role
    │   └─ Assign model
    └─ Save changes → PATCH /api/groups/{id}
       ↓
       ✓ Group updated
       ✓ All participants see changes
```

---

## 11. Design Considerations

### 11.1 UI Patterns to Follow

1. **Consistency with GroupCreatorPanel**
   - Same IKEA-style grayscale design
   - Same slot-based agent system
   - Same model directory integration

2. **Modal vs Sidebar**
   - Option A: Modal overlay (like GroupCreatorPanel fallback)
   - Option B: Replace GroupCreatorPanel when editing (less intrusive)
   - Recommendation: Option B - cleaner UX

3. **Permission Model**
   - Only admin (first agent) can edit group
   - OR: Allow all agents but log modifications
   - Consider: Group-level vs agent-specific permissions

### 11.2 State Management Strategy

**Current:** ChatPanel local state + API responses
**Recommended:**
- Keep in ChatPanel (isolated)
- OR: Add to useStore with group-specific reducer
- Load fresh on open to avoid stale data

### 11.3 Error Handling

- Participant in use elsewhere? Can't remove
- Model changed to offline? Show warning
- Network error during save? Retry UI
- Concurrent edits? Last-write-wins (add timestamp check)

---

## 12. Testing Strategy

### Unit Tests Needed
```
Backend:
- test_update_group() - name, description changes
- test_update_participant() - role, model changes
- test_remove_participant() - permission checks
- test_invalid_updates() - validation

Frontend:
- test_open_editor() - Settings button click
- test_change_model() - Update participant model
- test_change_role() - Update participant role
- test_save_changes() - API call validation
- test_revert_changes() - Cancel operation
```

### Integration Tests
```
- Create group → Edit → Verify in history
- Edit group → Leave → Rejoin → See changes
- Edit while in group chat → Messages continue
- Concurrent edits from different groups → isolation
```

---

## 13. Known Limitations & Constraints

1. **Agent Registration**
   - MCP agents need explicit registration
   - Current system: agents self-register on first message
   - Issue: Group creator doesn't auto-register unless they chat

2. **Offline Models**
   - Changing to offline model = potential failure
   - Need validation before save

3. **Data Consistency**
   - JSON file can be manually edited/corrupted
   - No database schema validation
   - Add checksums or timestamps

4. **Memory Management**
   - Groups kept in memory (LRU eviction after 24h)
   - Editing won't trigger persistence unless save button
   - Consider auto-save every 30s in editor

---

## 14. Phase 82 Scope Definition

### In Scope
- [x] Edit group name/description
- [x] Change participant models
- [x] Change participant roles
- [x] Remove participants from group
- [x] Add new participants to group
- [x] API endpoints (PATCH methods)

### Out of Scope (Phase 83+)
- MCP agent auto-registration
- Fine-grained permissions system
- Group archive/unarchive
- Participant permissions management
- Role templates/inheritance
- Audit log of edits

---

## 15. Quick Start Checklist

### To Implement Phase 82:

**Frontend**
- [ ] Add "Settings" button to group header (1h)
- [ ] Create GroupEditorPanel component (2h)
- [ ] Add modal/overlay system (1h)
- [ ] Implement save/cancel flows (1h)
- [ ] Connect to new endpoints (1h)
- [ ] Test with existing groups (30m)

**Backend**
- [ ] Add PATCH /api/groups/{id} endpoint (30m)
- [ ] Add PATCH /api/groups/{id}/participants/{agent_id} (1h)
- [ ] Add manager methods: update_group, update_participant (1h)
- [ ] Add validation/error handling (1h)
- [ ] Test with frontend (1h)

**Total Estimate: 10-11 hours for full Phase 82**

---

## Conclusion

The group editing feature is **architecturally simple** - all underlying systems exist. The gap is purely UI/API routing:

1. **Frontend:** Add Settings button + editor panel (straightforward component)
2. **Backend:** Add two PATCH endpoints (simple CRUD)
3. **Integration:** Connect them with proper error handling

No major refactoring needed. Implementation can be incremental with backward compatibility preserved.

**Next Steps:**
1. Review this research with team
2. Prioritize Phase 82 in sprint
3. Start with backend endpoints (less risk)
4. Add UI components iteratively
5. Test with existing groups + chat history
