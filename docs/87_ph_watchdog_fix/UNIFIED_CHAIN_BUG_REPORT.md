# UNIFIED CHAIN BUG REPORT: Agent @Mention Lookup Failure

**Phase:** 87_ph_watchdog_fix
**Date:** 2026-01-21
**Status:** ROOT CAUSE IDENTIFIED + FIX REQUIRED
**Severity:** HIGH - Agents mentioned in chain responses are silently ignored

---

## 1. PROBLEM

When PM agent (Claude Opus 4.5) calls other agents via @mentions in group chat responses, the mentioned agents are NOT added to the response queue.

**Log Evidence:**
```
[GROUP_DEBUG] Agent PM (Claude Opus 4.5) mentioned: ['Researcher', 'Dev', 'browser', 'Dev']
```

Expected: All mentioned agents added to queue and called
Actual: Mentioned agents are ignored, only PM responds

**Impact:**
- Agent chains don't work properly
- @mentions in agent responses have no effect
- Multi-agent workflows broken

---

## 2. ROOT CAUSE

**Location:** `src/api/handlers/group_message_handler.py` lines 645-650

The agent lookup uses **exact string matching** on `display_name`:

```python
# Current (BROKEN) logic:
for pid, pdata in group.get('participants', {}).items():
    pname = pdata.get('display_name', '')
    if pname.lower() == mentioned_name.lower():  # ← EXACT MATCH ONLY
        mentioned_participant = pdata
        break
```

**The Problem:**
- PM says: `@Researcher please analyze`
- UI has participant with `display_name = "Researcher (Claude Opus 4.5)"`
- Lookup tries to match: `"Researcher"` == `"Researcher (Claude Opus 4.5)"` → **NO MATCH**
- `mentioned_participant` becomes `None`
- Agent is NOT added to queue

**Why This Happens:**
Some agents in `participants` have display names like:
- `"Researcher (Claude Opus 4.5)"`
- `"Dev (Claude Sonnet)"`
- `"Browser Haiku"`

But PM generates mentions using just the base name:
- `@Researcher`
- `@Dev`
- `@Browser`

---

## 3. AFFECTED CODE

### File 1: `src/api/handlers/group_message_handler.py`

**Lines 645-660 - Agent Lookup**
```python
# Find mentioned agent in participants
mentioned_participant = None
for pid, pdata in group.get('participants', {}).items():
    pname = pdata.get('display_name', '')
    if pname.lower() == mentioned_name.lower():  # ← BUG HERE
        mentioned_participant = pdata
        break

if mentioned_participant and mentioned_participant.get('role') != 'observer':
    # Check if agent is already in queue (by agent_id)
    already_queued = any(
        p.get('agent_id') == mentioned_participant.get('agent_id')
        for p in participants_to_respond
    )
    if not already_queued:
        participants_to_respond.append(mentioned_participant)
```

### File 2: Participant Data Structure

Participants have this structure in `groups.json`:
```json
{
  "participants": {
    "p_123": {
      "id": "p_123",
      "agent_id": "researcher",
      "display_name": "Researcher (Claude Opus 4.5)",
      "role": "worker"
    }
  }
}
```

---

## 4. FIX REQUIRED

### Solution: Fallback Matching Strategy

Replace exact display_name match with multi-level lookup:

```python
# Fix: Try multiple matching strategies
mentioned_participant = None
mentioned_name_lower = mentioned_name.lower()

for pid, pdata in group.get('participants', {}).items():
    pname = pdata.get('display_name', '').lower()
    agent_id = pdata.get('agent_id', '').lower()

    # Strategy 1: Exact match on display_name
    if pname == mentioned_name_lower:
        mentioned_participant = pdata
        break

    # Strategy 2: Match against agent_id
    if agent_id == mentioned_name_lower:
        mentioned_participant = pdata
        break

    # Strategy 3: Match prefix of display_name
    # "Researcher (Claude Opus 4.5)" → base name is "Researcher"
    if pname.split('(')[0].strip() == mentioned_name_lower:
        mentioned_participant = pdata
        break
```

### Implementation Steps

1. **Locate the code:** `src/api/handlers/group_message_handler.py` lines 645-650
2. **Replace the lookup loop** with fallback matching above
3. **Add logging:** Log which strategy matched
   ```python
   print(f"[CHAIN_FIX] Matched '{mentioned_name}' to agent_id='{agent_id}' (strategy: {strategy})")
   ```
4. **Test:** Verify PM can now call Researcher, Dev, Browser agents

---

## 5. TEST PLAN

### Unit Test: Mention Matching

Create test with various participant display_name formats:

```python
# Test data
participants = {
    "p1": {"display_name": "Researcher (Claude Opus 4.5)", "agent_id": "researcher"},
    "p2": {"display_name": "Dev", "agent_id": "dev"},
    "p3": {"display_name": "Browser Haiku", "agent_id": "browser"},
}

# Test cases
test_mentions = [
    ("Researcher", "p1"),  # Strategy 3: prefix match
    ("researcher", "p1"),  # Strategy 2: agent_id match
    ("Dev", "p2"),         # Strategy 1: exact match
    ("Browser Haiku", "p3"), # Strategy 1: exact match
]

for mentioned_name, expected_pid in test_mentions:
    result = find_mentioned_agent(mentioned_name, participants)
    assert result['id'] == expected_pid
```

### Integration Test: Full Chain

1. Start group chat with PM, Researcher, Dev agents
2. Send message: `"@PM please analyze the problem"`
3. PM responds: `"@Researcher analyze this, then @Dev implement"`
4. Verify in logs:
   ```
   [GROUP_DEBUG] Agent PM mentioned: ['Researcher', 'Dev']
   [CHAIN_FIX] Matched 'Researcher' to agent_id='researcher' (strategy: prefix)
   [CHAIN_FIX] Matched 'Dev' to agent_id='dev' (strategy: exact)
   [GROUP] Agent Researcher called
   [GROUP] Agent Dev called
   ```

### Manual Test: Check Debug Endpoint

```bash
# Get group details to see participant display_name values
curl http://localhost:3000/api/debug/groups/{group_id}

# Verify fix - send message with @mentions from PM
curl -X POST http://localhost:3000/api/debug/mcp/groups/{group_id}/send \
  -d '{"agent_id":"pm","content":"@Researcher check this, then @Dev implement"}'
```

---

## RELATED ISSUES

- **Phase 80.6:** Agent isolation (prevents agent-to-agent auto-response without @mention)
- **Phase 86:** @Mention triggering for MCP endpoints (re-enabled after Phase 80.8)
- **Phase 87:** Watchdog-Qdrant integration race condition

**Key Insight:** This chain bug is separate from Phase 80.6 isolation. Even with explicit @mentions, lookup failure prevents the agent from being added to queue.

---

## IMPLEMENTATION CHECKLIST

- [ ] Read full context from VETKA_KNOWLEDGE_AUDIT.md
- [ ] Understand current participant structure in groups.json
- [ ] Implement fallback matching in group_message_handler.py
- [ ] Add detailed logging for each matching strategy
- [ ] Test with various display_name formats
- [ ] Verify PM can trigger multi-agent chains
- [ ] Document new matching behavior for future phases

---

Generated: 2026-01-21
Type: BUG REPORT + FIX SPECIFICATION
Location: `/docs/87_ph_watchdog_fix/UNIFIED_CHAIN_BUG_REPORT.md`
