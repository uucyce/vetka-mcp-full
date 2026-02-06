# Phase 115 BUG-3 Fix Summary

**Task:** Fix model_source persistence bug  
**Agent:** Claude Sonnet-4.5 (SONNET-A)  
**Status:** ✓ ANALYSIS COMPLETE, FIX SCRIPT READY  
**Date:** 2026-02-06

## Problem Statement

After server restart, model provider info is lost (e.g., "Grok@POLZA" → "Grok@OpenRouter"). 

**Root cause:** `model_source` (user's explicit choice like "polza_ai", "poe", "xai_direct") is received from frontend but never saved to chat history.

## Solution Overview

Add `"model_source": model_source` field to:
1. **handler_utils.py** - Line 249 (msg_to_save dict) ✓ FIXED via VETKA MCP
2. **user_message_handler.py** - 8 save_chat_message calls ⏳ READY TO FIX

## Files Modified

### 1. handler_utils.py ✓ COMPLETE
- **Status:** Fixed via VETKA MCP
- **Line:** 249
- **Change:** Added `"model_source": message.get("model_source")`
- **Backup:** `.vetka_backups/handler_utils.py.20260206_203142.bak`

### 2. user_message_handler.py ⏳ PENDING
- **Status:** Fix script ready
- **Lines:** 424, 500, 604, 771, 927, 1184, 1249, 2035
- **Tool:** `python3 docs/115_ph/apply_fix.py`

## Fix Locations (user_message_handler.py)

| # | Line | Type | Path | Status |
|---|------|------|------|--------|
| 1 | 424 | USER | Ollama | Ready |
| 2 | 500 | ASSISTANT | Ollama | Ready |
| 3 | 604 | USER | Streaming | Ready |
| 4 | 771 | ASSISTANT | Streaming | Ready |
| 5 | 927 | USER | @mention | Ready |
| 6 | 1184 | ASSISTANT | @mention | Ready |
| 7 | 1249 | USER | Hostess | Ready |
| 8 | 2035 | AGENT | Workflow | Ready |

## Implementation

### Option 1: Python Script (Recommended)
```bash
cd /Users/danilagulin/Documents/VETKA_Project/vetka_live_03
python3 docs/115_ph/apply_fix.py
```

### Option 2: Bash Script
```bash
cd /Users/danilagulin/Documents/VETKA_Project/vetka_live_03
bash docs/115_ph/SONNET_A_IMPLEMENTATION.sh
```

### Option 3: Manual (see SONNET_A_REPORT.md)
Full code examples in `docs/115_ph/SONNET_A_REPORT.md`

## Verification

After applying fix:
```bash
# 1. Check changes
git diff src/api/handlers/

# 2. Count markers (should be 9 total)
grep -c "MARKER_115_BUG3" src/api/handlers/handler_utils.py src/api/handlers/user_message_handler.py

# 3. Test
# - Restart server
# - Send message with model_source="polza_ai"
# - Check data/chat_history.json
# - Restart again and verify persistence
```

## Risk Assessment

**Risk Level:** LOW
- Only adding optional field to existing dicts
- Backwards compatible
- No refactoring of other code
- Variable in scope for all locations

## Deliverables

1. ✓ **SONNET_A_REPORT.md** - Detailed analysis with all code examples
2. ✓ **apply_fix.py** - Python script to apply all fixes
3. ✓ **SONNET_A_IMPLEMENTATION.sh** - Bash alternative
4. ✓ **SONNET_A_SUMMARY.md** - This file
5. ✓ **handler_utils.py** - Fixed (backup created)

## Next Steps

1. Run: `python3 docs/115_ph/apply_fix.py`
2. Review: `git diff src/api/handlers/`
3. Test with server restart
4. Commit if tests pass

## Notes

- All locations verified by reading file contents
- model_source variable is in scope (line 249)
- Consistent marker comment used: `# MARKER_115_BUG3: model_source persistence`
- One special case (workflow path) uses `resp.get("model_source", model_source)` fallback

---
**Agent:** SONNET-A (Claude Sonnet-4.5)  
**Phase:** 115  
**Bug:** BUG-3  
**Status:** READY FOR DEPLOYMENT
