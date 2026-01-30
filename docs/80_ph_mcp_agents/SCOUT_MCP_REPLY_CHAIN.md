# SCOUT 4: MCP Reply Chain

**Phase:** 80.16
**Status:** ANALYSIS COMPLETE - Gap Identified
**Focus:** MCP Agent-to-Agent Smart Reply Decay

---

## Current MCP Flow

### MCP Message Processing Path
```
User/MCP Agent → group_message_handler.py:handle_group_message()
                    ↓
                send_message() stores in group.messages
                    ↓
                select_responding_agents() decides who responds
                    ↓
                orchestrator.call_agent() executes chosen agent(s)
```

### MCP Message Endpoint (debug_routes.py)
```
POST /api/debug/mcp/groups/{group_id}/send
    ↓
send_group_message_from_mcp()
    ├─ Stores message in group
    ├─ Calls select_responding_agents()
    ├─ Orchestrates agent responses
    └─ Emits SocketIO events
```

### Key Differences: User vs MCP Messages
| Aspect | User Messages | MCP Messages |
|--------|---------------|--------------|
| Entry point | `group_message` event | `POST /api/debug/mcp/groups/{group_id}/send` |
| Storage | Via `manager.send_message()` | Via `manager.send_message()` ✓ SAME |
| Agent selection | `select_responding_agents()` | `select_responding_agents()` ✓ SAME |
| Response routing | Full orchestration loop | Full orchestration loop ✓ SAME |
| Mention tracking | In message mentions array | In message mentions array ✓ SAME |

---

## Gap Found: Phase 80.6 Firewall

### The Problem
**Phase 80.6 blocks agent-to-agent communication without explicit @mentions:**

File: `src/services/group_chat_manager.py` (lines 199-223)
```python
# Phase 80.6: Check if sender is MCP agent or AI agent (starts with @)
is_agent_sender = sender_id.startswith('@')

# 1. Check for @mentions
mentioned = re.findall(r'@(\w+)', content)
if mentioned:
    # ... route to mentioned agents
    return selected

# Phase 80.6: If sender is an agent (MCP or AI) and no explicit @mention,
# DO NOT auto-respond. This prevents Architect from "hijacking" MCP agent messages.
if is_agent_sender:
    logger.info(f"[GroupChat] Phase 80.6: Agent sender '{sender_id}' without @mention - no auto-response")
    return []
```

### Real-World Impact
```
Scenario: MCP → Agent → Agent Chain

User:        @Dev can you check this?
Dev:         Checked! @Architect review?  [Architect DOES respond ✓]

Dev:         What about tests?           [No @mention, just follow-up]
QA:          [Should respond to Dev, but doesn't ✗]
             Phase 80.6: is_agent_sender = True → returns []
```

### Why This Gap Exists
**Phase 80.6 was designed to prevent:**
- Infinite reply loops between agents
- Auto-cascade of agent responses
- MCP agents hijacking group control

**But it's too strict:**
- Requires explicit @mention for every agent-to-agent message
- Breaks natural conversational flow
- Different from user behavior (users can get follow-up responses without @mentions)

---

## Recommended Fix: Smart Reply Decay

### Design: Last Responder Tracking

Add to group message metadata:
```python
metadata = {
    'last_responder': '@Dev',        # Who responded to this message
    'response_chain_depth': 1,       # How many agent replies in chain
    'reply_to': message_id,          # Message being replied to
}
```

### Algorithm: Decay Logic

```python
async def select_responding_agents(
    self,
    content: str,
    participants: Dict[str, Any],
    sender_id: str,
    reply_to_agent: str = None
) -> List[Any]:
    """
    Phase 80.7+: Smart reply decay for agent-to-agent chains.

    Rules:
    1. Explicit @mentions: ALWAYS respond (highest priority)
    2. Reply to specific agent: Route to THAT agent (Phase 80.7 existing)
    3. User message: Smart keyword selection (existing)
    4. Agent follow-up without @mention:
       - If replying to agent who just responded: Yes (decay depth)
       - If replying to agent who responded >2 messages ago: No (prevent cascade)
       - Response decay: Dev→QA→(PM?) but not QA→Dev→Architect
    """

    # NEW: Check if this is a follow-up to recent agent response
    if sender_id.startswith('@') and not explicit_mentions:
        # Look up what message this sender is replying to
        referenced_msg = find_reply_target(content, group)

        if referenced_msg and referenced_msg['sender_id'].startswith('@'):
            # Get last responder from referenced message
            last_responder = referenced_msg.get('metadata', {}).get('last_responder')
            response_depth = referenced_msg.get('metadata', {}).get('response_chain_depth', 0)

            # Decay logic:
            # Depth 0: User → can get any agent
            # Depth 1: First agent responds → next agent can respond (Dev→Architect)
            # Depth 2: Second agent responds → STOP (no cascade)

            if response_depth < 2 and last_responder != sender_id:
                # Allow reply to PREVIOUS responder's message
                return [find_agent(last_responder, participants)]
            else:
                # Prevent cascade beyond depth 2
                return []

    # ... rest of existing logic
```

### Implementation Steps

**Step 1: Extend GroupMessage metadata**
```python
# In group_chat_manager.py
message = GroupMessage(
    id=str(uuid.uuid4()),
    group_id=group_id,
    sender_id=sender_id,
    content=content,
    mentions=mentions,
    message_type=message_type,
    metadata={
        **(metadata or {}),
        'last_responder': None,        # NEW
        'response_chain_depth': 0,     # NEW
    }
)
```

**Step 2: Track responder after agent responds**
```python
# In group_message_handler.py, after orchestrator.call_agent()
if result.get('status') == 'done':
    response_text = result.get('output', '')

    # Store agent response
    agent_message = await manager.send_message(
        group_id=group_id,
        sender_id=agent_id,
        content=response_text,
        message_type='response',
        metadata={
            'in_reply_to': user_message.id,
            'last_responder': agent_id,
            'response_chain_depth': 0,  # Reset depth for response
        }
    )

    # Update parent message to track who responded
    user_message.metadata['last_responder'] = agent_id
    user_message.metadata['response_chain_depth'] = 0
```

**Step 3: Modify select_responding_agents()**
```python
async def select_responding_agents(
    self,
    content: str,
    participants: Dict[str, Any],
    sender_id: str,
    reply_to_agent: str = None,
    reply_to_msg: dict = None  # NEW: original message being replied to
) -> List[Any]:

    # ... existing explicit @mention check ...

    # NEW Phase 80.6+: Smart reply decay for agent follow-ups
    if sender_id.startswith('@') and not mentioned:
        # This is an agent speaking without explicit mentions
        # Check if they're replying to a recent agent message

        if reply_to_msg:
            last_responder = reply_to_msg.get('metadata', {}).get('last_responder')
            response_depth = reply_to_msg.get('metadata', {}).get('response_chain_depth', 0)

            # Allow response if:
            # 1. We're at depth < 2 (prevent deep cascades)
            # 2. Not self-reply
            if response_depth < 2 and last_responder and last_responder != sender_id:
                # Find and return the last responder
                for pid, p in participants.items():
                    if p.get('agent_id') == last_responder:
                        logger.info(f"[GroupChat] Phase 80.6+: Reply decay depth {response_depth}→{response_depth+1}")
                        return [p]

        # No reply context or depth exceeded: no auto-response
        logger.info(f"[GroupChat] Phase 80.6: Agent {sender_id} without @mention and no reply context")
        return []

    # ... rest of existing logic (user messages) ...
```

**Step 4: Update message flow to pass reply context**
```python
# In group_message_handler.py
# When processing message from MCP agent:

# Phase 80.7: Find original agent if this is a reply
reply_to_agent = None
reply_to_msg = None
if reply_to_id:
    messages = manager.get_messages(group_id, limit=100)
    for msg in messages:
        if msg.get('id') == reply_to_id:
            reply_to_msg = msg  # NEW: pass full message for metadata
            original_sender = msg.get('sender_id', '')
            if original_sender.startswith('@'):
                reply_to_agent = original_sender
            break

# Pass both to select_responding_agents
participants_to_respond = await manager.select_responding_agents(
    content=content,
    participants=group.get('participants', {}),
    sender_id=sender_id,
    reply_to_agent=reply_to_agent,
    reply_to_msg=reply_to_msg  # NEW
)
```

---

## Design Diagram

```
┌─────────────────────────────────────────────────────────────┐
│ CURRENT PHASE 80.6: Firewall (Too Strict)                  │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  User: @Dev can you check?                                 │
│    ↓ is_agent_sender = False                              │
│    ↓ select_responding_agents → [Dev]                      │
│    ↓ Dev responds ✓                                        │
│                                                             │
│  Dev: @Architect review?                                   │
│    ↓ is_agent_sender = True                               │
│    ↓ mentioned = ['Architect']                             │
│    ↓ select_responding_agents → [Architect] ✓             │
│                                                             │
│  Dev: What about tests?  (NO @mention)                     │
│    ↓ is_agent_sender = True                               │
│    ↓ mentioned = []                                        │
│    ↓ Phase 80.6 blocks: return [] ✗                       │
│    ↗ QA never responds (no decay)                          │
│                                                             │
└─────────────────────────────────────────────────────────────┘

        ↓↓↓ APPLY PHASE 80.6+ FIX ↓↓↓

┌─────────────────────────────────────────────────────────────┐
│ PROPOSED PHASE 80.6+: Smart Reply Decay                    │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  User: @Dev can check?                                     │
│    ↓ select_responding_agents → [Dev]                      │
│    ↓ Dev responds (depth: 0→1) ✓                          │
│                                                             │
│  Dev: @Architect review?                                   │
│    ↓ mentioned = ['Architect']                             │
│    ↓ select_responding_agents → [Architect] ✓             │
│    ↓ Architect responds (depth: 1→2)                      │
│                                                             │
│  Architect: Tests?  (NO @mention)                          │
│    ↓ reply_to_msg.last_responder = @Architect              │
│    ↓ reply_to_msg.response_chain_depth = 2                │
│    ↓ Phase 80.6+: depth >= 2 → return [] ✓ (prevents)   │
│    ↓ Natural stop (no infinite cascade)                    │
│                                                             │
│  Dev: @QA can you test?  (EXPLICIT @mention)               │
│    ↓ Phase 80.6 check bypassed (mentioned = ['QA'])       │
│    ↓ select_responding_agents → [QA] ✓                    │
│    ↓ New chain: depth resets to 0→1                       │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Testing Strategy

### Test 1: Basic Reply Decay
```python
# User → Dev → Architect (stops at depth 2)
User: @Dev check this
Dev responds (depth 0→1)
Dev: @Architect review (explicit mention)
Architect responds (depth 1→2)
Architect: Tests look good
QA: [Should NOT auto-respond - depth 2]
```

### Test 2: Explicit Mention Override
```python
# Depth limit should not block explicit @mentions
Architect: depth is 2, but:
Architect: @QA please test this
QA: [MUST respond - explicit @mention]
```

### Test 3: User Follow-Up Resets
```python
User: @Architect any issues?
Architect responds (depth 0→1)
User: @QA can you verify?  (NEW question)
QA responds (depth 0→1 - NEW CHAIN)
```

---

## Files to Modify

1. **src/services/group_chat_manager.py**
   - Extend `GroupMessage` metadata fields
   - Update `select_responding_agents()` with decay logic
   - Lines 159-295 (select_responding_agents function)

2. **src/api/handlers/group_message_handler.py**
   - Track `last_responder` after agent response
   - Pass `reply_to_msg` to select_responding_agents
   - Lines 597-839 (agent response handling loop)

3. **src/api/routes/debug_routes.py**
   - Same updates in `send_group_message_from_mcp()`
   - Lines 1246-1420 (agent selection and response loop)

---

## Summary

**Current State:** Phase 80.6 prevents ALL agent-to-agent replies without explicit @mentions (too strict).

**Problem:** Breaks natural conversational chains where Dev asks QA a follow-up without @mention.

**Solution:** Implement smart reply decay with depth tracking:
- Allow 2-level agent-to-agent chains before stopping
- Explicit @mentions always override
- Metadata tracks: `last_responder`, `response_chain_depth`
- User messages reset the depth counter (new conversation)

**Impact:** Enable natural multi-agent conversations while preventing infinite cascade loops.

**Phases affected:** 80.6 → 80.6+ (enhancement), affects group_message_handler.py and select_responding_agents()

---

*Generated: 2026-01-22 | Scout Report 4 | MCP Reply Chain Analysis*
