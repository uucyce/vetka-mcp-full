# Phase 90.1.3: Fix Reply Routing Case-Sensitivity

**Date:** 2026-01-23
**Status:** ✅ COMPLETED
**File Modified:** `src/services/group_chat_manager.py`

## Problem
Reply routing to specific model in group chat was failing due to case-sensitive comparison:
- User replies to `@Grok` (capitalized)
- System compares `"@grok"` (lowercase) with `"@Grok"` (capitalized)
- Comparison fails → triggers fallback to Architect instead

## Root Cause
**Lines 198-207** in `select_responding_agents()`:
```python
# OLD CODE (case-sensitive):
if reply_to_agent:
    for pid, p in participants.items():
        agent_id = p.get('agent_id', '')
        # Match by agent_id (with or without @)
        if agent_id == reply_to_agent or agent_id == f"@{reply_to_agent}" or f"@{agent_id.lstrip('@')}" == reply_to_agent:
```

## Solution
**Lines 198-212** after fix (case-insensitive):
```python
# NEW CODE (normalized):
if reply_to_agent:
    # MARKER_90.1.3_START: Fix case-sensitive agent matching
    reply_to_normalized = reply_to_agent.lower().lstrip('@') if reply_to_agent else ''
    for pid, p in participants.items():
        agent_id = p.get('agent_id', '')
        agent_id_normalized = agent_id.lower().lstrip('@') if agent_id else ''
        # Match by normalized agent_id (case-insensitive)
        if agent_id_normalized == reply_to_normalized:
    # MARKER_90.1.3_END
```

## Changes
1. **Normalize both sides** before comparison:
   - `reply_to_agent` → `reply_to_normalized` (lowercase, no @)
   - `agent_id` → `agent_id_normalized` (lowercase, no @)
2. **Single clean comparison** instead of 3 messy conditions
3. **Handles all cases:**
   - `@Grok` vs `@grok` → ✅ match
   - `Grok` vs `@grok` → ✅ match
   - `@GROK` vs `@grok` → ✅ match

## Test Cases
| Input | Stored Agent ID | Result |
|-------|----------------|--------|
| `@Grok` | `@grok` | ✅ Match |
| `@grok` | `@Grok` | ✅ Match |
| `Grok` | `@grok` | ✅ Match |
| `@architect` | `@Architect` | ✅ Match |

## Impact
- **User Experience:** Reply routing now works regardless of capitalization
- **Backend:** Clean normalization logic, easier to debug
- **Future:** Pattern can be reused for other agent ID comparisons

## Markers
- `MARKER_90.1.3_START` → Line 200
- `MARKER_90.1.3_END` → Line 209
