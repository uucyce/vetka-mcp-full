# PHASE 170 cut_worker_task_v1 Draft
**Date:** 2026-03-09  
**Status:** first draft  
**Scope:** worker task contract for background CUT media jobs

## Goal
Define a small typed task envelope for CUT worker-lane execution.

This is not the same thing as `cut_mcp_job_v1`.
- `cut_mcp_job_v1` = control-plane job state
- `cut_worker_task_v1` = worker task identity and execution semantics

## Marker
- `MARKER_170.WORKER.MEDIA_SUBMCP`
- `MARKER_170.WORKER.BACKPRESSURE`
- `MARKER_170.WORKER.RETRY_CANCEL`
- `MARKER_170.WORKER.DEGRADED_SAFE`

## Required fields
1. `schema_version`
2. `task_id`
3. `project_id`
4. `task_type`
5. `route_mode`
6. `priority`
7. `status`
8. `created_at`

## Task types (V1)
1. `waveform_build`
2. `transcript_normalize`
3. `semantic_links`
4. `cam_overlay`
5. `rhythm_assist`
6. `export_xml`

## Rule
Worker tasks may write stable outputs into runtime/storage,
but control-plane state remains canonical for polling.

## First real task
The first worker-backed CUT task is `waveform_build`.
It writes a persisted `cut_waveform_bundle_v1` artifact and returns a `cut_worker_task_v1` summary inside the job result.
