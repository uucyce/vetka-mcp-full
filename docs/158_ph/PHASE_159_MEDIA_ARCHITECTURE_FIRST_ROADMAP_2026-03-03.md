# PHASE 159 Roadmap (Architecture-First, No Endpoint Rewrites)
**Date:** 2026-03-03  
**Status:** Draft for execution  
**Scope:** VETKA multimedia stack (JEPA/PULSE, media-MCP, Premiere/FCP lanes, montage UX)

## Why This Roadmap
Цель: идти от архитектуры к API/UI, чтобы не переписывать endpoints повторно.

Execution rule:
1. Freeze contracts and adapter boundaries first.
2. Build internal orchestration/services behind those contracts.
3. Expose/adjust HTTP routes only once at integration phase.
4. Frontend connects after API contract freeze.

## Research Intake (2026-03-04)
External research digest integrated with decisions:
- `docs/158_ph/GROK_RESEARCH_INTAKE_PHASE159_2026-03-04.md`

Execution policy from intake:
1. Queue + idempotency + DLQ first, workflow engine second.
2. `PremiereAdapter` remains the only bridge boundary (live lane hardened behind it).
3. Feature envelope evolves additively (no schema break in existing routes).

## Current Baseline (already done)
1. `ExtractorRegistry` with optional JEPA/PULSE hooks.
2. V-JEPA2 video profile baseline (`2.0/8.0/2.0`) on Berlin dataset.
3. `PremiereAdapter` + `xml_interchange_adapter`.
4. `mcp_live_bridge_adapter` v1 (sub-MCP lane with fallback).
5. `vetka_montage_sheet_v1` schema + tests.
6. Production media budgets (`realtime/background`, never-drop policy).

## User Validation Gaps (UAT, 2026-03-03)
Direct user run revealed critical UX/product gaps that must be fixed before further feature expansion.

### UAT-BLOCKERS (must-fix)
- [~] UAT-B1 Audio playback broken in artifact panel (audio does not play).  
  Backend/API contract fixed and covered by stream-decode E2E tests; UI browser probe still pending.
- [x] UAT-B2 No waveform shown for audio in real user flow.
- [x] UAT-B3 Unified search fails to find imported video files by expected identifiers.
- [~] UAT-B4 Media nodes rendered as generic white document cards instead of media previews (video 16:9 thumb).  
  Done: `FileCard` now has explicit `media` category with dark 16:9 card rendering; m4a treated as binary (no text-preview fallback).  
  Pending: real thumbnail/gif lane (300ms preview path).

### UAT-HIGH
- [ ] UAT-H1 Remove non-monochrome accent colors from media UI surfaces (strict monochrome style policy).
- [ ] UAT-H2 Reduce noisy media-edit banners/messages; keep only actionable signals.
- [x] UAT-H3 Replace user-facing `Jarvis` wording with `VETKA` assistant naming in UI copy.
- [~] UAT-H4 Improve video preview performance (lag/stutter on playback).  
  Added: panel `timeupdate` throttling, video fastplay strategy (`direct` vs `proxy_h264_fastplay`), metadata preload + poster support.  
  Pending: user-run acceptance on large real clips in current UI session.
- [x] UAT-H5 Align artifact panel controls with actual media workflows; hide text-editor-only actions in media context.

### UAT-MEDIUM
- [ ] UAT-M1 Add optional 16:9 preview thumb lane for video cards (target: short animated preview path).
- [ ] UAT-M2 Clarify JEPA role in UX: internal agent capability, not a required user-facing control.

## Immediate UAT Fix Pack (before next architecture layer)
1. UAT-FIX-1: restore audio playback + waveform in artifact media panel.
2. UAT-FIX-2: media search/index parity for video/audio discovery.
3. UAT-FIX-3: media card rendering (video/image thumbnails instead of paper cards).
4. UAT-FIX-4: monochrome UI policy pass + message copy cleanup (`VETKA`, not `Jarvis`).
5. UAT-FIX-5: remove media-irrelevant panel actions and reduce notification noise.

## Architecture Layers (strict order)
## L0 Contract Freeze
- [x] Freeze `media_chunks_v1` + `vetka_montage_sheet_v1` as canonical internal language.
- [x] Freeze `PremiereAdapter` request/response contract (no route-specific fields).
- [x] Freeze `MediaMCPJob` envelope for startup/progress/result/error.  
  Schema added: `docs/contracts/media_mcp_job_v1.schema.json`; tests: `tests/test_phase159_media_mcp_job_schema.py`.
- [x] Add compatibility policy (`v1` additive-only, deprecations via alias window).

Acceptance:
1. Contract docs in `docs/contracts`.
2. Schema validation tests in `/tests`.
3. No direct converter calls from routes (adapter-only boundary).

## L1 Service Core (no HTTP changes)
- [ ] Introduce `MediaPipelineService` as single orchestrator entrypoint.
- [ ] Move route business logic into service methods (`preview/startup/transcript/export/cam/rhythm`).
- [ ] Use `PremiereAdapter` via dependency injection (mode: `xml_interchange` or `mcp_live_bridge`).
- [ ] Add internal typed result models for degraded/status metadata.

Acceptance:
1. Existing routes become thin wrappers.
2. Service-level tests cover main flows.
3. Route regression tests stay green.

## L2 Sub-MCP Orchestration
- [x] Define `media-mcp` job model: `queued/running/partial/done/error`.
- [~] Add background worker queue abstraction (local implementation first).  
  Local in-memory job store added (`src/services/media_mcp_job_store.py`).
- [~] Wire startup endpoint to real async progress stream source (not static phases).  
  Added async startup lane: `POST /api/artifacts/media/startup-async` + `GET /api/artifacts/media/startup-job/{job_id}`.
- [ ] Persist minimal job telemetry for resume/retry.

Acceptance:
1. Long tasks never block API worker.
2. Progress polling or stream returns real job states.
3. Degraded fallback remains deterministic.

L2 progress notes:
1. Added job lifecycle tests: `tests/phase159/test_media_mcp_async_startup.py`.
2. Existing sync startup route remains backward-compatible (`/media/startup` unchanged in response shape).

## L3 Intelligence Plugins (JEPA/PULSE/CAM)
- [ ] Standardize plugin interface: `analyze(input)->features+confidence+latency`.
- [ ] Promote PULSE from proxy/native mix to explicit plugin modes (`native`, `proxy`, `hybrid`).
- [ ] Normalize CAM/JEPA/PULSE outputs into one feature envelope for timeline scoring.
- [ ] Add plugin capability registry and runtime health flags.

Acceptance:
1. Same feature envelope consumed by semantic-links/rhythm/cam overlays.
2. Plugin mode switchable without endpoint changes.
3. Integration tests on Berlin fixtures.

## L4 API Freeze (single pass)
- [ ] Refactor `/api/artifacts/media/*` endpoints to service calls only.
- [ ] Keep response shapes backward-compatible; add only additive fields.
- [ ] Add explicit API contract tests for each endpoint.

Acceptance:
1. No endpoint signature churn after this phase.
2. Existing client works without patches.
3. API schema snapshot tests pass.

## L5 Frontend Integration (after API freeze)
- [ ] Finish advanced timeline lanes/multicam UX using frozen API.
- [ ] CAM heat-track + semantic-edge overlays in panel.
- [ ] Real startup progress UI from media-MCP states.
- [ ] Jarvis multi-step fallback loop (missing script/sheet/transcript).

Acceptance:
1. No backend rewrites required for UI completion.
2. UI flows covered by smoke/integration tests.

## L6 Premiere Live Bridge Hardening
- [ ] Replace file-bridge v1 with robust adapter transport (still behind `PremiereAdapter`).
- [ ] Add command ack/timeout/retry/idempotency contract.
- [ ] Introduce safe allowlist for operations in live mode.

Acceptance:
1. Live bridge failures always degrade to XML lane.
2. No project-breaking operations outside allowlist.

## L7 Final Stabilization
- [ ] E2E scenario: ingest -> scan -> timeline assist -> export -> roundtrip check.
- [ ] Performance baselines for realtime/background budgets.
- [ ] Release checklist and operator runbook.

## Anti-Rewrite Rules
1. Routes cannot import low-level converters directly.
2. UI cannot call non-contract debug fields.
3. New feature work must extend service/plugin layers, not route handlers.
4. Breaking response changes require versioned endpoint or alias period.

## Immediate Next 3 Tasks
1. UAT-FIX-1 (partial done): Audio playback stream-source fix + non-WAV waveform backend extraction.
2. UAT-FIX-2: Unified search media discovery fixes (video/audio) + regression tests.
3. UAT-FIX-4: monochrome style + copy pass for media mode surfaces.

UAT-FIX-1 progress notes:
1. Implemented: non-WAV waveform via ffmpeg decode + fallback proxy.
2. Implemented: media panel uses raw stream endpoint for audio/video (not base64 payload).
3. Implemented: MIME normalization for `.m4a` (`audio/mp4a-latm` -> `audio/mp4`) in files API.
4. Implemented: media toolbar now hides text-edit actions for media artifacts.
5. Added tests: `tests/test_phase159_media_playback_contract.py`.
6. Added: stream-level E2E playback checks (`/api/files/raw` audio/video -> ffprobe decodable) in `tests/phase159/test_media_stream_playback_e2e.py`.
7. Added: media-toolbar contract checks (hide edit/save/save-as for media + raw stream source priority) in `tests/phase159/test_artifact_media_toolbar_contract.py`.
8. Remaining: optional browser DOM probe that asserts `currentTime` advances in artifact panel runtime.
9. Added video fastplay assets pipeline in preview API:
   `playback.source_url`, `playback.strategy`, `preview_assets.poster_url`, `preview_assets.animated_preview_url_300ms`.
10. Added fullscreen action in video panel (native browser fullscreen API).
11. UI-noise reduction: media diagnostics moved under explicit `i` toggle; media toolbar uses `Info` instead of `Copy`.
12. Default policy updated: no proxy transcode by default; preview derivatives (poster + 300ms dynamic preview) enabled by default.
13. Added real-browser DOM playback probe (`scripts/media_dom_playback_probe.sh`) + pytest gate (`tests/phase159/test_media_dom_playback_probe.py`) to assert `currentTime` advances after play.

Future enhancement note (queued):
1. Add adaptive playback scale ladder (editor-style `full/1/2/1/4/1/8/1/16/1/32`) as runtime quality control, instead of rigid pixel presets.
2. Add explicit selectable quality profiles (YouTube-style) mapped to adaptive ladder policy.

## Video Player Split Decision (2026-03-04)
Decision:
1. Keep unified `ArtifactShell`.
2. Extract dedicated `VideoArtifactPlayer`.
3. Integrate via adapter contract (no duplication of pin/download/open/close behaviors).

Detailed contract:
1. `docs/158_ph/VIDEO_ARTIFACT_PLAYER_CONTRACT_V1_2026-03-04.md`

Execution order:
1. [x] Add component scaffold + no-autoplay/source-switch correctness.  
   `client/src/components/artifact/viewers/VideoArtifactPlayer.tsx` wired into `ArtifactPanel`.
2. [x] Add hover-overlay controls (monochrome).
3. [x] Add quality/speed/volume menus.
4. [x] Preserve artifact actions and events.
5. [x] Run contract+integration tests from contract doc section 6.
6. [x] Hide diagnostic preview blocks (`poster`, `dynamic preview 300ms`) from default panel; expose only via `i` diagnostics toggle.

## Sub-Roadmap Linkage (2026-03-04)
For fullscreen/multi-window track (native window fullscreen + detached media window + sync contracts):
1. `docs/158_ph/PHASE_159_ARTIFACT_WINDOW_FULLSCREEN_SUBROADMAP_2026-03-04.md`
