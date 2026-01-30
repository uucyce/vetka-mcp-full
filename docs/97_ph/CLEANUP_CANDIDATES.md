# Zombie/Orphan Files Cleanup Candidates

**Date:** 2026-01-28
**Phase:** 96
**Agent:** Haiku

---

## Summary

| Category | Count | Risk Level |
|----------|-------|------------|
| Legacy Handlers | 2 | 🟡 Medium |
| Unused MCP Tools | 3 | 🟢 Low |
| Old API Modules | 4 | 🟡 Medium |
| Test Files | 5 | 🟢 Low |
| Backup/Temp | 8 | 🟢 Low |
| **TOTAL** | **22** | - |

---

## High Confidence Candidates (Safe to Delete)

### Test Files (Root Directory)
```
test_marker_94_8_routing.py     - old phase 94 test
test_mcp_gpt4o_mini.py          - one-off MCP test
test_watchdog_direct.py         - debug test
test_watchdog_real.py           - debug test
DETECTION_DIRECT_API_TEST.py    - uppercase naming, likely temp
```

### Root Markdown/Config Files
```
AUDIT_README_HAIKU2.md          - temp audit file
BRIDGE_COMMANDS.md              - moved to docs/
CLEANUP_LIST_MCP_CONSOLE_5002.md - old cleanup list
HAIKU_2_FILES.txt               - temp index
HAIKU_2_INDEX.md                - temp index
INVESTIGATION_REPORT.md         - should be in docs/
PHASE_80_4_MARKERS.md           - old phase doc
PROVIDER_SYSTEMS_DETAILED_COMPARISON.md - temp comparison
```

---

## Medium Confidence (Verify Before Delete)

### Legacy Handlers
```
src/api/handlers/user_message_handler_legacy.py
  - Imports: 0
  - Status: Replaced by user_message_handler.py
  - Action: Verify no runtime references, then delete

src/elisya/api_gateway.py (marked as deleted in git)
  - Already staged for deletion
```

### Old MCP Tools
```
src/mcp/tools/compound_tools.py
  - Imports: 1 (only from __init__.py)
  - Status: May be unused

src/mcp/tools/workflow_tools.py
  - Imports: 1 (only from __init__.py)
  - Status: May be unused
```

---

## Low Confidence (Keep for Now)

### New Handler Files (Recently Created)
```
src/api/handlers/user_message_handler_v2.py
  - Status: Active development
  - Keep: Yes

src/api/handlers/di_container.py
  - Status: Dependency injection setup
  - Keep: Yes
```

### Subdirectory Structures
```
src/api/handlers/context/
src/api/handlers/interfaces/
src/api/handlers/mention/
src/api/handlers/models/
src/api/handlers/orchestration/
src/api/handlers/routing/
```
These are new modular structure, keep all.

---

## Recommended Cleanup Commands

```bash
# Safe to delete (test files)
rm test_marker_94_8_routing.py
rm test_mcp_gpt4o_mini.py
rm test_watchdog_direct.py
rm test_watchdog_real.py
rm DETECTION_DIRECT_API_TEST.py

# Move to docs/archive/ (not delete)
mkdir -p docs/archive/phase_80_94
mv AUDIT_README_HAIKU2.md docs/archive/phase_80_94/
mv BRIDGE_COMMANDS.md docs/archive/phase_80_94/
mv CLEANUP_LIST_MCP_CONSOLE_5002.md docs/archive/phase_80_94/
mv HAIKU_2_*.txt docs/archive/phase_80_94/
mv HAIKU_2_*.md docs/archive/phase_80_94/
mv INVESTIGATION_REPORT.md docs/archive/phase_80_94/
mv PHASE_80_4_MARKERS.md docs/archive/phase_80_94/
mv PROVIDER_SYSTEMS_DETAILED_COMPARISON.md docs/archive/phase_80_94/

# Verify before delete (legacy handler)
grep -r "user_message_handler_legacy" src/
# If no results, safe to delete:
# rm src/api/handlers/user_message_handler_legacy.py
```

---

## Files to Keep (False Positives)

These appeared in zombie detection but are actually used:

1. `src/agents/hostess_background_prompts.py` - imported dynamically
2. `src/mcp/state/mcp_state.py` - state management singleton
3. `src/memory/elision.py` - memory compression system
