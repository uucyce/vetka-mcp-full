# PHASE 90.1.3: Group Chat Reply Routing Bug Investigation

Date: 2026-01-23
Status: INVESTIGATION COMPLETE
Severity: HIGH - Reply routing broken in group chat

---

## MARKER_90.1.3_START: Reply Routing Investigation

### Problem Summary
When user replies to a specific model's message in group chat (e.g., Grok), the reply goes to the ADMIN (mapped to "Architect") instead of the target model. Solo chat works correctly.

### Root Cause Identified

**Location**: `src/api/handlers/group_message_handler.py` lines 604-627
**Issue**: The `reply_to_agent` is being extracted but the matching logic has a critical flaw.

```python
# Phase 80.7: Find original agent if this is a reply
reply_to_agent = None
if reply_to_id:
    # Look up the original message to find its sender
    messages = manager.get_messages(group_id, limit=100)
    for msg in messages:
        if msg.get('id') == reply_to_id:
            original_sender = msg.get('sender_id', '')
            # Only route to agent replies (not user replies)
            if original_sender.startswith('@'):
                reply_to_agent = original_sender
                print(f"[GROUP_DEBUG] Phase 80.7: Reply to message {reply_to_id[:8]}... from {reply_to_agent}")
            break

# Pass reply_to_agent to select_responding_agents
participants_to_respond = await manager.select_responding_agents(
    content=content,
    participants=group.get('participants', {}),
    sender_id=sender_id,
    reply_to_agent=reply_to_agent,  # <-- This is passed
    group=group_object
)
```

### Reply Routing Flow Comparison

#### GROUP CHAT FLOW (BROKEN):
1. User replies to message from `@Grok` (reply_to_id = message_id)
2. Handler finds original sender: `@Grok` → sets `reply_to_agent = "@Grok"`
3. Calls `select_responding_agents(reply_to_agent="@Grok")`
4. In `group_chat_manager.py`, the matching logic runs:

```python
# src/services/group_chat_manager.py lines ~110-118
if reply_to_agent:
    for pid, p in participants.items():
        agent_id = p.get('agent_id', '')
        # Match by agent_id (with or without @)
        if agent_id == reply_to_agent or agent_id == f"@{reply_to_agent}" or f"@{agent_id.lstrip('@')}" == reply_to_agent:
            if p.get('role') != 'observer':
                logger.info(f"[GroupChat] Phase 80.7: Reply routing to {p.get('display_name')}")
                return [p]
    # If reply_to_agent not found in participants, fall through to normal selection
    logger.warning(f"[GroupChat] Phase 80.7: Reply target '{reply_to_agent}' not found in participants")
```

**THE BUG IS HERE**: The matching logic compares `agent_id` (which is stored as `@grok` or `@Grok` in participants) against `reply_to_agent` (which is `@Grok` from the message sender_id).

**Problem**: If the participant is added with `agent_id = "@grok"` (lowercase) but the message sender_id is `@Grok` (titlecase), the string comparison FAILS:
- `"@grok" == "@Grok"` → FALSE ❌
- `"@grok" == "@Grok"` → FALSE (second condition) ❌
- `"@grok".lstrip('@') == "@Grok"` → `"grok" == "@Grok"` → FALSE ❌

5. Since matching fails, the function logs: `"Reply target '@Grok' not found in participants"`
6. Falls through to default selection logic (line ~220 in group_chat_manager.py)
7. Default picks ADMIN (first non-observer if no admin exists)
8. Admin role is mapped to agent_type `'Architect'` (line 673 in group_message_handler.py)
9. **Result**: Message goes to Architect instead of target model ❌

#### SOLO CHAT FLOW (WORKS):
In `src/api/handlers/user_message_handler.py`:
1. User specifies model directly via UI: `requested_model = data.get('model')`
2. Handler DIRECTLY routes to that model (lines 227-245)
3. No fallback logic, no matching issues
4. Model receives message regardless of case sensitivity

**Key Difference**: Solo chat uses direct model selection, not participant matching.

---

### Root Cause Analysis

**File**: `src/services/group_chat_manager.py` (select_responding_agents function)

**Problem #1: Case Sensitivity**
The matching logic is case-sensitive but `reply_to_agent` comes from message `sender_id` which may have different casing than stored `agent_id` in participants dict.

**Problem #2: Missing Normalization**
No case normalization before comparison. Compare with @mention handling (lines ~135):
```python
all_mentions = list(set(m.lower() for m in all_mentions_raw))  # <-- NORMALIZES TO LOWERCASE
```

But reply_to_agent matching does NOT normalize:
```python
if agent_id == reply_to_agent or agent_id == f"@{reply_to_agent}" or ...  # <-- NO NORMALIZATION
```

**Problem #3: Agent ID Format Inconsistency**
- Participants may store agent_id as: `@grok`, `@Grok`, `Grok`, `grok`
- Message sender_id stores as: `@Grok`, `@grok` (depends on original)
- No standard format enforcement

---

### Suspected Fix Locations

**PRIMARY FIX** (HIGHEST PRIORITY):
**File**: `src/services/group_chat_manager.py`
**Function**: `select_responding_agents()`
**Lines**: ~110-120 (reply_to_agent matching block)

**Current Code**:
```python
if reply_to_agent:
    for pid, p in participants.items():
        agent_id = p.get('agent_id', '')
        # Match by agent_id (with or without @)
        if agent_id == reply_to_agent or agent_id == f"@{reply_to_agent}" or f"@{agent_id.lstrip('@')}" == reply_to_agent:
            if p.get('role') != 'observer':
                logger.info(f"[GroupChat] Phase 80.7: Reply routing to {p.get('display_name')}")
                return [p]
    logger.warning(f"[GroupChat] Phase 80.7: Reply target '{reply_to_agent}' not found in participants")
```

**FIX REQUIRED**: Normalize both strings to lowercase before comparison:
```python
if reply_to_agent:
    reply_to_agent_normalized = reply_to_agent.lower().lstrip('@')  # NORMALIZE
    for pid, p in participants.items():
        agent_id = p.get('agent_id', '')
        agent_id_normalized = agent_id.lower().lstrip('@')  # NORMALIZE

        # Match normalized versions
        if agent_id_normalized == reply_to_agent_normalized:
            if p.get('role') != 'observer':
                logger.info(f"[GroupChat] Phase 80.7: Reply routing to {p.get('display_name')}")
                return [p]
    logger.warning(f"[GroupChat] Phase 80.7: Reply target '{reply_to_agent}' not found in participants")
```

**SECONDARY FIX** (Optional, for consistency):
**File**: `src/api/handlers/group_message_handler.py`
**Lines**: 661-675 (agent_type_map)

Currently, 'admin' role defaults to 'PM'. If group admins are frequently models (Grok, Claude), consider if this fallback is appropriate.

**TERTIARY FIX** (Long-term):
- Implement agent_id normalization standards when participants are added
- Always store agent_id with `@` prefix and lowercase
- Normalize all comparisons consistently

---

### Detection Strategy

**In Logs**, look for:
```
[GroupChat] Phase 80.7: Reply target '@Grok' not found in participants
[GroupChat] Default: Architect
```

If you see both messages in sequence, the reply routing failed and fell back to admin.

**Expected Correct Logs**:
```
[GroupChat] Phase 80.7: Reply routing to Grok
```

---

### Impact Assessment

- **Severity**: HIGH - User's explicit reply routing is ignored
- **Affected Scope**: Group chat only (solo chat uses direct model selection)
- **User Experience**: Confusing - reply goes to wrong agent despite explicit targeting
- **Workaround**: None currently viable (reply routing is core feature)

---

## MARKER_90.1.3_END

### Next Steps (PHASE 90.1.4)
1. Apply case normalization fix to `select_responding_agents()`
2. Add test case: reply to @Grok with different case variations
3. Verify solo chat continues to work (unaffected by group chat fix)
4. Test with multiple models (verify works for all, not just Architect)
