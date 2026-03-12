# PHASE 170 VETKA CUT Roadmap + Recon Markers
**Date:** 2026-03-09  
**Status:** Draft roadmap with recon intake  
**Scope:** sandbox launch plan for `VETKA CUT`

## Why this roadmap
Цель: не прыгать сразу в UI монтажки, а последовательно собрать standalone CUT вокруг mirrored `VETKA Core`, MCP isolation и реальных media workflows.

Execution order:
1. Recon -> freeze assumptions.
2. Sandbox -> boot mirrored core.
3. MCP -> separate orchestration.
4. Worker -> isolate heavy media tasks.
5. UI -> connect only after runtime loop works.
6. Reintegration -> only after stability.

## Recon intake (used as source set)
1. `docs/169_ph_editmode_recon/Stage1_GPT-5.1-Codex-Mini.md`
2. `docs/169_ph_editmode_recon/Stage1_GPT-5.1-Codex-CandidatePriority.md`
3. `docs/169_ph_editmode_recon/Stage1_GPT-5.1-Codex-CinemaFactoryAudit.md`
4. `docs/169_ph_editmode_recon/VetkaScanSearchAudit.md`
5. `docs/169_ph_editmode_recon/VetkaMCPAudit.md`
6. `docs/169_ph_editmode_recon/VJepaPulseIntegration.md`
7. `docs/169_ph_editmode_recon/VetkaMemorySystemsAudit.md`
8. `docs/158_ph/VETKA_MEDIA_MODE_FOLDER_SPEC_V1.md`
9. `docs/158_ph/PHASE_159_MEDIA_ARCHITECTURE_FIRST_ROADMAP_2026-03-03.md`

## Strategic conclusion from recon
1. The main asset is `VETKA Core`, not external editor imitation.
2. `Olive` is useful as UX reference, not architecture.
3. `CinemaFactory` is useful as pipeline/reference source for analysis/export patterns.
4. Async orchestration is mandatory before rich editor UI.
5. Memory/context is a differentiator, but current VETKA history shows integration gaps and duplication risks.

## Phase roadmap
### P170.1 Sandbox Foundation
- [x] Create standalone `VETKA CUT` sandbox directory/runtime.
- [x] Define env isolation, ports, cache paths, storage paths.
- [x] Create mirror manifest of VETKA Core modules copied into sandbox.
- [x] Define Qdrant namespace / collection-prefix strategy.

Markers:
1. `MARKER_170.SANDBOX.CREATE`
2. `MARKER_170.SANDBOX.ENV_ISOLATION`
3. `MARKER_170.SANDBOX.CORE_MIRROR_MANIFEST`
4. `MARKER_170.SANDBOX.STORAGE_NAMESPACE`

### P170.2 Core Mirror Boot
- [x] Mirror watcher/import stack baseline through manifest + sync scripts.
- [x] Mirror extractor registry + multimodal contracts baseline through Tier 1 manifest.
- [ ] Mirror memory/context modules needed by CUT.
- [ ] Boot namespaced vector/search flow in sandbox.

Markers:
1. `MARKER_170.CORE.WATCHER_MIRROR`
2. `MARKER_170.CORE.EXTRACTOR_MIRROR`
3. `MARKER_170.CORE.MEMORY_MIRROR`
4. `MARKER_170.CORE.QDRANT_NAMESPACE`

### P170.3 CUT MCP
- [x] Create dedicated `CUT MCP` orchestration layer.
- [x] Add startup/project bootstrap contract.
- [x] Add job orchestration for analyze/scene/timeline flows.
- [x] Keep response shape compatible with shared media contracts where possible.

Markers:
1. `MARKER_170.MCP.CUT_SERVER`
2. `MARKER_170.MCP.STARTUP_CONTRACT`
3. `MARKER_170.MCP.JOB_ORCHESTRATION`
4. `MARKER_170.MCP.CONTRACT_COMPAT`
5. `MARKER_170.MCP.PROJECT_STATE_V1`
6. `MARKER_170.MCP.TIMELINE_APPLY_V1`
7. `MARKER_170.MCP.SCENE_GRAPH_APPLY_V1`

### P170.4 Media Worker MCP / sub-MCP
- [ ] Isolate heavy FFmpeg/transcript/vision/rhythm tasks.
- [x] Add retry/backpressure/cancel semantics baseline at control-plane contract level.
- [ ] Route long-running jobs away from main CUT control lane.
- [x] Return partial states and degraded-safe statuses at contract/job-envelope level.
- [x] Add audio-based sync worker for external recorders / second-camera audio using waveform peaks first, then correlation refinement.
- [x] Freeze `audio_sync` alignment result contract: source pair/group, detected offset, confidence, method, degraded_reason.
- [x] Run recon on existing open-source audio sync options before custom implementation to avoid inventing a weak sync pipeline.
- [x] Add comparison bakeoff tests for sync methods and decide whether hybrid `peaks + correlation` becomes the CUT baseline.
- [x] Add standard timecode sync path as first-class worker/result alongside waveform sync.
- [x] Freeze shared sync result model so `timecode`, `waveform`, and future `meta_sync` can coexist in one alignment surface.

Markers:
1. `MARKER_170.WORKER.MEDIA_SUBMCP`
2. `MARKER_170.WORKER.BACKPRESSURE`
3. `MARKER_170.WORKER.RETRY_CANCEL`
4. `MARKER_170.WORKER.DEGRADED_SAFE`
5. `MARKER_170.WORKER.AUDIO_SYNC_V1`
6. `MARKER_170.RECON.OPEN_SOURCE_AUDIO_SYNC`
7. `MARKER_170.WORKER.AUDIO_SYNC_BAKEOFF`
8. `MARKER_170.WORKER.TIMECODE_SYNC_V1`
9. `MARKER_170.CONTRACT.MULTI_SYNC_ALIGNMENT_V1`

### P170.5 Editorial Data Model
- [x] Define `cut_project_v1`.
- [x] Define `cut_timeline_state_v1`.
- [x] Define `cut_scene_graph_v1`.
- [x] Map all of them back to `media_chunks_v1` and `vetka_montage_sheet_v1`.
- [x] Freeze cognitive time marker contracts before player/CAM integration starts.

Markers:
1. `MARKER_170.CONTRACT.CUT_PROJECT_V1`
2. `MARKER_170.CONTRACT.CUT_TIMELINE_STATE_V1`
3. `MARKER_170.CONTRACT.CUT_SCENE_GRAPH_V1`
4. `MARKER_170.CONTRACT.SHARED_MAPPING`
5. `MARKER_170.CONTRACT.CUT_TIME_MARKER_V1`

### P170.6 Standalone UI Shell
- [ ] Build CUT shell separate from main VETKA UI.
- [x] Connect to CUT MCP only at contract level.
- [x] Add folder bootstrap, media overview, timeline shell contract.
- [x] Keep node-graph optional until timeline flow is stable.
- [x] Run design recon against current VETKA style system: color palette, icon rules, panel shapes, spacing rhythm.
- [x] Define CUT UI unification rules: simple white icons, contextual buttons, smart panels, and "swedish buffet" interaction model.
- [ ] Revisit `player_playground` as donor surface for compact overlay toolbar, preview quality flyout, and minimal contextual controls.
- [ ] Adopt only selective player-lab patterns into CUT preview/storyboard surfaces; do not couple CUT shell to player-lab runtime directly.
- [ ] Prepare player/CUT bridge for time markers, comment markers, and CAM-linked cognitive markers before rich timeline UI.
- [ ] Keep donor-player default route in `pure player mode`: no external lab UI, only overlay controls and future contextual actions.
- [ ] Preserve standalone player runtime as a reusable preview surface for CUT; do not pull CUT orchestration into player donor.
- [ ] Gate contextual action icon by VETKA status:
  `not in VETKA -> show VETKA ingest action`
  `already in VETKA -> hide ingest action and enable moment-star / marker actions`
- [ ] Support transitional donor-player behavior before Core/CUT exists:
  `VETKA logo press -> provisional local marker/comment event`
  `Core/CUT appears -> migrate provisional events into canonical CUT markers`
  `after handoff -> replace VETKA logo with star`
- [ ] Treat `favorite` in editorial surfaces as a time marker action only, never as a primary file-level state.
- [ ] Keep preview quality selector in donor-player because CUT preview surfaces will need the same performance discipline for high-resolution footage.

Architectural rule:
- player donor, CUT shell, and future VETKA edit mode must share one editorial identity model:
  `no primary file-level favorite`
  `time marker is the canonical cognitive unit`
  `star means favorite moment`
  `CAM and chat attach to markers, not to a parallel file-favorite system`
- keep player-lab docs aligned with this rule so donor patterns do not reintroduce file-favorite logic into CUT.
- allow standalone donor-player to capture provisional `VETKA`-logo events before Core/CUT is present, but require those events to migrate into canonical marker contracts instead of becoming a second permanent state system.

Design timing note:
- Do not start full design-system recon before CUT MCP read/write surfaces are stable enough to avoid UI-contract churn.
- Start `MARKER_170.UI.DESIGN_UNIFICATION_RECON` after these are in place: `project-state`, worker outputs (`waveform`, `transcript`, `thumbnail`), worker queue visibility, and storyboard strip baseline.
- That means: design recon belongs after current worker/state foundation and before rich timeline interactions, smart inspector panels, node canvas, and contextual editing surfaces.
- Practical gate: once storyboard thumbnails are live and no endpoint shape changes are expected for the current shell slice, run design recon immediately as the next UI-focused recon step.
- Player-lab adoption gate: after storyboard strip baseline and shell style alignment, but before rich timeline chrome. This keeps good minimalism patterns while avoiding a second UI architecture.

Markers:
1. `MARKER_170.UI.STANDALONE_SHELL`
2. `MARKER_170.UI.TIMELINE_BOOTSTRAP`
3. `MARKER_170.UI.SCENE_GRAPH_OPTIONAL`
4. `MARKER_170.UI.MCP_ONLY_BINDING`
5. `MARKER_170.UI.STANDALONE_SHELL_CONTRACT_V1`
6. `MARKER_170.UI.DESIGN_UNIFICATION_RECON`
7. `MARKER_170.UI.SMART_PANELS_CONTEXTUAL_ACTIONS`
8. `MARKER_170.UI.PLAYER_LAB_ADOPTION`
9. `MARKER_170.INTEL.TIME_MARKERS_CAM_BRIDGE`
10. `MARKER_170.UI.PURE_PLAYER_DONOR`
11. `MARKER_170.UI.VETKA_STATUS_GATED_ACTIONS`
12. `MARKER_170.UI.TRANSITIONAL_VETKA_TO_STAR_HANDOFF`

### P170.7 Intelligence Overlays
- [ ] Add semantic links overlay.
- [ ] Add CAM/contextual suggestions.
- [ ] Add JEPA/PULSE assists as overlay/enrichment, not hard dependency.
- [ ] Add fallback question loop powered by CUT MCP.
- [ ] Add cognitive time markers: comments, favorites, CAM markers, and pause-to-pause smart context slices.
- [ ] Add ranking logic where media importance increases with density/quality of marked moments instead of file-level favorite only.
- [ ] Add MCP/API write-read path for time markers compatible with player-lab bridge.
- [ ] Use simple window-around-anchor slice first, then upgrade marker creation to pause-to-pause / silence-aware segmentation.
- [x] Add interim transcript-aware smart slice heuristic before full pause/silence-aware segmentation.
- [x] Capture external recon for `pydub` / `pyannote` pause-aware slicing candidates and baseline hybrid recommendation.
- [x] Add comparison bakeoff tests for slicing methods and decide whether hybrid transcript + silence windows becomes the CUT baseline.
- [x] Add first worker-backed `energy_pause_v1` slice bundle for offline pause/silence-aware segmentation.
- [ ] Allow marker payloads to carry `cam_payload`, `chat_thread_id`, and `comment_thread_id` without forcing full CUT runtime into the donor-player.
- [ ] Keep media ranking derived from weighted marked moments, not from persistent file star state.
- [ ] Treat pre-Core `VETKA`-logo captures as provisional events only; once Core/CUT is online they must be absorbed into the same marker/ranking model instead of remaining a parallel store.
- [ ] Add `meta_sync` overlay path for scenario/semantic/visual/rhythm alignment once hard sync baselines are stable.
- [x] Freeze initial `meta_sync` result contract as proposal/refinement-only layer; do not wire runtime until hard sync surfaces are stable.
- [ ] Keep `meta_sync` secondary to hard sync methods: `timecode -> waveform -> meta_sync refinement`, not replacement.

Architectural rule:
- `star time marker` is the same core primitive across player, CUT, and future edit-mode reintegration.
- intelligence overlays may enrich marker creation and ranking, but they must not replace time markers with opaque CAM-only state.

Markers:
1. `MARKER_170.INTEL.SEMANTIC_LINKS`
2. `MARKER_170.INTEL.CAM_CONTEXT`
3. `MARKER_170.INTEL.JEPA_PULSE_OVERLAY`
4. `MARKER_170.INTEL.FALLBACK_LOOP`
5. `MARKER_170.INTEL.COGNITIVE_TIME_MARKERS`
6. `MARKER_170.INTEL.META_SYNC_V1`
7. `MARKER_170.INTEL.META_SYNC_GUARDRAIL`
6. `MARKER_170.INTEL.MOMENT_RANKING`
7. `MARKER_170.MCP.TIME_MARKERS_V1`
8. `MARKER_170.INTEL.SLICE_METHOD_BAKEOFF`

### P170.8 Upstream Sync + Reintegration Path
- [ ] Define automated or scripted sync from main VETKA core.
- [ ] Maintain list of mirrored modules and local overrides.
- [ ] Test reintegration path as future `edit_mode` mount.
- [ ] Keep CUT stable as standalone even before reintegration.

Markers:
1. `MARKER_170.SYNC.UPSTREAM_PULL`
2. `MARKER_170.SYNC.MIRROR_DIFF_POLICY`
3. `MARKER_170.REINTEGRATION.EDIT_MODE_PATH`
4. `MARKER_170.REINTEGRATION.CONTRACT_BRIDGE`

## Immediate priorities
1. Freeze standalone shell contract and first UI skeleton.
2. Separate heavy worker lane before real-user media tests.
3. Add schema coverage for new MCP read/write surfaces.
4. Keep CUT-specific contracts frozen before timeline complexity expands.
5. Add storyboard/thumbnail bridge as first visual CUT layer before rich timeline UI.
6. Run VETKA design-system recon before visual polish or icon work.
7. Keep player-lab as a donor/reference track, not a parallel UI foundation.
8. Freeze the donor-player rule set:
   `VETKA ingest action before indexing`
   `time-marker actions after indexing`
   `preview quality always available for performance control`

## Known risks from recon
1. Existing VETKA docs/tests mention async media lanes that are only partially realized in runtime.
2. Memory stack is powerful but historically had duplication/integration gaps (`CAM`, `STM`, `MGC`).
3. Direct editing inside mirrored core can make future sync painful.
4. Rich node UI too early can mask unresolved orchestration problems.
5. Heavy media jobs can pollute shared infra if namespace isolation is weak.

## Anti-rewrite rules
1. Do not fork shared contracts without namespace/version reason.
2. Do not couple CUT UI directly to worker internals.
3. Do not treat JEPA/PULSE as hard blockers for initial CUT launch.
4. Do not move unstable CUT runtime into main VETKA before exit criteria.

## Exit criteria for Phase 170
1. Sandbox boots with mirrored core.
2. CUT MCP controls project startup and job state.
3. Worker lane handles heavy tasks outside UI/control loop.
4. Shared contracts remain compatible with future VETKA reintegration.
5. CUT can be tested as a standalone product by first external users.
