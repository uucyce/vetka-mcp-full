# PHASE 151 — EXECUTION PLAN
## Unified Multi-Agent Implementation Schedule
**Commander: Opus | Frontend: Codex | Research: Grok (done)**
**Date: 2026-02-15**

---

## DEPENDENCY MAP

```
                    Wave 1 (Codex)              Wave 4 (Opus)
                    ┌─────────────┐             ┌──────────────┐
                    │ 151.1 HB    │             │ 151.11 stats │
                    │ 151.3 Nodes │   PARALLEL  │ 151.12 fdbck │
                    │ 151.4 Hndls │             │ 151.14 arch  │
                    └──────┬──────┘             └──────┬───────┘
                           │                           │
                    Wave 2 (Codex)                     │
                    ┌──────┴──────┐                    │
                    │ 151.5 Header│ ← uses HB dropdown │
                    │ 151.6 Merge │                    │
                    │ 151.7 Clean │                    │
                    └──────┬──────┘                    │
                           │                           │
                    Wave 3 (Codex)                     │
                    ┌──────┴──────┐                    │
                    │ 151.8 Chat  │                    │
                    │ 151.9 Stats │ ← needs 151.13 UI │
                    │ 151.10 Bal  │                    │
                    └──────┬──────┘                    │
                           │                           │
                    Wave 5 (Codex)                     │
                    ┌──────┴──────────────────────────┴┐
                    │ 151.13 Stats UI (needs 151.11 backend) │
                    │ 151.15 Onboarding                      │
                    │ 151.16 Tooltips                        │
                    │ 151.17 Visual audit                    │
                    │ 151.18 PG↔WF logic                     │
                    └────────────────────────────────────────┘
```

**Key parallel:** Wave 1 (Codex frontend) + Wave 4 (Opus backend) run simultaneously.
**Key dependency:** Wave 5 task 151.13 (Stats UI) needs Wave 4 task 151.11 (per-agent backend) done first.

---

## SPRINT SCHEDULE

### Sprint 1 (Days 1-3) — PARALLEL

| Agent | Tasks | Files |
|-------|-------|-------|
| **Codex** | Wave 1: 151.1, 151.3, 151.4 | HeartbeatChip.tsx, DAGView.tsx, useMCCStore.ts, new NodePicker.tsx, MCC.tsx |
| **Opus** | Wave 4: 151.11, 151.12, 151.14 | agent_pipeline.py, task_board.py, pipeline_prompts.json |

**No file conflicts.** Codex = `client/src/`, Opus = `src/` python backend.
Note: 151.2 (edges) already done by Opus in dagLayout.ts + DAGView.tsx.

### Sprint 2 (Days 4-6) — SEQUENTIAL (Codex)

| Agent | Tasks | Files |
|-------|-------|-------|
| **Codex** | Wave 2: 151.5, 151.6, 151.7 | MyceliumCommandCenter.tsx, WorkflowToolbar.tsx |
| **Opus** | Review + tests for Wave 4 | tests/test_phase151_*.py |

**Dependency:** 151.5 (unified header) uses HeartbeatDropdown from 151.1.

### Sprint 3 (Days 7-9) — SEQUENTIAL (Codex)

| Agent | Tasks | Files |
|-------|-------|-------|
| **Codex** | Wave 3: 151.8, 151.9, 151.10 | ArchitectChat.tsx, PipelineStats.tsx, BalancesPanel.tsx, MCCDetailPanel.tsx |
| **Opus** | Standby / review | — |

### Sprint 4 (Days 10-14) — CODEX HEAVY

| Agent | Tasks | Files |
|-------|-------|-------|
| **Codex** | Wave 5: 151.13, 151.15, 151.16, 151.17, 151.18 | PipelineStats.tsx (rewrite), new OnboardingOverlay.tsx, useOnboarding.ts, globals.css |
| **Opus** | Final review, commit, memory update | docs/, MEMORY.md |

---

## OPUS TASKS — Wave 4 Backend (Sprint 1)

### 151.11 — Per-Agent Metrics Collection
**File:** `src/orchestration/agent_pipeline.py`

**Current state:** Pipeline collects aggregate stats: `_llm_calls`, `_tokens_in`, `_tokens_out`, `verifier_avg_confidence`. No per-agent breakdown.

**What to build:**
Add `_agent_stats: Dict[str, Dict]` to AgentPipeline.__init__. Track per-agent:
```python
self._agent_stats = {}  # role → {calls, tokens_in, tokens_out, duration_s, retries, success}
```

At each LLM call site (5 total), update:
```python
def _track_agent_stat(self, role: str, tokens_in: int, tokens_out: int, duration: float, success: bool = True):
    if role not in self._agent_stats:
        self._agent_stats[role] = {
            'calls': 0, 'tokens_in': 0, 'tokens_out': 0,
            'duration_s': 0, 'retries': 0, 'success_count': 0, 'fail_count': 0
        }
    stats = self._agent_stats[role]
    stats['calls'] += 1
    stats['tokens_in'] += tokens_in
    stats['tokens_out'] += tokens_out
    stats['duration_s'] += duration
    if success:
        stats['success_count'] += 1
    else:
        stats['fail_count'] += 1
```

Add to `pipeline_stats` dict at end of `execute()`:
```python
'agent_stats': self._agent_stats,  # per-role breakdown
```

**LLM call sites to instrument:** (search for `_track_llm_call`)
1. Scout LLM call
2. Architect LLM call
3. Researcher LLM call
4. Coder LLM call (both FC and one-shot paths)
5. Verifier LLM call

Each already calls `_track_llm_call()` — add `_track_agent_stat()` call next to it.

For verifier: track retry_count from subtask.retry_count.
For coder: track whether verifier passed (success=True) or failed (success=False).

**Tests:** `test_phase151_11_per_agent_stats.py`
- Pipeline has _agent_stats dict
- Each role tracked after LLM call
- pipeline_stats includes agent_stats
- Retries counted for coder

---

### 151.12 — User Feedback → Stats Integration
**File:** `src/orchestration/task_board.py`

**Current state:** `task.stats` has pipeline self-assessment. `task.result_status` has user feedback (applied/rejected/rework). They are separate — user feedback doesn't affect success metrics.

**What to build:**
New method `compute_adjusted_stats(task_id)`:
```python
def compute_adjusted_stats(self, task_id: str) -> dict:
    task = self.get_task(task_id)
    if not task or 'stats' not in task:
        return {}

    stats = task['stats']
    result_status = task.get('result_status')

    # Blend: 70% self-assessment + 30% user feedback
    verifier_success = 1.0 if stats.get('success', False) else 0.0
    user_success = {
        'applied': 1.0,
        'rework': 0.5,
        'rejected': 0.0,
        None: verifier_success,  # No feedback = trust verifier
    }.get(result_status, verifier_success)

    adjusted_success = 0.7 * verifier_success + 0.3 * user_success

    return {
        **stats,
        'adjusted_success': adjusted_success,
        'user_feedback': result_status,
        'has_user_feedback': result_status is not None,
    }
```

Add to task board REST API response: include `adjusted_stats` when returning task list.

**Tests:** `test_phase151_12_feedback_stats.py`
- applied → adjusted = 0.7*1 + 0.3*1 = 1.0
- rejected → adjusted = 0.7*1 + 0.3*0 = 0.7 (verifier said OK, user said no)
- rework → adjusted = 0.7*1 + 0.3*0.5 = 0.85
- no feedback → adjusted = verifier_success (passthrough)

---

### 151.14 — Architect Reads Stats for Model Swap
**File:** `src/orchestration/agent_pipeline.py`, `data/templates/pipeline_prompts.json`

**What to build:**
Before Architect LLM call, collect team performance history from TaskBoard:
```python
async def _get_team_performance_summary(self) -> str:
    """Collect recent per-agent stats for Architect context."""
    try:
        board = TaskBoard()
        recent_tasks = [t for t in board.list_tasks() if t.get('stats', {}).get('agent_stats')]
        if not recent_tasks:
            return ""

        # Aggregate per-agent across recent tasks (last 10)
        agent_totals = {}
        for task in recent_tasks[-10:]:
            for role, stats in task['stats'].get('agent_stats', {}).items():
                if role not in agent_totals:
                    agent_totals[role] = {'calls': 0, 'success': 0, 'fail': 0}
                agent_totals[role]['calls'] += stats.get('calls', 0)
                agent_totals[role]['success'] += stats.get('success_count', 0)
                agent_totals[role]['fail'] += stats.get('fail_count', 0)

        lines = ["## TEAM PERFORMANCE (last 10 runs)"]
        for role, totals in agent_totals.items():
            total = totals['success'] + totals['fail']
            rate = totals['success'] / total * 100 if total > 0 else 0
            flag = " ⚠️ WEAK" if rate < 60 else ""
            lines.append(f"- {role}: {rate:.0f}% success ({totals['calls']} calls){flag}")

        return "\n".join(lines)
    except Exception:
        return ""  # Graceful — never block pipeline
```

Inject into Architect's user message (before plan):
```python
# In _architect_plan():
team_perf = await self._get_team_performance_summary()
if team_perf:
    user_message = f"{team_perf}\n\n{user_message}"
```

Update Architect prompt in `pipeline_prompts.json`:
```
"If TEAM PERFORMANCE data is provided, consider agent success rates.
If any agent is marked ⚠️ WEAK (<60% success), note this in your plan
and suggest the team leader consider swapping to a stronger model."
```

**Tests:** `test_phase151_14_architect_stats.py`
- Empty board → no injection (empty string)
- Board with stats → summary injected
- Weak agent (<60%) → ⚠️ flag
- Exception → graceful empty string

---

## CODEX BRIEFS

Each brief below is a self-contained document for Codex. No ambiguity — exact files, line numbers, before/after code.

---

## FILE CONFLICT MATRIX

| File | Wave 1 | Wave 2 | Wave 3 | Wave 4 | Wave 5 |
|------|--------|--------|--------|--------|--------|
| HeartbeatChip.tsx | ✏️ 151.1 | 🔗 151.5 | | | |
| dagLayout.ts | ✅ done | | | | |
| DAGView.tsx | ✅ done + ✏️ 151.4 | | | | |
| useMCCStore.ts | ✏️ 151.3 | ✏️ 151.5 | | | ✏️ 151.18 |
| NodePicker.tsx | 🆕 151.3 | | | | |
| MCC.tsx | ✏️ 151.3 | ✏️ 151.5-7 | | | |
| WorkflowToolbar.tsx | | ✏️ 151.6 | | | |
| ArchitectChat.tsx | | | ✏️ 151.8 | | |
| PipelineStats.tsx | | | ✏️ 151.9 | | 🔄 151.13 |
| BalancesPanel.tsx | | | ✏️ 151.10 | | |
| MCCDetailPanel.tsx | | | ✏️ 151.8-9 | | |
| DevPanel.tsx | | | ✏️ 151.8 | | |
| agent_pipeline.py | | | | ✏️ 151.11,14 | |
| task_board.py | | | | ✏️ 151.12 | |
| pipeline_prompts.json | | | | ✏️ 151.14 | |
| OnboardingOverlay.tsx | | | | | 🆕 151.15 |
| useOnboarding.ts | | | | | 🆕 151.15 |
| globals.css | | | | | ✏️ 151.17 |

**Zero conflicts between Opus (python) and Codex (typescript) in Sprint 1.**
Waves 2-5 are sequential for Codex — no overlap.

---

*Execution Plan by Opus Commander | Phase 151 | 2026-02-15*
