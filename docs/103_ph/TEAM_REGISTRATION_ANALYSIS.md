# Team Registration Analysis - Agent Numbering System

**Status:** Phase 103 - Research Complete
**Date:** 2026-01-31
**Objective:** Understand current agent registration flow and identify changes needed for dev1/dev2 numbering

---

## Current Registration Flow

### 1. Frontend: GroupCreatorPanel.tsx
**Location:** `/client/src/components/chat/GroupCreatorPanel.tsx`

**UI Setup:**
- **Default Roles:** `['PM', 'Architect', 'Dev', 'QA', 'Researcher']` (line 53)
- **IKEA-style slots:** Each role gets ONE slot with model assignment
- **Agent state:** `{ role: string, model: string | null, agent_id?: string }`

**Creation Flow:**
```tsx
// User fills slots:
const agents = [
  { role: 'PM', model: 'openai/gpt-4' },
  { role: 'Dev', model: 'deepseek/deepseek-r1' },
  { role: 'QA', model: 'anthropic/claude-3' }
]

// On "Create Group" click:
handleCreateGroup(groupName, agents)
```

### 2. ChatPanel.tsx - Group Creation Handler
**Location:** `/client/src/components/chat/ChatPanel.tsx:515`

**Key Logic:**
```tsx
const handleCreateGroup = async (name, agents) => {
  const firstAgent = validAgents[0];

  // Generate display_name with model info
  const getDisplayName = (role, model) => {
    // "openai/gpt-4o" -> "GPT-4o"
    const modelPart = model.split('/').pop();
    const shortName = modelPart.split(':')[0];
    const prettyModel = capitalize(shortName);
    return `${role} (${prettyModel})`; // ⚠️ PROBLEM: No numbering!
  };

  // Create admin (first agent)
  POST /api/groups {
    admin_agent_id: `@${firstAgent.role}`, // ⚠️ "@Dev" - не уникально!
    admin_model_id: firstAgent.model,
    admin_display_name: getDisplayName(...)
  }

  // Add remaining participants
  for (let i = 1; i < validAgents.length; i++) {
    POST /api/groups/{groupId}/participants {
      agent_id: `@${agent.role}`,    // ⚠️ "@Dev" - коллизия!
      model_id: agent.model,
      display_name: getDisplayName(...)
    }
  }
}
```

**PROBLEM 1:** `agent_id` is role-based (`@Dev`, `@PM`) - no auto-increment!

### 3. Backend: group_routes.py
**Location:** `/src/api/routes/group_routes.py:104`

**Participant Registration:**
```python
@router.post("/{group_id}/participants")
async def add_participant(group_id: str, body: AddParticipantRequest):
    participant = GroupParticipant(
        agent_id=body.agent_id,        # ⚠️ From frontend - "@Dev"
        model_id=body.model_id,
        role=GroupRole(body.role),     # "admin", "worker", etc.
        display_name=body.display_name  # "Dev (Deepseek R1)"
    )
    await manager.add_participant(group_id, participant)
```

**PROBLEM 2:** No uniqueness check - accepts duplicate `@Dev`!

### 4. GroupChatManager - Storage
**Location:** `/src/services/group_chat_manager.py:472`

**Data Structure:**
```python
@dataclass
class Group:
    participants: Dict[str, GroupParticipant]  # ⚠️ Key = agent_id
    # {"@PM": GroupParticipant(...), "@Dev": GroupParticipant(...)}

async def add_participant(self, group_id, participant):
    group.participants[participant.agent_id] = participant
    # ⚠️ OVERWRITES if agent_id already exists!
```

**PROBLEM 3:** Dict key collision - second `@Dev` replaces first!

---

## Data Structure

### GroupParticipant (group_chat_manager.py:46)
```python
@dataclass
class GroupParticipant:
    agent_id: str         # "@architect", "@dev" ⚠️ NOT UNIQUE
    model_id: str         # "llama-405b", "deepseek-r1"
    role: GroupRole       # ADMIN, WORKER, REVIEWER, OBSERVER
    display_name: str     # "Dev (Deepseek R1)" ⚠️ HAS model, NO number
    permissions: List[str] = ["read", "write"]
```

### Current groups.json Example
**Location:** `/data/groups.json:1-98`

```json
{
  "groups": {
    "5e2198c2-8b1a-45df-807f-5c73c5496aa8": {
      "name": "MCP Dev",
      "admin_id": "@Architect",
      "participants": {
        "@Architect": {
          "agent_id": "@Architect",
          "model_id": "openai/gpt-5.2-chat",
          "role": "admin",
          "display_name": "Architect (Claude_code)"
        },
        "@Researcher": {
          "agent_id": "@Researcher",
          "model_id": "x-ai/grok-4",
          "role": "worker",
          "display_name": "Researcher (Grok 4)"
        },
        "@grok-4": {  // ⚠️ Direct model addition - auto-generated ID
          "agent_id": "@grok-4",
          "model_id": "grok-4",
          "role": "worker",
          "display_name": "Grok 4"
        }
      }
    }
  }
}
```

**Current Behavior:**
- ✅ Model-based IDs work: `@grok-4`, `@gpt-5.2-chat` (from Phase 80.19 direct add)
- ❌ Role-based IDs collide: `@Dev`, `@PM` (only 1 per group!)

---

## Numbering Status

### Current System: ❌ NO NUMBERING
- **agent_id format:** `@{role}` (e.g., `@Dev`, `@PM`)
- **display_name format:** `{role} ({model})` (e.g., `Dev (Deepseek R1)`)
- **Uniqueness:** ❌ NONE - relies on single role per group

### Desired System: ✅ AUTO-NUMBERING
- **agent_id format:** `@{role}{number}` (e.g., `@dev1`, `@dev2`)
- **display_name format:** `{role}{number} ({model})` (e.g., `Dev1 (Deepseek R1)`)
- **Uniqueness:** ✅ Enforced by sequential numbering

---

## Duplicate Roles Support

### Current: ❌ NOT SUPPORTED
**Test Case:**
```
User adds:
1. Dev (deepseek/deepseek-r1)
2. Dev (openai/gpt-4)

Result:
{
  "@Dev": {
    "agent_id": "@Dev",
    "model_id": "openai/gpt-4",  // ⚠️ Second Dev OVERWRITES first!
    "display_name": "Dev (GPT-4)"
  }
}

// First Dev (Deepseek) is LOST!
```

### Why Duplicates Fail:
1. **Frontend:** `agent_id` generated as `@${role}` (no counter)
2. **Backend:** `participants` dict uses `agent_id` as key
3. **Storage:** Second insert with same key replaces first entry

### Phase 80.19 Workaround (Direct Model Add)
**Location:** `/src/api/routes/group_routes.py:229`

```python
@router.post("/{group_id}/models/add-direct")
async def add_model_direct(group_id, body: AddModelDirectRequest):
    # Extract name from model_id
    model_part = body.model_id.split('/')[-1].split(':')[0]
    agent_id = f"@{model_part}"  # e.g., "@deepseek-r1"

    # ✅ Uniqueness check with counter
    while agent_id in existing_participants:
        agent_id = f"{base_agent_id}-{counter}"
        counter += 1

    # Creates: @deepseek-r1, @deepseek-r1-1, @deepseek-r1-2, etc.
```

**Problem:** Only works for DIRECT model add, NOT for role-based slots!

---

## Changes Needed for dev1/dev2 Numbering

### 🔴 MARKER 1: Frontend - GroupCreatorPanel.tsx
**Location:** `/client/src/components/chat/GroupCreatorPanel.tsx:122-125`

**Current:**
```tsx
const [agents, setAgents] = useState<Agent[]>(
  DEFAULT_ROLES.map(role => ({ role, model: null }))
);
// Creates: [{ role: 'PM', model: null }, { role: 'Dev', model: null }, ...]
```

**Change Needed:**
```tsx
// ✅ Support multiple agents of same role
const [agents, setAgents] = useState<Agent[]>(
  DEFAULT_ROLES.map(role => ({
    role,
    model: null,
    instanceNumber: null  // NEW: Track instance number (1, 2, 3...)
  }))
);

// ✅ Allow adding duplicate roles
const handleAddRole = (roleName: string) => {
  const existingCount = agents.filter(a => a.role === roleName).length;
  setAgents([...agents, {
    role: roleName,
    model: null,
    instanceNumber: existingCount + 1  // Auto-increment
  }]);
};
```

**UI Change:**
- Add "+" button next to each role to add duplicates
- Show instance number in slot: "Dev 1", "Dev 2", etc.

---

### 🔴 MARKER 2: Frontend - ChatPanel.tsx
**Location:** `/client/src/components/chat/ChatPanel.tsx:535-542`

**Current:**
```tsx
const getDisplayName = (role: string, model: string) => {
  const modelPart = model.split('/').pop() || model;
  const shortName = modelPart.split(':')[0];
  const prettyModel = capitalize(shortName);
  return `${role} (${prettyModel})`;  // ❌ No instance number
};
```

**Change Needed:**
```tsx
const getDisplayName = (role: string, model: string, instanceNumber?: number) => {
  const modelPart = model.split('/').pop() || model;
  const shortName = modelPart.split(':')[0];
  const prettyModel = capitalize(shortName);

  // ✅ Add instance number if provided
  const roleWithNumber = instanceNumber ? `${role}${instanceNumber}` : role;
  return `${roleWithNumber} (${prettyModel})`;
  // "Dev1 (Deepseek R1)", "Dev2 (GPT-4)", etc.
};
```

**agent_id Generation:**
```tsx
// Current:
admin_agent_id: `@${firstAgent.role}`  // ❌ "@Dev"

// Change to:
admin_agent_id: `@${firstAgent.role.toLowerCase()}${firstAgent.instanceNumber || ''}`
// ✅ "@dev1", "@dev2", "@pm1", etc.
```

---

### 🔴 MARKER 3: Backend - group_routes.py
**Location:** `/src/api/routes/group_routes.py:104`

**Current:**
```python
@router.post("/{group_id}/participants")
async def add_participant(group_id: str, body: AddParticipantRequest):
    participant = GroupParticipant(
        agent_id=body.agent_id,  # ❌ Accepts duplicate "@Dev"
        model_id=body.model_id,
        role=GroupRole(body.role),
        display_name=body.display_name
    )
    await manager.add_participant(group_id, participant)
```

**Change Needed:**
```python
@router.post("/{group_id}/participants")
async def add_participant(group_id: str, body: AddParticipantRequest):
    manager = get_group_chat_manager()
    group = manager.get_group(group_id)

    # ✅ UNIQUENESS CHECK
    if body.agent_id in group['participants']:
        # Auto-generate unique ID with counter
        base_id = body.agent_id
        counter = 1
        while f"{base_id}{counter}" in group['participants']:
            counter += 1
        agent_id = f"{base_id}{counter}"  # "@dev1" -> "@dev2"
    else:
        agent_id = body.agent_id

    participant = GroupParticipant(
        agent_id=agent_id,  # ✅ Guaranteed unique
        model_id=body.model_id,
        role=GroupRole(body.role),
        display_name=body.display_name
    )
    await manager.add_participant(group_id, participant)

    return {'agent_id': agent_id}  # Return actual ID to frontend
```

---

### 🔴 MARKER 4: Backend - GroupChatManager
**Location:** `/src/services/group_chat_manager.py:472`

**Current:**
```python
async def add_participant(self, group_id, participant):
    group.participants[participant.agent_id] = participant
    # ❌ Silent overwrite if duplicate
```

**Change Needed:**
```python
async def add_participant(self, group_id, participant):
    async with self._lock:
        group = self._groups.get(group_id)
        if not group:
            return False

        # ✅ UNIQUENESS ENFORCEMENT
        if participant.agent_id in group.participants:
            logger.warning(
                f"[GroupChat] Duplicate agent_id '{participant.agent_id}' "
                f"in group {group_id}. Use auto-numbering in routes!"
            )
            return False  # Reject duplicate

        group.participants[participant.agent_id] = participant
        self._track_agent_group(participant.agent_id, group_id)

    # Emit event
    await self._socketio.emit('group_joined', {
        'group_id': group_id,
        'participant': participant.to_dict()
    })

    await self.save_to_json()
    return True
```

**Alternative:** Auto-number inside manager instead of routes
```python
async def add_participant(self, group_id, participant):
    async with self._lock:
        group = self._groups.get(group_id)
        if not group:
            return False

        # ✅ Auto-generate unique agent_id if collision
        agent_id = participant.agent_id
        if agent_id in group.participants:
            base_id = agent_id
            counter = 1
            while f"{base_id}{counter}" in group.participants:
                counter += 1
            agent_id = f"{base_id}{counter}"
            participant.agent_id = agent_id  # Mutate before storing
            logger.info(f"[GroupChat] Auto-numbered: {base_id} -> {agent_id}")

        group.participants[agent_id] = participant
```

---

### 🔴 MARKER 5: Agent Selection Logic
**Location:** `/src/services/group_chat_manager.py:236-264`

**Current @mention Matching:**
```python
all_mentions = re.findall(r'@([\w\-\.]+)', content)

for mention in all_mentions:
    if mention == agent_id or mention in display.split()[0]:
        selected.append(p)
```

**Change Needed:**
```python
# ✅ Support numbered mentions: @dev1, @dev2
all_mentions = re.findall(r'@([\w\-\.]+\d*)', content)  # Allow digits

for mention in all_mentions:
    # Exact match: "@dev1" matches agent_id "@dev1"
    if mention == agent_id.lstrip('@'):
        selected.append(p)
    # Role match: "@dev" matches "Dev1", "Dev2" (first instance)
    elif mention.lower() in display.lower().split()[0].lower():
        selected.append(p)
```

**Behavior:**
- `@dev1` → exact match, selects Dev1
- `@dev2` → exact match, selects Dev2
- `@dev` → fuzzy match, selects first Dev (Dev1)
- `@dev @dev2` → selects Dev1 and Dev2

---

### 🔴 MARKER 6: Message Handler @mention Regex
**Location:** `/src/api/handlers/group_message_handler.py:1024`

**Current:**
```python
agent_mentions = re.findall(r"@(\w+)", response_text)
```

**Change Needed:**
```python
# ✅ Support numbered agents in agent-to-agent mentions
agent_mentions = re.findall(r"@([\w\-]+\d*)", response_text)
# Matches: @dev1, @dev2, @pm, @qa1, etc.
```

---

## Implementation Priority

### Phase 1: Backend Foundation (CRITICAL)
1. ✅ Add uniqueness check in `group_routes.py:add_participant`
2. ✅ Add auto-numbering logic (backend-side generation)
3. ✅ Update `GroupChatManager.add_participant` to reject duplicates
4. ✅ Fix @mention regex to support numbers

### Phase 2: Frontend Display (HIGH)
1. ✅ Update `getDisplayName` to include instance number
2. ✅ Update `agent_id` generation to use lowercase + number
3. ✅ Test existing groups with new numbering

### Phase 3: UI Enhancement (MEDIUM)
1. ✅ Add "+" button to duplicate roles in GroupCreatorPanel
2. ✅ Show instance numbers in UI slots
3. ✅ Allow removing specific instances (not just role)

### Phase 4: Migration (LOW)
1. ⚠️ Existing groups.json has non-numbered IDs
2. ⚠️ Need migration script or backward compatibility
3. ⚠️ Consider: Convert `@Dev` → `@dev1` on first load

---

## Testing Checklist

### Test Case 1: Duplicate Roles
```
Create group with:
- Dev1 (deepseek/deepseek-r1)
- Dev2 (openai/gpt-4)
- QA (anthropic/claude-3)

Expected:
{
  "@dev1": { "agent_id": "@dev1", "model_id": "deepseek/deepseek-r1" },
  "@dev2": { "agent_id": "@dev2", "model_id": "openai/gpt-4" },
  "@qa": { "agent_id": "@qa", "model_id": "anthropic/claude-3" }
}

✅ All 3 agents stored
✅ No overwrites
```

### Test Case 2: @mention Routing
```
User: "@dev1 fix the bug"
Expected: Only Dev1 responds

User: "@dev2 write tests"
Expected: Only Dev2 responds

User: "@dev review this"
Expected: Dev1 responds (first instance)
```

### Test Case 3: Agent-to-Agent Mentions
```
Dev1 response includes: "@dev2 can you review?"
Expected: Dev2 added to responders queue
```

### Test Case 4: Direct Model Add (Existing Feature)
```
Add model directly: "deepseek/deepseek-r1"
Expected:
- agent_id = "@deepseek-r1"
- If duplicate: "@deepseek-r1-1", "@deepseek-r1-2"
✅ Already works (Phase 80.19)
```

---

## Backward Compatibility

### Existing groups.json Format
**Current:**
```json
{
  "@Dev": { "agent_id": "@Dev", "display_name": "Dev (Deepseek R1)" }
}
```

**After Changes:**
```json
{
  "@dev1": { "agent_id": "@dev1", "display_name": "Dev1 (Deepseek R1)" }
}
```

### Migration Strategy:
1. **Option A:** Auto-convert on load
   - Read old format: `@Dev` → convert to `@dev1`
   - Preserve old groups with lowercase + "1" suffix

2. **Option B:** Support both formats
   - Keep old groups as-is (`@Dev`)
   - New groups use numbered format (`@dev1`)
   - @mention logic handles both

**Recommendation:** Option B (gradual migration, no breaking changes)

---

## Summary

### Current State: ❌ BROKEN
- Agent registration uses role-based IDs (`@Dev`, `@PM`)
- Duplicate roles OVERWRITE each other (dict key collision)
- No numbering, no uniqueness enforcement

### Required Changes: 6 Critical Markers
1. **Frontend UI:** Support multiple instances per role
2. **Frontend Logic:** Generate numbered agent_ids (`@dev1`)
3. **Backend Routes:** Add uniqueness check + auto-numbering
4. **Backend Manager:** Enforce uniqueness or auto-number
5. **Agent Selection:** Update @mention regex for numbers
6. **Message Handler:** Update agent-to-agent mention parsing

### Complexity: MEDIUM
- **Frontend:** 2 files, ~50 lines
- **Backend:** 3 files, ~100 lines
- **Risk:** Low (backward compatible if done right)

### Next Steps:
1. Implement backend uniqueness check (highest priority)
2. Update frontend agent_id generation
3. Add UI for duplicate role creation
4. Test with 2-3 Dev agents in one group

---

**END OF ANALYSIS**
