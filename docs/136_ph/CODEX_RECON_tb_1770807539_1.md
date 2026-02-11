# MARKER_136.RECON_AUTOCLOSE_COMMIT

# Recon: tb_1770807539_1 (Auto-close tasks on git commit)
Date: 2026-02-11

## Current state
- `vetka_git_commit` handler in `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/mcp/vetka_mcp_bridge.py` calls `GitCommitTool.execute()`.
- `GitCommitTool.execute()` in `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/mcp/tools/git_tool.py` already runs post-commit hook:
  - `_auto_complete_tasks(commit_hash, message)`
  - delegates to `TaskBoard.auto_complete_by_commit(...)`.

## Found gap (bug/risk)
- `TaskBoard.auto_complete_by_commit()` currently limits eligible tasks to statuses `claimed` and `running`.
- Task requirement says: if commit message contains `tb_XXXX_Y`, task should auto-close.
- With current logic, task IDs in `pending`/`queued` will not auto-close even with direct match in commit message.

## Fix plan
1. Keep existing `vetka_git_commit -> GitCommitTool -> TaskBoard` flow (no duplication).
2. Expand eligible statuses in `TaskBoard.auto_complete_by_commit()` to include `pending` and `queued`.
3. Add focused tests for pending/queued auto-close behavior.

## Marker plan
- Code marker: `MARKER_136.AUTO_CLOSE_COMMIT`
- Test marker: `MARKER_136.TEST_AUTO_CLOSE_COMMIT`
