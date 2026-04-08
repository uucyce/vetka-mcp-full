# Task Board Compliance Guide

**MARKER_210.TASK_BOARD_GUARDRAIL**

This document explains the task board guardrail system and how to work with it.

---

## Overview

The **task board guardrail** enforces that all commits are tied to a claimed task. This ensures:

- ✅ Clear ownership and accountability for all code changes
- ✅ Proper task tracking and metrics
- ✅ Cross-agent coordination visibility
- ✅ QA debrief data collection

---

## How It Works

### Pre-commit Hook (Primary Guard)

When you run `git commit`, the pre-commit hook:

1. **Detects your role** from the branch name
   - Pattern: `claude/{role}-{domain}` or `agent/{role}-{domain}`
   - Example: `claude/wu-harness` → role is `Wu`

2. **Queries task board** for claimed/running tasks
   - Looks for tasks where `assigned_to = Wu` and `status IN ('claimed', 'running')`
   - Must be claimed within the last 4 hours (or started within 8 hours)

3. **Allows or blocks commit**
   - ✅ Found claimed task → commit proceeds
   - ❌ No claimed task → commit rejected with helpful message

### Worktree Behavior

In worktrees, the check is **skipped** because:
- Worktrees are feature branches with their own task context
- The guardrail only runs in the main repository (where `assigned_to` is meaningful)

---

## Getting a Claimed Task

You need to claim a task before committing. Here are the options:

### 1. Claim an Existing Task

List pending high-priority tasks:
```bash
vetka_task_board action=list filter_status=pending priority=1,2 limit=5
```

This shows pending tasks. Claim one:
```bash
vetka_task_board action=claim task_id=tb_1775670715_6783_1
```

### 2. Create a New Task

If there's no suitable pending task:
```bash
vetka_task_board action=add \
  title="Your task title" \
  phase_type=build \
  description="What you're working on" \
  priority=3
```

Then claim it:
```bash
vetka_task_board action=claim task_id=tb_XXXXX
```

### 3. Check Current Tasks

See what you have claimed:
```bash
vetka_task_board action=list filter_status=claimed
```

---

## Common Scenarios

### Scenario 1: You Try to Commit Without a Claimed Task

```bash
$ git commit -m "Fix bug"

❌ Task Board Compliance Check Failed
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
No claimed task found for role: Wu
Branch: claude/wu-harness

Your commits MUST be tied to a claimed task.

Options:
  1. Claim a task:
     vetka_task_board action=claim task_id=tb_XXXXX

  2. View pending tasks:
     vetka_task_board action=list filter_status=pending priority=1,2 limit=5

  3. Create a new task:
     vetka_task_board action=add title="YOUR TASK" phase_type=build

Emergency bypass (⚠️  use sparingly):
  git commit --no-verify
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

**Solution:** Claim a task first
```bash
vetka_task_board action=claim task_id=tb_1775670715_6783_1
git commit -m "Fix bug"  # Now succeeds
```

### Scenario 2: You Have a Claimed Task But Commit Still Fails

This can happen if:
- Your claimed task is **older than 4 hours** and marked as stale
- Your role in the branch name doesn't match your `assigned_to` in task board

**Solution:** Check your claimed tasks
```bash
vetka_task_board action=list filter_status=claimed assigned_to=Wu
```

If no active task found, claim a new one.

### Scenario 3: You're on an Emergency and Need to Bypass

Only use this if you have a **genuine emergency** and plan to update the task afterward:

```bash
git commit --no-verify -m "EMERGENCY: Fix critical bug [task:tb_XXXXX]"
```

⚠️ **WARNING:** This is logged and audited. Use sparingly.

After bypassing:
1. Document what happened in the task's debrief
2. Update the task's status
3. Don't make this a habit

---

## Worktree-Specific Notes

If you're working in a worktree (`.claude/worktrees/musing-wu/`):

```bash
# Worktree commits skip the task board check
# But the parent task board on main still tracks your work
git commit -m "Work on feature"  # No guardrail blocks

# Your task completion/merge uses the main repo's task board
# when you promote the worktree branch to main
```

---

## Troubleshooting

### Q: "Hook not installed" error

**A:** Reinstall the hook:
```bash
bash scripts/hooks/install-hooks.sh
```

### Q: "Role not detected" error

**A:** Check your branch name matches the pattern:
```bash
git branch --show-current
# Should output: claude/wu-harness (or similar)
# Not: fix/my-bug or feature/x
```

If on a non-compliant branch:
```bash
git checkout -b claude/wu-harness  # Create proper branch
git merge -  # Merge previous branch into this one
```

### Q: "Database locked" error

**A:** The task board database is being accessed by another process.
```bash
# Wait a moment and try again
sleep 2
git commit -m "..."

# Or check if a concurrent agent is running
pgrep -f "task_board.py" | wc -l
```

### Q: Emergency bypass was logged — what now?

**A:** Update your task with debrief:
```bash
vetka_task_board action=complete \
  task_id=tb_XXXXX \
  q1_bugs="I bypassed the hook due to production bug X" \
  q2_worked="The quick response prevented customer data loss" \
  q3_idea="We should add a fast-track task approval path"
```

---

## Hook Installation

The hook is automatically installed when:
- You initialize a new VETKA session (`vetka_session_init`)
- You run the installation script manually

To manually install or reinstall:
```bash
bash scripts/hooks/install-hooks.sh
```

To uninstall:
```bash
bash scripts/hooks/install-hooks.sh --uninstall
```

---

## Implementation Details

**Files involved:**
- `.git/hooks/pre-commit` — Main hook script
- `scripts/check_task_board_compliance.py` — Guard check script
- `src/orchestration/task_board.py:check_claimed_task_for_hook()` — Database query

**Marker:** `MARKER_210.TASK_BOARD_GUARDRAIL`

**Related markers:**
- `MARKER_200.NEVER_STAGE` — Blocks generated artifacts
- `MARKER_188.1` — Worktree detection

---

## See Also

- [Task Board Architecture Bible](ARCHITECTURE_TASKBOARD_BIBLE.md)
- [Task Board Manual](TASKBOARD_MANUAL.md)
- [Pre-commit Hook Recon](RECON_TASK_BOARD_GUARDRAIL_2026-04-08.md)
