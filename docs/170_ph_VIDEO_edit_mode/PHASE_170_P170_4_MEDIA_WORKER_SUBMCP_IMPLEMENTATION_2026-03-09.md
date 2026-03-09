# PHASE 170 P170.4 Media Worker MCP / sub-MCP Implementation
**Date:** 2026-03-09  
**Status:** narrow implementation plan  
**Scope:** isolate heavy CUT media jobs from control/runtime MCP

## Goal
Define the first concrete worker-lane contract for `VETKA CUT` so heavy media jobs do not block:
1. CUT bootstrap,
2. project-state hydrate,
3. timeline/graph edits,
4. standalone shell responsiveness.

## Markers
- `MARKER_170.WORKER.MEDIA_SUBMCP`
- `MARKER_170.WORKER.BACKPRESSURE`
- `MARKER_170.WORKER.RETRY_CANCEL`
- `MARKER_170.WORKER.DEGRADED_SAFE`

## Why now
Current CUT runtime already has:
1. bootstrap,
2. async scene assembly,
3. timeline apply,
4. scene-graph apply,
5. standalone shell.

The next risk is obvious: once transcript, waveform, semantic links, CAM overlay, JEPA/PULSE enrichments start, the same MCP lane will become too heavy.

## Worker topology (V1)
```text
CUT Shell
   |
   v
CUT MCP (control plane)
   |
   +--> local CutMCPJobStore
   |
   +--> Media Worker MCP / sub-MCP
            |
            +--> transcript worker
            +--> waveform worker
            +--> semantic-links worker
            +--> cam-overlay worker
            +--> export worker
```

## Control-plane rule
`CUT MCP` owns:
1. project identity,
2. bootstrap state,
3. job creation,
4. job status polling,
5. degraded-safe response envelopes.

Worker lane owns:
1. long-running execution,
2. retries,
3. partial outputs,
4. heavy adapters and external tools.

## Job state expectations
`cut_mcp_job_v1` should expose at least:
1. `state`
2. `progress`
3. `retry_count`
4. `route_mode`
5. `cancel_requested`
6. `degraded_mode`
7. `degraded_reason`

State meanings:
1. `queued` -> accepted, not started
2. `running` -> active worker execution
3. `partial` -> partial artifacts available
4. `done` -> complete result available
5. `error` -> terminal failure
6. `cancelled` -> user/system cancelled before completion

## V1 worker task families
1. `transcript_normalize`
2. `waveform_build`
3. `semantic_links`
4. `cam_overlay`
5. `rhythm_assist`
6. `export_xml`

## Backpressure policy (V1)
1. max one heavy worker job per project for the same task family
2. max two heavy worker jobs total per sandbox before queueing
3. `route_mode=control` is reserved for lightweight MCP operations only
4. queue overflow must return recoverable degraded-safe status, not crash runtime

## Retry / cancel policy (V1)
1. retries are explicit and counted in job metadata
2. idempotent tasks may retry automatically once
3. non-idempotent export tasks require explicit retry command later
4. cancel requests set `cancel_requested=true` immediately
5. if execution has not started, job becomes `cancelled`
6. if execution is already running, control plane exposes cancel intent and worker exits at next safe checkpoint

## Degraded-safe rule
When a worker task fails, CUT must still remain editable.

Examples:
1. transcript failed -> timeline still opens, transcript panel marked degraded
2. semantic links failed -> graph still opens without overlay edges
3. waveform failed -> audio lane still exists, waveform UI hidden or placeholder

## Persistence rule
Do not persist volatile worker queue state into:
- `cut_project.json`
- `cut_bootstrap_state.json`

Allowed persistence:
1. job envelope snapshots if needed later
2. stable task outputs in runtime/storage
3. edit-safe degraded metadata

## Immediate implementation slice
1. extend `cut_mcp_job_v1` with retry/cancel/degraded metadata
2. add `POST /api/cut/job/{job_id}/cancel`
3. keep cancel semantics in control plane even before full worker subprocess split
4. document task-family mapping before adding real FFmpeg/Whisper workers

## Baseline now implemented
1. `cut_mcp_job_v1` carries retry/cancel/degraded metadata
2. control plane exposes `POST /api/cut/job/{job_id}/cancel`
3. first real worker-backed task exists: `POST /api/cut/worker/waveform-build-async`
4. duplicate active worker tasks are suppressed per `project_id + task_type + sandbox_root`
5. sandbox-level background backpressure blocks the third active worker/control-plane background job

## Follow-up
After this narrow step:
1. add explicit worker-task contract draft (`cut_worker_task_v1`)
2. add queue limits / duplicate-task suppression
3. add first real worker-backed task, likely transcript or waveform
