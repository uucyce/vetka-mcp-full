# 🚀 Group Chat Fixes - Quick Start Implementation

**Status:** Ready to implement
**Complexity:** LOW-MEDIUM
**Time Estimate:** 2-4 hours for critical fixes

---

## 🎯 What's Broken

When user sends "тест 6" (message without @mentions):
1. ❌ **No agents respond** (looking for 'admin' role, all are 'worker')
2. ❌ **Only 1 agent would respond even if role matched** (break statement)
3. ❌ **Generic prompts** (not using PM_SYSTEM_PROMPT, DEV_SYSTEM_PROMPT, etc.)
4. ❌ **No code context** (semantic search not injected)
5. ❌ **Artifacts lost** (created but not returned)

---

## 🔧 Fix #1: CRITICAL - Role Mismatch (30 minutes)

### Problem
- Frontend: `role: 'worker'` (ChatPanel.tsx:258)
- Backend: Looking for `role: 'admin'` (group_message_handler.py:122)
- Result: No agents match → early return

### Solution: Make first agent 'admin'

**File:** `client/src/components/chat/ChatPanel.tsx`

**Find (line ~254-259):**
```javascript
for (let i = 1; i < validAgents.length; i++) {
  const agent = validAgents[i];
  const addResponse = await fetch(`/api/groups/${groupId}/participants`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      agent_id: `@${agent.role}`,
      model_id: agent.model,
      display_name: agent.role,
      role: 'worker'  // ← CHANGE THIS
    })
```

**Replace with:**
```javascript
for (let i = 1; i < validAgents.length; i++) {
  const agent = validAgents[i];
  // First remaining agent gets 'admin', rest are 'worker'
  const agentRole = (i === 1) ? 'admin' : 'worker';

  const addResponse = await fetch(`/api/groups/${groupId}/participants`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      agent_id: `@${agent.role}`,
      model_id: agent.model,
      display_name: agent.role,
      role: agentRole  // ← Now varies by position
    })
```

**Test:** Send "тест 6" → should get response from @Dev (first remaining agent)

---

## 🔧 Fix #2: HIGH - Multi-Agent Responses (1 hour)

### Problem
Handler finds agents but `break` statement stops after first match:
```python
if pdata['role'] == 'admin' and pid != sender_id:
    participants_to_respond.append(pdata)
    break  # ← STOPS HERE!
```

### Solution: Remove break to collect ALL matching agents

**File:** `src/api/handlers/group_message_handler.py`

**Find (lines ~118-132):**
```python
else:
    # Phase 57.3: Without @mention, only admin responds
    for pid, pdata in group['participants'].items():
        if pdata['role'] == 'admin' and pid != sender_id:
            participants_to_respond.append(pdata)
            break  # Only one agent responds without explicit mention

if not participants_to_respond:
    print(f"[GROUP] No agents to respond in group {group_id}")
    # ... debug output ...
    return
```

**Replace with:**
```python
else:
    # Phase 57.6: All non-admin agents can respond (since we have multiple admins now)
    # First try to get admin
    admin_found = False
    for pid, pdata in group['participants'].items():
        if pdata['role'] == 'admin' and pid != sender_id:
            participants_to_respond.append(pdata)
            admin_found = True
            break  # Only need 1 admin

    # Then collect all non-observer agents (for parallel responses)
    if not admin_found:
        for pid, pdata in group['participants'].items():
            if pdata['role'] != 'observer' and pid != sender_id:
                participants_to_respond.append(pdata)

if not participants_to_respond:
    print(f"[GROUP_DEBUG] No agents to respond in group {group_id}")
    print(f"[GROUP_DEBUG] All participants: {[(pid, pdata.get('role')) for pid, pdata in group.get('participants', {}).items()]}")
    return
```

**Test:**
- Send "тест 6" → should see `[GROUP_DEBUG] Participants to respond: ['@Dev', '@QA', '@Architect']`
- Each agent should call orchestrator

---

## 🔧 Fix #3: HIGH - Role-Specific Prompts (1 hour)

### Problem
All agents get same generic prompt:
```python
prompt = f"""{context}

---
Current message from {sender_id}: {content}
---

Respond as {display_name}. Be helpful and collaborate with the team."""
```

Should use `PM_SYSTEM_PROMPT`, `DEV_SYSTEM_PROMPT`, etc.

### Solution: Inject role system prompts

**File:** `src/api/handlers/group_message_handler.py`

**Add imports at top:**
```python
from src.agents.role_prompts import (
    PM_SYSTEM_PROMPT,
    DEV_SYSTEM_PROMPT,
    QA_SYSTEM_PROMPT,
    ARCHITECT_SYSTEM_PROMPT
)
```

**Find (lines ~204-221), the prompt building section:**
```python
try:
    # Build context from group history
    recent_messages = manager.get_messages(group_id, limit=10)
    context_parts = [
        f"You are {display_name} ({agent_id}) in a group chat called '{group['name']}'.",
        f"Your role: {participant['role']}",
        "",
        "Recent messages:"
    ]
    for msg in recent_messages:
        context_parts.append(f"[{msg['sender_id']}]: {msg['content']}")

    context = "\n".join(context_parts)

    prompt = f"""{context}

---
Current message from {sender_id}: {content}
---

Respond as {display_name}. Be helpful and collaborate with the team."""
```

**Replace with:**
```python
try:
    # Build context from group history
    recent_messages = manager.get_messages(group_id, limit=10)
    context_parts = [
        f"You are {display_name} ({agent_id}) in a group chat called '{group['name']}'.",
        f"Your role: {participant['role']}",
        "",
        "Recent messages:"
    ]
    for msg in recent_messages:
        context_parts.append(f"[{msg['sender_id']}]: {msg['content']}")

    context = "\n".join(context_parts)

    # Map display_name to role prompt
    role_prompts_map = {
        'PM': PM_SYSTEM_PROMPT,
        'pm': PM_SYSTEM_PROMPT,
        'Dev': DEV_SYSTEM_PROMPT,
        'dev': DEV_SYSTEM_PROMPT,
        'QA': QA_SYSTEM_PROMPT,
        'qa': QA_SYSTEM_PROMPT,
        'Architect': ARCHITECT_SYSTEM_PROMPT,
        'architect': ARCHITECT_SYSTEM_PROMPT,
    }

    system_prompt = role_prompts_map.get(display_name, DEV_SYSTEM_PROMPT)

    prompt = f"""{context}

---
Current message from {sender_id}: {content}
---

{system_prompt}"""
```

**Test:**
- Send "тест 6" → check logs for role prompts being used
- Dev response should mention tools (write_code, create_artifact)
- PM response should mention task analysis
- QA response should mention testing

---

## 🔧 Fix #4: MEDIUM - Deduplicate Messages (30 min)

### Problem
Backend sends both `group_stream_end` and `group_message`
Frontend listens to both → duplicate in chat

### Solution: Only listen to stream events for agent messages

**File:** `client/src/components/chat/ChatPanel.tsx`

**Find handleGroupMessage (line ~84-98):**
```typescript
const handleGroupMessage = (e: CustomEvent) => {
  const data = e.detail;
  if (data.group_id !== activeGroupId) return;

  console.log('[ChatPanel] Group message received:', data.sender_id);
  addChatMessage({
    id: data.id || crypto.randomUUID(),
    role: data.sender_id === 'user' ? 'user' : 'assistant',
    agent: data.sender_id !== 'user' ? data.sender_id.replace('@', '') : undefined,
    content: data.content,
    type: 'text',
    timestamp: data.created_at || new Date().toISOString(),
  });
};
```

**Replace with:**
```typescript
const handleGroupMessage = (e: CustomEvent) => {
  const data = e.detail;
  if (data.group_id !== activeGroupId) return;

  // Only handle USER messages here
  // Agent messages come via group_stream_end instead
  if (data.sender_id !== 'user') {
    console.log('[ChatPanel] Skipping agent message (comes via stream_end):', data.sender_id);
    return;
  }

  console.log('[ChatPanel] Group message received:', data.sender_id);
  addChatMessage({
    id: data.id || crypto.randomUUID(),
    role: 'user',
    content: data.content,
    type: 'text',
    timestamp: data.created_at || new Date().toISOString(),
  });
};
```

**Test:** Send message → only appears once in chat, not duplicated

---

## 📋 Testing Checklist

After each fix, test:

### Fix #1 Test:
```
1. Create group with 4 agents (PM, Dev, QA, Architect)
2. Check database or logs
3. Verify: agent[0]=PM (admin), agent[1]=Dev (admin), agent[2]=QA (worker), agent[3]=Arch (worker)
```

### Fix #2 Test:
```
1. Send "тест 6" (no @mentions)
2. Check backend logs for: [GROUP_DEBUG] Participants to respond: [...]
3. Should see at least Dev agent listed
4. Should see orchestrator called multiple times
```

### Fix #3 Test:
```
1. Send "write a hello world script"
2. Check Dev response - should mention tools
3. Check PM response - should talk about tasks
4. Each agent should have different perspective
```

### Fix #4 Test:
```
1. Send message
2. Check chat UI
3. Should see EACH message once
4. No duplicates
```

---

## 🚨 Common Issues

### Issue: "Still no agents responding"
- Check logs for: `[GROUP_DEBUG] Participants to respond:`
- If empty, check agent roles in database
- Verify sender_id isn't matching all participant IDs

### Issue: "Orchestrator not initialized"
- Check `get_orchestrator()` returns valid object
- Check components_init.py setup
- Verify main.py initializes orchestrator before handlers

### Issue: "Messages appearing twice"
- Check if both `group_message` and `group_stream_end` add message
- Implement Fix #4 deduplication
- May need to check message IDs match

---

## 📊 Monitoring Commands

After fixes, run these to verify:

```bash
# Check for agent selection logs
grep -n "GROUP_DEBUG.*Participants" /dev/stdout

# Count how many times orchestrator is called per message
grep -c "GROUP_DEBUG.*call_agent" /dev/stdout

# Check for duplicates (should be 0)
grep "duplicate" /dev/stdout

# Verify role prompts are used
grep "DEV_SYSTEM_PROMPT\|PM_SYSTEM_PROMPT" /dev/stdout
```

---

## 🎬 Final Result

After implementing Fixes #1-#3:

```
User: "тест 6"
│
├─ PM (admin): "I understand the task. Breaking down into subtasks..."
├─ Dev (admin): "I'll implement the solution. Using these tools..."
├─ QA (worker): "I'll create test cases for..."
└─ Architect (worker): "From architecture perspective, we should..."
```

---

**Next Step:** Go to GROUP_CHAT_AUDIT_57_6.md for detailed analysis
**Implementation Help:** Ask about specific files/functions
