# Phase 80.22: Fix @Mention Dropdown Sync with Group Participants

## Problem

The @mention dropdown in group chat mode was using hardcoded `MENTION_ALIASES` from `types/chat.ts` instead of dynamically showing the actual participants in the current group.

When a model is added to a group via Model Directory, it should automatically appear in the @mention dropdown.

## Solution

### 1. MentionPopup.tsx - Dynamic Participants

**Before**: Always filtered from hardcoded `MENTION_ALIASES`, matching by display_name.

**After**: In group mode with participants, renders dynamically from `groupParticipants` prop:
- Shows agent_id as the alias (e.g., `@PM`)
- Shows display_name as the label (e.g., `PM (GPT-4o)`)
- Always includes @hostess as orchestrator
- Falls back to hardcoded aliases for solo chat mode

```typescript
// Phase 80.22: Dynamic @mention dropdown
if (isGroupMode && groupParticipants && groupParticipants.length > 0) {
  // Build entries from actual group participants
  const dynamicParticipants = groupParticipants
    .filter(p => /* matches filter */)
    .map(p => ({
      alias: p.agent_id,      // @PM
      label: p.display_name,  // PM (GPT-4o)
    }));
  // Render dynamic dropdown
}
```

### 2. ChatPanel.tsx - Fetch Participants

Added state and useEffect to fetch group participants:

```typescript
// Phase 80.22: Current group participants for @mention dropdown
const [currentGroupParticipants, setCurrentGroupParticipants] = useState([]);

// Fetch when activeGroupId changes
useEffect(() => {
  if (!activeGroupId) return;

  fetch(`/api/groups/${activeGroupId}`)
    .then(response => response.json())
    .then(data => {
      const participants = Object.values(data.group.participants);
      setCurrentGroupParticipants(participants);
    });
}, [activeGroupId]);
```

### 3. Props Flow

```
ChatPanel.tsx
  |-- currentGroupParticipants (state)
  |-- Fetches from /api/groups/{id} when activeGroupId changes
  |
  +-> MessageInput
        |-- groupParticipants={currentGroupParticipants}
        |
        +-> MentionPopup
              |-- groupParticipants (prop)
              |-- Renders dynamic list in group mode
```

## Files Changed

1. **client/src/components/chat/MentionPopup.tsx**
   - Added dynamic rendering for group mode
   - Fallback to hardcoded aliases for solo chat
   - Added Bot icon for dynamic participants

2. **client/src/components/chat/ChatPanel.tsx**
   - Added `currentGroupParticipants` state
   - Added useEffect to fetch participants when group changes
   - Pass participants to MessageInput

## Display Format in Dropdown

Group mode:
```
@PM -> PM (GPT-4o)
@Dev -> Dev (DeepSeek R1)
@QA -> QA (Llama 3)
@hostess -> Hostess (Orchestrator)
```

Solo mode (fallback):
```
@pm -> PM (Project Manager)
@dev -> Developer
@claude -> Claude
```

## Auto-Registration

Model auto-registration is already implemented in Phase 80.19:
- When user clicks model in Model Directory while in group mode
- If no active slot -> calls `/api/groups/{id}/models/add-direct`
- Model becomes participant and appears in @mention dropdown

## Testing

1. Create a group with PM and Dev roles
2. Type `@` in message input
3. Verify dropdown shows only `@PM`, `@Dev`, `@hostess`
4. Open Model Directory, click any model
5. Verify model appears in @mention dropdown with correct label
