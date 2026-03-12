# Vetka MCP & Multitask Coordination Audit

## 1. Architecture overview
- **Async job store:** `src/services/media_mcp_job_store.py` holds in-memory `MediaMCPJobStore` (`schema_version` `media_mcp_job_v1`). Phase 159 roadmap and `docs/contracts/media_mcp_job_v1.schema.json` describe states (`queued/running/partial/done/error`), progress, `dlq`, and `trace`. `MARKER_158.RUNTIME.MEDIA_MCP_SPLIT` emphasizes separating heavy media orchestration from UI thread.
- **Routes:** `POST /api/artifacts/media/startup` (synchronous) is in `src/api/routes/artifact_routes.py`; doc `PHASE_159_MEDIA_ARCHITECTURE_FIRST_ROADMAP_2026-03-03.md` adds async lane (`/media/startup-async` + `/media/startup-job/{job_id}`) with tests `tests/phase159/test_media_mcp_async_startup.py`. Side note: implement job lifecycle hooking `MediaMCPJobStore` to background workers before exposing to UI.
- **Multitasking & agents:** `docs/158_ph/PHASE_158_MULTIMEDIA_VJEPA_ROADMAP_CHECKLIST_2026-03-02.md` and `docs/159_ph_bugs/PHASE_130_160_RECON_SUMMARY` highlight connectors to JEPA/PULSE, CAM overlays, and `media_mcp` job gating. The overall pattern is: orchestrator (MCP_MEDIA) dispatches asynchronous analysis (FFprobe/Whisper/Apple Vision) with fallback questions (missing script, montage sheet, transcript). Each job updates `fallback_questions`, `phases`, `stats`, and `next_actions` returned to UI.
- **Coordination:** Jobs should be orchestrated via Orchestrator-Worker pattern (see `docs/02_BACKEND_DEVELOPMENT/grok_research_02_multi_agent_coordination.md`). Use the job store for queueing and `Claude/Jarvis` fallback loops to spawn worker tasks for transcription, rhythm assist, semantic links, etc. Each worker updates job progress and writes to Qdrant/TripleWrite.

## 2. Connecting to the MCP core
- **Hooking in:** instantiate `MediaMCPJobStore` via `get_media_mcp_job_store()` and call `create_job()` when `/media/startup-async` begins (store `scope_path`, `quick_scan_limit`). Worker threads should poll the job store to update progress; once ready, use `update_job` to set `result` (stats + signals). Frontend poll via `/media/startup-job/{job_id}` (per tests). `docs/contracts/media_mcp_job_v1.schema.json` defines fields to expose.
- **Safe sandbox copy:** create sandbox environment with a dedicated job store (copy file to sandbox). Use `python -m venv sandbox` and symlink `src/services/media_mcp_job_store.py`. Run job tests inside sandbox to ensure concurrency state is isolated. Markers `MARKER_158.RUNTIME.MEDIA_BACKPRESSURE` highlight backpressure controls; follow them to limit job concurrency in sandbox (e.g., throttle `asyncio` worker loops).
- **Async agents:** identify each worker (transcript/rhythm/cam/semantic). In sandbox, stub connectors (Whisper, AppleVision) to return canned outputs so job store can switch to `done` state. Use `tests/phase159/` as blueprint for job life-cycle coverage.

## 3. Recommendations
1. Expand `media/startup` to enqueue `media_mcp_job` for heavy scans, returning `job_id` and polling endpoint. 2. Use `docs/contracts/media_mcp_job_v1.schema.json` for validation before storing results. 3. Document agent coordination pattern referencing Grok research (Orchestrator-Worker + fallbacks) and tie to `fallback_questions` in API responses.

Report saved as `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/docs/169_ph_editmode_recon/VetkaMCPAudit.md`.
