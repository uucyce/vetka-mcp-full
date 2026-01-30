# SCOUT 3: Smart Reply with Decay

**Phase:** 80.14
**Status:** INVESTIGATION COMPLETE
**Date:** 2026-01-22

---

## Current State

**FINDING: No `last_responder` tracking exists in current codebase.**

Codebase status:
- `Group` dataclass (line 76-100 in `group_chat_manager.py`): Has no `last_responder` field
- Agent selection in `select_responding_agents()` (lines 159-295): Purely rule-based, NO memory of who responded previously
- Message handler in `group_message_handler.py` (lines 500-866): Calls `select_responding_agents()` but never tracks which agent responded

Current selection mechanism (priority order):
1. Reply routing to specific agent (Phase 80.7) ✓
2. Explicit @mentions ✓
3. Command overrides (/solo, /team, /round) ✓
4. Smart keyword matching ✓
5. First available non-observer agent ✓

---

## Where to Track

**RECOMMENDED LOCATION: `Group` dataclass**

```python
@dataclass
class Group:
    id: str
    name: str
    # ... existing fields ...

    # PHASE 80.14: Add smart reply with decay
    last_responder_id: Optional[str] = None          # @architect, @dev, etc
    last_responder_decay_count: int = 0              # Counts user messages since response
    last_responder_timestamp: Optional[datetime] = None  # When they last responded
```

**Why here?**
- Group state is persistent (saved to JSON in `save_to_json()`)
- Already tracked per-group (responder memory doesn't cross groups)
- Simple to reset on new @mention or /command
- Easy to access in `select_responding_agents()`

---

## Implementation Outline

### Step 1: Modify `Group` Model
Location: `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/services/group_chat_manager.py`

Add to `Group` dataclass (around line 76):
```python
last_responder_id: Optional[str] = None
last_responder_decay_count: int = 0
last_responder_timestamp: Optional[datetime] = None
```

Update `to_dict()` method (line 89) to include these fields for persistence.

---

### Step 2: Track Responder After Agent Response
Location: `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/api/handlers/group_message_handler.py`

After agent successfully responds (around line 750):
```python
# Phase 80.14: Track who just responded for smart reply
if agent_message:
    async with manager._lock:
        group = manager._groups.get(group_id)
        if group:
            group.last_responder_id = agent_id
            group.last_responder_decay_count = 0
            group.last_responder_timestamp = datetime.now()
```

---

### Step 3: Implement Smart Selection in `select_responding_agents()`
Location: `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/services/group_chat_manager.py`

Insert after explicit @mention check (around line 216), before agent sender check:

```python
# Phase 80.14: Smart reply with decay
# If user message (not agent) and no explicit @mention/command
# and within decay window, route to last responder
if sender_id == 'user':  # Only for user messages, not agent-to-agent
    if group.last_responder_id and group.last_responder_decay_count < 1:
        # Last responder still valid (only 1 message decay)
        for pid, p in participants.items():
            if p.get('agent_id') == group.last_responder_id and p.get('role') != 'observer':
                logger.info(f"[GroupChat] Phase 80.14: Smart reply routing to {p.get('display_name')} (decay={group.last_responder_decay_count})")
                return [p]
```

---

### Step 4: Increment Decay Counter on User Message
Location: `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/services/group_chat_manager.py`

In `send_message()` method (around line 544), after storing message:
```python
# Phase 80.14: Increment decay counter on user messages
if sender_id == 'user':
    group.last_responder_decay_count += 1
```

---

### Step 5: Reset on Explicit Routing
Location: `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/services/group_chat_manager.py`

In `select_responding_agents()`, reset decay when:
- Any @mention is detected
- Any /command is used
- Keyword matching triggers different agent

```python
# When resetting routing (line 213-216, etc):
async with manager._lock:
    group = manager._groups.get(group_id)
    if group:
        group.last_responder_decay_count = 0  # Reset decay
```

---

## Smart Reply Flow Example

```
User: "Can you help with the dashboard?"
→ Architect responds (selected by smart keyword matching)
→ last_responder_id = '@architect', decay_count = 0

User: "Add dark mode too"
→ No @mention, decay_count=0, so route to Architect again
→ Architect responds
→ decay_count = 0 (reset after response)

User: "@QA please test this"
→ Explicit @mention overrides smart reply
→ QA responds, becomes new last_responder

User: "Is it working?"
→ No @mention, decay_count < 1, route to QA (last responder)
→ QA responds
→ decay_count = 0 (reset after response)

User: "Great! Now fix the button"
→ User message #2 without @mention
→ decay_count=1, exceeds limit, fall back to smart/default
→ Dev responds (matches 'fix' keyword), becomes new last_responder
```

---

## Key Design Decisions

1. **Decay = 1 message**: Simple, predictable. User can always override with @mention.
2. **User messages only**: Agent-to-agent still requires explicit @mention (Phase 80.6).
3. **Reset on response**: After responder answers, decay resets to 0.
4. **Persistence**: Stored in Group.to_dict() so survives server restart.
5. **Override hierarchy**: @mention > command > smart reply decay > keyword matching > default.

---

## Testing Strategy

```python
# Test case 1: Basic decay
async def test_smart_reply_decay():
    group = manager.create_group(...)

    # Message 1: selects Architect
    await manager.send_message(group, 'user', 'design the system')
    agents = await manager.select_responding_agents(...)
    assert agents[0].agent_id == '@architect'

    # Message 2: decay=0, should select Architect again
    await manager.send_message(group, 'user', 'make it async')
    agents = await manager.select_responding_agents(...)
    assert agents[0].agent_id == '@architect'

    # Message 3: decay=1, exceeds limit, falls back to keyword/default
    await manager.send_message(group, 'user', 'anything')
    agents = await manager.select_responding_agents(...)
    assert agents[0].agent_id != '@architect'  # Different agent selected

# Test case 2: @mention resets decay
async def test_mention_resets_decay():
    # After Architect responds and decay increments
    await manager.send_message(group, 'user', '@QA test this')
    agents = await manager.select_responding_agents(...)
    assert agents[0].agent_id == '@qa'

    # Verify decay was reset
    assert group.last_responder_decay_count == 0
```

---

## Files to Modify

| File | Changes | Lines |
|------|---------|-------|
| `group_chat_manager.py` | 1. Add fields to `Group` dataclass | 76-88 |
| | 2. Update `to_dict()` method | 89-99 |
| | 3. Add smart reply logic to `select_responding_agents()` | After 216 |
| | 4. Increment decay in `send_message()` | After 544 |
| `group_message_handler.py` | 5. Track responder after response | After 750 |

---

## Edge Cases Handled

- **Responder leaves group**: Smart reply falls back to keyword matching
- **Group has no responders**: Never happens (always at least 1 agent)
- **User is agent**: Check `sender_id == 'user'` to avoid agent-to-agent confusion
- **Multiple mentions**: First @mention wins, resets decay
- **Server restart**: Decay state persists in JSON

---

**Status:** Ready for implementation
**Complexity:** Low-Medium (2-3 hours)
**Risk:** Low (backwards compatible, opt-in via decay check)
**Impact:** Improved UX for multi-turn conversations with single agent focus
