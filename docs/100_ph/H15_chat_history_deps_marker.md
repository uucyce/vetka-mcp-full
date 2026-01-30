# H15: Chat History Dependencies Marker Report

**Objective:** Comprehensive mapping of all dependencies on chat header/title (`display_name`/`displayName`) across the VETKA codebase.

**Status:** Complete
**Date:** 2026-01-29
**Phase:** 100.2 (Persistent pinned files + display_name integration)

---

## Executive Summary

The `display_name` field is a core feature of the chat system introduced in Phase 74. It provides custom naming for chats independent of file paths. This report documents:

- **68 dependency references** across 16 files
- **Backend**: 7 files (Python) - storage, API, handlers
- **Frontend**: 9 files (TypeScript/TSX) - UI, state management, components
- **Data Storage**: 1 file (JSON) - persistent chat history

---

## 1. Backend Dependencies (Python)

### 1.1 Core Storage Layer

#### `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/chat/chat_history_manager.py`
**Status:** Primary implementation | **Phase:** 74, 74.10

| Line | Function/Method | Purpose | Operation |
|------|-----------------|---------|-----------|
| 75 | `get_or_create_chat()` | Parameter definition | Input parameter for custom chat naming |
| 81 | `get_or_create_chat()` docstring | Schema documentation | Phase 74 extended schema mention |
| 88 | `get_or_create_chat()` docstring | Parameter docs | Describes display_name parameter |
| 114-128 | `get_or_create_chat()` | Search logic | Phase 74.9: Find chat by display_name for null-context chats |
| 117 | `get_or_create_chat()` | Normalization | Phase 74.10: Strip whitespace to prevent duplicates |
| 119-121 | `get_or_create_chat()` | Comparison | Stored name normalization for matching |
| 137 | `get_or_create_chat()` | Null-context logic | Check if chat has been renamed (display_name exists) |
| 186-187 | `get_or_create_chat()` | Sanitization | Phase 74.10: Strip display_name before storage |
| 193 | `get_or_create_chat()` | Storage | Save cleaned display_name to chat object |
| 204 | `get_or_create_chat()` | Logging | Log creation with display_name |
| 306 | `rename_chat()` docstring | Documentation | Method to set display_name |
| 318 | `rename_chat()` | Update | Set display_name field to new_name |

**Key behavior:**
- Normalizes display_name by stripping whitespace (Phase 74.10)
- Searches existing chats by display_name for null-context scenarios
- Stores display_name as optional field in chat object

---

### 1.2 API Routes Layer

#### `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/api/routes/chat_history_routes.py`
**Status:** Active | **Phase:** 50, 74, 74.3, 74.8, 100.2

| Line | Endpoint | Purpose | Operation |
|------|----------|---------|-----------|
| 46 | `ChatResponse` model | Type definition | Optional display_name field |
| 87 | `GET /api/chats` | List response | Include display_name in chat list |
| 138 | `GET /api/chats/{chat_id}` | Single chat response | Return display_name field |
| 222 | `RenameRequest` model | Request schema | Pydantic model for display_name |
| 225-259 | `PATCH /api/chats/{chat_id}` | Rename endpoint | Update chat display_name |
| 240 | `PATCH` validation | Input validation | Check display_name not empty/None |
| 244 | `PATCH` update | Call manager | manager.rename_chat() |
| 252 | `PATCH` response | Response payload | Return updated display_name |
| 391 | `CreateChatRequest` model | Request schema | display_name required for creation |
| 412-413 | `POST /api/chats` | Input validation | Check display_name not empty |
| 417-423 | `POST /api/chats` | Chat creation | Pass display_name to get_or_create_chat() |
| 426-429 | `POST /api/chats` | Fallback logic | If chat was reused without name, set it now |
| 443 | `POST` response | Response payload | Return display_name in response |

**Key endpoints:**
- `GET /api/chats` - Returns all chats with display_name
- `GET /api/chats/{chat_id}` - Single chat includes display_name
- `PATCH /api/chats/{chat_id}` - Rename chat (update display_name)
- `POST /api/chats` - Create named chat with display_name

---

#### `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/api/routes/group_routes.py`
**Status:** Active | **Phase:** 56, 80.19

| Line | Context | Purpose | Operation |
|------|---------|---------|-----------|
| 31 | `CreateGroupRequest` model | Participant naming | admin_display_name field |
| 38 | `AddParticipantRequest` model | Participant naming | display_name field for workers |
| 79 | `POST /api/groups` | Admin setup | Create admin with display_name |
| 113 | `POST /api/groups/{group_id}/participants` | Worker addition | Create participant with display_name |
| 260 | `POST /api/groups/{group_id}/direct-add` | Model name derivation | Generate display_name from model_id |
| 267 | `POST /api/groups/{group_id}/direct-add` | Participant creation | Add participant with generated display_name |

**Key distinction:** Group participants also use display_name for agent identification.

---

### 1.3 Event Handlers

#### `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/api/handlers/group_message_handler.py`
**Status:** Active | **Phase:** 56, 74, 80.7, 80.28

| Line | Function | Purpose | Operation |
|------|----------|---------|-----------|
| 243 | Message handler | Parse participants | Extract display_name from group participants |
| 639 | Chat creation | Group chat naming | Pass group_name to display_name |
| 733 | Agent routing | Get participant name | Extract display_name for agent identification |
| 753 | Agent type mapping | Route by type | Use display_name to map to agent type |
| 860 | Agent response storage | Track output | Store by display_name key |
| 882 | Context building | Previous outputs | Map display_name -> response |
| 931 | Chat message creation | Context | Pass display_name as agent metadata |
| 938 | Message composition | Agent attribution | Set agent field to display_name |
| 954 | Mention detection | Logging | Log agent mentions with display_name |
| 959 | Mention matching | String comparison | Match mentioned_name against display_name |
| 967-979 | Mention resolution | Three-tier strategy | Match by: exact display_name, agent_id, display_name prefix |

**Critical behavior:**
- Multi-strategy agent mention resolution (lines 967-979)
- Strategies:
  1. Exact `display_name` match (case-insensitive)
  2. `agent_id` match (`@architect`)
  3. `display_name` prefix before parentheses (for "PM (GPT-4o)" format)

---

#### `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/api/handlers/key_handlers.py`
**Status:** Active | **Phase:** 81

| Line | Context | Purpose | Operation |
|------|---------|---------|-----------|
| 87 | Key detection response | API provider naming | Get display_name from detector |
| 89 | Success message | User feedback | Include display_name in toast message |
| 155 | Direct key addition | Fallback naming | Generate display_name from provider |

---

#### `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/api/routes/debug_routes.py`
**Status:** Active | **Phase:** 80, 100

| Line | Context | Purpose | Operation |
|------|---------|---------|-----------|
| 1121 | MCP debug endpoint | Participant info | Include display_name in response |
| 1282-1294 | Agent trigger | Name mapping | Get display_name and map to agent type |
| 1357 | Agent response | Metadata | Store with display_name |
| 1375 | Context cache | Previous outputs | Map by display_name |
| 1414-1425 | Mention resolution | Detection | Three-strategy matching (same as group handler) |

---

#### `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/services/group_chat_manager.py`
**Status:** Active | **Phase:** 56, 80.7, 80.28

| Line | Method/Function | Purpose | Operation |
|------|-----------------|---------|-----------|
| 51 | `GroupParticipant` dataclass | Field definition | display_name: str attribute |
| 59 | `to_dict()` | Serialization | Include display_name in dict |
| 223 | `select_agents()` | Reply routing | Log selection by display_name |
| 244 | `select_agents()` | Mention matching | Extract display_name for comparison |
| 267 | `select_agents()` | Logging | Log selected agents by display_name |
| 284, 301, 310, 320, 330-331, 355, 371 | `select_agents()` | Various routing modes | Use display_name in: @mention, /solo, /team, /round, smart selection, default |
| 694 | `broadcast_to_agents()` | Message composition | Include agent display_name in message |
| 900 | `load_from_file()` | Persistence | Reconstruct GroupParticipant with display_name |

**Key feature:** Smart agent selection (Phase 80.28) uses display_name across 8 different routing strategies.

---

### 1.4 Key Handler & Config Routes

#### `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/api/routes/config_routes.py`
**Status:** Active | **Phase:** 81

| Line | Context | Purpose | Operation |
|------|---------|---------|-----------|
| 373 | API key detection | Provider naming | Get display_name from detector |
| 446 | API key detection | Provider naming | Get display_name from detector |
| 448 | Success message | User feedback | Include display_name in response |

---

#### `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/api/routes/health_routes.py`
**Status:** Active | **Phase:** 50

| Line | Context | Purpose | Operation |
|------|---------|---------|-----------|
| 45-52 | System health check | Component naming | Variable display_name for component names |
| 79, 91 | Component status | Logging | Use display_name in status output |

---

## 2. Frontend Dependencies (TypeScript/React)

### 2.1 Chat Management Components

#### `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/client/src/components/chat/ChatPanel.tsx`
**Status:** Active | **Phase:** 50, 74, 80.8, 100.2

| Line | Component/Function | Purpose | Operation |
|------|-------------------|---------|-----------|
| 92 | `currentChatInfo` state | Type definition | displayName: string \| null field |
| 130 | Participant interface | Type definition | display_name: string field |
| 417, 446 | Group creation | Participant payload | Include display_name in request |
| 534 | Comment | Display info | Phase 80.8: Include model name in display_name |
| 551 | Group creation | Admin setup | admin_display_name parameter |
| 573 | Group creation | Worker addition | getDisplayName() generates display_name with model |
| 616 | Chat rename | Payload | display_name: name |
| 628 | Chat creation | State update | displayName: name |
| 794 | Display logic | Fallback | currentChatInfo.displayName \|\| currentChatInfo.fileName |
| 805 | API request | Rename endpoint | PATCH /api/chats with {display_name} |
| 809 | State update | Local sync | Update displayName after API call |
| 840 | Chat load | Response parsing | Map API display_name to state displayName |
| 1316 | Toast message | Feedback | Show "Added {participant.display_name}..." |
| 1329 | Group data | Participant list | Include display_name |
| 1926 | Chat header | Render | Display currentChatInfo.displayName or fileName |

**Key functions:**
- `getDisplayName()` generates "Role (Model)" format (line 573)
- State includes both displayName and fileName for fallback rendering
- Updates both local state and backend on rename

---

#### `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/client/src/components/chat/ChatSidebar.tsx`
**Status:** Active | **Phase:** 50, 74

| Line | Function | Purpose | Operation |
|------|----------|---------|-----------|
| 25 | `Chat` interface | Type definition | display_name?: string field |
| 128 | Rename handler | Display logic | currentName = chat.display_name \|\| chat.file_name |
| 139 | API request | Rename | PATCH with {display_name} |
| 145 | State update | Array map | Update chat.display_name in list |
| 234 | Render | Chat item text | Show {chat.display_name \|\| chat.file_name} |

**Key feature:** Sidebar shows custom chat names with file_name fallback.

---

#### `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/client/src/components/chat/GroupCreatorPanel.tsx`
**Status:** Active | **Phase:** 56, 80.8

| Line | Context | Purpose | Operation |
|------|---------|---------|-----------|
| 24 | `Participant` interface | Type definition | display_name: string field |

---

#### `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/client/src/components/chat/MessageInput.tsx`
**Status:** Active | **Phase:** 56

| Line | Context | Purpose | Operation |
|------|---------|---------|-----------|
| 20 | `Participant` interface | Type definition | display_name: string field |

---

#### `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/client/src/components/chat/MentionPopup.tsx`
**Status:** Active | **Phase:** 56, 80.8

| Line | Function | Purpose | Operation |
|------|----------|---------|-----------|
| 46 | `Participant` interface | Type definition | display_name: string (Role + Model format) |
| 139-140 | Filter logic | Search | Match against displayName lowercase |
| 144 | Mention list | Option label | Use p.display_name \|\| p.agent_id as label |

**Key feature:** Mention popup filters and displays participants by display_name.

---

### 2.2 Canvas & UI Components

#### `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/client/src/components/canvas/FileCard.tsx`
**Status:** Active | **Phase:** 50

| Line | Context | Purpose | Operation |
|------|---------|---------|-----------|
| 413-414 | Canvas rendering | Text truncation | Local displayName for file name truncation (NOT chat display_name) |

**Note:** This is a local variable for text truncation, not related to chat display_name.

---

#### `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/client/src/components/panels/RoleEditor.tsx`
**Status:** Active | **Phase:** 50

| Line | Context | Purpose | Operation |
|------|---------|---------|-----------|
| 27 | State | Form input | displayName state for custom role naming |
| 42-43 | Validation | Error handling | Validate displayName not empty |
| 61 | Form submit | Role creation | Pass displayName to addRole |
| 129, 132, 136-137 | Form UI | Input field | Render displayName input with validation |
| 213 | Submit button | Enable logic | Disable if !displayName |

**Note:** This is for custom roles, NOT chat display_name. Similar UI pattern.

---

#### `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/client/src/components/ModelDirectory.tsx`
**Status:** Active | **Phase:** 81

| Line | Context | Purpose | Operation |
|------|---------|---------|-----------|
| 140 | `KeyConfig` interface | Type definition | display_name: string for API provider |
| 346 | API key request | Payload | Include display_name |
| 379 | Toast message | User feedback | Show "{data.display_name} key added" |
| 966, 1015 | UI render | Labels | Show provider.display_name in buttons/headers |

**Note:** This is for API provider keys, NOT chat display_name.

---

### 2.3 State Management & Hooks

#### `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/client/src/store/roleStore.ts`
**Status:** Active | **Phase:** 50

| Line | Context | Purpose | Operation |
|------|---------|---------|-----------|
| 18 | `CustomRole` interface | Type definition | displayName: string for role UI name |

**Note:** This is for custom roles, NOT chat display_name.

---

#### `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/client/src/hooks/useSocket.ts`
**Status:** Active | **Phase:** 56, 80.8

| Line | Context | Purpose | Operation |
|------|---------|---------|-----------|
| 226 | `CreateGroupPayload` type | Parameter definition | display_name: string for admin |
| 232 | `AddParticipantPayload` type | Parameter definition | display_name: string for worker |

---

## 3. Data Storage Structure

### `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/data/chat_history.json`
**Status:** Persistent storage | **Phase:** 74, 100.2

**Structure:**
```json
{
  "chats": {
    "uuid-here": {
      "id": "uuid-here",
      "file_path": "/path/to/file",
      "file_name": "filename.ext",
      "display_name": "Custom Chat Name",  // OPTIONAL - Phase 74
      "context_type": "file|folder|group|topic",  // Phase 74
      "items": [],  // Group file list - Phase 74
      "topic": null,  // Topic name - Phase 74
      "pinned_file_ids": [],  // Phase 100.2
      "created_at": "ISO timestamp",
      "updated_at": "ISO timestamp",
      "messages": [...]
    }
  },
  "groups": {...}
}
```

**Key fields:**
- `display_name`: Optional string, custom name for chat
- Can be null for unnamed chats (uses file_name as fallback)
- Updated when user renames chat (PATCH /api/chats/{id})

---

## 4. Dependency Patterns

### 4.1 Write Operations (display_name Updates)

1. **Chat Creation** (Phase 74.8)
   - Frontend: `POST /api/chats` with `CreateChatRequest.display_name`
   - Backend: `ChatHistoryManager.get_or_create_chat(display_name=...)`
   - Storage: Persisted to `data/chat_history.json`

2. **Chat Rename** (Phase 74)
   - Frontend: `PATCH /api/chats/{chat_id}` with `RenameRequest.display_name`
   - Backend: `ChatHistoryManager.rename_chat(chat_id, new_name)`
   - Storage: Updated in JSON file

3. **Participant Addition** (Phase 56, 80.8)
   - Frontend: Group creator sends display_name for participants
   - Backend: Stored in `GroupParticipant.display_name`
   - No JSON persistence (loaded from group session)

### 4.2 Read Operations (display_name Usage)

1. **Chat List Display** (Phase 50, 74.3)
   - Frontend: `GET /api/chats` returns all chats
   - Display: `display_name || file_name` (fallback)

2. **Chat Header**
   - Frontend: Display current chat name in header (Phase 74.3)
   - Logic: `currentChatInfo.displayName || currentChatInfo.fileName`

3. **Agent Routing** (Phase 80.7, 80.28)
   - Group handler: Select agents by @mention
   - Matching: `display_name` vs mentioned text
   - Three strategies: exact match, agent_id, prefix match

4. **Mention Popup** (Phase 56, 80.8)
   - Frontend: Filter participants by `display_name`
   - Display: Show as mention option label

### 4.3 Data Flow

```
User Input (rename chat)
    ↓
Frontend: ChatPanel/ChatSidebar
    ↓
API: PATCH /api/chats/{chat_id}
    ↓
Backend: ChatHistoryManager.rename_chat()
    ↓
Persistence: data/chat_history.json
    ↓
Reload triggers: GET /api/chats
    ↓
Frontend state update: currentChatInfo.displayName
    ↓
UI render: Chat header + sidebar
```

---

## 5. Critical Dependencies & Change Impact

### 5.1 High-Impact Changes
**If display_name field is modified:**
- **Phase 74 chat system** breaks - no custom naming
- **Chat header** fallback logic fails if display_name removed
- **Agent routing** (Phase 80.7, 80.28) depends on display_name for @mention resolution
- **Group participant** naming system needs update

### 5.2 Dependent Phases
- **Phase 50**: Basic chat history (uses display_name)
- **Phase 56**: Group chat system (participant.display_name)
- **Phase 74**: Custom chat naming (primary use of display_name)
- **Phase 80.7/80.28**: Smart agent routing (@mention parsing)
- **Phase 100.2**: Persistent state (display_name included)

### 5.3 Deprecation Safety
1. Add new field for replacement (e.g., `title`)
2. Keep `display_name` as fallback for 2 phases
3. Update all read operations to prefer new field
4. Migrate data in ChatHistoryManager
5. Remove old field in final phase

---

## 6. Testing Recommendations

### 6.1 Unit Tests Needed
- [ ] `ChatHistoryManager.rename_chat()` - whitespace handling
- [ ] `ChatHistoryManager.get_or_create_chat()` - display_name matching logic
- [ ] Group mention resolution - three-strategy matching
- [ ] Display_name normalization - strip() edge cases

### 6.2 Integration Tests Needed
- [ ] Chat rename API: verify JSON persistence
- [ ] Group participant creation: verify display_name storage
- [ ] Agent mention routing: verify all three strategies work
- [ ] Fallback rendering: file_name used when display_name null

### 6.3 Edge Cases
- Rename to same name (idempotency)
- Rename with leading/trailing whitespace
- Rename to duplicate name (prevent or allow?)
- Delete chat with custom name
- Reload with custom name persistence

---

## 7. Summary Statistics

| Metric | Count |
|--------|-------|
| Total files | 16 |
| Backend files (Python) | 7 |
| Frontend files (TypeScript) | 9 |
| Total dependency references | 68+ |
| High-impact modifications | 3 (rename, creation, routing) |
| Phases involved | 7 (50, 56, 74, 80.7, 80.28, 81, 100.2) |

---

## 8. File Inventory

### Backend (Python)
1. `/src/chat/chat_history_manager.py` - 12 references (core logic)
2. `/src/api/routes/chat_history_routes.py` - 20 references (API)
3. `/src/api/routes/group_routes.py` - 6 references (groups)
4. `/src/api/handlers/group_message_handler.py` - 16 references (routing)
5. `/src/api/handlers/key_handlers.py` - 3 references (provider naming)
6. `/src/api/routes/debug_routes.py` - 11 references (debug)
7. `/src/services/group_chat_manager.py` - 22 references (agent selection)
8. `/src/api/routes/config_routes.py` - 3 references (config)
9. `/src/api/routes/health_routes.py` - 3 references (health check)

### Frontend (TypeScript)
1. `/client/src/components/chat/ChatPanel.tsx` - 16 references (main UI)
2. `/client/src/components/chat/ChatSidebar.tsx` - 5 references (sidebar)
3. `/client/src/components/chat/GroupCreatorPanel.tsx` - 1 reference (types)
4. `/client/src/components/chat/MessageInput.tsx` - 1 reference (types)
5. `/client/src/components/chat/MentionPopup.tsx` - 4 references (mention UI)
6. `/client/src/components/canvas/FileCard.tsx` - 1 reference (NOT chat display_name)
7. `/client/src/components/panels/RoleEditor.tsx` - 6 references (NOT chat display_name)
8. `/client/src/components/ModelDirectory.tsx` - 4 references (NOT chat display_name)
9. `/client/src/store/roleStore.ts` - 1 reference (NOT chat display_name)
10. `/client/src/hooks/useSocket.ts` - 2 references (types)

### Data
1. `/data/chat_history.json` - Storage structure (display_name field)

---

## Conclusion

The `display_name` field is deeply integrated across the VETKA system, serving as:
1. **Chat identity** - Custom naming independent of file paths
2. **Agent identity** - Display name for group participants with model info
3. **Mention resolution** - Target for @mention routing with 3-tier strategy
4. **UI display** - Primary display in chat headers and sidebars

Any changes to this field require updates across **16 files** and careful attention to **3 read/write operations** and **7 involved phases**. Backward compatibility should be maintained for at least 2 phases if deprecation is needed.
