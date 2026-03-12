# Phase 177 — Shared metrics vocabulary

Status: active
Purpose: keep localguys and adjacent benchmark lanes comparable inside MCC.

## Required common fields
- `runtime_name`
- `workflow_family`
- `run_status`
- `cold_start_ms`
- `avg_runtime_ms`
- `runtime_ms`
- `artifact_missing_count`
- `required_artifact_count`
- `artifact_present_count`
- `success_rate`
- `notes`

## Localguys mapping
- `workflow_family` -> existing localguys contract family
- `run_status` -> existing run registry status
- `runtime_ms` -> existing run metric
- `artifact_missing_count` -> existing run metric
- `required_artifact_count` -> existing run metric
- `artifact_present_count` -> existing run metric

## LiteRT mapping target
- `runtime_name` -> `litert`
- `workflow_family` -> benchmark lane or helper lane identifier
- `cold_start_ms` -> first invocation cost
- `avg_runtime_ms` -> average repeat runtime
- `success_rate` -> successful runs / attempted runs
- `notes` -> accelerator path, model notes, machine notes

## Rule
Do not create a second incompatible metrics dashboard.
Any adjacent runtime benchmark should map into this vocabulary first.
