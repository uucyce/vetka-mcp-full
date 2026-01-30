# Scout: mimo-v2-flash Missing from @mention Dropdown

**Issue:** Model added to Group Settings panel doesn't appear in @mention dropdown.

**Marker:** `HAIKU_SCOUT_MIMO`

---

## Root Cause Analysis

### 1. Refetch Trigger (Phase 80.29)

**File:** `ChatPanel.tsx:412-456`

```typescript
// Lines 439-451: Refetch conditions
const shouldRefetch =
  sender_id === 'system' ||
  content?.includes('Added') ||
  content?.includes('to group') ||
  content?.includes('Use @');
```

**Status:** ✅ **WORKING**
- When model added, system message says: `"Added {participant.display_name} ({participant.agent_id}) to group. Use {participant.agent_id} to mention."`
- This contains "Added", "to group", and "Use @" — all match refetch conditions
- Refetch fires and updates `currentGroupParticipants`

**Check:** Does the Model Directory trigger this message?

---

### 2. API Response Format (Phase 80.22)

**File:** `group_routes.py:86-95`

```python
@router.get("/{group_id}")
async def get_group(group_id: str):
    """Get group by ID."""
    manager = get_group_chat_manager()
    group = manager.get_group(group_id)

    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    return {'group': group}  # Returns group.to_dict()
```

**File:** `group_chat_manager.py:92-105` (Group.to_dict())

```python
def to_dict(self) -> dict:
    return {
        'id': self.id,
        'name': self.name,
        'description': self.description,
        'admin_id': self.admin_id,
        'participants': {k: v.to_dict() for k, v in self.participants.items()},
        'message_count': len(self.messages),
        'project_id': self.project_id,
        'created_at': self.created_at.isoformat(),
        'last_responder_id': self.last_responder_id,
        'last_responder_decay': self.last_responder_decay
    }
```

**Status:** ✅ **CORRECT FORMAT**
- API returns `participants` as dict: `{"@pm": {...}, "@dev": {...}}`
- Each participant has `agent_id`, `display_name`, `model_id`, `role`

---

### 3. Frontend Participant Loading (Phase 80.22)

**File:** `ChatPanel.tsx:379-410`

```typescript
// Phase 80.22: Fetch group participants when activeGroupId changes
useEffect(() => {
  if (!activeGroupId) {
    setCurrentGroupParticipants([]);
    return;
  }

  const fetchParticipants = async () => {
    try {
      const response = await fetch(`/api/groups/${activeGroupId}`);
      if (response.ok) {
        const data = await response.json();
        const participants = data.group?.participants;  // ← Gets dict
        if (participants) {
          // Convert object to array
          const participantsArray = Object.values(participants).map((p: any) => ({
            agent_id: p.agent_id,
            display_name: p.display_name,
            role: p.role,
            model_id: p.model_id
          }));
          setCurrentGroupParticipants(participantsArray);
          console.log('[ChatPanel] Phase 80.22: Loaded', participantsArray.length, 'group participants for @mention');
        }
      }
    } catch (error) {
      console.error('[ChatPanel] Phase 80.22: Error fetching group participants:', error);
    }
  };

  fetchParticipants();
}, [activeGroupId]);
```

**Status:** ✅ **CORRECT** - Converts participants dict to array and logs count

---

### 4. Mention Popup Rendering (Phase 80.22)

**File:** `MentionPopup.tsx:118-221`

```typescript
// In group mode with participants - show ONLY dynamic participants
if (isGroupMode && groupParticipants && groupParticipants.length > 0) {
  // Build dynamic entries from group participants
  const dynamicParticipants = groupParticipants
    .filter(p => {
      // Filter by search text
      const alias = p.agent_id.replace('@', '').toLowerCase();
      const displayName = p.display_name?.toLowerCase() || '';
      return alias.includes(filter.toLowerCase()) ||
             displayName.includes(filter.toLowerCase());
    })
    .map(p => ({
      alias: p.agent_id,  // e.g., "@PM"
      label: p.display_name || p.agent_id,  // e.g., "PM (GPT-4o)"
      role: p.role,
    }));

  // Always include Hostess in group mode (if matches filter)
  const showHostess = 'hostess'.includes(filter.toLowerCase());

  if (dynamicParticipants.length === 0 && !showHostess) {
    return null;
  }

  return (
    <div>
      {/* ... header ... */}
      {dynamicParticipants.map(({ alias, label }) => (
        <button key={alias} onClick={() => onSelect(alias)}>
          {alias}
          {label}
        </button>
      ))}
    </div>
  );
}
```

**Status:** ✅ **CORRECT** - Renders each participant from `groupParticipants` array

---

## Critical Path Analysis

### When Model Added to Existing Group:

1. **ModelDirectory** → Click model in Group Settings
2. **POST /api/groups/{id}/models/add-direct** (Phase 80.19)
   - Generates agent_id from model name: `@mimo-v2-flash`
   - Creates participant: `{agent_id: "@mimo-v2-flash", model_id: "mimo-v2-flash", display_name: "Mimo V2 Flash", ...}`
   - Adds to group via `manager.add_participant()`
3. **ModelDirectory sends system message?** ← **⚠️ POTENTIAL GAP**
4. **ChatPanel refetch triggers** ← Depends on step 3
5. **MentionPopup updated** ← Depends on step 4

---

## Key Question

**Does `ModelDirectory` emit a system message after successful add-direct call?**

- If **YES**: Refetch works, participant appears
- If **NO**: Refetch never triggers, stale `currentGroupParticipants` stays in state

---

## Expected Data Format

### API Response (Working)
```json
{
  "group": {
    "id": "group-123",
    "participants": {
      "@pm": {
        "agent_id": "@pm",
        "display_name": "PM (GPT-4o)",
        "model_id": "openai/gpt-4o",
        "role": "admin"
      },
      "@mimo-v2-flash": {
        "agent_id": "@mimo-v2-flash",
        "display_name": "Mimo V2 Flash",
        "model_id": "deepseek/mimo-v2-flash",
        "role": "worker"
      }
    }
  }
}
```

### Frontend State (After Refetch)
```typescript
currentGroupParticipants = [
  {
    agent_id: "@pm",
    display_name: "PM (GPT-4o)",
    model_id: "openai/gpt-4o",
    role: "admin"
  },
  {
    agent_id: "@mimo-v2-flash",
    display_name: "Mimo V2 Flash",
    model_id: "deepseek/mimo-v2-flash",
    role: "worker"
  }
]
```

### Mention Popup Render
```
@pm         PM (GPT-4o)
@mimo-v2-flash    Mimo V2 Flash
```

---

## Diagnostic Steps

### 1. Check Browser Console
Look for log: `[ChatPanel] Phase 80.29: Updated @mention to X participants`
- If missing → Refetch never triggered
- If present → Check participant count changed

### 2. Check Network Tab
- POST `/api/groups/{id}/models/add-direct` → 200 OK?
- GET `/api/groups/{id}` (refetch) → participants include new model?

### 3. Check ModelDirectory.tsx
- Does `onModelAddedDirect()` get called after add-direct API call?
- Does it emit system message with "Use @" text?

---

## Solution Path

If refetch doesn't trigger:
1. Add fallback refetch in `onModelAddedDirect` callback (Phase 80.19)
2. OR emit system message from ModelDirectory after successful add
3. OR add manual refetch button in Group Settings

**Recommended:** Trigger refetch from `onModelAddedDirect` callback:

```typescript
onModelAddedDirect={(participant) => {
  // Notify user
  addChatMessage({...});

  // Force refetch participants
  fetch(`/api/groups/${activeGroupId}`)
    .then(res => res.json())
    .then(data => {
      const participants = data.group?.participants;
      if (participants) {
        const array = Object.values(participants).map((p: any) => ({...}));
        setCurrentGroupParticipants(array);
      }
    });
}}
```

---

## Files Involved

- `/client/src/components/chat/ChatPanel.tsx` — Refetch logic (lines 412-456)
- `/client/src/components/chat/MentionPopup.tsx` — Render logic (lines 118-221)
- `/src/api/routes/group_routes.py` — GET /api/groups/{id} endpoint
- `/src/services/group_chat_manager.py` — Group.to_dict() serialization
- `/client/src/components/ModelDirectory.tsx` — ⚠️ CHECK THIS

---

**Status:** Refetch mechanism is correct. Issue likely in ModelDirectory callback not triggering system message or refetch.
