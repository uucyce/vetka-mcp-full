# VETKA CUT MCP Bootstrap Contract V1
**Date:** 2026-03-09  
**Status:** draft  
**Scope:** first bootstrap handshake between CUT UI / CLI and standalone `CUT MCP`

## Purpose
Bootstrap a `VETKA CUT` project from a folder or mirrored sandbox without forcing the UI to know internal worker topology.

This contract is the CUT-side analogue of early `media/startup`, but for standalone sandbox operation and future `cut_project_v1` creation.

## Marker
- `MARKER_170.MCP.BOOTSTRAP.CONTRACT_V1`

## Endpoint
- `POST /api/cut/bootstrap`

## Request
```json
{
  "source_path": "/absolute/path/to/project_or_media_folder",
  "sandbox_root": "/absolute/path/to/VETKA_CUT_SANDBOX",
  "project_name": "Optional display name",
  "mode": "create_or_open",
  "quick_scan_limit": 5000,
  "bootstrap_profile": "default",
  "use_core_mirror": true,
  "create_project_if_missing": true
}
```

## Request fields
- `source_path`: absolute source path to media/project folder
- `sandbox_root`: absolute CUT sandbox root
- `project_name`: optional friendly name
- `mode`: one of `create_or_open`, `open_existing`, `create_new`
- `quick_scan_limit`: startup scan bound for fast bootstrap
- `bootstrap_profile`: initial runtime profile, default `default`
- `use_core_mirror`: whether CUT MCP should expect/use mirrored core files
- `create_project_if_missing`: if false, missing project returns recoverable error

## Response
```json
{
  "success": true,
  "schema_version": "cut_bootstrap_v1",
  "project": {
    "schema_version": "cut_project_v1",
    "project_id": "cut_demo_1234abcd",
    "display_name": "Demo Cut",
    "source_path": "/absolute/path/to/project_or_media_folder",
    "sandbox_root": "/absolute/path/to/VETKA_CUT_SANDBOX"
  },
  "bootstrap": {
    "mode": "create_or_open",
    "state": "ready",
    "use_core_mirror": true,
    "core_mirror_root": "/absolute/path/to/VETKA_CUT_SANDBOX/core_mirror",
    "estimated_ready_sec": 3.2,
    "job_id": "optional-async-job-id"
  },
  "stats": {
    "media_files": 12,
    "video_files": 8,
    "audio_files": 4,
    "image_files": 0
  },
  "missing_inputs": {
    "script_or_treatment": true,
    "montage_sheet": true,
    "transcript_or_timecodes": false
  },
  "fallback_questions": [],
  "phases": [
    {"id": "discover", "label": "Scope discovery", "status": "done", "progress": 0.33},
    {"id": "project", "label": "Project bootstrap", "status": "done", "progress": 0.66},
    {"id": "align", "label": "Timeline bootstrap", "status": "ready", "progress": 1.0}
  ],
  "next_actions": [
    "open_cut_project",
    "poll_bootstrap_job",
    "start_scene_assembly"
  ],
  "degraded_mode": false,
  "degraded_reason": ""
}
```

## Response rules
1. `project` must be present on success.
2. `schema_version` must be `cut_bootstrap_v1`.
3. `project.schema_version` must be `cut_project_v1`.
4. `job_id` is optional for fast sync boots, expected for async-heavy boots.
5. `phases`, `fallback_questions`, `missing_inputs`, `degraded_mode` stay stylistically aligned with existing media startup responses.

## Failure shape
```json
{
  "success": false,
  "schema_version": "cut_bootstrap_v1",
  "error": {
    "code": "sandbox_missing",
    "message": "Sandbox root does not exist",
    "recoverable": true
  },
  "degraded_mode": true,
  "degraded_reason": "sandbox_missing"
}
```

## Compatibility notes
1. This contract intentionally resembles `/media/startup` in `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/api/routes/artifact_routes.py:1229`.
2. CUT bootstrap adds `project` and `bootstrap` objects because standalone CUT must manage sandbox/project state, not just media scope state.
3. Async boot should remain compatible with `media_mcp_job_v1` style job envelopes when a background lane is used.
