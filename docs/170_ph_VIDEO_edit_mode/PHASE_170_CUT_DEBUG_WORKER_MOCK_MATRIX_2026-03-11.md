# Phase 170 CUT Debug Shell Worker-Actions Mock Matrix

## Scope
This document lists the mocked routes and payload shapes required for the CUT debug shell worker-actions smoke test.

## Mocked Endpoints

### 1. `/api/cut/project-state`
**Method:** GET  
**Purpose:** Provides the initial project state for the CUT editor.  
**Response Shape:**  
```json
{
  "success": true,
  "schema_version": "cut_project_state_v1",
  "project": {
    "project_id": "string",
    "display_name": "string",
    "source_path": "/tmp/cut/smoke-source.mov",
    "sandbox_root": "/tmp/cut-smoke-worker-actions",
    "state": "ready"
  },
  "runtime_ready": true,
  "graph_ready": true,
  "waveform_ready": true,
  "transcript_ready": true,
  "thumbnail_ready": true,
  "slice_ready": true,
  "timecode_sync_ready": false,
  "sync_surface_ready": true,
  "meta_sync_ready": false,
  "time_markers_ready": false,
  "timeline_state": {
    "timeline_id": "main",
    "selection": { "clip_ids": [], "scene_ids": [] },
    "lanes": [
      {
        "lane_id": "video_main",
        "lane_type": "video_main",
        "clips": [
          {
            "clip_id": "clip_a",
            "scene_id": "scene_a",
            "start_sec": 1,
            "duration_sec": 4,
            "source_path": "/tmp/cut/shot-a.mov",
            "sync": {
              "method": "waveform",
              "offset_sec": 0.24,
              "confidence": 0.92,
              "reference_path": "/tmp/cut/master.wav"
            }
          }
        ]
      }
    ]
  },
  "waveform_bundle": {
    "items": [
      {
        "item_id": "string",
        "source_path": "/tmp/cut/shot-a.mov",
        "waveform_bins": [number]
      }
    ]
  },
  "thumbnail_bundle": {
    "items": [
      {
        "item_id": "string",
        "source_path": "/tmp/cut/shot-a.mov",
        "modality": "video",
        "duration_sec": number
      }
    ]
  },
  "sync_surface": {
    "items": [
      {
        "item_id": "string",
        "source_path": "/tmp/cut/shot-a.mov",
        "reference_path": "/tmp/cut/master.wav",
        "recommended_method": "waveform",
        "recommended_offset_sec": number,
        "confidence": number
      }
    ]
  },
  "time_marker_bundle": { "items": [] },
  "recent_jobs": [],
  "active_jobs": []
}
```

### 2. `/api/cut/debug-shell/bootstrap`
**Method:** GET  
**Purpose:** Initializes the debug shell and returns shell readiness status.  
**Response Shape:**  
```json
{
  "success": true,
  "shell_ready": true
}
```

### 3. `/api/cut/debug-shell/worker/action`
**Method:** POST  
**Purpose:** Handles worker actions triggered from the debug shell (e.g., run, stop, pause).  
**Request Shape:**  
```json
{
  "action": "string", // e.g., "run", "stop", "pause"
  "worker_id": "string", // optional
  "job_id": "string", // optional
  "parameters": {} // optional action-specific parameters
}
```
**Response Shape:**  
```json
{
  "success": true,
  "action_executed": true,
  "worker_id": "string", // echoed back
  "job_id": "string", // echoed back
  "result": {} // optional action-specific result
}
```

### 4. `/api/cut/debug-shell/worker/jobs`
**Method:** GET  
**Purpose:** Returns the list of current worker jobs for display in the debug shell.  
**Response Shape:**  
```json
{
  "success": true,
  "jobs": [
    {
      "job_id": "string",
      "worker_id": "string",
      "action": "string",
      "status": "queued|running|completed|failed",
      "progress": number, // 0-100
      "created_at": "ISO timestamp",
      "started_at": "ISO timestamp|null",
      "completed_at": "ISO timestamp|null",
      "result": {} // optional
    }
  ]
}
```

## Usage Notes
- The smoke test only requires successful responses (200 OK) with the above shapes.
- No actual backend worker processes are spawned or interacted with.
- All endpoints are mocked at the API routing level within the test spec.
- The debug shell UI should display job statuses from the `/api/cut/debug-shell/worker/jobs` endpoint.
- Worker actions like "run" should transition jobs from queued to running to completed in the mock responses if statefulness is desired, but the smoke test only verifies endpoint calls.