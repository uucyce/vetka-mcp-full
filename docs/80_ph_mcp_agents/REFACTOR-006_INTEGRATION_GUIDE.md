# REFACTOR-006: MentionHandler Integration Guide

**For Phase 4 Integration into user_message_handler.py**

## Current Status
- ✅ MentionHandler extracted (Phase 3 complete)
- ⏳ Integration into user_message_handler.py (Phase 4 pending)

## Files Created
```
src/api/handlers/mention/
├── __init__.py               # Public API exports
└── mention_handler.py        # MentionHandler implementation (484 lines)

docs/80_ph_mcp_agents/
└── PHASE3_REFACTOR_MENTION.md  # Documentation
```

## Integration Steps for Phase 4

### 1. Add Import to user_message_handler.py
Add after line 54 (after `from src.agents.agentic_tools import parse_mentions`):

```python
# Phase REFACTOR-006: Extracted mention handler
from src.api.handlers.mention import MentionHandler
```

### 2. Instantiate Handler
Add inside `register_user_message_handler()` function (around line 140):

```python
# Phase REFACTOR-006: Initialize mention handler
mention_handler = MentionHandler(sio)
```

### 3. Replace Lines 603-891
Replace the entire @mention handling section with:

```python
# ========================================
# PHASE J-K: @MENTION PARSING (REFACTORED)
# ========================================
parsed_mentions = mention_handler.parse_mentions(text)
clean_text = parsed_mentions['clean_message']

# Handle @mention direct model calls
mention_handled = await mention_handler.handle_mention_call(
    sid=sid,
    data=data,
    parsed=parsed_mentions
)

if mention_handled:
    # Early return - @mention was processed directly
    return
```

### 4. Remove Old Code
Delete lines 603-891 from original file (288 lines):
- Delete from: `# PHASE J-K: @MENTION PARSING` (line 603)
- Delete to: Just before `# Phase H: Save user message` (line 891)

### 5. Update Line References
After deletion, line numbers will shift. Update any comments that reference line numbers.

## Verification Checklist

After integration:
- [ ] Code compiles without syntax errors
- [ ] @mention parsing still works
- [ ] Direct Ollama calls work (@ollama:model)
- [ ] Direct OpenRouter calls work (@model-name)
- [ ] Tool calls work with Ollama models
- [ ] Chat history is saved correctly
- [ ] CAM events are emitted
- [ ] Error handling works
- [ ] All tests pass

## Expected Behavior

### Before Integration (Current)
- Lines 603-891 handle @mentions inline
- 288 lines of mixed concerns in user_message_handler.py

### After Integration
- MentionHandler is a separate, testable class
- ~10 lines in user_message_handler.py for @mention handling
- Clean separation of concerns
- Easier to test and maintain

## Rollback Plan

If integration fails:
1. Remove the MentionHandler import
2. Restore lines 603-891 from git history
3. Keep the extracted files for future attempts

Git restore command:
```bash
git checkout HEAD -- src/api/handlers/user_message_handler.py
```

## Testing Commands

After integration:
```bash
# 1. Syntax check
python3 -m py_compile src/api/handlers/user_message_handler.py

# 2. Start server and test @mentions
python3 main.py

# 3. Test cases
# - "@deepseek hello" (alias)
# - "@ollama:qwen2:7b show me main.py" (ollama + tool)
# - "@anthropic/claude-3-haiku summarize" (OpenRouter)
```

## Dependencies Required

All dependencies are already in user_message_handler.py:
- Socket.IO instance (sio)
- All context builders are imported
- All model clients work

No new dependencies needed.

## Next Steps After Integration

1. Run full test suite
2. Verify @mention functionality in UI
3. Update any related documentation
4. Consider extracting other handlers (streaming, workflow)

---

**Ready for Phase 4 integration by next agent.**
