# Dragon Pipeline — Real Tasks for Phase 133
**Date:** 2026-02-10
**Dispatch via:** `@dragon <task>` in chat or `mycelium_task_board` → `mycelium_task_dispatch`

---

## Task 1: Pipeline Checkpoint System (Silver)
**Trigger:** `@dragon build checkpoint system for agent_pipeline.py`
**Description:** After each pipeline phase completes, save intermediate results to `data/pipeline_checkpoints/{task_id}.json`. Format: `{task_id, phase, status, result_summary, timestamp, subtasks_completed}`. If pipeline crashes, next run can resume from last checkpoint.
**Files:** `src/orchestration/agent_pipeline.py`
**Complexity:** medium
**Tag:** checkpoint

## Task 2: Heartbeat Health Endpoint (Bronze)
**Trigger:** `@dragon build GET /api/heartbeat/health endpoint`
**Description:** Add FastAPI endpoint that returns: `{status: "alive"|"dead", last_tick: timestamp, total_ticks: int, tasks_dispatched: int, uptime_seconds: int}`. Read from heartbeat engine state. Add to existing routes.
**Files:** `src/api/routes/task_routes.py`, `src/orchestration/mycelium_heartbeat.py`
**Complexity:** simple
**Tag:** health

## Task 3: Pipeline Run History (Bronze)
**Trigger:** `@dragon build pipeline run history storage`
**Description:** After each pipeline completes, append a summary record to `data/pipeline_history.json`. Record: `{run_id, task_title, preset, phases_completed, total_duration_s, eval_score, status, timestamp}`. Add GET /api/pipeline/history?limit=20 endpoint.
**Files:** `src/orchestration/agent_pipeline.py`, `src/api/routes/task_routes.py`
**Complexity:** simple
**Tag:** metrics

## Task 4: EvalAgent Model Upgrade Config (Bronze)
**Trigger:** `@dragon fix eval_agent to use configurable model`
**Description:** In `src/agents/eval_agent.py`, replace hardcoded `deepseek-coder:6.7b` with configurable model from env var `VETKA_EVAL_MODEL` (default: `qwen3-30b-a3b`). Add to model_presets.json as `eval_model` field.
**Files:** `src/agents/eval_agent.py`, `data/templates/model_presets.json`
**Complexity:** simple
**Tag:** eval

## Task 5: TaskBoard Cleanup Cron (Silver)
**Trigger:** `@dragon build auto-cleanup for stale tasks in task_board`
**Description:** Add method `cleanup_stale()` to TaskBoard: tasks in "running" state for >10min → mark as "failed" with reason "timeout". Tasks in "claimed" for >5min → release back to "pending". Call from heartbeat every 10 ticks.
**Files:** `src/orchestration/task_board.py`, `src/orchestration/mycelium_heartbeat.py`
**Complexity:** medium
**Tag:** cleanup

---

## Dispatch Order
1. Task 2 (health endpoint) — simplest, validates pipeline works
2. Task 4 (eval model config) — quick win
3. Task 3 (run history) — enables observability
4. Task 1 (checkpoints) — medium complexity test
5. Task 5 (cleanup) — requires coordination

## How to Dispatch
```
# Via MCP:
mycelium_task_board(action="add", title="Build heartbeat health endpoint", phase_type="build", preset="dragon_bronze", priority=1)
mycelium_task_dispatch()

# Via chat:
@dragon build GET /api/heartbeat/health endpoint that returns {status, last_tick, total_ticks, tasks_dispatched, uptime_seconds}
```
