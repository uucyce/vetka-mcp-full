# Mycelium Feedback Loop — Self-Improvement Architecture
**Date:** 2026-02-10
**Designed by:** Opus (Claude Code Commander)
**Status:** PROPOSAL — for review

---

## Core Idea

Every pipeline run generates **lessons learned**. Today they're lost.
We need a closed loop:

```
Pipeline Run → Verifier Reports Issues → Architect Writes Final Report
    → Report saved to data/feedback/ → Opus Reviews
    → Improvements become new tasks → Next pipeline is smarter
```

---

## Architecture: 3 Feedback Channels

### Channel 1: Verifier → Architect (Per-Pipeline)
**Already exists partially.** Verifier scores each subtask.
**What's missing:** Verifier doesn't explain WHY score is low.

**Fix:** After verifier scores < 0.8, it writes a structured feedback:
```json
{
  "subtask_marker": "MARKER_102.3",
  "score": 0.65,
  "issues": ["Missing error handling", "No type hints"],
  "suggestion": "Add try/except and type annotations",
  "severity": "medium"
}
```

This gets passed to Architect in the **Final Report** phase (new phase 6).

### Channel 2: Architect Final Report (Per-Pipeline)
**NEW.** After all subtasks done + verified, Architect generates a final report:

```json
{
  "run_id": "run_1770729542",
  "task": "Build heartbeat health endpoint",
  "summary": "Completed 4/4 subtasks. Health endpoint created.",
  "quality_score": 0.78,
  "issues_found": [
    {"type": "code_quality", "detail": "Missing docstrings in 2 functions"},
    {"type": "architecture", "detail": "Should use dependency injection for config"}
  ],
  "improvements_for_next_run": [
    "Prompt coder to always include docstrings",
    "Add config injection pattern to system prompt"
  ],
  "files_created": ["src/api/routes/heartbeat_health.py"],
  "tokens_used": 12630,
  "duration_s": 220,
  "timestamp": "2026-02-10T16:22:43Z"
}
```

Saved to: `data/feedback/reports/{run_id}.json`

### Channel 3: Opus Review Queue (Cross-Pipeline)
**NEW.** Opus (Claude Code) periodically reviews accumulated reports:

1. Read all reports from `data/feedback/reports/`
2. Identify patterns (recurring issues across runs)
3. Generate **improvement tasks** for Mycelium itself
4. Add to TaskBoard as `phase_type: "improve"` tasks

These improvement tasks are **architect-level** — they modify:
- `data/templates/pipeline_prompts.json` (system prompts for each role)
- `data/templates/model_presets.json` (team configs)
- Quality thresholds
- Code extraction patterns

---

## Data Flow

```
                    ┌─────────────┐
                    │ Pipeline Run │
                    └──────┬──────┘
                           │
              ┌────────────┼────────────┐
              ▼            ▼            ▼
        ┌──────────┐ ┌──────────┐ ┌──────────┐
        │  Scout   │ │  Coder   │ │ Verifier │
        └──────────┘ └──────────┘ └─────┬────┘
                                        │
                                   ┌────▼────┐
                                   │ Feedback │
                                   │  Items   │
                                   └────┬────┘
                                        │
                                   ┌────▼──────────┐
                                   │   Architect    │
                                   │ Final Report   │
                                   │ (NEW Phase 6)  │
                                   └────┬──────────┘
                                        │
                              ┌─────────▼──────────┐
                              │ data/feedback/      │
                              │   reports/          │
                              │   patterns/         │
                              │   improvements/     │
                              └─────────┬──────────┘
                                        │
                              ┌─────────▼──────────┐
                              │  Opus Review        │
                              │  (periodic or       │
                              │   on-demand)        │
                              └─────────┬──────────┘
                                        │
                              ┌─────────▼──────────┐
                              │  Improvement Tasks  │
                              │  → TaskBoard        │
                              │  → Next Pipeline    │
                              │    gets smarter     │
                              └────────────────────┘
```

---

## Implementation Plan (Minimal Viable)

### Phase A: Verifier Feedback (agent_pipeline.py)
**Effort:** 30 min
**What:** After verifier scores subtask, if score < 0.8, add structured feedback to subtask result.
**Where:** `agent_pipeline.py` verifier phase, around line 2700+
**How:** Append feedback dict to subtask, pass to architect.

### Phase B: Architect Final Report (agent_pipeline.py)
**Effort:** 1 hour
**What:** New phase after all subtasks done. Architect model generates final report JSON.
**Where:** After `_phase_verifier()`, before stats recording.
**Output:** `data/feedback/reports/{task_id}_report.json`

### Phase C: Feedback Storage + API
**Effort:** 30 min
**New files:**
- `src/services/feedback_service.py` — save/load reports, pattern detection
- `src/api/routes/feedback_routes.py` — API for MCC to show reports

**Endpoints:**
- `GET /api/feedback/reports?limit=20` — list reports
- `GET /api/feedback/reports/{id}` — single report
- `GET /api/feedback/patterns` — recurring issues
- `GET /api/feedback/improvements` — suggested improvements

### Phase D: MCC Integration
**Effort:** Cursor task
**What:** Add "Feedback" section to MCC Overview or new tab.
Show: last 5 reports, recurring patterns, suggested improvements.

### Phase E: Opus Auto-Review
**Effort:** MCP tool
**What:** `mycelium_review_feedback` — Opus reads accumulated reports, generates improvement tasks.
**When:** On-demand or after every 10 pipeline runs.

---

## Safety: Read-Only Feedback

Key principle: **Feedback NEVER auto-modifies prompts.**

1. Verifier and Architect only WRITE reports (data/feedback/)
2. Reports are READ by Opus (human-in-loop)
3. Opus decides which improvements to accept
4. Improvements go through normal TaskBoard → Pipeline flow
5. Only after human approval do they modify system prompts

Later (when trust is established):
- Auto-apply improvements with score > 0.95
- Playground mode for testing prompt changes
- A/B testing of prompt variants

---

## Digest Integration

Final reports automatically update `project_digest.json` via task_tracker:
- `on_task_completed()` already fires
- Report summary added to `key_achievements`
- `improvements_for_next_run` added to `pending_items`

MCC shows digest in real-time. All agents see it via `vetka_session_init`.

---

## Chat Integration

Agents in Vetka chat CAN:
- ✅ Read digest via `vetka_session_init` or `vetka_get_context_dag`
- ✅ Read feedback reports via API
- ✅ Mark tasks done via `mycelium_track_done`
- ✅ Leave messages via `vetka_send_message`
- ✅ Get tracker status via `mycelium_tracker_status`

Agents CANNOT:
- ❌ Modify system prompts directly
- ❌ Approve their own artifacts
- ❌ Change pipeline configuration
- ❌ Delete feedback reports

---

## Files Created/Modified

| File | Action | Purpose |
|------|--------|---------|
| `src/services/feedback_service.py` | NEW | Save/load reports, patterns |
| `src/api/routes/feedback_routes.py` | NEW | API for MCC |
| `src/orchestration/agent_pipeline.py` | MODIFY | Phase 6 (Final Report) |
| `data/feedback/reports/` | NEW DIR | Report storage |
| `data/feedback/patterns.json` | NEW | Recurring issue patterns |

---

## Cursor Brief Summary

C35A: Verifier structured feedback (agent_pipeline.py)
C35B: Architect final report phase (agent_pipeline.py)
C35C: Feedback service + API (new files)
C35D: MCC Feedback tab (client)
C35E: Pattern detection (feedback_service.py)

---

## Why This Matters

After 27 pipeline runs with 0 files written, we now have:
1. ✅ auto_write=True (files get written)
2. ✅ Multi-format parser (code extraction works)
3. ✅ Task tracker (digest stays current)
4. 🔜 Feedback loop (system gets smarter)

Each run teaches the next. This is how Mycelium evolves from
"generates code that goes nowhere" to
"autonomously improves its own quality and writes production code."
