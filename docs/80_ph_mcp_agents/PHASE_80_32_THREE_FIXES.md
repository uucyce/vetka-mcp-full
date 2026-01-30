# Phase 80.32: Three Fixes Summary

**Date:** 2026-01-22
**Status:** COMPLETE

---

## Fixes Applied

### 1. Solo Chat @mention with soloModels (Phase 80.30)

**Problem:** Solo chat @mention dropdown showed hardcoded list instead of models actually used in chat.

**Files Modified:**
- `client/src/components/chat/MessageInput.tsx`
  - Added `soloModels?: string[]` to Props interface (line 42)
  - Added `soloModels` to destructured props (line 133)
  - Passed `soloModels` to MentionPopup (line 569)

**Flow:**
```
ChatPanel (soloModels via useMemo)
  → MessageInput (receives soloModels prop)
    → MentionPopup (renders dynamic list from soloModels)
```

---

### 2. GPT vs PM Conflict - Regex Fix (Phase 80.31)

**Problem:** When user typed `@gpt-5.2-pro`, regex `@(\w+)` captured only "gpt", which matched PM (contains "gpt" in some contexts).

**File Modified:**
- `src/services/group_chat_manager.py`

**Fix:** Changed regex to capture full model IDs with hyphens, dots, and slashes:
```python
all_mentions_raw = re.findall(r'@([\w\-\.]+(?:/[\w\-\.]+)?(?::[\w\-\.]+)?)', content)
```

Added exact matching logic for model IDs:
```python
is_model_mention = '-' in mention or '.' in mention or '/' in mention
if is_model_mention:
    # Exact match for model IDs
    if mention == agent_id or mention == model_id or mention == display:
        selected.append(p)
```

---

### 3. Model Added but Not in @mention (Phase 80.32)

**Problem:** When model added via Model Directory panel, @mention dropdown didn't update.

**File Modified:**
- `client/src/components/chat/ChatPanel.tsx`

**Fix:** Added explicit refetch in `onModelAddedDirect` callback:
```typescript
onModelAddedDirect={(participant) => {
  // ... existing notification code ...

  // Phase 80.32: Force refetch participants for @mention dropdown
  if (activeGroupId) {
    fetch(`/api/groups/${activeGroupId}`)
      .then(res => res.json())
      .then(data => {
        const participants = data.group?.participants;
        if (participants) {
          const participantsArray = Object.values(participants).map((p: any) => ({
            agent_id: p.agent_id,
            display_name: p.display_name,
            role: p.role,
            model_id: p.model_id
          }));
          setCurrentGroupParticipants(participantsArray);
        }
      });
  }
}}
```

---

## Testing Checklist

- [ ] Solo chat: Type `@` - should show only models used in current chat
- [ ] Group chat: Type `@gpt-5.2-pro` - should route to GPT model, NOT PM
- [ ] Group chat: Add model via Model Directory - should appear in @mention dropdown immediately

---

## Related Scout Reports

1. `SCOUT_MODEL_NOT_IN_MENTION.md` - Identified missing refetch trigger
2. `SCOUT_GPT_PM_CONFLICT.md` - Identified regex truncation bug
3. `TEST_SONNET_2_FIXES.md` - Validated Phase 80.22 implementation

---

**All three user-reported issues resolved.**
