# Recon: Localguys Step Executor
**Date:** 2026-03-29 | **Author:** Zeta | **Task:** tb_1774756047_8869_1

## Problem
Localguys has full orchestration infrastructure (11 workflows, contract builder, run registry, playground isolation, artifact validation, CLI) but **no execution engine**. Runs are created in `queued` status and stay there forever — nothing calls Ollama.

## What Exists (working)
| Layer | Status | Component |
|-------|--------|-----------|
| Contract builder | DONE | `_build_localguys_contract()` — sandbox, tools, artifacts, model policy |
| Run registry | DONE | `mcc_local_run_registry.py` — JSON persistence, lifecycle, metrics |
| Playground isolation | DONE | git worktree per run, branch per playground |
| Artifact validation | DONE | PUT artifacts via REST, missing-check blocks `done` |
| Signal/advance | DONE | PATCH endpoint with tool budget + turn count enforcement |
| CLI | DONE | `scripts/localguys.py` — catalog, run, status, signal |
| Model Matrix | DONE | 8 models mapped to roles, prompt styles, tool budgets |
| Workflow templates | PARTIAL | Only g3_localguys has real nodes (4). Other 10 = empty stubs |

## What's Missing: Step Executor
A module that:
1. Takes a `run_id` (already created via `localguys run <method> --task <id>`)
2. Reads current step from run state
3. Selects model by role from Model Matrix
4. Builds prompt from task context + step requirements
5. Calls Ollama `POST /api/generate`
6. Saves result as artifact via `PUT /api/mcc/localguys-runs/{id}/artifacts/{name}`
7. Signals step advance via `PATCH /api/mcc/localguys-runs/{id}`
8. Repeats until `finalize` or failure

## Execution Flow (per step)

```
for step in contract.steps:
    1. Select model: role → Model Matrix → preferred_models[0]
    2. Build prompt: step_template + task_snapshot + previous artifacts
    3. Call Ollama: POST /api/generate {model, prompt, stream: false}
    4. Save artifact: PUT /api/mcc/localguys-runs/{run_id}/artifacts/{step_artifact}
    5. Signal advance: PATCH /api/mcc/localguys-runs/{run_id}
       {status: "running", current_step: next_step, model_id, turn_increment: 1}
    6. If last step → status: "done" (auto-validates artifacts)
```

## Step → Artifact → Role Mapping

| Step | Artifact | Role | Model (default) |
|------|----------|------|-----------------|
| recon | `facts.json` | scout/coder | qwen2.5:7b |
| plan | `plan.json` | architect | qwen3:8b |
| execute | `patch.diff` | coder | qwen3:8b |
| verify | `test_output.txt` | verifier | deepseek-r1:8b |
| review | `review.json` | verifier | deepseek-r1:8b |
| finalize | `final_report.json` | coder | qwen2.5:3b (cheap) |

## Prompt Templates (per step)

### recon
```
You are a code scout. Analyze this task and produce facts.json with:
- affected_files: list of files to examine
- dependencies: what this task depends on
- risks: potential issues
- scope_estimate: low/medium/high

Task: {title}
Description: {description}
Allowed paths: {allowed_paths}
```

### plan
```
You are a software architect. Based on the recon facts, produce plan.json with:
- approach: high-level strategy (1-3 sentences)
- steps: ordered list of implementation steps
- files_to_modify: exact file paths and what to change

Facts: {facts.json content}
```

### execute
```
You are a coder. Implement the plan. Produce a unified diff (patch.diff).
Work ONLY within allowed_paths. Be minimal and precise.

Plan: {plan.json content}
Task: {title}
```

### verify
```
You are a code verifier. Review the patch for correctness.
Produce test_output.txt with: PASS/FAIL per check, overall verdict.

Checks:
- Syntax valid?
- Matches plan?
- Within allowed_paths?
- No obvious bugs?

Patch: {patch.diff content}
```

### review
```
You are a senior reviewer. Produce review.json with:
- verdict: approve/request_changes/reject
- comments: list of issues or approvals
- quality_score: 1-10

Patch: {patch.diff content}
Facts: {facts.json content}
```

### finalize
```
Produce final_report.json summarizing:
- task_id, run_id, model used per step
- artifacts produced
- verdict from review
- total duration
```

## Integration with Event Bus

Step executor emits AgentEvent at each step transition:
```python
event_bus.emit(AgentEvent(
    event_type="localguys_step_complete",
    source_agent="ollama-worker",
    source_tool="local_ollama",
    payload={"run_id": ..., "step": ..., "artifact": ..., "model": ...},
    tags=["notify_commander"],
))
```

Commander sees step progression via piggyback. UDS Daemon pushes to MCC.

## Implementation Plan

### Task 1: Step executor module (`scripts/localguys_executor.py`)
- Reads run from registry, iterates steps
- Prompt templates per step
- Ollama generate calls
- Artifact upload via REST
- Signal advance via REST
- ~200 lines, reuses `ollama_orchestrator.py` HTTP helpers

### Task 2: Wire into localguys CLI
- `localguys run <method> --task <id> --execute` — create run AND execute
- Or: `localguys execute --run-id <id>` — execute existing run

### Task 3: Model selection from contract
- Read `contract.model_policy[role].preferred_models`
- Check Ollama availability, fallback to next

## Known Risks
1. `get_profile_sync` missing in LLMModelRegistry — workaround: hardcode model selection from Matrix
2. Ollama can be slow (22s for 7b model) — total run = 6 steps x 22s = ~2 min minimum
3. Code generation quality from 7b models is limited — start with research/docs tasks
