# VETKA Unused Imports Analysis Report
**Generated:** 2026-01-07
**Analysis Tool:** Python AST with re-export detection
**Files Analyzed:** 191 Python files

---

## Executive Summary

- **Total unused imports found:** 149
- **Files affected:** 77 (40% of codebase)
- **Safe to remove immediately:** ~50 imports
- **Require verification:** ~99 imports
- **Intentional "unused" imports:** ~15 (side-effects, availability checks)

---

## Top Offending Files

### 1. `/src/initialization/dependency_check.py` (12 unused imports)
**Status:** ⚠️ Requires Manual Review

**Unused Imports:**
- Line 16: `from typing import Optional`
- Line 17: `from logging_setup import LOGGER`
- Line 99: `import ollama` ⚠️ **INTENTIONAL** - used for availability check
- Line 106: `import openai` ⚠️ **INTENTIONAL** - used for availability check
- Line 113: `import anthropic` ⚠️ **INTENTIONAL** - used for availability check
- Line 120: `import google.generativeai` ⚠️ **INTENTIONAL** - used for availability check
- Line 285: `from src.agents.pixtral_learner import PixtralLearner` ⚠️ **INTENTIONAL** - triggers @register decorator
- Line 286: `from src.agents.qwen_learner import QwenLearner` ⚠️ **INTENTIONAL** - triggers @register decorator
- Lines 342-345: Factory imports (may be used in modules dict)

**Recommendation:** Add `# noqa: F401` comments to intentional unused imports. Review LOGGER usage.

---

### 2. `/src/orchestration/orchestrator_with_elisya.py` (10 unused imports)
**Status:** ✅ High Priority Cleanup

**Unused Imports:**
```python
Line 31: from src.agents.streaming_agent import StreamingAgent
Line 32: from src.orchestration.progress_tracker import ProgressTracker
Line 34: from src.orchestration.query_dispatcher import RouteStrategy
Line 37: from src.tools import registry
Line 37: from src.tools import PermissionLevel
Line 38: from src.agents.tools import CreateArtifactTool
Line 42: from src.orchestration.chain_context import ChainContext
Line 45: from src.orchestration.response_formatter import format_response
Line 48: from src.elisya.state import ConversationMessage
Line 51: from src.elisya.key_manager import APIKeyRecord
```

**Impact:** Large orchestrator file - removing 10 imports will improve clarity
**Risk:** Low - verified these are not used anywhere in file

---

### 3. `/src/orchestration/agent_orchestrator_parallel.py` (5 unused imports)
**Status:** ✅ Safe to Remove

**Unused Imports:**
```python
Line 12: from typing import Optional, Dict, Any
Line 20: from src.agents.streaming_agent import StreamingAgent
Line 21: from src.orchestration.progress_tracker import ProgressTracker
```

---

### 4. `/src/tools/code_tools.py` (3 unused imports)
**Status:** ✅ Safe to Remove - VERIFIED

**Unused Imports:**
```python
Line 4: import os
Line 5: import asyncio
Line 7: from typing import Optional
```

**Verification:** Searched entire file - no `os.`, `asyncio.`, or `Optional[` usage found.

---

## Common Patterns

### Pattern 1: Unused Typing Imports (18 files affected)
**Most Common:**
- `from typing import Optional` - 18 occurrences
- `from typing import Tuple` - 10 occurrences
- `from typing import Any` - 9 occurrences
- `from typing import List` - 8 occurrences
- `from typing import Dict` - 7 occurrences

**Example Files:**
- `src/elisya/api_gateway.py`
- `src/agents/agentic_tools.py`
- `src/orchestration/feedback_loop_v2.py`
- `src/layout/fan_layout.py`
- Many more...

**Recommendation:** Bulk cleanup opportunity - these are type hints that were never used.

---

### Pattern 2: Unused Standard Library Imports (24 files affected)
**Most Common:**
- `import os` - 9 occurrences
- `import json` - 7 occurrences
- `from datetime import datetime` - 8 occurrences
- `import math` - 3 occurrences
- `import time` - 3 occurrences
- `import asyncio` - 2 occurrences

**Likely Cause:** Copy-paste from templates or refactoring remnants

**Recommendation:** Safe to remove after verification

---

### Pattern 3: Unused Project Imports (Potential Legacy Code)
**Suspicious Patterns:**
- `StreamingAgent` imported but never used (2 files)
- `ProgressTracker` imported but never used (2 files)
- `RouteStrategy` imported but never used (2 files)

**Files:**
- `src/orchestration/orchestrator_with_elisya.py`
- `src/orchestration/agent_orchestrator_parallel.py`

**Recommendation:** Check git history - these may be from previous architecture

---

## Cleanup Priorities

### 🔴 High Priority (High Impact, Low Risk)
1. **`src/orchestration/orchestrator_with_elisya.py`** - 10 unused imports
2. **`src/orchestration/agent_orchestrator_parallel.py`** - 5 unused imports
3. **`src/tools/code_tools.py`** - 3 unused imports (verified safe)

**Estimated Impact:** Remove 18 imports from 3 core files

---

### 🟡 Medium Priority (Bulk Cleanup)
1. **All typing imports** - 18 files with unused `Optional`, `Tuple`, `Any`, etc.
2. **Standard library imports** - 24 files with unused `os`, `json`, `datetime`, etc.

**Estimated Impact:** Remove 50+ imports across codebase

---

### 🟢 Low Priority / Skip
1. **`src/initialization/dependency_check.py`** - Most "unused" imports are intentional
2. **`__init__.py` files** - Already handled with re-export logic (28 files)

---

## Systematic Issues

### Issue 1: Type Hints Imported But Never Used
**Root Cause:** Developers import typing types but don't actually add type annotations

**Solution:**
1. Remove unused typing imports (short-term)
2. Enable stricter type checking with mypy (long-term)
3. Add pre-commit hook to catch unused imports

---

### Issue 2: Copy-Paste from Templates
**Root Cause:** Files created from templates with standard imports that aren't needed

**Solution:**
1. Create leaner file templates
2. Use tools like `autoflake` to auto-remove unused imports
3. Add to pre-commit hooks

---

## Recommended Tools for Ongoing Maintenance

### Option 1: autoflake (Recommended)
```bash
pip install autoflake
autoflake --remove-all-unused-imports --in-place --recursive src/
```

### Option 2: ruff (Modern, Fast)
```bash
pip install ruff
ruff check --select F401 --fix src/
```

### Option 3: flake8 (Detection Only)
```bash
pip install flake8
flake8 --select=F401 src/
```

---

## Action Plan

### Phase 1: Quick Wins (30 minutes)
- [ ] Remove 3 imports from `src/tools/code_tools.py`
- [ ] Remove 10 imports from `src/orchestration/orchestrator_with_elisya.py`
- [ ] Remove 5 imports from `src/orchestration/agent_orchestrator_parallel.py`
- [ ] **Impact:** 18 imports removed, 3 files cleaned

### Phase 2: Typing Cleanup (1 hour)
- [ ] Review and remove unused typing imports from 18 files
- [ ] **Impact:** ~40 imports removed

### Phase 3: Standard Library Cleanup (1 hour)
- [ ] Review and remove unused os/json/datetime imports from 24 files
- [ ] **Impact:** ~30 imports removed

### Phase 4: Add to CI/CD (30 minutes)
- [ ] Install `ruff` or `autoflake`
- [ ] Add pre-commit hook to catch unused imports
- [ ] Add to GitHub Actions workflow

### Phase 5: Documentation (15 minutes)
- [ ] Add `# noqa: F401` comments to intentional unused imports in `dependency_check.py`
- [ ] Document why those imports are needed

---

## Files Reference

### All Files with Unused Imports (77 files)

**Top 20 by Count:**
1. `src/initialization/dependency_check.py` (12)
2. `src/orchestration/orchestrator_with_elisya.py` (10)
3. `src/orchestration/agent_orchestrator_parallel.py` (5)
4. `src/elisya/api_gateway.py` (4)
5. `src/agents/agentic_tools.py` (4)
6. `src/tools/code_tools.py` (3) ✅ VERIFIED SAFE
7. `src/agents/arc_solver_agent.py` (3)
8. `src/initialization/components_init.py` (3)
9. `src/orchestration/cam_engine.py` (3)
10. `src/orchestration/feedback_loop_v2.py` (3)
11-20. Multiple files with 2-3 unused imports each

**See `analyze_unused_imports_v2.py` output for complete list**

---

## Technical Details

### Analysis Method
- **Tool:** Custom Python AST analyzer
- **Features:**
  - Handles `__all__` re-exports
  - Skips `__init__.py` re-export patterns
  - Detects both `import X` and `from X import Y` patterns
  - Tracks attribute access (`module.function`)

### Known Limitations
- Cannot detect string-based imports (`importlib.import_module`)
- Cannot detect type comments (Python 2 style)
- May miss imports used only in `TYPE_CHECKING` blocks
- Cannot detect imports used in f-strings with `{module.attr}`

### False Positives Handled
- ✅ Re-exports in `__init__.py`
- ✅ Names in `__all__`
- ✅ Side-effect imports (with manual review)

---

## Conclusion

The VETKA codebase has **149 unused imports** across **77 files**. Of these:

- **~50 are safe to remove** (verified unused)
- **~99 require verification** (likely unused but need confirmation)
- **~15 are intentional** (side-effects, availability checks)

**Quick wins are available** by cleaning up the top 3 files, which would remove 18 imports with minimal risk.

For long-term maintenance, consider adding **ruff** or **autoflake** to the pre-commit hooks to prevent unused imports from accumulating.

---

**Generated by:** Python AST analysis script
**Contact:** See `analyze_unused_imports_v2.py` for reproduction
**Data:** See `unused_imports_report.json` for machine-readable format
