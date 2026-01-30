# SCOUT: GPT-5.2-Pro vs PM Response Conflict

**Status**: ROOT CAUSE IDENTIFIED ✅

---

## Problem Statement

When user types `@gpt-5.2-pro do X`, **both PM and MCP agent respond**. Should be exclusive to MCP agent.

---

## Root Cause Analysis

### Three Regex Patterns in select_responding_agents()

**Line 215** - Simple @mention regex:
```python
mentioned = re.findall(r'@(\w+)', content)
```
- Captures: word characters only (letters, digits, underscore)
- STOPS AT HYPHEN
- `@gpt-5.2-pro` → captures only `['gpt']` ⚠️

**Line 217** - Model ID regex (Phase 80.27):
```python
mentioned_models = re.findall(r'@([\w\-\.]+(?:/[\w\-\.]+)?(?::[\w\-\.]+)?)', content)
```
- Captures: word chars, hyphens, dots, slashes, colons
- `@gpt-5.2-pro` → captures `['gpt-5.2-pro']` ✅

**Line 547** - parse_mentions (used in send_message):
```python
re.findall(r'@([\w\-.:\/]+)', content)
```
- Captures: word chars, hyphens, dots, colons, slashes
- `@gpt-5.2-pro` → captures `['gpt-5.2-pro']` ✅

---

## The Bug: Substring Matching in Line 227

### Code (Lines 215-234):

```python
mentioned = re.findall(r'@(\w+)', content)                    # Line 215 - BREAKS on hyphen
mentioned_models = re.findall(r'@([\w\-\.]+(?:/[\w\-\.]+)?(?::[\w\-\.]+)?)', content)

if mentioned or mentioned_models:
    selected = []
    matched_any = False
    for pid, p in participants.items():
        display = p.get('display_name', '').lower()
        agent_id = p.get('agent_id', '').lower().lstrip('@')
        # Create combined set: {'gpt', 'gpt-5.2-pro'}
        all_mentions = set(m.lower() for m in mentioned) | set(m.lower() for m in mentioned_models)
        # LINE 227: SUBSTRING MATCHING BUG!
        if any(m in display or m == agent_id for m in all_mentions):
            if p.get('role') != 'observer':
                selected.append(p)
                matched_any = True
```

### Execution Trace

Input: `"@gpt-5.2-pro do something"`

1. **Line 215**: `mentioned = ['gpt']` (stops at hyphen) ⚠️
2. **Line 217**: `mentioned_models = ['gpt-5.2-pro']` ✅
3. **Line 226**: `all_mentions = {'gpt', 'gpt-5.2-pro'}`
4. **Line 227**: For PM participant:
   - `display = "pm (gpt 5.2 codex)"` (lowercased)
   - `agent_id = "pm"`
   - Check: `'gpt' in "pm (gpt 5.2 codex)"` → **TRUE** ✅ (MATCH!)
   - Check: `'gpt-5.2-pro' in "pm (gpt 5.2 codex)"` → FALSE
   - **Result**: PM matches because of substring 'gpt' in display_name

### Why Phase 80.27 Check Doesn't Stop It

Lines 236-241:
```python
if selected:
    logger.info(f"[GroupChat] Selected by @mention: {[p.get('display_name') for p in selected]}")
    return selected  # RETURNS EARLY before Phase 80.27 check!

# Phase 80.27: If @mention exists but NOT found in participants...
if mentioned_models or mentioned:
    logger.info(f"[GroupChat] Phase 80.27: @mention '{mentioned or mentioned_models}' not in participants")
    return []  # This check NEVER RUNS because we already returned above!
```

**The problem**: Phase 80.27 only triggers if `selected` is empty. But PM was already selected due to substring match, so we return early.

---

## Why This Happens

**Substring matching in Line 227**:
```python
if any(m in display or m == agent_id for m in all_mentions):
```

This checks:
- `m in display` → substring match (WRONG for model IDs)
- `m == agent_id` → exact match (OK for agent IDs)

For model/display names:
- `'gpt'` in `"PM (GPT 5.2 Codex)"` = TRUE (accidental match)
- Should be: `'gpt-5.2-pro'` exact match only

---

## The Fix

### Option 1: Remove Broken Line 215 Regex ✅ RECOMMENDED

**Problem with Line 215**: It's designed for simple agent names like `@architect`, `@rust_dev`. But it breaks on model IDs with hyphens/dots.

**Line 547** (`parse_mentions`) already handles this correctly and is used in `send_message()`.

**Solution**: Replace Line 215-217 with Line 547's regex:

```python
# OLD (Lines 215-217):
mentioned = re.findall(r'@(\w+)', content)                                          # BROKEN
mentioned_models = re.findall(r'@([\w\-\.]+(?:/[\w\-\.]+)?(?::[\w\-\.]+)?)', content)

# NEW (unified):
all_mention_strings = re.findall(r'@([\w\-.:\/]+)', content)
```

Then:
```python
if all_mention_strings:
    selected = []
    for pid, p in participants.items():
        display = p.get('display_name', '').lower()
        agent_id = p.get('agent_id', '').lower().lstrip('@')

        for mention in all_mention_strings:
            mention_lower = mention.lower()
            # Exact matches only (no substring matching for model IDs)
            if mention_lower == agent_id or mention_lower == display:
                if p.get('role') != 'observer':
                    selected.append(p)
                    break
```

### Option 2: Distinguish Simple Mentions from Model IDs

Separate logic for agent names vs model IDs:

```python
# Simple agent @mentions (original agent_id names)
simple_mentions = re.findall(r'@(\w+)', content)

# Full model/agent IDs (with hyphens/dots/slashes/colons)
full_mentions = re.findall(r'@([\w\-.:\/]+)', content)

if simple_mentions or full_mentions:
    # For simple mentions: use substring match (backward compatible)
    # For full mentions: use exact match (Phase 80.27 compliant)
```

---

## Test Cases

| Input | Expected | Current | Status |
|-------|----------|---------|--------|
| `@gpt-5.2-pro` | Only MCP responds | PM + MCP respond | ❌ BROKEN |
| `@architect` | Only Architect | Only Architect | ✅ OK |
| `@PM` | Only PM | Only PM | ✅ OK |
| `@dev` | Only Dev | Only Dev | ✅ OK |
| `@deepseek/deepseek-r1` | Only MCP | PM responds | ❌ BROKEN |
| `@nvidia/nemotron:free` | Only MCP | Depends on display | ❌ RISKY |

---

## Affected Code Locations

| File | Lines | Issue |
|------|-------|-------|
| `src/services/group_chat_manager.py` | 215 | Broken regex for model IDs |
| `src/services/group_chat_manager.py` | 217 | Correct regex exists but not used alone |
| `src/services/group_chat_manager.py` | 226-227 | Substring matching logic |
| `src/services/group_chat_manager.py` | 232-234 | Early return prevents Phase 80.27 check |

---

## Phase 80.27 Status

**Attempted Fix**: Lines 217 + 236-241

**What it tried**: Detect MCP model mentions and skip default selection if not found in participants.

**Why it fails**: Substring match at Line 227 catches PM before Phase 80.27 check runs.

**Result**: Phase 80.27 is ineffective due to this bug.

---

## Recommendation

**Priority**: HIGH (affects agent routing)

**Fix**: Replace Lines 215-217 with unified regex from Line 547, implement exact matching for model IDs, keep substring matching for simple agent names for backward compatibility.

**Testing**: Add unit tests for:
- `@gpt-5.2-pro` → only MCP response
- `@deepseek/deepseek-r1` → only MCP response
- `@architect` → only Architect response
- `@PM` → only PM response

---

**Marker**: HAIKU_SCOUT_GPT_PM_CONFLICT ✅ Investigation Complete
