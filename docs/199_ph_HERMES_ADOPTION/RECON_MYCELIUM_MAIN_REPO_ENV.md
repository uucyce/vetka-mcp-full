# RECON: Add VETKA_MAIN_REPO to Mycelium MCP Config

**Phase:** 199
**Status:** Active
**Owner:** Zeta (Harness)
**Created:** 2026-03-26
**Branch:** claude/harness

---

## Problem

Mycelium MCP server config in `.mcp.json` is missing `VETKA_MAIN_REPO`.
Only the vetka server has it:

```json
"vetka": {
  "env": {
    "VETKA_MAIN_REPO": "/Users/danilagulin/Documents/VETKA_Project/vetka_live_03"
  }
}
```

Mycelium has:
```json
"mycelium": {
  "env": {
    "VETKA_API_URL": "http://localhost:5001",
    "PYTHONPATH": "/Users/danilagulin/Documents/VETKA_Project/vetka_live_03",
    "MYCELIUM_WS_PORT": "8082"
  }
}
```

Without `VETKA_MAIN_REPO`, mycelium tools that need the main repo path
(task_board, git operations, file resolution) must either hardcode it or
rely on PYTHONPATH heuristics.

## Solution

Add `VETKA_MAIN_REPO` to mycelium env in ALL `.mcp.json` files:
- Root: `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/.mcp.json`
- All worktrees: `.claude/worktrees/*/.mcp.json`

## Files to Modify

| File | Change |
|------|--------|
| `.mcp.json` (root) | Add VETKA_MAIN_REPO to mycelium.env |
| `.claude/worktrees/*/.mcp.json` | Same — all worktrees |

## Value

Consistent path resolution. Needed for MAIN_REPO.
