# SCOUT 2: PM Hardcode Priority

## Investigation: Is PM Hardcoded as Default Responder?

**Status**: NO HARDCODED PM DEFAULT FOUND ✅

---

## Current Implementation

### File: `/src/services/group_chat_manager.py` Lines 159-295

**Function**: `select_responding_agents()`

#### Priority Order (Actual):
1. **Phase 80.7** - Reply routing: If replying to a specific agent (lines 188-197)
2. **@mentions** - Explicit targeting via @Agent_Name (lines 204-216)
3. **Agent sender isolation** (Phase 80.6) - If sender is AI/MCP agent without @mention → NO response (lines 221-223)
4. **/solo, /team, /round** commands - Explicit commands (lines 228-253)
5. **SMART keyword matching** - Route based on content keywords (lines 255-277)
6. **Default: Prefer admin over first worker** (lines 279-295)

---

## Key Finding: NO PM HARDCODE

### The Default Logic (Lines 279-295)
```python
# 6. Default: first non-observer agent (prefer admin)
admin = None
first_worker = None
for p in participants.values():
    if p.get('role') == 'observer' or p.get('agent_id') == sender_id:
        continue
    if p.get('role') == 'admin' and not admin:
        admin = p
    elif not first_worker:
        first_worker = p

result = admin or first_worker
if result:
    logger.info(f"[GroupChat] Default: {result.get('display_name')}")
    return [result]
```

**What this does**:
- Prefers agents with `role='admin'` (not PM specifically)
- Falls back to first available non-observer worker
- PM only responds if they are the admin OR the first non-observer

---

## The Real Answer: Why PM Seems to Always Respond

### Issue is in Group Initialization, NOT Agent Selection

**Root Cause**: When groups are created, **PM is typically assigned the `admin` role**.

Example from group initialization patterns:
- `role='admin'` when creating PM participant
- `select_responding_agents()` defaults to admin when no explicit routing applies
- This makes PM appear "hardcoded" but it's actually **admin role preference**

---

## @Mention Behavior Analysis

### File: `/src/api/handlers/group_message_handler.py` Lines 74-89, 204-216

When user types `@gpt-5.2-pro`:
1. **MCP agents** are NOT in `participants` dict (lines 74-89)
2. Regular @mention logic searches `participants` (lines 208-211)
3. MCP agents notified via `notify_mcp_agents()` (Phase 80.13)
4. But `select_responding_agents()` only selects from participants

**Result**: `@gpt-5.2-pro` doesn't prevent PM from responding via admin default.

---

## Problem: Missing @Mention Blocking

### Current Flow When User Types `@gpt-5.2-pro someaction`:

1. ✅ MCP mention detected → notify browser_haiku/claude_code (lines 555-568)
2. ❌ **BUT** `select_responding_agents()` still runs (line 613)
3. ❌ No explicit @mentions found in `participants` → falls to default
4. ❌ PM (as admin) gets selected anyway

This is why PM responds even when `@gpt-5.2-pro` is mentioned!

---

## Recommended Fix

### Proposal: Respect @Mentions Priority

**New Priority Order**:
1. **Explicit agent @mentions** → ONLY those agents (or MCP agents)
2. **Reply routing** → Original message sender
3. **Commands** → /solo, /team, /round
4. **Keywords** → SMART matching
5. **Default** → Admin, then first worker

**Implementation**:
```python
# Phase 80.13: If @mentions detected (including MCP agents),
# ONLY respond to mentioned agents in participants
if mentioned or has_mcp_mentions:
    if selected:  # from explicit participants
        return selected
    elif has_mcp_mentions:
        return []  # Wait for MCP agent response via API
```

---

## Summary Table

| Scenario | Current Behavior | Issue | Fix |
|----------|-----------------|-------|-----|
| `@PM do X` | PM responds | ✅ Correct | None needed |
| `@gpt-5.2-pro do X` | Both PM + MCP respond | ❌ Double-response | MCP mention → skip default selection |
| No mention | PM (admin) responds | ✅ Expected | None needed |
| `/solo @Dev` | Dev only | ✅ Correct | None needed |
| Agent sends `@PM` | Only PM responds | ✅ Correct (no cascade) | None needed |

---

## Conclusion

**PM is NOT hardcoded.** The system uses:
- **Admin role preference** in default routing
- **Keyword-based smart selection**
- **Explicit @mention routing**

The **real issue**: When `@gpt-5.2-pro` is mentioned, the system notifies the MCP agent AND still selects PM via default admin preference. This creates overlapping responses rather than exclusive routing.

**Marker**: HAIKU_SCOUT_2_PM_HARDCODE ✅ Investigation Complete
