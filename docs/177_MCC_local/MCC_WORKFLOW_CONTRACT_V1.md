# PHASE 177 — MCC Workflow Contract V1

Date: 2026-03-12
Status: planning
Tag: `localguys`

## Purpose
Define the first machine-readable contract that lets MCC execute and supervise autonomous workers safely.

This contract is the missing layer between:
- workflow family selection
- role preprompt
- model policy
- playground isolation
- verifier gating
- artifact proof

## Contract object

```json
{
  "workflow_family": "g3_localguys",
  "version": "v1",
  "roles": ["coder", "verifier"],
  "steps": ["recon", "plan", "execute", "verify", "review", "finalize"],
  "model_policy": {},
  "tool_budget": {},
  "allowed_tools": [],
  "allowed_files": [],
  "artifact_contract": {},
  "failure_policy": {},
  "sandbox_policy": {},
  "completion_policy": {}
}
```

## Required fields

### `workflow_family`
Stable workflow family id.
Examples:
- `g3_localguys`
- `ralph_localguys`

### `roles`
Roles that may actively execute in this workflow.
For MVP local deployment:
- `coder`
- `verifier`

### `steps`
Strict ordered steps.
Default for localguys:
1. `recon`
2. `plan`
3. `execute`
4. `verify`
5. `review`
6. `finalize`

### `model_policy`
Per-role model assignment and constraints.
Example:

```json
{
  "coder": {
    "preferred_models": ["qwen3:8b", "qwen2.5:7b"],
    "fallback_models": ["qwen2.5:3b"],
    "prompt_style": "coder_compact_v1",
    "max_context_chars": 24000
  },
  "verifier": {
    "preferred_models": ["deepseek-r1:8b"],
    "fallback_models": ["phi4-mini:latest"],
    "prompt_style": "verifier_attack_v1",
    "max_context_chars": 18000
  }
}
```

### `tool_budget`
Per-step caps.
Example:

```json
{
  "recon": { "max_tool_calls": 6, "max_retries": 1 },
  "plan": { "max_tool_calls": 2, "max_retries": 1 },
  "execute": { "max_tool_calls": 8, "max_retries": 2 },
  "verify": { "max_tool_calls": 4, "max_retries": 1 },
  "review": { "max_tool_calls": 3, "max_retries": 1 }
}
```

### `allowed_tools`
Logical tool groups or exact tools permitted for the family.
Start minimal:
- `context`
- `tasks`
- `artifacts`
- `stats`
- `search`
- `tests`
- `git_diff`

### `allowed_files`
Optional task/file allowlist.
If present, executor must not touch anything outside it.

### `artifact_contract`
Required outputs.
Example:

```json
{
  "required": [
    "facts.json",
    "plan.json",
    "patch.diff",
    "test_output.txt",
    "review.json",
    "final_report.json"
  ],
  "base_path": "artifacts/mcc_local/{task_id}/"
}
```

### `failure_policy`
When to stop.
Example:

```json
{
  "stop_on": [
    "budget_exhausted",
    "playground_missing",
    "verifier_blocked",
    "required_artifact_missing",
    "required_test_failed"
  ],
  "terminal_states": ["blocked", "failed", "escalated"]
}
```

### `sandbox_policy`
Execution isolation rules.
Example:

```json
{
  "mode": "playground_only",
  "requires_playground": true,
  "requires_branch": true,
  "allow_main_tree_write": false,
  "lock_to_playground_id": true
}
```

### `completion_policy`
Definition of `done`.
Example:

```json
{
  "requires_verifier_pass": true,
  "requires_required_artifacts": true,
  "requires_targeted_tests": true,
  "requires_final_report": true
}
```

## MCC API shape
Recommended additions:
- `GET /api/mcc/workflow-contract/{family}`
- `GET /api/mcc/tasks/{task_id}/workflow-contract`
- include `workflow_contract` in task-detail payloads
- include `resolved_model_policy` in active run payloads

## Runtime state shape
Every active run should surface:

```json
{
  "task_id": "tb_xxx",
  "workflow_family": "g3_localguys",
  "current_step": "execute",
  "active_role": "coder",
  "model_id": "qwen3:8b",
  "playground_id": "pg_xxx",
  "branch_name": "playground/pg_xxx",
  "artifacts": [],
  "status": "running",
  "failure_reason": ""
}
```

## Enforcement rules
1. No run starts without resolved workflow contract.
2. No local run starts without playground lock.
3. No `done` without verifier pass.
4. No missing required artifacts at finalize.
5. Any contract violation returns structured `blocked` or `failed`.

## First family: `g3_localguys`
Recommended V1 contract:
- roles: `coder`, `verifier`
- sandbox: required
- artifacts: required
- verifier: mandatory
- model policy: local-only
- completion: tests pass + review pass + report written

## Why this matters
Without this contract MCC only previews prompts and workflows.
With this contract MCC can supervise actual autonomous local workers instead of just describing them.

## Operator tool compatibility
The contract must be executable from both MCC UI and a one-command operator tool for Codex/Claude.

Required properties for tool-mode launch:
- same `workflow_family` resolution as MCC
- same playground lock rules
- same model policy resolution
- same artifact contract
- same completion and failure semantics

That means any future localguys CLI/MCP tool is a transport wrapper around this contract, not a second execution system.
