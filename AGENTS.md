# VETKA Project — Agent Instructions
# This is the MAIN branch generic AGENTS.md.
# Each agent gets a role-specific AGENTS.md in their worktree.
# DO NOT hardcode a specific role here.

## You are on the MAIN branch

If you are reading this, you are NOT in a role-specific worktree.
You need to either:

1. **Open your assigned worktree** — each role has a dedicated worktree directory
2. **Generate a new role** if you don't have one yet:

```bash
scripts/release/add_role.sh --callsign NAME --domain DOMAIN --worktree WORKTREE \
  --tool-type TYPE --model-tier MODEL --role-title "TITLE"
```

## Init (once in correct worktree)
```
1. mcp__vetka__vetka_session_init role=<YourCallsign>
   → returns: role_context, tasks, docs, protocol guards
2. mcp__vetka__vetka_task_board action=notifications role=<YourCallsign>
3. mcp__vetka__vetka_task_board action=ack_notifications role=<YourCallsign>
4. mcp__vetka__vetka_task_board action=list filter_status=pending
5. Claim → Work → action=complete task_id=<id> branch=<your-branch>
```

`action=complete` = auto-stage + commit + close. NEVER raw git commit.

## Registered Roles

Run `vetka_session_init` without role= to see available roles,
or check `data/templates/agent_registry.yaml` for the full list.

## Rules
- NEVER commit directly to main
- NEVER raw `git merge` — use `vetka_task_board action=merge_request`
- Modify ONLY files in your `role_context.owned_paths`
- Commit via `mcp__vetka__vetka_git_commit` with `[task:tb_xxxx]`
