# H17: GROUP CHAT HEADER IMPLEMENTATION MARKER

**Status:** COMPLETE
**Phase:** 96+
**Objective:** Understand group chat header creation and display for solo chat implementation
**Date:** 2026-01-29

---

## EXECUTIVE SUMMARY

Group chat headers work through a 3-stage pipeline:
1. **Creation** - Group name captured in `GroupCreatorPanel.tsx` input field
2. **Storage** - Name sent to backend via REST API `/api/groups` POST
3. **Display** - Name rendered in `ChatPanel.tsx` header with group context icons

This document captures the exact implementation for reuse in solo chat headers.

---

## STAGE 1: GROUP NAME INPUT (Frontend)

### File: `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/client/src/components/chat/GroupCreatorPanel.tsx`

**State Management:**
```typescript
const [groupName, setGroupName] = useState('');  // Line 122
```

**UI Input Field (Lines 410-443):**
```typescript
<div style={{ marginBottom: 16 }}>
  <div style={{ fontSize: 10, color: '#666', ... }}>
    Group Name
  </div>
  <input
    type="text"
    value={groupName}
    onChange={(e) => setGroupName(e.target.value)}
    placeholder="e.g., Code Review Team"
    style={{
      width: '100%',
      padding: '10px 12px',
      background: '#111',
      border: '1px solid #333',
      borderRadius: 4,
      color: '#ccc',
      fontSize: 13,
      ...
    }}
    onFocus={(e) => { e.currentTarget.style.borderColor = '#555'; }}
    onBlur={(e) => { e.currentTarget.style.borderColor = '#333'; }}
  />
</div>
```

**Key Styling Details:**
- Label: fontSize 10, uppercase, letterSpacing 0.5px, color #666
- Input: fontSize 13, padding 10px 12px, background #111, border #333
- Focus state: border changes to #555 (brighter)
- Placeholder text: "e.g., Code Review Team"

**Handler (Lines 282-290):**
```typescript
const handleCreate = () => {
  if (canCreate) {
    onCreateGroup(groupName, filledAgents);  // Pass name to parent
    setGroupName('');  // Reset form
    setAgents(DEFAULT_ROLES.map(role => ({ role, model: null })));
    setActiveSlot(null);
  }
};
```

---

## STAGE 2: GROUP NAME STORAGE (Backend/API)

### File: `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/api/routes/group_routes.py`

**Create Group Endpoint (Lines 70-89):**
```python
@router.post("")
async def create_group(body: CreateGroupRequest):
    """Create new group."""
    manager = get_group_chat_manager()

    admin = GroupParticipant(...)

    group = await manager.create_group(
        name=body.name,  # Group name stored here
        admin_agent=admin,
        description=body.description,
        project_id=body.project_id
    )

    return {'group': group.to_dict()}
```

**Request Model (Lines 26-32):**
```python
class CreateGroupRequest(BaseModel):
    name: str                    # Group name (required)
    description: str = ""        # Group description (optional)
    admin_agent_id: str          # Admin agent ID
    admin_model_id: str          # Admin model ID
    admin_display_name: str      # Admin display name
    project_id: Optional[str] = None
```

**Frontend API Call (ChatPanel.tsx, Lines 543-552):**
```typescript
const createResponse = await fetch('/api/groups', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    name,  // Group name from input
    description: `Group chat with ${validAgents.length} agents`,
    admin_agent_id: `@${firstAgent.role}`,
    admin_model_id: firstAgent.model,
    admin_display_name: getDisplayName(firstAgent.role, firstAgent.model!)
  })
});
```

---

## STAGE 3: GROUP HEADER DISPLAY (Frontend)

### File: `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/client/src/components/chat/ChatPanel.tsx`

**Chat Info State (Lines 90-95):**
```typescript
const [currentChatInfo, setCurrentChatInfo] = useState<{
  id: string;
  displayName: string | null;
  fileName: string;
  contextType: string;
} | null>(null);
```

**State Initialization After Group Creation (Lines 626-631):**
```typescript
setCurrentChatInfo({
  id: chatData.chat_id,
  displayName: name,           // Group name from creation
  fileName: 'unknown',
  contextType: 'group'         // Mark as group context
});
```

**Header Rendering (Lines 1869-1957):**

The header displays when:
```typescript
{(activeTab === 'chat' || activeTab === 'group') && currentChatInfo &&
 !(currentChatInfo.contextType === 'file' && pinnedFileIds.length > 0) && (
  <div style={{
    padding: '6px 12px',
    background: '#0f0f0f',
    borderBottom: '1px solid #222',
  }}>
    <div
      onClick={handleRenameChatFromHeader}
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: 6,
        padding: '4px 10px',
        background: '#1a1a1a',
        border: '1px solid #333',
        borderRadius: 4,
        fontSize: 12,
        color: '#aaa',
        cursor: 'pointer',
        ...
      }}
    >
      {/* Context-type icon */}
      {currentChatInfo.contextType === 'group' ? (
        <svg width="12" height="12" ...>
          {/* Two-person icon for group */}
          <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/>
          <circle cx="9" cy="7" r="4"/>
          <path d="M23 21v-2a4 4 0 0 0-3-3.87"/>
          <path d="M16 3.13a4 4 0 0 1 0 7.75"/>
        </svg>
      ) : ...}

      {/* Chat name - displays displayName or fileName */}
      <span style={{ fontWeight: 500 }}>
        {currentChatInfo.displayName || currentChatInfo.fileName}
      </span>

      {/* Edit icon */}
      <svg width="10" height="10" ...>
        {/* Pencil icon */}
      </svg>

      {/* Close/clear icon */}
      <svg width="10" height="10" ...>
        {/* X icon */}
      </svg>
    </div>
  </div>
)}
```

**Header Position in Layout:**
1. **Top:** Below the toolbar buttons (Chat/History/Models/Scanner)
2. **Middle:** Above the UnifiedSearchBar (lines 1846-1867)
3. **Order:** Always renders after search bar, before pinned context (line 1960+)

**Header Container Styling:**
- Outer: padding 6px 12px, background #0f0f0f, borderBottom 1px solid #222
- Inner button: padding 4px 10px, background #1a1a1a, border 1px solid #333, borderRadius 4
- Text: fontSize 12, color #aaa, fontWeight 500
- Gap between icon/name/buttons: 6px

**Interactive Features:**
- **Click to Rename:** `onClick={handleRenameChatFromHeader}` (line 1879)
  - Triggers prompt for new name
  - Updates via `/api/chats/{chat_id}` PATCH endpoint
  - Only works if name differs from current
- **Close Icon:** Clears currentChatInfo and currentChatId (lines 1936-1948)
- **Hover State:** Changes border and background on hover (lines 1893-1900)

---

## DATA FLOW DIAGRAM

```
GroupCreatorPanel
    ↓
[User enters "Code Review Team" in input]
    ↓
handleCreate() called
    ↓
onCreateGroup(groupName, agents)
    ↓
ChatPanel.handleCreateGroup()
    ↓
POST /api/groups {name, description, admin_*}
    ↓
Backend creates group
    ↓
Response: {group: {id, name, ...}}
    ↓
setCurrentChatInfo({
  displayName: name,
  contextType: 'group'
})
    ↓
Header renders:
  [group icon] Code Review Team [edit] [x]
```

---

## KEY IMPLEMENTATION DETAILS FOR SOLO CHAT

### What Groups DO:
1. ✓ Capture name in text input field
2. ✓ Store name in API with metadata (contextType='group')
3. ✓ Display in standardized header format
4. ✓ Support rename via click
5. ✓ Show context icon (group icon for groups)
6. ✓ Allow close/clear header

### What We Need for Solo Chat:
1. Create similar input field in solo chat creation (or chat init)
2. Store with contextType='solo' or contextType='chat'
3. Use same header rendering logic
4. Show chat/single-file icon instead of group icon
5. Support rename same way
6. Reuse header container and styling

### Code Reuse Opportunities:
- **Icon Selection Logic:** Move icon selection to utility function
  - Current: Lines 1904-1922 in ChatPanel.tsx (if/else for contextType)
  - Proposal: Create `getContextIcon(contextType)` utility
- **Header Styling:** Extract to constant object
  - Used for both groups and solo chats
  - Defines: padding, background, border, fontSize, etc.
- **Rename Handler:** Already generic `handleRenameChatFromHeader()`
  - Uses `currentChatInfo.id` and `currentChatInfo.displayName`
  - Will work for solo chats once currentChatInfo is populated

---

## STORAGE SCHEMA

**Group Object Structure (returned from API):**
```json
{
  "id": "group_uuid",
  "name": "Code Review Team",
  "description": "Group chat with 4 agents",
  "admin_id": "@PM",
  "participants": {
    "@PM": {
      "agent_id": "@PM",
      "model_id": "openai/gpt-4",
      "display_name": "PM (GPT-4)",
      "role": "admin"
    },
    "@Dev": {
      "agent_id": "@Dev",
      "model_id": "deepseek/deepseek-r1:free",
      "display_name": "Dev (Deepseek R1)",
      "role": "worker"
    }
    ...
  }
}
```

**Chat History Entry (saved for both solo and group):**
```typescript
POST /api/chats {
  display_name: "Code Review Team",      // Group name or solo file name
  context_type: "group",                 // 'group', 'file', 'folder', 'topic'
  items: ["@PM", "@Dev", "@QA"],        // Agents for groups, files for file context
  group_id: "group_uuid"                // Optional: Link to GroupChatManager
}
```

---

## CURRENT LIMITATIONS & NOTES

1. **No Auto-Generated Names:** Groups require explicit name entry
   - Solo chats will need same: ask user for name or use file name as default
2. **Name Character Limit:** No validation in current code
   - Should add max length (e.g., 100 chars) for UI consistency
3. **Special Characters:** Not filtered - names can contain any UTF-8
   - May need sanitization for display
4. **Rename Persistence:** Uses prompt() then PATCH to API
   - Works but not modern UX - consider inline editing for phase 100+

---

## FILES TOUCHED

- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/client/src/components/chat/GroupCreatorPanel.tsx`
  - Lines 122, 410-443: Name input field
  - Lines 282-290: handleCreate()

- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/client/src/components/chat/ChatPanel.tsx`
  - Lines 90-95: currentChatInfo state
  - Lines 515-661: handleCreateGroup() full flow
  - Lines 1869-1957: Header rendering with group name display
  - Lines 1904-1922: Icon selection by contextType

- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/api/routes/group_routes.py`
  - Lines 26-32: CreateGroupRequest model
  - Lines 70-89: create_group() endpoint

---

## READY FOR SOLO CHAT IMPLEMENTATION

This marker provides the complete pattern for solo chat headers. The next phase can:
1. Extract header rendering to shared component
2. Create solo chat creation UI (copy GroupCreatorPanel pattern)
3. Populate currentChatInfo with solo context
4. Test rename/close functionality
5. Ensure icon display works for all contextTypes
