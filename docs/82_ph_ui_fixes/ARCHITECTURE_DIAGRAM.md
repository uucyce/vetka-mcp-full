# Group Chat Architecture Diagram

## Current System Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                         FRONTEND (React)                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ChatPanel.tsx (Main Container)                                  │
│  ├─ activeTab: 'chat' | 'scanner' | 'group'                     │
│  ├─ activeGroupId: string | null                                │
│  ├─ currentChatInfo: {id, displayName, contextType}             │
│  │                                                               │
│  ├─ Tab: 'group' (CREATION ONLY)                                │
│  │   └─ GroupCreatorPanel                                       │
│  │       ├─ Group name input                                    │
│  │       ├─ Agent slots [PM] [Arch] [Dev] [QA]                 │
│  │       ├─ Model selection (click slot → ModelDirectory)       │
│  │       └─ Create button → handleCreateGroup()                 │
│  │                                                               │
│  ├─ Tab: 'chat' (WITH ACTIVE GROUP)                             │
│  │   ├─ Group Header (Line 1296-1346)                           │
│  │   │   ├─ Status: "Group Active | Use @role"                  │
│  │   │   ├─ Leave button ← ONLY BUTTON!                         │
│  │   │   └─ [MISSING] Settings button ← Phase 82                │
│  │   │                                                           │
│  │   ├─ Messages (with @mention detection)                      │
│  │   │   └─ MentionPopup (shows: @PM, @Dev, etc.)              │
│  │   │                                                           │
│  │   └─ MessageInput.tsx                                        │
│  │       ├─ Text input with @mention support                    │
│  │       ├─ Voice detection (if @voicemodel)                    │
│  │       └─ Send button                                         │
│  │                                                               │
│  └─ useStore (Zustand)                                          │
│      ├─ chatMessages: ChatMessage[]                             │
│      ├─ nodes: {id → TreeNode}                                  │
│      └─ [NO GROUP-SPECIFIC STATE]                               │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
                              ↓ HTTP/Socket.IO
┌─────────────────────────────────────────────────────────────────┐
│                    BACKEND (FastAPI + Python)                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  HTTP Routes (group_routes.py)                                   │
│  ├─ POST   /api/groups                  (createGroup)           │
│  ├─ GET    /api/groups                  (listGroups)            │
│  ├─ GET    /api/groups/{id}             (getGroup)              │
│  ├─ POST   /api/groups/{id}/participants    (addParticipant)    │
│  ├─ DELETE /api/groups/{id}/participants/{agent} (remove)       │
│  ├─ GET    /api/groups/{id}/messages    (getMessages)           │
│  ├─ POST   /api/groups/{id}/messages    (sendMessage)           │
│  └─ POST   /api/groups/{id}/tasks       (assignTask)            │
│                                                                   │
│  [MISSING in Phase 82]:                                          │
│  ├─ PATCH  /api/groups/{id}             (updateGroup)           │
│  └─ PATCH  /api/groups/{id}/participants/{agent} (updatePart)   │
│                                                                   │
│      ↓                                                            │
│                                                                   │
│  GroupChatManager (group_chat_manager.py - SINGLETON)            │
│  ├─ _groups: Dict[group_id → Group]                             │
│  ├─ _agent_groups: Dict[agent_id → [group_ids]]                 │
│  │                                                               │
│  ├─ Group (Dataclass)                                           │
│  │   ├─ id: UUID                                                │
│  │   ├─ name: str                                               │
│  │   ├─ description: str                                        │
│  │   ├─ admin_id: str (@PM, @architect, etc.)                  │
│  │   ├─ participants: Dict[agent_id → GroupParticipant]         │
│  │   │   └─ GroupParticipant                                    │
│  │   │       ├─ agent_id: "@architect"                          │
│  │   │       ├─ model_id: "llama-405b"                          │
│  │   │       ├─ role: ADMIN|WORKER|REVIEWER|OBSERVER            │
│  │   │       ├─ display_name: "Architect (Llama)"               │
│  │   │       └─ permissions: ["read", "write"]                  │
│  │   ├─ messages: deque[GroupMessage] (max 1000)                │
│  │   │   └─ GroupMessage                                        │
│  │   │       ├─ id: UUID                                        │
│  │   │       ├─ sender_id: "@PM" | "user"                       │
│  │   │       ├─ content: str                                    │
│  │   │       ├─ mentions: ["@Dev", "@QA"]                       │
│  │   │       ├─ message_type: "chat" | "task" | "system"        │
│  │   │       └─ metadata: {}                                    │
│  │   ├─ shared_context: Dict[key → value]                       │
│  │   ├─ project_id: Optional[str]                               │
│  │   ├─ created_at: datetime                                    │
│  │   └─ last_activity: datetime                                 │
│  │                                                               │
│  ├─ Methods:                                                     │
│  │   ├─ create_group() → Group                                  │
│  │   ├─ add_participant(group_id, participant) → bool           │
│  │   ├─ remove_participant(group_id, agent_id) → bool           │
│  │   ├─ send_message(group_id, content) → GroupMessage          │
│  │   ├─ select_responding_agents(content, participants)         │
│  │   │   └─ Routes to agents based on:                          │
│  │   │       1. Reply routing (if replying to agent)            │
│  │   │       2. @mentions (explicit)                            │
│  │   │       3. /solo, /team, /round commands                   │
│  │   │       4. SMART keyword matching                          │
│  │   │       5. Default: first available                        │
│  │   │                                                           │
│  │   ├─ assign_task() → Task                                    │
│  │   ├─ get_group(group_id) → dict                              │
│  │   ├─ get_messages(group_id) → [GroupMessage]                 │
│  │   └─ save_to_json() / load_from_json()                       │
│  │                                                               │
│  └─ Persistence: data/groups.json (auto-saved)                  │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

## State Flow Diagram

```
CREATE GROUP
    │
    ├─ GroupCreatorPanel
    │   ├─ Input: Group name
    │   └─ Input: Agent slots + models
    │
    └─ handleCreateGroup()
        │
        ├─ POST /api/groups
        │   └─ Response: {group_id, group}
        │
        ├─ POST /api/groups/{id}/participants (for each agent)
        │   └─ Response: {success: true}
        │
        ├─ setActiveGroupId(groupId)
        │
        ├─ Switch to 'chat' tab
        │
        └─ setCurrentChatInfo({
            contextType: 'group',
            displayName: groupName,
            id: chatId
        })
            │
            └─ RENDER: Group Header with Leave button
                │
                ├─ User sends message → sendGroupMessage()
                │   ├─ POST /api/groups/{id}/messages
                │   └─ Message broadcast via Socket.IO
                │
                └─ [STUCK] Cannot edit!
                    └─ No Settings button
                    └─ No way to reload editor
                    └─ Can only Leave

DESIRED PHASE 82 FLOW:
    │
    └─ Group Header with Settings button
        │
        ├─ Click Settings
        │   │
        │   └─ GroupEditorPanel modal opens
        │       ├─ Show: Group name, description
        │       ├─ Show: Participants with roles/models
        │       ├─ Allow: Change name, description
        │       ├─ Allow: Change participant model
        │       ├─ Allow: Change participant role
        │       ├─ Allow: Remove participant
        │       ├─ Allow: Add new participant
        │       └─ Save button
        │           │
        │           ├─ PATCH /api/groups/{id} (name, desc)
        │           ├─ PATCH /api/groups/{id}/participants/{agent} (model, role)
        │           └─ PATCH /api/groups/{id}/participants/{agent} (remove)
        │               │
        │               └─ Update UI with new state
        │
        └─ Continue chatting with updated group
```

## Component Hierarchy

```
App.tsx
└─ ChatPanel
    ├─ Left Sidebar (mutually exclusive)
    │   ├─ ChatSidebar (if leftPanel='history')
    │   │   └─ Shows: All chats including groups
    │   └─ ModelDirectory (if leftPanel='models')
    │       └─ Shows: Available models for selection
    │
    ├─ Chat Container
    │   ├─ Header
    │   │   ├─ AI-Chat toggle button
    │   │   ├─ History button
    │   │   ├─ Model Directory button
    │   │   ├─ Scanner button
    │   │   └─ Close button
    │   │
    │   ├─ Chat name header (if contextType='group')
    │   │   ├─ Group icon
    │   │   ├─ Group name (editable)
    │   │   └─ Edit icon
    │   │
    │   ├─ UnifiedSearchBar
    │   │   └─ Search files/code
    │   │
    │   ├─ Pinned Context
    │   │   └─ Show: Pinned files for context
    │   │
    │   ├─ Tab Content
    │   │   ├─ If activeTab='chat' + activeGroupId
    │   │   │   ├─ GROUP HEADER ← PHASE 82 TARGET
    │   │   │   │   ├─ Status indicator
    │   │   │   │   ├─ [NEW] Settings button
    │   │   │   │   └─ Leave button
    │   │   │   │       │
    │   │   │   │       └─ When clicked:
    │   │   │   │           ├─ leaveGroup(groupId)
    │   │   │   │           ├─ setActiveGroupId(null)
    │   │   │   │           └─ clearChat()
    │   │   │   │
    │   │   │   ├─ MessageList
    │   │   │   │   └─ Show: chat messages with @mentions
    │   │   │   │
    │   │   │   └─ MessageInput
    │   │   │       ├─ Text input with @mention detection
    │   │   │       ├─ MentionPopup
    │   │   │       │   └─ Filter: Group participants
    │   │   │       └─ Send button
    │   │   │
    │   │   ├─ If activeTab='group'
    │   │   │   └─ GroupCreatorPanel
    │   │   │       └─ [FUTURE] Reuse as GroupEditorPanel?
    │   │   │
    │   │   └─ If activeTab='scanner'
    │   │       └─ ScannerPanel
    │   │
    │   ├─ Reply Indicator (if replyTo)
    │   │   ├─ Show: agent name
    │   │   ├─ Show: quoted message
    │   │   └─ Clear button
    │   │
    │   └─ MessageInput (bottom)
    │
    └─ [NEW - Phase 82]
        └─ GroupEditorPanel Modal
            ├─ Backdrop (click to close)
            └─ Modal Content
                ├─ Title: "Edit Group"
                ├─ Group name input
                ├─ Group description input
                ├─ Participant list
                │   └─ For each participant:
                │       ├─ Agent display name
                │       ├─ Model dropdown (change model)
                │       ├─ Role dropdown (change role)
                │       └─ Remove button
                ├─ Add participant button
                │   └─ Opens: Select role + model
                ├─ Cancel button
                └─ Save button → PATCH API
```

## Data Flow: Group Creation to Editing

```
FRONTEND                          BACKEND                       STORAGE
─────────────────────────────────────────────────────────────────────
User Input (GroupCreatorPanel)
    │
    ├─ name: "Code Review"
    ├─ agents: [
    │   {role: "PM", model: "gpt-4"},
    │   {role: "Dev", model: "claude-3"},
    │   {role: "QA", model: "llama-405b"}
    └─ ]
         │
         └─ handleCreateGroup()
             │
             ├─ POST /api/groups
             │   │
             │   └─ Router: create_group(CreateGroupRequest)
             │       │
             │       └─ GroupChatManager.create_group()
             │           │
             │           ├─ Generate group_id (UUID)
             │           ├─ Create Group object
             │           ├─ Add admin participant (PM)
             │           ├─ Store in self._groups
             │           ├─ emit('group_created')
             │           └─ save_to_json()
             │               └─ data/groups.json ← PERSISTED
             │                   {
             │                     "groups": {
             │                       "uuid-123": {
             │                         "id": "uuid-123",
             │                         "name": "Code Review",
             │                         "participants": {...},
             │                         "messages": [],
             │                         "created_at": "2026-01-21T...",
             │                         "last_activity": "2026-01-21T..."
             │                       }
             │                     }
             │                   }
             │
             ├─ POST /api/groups/{id}/participants (×2)
             │   │
             │   ├─ Add Dev agent
             │   ├─ Add QA agent
             │   └─ save_to_json() after each
             │
             ├─ setActiveGroupId("uuid-123")
             ├─ setCurrentChatInfo({contextType: 'group', ...})
             ├─ Switch to 'chat' tab
             │
             └─ RENDER: Group Header
                 ├─ Text: "Group Active | Use @role"
                 ├─ Button: Leave
                 └─ [PHASE 82] Button: Settings ← NEW!


─────────────────────────────────────────────────────────────────────
[PHASE 82 - NEW FLOW]

User clicks Settings button
    │
    └─ Show GroupEditorPanel Modal
        │
        ├─ Load current group state
        │   └─ GET /api/groups/{id} (if not cached)
        │
        ├─ User changes: name, description, participants
        │
        ├─ Save button
        │   │
        │   ├─ PATCH /api/groups/{id}
        │   │   {name: "New Name", description: "..."}
        │   │   │
        │   │   └─ Router: update_group()
        │   │       └─ GroupChatManager.update_group()
        │   │           ├─ Update group.name
        │   │           ├─ Update group.description
        │   │           ├─ Save to JSON
        │   │           └─ emit('group_updated')
        │   │               └─ data/groups.json ← UPDATED
        │   │
        │   ├─ PATCH /api/groups/{id}/participants/{agent_id}
        │   │   {model_id: "new-model", role: "admin"}
        │   │   │
        │   │   └─ Router: update_participant()
        │   │       └─ GroupChatManager.update_participant()
        │   │           ├─ Update participant.model_id
        │   │           ├─ Update participant.role
        │   │           ├─ Save to JSON
        │   │           └─ emit('participant_updated')
        │   │
        │   └─ Close modal
        │       └─ Refresh chatMessages (reload from /api/groups/{id}/messages)
        │
        └─ Continue chatting with updated group
```

## Socket.IO Real-Time Events

```
GROUP CREATION/EDITING LIFECYCLE
──────────────────────────────────

Server Events (what client listens for):

When group created:
    window.dispatchEvent(new CustomEvent('group-created', {
        detail: {group_id, group_data}
    }))

When participant added:
    window.dispatchEvent(new CustomEvent('group-joined', {
        detail: {group_id, participant}
    }))

When message received:
    window.dispatchEvent(new CustomEvent('group-message', {
        detail: {group_id, id, sender_id, content, created_at}
    }))

When agent starts responding:
    window.dispatchEvent(new CustomEvent('group-stream-start', {
        detail: {group_id, id, agent_id, model}
    }))

When token received (streaming):
    window.dispatchEvent(new CustomEvent('group-stream-token', {
        detail: {group_id, id, token}
    }))

When agent finishes:
    window.dispatchEvent(new CustomEvent('group-stream-end', {
        detail: {group_id, id, agent_id, full_message}
    }))

[PHASE 82 NEW]:
When group updated:
    window.dispatchEvent(new CustomEvent('group-updated', {
        detail: {group_id, updated_fields: {name, description}}
    }))

When participant updated:
    window.dispatchEvent(new CustomEvent('participant-updated', {
        detail: {group_id, agent_id, updated_fields: {model_id, role}}
    }))

When participant removed:
    window.dispatchEvent(new CustomEvent('participant-removed', {
        detail: {group_id, agent_id}
    }))
```

## Command vs Mention System

```
@ MENTIONS (for targeting)
─────────────────────────
Syntax: @role or @agent_id
Example: @PM please review, @architect design review
Parsed by: parse_mentions() → List[agent_id]
Stored in: message.mentions
Used for: Explicit agent routing
Model: Agent selection via mention matching

/ COMMANDS (for behavior)
─────────────────────────
Syntax: /command message
Examples:
  - /solo Just one agent
  - /team Everyone respond
  - /round Roundtable (ordered)
Parsed by: select_responding_agents() via regex
NOT stored in message
Used for: Group interaction patterns
Model: Select multiple agents based on mode

EXAMPLE MESSAGE: "@PM /solo Please review code"
├─ @ Parse: mentions = ["PM"]
├─ / Parse: mode = "solo"
└─ Result: PM selected once, all others excluded


MENTION DETECTION IN UI
──────────────────────

MessageInput.tsx watches for @ character:

    "@" typed
        │
        └─ MentionPopup shows
            ├─ Filter by input text
            ├─ Show: Group participants
            │   ├─ @PM (Architect - GPT-4)
            │   ├─ @Dev (Dev - Claude-3)
            │   └─ @QA (QA - Llama-405b)
            │
            ├─ User types: "@P"
            │   └─ Filter: Only "PM" matches
            │
            └─ User clicks: @PM
                └─ Replace "@P" with "@PM"
                    └─ Continue typing

Send message "@PM please fix":
    ├─ Parse mentions: ["PM"]
    ├─ Parse /commands: none
    └─ Route to: PM only (default behavior)
```

## Persistence Layer

```
MEMORY (RAM)
─────────────────────────
GroupChatManager
├─ _groups: Dict[group_id → Group]
│   └─ Max 100 groups (LRU eviction)
│   └─ Timeout: 24 hours inactive = remove
│
├─ _messages: Per-group deque
│   └─ Max 1000 messages per group
│
└─ _agent_groups: Dict[agent_id → [group_ids]]


DISK (Persistent)
─────────────────────────
data/groups.json
└─ Auto-saved after:
    ├─ create_group()
    ├─ add_participant()
    ├─ send_message()
    ├─ remove_participant()
    └─ [PHASE 82] update_group()
    └─ [PHASE 82] update_participant()

Format:
{
  "groups": {
    "group-id-1": {
      "id": "...",
      "name": "...",
      "participants": {...},
      "messages": [...],
      "created_at": "...",
      "last_activity": "..."
    }
  },
  "saved_at": "2026-01-21T..."
}


CHAT HISTORY (Database)
─────────────────────────
/api/chats
├─ Stores: Display name, context_type, group_id link
├─ Used for: Sidebar chat history
└─ Groups appear as chat entries
    └─ Can be reopened to load messages
    └─ [PHASE 82] Now also editable!
```

---

**This diagram shows the complete architecture needed to understand how group editing would integrate with the existing system.**
