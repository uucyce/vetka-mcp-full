# MARKER_GIT_AUTO_PUSH - Quick Reference

## Overview
Marker tracking auto-push functionality added to GitCommitTool in Phase 106/107.

## Marker Locations

### 1. Schema Parameter Definition
**File:** `src/mcp/tools/git_tool.py`
**Line:** 131
**Context:** GitCommitTool.schema property

```python
"auto_push": {
    "type": "boolean",
    "default": False,
    "description": "Auto-push to remote after successful commit (MARKER_GIT_AUTO_PUSH)"
}
```

### 2. Argument Extraction
**File:** `src/mcp/tools/git_tool.py`
**Line:** 156
**Context:** GitCommitTool.execute() method

```python
auto_push = arguments.get("auto_push", False)  # MARKER_GIT_AUTO_PUSH: Auto-push after commit
```

### 3. Push Execution Logic
**File:** `src/mcp/tools/git_tool.py`
**Line:** 223
**Context:** Post-commit push conditional

```python
# MARKER_GIT_AUTO_PUSH: Auto-push to remote if requested
if auto_push:
    push_result = self._git_push()
    if push_result["success"]:
        result_data["status"] = "committed_and_pushed"
        result_data["push"] = push_result["result"]
    else:
        result_data["push_error"] = push_result["error"]
        result_data["status"] = "committed_push_failed"
```

### 4. Helper Method Definition
**File:** `src/mcp/tools/git_tool.py`
**Line:** 244
**Context:** Private helper method for git push

```python
def _git_push(self, remote: str = "origin", branch: str = None) -> Dict[str, Any]:
    """
    MARKER_GIT_AUTO_PUSH: Push commits to remote repository.

    Helper method for auto-push after commit.
    Returns dict with success, result, and error.
    """
```

## Marker Search Command

Find all auto-push markers:
```bash
grep -n "MARKER_GIT_AUTO_PUSH" src/mcp/tools/git_tool.py
```

Expected output:
```
131:    "description": "Auto-push to remote after successful commit (MARKER_GIT_AUTO_PUSH)"
156:    auto_push = arguments.get("auto_push", False)  # MARKER_GIT_AUTO_PUSH: Auto-push after commit
223:            # MARKER_GIT_AUTO_PUSH: Auto-push to remote if requested
246:        MARKER_GIT_AUTO_PUSH: Push commits to remote repository.
```

## Implementation Details

### Parameters
- **auto_push** (boolean): Enable automatic push after commit
  - Default: `false`
  - Requires: `dry_run=false`

### Return Statuses
- `"committed"`: Commit successful, no push
- `"committed_and_pushed"`: Both commit and push successful
- `"committed_push_failed"`: Commit successful, push failed

### Helper Method: _git_push()
- Auto-detects current branch
- 60-second timeout for push operation
- Returns structured result with remote/branch info
- Handles SSH authentication errors gracefully

## Usage

### Without Auto-Push (Default)
```python
{
    "message": "Fix bug in cache.py",
    "dry_run": false
}
```

### With Auto-Push
```python
{
    "message": "Fix bug in cache.py",
    "dry_run": false,
    "auto_push": true
}
```

## Related Files

- **Implementation:** `src/mcp/tools/git_tool.py`
- **Documentation:** `docs/VETKA_GIT_AUTO_PUSH_RESEARCH.md`
- **Reference:** `scripts/update_project_digest.py` (existing push patterns)

## Phase Info
- **Phase:** 106/107
- **Status:** Active
- **Depends:** git, subprocess, pathlib
- **Used By:** MCP server, vetka_git_commit tool

