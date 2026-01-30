# Phase 82: Code Locations & Implementation Reference

Quick lookup guide for all relevant code locations and exact line numbers.

---

## FRONTEND CODE LOCATIONS

### 1. ChatPanel.tsx - Main Orchestrator
**Path:** `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/client/src/components/chat/ChatPanel.tsx`

| Feature | Lines | What's Here |
|---------|-------|-----------|
| Group state variables | 87-91 | `activeGroupId`, `modelForGroup`, `activeTab` |
| Group socket listeners | 167-280 | Event handlers for group messages |
| Group creation handler | 314-441 | `handleCreateGroup()` - full implementation |
| Chat name header (EDITABLE) | 1372-1460 | Click to rename chat name |
| **GROUP HEADER (TARGET FOR PHASE 82)** | **1296-1346** | **WHERE TO ADD SETTINGS BUTTON** |
| Group Creator Panel renderer | 1571-1590 | GroupCreatorPanel display |
| Message input props | 1653-1669 | Pass group mode flag |

**Key Functions:**
```typescript
// Line 314
const handleCreateGroup = useCallback(async (name, agents) => {
  // 1. POST /api/groups (create)
  // 2. POST /api/groups/{id}/participants (add agents)
  // 3. setActiveGroupId(groupId)
  // 4. Switch to chat tab
})

// Line 1296 - Group Header START
{activeGroupId && (
  <div>
    {/* MODIFY THIS SECTION - Add Settings button here */}
    <button onClick={() => leaveGroup()}>Leave</button>
  </div>
)}
```

**Current Group Header Code (Lines 1296-1346):**
```typescript
{activeGroupId && (
  <div style={{
    display: 'flex',
    alignItems: 'center',
    gap: 8,
    padding: '6px 12px',
    fontSize: 12,
    color: '#888',
    background: '#161616',
    borderRadius: 4,
  }}>
    <span style={{ width: 6, height: 6, borderRadius: '50%', background: '#6a8' }} />
    <span style={{ color: '#aaa' }}>Group Active</span>
    <span style={{ color: '#555' }}>|</span>
    <span style={{ color: '#666', fontSize: 10 }}>Use @role to mention</span>
    <button onClick={() => { leaveGroup(activeGroupId); setActiveGroupId(null); }}>
      Leave
    </button>
  </div>
)}
```

**TODO for Phase 82:**
- Add Settings button before Leave button
- Add `showGroupEditor` state
- Create modal trigger function

---

### 2. GroupCreatorPanel.tsx - Reference for Editor
**Path:** `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/client/src/components/chat/GroupCreatorPanel.tsx`

| Feature | Lines | Notes |
|---------|-------|-------|
| Agent interface | 9-12 | Model for participant |
| Component props | 14-21 | What data it receives |
| Default roles | 24 | `['PM', 'Architect', 'Dev', 'QA', 'Researcher']` |
| Agent slot rendering | 215-301 | How roles are displayed with models |
| Create button | 354-384 | Logic for enabling/disabling |

**Pattern to Reuse:** Agent slot system (click to select model) is perfect for the editor!

---

### 3. MessageInput.tsx - Mention System
**Path:** `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/client/src/components/chat/MessageInput.tsx`

| Feature | Lines | What's Here |
|---------|-------|-----------|
| Group participant interface | 25-29 | Type for mentions |
| Mention popup import | 21 | MentionPopup component |
| Voice models detection | 41-42 | Props for voice support |
| Group mode flag | 39 | `isGroupMode?: boolean` |

**Note:** @mention detection happens automatically - already handles group participants!

---

### 4. useStore.ts - State Management
**Path:** `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/client/src/store/useStore.ts`

| Feature | Lines | Notes |
|---------|-------|-------|
| Chat messages state | 79 | `chatMessages: ChatMessage[]` |
| **GROUP-SPECIFIC STATE** | **NONE** | **Add new fields here for Phase 82?** |
| Pinned files | 91 | How context files are managed |

**Decision Point:** Should group editor state live in:
1. ChatPanel local state (isolated) ← Current approach for activeGroupId
2. useStore (global) ← New fields for group data

**Recommendation:** Keep in ChatPanel to avoid store bloat.

---

### 5. ChatSidebar.tsx - Group in History
**Path:** `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/client/src/components/chat/ChatSidebar.tsx`

Groups appear in sidebar as chat history entries. When clicked, loads group messages and sets activeGroupId.

---

## BACKEND CODE LOCATIONS

### 1. group_routes.py - HTTP API Endpoints
**Path:** `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/api/routes/group_routes.py`

#### Existing Endpoints:
```python
# Line 49 - List groups
@router.get("")
async def list_groups():

# Line 58 - Create group (WORKS)
@router.post("")
async def create_group(body: CreateGroupRequest):
    # 165 lines of implementation
    # Uses GroupChatManager.create_group()

# Line 80 - Get single group
@router.get("/{group_id}")
async def get_group(group_id: str):

# Line 92 - Add participant (WORKS)
@router.post("/{group_id}/participants")
async def add_participant(group_id: str, body: AddParticipantRequest):

# Line 110 - Remove participant (WORKS)
@router.delete("/{group_id}/participants/{agent_id}")
async def remove_participant(group_id: str, agent_id: str):

# Line 121 - Get messages
@router.get("/{group_id}/messages")
async def get_messages(group_id: str, limit: int = 50):

# Line 130 - Send message (WORKS)
@router.post("/{group_id}/messages")
async def send_message(group_id: str, body: SendMessageRequest):

# Line 148 - Assign task
@router.post("/{group_id}/tasks")
async def assign_task(group_id: str, body: AssignTaskRequest):
```

#### Missing Endpoints (Phase 82):
```python
# NEEDS TO BE ADDED:

@router.patch("/{group_id}")
async def update_group(group_id: str, body: UpdateGroupRequest):
    """Update group metadata (name, description)."""
    # Similar to add_participant pattern
    # Call manager.update_group()
    # Return updated group

@router.patch("/{group_id}/participants/{agent_id}")
async def update_participant(group_id: str, agent_id: str, body: UpdateParticipantRequest):
    """Update participant (model_id, role, display_name)."""
    # Similar to add_participant pattern
    # Call manager.update_participant()
    # Return updated participant
```

#### Request Models to Add:
```python
# After line 45 (AddParticipantRequest)

class UpdateGroupRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None

class UpdateParticipantRequest(BaseModel):
    model_id: Optional[str] = None
    role: Optional[str] = None
    display_name: Optional[str] = None
```

---

### 2. group_chat_manager.py - Core Business Logic
**Path:** `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/services/group_chat_manager.py`

#### Data Classes:
```python
# Lines 24-28 - GroupRole Enum
class GroupRole(Enum):
    ADMIN = "admin"
    WORKER = "worker"
    REVIEWER = "reviewer"
    OBSERVER = "observer"

# Lines 31-47 - GroupParticipant
@dataclass
class GroupParticipant:
    agent_id: str              # "@architect"
    model_id: str              # "llama-405b"
    role: GroupRole
    display_name: str
    permissions: List[str]

# Lines 75-99 - Group
@dataclass
class Group:
    id: str
    name: str
    description: str
    admin_id: str
    participants: Dict[str, GroupParticipant]
    messages: deque
    shared_context: Dict[str, Any]
    project_id: Optional[str]
    created_at: datetime
    last_activity: datetime
```

#### Key Methods to Reference:
```python
# Line 297 - Create group (REFERENCE)
async def create_group(self, name, admin_agent, ...):
    # Creates Group, stores in _groups, saves to JSON
    # Pattern to follow for update_group

# Line 349 - Add participant (REFERENCE)
async def add_participant(self, group_id, participant):
    # Updates participants dict
    # Saves to JSON
    # Emits event

# Line 377 - Remove participant (REFERENCE)
async def remove_participant(self, group_id, agent_id):
    # Removes from dict
    # Updates agent tracking
    # Saves to JSON

# Line 625 - Get group (UTILITY)
def get_group(self, group_id):
    return self._groups.get(group_id).to_dict()

# Line 653 - Save to JSON (CALLED BY ALL UPDATES)
async def save_to_json(self):
    # Persists all groups to data/groups.json
    # Called after every change
    # Handles atomic writes
```

#### Methods to Add (Phase 82):
```python
# Add after remove_participant (around line 400):

async def update_group(self, group_id: str, updates: dict) -> Optional[Group]:
    """Update group metadata.

    Updates: name, description
    """
    async with self._lock:
        group = self._groups.get(group_id)
        if not group:
            return None

        # Update fields if provided
        if 'name' in updates:
            group.name = updates['name']
        if 'description' in updates:
            group.description = updates['description']

        # Update activity timestamp
        group.last_activity = datetime.now()

    # Emit event
    if self._socketio:
        await self._socketio.emit('group_updated', {
            'group_id': group_id,
            'updates': updates
        })

    # Persist
    await self.save_to_json()

    logger.info(f"[GroupChat] Updated group: {group_id}")
    return group


async def update_participant(
    self,
    group_id: str,
    agent_id: str,
    updates: dict
) -> bool:
    """Update participant metadata.

    Updates: model_id, role, display_name
    """
    async with self._lock:
        group = self._groups.get(group_id)
        if not group or agent_id not in group.participants:
            return False

        participant = group.participants[agent_id]

        # Update fields if provided
        if 'model_id' in updates:
            participant.model_id = updates['model_id']
        if 'role' in updates:
            participant.role = GroupRole(updates['role'])
        if 'display_name' in updates:
            participant.display_name = updates['display_name']

        # Update activity timestamp
        group.last_activity = datetime.now()

    # Emit event
    if self._socketio:
        await self._socketio.emit('participant_updated', {
            'group_id': group_id,
            'agent_id': agent_id,
            'updates': updates
        })

    # Persist
    await self.save_to_json()

    logger.info(f"[GroupChat] Updated participant {agent_id} in {group_id}")
    return True
```

#### Persistence:
```python
# Line 653-700 - save_to_json()
# Already called by all update methods
# Handles atomic writes to data/groups.json
# No changes needed - just call from new methods

# Line 702-779 - load_from_json()
# Called on startup to restore groups from disk
# No changes needed for Phase 82
```

---

### 3. group_message_handler.py - Real-time Message Routing
**Path:** `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/api/handlers/group_message_handler.py`

Not directly involved in editing, but handles:
- Socket.IO events for group messages
- Agent selection and routing
- Broadcasting to clients

**Note:** May need to add new event handlers for:
- `group_updated` - notify all members
- `participant_updated` - notify all members

---

## CONFIGURATION & CONSTANTS

### Router Registration
**Path:** `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/api/routes/__init__.py`

Check that `group_routes.py` is imported and registered with FastAPI app.

### GroupChatManager Singleton
**Path:** `src/api/routes/group_routes.py` (lines 11-15)

```python
from src.services.group_chat_manager import (
    get_group_chat_manager,
    GroupParticipant,
    GroupRole
)

manager = get_group_chat_manager()  # Always use singleton
```

All backend endpoints use `get_group_chat_manager()` - ensures single instance!

---

## DATA PERSISTENCE PATHS

### Groups File
```
Location: data/groups.json
Created by: GroupChatManager.save_to_json()
Format: JSON with groups dict
Size: Grows with group count and messages
Cleanup: Inactive groups removed after 24h
```

### Chat History
```
Endpoint: /api/chats (separate from /api/groups)
Purpose: Frontend sidebar history
Linked via: group_id in chat record
```

---

## SOCKET.IO EVENT NAMES

### Existing (in use):
```
group-message         - User message received
group-stream-start    - Agent started responding
group-stream-token    - Streaming token
group-stream-end      - Agent finished
group-error           - Error occurred
```

### Need to Add (Phase 82):
```
group-updated         - Group name/description changed
participant-updated   - Participant model/role changed
participant-removed   - Participant removed
```

**Emit location:** `group_chat_manager.py` in update methods (already shown above)

---

## TYPE DEFINITIONS

### ChatMessage Interface (Frontend)
**File:** `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/client/src/types/chat.ts`

```typescript
interface ChatMessage {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  type: 'text' | 'artifact';
  timestamp: string;
  agent?: string;
  metadata?: Record<string, any>;
}
```

### GroupMessage (Backend)
**File:** `src/services/group_chat_manager.py` (lines 50-72)

```python
@dataclass
class GroupMessage:
    id: str
    group_id: str
    sender_id: str
    content: str
    mentions: List[str]
    message_type: str
    metadata: Dict[str, Any]
    created_at: datetime
```

---

## HTTP STATUS CODES USED

```
200 OK              - Successful GET/PATCH/DELETE
201 Created         - Successful POST
400 Bad Request     - Validation error
404 Not Found       - Group/participant not found
500 Server Error    - Unexpected error
```

**Pattern in group_routes.py:**
```python
if not group:
    raise HTTPException(status_code=404, detail="Group not found")

return {'success': True}  # For operations
return {'group': group.to_dict()}  # For data returns
```

---

## TESTING ENDPOINTS

### Manual cURL Commands (for verification):

```bash
# Create a group
curl -X POST http://localhost:8000/api/groups \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test Group",
    "admin_agent_id": "@PM",
    "admin_model_id": "gpt-4",
    "admin_display_name": "PM"
  }'

# Get group
curl -X GET http://localhost:8000/api/groups/{group-id}

# Send message
curl -X POST http://localhost:8000/api/groups/{group-id}/messages \
  -H "Content-Type: application/json" \
  -d '{
    "sender_id": "user",
    "content": "Hello team"
  }'

# [PHASE 82] Update group
curl -X PATCH http://localhost:8000/api/groups/{group-id} \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Updated Name",
    "description": "New description"
  }'

# [PHASE 82] Update participant
curl -X PATCH http://localhost:8000/api/groups/{group-id}/participants/@PM \
  -H "Content-Type: application/json" \
  -d '{
    "model_id": "claude-3",
    "role": "worker"
  }'
```

---

## QUICK CHECKLIST FOR IMPLEMENTATION

### Phase 82 Checklist:

**Backend (src/api/routes/group_routes.py)**
- [ ] Add `UpdateGroupRequest` model (after line 45)
- [ ] Add `UpdateParticipantRequest` model (after line 45)
- [ ] Add `@router.patch("/{group_id}")` endpoint
- [ ] Add `@router.patch("/{group_id}/participants/{agent_id}")` endpoint

**Backend (src/services/group_chat_manager.py)**
- [ ] Add `update_group()` method (after line 400)
- [ ] Add `update_participant()` method (after `update_group()`)
- [ ] Add logger calls for debugging

**Frontend (client/src/components/chat/ChatPanel.tsx)**
- [ ] Add `showGroupEditor` state (line 90-ish)
- [ ] Add Settings button to group header (line 1296-1346)
- [ ] Create modal/overlay for GroupEditorPanel
- [ ] Add event listener for group updates (if needed)

**Frontend (new file: GroupEditorPanel.tsx)**
- [ ] Create component (based on GroupCreatorPanel pattern)
- [ ] Show group name/description editable
- [ ] Show participants with edit controls
- [ ] Implement save logic (calls PATCH endpoints)
- [ ] Implement cancel logic

**Integration**
- [ ] Test create → edit → save flow
- [ ] Test adding/removing participants
- [ ] Test model/role changes
- [ ] Test socket.io event broadcasts
- [ ] Verify data persistence to JSON

---

## References & Dependencies

### Frontend Dependencies
- React (hooks: useState, useCallback, useEffect)
- Zustand (useStore)
- Lucide icons (for UI buttons)
- Custom hooks: useSocket (for group operations)

### Backend Dependencies
- FastAPI (routes, HTTPException)
- Pydantic (request/response models)
- Python asyncio (async/await, Lock)
- dataclasses (Group, GroupParticipant, GroupMessage)

### Runtime Files
- `data/groups.json` - Group persistence
- `data/chats/` - Chat history (separate)
- Socket.IO connections - Real-time updates

---

## Key Insights for Implementation

1. **Group objects already exist** in memory and JSON
   - No database migrations needed
   - Just add UI + endpoints

2. **GroupChatManager pattern is proven**
   - `add_participant()` and `remove_participant()` already work
   - `update_*` methods follow the same pattern

3. **No schema validation needed yet**
   - Groups saved as JSON, not database
   - Validation can be done in Pydantic models

4. **Socket.IO events are optional**
   - Updates work without real-time broadcast
   - Can add event emission later for better UX

5. **Persistence is automatic**
   - `save_to_json()` called after every update
   - No explicit save logic needed

---

**This reference guide maps every relevant line of code for Phase 82 implementation.**
