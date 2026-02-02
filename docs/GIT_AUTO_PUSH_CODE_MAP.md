# Git Auto-Push Code Map

## File Structure

```
src/mcp/tools/git_tool.py
├── GitStatusTool (existing)
│   └── No changes
├── GitCommitTool (modified)
│   ├── schema property (MODIFIED - line 110-135)
│   │   └── Added "auto_push" parameter
│   ├── execute() method (MODIFIED - line 152-242)
│   │   ├── Load auto_push flag (line 156)
│   │   ├── Stage files
│   │   ├── Create commit
│   │   ├── NEW: Conditional push logic (line 223-232)
│   │   └── Return result with status
│   └── NEW: _git_push() helper method (line 244-292)
│       ├── Auto-detect branch
│       ├── Execute git push
│       ├── Handle success/failure
│       └── Return structured result
```

## Execution Flow

### With auto_push=false (Default)
```
vetka_git_commit()
    ↓
[dry_run check] → if true: return preview
    ↓
[stage files] → git add
    ↓
[create commit] → git commit -m
    ↓
[get hash] → git rev-parse HEAD
    ↓
[MARKER_GIT_AUTO_PUSH check] → if false: skip push
    ↓
[return] {status: "committed", hash, message}
```

### With auto_push=true
```
vetka_git_commit()
    ↓
[dry_run check] → if true: return preview
    ↓
[stage files] → git add
    ↓
[create commit] → git commit -m
    ↓
[get hash] → git rev-parse HEAD
    ↓
[MARKER_GIT_AUTO_PUSH check] → if true: call _git_push()
    ↓
_git_push()
    ├─ [get branch] → git branch --show-current
    ├─ [push] → git push origin branch
    └─ [return] {success, status, remote, branch, error}
    ↓
[return] {status: "committed_and_pushed" | "committed_push_failed", ...}
```

## Line-by-Line Implementation

### Schema Addition (Lines 128-132)
```python
"auto_push": {
    "type": "boolean",
    "default": False,
    "description": "Auto-push to remote after successful commit (MARKER_GIT_AUTO_PUSH)"
}
```
**Purpose:** Define parameter in tool schema for MCP discovery

### Argument Extraction (Line 156)
```python
auto_push = arguments.get("auto_push", False)  # MARKER_GIT_AUTO_PUSH: Auto-push after commit
```
**Purpose:** Extract flag from incoming request, mark for tracking

### Result Data Structure (Lines 217-221)
```python
result_data = {
    "status": "committed",
    "hash": commit_hash,
    "message": message
}
```
**Purpose:** Base result object that will be augmented if push occurs

### Push Conditional (Lines 223-232)
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
**Purpose:** Execute push after commit if requested, handle results

### Helper Method (Lines 244-292)
```python
def _git_push(self, remote: str = "origin", branch: str = None) -> Dict[str, Any]:
    """
    MARKER_GIT_AUTO_PUSH: Push commits to remote repository.

    Helper method for auto-push after commit.
    Returns dict with success, result, and error.
    """
    # ... implementation
```
**Purpose:** Encapsulate push logic for reusability

## Data Flow

### Request
```json
{
    "message": "Update cache",
    "files": ["src/cache.py"],
    "dry_run": false,
    "auto_push": true
}
```

### Response (Success)
```json
{
    "success": true,
    "result": {
        "status": "committed_and_pushed",
        "hash": "abc1234",
        "message": "Update cache",
        "push": {
            "status": "pushed",
            "remote": "origin",
            "branch": "main"
        }
    },
    "error": null
}
```

### Response (Push Failed)
```json
{
    "success": true,
    "result": {
        "status": "committed_push_failed",
        "hash": "abc1234",
        "message": "Update cache",
        "push_error": "error: failed to push some refs"
    },
    "error": null
}
```

## Search Commands

### Find All Markers
```bash
grep -n "MARKER_GIT_AUTO_PUSH" src/mcp/tools/git_tool.py
```

### Find Push Logic
```bash
grep -n "auto_push" src/mcp/tools/git_tool.py
```

### Find _git_push Method
```bash
grep -n "def _git_push" src/mcp/tools/git_tool.py
```

### Check Syntax
```bash
python3 -m py_compile src/mcp/tools/git_tool.py
```

## Integration Points

### MCP Server
- Tool auto-registered from schema
- No manual tool registration needed
- Parameters discovered via schema property

### Approval System
- `requires_approval = True` (line 138)
- Push execution is part of approved commit
- No separate approval needed for push

### Audit Logging
- Could be enhanced in future phases
- Currently returns push result in response
- Consider audit_logger.py integration

## Related Code References

### Push Pattern Reference
File: `scripts/update_project_digest.py` (lines 242-279)
- Existing `git_push()` function
- Same pattern: get branch → push → handle errors
- Could be unified in future refactoring

### Similar Tools
- `GitStatusTool`: Read-only git operations
- `update_project_digest.py`: Digest commit + push
- Future: `vetka_git_sync()`, `vetka_create_pr()`

## Version Info
- **Phase:** 106/107
- **Status:** Active
- **Last Modified:** 2026-02-02
- **Lines:** 292 (original 224 + 68 additions)

