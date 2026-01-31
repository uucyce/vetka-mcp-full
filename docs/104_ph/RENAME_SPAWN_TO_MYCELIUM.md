# RENAME SPAWN → MYCELIUM Refactoring Map

**Generated**: 2026-01-31
**Status**: AUDIT ONLY - No renaming performed yet
**Scope**: Complete project scope (src/, scripts/, docs/, data/, client/)

---

## Executive Summary

Found **~95 occurrences** of "spawn" terminology across the codebase:
- **Project code** (Python, Rust, Markdown): ~40 relevant instances
- **Data files** (JSON): ~15 references
- **Dependencies** (venv, node_modules): ~40 instances (OUT OF SCOPE)

### Key Findings

1. **Core rename candidates**: 25+ primary targets
2. **Secondary mentions**: 15+ documentation/comment updates
3. **Tool/function names**: 8 core renames
4. **Directory paths**: 2 directories to rename
5. **Risk level**: **MEDIUM** - Widespread use in active pipeline system

---

## Detailed Renaming Map

### A. TOOL & FUNCTION NAMES (HIGH PRIORITY)

| File | Current Name | Type | New Name | Priority | Notes |
|------|------------|------|----------|----------|-------|
| src/mcp/vetka_mcp_bridge.py | `vetka_spawn_pipeline` | Tool | `vetka_mycelium_pipeline` | **HIGH** | MCP tool definition (line 682) |
| src/orchestration/agent_pipeline.py | `spawn_pipeline()` | Function | `mycelium_pipeline()` | **HIGH** | Async function (line 725) |
| src/orchestration/agent_pipeline.py | `stage_spawn_result()` | Function | `stage_mycelium_result()` | **MEDIUM** | In staging_utils.py (line 154) |
| scripts/retro_apply_spawn.py | Filename | Script | `retro_apply_mycelium.py` | **HIGH** | Primary artifact application tool |
| scripts/retro_apply_spawn.py | `apply_spawn_tasks()` | Function | `apply_mycelium_tasks()` | **HIGH** | Line 77 |
| src/utils/staging_utils.py | `apply_spawn_tasks()` | Internal | `apply_mycelium_tasks()` | **MEDIUM** | Line 318 condition check |

### B. VARIABLE NAMES (MEDIUM PRIORITY)

| File | Current Name | Type | New Name | Priority | Context |
|------|------------|------|----------|----------|---------|
| src/utils/staging_utils.py | `spawn` (dict key) | JSON key | `mycelium` | **MEDIUM** | Line 38-39 (staging.json structure) |
| src/utils/staging_utils.py | `spawn` (dict key) | JSON key | `mycelium` | **MEDIUM** | Line 177-179 (data structure) |
| src/utils/staging_utils.py | `spawn` (condition) | Item type | `mycelium` | **MEDIUM** | Line 318 (`item_type == "spawn"`) |
| src/orchestration/agent_pipeline.py | `spawn_output` | Directory | `mycelium_output` | **MEDIUM** | Line 359 (hardcoded path) |
| data/staging.json | `"spawn": {}` | JSON structure | `"mycelium": {}` | **LOW** | Data file (will auto-update with code) |

### C. DIRECTORY PATHS (MEDIUM PRIORITY)

| Current Path | New Path | Priority | Files | Notes |
|--------------|----------|----------|-------|-------|
| `src/spawn_output/` | `src/mycelium_output/` | **MEDIUM** | Dynamic creation | Code path line 359, 373 |
| `data/spawn_staging/` | `data/mycelium_staging/` | **MEDIUM** | Fallback directory | Created on write errors (line 373) |

### D. DOCUMENTATION & COMMENTS (LOW PRIORITY)

| File | Current Text | New Text | Priority | Type |
|------|------------|----------|----------|------|
| docs/103_ph/MYCELIUM_SPAWN_ANALYSIS.md | "MYCELIUM SPAWN ANALYSIS" | "MYCELIUM IMPLEMENTATION OVERVIEW" | **LOW** | Doc title |
| docs/103_ph/MYCELIUM_SPAWN_ANALYSIS.md | Multiple "spawn" mentions (16x) | "mycelium" | **LOW** | Documentation text |
| src/mcp/vetka_mcp_bridge.py | Line 684-685 doc string | Update descriptions | **LOW** | Tool description |
| src/orchestration/agent_pipeline.py | "spawn" in comments | "mycelium" | **LOW** | Code comments |
| src/utils/staging_utils.py | "spawn" in comments/docstrings | "mycelium" | **LOW** | Documentation strings |
| scripts/retro_apply.py | "spawn outputs" references | "mycelium outputs" | **LOW** | CLI help text |

### E. DATA FILE REFERENCES (LOW PRIORITY)

| File | Current Content | New Content | Priority | Notes |
|------|-----------------|-------------|----------|-------|
| data/pipeline_tasks.json | Task descriptions mention "spawn" | Auto-updated | **LOW** | Historical data, no changes needed |
| data/chat_history.json | References to spawn tool calls | Auto-updated | **LOW** | Chat logs, no changes needed |
| data/groups.json | Potential spawn mentions | Auto-updated | **LOW** | Group metadata |

### F. CLIENT-SIDE REFERENCES (LOW PRIORITY)

| File | Current | New | Priority | Reason |
|------|---------|-----|----------|--------|
| client/src-tauri/src/main.rs | spawn terminology | mycelium | **LOW** | Process spawning (native, not our tool) |
| client/src-tauri/src/file_system.rs | spawn in comments | Update | **LOW** | Native process management |
| client/package-lock.json | cross-spawn | KEEP | **N/A** | External dependency, don't change |

---

## Categorized Occurrence List

### HIGH PRIORITY (Must rename for functional correctness)

```python
# 1. Tool Registration (src/mcp/vetka_mcp_bridge.py:682)
Tool(
    name="vetka_spawn_pipeline",  ← RENAME to "vetka_mycelium_pipeline"
    description="Spawn fractal agent pipeline...",  ← Update description
    ...
)

# 2. Tool Handler (src/mcp/vetka_mcp_bridge.py:1300)
elif name == "vetka_spawn_pipeline":  ← Update condition
    ...
    error: f"[MCP] vetka_spawn_pipeline error: {e}"  ← Update log message

# 3. Main Function (src/orchestration/agent_pipeline.py:725)
async def spawn_pipeline(...):  ← RENAME to "mycelium_pipeline"
    """Convenience function for spawning pipelines"""  ← Update docstring

# 4. Script Name (scripts/)
retro_apply_spawn.py  ← RENAME to "retro_apply_mycelium.py"
```

### MEDIUM PRIORITY (Affects data structures and internal APIs)

```python
# 1. Data Structure Keys (src/utils/staging_utils.py:38-39)
return {"version": "1.0", "spawn": {}, "artifacts": {}}
                          ↓
return {"version": "1.0", "mycelium": {}, "artifacts": {}}

# 2. Directory Paths (src/orchestration/agent_pipeline.py:359)
filepath = f"src/spawn_output/{safe_marker}.py"
                  ↓
filepath = f"src/mycelium_output/{safe_marker}.py"

# 3. Item Type Checks (src/utils/staging_utils.py:318)
elif item_type == "spawn":
              ↓
elif item_type == "mycelium":

# 4. Function Calls (src/utils/staging_utils.py:154)
def stage_spawn_result(...):
         ↓
def stage_mycelium_result(...):
```

### LOW PRIORITY (Documentation and comments)

```python
# Comments (multiple files)
# SPAWN STAGING (from pipeline results)  ← Update comment
# MYCELIUM STAGING (from pipeline results)

# Docstrings
"""Stage a spawn subtask result"""
         ↓
"""Stage a mycelium subtask result"""

# CLI Help text (scripts/retro_apply.py)
"Apply spawn outputs to disk"
         ↓
"Apply mycelium outputs to disk"
```

---

## Impact Analysis by File

### 🔴 CRITICAL FILES (Rename required for system function)

1. **src/mcp/vetka_mcp_bridge.py** (Lines: 679-715, 1300-1353)
   - Contains MCP tool registration and handler
   - Impact: High - breaks MCP integration if not updated
   - Changes: 4 locations (tool name, description, handler condition, error message)

2. **src/orchestration/agent_pipeline.py** (Lines: 69-82, 359, 373, 725-750)
   - Core pipeline orchestration
   - Impact: High - function names affect external API
   - Changes: 2 function names + 2 path strings + docstrings

3. **scripts/retro_apply_spawn.py** (Lines: 1-90)
   - Script filename + all references
   - Impact: High - documentation and scripts reference this
   - Changes: Rename file + update all imports

4. **src/utils/staging_utils.py** (Lines: 38-39, 154, 177-179, 318)
   - Staging infrastructure
   - Impact: Medium - data structure keys
   - Changes: Dictionary keys in JSON + type checks + function name

### 🟡 IMPORTANT FILES (Update for consistency)

5. **scripts/retro_apply.py** (Lines: 39-44, 77-110, 182-185, 226-261)
   - Support script for applying artifacts
   - Impact: Medium - user-facing CLI
   - Changes: 8+ occurrences (help text, variable names, function calls)

6. **docs/103_ph/MYCELIUM_SPAWN_ANALYSIS.md** (Lines: 1-738)
   - Analysis document (16+ occurrences)
   - Impact: Low - documentation only
   - Note: Consider keeping "SPAWN" in title as historical reference (e.g., "MYCELIUM Implementation (formerly SPAWN)")

### 🟢 MINOR FILES (For consistency)

7. **src/mcp/stdio_server.py** (Line 6)
   - Comment about spawning MCP server
   - Impact: None - comment only
   - Change: Optional update for consistency

8. **client/src-tauri/src/main.rs** & **src/file_system.rs**
   - References to native process spawning
   - Impact: None - different context (OS-level, not our tool)
   - Recommendation: SKIP (avoid confusion with native OS concept)

---

## Breaking Changes & Migration Path

### What Will Break

1. **MCP Tool calls**: All existing calls to `vetka_spawn_pipeline` will fail
   - Existing: `vetka_spawn_pipeline(task="...", phase_type="build")`
   - New: `vetka_mycelium_pipeline(task="...", phase_type="build")`
   - Impact: Any chat history or saved commands using old tool name

2. **Script references**: Documentation referencing `retro_apply_spawn.py`
   - Impact: User guides, automation scripts

3. **API responses**: Any code parsing responses will see `"mycelium"` instead of `"spawn"`
   - Impact: Integration with other systems relying on JSON structure

### Migration Strategy (Recommended)

**Phase 1: Add compatibility layer** (optional)
```python
# Keep old names as aliases
async def spawn_pipeline(*args, **kwargs):
    """Deprecated: Use mycelium_pipeline instead"""
    logger.warning("spawn_pipeline is deprecated, use mycelium_pipeline")
    return await mycelium_pipeline(*args, **kwargs)
```

**Phase 2: Update core code**
- Rename tool definition
- Rename functions
- Update data structures

**Phase 3: Update documentation**
- Update user guides
- Update examples
- Update comments

**Phase 4: Deprecation period** (optional)
- Keep aliases for 1-2 releases
- Log warnings on old usage
- Remove in major version bump

---

## Detailed Occurrence List

### File: src/mcp/vetka_mcp_bridge.py

| Line | Context | Current | New | Priority |
|------|---------|---------|-----|----------|
| 682 | Tool name | `"vetka_spawn_pipeline"` | `"vetka_mycelium_pipeline"` | **HIGH** |
| 684 | Description start | `"Spawn fractal agent pipeline"` | `"Execute fractal agent pipeline via mycelium"` | **MEDIUM** |
| 709 | Parameter description | `"...retro_apply_spawn.py"` | `"...retro_apply_mycelium.py"` | **MEDIUM** |
| 1300 | Handler condition | `elif name == "vetka_spawn_pipeline":` | `elif name == "vetka_mycelium_pipeline":` | **HIGH** |
| 1334 | Log message | `"Auto-write: ON..."` | Update reference | **MEDIUM** |
| 1350 | Error log | `"[MCP] vetka_spawn_pipeline error:"` | `"[MCP] vetka_mycelium_pipeline error:"` | **MEDIUM** |

### File: src/orchestration/agent_pipeline.py

| Line | Context | Current | New | Priority |
|------|---------|---------|-----|----------|
| 359 | Directory path | `"src/spawn_output/{safe_marker}.py"` | `"src/mycelium_output/{safe_marker}.py"` | **MEDIUM** |
| 373 | Fallback directory | `Path("data/spawn_staging")` | `Path("data/mycelium_staging")` | **MEDIUM** |
| 725 | Function name | `async def spawn_pipeline(` | `async def mycelium_pipeline(` | **HIGH** |
| 738 | Docstring | `"phase_type: ...research...build"` | Update as needed | **LOW** |
| 746 | Example comment | `"result = await spawn_pipeline(...)"` | `"result = await mycelium_pipeline(...)"` | **LOW** |

### File: src/utils/staging_utils.py

| Line | Context | Current | New | Priority |
|------|---------|---------|-----|----------|
| 38 | Default dict | `{"spawn": {}, "artifacts": {}}` | `{"mycelium": {}, "artifacts": {}}` | **MEDIUM** |
| 39 | Default dict | Same as above | Same as above | **MEDIUM** |
| 154 | Function name | `def stage_spawn_result(` | `def stage_mycelium_result(` | **MEDIUM** |
| 160 | Docstring | `"Stage a spawn subtask result"` | `"Stage a mycelium subtask result"` | **LOW** |
| 177 | Dict key access | `data["spawn"] = {}` | `data["mycelium"] = {}` | **MEDIUM** |
| 179 | Dict key assignment | `data["spawn"][task_id]` | `data["mycelium"][task_id]` | **MEDIUM** |
| 183 | Log message | `"Failed to stage spawn:"` | `"Failed to stage mycelium:"` | **LOW** |
| 318 | Type check | `item_type == "spawn"` | `item_type == "mycelium"` | **MEDIUM** |
| 327 | Default marker | `marker=item.get("marker", f"spawn_{i}")` | `marker=item.get("marker", f"mycelium_{i}")` | **LOW** |
| 349 | Docstring | `type='artifact' or type='spawn_output'` | `type='artifact' or type='mycelium_output'` | **LOW** |

### File: scripts/retro_apply_spawn.py

| Line | Context | Current | New | Priority |
|------|---------|---------|-----|----------|
| 1 | Shebang | (same) | (same) | **N/A** |
| 3 | Title comment | `"MARKER_103.4: Retro-apply spawn results"` | `"MARKER_103.4: Retro-apply mycelium results"` | **LOW** |
| 5 | Docstring | `"This script processes existing spawn results"` | `"This script processes existing mycelium results"` | **LOW** |
| 63 | Path | `f"src/spawn_output/{safe_marker}.py"` | `f"src/mycelium_output/{safe_marker}.py"` | **MEDIUM** |
| 82 | Help text | `"Retro-apply spawn results to create files"` | `"Retro-apply mycelium results to create files"` | **LOW** |
| (FILE) | Filename | `retro_apply_spawn.py` | `retro_apply_mycelium.py` | **HIGH** |

### File: scripts/retro_apply.py

| Line | Context | Current | New | Priority |
|------|---------|---------|-----|----------|
| 5 | Docstring | `"Apply staged results (spawn outputs or artifacts)"` | `"Apply staged results (mycelium outputs or artifacts)"` | **LOW** |
| 9 | Example | `"python scripts/retro_apply.py --type spawn --dry-run"` | `"python scripts/retro_apply.py --type mycelium --dry-run"` | **LOW** |
| 12 | Example | `"python scripts/retro_apply.py --type spawn --task-filter"` | `"python scripts/retro_apply.py --type mycelium --task-filter"` | **LOW** |
| 39 | Comment | `"Also support legacy pipeline_tasks.json for spawn"` | `"Also support legacy pipeline_tasks.json for mycelium"` | **LOW** |
| 43 | Function name | `def load_spawn_tasks(` | `def load_mycelium_tasks(` | **MEDIUM** |
| 44 | Docstring | `"""Load spawn tasks from pipeline_tasks.json"""` | `"""Load mycelium tasks from pipeline_tasks.json"""` | **LOW** |
| 77 | Function name | `def apply_spawn_tasks(` | `def apply_mycelium_tasks(` | **MEDIUM** |
| 78 | Docstring | `"""Apply spawn tasks to disk."""` | `"""Apply mycelium tasks to disk."""` | **LOW** |
| 109 | Function call | `apply_staged_item(task, item_type="spawn"` | `apply_staged_item(task, item_type="mycelium"` | **MEDIUM** |
| 182 | CLI choice | `choices=["spawn", "artifacts", "all"]` | `choices=["mycelium", "artifacts", "all"]` | **MEDIUM** |
| 184 | Help text | `"What to apply: spawn outputs, artifacts, or all"` | `"What to apply: mycelium outputs, artifacts, or all"` | **LOW** |
| 226 | Variable | `total_spawn = 0` | `total_mycelium = 0` | **LOW** |
| 230 | Condition | `if args.type in ["spawn", "all"]:` | `if args.type in ["mycelium", "all"]:` | **MEDIUM** |
| 231 | Print | `print("\n📂 Processing Spawn outputs...")` | `print("\n📂 Processing Mycelium outputs...")` | **LOW** |
| 232 | Function call | `spawn_tasks = load_spawn_tasks(` | `mycelium_tasks = load_mycelium_tasks(` | **MEDIUM** |
| 234 | Function call | `total_spawn = apply_spawn_tasks(` | `total_mycelium = apply_mycelium_tasks(` | **MEDIUM** |
| 240 | Print | `print("   No spawn tasks found")` | `print("   No mycelium tasks found")` | **LOW** |
| 255 | Condition | `if args.type in ["spawn", "all"]:` | `if args.type in ["mycelium", "all"]:` | **MEDIUM** |
| 257 | Print | `print(f"   Spawn files {action}: {total_spawn}")` | `print(f"   Mycelium files {action}: {total_mycelium}")` | **LOW** |
| 261 | Print | `print(f"   Total: {total_spawn + total_artifacts}")` | `print(f"   Total: {total_mycelium + total_artifacts}")` | **LOW** |

### File: docs/103_ph/MYCELIUM_SPAWN_ANALYSIS.md

**Note**: This is a comprehensive analysis document. Consider:
1. Keeping filename as-is (title contains context)
2. OR rename to `MYCELIUM_IMPLEMENTATION_OVERVIEW.md`
3. Update title from "MYCELIUM SPAWN ANALYSIS" to "MYCELIUM Implementation Overview"

16+ occurrences of "spawn" used in context of explaining the system. Recommend:
- Title: Keep historical reference or change to implementation focus
- Body: Update "spawn pipeline" → "mycelium pipeline" (4 occurrences)
- Code examples: Update function names to match new naming

---

## Implementation Checklist

### Phase 1: Core Rename (Critical)
- [ ] Rename MCP tool `vetka_spawn_pipeline` → `vetka_mycelium_pipeline` (vetka_mcp_bridge.py)
- [ ] Update MCP handler condition (vetka_mcp_bridge.py:1300)
- [ ] Rename function `spawn_pipeline()` → `mycelium_pipeline()` (agent_pipeline.py)
- [ ] Rename script `retro_apply_spawn.py` → `retro_apply_mycelium.py`
- [ ] Update directory paths: `spawn_output` → `mycelium_output`
- [ ] Update directory paths: `spawn_staging` → `mycelium_staging`

### Phase 2: Data Structure Updates (Important)
- [ ] Update JSON key: `"spawn"` → `"mycelium"` in staging.json (staging_utils.py)
- [ ] Update item type checks: `"spawn"` → `"mycelium"` (staging_utils.py:318)
- [ ] Rename function: `stage_spawn_result()` → `stage_mycelium_result()`
- [ ] Update CLI argument choices (retro_apply.py)
- [ ] Update load/apply function names in retro_apply.py

### Phase 3: Documentation (Important)
- [ ] Update all docstrings referencing spawn
- [ ] Update code comments
- [ ] Update CLI help text
- [ ] Consider renaming/updating MYCELIUM_SPAWN_ANALYSIS.md
- [ ] Update user guides if any

### Phase 4: Testing & Validation
- [ ] Test MCP tool registration
- [ ] Test pipeline execution with new function names
- [ ] Test artifact creation with new directory paths
- [ ] Test retro_apply script with new naming
- [ ] Verify data migration (staging.json compatibility)

---

## Risk Assessment

### 🔴 HIGH RISK AREAS

1. **MCP Tool Integration** - Breaks Claude Desktop / other client integrations
   - Mitigation: Update MCP server simultaneously with client
   - Risk: Partial outage if not coordinated

2. **Script Naming** - User scripts and documentation reference old names
   - Mitigation: Add symlink or alias during transition period
   - Risk: Broken automation scripts

3. **JSON Structure Changes** - Data parsing depends on key names
   - Mitigation: Support both key names during transition
   - Risk: Data loss if migration not careful

### 🟡 MEDIUM RISK AREAS

1. **Function Signature Changes** - Code importing these functions
   - Impact: Limited scope (mostly internal usage)
   - Mitigation: Deprecation warnings before removal

2. **Directory Creation** - Dynamic path generation
   - Impact: Files created in new directories
   - Mitigation: Add migration script to move old files

### 🟢 LOW RISK AREAS

1. **Comments & Documentation** - No functional impact
2. **Variable Names** - Internal usage only
3. **Log Messages** - No code depends on log format

---

## Backward Compatibility Strategy

### Option 1: Soft Deprecation (Recommended)
```python
# Keep old function with deprecation warning
async def spawn_pipeline(*args, **kwargs):
    """DEPRECATED: Use mycelium_pipeline instead"""
    warnings.warn(
        "spawn_pipeline is deprecated, use mycelium_pipeline",
        DeprecationWarning,
        stacklevel=2
    )
    return await mycelium_pipeline(*args, **kwargs)

# Keep old tool name as alias
TOOL_ALIASES = {
    "vetka_spawn_pipeline": "vetka_mycelium_pipeline"  # Auto-forward requests
}
```

### Option 2: Hard Cutover
- Complete rename across all files
- Update documentation
- Note breaking change in release notes
- Provide migration guide

### Option 3: Parallel Implementation
- Introduce new names alongside old ones
- Mark old names as deprecated
- Remove old names in next major version

**Recommendation**: **Option 1** (soft deprecation) for smooth transition

---

## Summary Statistics

| Category | Count | Impact |
|----------|-------|--------|
| **HIGH Priority Renames** | 6 | CRITICAL |
| **MEDIUM Priority Updates** | 18 | IMPORTANT |
| **LOW Priority Updates** | 25+ | DOCUMENTATION |
| **Dependencies (excluded)** | 40+ | NONE (external) |
| **Total Occurrences** | ~95 | DEPENDS ON SCOPE |
| **Affected Files** | 12 | Project scope |
| **Estimated Effort** | 2-3 hours | Full refactor |
| **Risk Level** | MEDIUM | With mitigation |

---

## Appendix: File-by-File Summary

### Critical Path Files (Update in this order)

1. **src/mcp/vetka_mcp_bridge.py** - 6 changes (HIGH priority)
2. **src/orchestration/agent_pipeline.py** - 4 changes (HIGH priority)
3. **scripts/retro_apply_spawn.py** - Rename file + 2 changes (HIGH priority)
4. **src/utils/staging_utils.py** - 8 changes (MEDIUM priority)
5. **scripts/retro_apply.py** - 15 changes (MEDIUM priority)
6. **docs/** - Multiple files (LOW priority, documentation)

### Non-Critical Files (Can skip safely)

- client/src-tauri/src/main.rs - OS-level spawning (different context)
- client/src-tauri/src/file_system.rs - OS-level spawning (different context)
- client/package-lock.json - External dependency (cross-spawn)
- venv_voice/ - External Python packages (excluded)
- node_modules/ - External JavaScript packages (excluded)

---

**End of Report**

Generated by: Spatial Architect Analysis
Date: 2026-01-31
Status: Awaiting manual review and execution

