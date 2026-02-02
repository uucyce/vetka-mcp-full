# VETKA Git Auto-Push Research & Implementation
**Date:** 2026-02-02
**Status:** Research Complete - Markers Added
**Problem:** Git commits via MCP don't auto-push to GitHub

---

## PROBLEM STATEMENT

User requirement: "коммит в Vetka = коммит на гит" (commit in Vetka = commit to Git)

Currently:
- `vetka_git_commit` MCP tool creates local commits only
- No automatic push to remote repository
- Manual `git push` required after each commit
- Breaks the principle of "commit = push" workflow

---

## FINDINGS

### 1. Current Git Implementation

**File:** `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/mcp/tools/git_tool.py`

**Current Structure:**
- `GitStatusTool`: Read-only, shows git status (no changes)
- `GitCommitTool`: Creates commits locally, requires approval
- **Missing:** Auto-push functionality in commit workflow

**Current Flow:**
```
execute() → stage files → git commit → return result → STOP
```

### 2. Push Implementation Exists Elsewhere

**File:** `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/scripts/update_project_digest.py`

**Relevant Functions:**
- `git_push(remote="origin", branch=None)` (lines 242-279)
  - Gets current branch automatically
  - Executes `git push remote branch`
  - Returns success/failure with error handling
  - Handles SSH passphrase warnings gracefully

**Key Code Pattern:**
```python
def git_push(remote: str = "origin", branch: str = None) -> bool:
    try:
        if not branch:
            result = subprocess.run(["git", "branch", "--show-current"], ...)
            branch = result.stdout.strip()

        result = subprocess.run(["git", "push", remote, branch], ...)
        if result.returncode == 0:
            print(f"  Git push: {remote}/{branch}")
            return True
        else:
            print(f"  Warning: git push may need manual intervention")
            return False
    except Exception as e:
        print(f"  Warning: git push error: {e}")
        return False
```

### 3. Pre-Commit Hooks Analysis

**Search Results:**
- No `.git/hooks/pre-commit` file found (or not accessible via shell)
- `update_project_digest.py` uses `--commit` and `--push` flags for optional git operations
- No automatic pre-commit hooks currently installed

**Implication:** Project digest updates are currently manual; hooks could be beneficial for future phases.

### 4. Marker Pattern Analysis

**Existing Markers in Codebase:**
- `MARKER-99-03`: Circuit breaker patterns in memory_proxy.py
- `MARKER-99-02`: MGC promotion thresholds in mgc_cache.py
- `MARKER_104_COMPRESSION_FIX`: Compression module renaming
- `MARKER-77-09`: Quality degradation metrics
- `# MARKER_*` format used throughout codebase

**MarkerTool Capabilities:**
- `vetka_add_markers`: Adds @status/@phase/@depends/@used_by markers to files
- `vetka_verify_markers`: Verifies marker coverage
- Supports Python docstrings and JSDoc comments
- Used for version tracking and dependency documentation

---

## SOLUTION IMPLEMENTED

### Changes to git_tool.py

#### 1. Schema Update (Lines 109-135)

Added `auto_push` parameter to GitCommitTool schema:

```python
"auto_push": {
    "type": "boolean",
    "default": False,
    "description": "Auto-push to remote after successful commit (MARKER_GIT_AUTO_PUSH)"
}
```

**Key Design Decision:** Optional parameter with default False for backward compatibility.

#### 2. Execute Method Update (Line 156)

Added auto_push argument extraction with marker:

```python
auto_push = arguments.get("auto_push", False)  # MARKER_GIT_AUTO_PUSH: Auto-push after commit
```

#### 3. Post-Commit Push Logic (Lines 223-232)

After successful commit, conditionally push:

```python
# MARKER_GIT_AUTO_PUSH: Auto-push to remote if requested
if auto_push:
    push_result = self._git_push()
    if push_result["success"]:
        result_data["status"] = "committed_and_pushed"
        result_data["push"] = push_result["result"]
    else:
        # Commit succeeded but push failed
        result_data["push_error"] = push_result["error"]
        result_data["status"] = "committed_push_failed"
```

**Status Values:**
- `"committed"`: No push requested
- `"committed_and_pushed"`: Push successful
- `"committed_push_failed"`: Commit succeeded, push failed (important distinction)

#### 4. Helper Method: _git_push (Lines 244-292)

New private method for git push operations:

```python
def _git_push(self, remote: str = "origin", branch: str = None) -> Dict[str, Any]:
    """
    MARKER_GIT_AUTO_PUSH: Push commits to remote repository.

    Helper method for auto-push after commit.
    Returns dict with success, result, and error.
    """
    # ... implementation
```

**Features:**
- Automatically detects current branch
- 60-second timeout for large pushes
- Returns structured result with remote/branch info
- Handles SSH authentication errors gracefully
- Marks as `"committed_push_failed"` if push fails after successful commit

---

## MARKER LOCATIONS

### MARKER_GIT_AUTO_PUSH Locations:

1. **Schema Definition** (Line 131)
   - In description: `"(MARKER_GIT_AUTO_PUSH)"`
   - Purpose: Documents the auto-push parameter

2. **Argument Extraction** (Line 156)
   - In comment: `# MARKER_GIT_AUTO_PUSH: Auto-push after commit`
   - Purpose: Marks where auto_push flag is loaded

3. **Push Execution** (Line 223)
   - In comment: `# MARKER_GIT_AUTO_PUSH: Auto-push to remote if requested`
   - Purpose: Marks the conditional push logic

4. **Helper Method Definition** (Line 246)
   - In docstring: `MARKER_GIT_AUTO_PUSH: Push commits to remote repository.`
   - Purpose: Identifies the helper function

**Marker Pattern:** Consistent across codebase - used in comments/docstrings for tracking cross-cutting concerns

---

## USAGE EXAMPLES

### Example 1: Commit Only (Default Behavior)
```python
{
    "message": "Fix memory leak in cache",
    "files": ["src/memory/cache.py"],
    "dry_run": false,
    # auto_push not specified, defaults to false
}
```

**Result:**
```json
{
    "success": true,
    "result": {
        "status": "committed",
        "hash": "a1b2c3d4",
        "message": "Fix memory leak in cache"
    }
}
```

### Example 2: Commit and Auto-Push
```python
{
    "message": "Update project digest for Phase 107",
    "files": ["data/project_digest.json"],
    "dry_run": false,
    "auto_push": true
}
```

**Result (Success):**
```json
{
    "success": true,
    "result": {
        "status": "committed_and_pushed",
        "hash": "b2c3d4e5",
        "message": "Update project digest for Phase 107",
        "push": {
            "status": "pushed",
            "remote": "origin",
            "branch": "main"
        }
    }
}
```

**Result (Push Failed):**
```json
{
    "success": true,
    "result": {
        "status": "committed_push_failed",
        "hash": "b2c3d4e5",
        "message": "Update project digest for Phase 107",
        "push_error": "error: failed to push some refs to 'origin'"
    }
}
```

---

## DESIGN DECISIONS

### 1. Optional Parameter
- **Why:** Backward compatibility with existing tools/workflows
- **Default:** `false` to require explicit opt-in
- **Future:** Could be flipped to `true` for "commit = push" philosophy

### 2. Commit Success ≠ Push Success
- **Why:** Distinguishing between local and remote failures is important
- **Implementation:** Even if push fails, commit is preserved
- **Status Value:** `"committed_push_failed"` indicates this condition
- **Approval:** Commit requires approval; push does not need separate approval since it's part of approved commit

### 3. Helper Method Pattern
- **Why:** Reusability and separation of concerns
- **Naming:** `_git_push()` as private method (not exposed via MCP)
- **Return Format:** Matches existing codebase patterns from `update_project_digest.py`

### 4. Branch Detection
- **Why:** Automatic branch detection avoids requiring extra parameters
- **Fallback:** Defaults to "main" if detection fails
- **Timeout:** 60-second timeout prevents hangs on network issues

---

## INTEGRATION POINTS

### MCP Server Registration
The tool is already registered in the MCP server via:
- `vetka_mcp_bridge.py`: Main MCP bridge
- `vetka_mcp_server.py`: Server implementation
- Tool auto-registration from `src/mcp/tools/git_tool.py`

**No additional registration needed** - schema changes are auto-discovered.

### Project Digest Updates
The `update_project_digest.py` script already has push functionality that could:
- Be modified to use the new auto_push parameter
- Or continue using its own push implementation
- Both approaches are compatible

---

## TESTING RECOMMENDATIONS

### Unit Tests Needed:
1. **Auto-push success case**: Commit and push both succeed
2. **Auto-push push-failure case**: Commit succeeds, push fails
3. **Auto-push false case**: Commit succeeds, no push attempt
4. **SSH authentication case**: Push requires SSH passphrase
5. **Network timeout case**: Push times out after 60 seconds

### Integration Tests:
1. Test with actual GitHub remote
2. Test with feature branch vs main branch
3. Test with multiple commits in sequence

---

## FUTURE ENHANCEMENTS

### Phase 107+ Considerations:

1. **Pre-Commit Hooks**
   - Auto-update project_digest.json before commit
   - Run linting/formatting checks
   - Generate changelog entries

2. **Push Options**
   - Custom remote support: `push(remote="upstream")`
   - Force push option: `push_force=true` (dangerous, requires extra approval)
   - Push tags: `push_tags=true`

3. **Workflow Integration**
   - `vetka_git_sync()`: Pull, commit, push in one operation
   - `vetka_create_pr()`: Commit, push, create PR
   - Branch management: `vetka_create_branch()`, `vetka_merge_branch()`

4. **Audit Logging**
   - Track all pushes in audit_logger.py
   - Record who pushed what when
   - Link to MCP request audit trail

---

## SYNTAX VERIFICATION

✓ Python compilation check passed
✓ No syntax errors in modified file
✓ Type hints consistent with codebase

---

## FILES MODIFIED

| File | Changes | Lines |
|------|---------|-------|
| `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/mcp/tools/git_tool.py` | Added auto_push parameter, _git_push() method, push logic | 109-292 |

**Total Added:** ~70 lines (comments, method, logic)
**Total Modified:** Schema property
**Backward Compatibility:** 100% (optional parameter with default false)

---

## CONCLUSION

The VETKA git commit workflow can now support auto-push via the `auto_push` parameter. This enables the "commit in VETKA = commit to GitHub" workflow while maintaining backward compatibility through an optional parameter.

**Key Achievement:** User can now use `vetka_git_commit(message="...", auto_push=true)` to push immediately after commit, fulfilling the requirement: "коммит в Vetka = коммит на гит"

**Marker Location:** `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/mcp/tools/git_tool.py` lines 131, 156, 223, 246

