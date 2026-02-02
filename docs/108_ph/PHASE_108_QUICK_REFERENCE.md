# Phase 108 - Quick Reference для Sonnet

**TL;DR:** 4 баги найдены, 2 критичные, отчеты готовы в docs/

---

## 🎯 В ЧЕМ ПРОБЛЕМА

```
BEFORE (Текущее состояние):
┌─────────────────────────────────┐
│ User: "@grok-4 analyze"         │
├─────────────────────────────────┤
│ System: Grok API rate-limited   │
│ → AUTO-FALLBACK to OpenRouter   │  ❌ БАГ #1
│ → OpenRouter sends back Claude  │
│ → User gets Claude, NOT Grok    │
└─────────────────────────────────┘

AFTER (Что должно быть):
┌─────────────────────────────────┐
│ User: "@grok-4 analyze"         │
├─────────────────────────────────┤
│ System: Grok API rate-limited   │
│ → Error shown to user: "Grok    │
│   keys exhausted, try later"    │
│ → User can try different model  │
└─────────────────────────────────┘
```

---

## 🔴 КРИТИЧНЫЕ БАГИ (ДЕЛАТЬ ПЕРВЫМ)

### БАГ #1: Auto-Fallback на OpenRouter

**Файл:** `/src/elisya/provider_registry.py`

**Lines:**
- 1139-1154 (XaiKeysExhausted)
- 1155-1182 (HTTP 401/402/403/429)
- 1220-1225 (General Exception)

**Код сейчас:**
```python
async def call_model_v2(...):
    try:
        result = await provider_instance.call(...)
        return result
    except ValueError:
        # AUTO-FALLBACK to OpenRouter ❌ BAD
        print(f"[REGISTRY] {provider.value} API key not found, trying OpenRouter fallback...")
        result = await openrouter_provider.call(...)
        return result
```

**Что нужно:**
```python
async def call_model_v2(...):
    try:
        result = await provider_instance.call(...)
        return result
    except ValueError as e:
        # ✅ GOOD: Propagate error, don't hide
        print(f"[REGISTRY] {provider.value} failed: {e}")
        raise  # Let caller decide
```

**Test:** `@grok-4` with no xAI keys → should show error, not silently use OpenRouter

---

### БАГ #2: Reply to MCP Agents

**Файл:** `/src/api/handlers/group_message_handler.py`

**Lines:** 663-677

**Код сейчас:**
```python
if reply_to_id:
    messages = manager.get_messages(group_id, limit=100)
    for msg in messages:
        if msg.get("id") == reply_to_id:
            original_sender = msg.get("sender_id", "")
            # ❌ BUG: Only checks if sender starts with "@"
            if original_sender.startswith("@"):
                reply_to_agent = original_sender
            # ❌ But MCP messages have sender_id = "claude_code" (NO @)
            # ❌ So reply gets ignored!
```

**Что нужно:**
```python
if reply_to_id:
    messages = manager.get_messages(group_id, limit=100)
    for msg in messages:
        if msg.get("id") == reply_to_id:
            original_sender = msg.get("sender_id", "")

            # ✅ Check if MCP agent FIRST
            if original_sender in ["claude_code", "browser_haiku"]:
                await notify_mcp_agents(
                    sio=sio,
                    group_id=group_id,
                    sender_id=sender_id,
                    content=content,
                    mentions=[original_sender],
                    message_id=user_message.id,
                    is_reply=True  # Mark as reply!
                )
                return  # Don't continue!

            # ✅ Then check AI agents
            elif original_sender.startswith("@"):
                reply_to_agent = original_sender
```

**Test:** Reply to claude_code message → should route to claude_code, not another agent

---

## 🟡 ВАЖНЫЕ ПРОБЛЕМЫ

### ПРОБЛЕМА #3: Author Format Inconsistency

**Files:** Multiple (see AUDIT)

**Что нужно:**
Choose ONE format for sender_id:
- A: `"claude-3-opus (anthropic)"`
- B: `"@architect (claude-3-opus)"` ← **RECOMMENDED**
- C: `"Architect (claude-3-opus)"`

Then apply EVERYWHERE:
- group_message_handler.py:656 (sender_id)
- group_message_handler.py:944-946 (chat_history)
- group_chat_manager.py:656 (send_message)

**Why:** UI attribution currently confused about agent identity

---

### ПРОБЛЕМА #4: @mention Regex Too Simple

**File:** `/src/api/handlers/group_message_handler.py:617`

**Текущий regex:**
```python
all_mentions = re.findall(r"@(\w+)", content)
# Captures: @grok → ["grok"]
# Misses: @gpt-5.2 → ["gpt"] ❌
# Misses: @grok-4 → ["grok"] ❌
```

**New regex (use from group_chat_manager.py:235):**
```python
all_mentions = re.findall(
    r'@([\w\-\.]+(?:/[\w\-\.]+)?(?::[\w\-\.]+)?)',
    content
)
# Captures: @gpt-5.2 → ["gpt-5.2"] ✅
# Captures: @grok-4 → ["grok-4"] ✅
# Captures: @openai/gpt-4 → ["openai/gpt-4"] ✅
```

---

## 📋 IMPLEMENTATION ORDER

```
Phase 108.1 (Days 1-2) - CRITICAL
├─ Fix MARKER_FALLBACK_BUG (provider_registry.py)
├─ Fix MARKER_REPLY_HANDLER (group_message_handler.py)
└─ Test both fixes work

Phase 108.2 (Day 3) - IMPORTANT
├─ Choose author format
├─ Apply to all 3 locations
├─ Update groups.json schema
└─ Test attribution is consistent

Phase 108.3 (Optional) - NICE TO HAVE
├─ Fix MARKER_MCP_ROUTING (regex)
├─ Add Phase 80.28 logging
└─ Update ROUTING.md docs
```

---

## 🧪 TEST CHECKLIST

After each fix, test:

### Test Scenario 1: Fallback Bug Fix
```
Setup: No xAI keys, Grok rate-limited
Action: Send "@grok-4 help"
Expected: Error message shown, not silent fallback
Status: [ ] PASS / [ ] FAIL
```

### Test Scenario 2: MCP Reply Fix
```
Setup: claude_code sent message, user replies
Action: User replies to claude_code message
Expected: claude_code receives reply notification
Status: [ ] PASS / [ ] FAIL
```

### Test Scenario 3: Author Format
```
Setup: Multiple agents (Claude, Llama, Grok)
Action: All respond to same user message
Expected: UI shows "@architect (claude-3-opus)", etc
Status: [ ] PASS / [ ] FAIL
```

### Test Scenario 4: @mention Regex
```
Setup: User types "@gpt-5.2 analyze"
Action: Message is sent
Expected: @mention correctly parsed, routed
Status: [ ] PASS / [ ] FAIL
```

---

## 📍 MARKER LOCATIONS

Quick search for all markers:

```bash
# Find all markers:
grep -r "MARKER_FALLBACK_BUG\|MARKER_ROUTING_LOGIC\|MARKER_AUTHOR_FORMAT\|MARKER_REPLY_HANDLER\|MARKER_MCP_ROUTING" src/

# By severity:
# CRITICAL:
grep -r "MARKER_FALLBACK_BUG\|MARKER_REPLY_HANDLER" src/

# IMPORTANT:
grep -r "MARKER_AUTHOR_FORMAT" src/

# OPTIONAL:
grep -r "MARKER_MCP_ROUTING" src/
```

---

## 📂 DOCUMENTATION

Created 4 files:

1. **PHASE_108_ROUTING_AUDIT.md** (15 KB)
   - Full technical analysis
   - Every issue documented
   - Recommended fixes

2. **PHASE_108_ROUTING_EXAMPLES.md** (12 KB)
   - Concrete code examples
   - Before/after scenarios
   - Test cases

3. **PHASE_108_SUMMARY.md** (8 KB)
   - Executive overview
   - Issues table
   - Implementation order

4. **PHASE_108_QUICK_REFERENCE.md** (this file)
   - TL;DR version
   - For busy devs
   - Copy-paste fixes

---

## 🎬 START HERE

1. Read **PHASE_108_SUMMARY.md** (5 min read)
2. Read **PHASE_108_ROUTING_EXAMPLES.md** for actual code (10 min)
3. Implement fixes in order (Phase 108.1 → 108.2 → 108.3)
4. Test each fix using test scenarios above
5. Submit PR with fixes

---

## 💬 FAQ

**Q: Can code work without fixes?**
A: Partially. Basic group chats work, but:
- Auto-fallback can route to wrong model
- Reply to MCP agents fails silently
- Author attribution inconsistent

**Q: Which is most urgent?**
A: MARKER_FALLBACK_BUG - it affects user expectations most

**Q: Can I do Phase 108.2 and 108.3 together?**
A: Yes, they're independent. Do 108.1 first.

**Q: How long to implement all?**
A: ~3 days for full Phase 108

---

## 📞 REFERENCE

- **Main audit:** docs/PHASE_108_ROUTING_AUDIT.md
- **Examples:** docs/PHASE_108_ROUTING_EXAMPLES.md
- **Summary:** docs/PHASE_108_SUMMARY.md
- **This file:** docs/PHASE_108_QUICK_REFERENCE.md

---

**READY TO START? Go to PHASE_108_ROUTING_AUDIT.md for detailed guide.**
