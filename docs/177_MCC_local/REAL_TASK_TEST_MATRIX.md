# PHASE 177 — localguys Real-Task Test Matrix

Date: 2026-03-12
Status: planning
Tag: `localguys`

## Objective
Define the proving set for localguys using real TaskBoard-style work instead of synthetic toy prompts.

## Test layers

### Layer 1 — Contract tests
Purpose:
- verify workflow contract, model policy, and playground lock before any real execution

Examples:
- resolve `g3_localguys` contract
- resolve `coder` local model policy for `qwen3:8b`
- reject run without playground

### Layer 2 — Replay tests
Purpose:
- replay already-solved narrow tasks in a fresh playground and compare outputs

Examples:
- small backend route addition
- patch to task status/feedback wiring
- test-only bugfix

### Layer 3 — Live queue tests
Purpose:
- run localguys against real active multitask tasks with operator oversight

Examples:
- pending TaskBoard task tagged backend/frontend narrow
- queued test-only task

### Layer 4 — Soak tests
Purpose:
- check repeated runs, cleanup, and no state drift

Examples:
- 3 sequential tasks in different playgrounds
- failure then success on next task
- repeated verifier loops within budget

## Evaluation columns
- `task_id`
- `task_type`
- `scope_size`
- `workflow_family`
- `models_used`
- `playground_id`
- `tests_passed`
- `verifier_verdict`
- `artifacts_complete`
- `operator_verdict`
- `failure_bucket`

## Failure buckets
- `policy_gap`
- `tooling_gap`
- `model_gap`
- `workflow_gap`
- `mcc_visibility_gap`

## Promotion rule
localguys are ready for wider use when:
- contract tests are green
- replay tasks are reproducible
- live queue tasks complete with useful output
- failure reasons are structured and actionable
- MCC shows enough runtime state to supervise runs without guesswork
