# Phase 133: Stable Dragons — Cursor Brief
**Date:** 2026-02-10
**Priority:** CRITICAL — enables autonomous pipeline execution
**Effort:** ~80 min total
**Branch:** `claude/eloquent-ptolemy`

---

## Context

Mycelium pipeline (Dragon/Titan teams) must run autonomously:
- Heartbeat scans chat every 60s for @dragon/@titan commands
- TaskBoard queues and dispatches to AgentPipeline
- Pipeline runs 5 phases: Scout → Architect → Researcher → Coder → Verifier
- LLM calls go through Polza provider (Kimi, Grok Fast, Qwen, GLM)

**Problem:** Pipeline crashes on provider 429/502, no timeouts on phases, no concurrency limits, no client tracking. We need rock-solid execution.

**Grok research:** `docs/131_ph/Grok Research- Stable Autonomous Pipeline for VETKA.txt`

---

## C33A: Provider Resilience Decorator (30 min) — P1

**File:** `src/mcp/tools/llm_call_tool_async.py`

**What:** Wrap LLM calls with retry + fallback chain.

**Implementation:**
1. Add retry decorator with exponential backoff (1s → 16s) + jitter (±20%)
2. Max 5 retries per provider on 429/502/504/timeout errors
3. Fallback chain: polza → openrouter → ollama (local)
4. Log each retry attempt and provider switch

```python
# MARKER_133.C33A: Provider Resilience
import asyncio
import random
import logging

logger = logging.getLogger(__name__)

async def resilient_llm_call(func, *args, max_retries=5, **kwargs):
    """Exponential backoff + jitter + provider fallback."""
    providers = ["polza", "openrouter", "ollama"]
    last_exc = None

    for provider in providers:
        kwargs["model_source"] = provider
        for attempt in range(max_retries):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                last_exc = e
                err_str = str(e)
                if any(code in err_str for code in ["429", "502", "503", "504", "timeout", "Timeout"]):
                    wait = min(2 ** attempt, 16) + random.uniform(-0.2, 0.2)
                    logger.warning(f"[Resilience] {provider} attempt {attempt+1}/{max_retries}: {err_str[:80]}. Retry in {wait:.1f}s")
                    await asyncio.sleep(wait)
                else:
                    logger.error(f"[Resilience] {provider} non-retryable: {err_str[:120]}")
                    break
        logger.warning(f"[Resilience] Provider {provider} exhausted after {max_retries} retries, trying next")

    raise last_exc or RuntimeError("All providers failed")
```

**Where to inject:** In `LLMCallToolAsync.execute()` — wrap the actual HTTP call with `resilient_llm_call()`.

**Test:** Simulate 3x 429 → should retry and succeed on 4th attempt.

**MARKER:** `MARKER_133.C33A`

---

## C33B: Per-Phase Timeout (20 min) — P1

**File:** `src/orchestration/agent_pipeline.py`

**What:** Each pipeline phase gets a timeout. If exceeded — skip, don't crash the whole pipeline.

**Implementation:**
1. Add timeout constants (configurable via env):
```python
# MARKER_133.C33B: Per-phase timeouts
PHASE_TIMEOUTS = {
    "scout": int(os.getenv("VETKA_TIMEOUT_SCOUT", "30")),
    "architect": int(os.getenv("VETKA_TIMEOUT_ARCHITECT", "60")),
    "researcher": int(os.getenv("VETKA_TIMEOUT_RESEARCHER", "45")),
    "coder": int(os.getenv("VETKA_TIMEOUT_CODER", "90")),
    "verifier": int(os.getenv("VETKA_TIMEOUT_VERIFIER", "30")),
}
```

2. Wrap phase execution:
```python
async def safe_phase(self, phase_name: str, coro):
    """Execute phase with timeout. Returns None on timeout (non-fatal)."""
    timeout = PHASE_TIMEOUTS.get(phase_name, 60)
    try:
        return await asyncio.wait_for(coro, timeout=timeout)
    except asyncio.TimeoutError:
        logger.error(f"[Pipeline] Phase '{phase_name}' timed out after {timeout}s — skipping")
        await self._emit_progress("system", f"Phase {phase_name} timed out ({timeout}s) — continuing")
        return None
```

3. Apply to existing phase calls:
- `_scout_scan()` → `await self.safe_phase("scout", self._scout_scan(task, phase_type))`
- `_architect_plan()` → `await self.safe_phase("architect", self._architect_plan(...))`
- `_research()` → `await self.safe_phase("researcher", self._research(...))`
- `_execute_subtask()` → `await self.safe_phase("coder", self._execute_subtask(...))`
- `_verify_subtask()` → `await self.safe_phase("verifier", self._verify_subtask(...))`

**Important:** If architect times out → abort pipeline (no plan = can't continue). Other phases can be skipped gracefully.

**Test:** Set `VETKA_TIMEOUT_SCOUT=1` → scout should timeout, pipeline continues without scout context.

**MARKER:** `MARKER_133.C33B`

---

## C33C: max_concurrent Semaphore (15 min) — P2

**File:** `src/orchestration/task_board.py`

**What:** Enforce max_concurrent setting — no more than N pipelines running simultaneously.

**Implementation:**
1. Add class-level semaphore:
```python
# MARKER_133.C33C: Concurrent dispatch limiter
import asyncio

class TaskBoard:
    _dispatch_semaphore: asyncio.Semaphore = None

    @classmethod
    def _get_semaphore(cls, max_concurrent: int = 2) -> asyncio.Semaphore:
        if cls._dispatch_semaphore is None:
            cls._dispatch_semaphore = asyncio.Semaphore(max_concurrent)
        return cls._dispatch_semaphore
```

2. In `dispatch_task()` (around line 681), wrap the pipeline execution:
```python
async def dispatch_task(self, task_id, chat_id=None, ...):
    max_c = self.settings.get("max_concurrent", 2)
    sem = TaskBoard._get_semaphore(max_c)

    if sem.locked():
        logger.warning(f"[TaskBoard] Max concurrent ({max_c}) reached, queuing {task_id}")
        return {"success": False, "error": "max_concurrent reached", "queued": True}

    async with sem:
        # ... existing dispatch logic ...
        pipeline = AgentPipeline(...)
        result = await pipeline.execute(...)
        # ...
```

3. Add `/api/tasks/concurrent` GET endpoint to check current load:
```python
@router.get("/concurrent")
async def get_concurrent_info():
    sem = TaskBoard._get_semaphore()
    return {
        "max": board.settings.get("max_concurrent", 2),
        "available": sem._value if hasattr(sem, '_value') else "unknown",
        "running": len([t for t in board.list_tasks() if t["status"] == "running"])
    }
```

**Test:** Dispatch 3 tasks rapidly → only 2 run, 3rd gets "queued" response.

**MARKER:** `MARKER_133.C33C`

---

## C33D: client_id in Task Creation (15 min) — P2

**File:** `src/api/routes/task_routes.py` + `src/orchestration/task_board.py`

**What:** Track which client (Claude Code, Cursor, OpenCode) created each task.

**Implementation:**

1. In `task_board.py` `add_task()` (around line 179), add `created_by` parameter:
```python
# MARKER_133.C33D: Client attribution
def add_task(self, title, description="", priority=PRIORITY_MEDIUM,
             phase_type="build", tags=None, preset=None,
             dependencies=None, created_by="unknown"):  # NEW param
    task = {
        "id": task_id,
        "title": title,
        # ... existing fields ...
        "created_by": created_by,  # NEW: "claude-code", "cursor", "opencode", "heartbeat"
    }
```

2. In `task_routes.py` POST `/api/tasks`, read header:
```python
@router.post("")
async def create_task(body: Dict[str, Any], request: Request):
    created_by = request.headers.get("X-Agent-ID", "unknown")
    task_id = board.add_task(
        title=body["title"],
        # ... existing params ...
        created_by=created_by,
    )
```

3. In `mycelium_heartbeat.py`, when creating tasks from chat, set `created_by="heartbeat"`:
```python
board.add_task(title=task_title, ..., created_by=f"heartbeat:{task.trigger}")
```

4. Add to task list/get responses so DevPanel can show who created what.

**Test:** `curl -H "X-Agent-ID: cursor" -X POST /api/tasks -d '{"title":"test"}'` → task.created_by == "cursor"

**MARKER:** `MARKER_133.C33D`

---

## Execution Order

```
C33A (retry/fallback) ← CRITICAL, do first
  ↓
C33B (phase timeouts) ← CRITICAL, prevents hangs
  ↓
C33C (semaphore)      ← Important, prevents overload
  ↓
C33D (client_id)      ← Nice-to-have, tracking
```

## DO NOT TOUCH
- Frontend/DevPanel UI
- docs/ directory
- main.py
- approval_service.py
- eval_agent.py

## Files to Edit
1. `src/mcp/tools/llm_call_tool_async.py` (C33A)
2. `src/orchestration/agent_pipeline.py` (C33B)
3. `src/orchestration/task_board.py` (C33C, C33D)
4. `src/api/routes/task_routes.py` (C33D)
5. `src/orchestration/mycelium_heartbeat.py` (C33D — one line)

## Reference
- Grok research: `docs/131_ph/Grok Research- Stable Autonomous Pipeline for VETKA.txt`
- Pipeline prompts: `data/templates/pipeline_prompts.json`
- Model presets: `data/templates/model_presets.json`
- Existing retry: `agent_pipeline.py:2068-2088` (coder retry loop — don't break it)
