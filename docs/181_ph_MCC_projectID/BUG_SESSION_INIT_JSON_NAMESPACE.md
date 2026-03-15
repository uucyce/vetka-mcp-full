# BUG: session_init JSON Namespace Shadowing Error

**Status:** IDENTIFIED, NEEDS FIX
**Severity:** HIGH (blocks session initialization)
**Phase:** 181.5
**Date:** 2026-03-15

---

## Problem Statement

`vetka_session_init()` crashes with:
```
❌ Error in session_init: cannot access local variable 'json' where it is not associated with a value
```

### Root Cause Analysis

This is a **Python variable shadowing** issue:

1. **Module-level import** (line 51 in `vetka_mcp_bridge.py`):
   ```python
   import json  # Global module import — works fine
   ```

2. **Async function execution** (line 1675 in `vetka_mcp_bridge.py`):
   ```python
   result = await vetka_session_init(**arguments)
   return [TextContent(type="text", text=json.dumps(result, ...))]  # ❌ FAILS HERE
   ```

3. **The actual bug location**: Somewhere in `vetka_session_init()` or one of its async call chains, a local variable named `json` is being assigned (likely in a try/except or dynamic import block).

4. **Python's name resolution**: Python pre-scans the entire function scope during compilation. If it finds `json = ...` anywhere in the function body, it treats `json` as a LOCAL variable for the entire function, not the global module.

5. **Result**: When the code tries to call `json.dumps()` BEFORE the local `json = ...` assignment happens, Python throws: `UnboundLocalError: cannot access local variable 'json' where it is not associated with a value`

---

## Investigation Checkpoints

### MARKER_181.5.1: Audit json usage in session_tools.py

**File:** `src/mcp/tools/session_tools.py`
**Status:** ✅ CLEAN (no local `json = ...` found)

- Line 38: `import json` ✓
- Line 63: `json.load(f)` ✓
- No shadowing detected in this file

### MARKER_181.5.2: Audit json usage in async call chain

**Suspects (async functions called from session_init):**

1. `_get_viewport_context()` — lines 419-454
   - Status: ✓ CLEAN (no `json` variable)

2. `_get_pinned_files()` — lines 456-502
   - Status: ✓ CLEAN (no `json` variable)

3. `load_project_digest()` — lines 48-78
   - Status: ✓ CLEAN (`json.load()` only)

4. **Async imports & dynamic module loading**
   - Lines 180, 221, 242, 256, 274, 289, 315, 344, 359, 368
   - Each dynamically imports modules (e.g., `from src.memory.jarvis_prompt_enricher import JARVISPromptEnricher`)
   - **⚠️ POTENTIAL ISSUE**: If any of these imports or their execution creates a local variable named `json`, it will shadow the module

### MARKER_181.5.3: Find the hidden json assignment

**Search pattern:**
```python
json = ...  # Not in json={...} parameter form
```

**Locations checked:**
- ❌ Direct `json =` assignments: NONE found in vetka_mcp_bridge.py call_tool()
- ❌ Direct `json =` assignments: NONE found in session_tools.py functions
- ⚠️ **LIKELY CULPRIT**: One of the imported modules (`jarvis_prompt_enricher`, `engram_user_memory`, `build_manifest`, etc.) might be doing `json = ...` at module load time or in a function that gets called

---

## Solution Strategy

### Option A: Immediate Workaround (5 min fix)
**Apply in `vetka_mcp_bridge.py` line 1678:**

Change from:
```python
return [TextContent(type="text", text=json.dumps(result, indent=2, ensure_ascii=False))]
```

To:
```python
import json as json_module  # Explicit alias at function start
return [TextContent(type="text", text=json_module.dumps(result, indent=2, ensure_ascii=False))]
```

**Or use inline**:
```python
import json as _json
return [TextContent(type="text", text=_json.dumps(result, indent=2, ensure_ascii=False))]
```

### Option B: Root Cause Fix (15 min fix)
**Find the actual `json = ...` assignment**:

1. Add debug logging in `session_tools._execute_async()`:
   ```python
   import json as _json
   # Add at line 162 in _execute_async
   logger.info(f"[SessionInit] json module: {_json}, type: {type(_json)}")
   ```

2. Run `vetka_session_init()` again and check logs

3. Once found, either:
   - Rename the offending local variable in the imported module
   - Use `import json as _json` in that module too
   - Use `import importlib; json_module = importlib.import_module('json')`

### Option C: Module-level Defense (10 min fix)
**Add at top of `session_tools.py` after imports:**

```python
# MARKER_181.5.4: Explicit json module reference to prevent shadowing
import json as _json  # Alias to prevent accidental shadowing
```

Then replace all `json.X()` calls with `_json.X()` in the file.

---

## Implementation Plan

### Phase 181.5 Tasks

| Task | File | Change | Time |
|------|------|--------|------|
| **181.5.A** | `vetka_mcp_bridge.py` | Add `_json` alias in `call_tool()` | 5m |
| **181.5.B** | `session_tools.py` | Add `_json` alias, update all calls | 10m |
| **181.5.C** | All imports in `session_tools._execute_async()` | Audit for hidden `json = ...` | 10m |
| **181.5.D** | Test `vetka_session_init()` | Verify fix | 5m |

**Total time: ~30 minutes**

---

## Code Changes

### Change 1: `src/mcp/tools/session_tools.py`

**Line 38** (imports section):
```python
import json as _json  # MARKER_181.5.4: Prevent shadowing in async call chain
```

**All `json.load()` calls** → `_json.load()`:
- Line 63: `digest = json.load(f)` → `digest = _json.load(f)`

### Change 2: `src/mcp/vetka_mcp_bridge.py`

**Line 1678** (session_init result formatting):
```python
# MARKER_181.5.5: Use explicit _json alias to avoid shadowing from session_tools imports
return [TextContent(type="text", text=json.dumps(result, indent=2, ensure_ascii=False))]

# ↓ CHANGE TO:

import json as _json  # At function start or module level
return [TextContent(type="text", text=_json.dumps(result, indent=2, ensure_ascii=False))]
```

Alternatively, add at top of `call_tool()` function (line 1090):
```python
import json as _json  # MARKER_181.5.5: Prevent shadowing from async imports
```

Then replace ALL `json.dumps()` and `json.loads()` in the function:
- Line 1163, 1244, 1272, 1473, 1484, 1678, 1689, 1700, 1718, 1729, 1775

---

## Testing

### Test Case 1: Basic session_init
```bash
# Should return session context instead of error
claude_code
> I need to initialize the session
```

### Test Case 2: Verify json module is available
```python
import sys
from src.mcp.tools.session_tools import SessionInitTool
tool = SessionInitTool()
result = tool.execute({})  # Sync execution
print(result)  # Should show success
```

### Test Case 3: Async execution
```python
import asyncio
from src.mcp.tools.session_tools import vetka_session_init
result = asyncio.run(vetka_session_init())
print(result['success'])  # Should be True
```

---

## Prevention

Add to `.pre-commit` hook:

```bash
# Check for json shadowing in MCP tools
grep -n "^\s*json\s*=" src/mcp/tools/*.py src/mcp/vetka_mcp_bridge.py || true
grep -n "^\s*json\s*=" src/memory/*.py || true  # Check dependent modules
```

---

## References

- **Python Docs:** [UnboundLocalError with variable shadowing](https://docs.python.org/3/faq/programming.html#what-are-local-variables)
- **Related Phases:** 108 (session_init), 129 (MCP scaling), 177 (capability broker)
- **Codex Report:** Phase 180 feedback noted this issue exists pre-dating recent changes
- **Opus Note:** Not caused by task_board_tools.py changes (Phase 178-179)

---

## Status Tracker

- [ ] **181.5.A** — Fix vetka_mcp_bridge.py (json.dumps line 1678)
- [ ] **181.5.B** — Fix session_tools.py (json.load line 63)
- [ ] **181.5.C** — Audit async call chain for hidden assignments
- [ ] **181.5.D** — Test and verify
- [ ] **181.5.E** — Add pre-commit check
- [ ] **181.5.F** — Document in CLAUDE.md as prevention rule
