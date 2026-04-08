# RECON: Task Board Guardrail — Pre-commit Hook vs MCP Tool Guard

**Date:** 2026-04-08  
**Task ID:** `tb_1775672178_6783_1`  
**Domain:** harness  
**Phase:** 210 (WAKE-LITE-2 cycle)

---

## Problem Statement

**Current Issue:** Agents frequently commit code without claiming tasks on the task board.

**Evidence:**
- Query: `SELECT COUNT(*) FROM tasks WHERE assigned_to = ''` → **579 tasks** with no assigned_to
- Pattern: Agents work, commit [task:tb_*] in message, but never go through `vetka_task_board action=claim`
- Root cause: No enforcement mechanism — commitment is voluntary, can be forgotten

**Risk:**
- Task board loses tracking of actual work distribution
- Cross-agent coordination breaks (no owner visibility)
- QA metrics become unreliable (debrief data sparse)
- Task dependency chains break

---

## Evaluation: Three Guardrail Options

### Option 1: Pre-commit Hook ✅ RECOMMENDED
**Location:** `.git/hooks/pre-commit`

**Current State:**
- Hook exists at `scripts/hooks/pre-commit`
- Currently only:
  - Blocks generated artifacts (`CLAUDE.md`, `.agent_lock`)
  - Updates project digest
  - Handles worktree detection
- **Does NOT** check claimed tasks

**Proposed Logic:**
```bash
1. Extract role from git branch (claude/{callsign}-{domain})
2. Query task_board for claimed task:
   SELECT id FROM tasks 
   WHERE assigned_to = {role}
     AND status IN ('claimed', 'running')
     AND started_at > NOW() - INTERVAL 4 HOURS
3. If NO claimed task found:
   → Print error message (see below)
   → exit 1 (reject commit)
4. If claimed task found:
   → exit 0 (allow commit)
```

**Error Message:**
```
❌ Task Board Compliance Check Failed
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
No claimed task found for role: Wu (branch: agent/wu-harness)

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

Docs: https://docs/200_taskboard_forever/TASK_BOARD_COMPLIANCE.md
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

**Pros:**
- ✅ Works independently — doesn't depend on agent behavior
- ✅ Can't be bypassed accidentally — only via `--no-verify`
- ✅ Catches mistakes before they reach repository
- ✅ Simple shell script (fast, no Python dependencies)
- ✅ Works in main repo AND worktrees

**Cons:**
- ⚠️ Requires shell integration (`install_hooks.sh` for CI/developers)
- ⚠️ Needs worktree-aware branch parsing (not all branches follow convention)
- ⚠️ Time window for "claimed task" is fuzzy (4h? 24h?)
- ⚠️ False positives possible (stale claimed task from previous agent)

**Implementation Effort:** ~3h (hook logic + install script + docs)

---

### Option 2: MCP Tool Guard
**Location:** `vetka_edit_file`, `vetka_git_commit`

**Proposed Logic:**
```python
# In vetka_git_commit.execute() at line 180:
def execute(self, arguments):
    role = os.environ.get('VETKA_AGENT_ROLE')
    if not role:
        return {"success": False, "error": "VETKA_AGENT_ROLE not set"}
    
    # Query task board for claimed task
    tb = get_task_board()
    claimed = tb.get_claimed_tasks_for_role(role)
    
    if not claimed:
        return {
            "success": False,
            "error": f"❌ No claimed task for role {role}. Use: "
                     f"vetka_task_board action=claim task_id=tb_XXXXX"
        }
    
    # Proceed with commit logic...
```

**Pros:**
- ✅ UX-friendly with actionable error message
- ✅ Works within MCP ecosystem (no shell scripting)
- ✅ Can provide context (e.g., suggest top 3 pending high-priority tasks)
- ✅ Easier to test in unit tests

**Cons:**
- ❌ Only triggers when MCP tool is used (agent could use raw `git commit`)
- ❌ Requires ENV variable setup (`VETKA_AGENT_ROLE`)
- ❌ Multiple tools to update (`vetka_git_commit`, `vetka_edit_file`)
- ❌ Can be bypassed: `git commit` directly, or `git reset HEAD && git commit --no-verify`
- ❌ Depends on agent following MCP pattern (not enforced)

**Implementation Effort:** ~2h (modify 2 tools, add test cases)

---

### Option 3: Soft Guard at session_init
**Location:** `vetka_session_init` (VETKA MCP)

**Proposed Logic:**
```python
def session_init(role=None):
    ...
    
    claimed_task = tb.get_claimed_tasks_for_role(role)
    if not claimed_task:
        ps.no_task_claimed = true  # Flag in protocol status
        next_steps.append(
            "⚠️  No claimed task found. "
            "Start with: vetka_task_board action=claim task_id=TB_ID"
        )
    ...
```

**Pros:**
- ✅ Non-blocking (informative, not enforcing)
- ✅ Gentle nudge, not punitive
- ✅ Easy to implement
- ✅ Good for awareness-building

**Cons:**
- ❌ Doesn't prevent anything — only warns at session start
- ❌ Agent can ignore warning and proceed anyway
- ❌ Only fires once per session (not per commit)
- ❌ Doesn't help agents who forget mid-session

**Implementation Effort:** ~1h (add flag logic + next_steps)

---

## Comparative Analysis

| Factor | Pre-commit Hook | MCP Guard | Soft Guard |
|--------|-----------------|-----------|-----------|
| **Enforcement** | ✅ Hard block | ⚠️ Soft (can bypass) | ❌ None |
| **Coverage** | ✅ 100% commits | ❌ Only MCP calls | ❌ Only session start |
| **UX** | ⚠️ Blocks workflow | ✅ Integrated msg | ✅ Informational |
| **Reliability** | ✅ High | ⚠️ Medium | ❌ Low |
| **Difficulty** | ⚠️ Medium | ✅ Easy | ✅ Easy |
| **False Positives** | ⚠️ Possible | ✅ Low | N/A |
| **Can Bypass** | `--no-verify` | raw `git` | ignore warning |
| **Time to Implement** | 3h | 2h | 1h |

---

## Hybrid Recommendation

**Best combination:** Pre-commit hook (primary) + MCP guard (secondary) + soft guard (awareness)

**Rationale:**
1. **Pre-commit hook** = hard guarantee (prevents 95% of cases)
2. **MCP guard** = catches MCP-only workflows with clear feedback
3. **Soft guard** = awareness for agents doing session_init

**Rollout:**
- Phase 1 (Week 1): Pre-commit hook + install script
- Phase 2 (Week 2): MCP guard in `vetka_git_commit`
- Phase 3 (Week 3): Soft guard + metrics dashboard

---

## Technical Details

### Branch Parsing Strategy
```bash
# Extract role from branch name
# Patterns supported:
#   claude/{callsign}-{domain}      (Wu-harness)
#   agent/{callsign}-{domain}       (Codex-parallax)
#   {callsign}/{branch-name}         (ws/feature-x)

BRANCH=$(git rev-parse --abbrev-ref HEAD)
ROLE=$(echo "$BRANCH" | sed -E 's/^(claude|agent)\/([^-]+)-.*/\2/' | tr a-z A-Z)
```

### Task Query Strategy
```sql
-- Find claimed task for role, excluding stale entries
SELECT id, title, status FROM tasks 
WHERE assigned_to = ?
  AND status IN ('claimed', 'running')
  AND (
    -- Task claimed within last 4 hours (fresh)
    (assigned_at IS NOT NULL AND datetime(assigned_at) > datetime('now', '-4 hours'))
    OR
    -- Task still in progress (started recently)
    (started_at IS NOT NULL AND datetime(started_at) > datetime('now', '-8 hours'))
  )
LIMIT 1
```

### Worktree Handling
Pre-commit hook must detect and skip in worktrees (commit on branch, not main):
```bash
GIT_DIR=$(git rev-parse --git-dir)
GIT_COMMON=$(git rev-parse --git-common-dir)
if [ "$GIT_DIR" != "$GIT_COMMON" ]; then
    # In worktree — skip check (commit should be on feature branch)
    exit 0
fi
```

---

## Known Issues to Avoid

### Issue 1: Task Counter Collision
**Problem:** Multiple MCP processes generating same task ID in same second  
**Solution (existing):** Use PID in ID: `tb_{timestamp}_{pid}_{counter}`  
**Relevance:** Task board query must use `.find_tasks_for_role()` which handles this

### Issue 2: Post-Commit Hook Noise
**Problem:** Pre-commit hook can print to stderr, causing `git commit` to report false failure  
**Solution (existing):** `git_tool.py` checks if HEAD changed despite non-zero return  
**Relevance:** Our hook must NOT interfere with existing post-commit digest update

### Issue 3: Stale Claimed Tasks
**Problem:** Agent claims task A, works on unrelated task B → commit blocked on A  
**Solution:** Time window (4h default) + manual `--no-verify` escape hatch

---

## Metrics to Track

After implementation, measure:

1. **Compliance Rate:**
   - % commits rejected by pre-commit hook (should be 0 for compliant agents)
   - % commits with `--no-verify` (should be <5%)

2. **Task Board Coverage:**
   - Before: 579 tasks with no `assigned_to`
   - After: Goal <10 unassigned

3. **Enforcement Effectiveness:**
   - Hook rejection rate by agent
   - Time from task claim to first commit

4. **False Positive Rate:**
   - Legitimate rejections (agent forgot to claim)
   - Stale task rejections (should be <2%)

---

## Implementation Plan

### Phase 1: Pre-Commit Hook (Week 1)
- [ ] Enhance existing hook with role extraction logic
- [ ] Add claimed task query function to `task_board.py`
- [ ] Create `install_hooks.sh` for easy setup
- [ ] Write `TASK_BOARD_COMPLIANCE.md` docs
- [ ] Test in main repo + worktree

### Phase 2: MCP Guard (Week 2)
- [ ] Modify `git_tool.py::GitCommitTool.execute()`
- [ ] Add `@check_claimed_task` decorator pattern
- [ ] Update error messages to guide toward task board
- [ ] Add unit tests

### Phase 3: Soft Guard (Week 3)
- [ ] Update `session_init` to check claimed tasks
- [ ] Add flag to `ps.no_task_claimed`
- [ ] Add to `next_steps` output
- [ ] Dashboard metric

---

## Documentation Deliverables

1. **TASK_BOARD_COMPLIANCE.md** — User guide for compliance
2. **GUARDRAIL_ARCHITECTURE.md** — Technical deep dive
3. **TROUBLESHOOTING_GUIDES.md** — FAQ for agents hitting blocks

---

## Open Questions

1. **Time Window:** Should "claimed" task be fresh (4h) or just "not abandoned" (24h)?
2. **Worktree Bypass:** In worktrees, should we still enforce or be lenient (they're branches)?
3. **Role Parsing:** What's the canonical format for extracting role from branch name?
4. **Emergency Bypass:** Should `--no-verify` log an audit event?

---

## Decision Log

**2026-04-08 — Wu Recon Complete**
- Evaluated 3 options
- Recommended hybrid: pre-commit (primary) + MCP guard (secondary) + soft (awareness)
- Ready for implementation planning

**Next:** Implementation task `tb_1775672198_6783_1`
