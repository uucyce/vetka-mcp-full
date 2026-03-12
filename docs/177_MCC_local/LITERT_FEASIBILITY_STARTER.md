# PHASE 177 — LiteRT feasibility starter

Date: 2026-03-12
Status: starter
Tag: `localguys`, `litert`, `benchmark`

## Immediate goal
Start `tb_1773275513_6` with a bounded feasibility pass, not full integration.

## First pass checklist
1. confirm current LiteRT macOS build/install path on Apple Silicon
2. identify one minimal model/runtime smoke test we can run locally
3. record supported acceleration paths we can actually use on this machine
4. define the benchmark schema so it matches existing localguys summary fields

## Required output
- setup notes
- smoke test result
- risk list
- go/no-go recommendation for Phase 177 benchmark lane

## Benchmark schema target
- `runtime_name`
- `device_profile`
- `cold_start_ms`
- `avg_runtime_ms`
- `batch_size`
- `success_rate`
- `notes`

## Guardrails
- no core MCC dependency change in the first pass
- no assumption that ANE path is ready for our macOS lane
- keep Metal/GPU as the realistic first target
