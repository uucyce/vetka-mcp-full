# PHASE 170 VETKA CUT Architecture
**Date:** 2026-03-09  
**Status:** Draft for execution  
**Scope:** standalone `VETKA CUT` architecture over mirrored `VETKA Core`

## Why this architecture
Цель: дать `VETKA CUT` возможность быстро стартовать как самостоятельный монтажный контур, не ломая основной `VETKA` runtime и не теряя доступ к главному УТП ядра — scan/search/memory/context.

Execution rule:
1. Mirror the core first.
2. Isolate the heavy runtime second.
3. Build editorial flows third.
4. Reintegrate only after stability.

## Architectural principles
1. `Core mirror, not core rewrite`.
2. `Contracts shared, runtime isolated`.
3. `Heavy media work off the UI path`.
4. `Async-first orchestration`.
5. `Reintegration must stay possible`.

## System topology
### L0 Core Mirror
Sandbox copy of `VETKA Core` provides:
1. watcher/import/search stack,
2. extractor registry,
3. multimodal contracts,
4. memory/context stack,
5. vector/search infrastructure,
6. baseline MCP primitives.

### L1 CUT MCP
Main orchestration server for CUT:
1. project startup,
2. scene assembly,
3. timeline bootstrap,
4. fallback questions,
5. edit-state coordination,
6. export orchestration.

### L2 Media Worker MCP
Heavy execution lane:
1. ffprobe / ffmpeg,
2. waveform/transcoding,
3. transcription,
4. OCR / vision / scene cuts,
5. JEPA / PULSE enrichments,
6. long-running background jobs.

### L3 CUT Storage Layer
Namespaced persistence for sandbox:
1. isolated Qdrant collections or collection prefix,
2. isolated job state,
3. isolated preview/cache folders,
4. isolated artifacts and logs,
5. separate env/config.

### L4 CUT UI
Standalone editor shell:
1. folder/project bootstrap,
2. media overview,
3. timeline lanes,
4. scene graph / semantic links,
5. assistant/fallback surfaces,
6. export controls.

## MCP topology
```text
CUT UI
  -> CUT MCP
      -> Core Mirror services
      -> Media Worker MCP
      -> Qdrant / cache / storage
```

Rules:
1. UI never calls heavy workers directly.
2. CUT MCP owns orchestration and job state.
3. Media Worker MCP owns expensive processing.
4. Shared core services stay replaceable via sync from upstream VETKA.

## Contract strategy
### Freeze and keep shared
1. `media_chunks_v1`
2. `vetka_montage_sheet_v1`
3. job envelope compatible with `media_mcp_job_v1`
4. degraded/telemetry metadata style
5. semantic link payload primitives

### Add CUT-specific contracts
1. `cut_project_v1`
2. `cut_timeline_state_v1`
3. `cut_scene_graph_v1`
4. `cut_playback_session_v1`
5. `cut_worker_task_v1`
6. `cut_audio_sync_result_v1`
7. future shared multi-sync alignment surface for `timecode`, `waveform`, and `meta_sync`

Constraint:
- new contracts must be additive and namespace-safe; do not break shared VETKA contracts.

## Sync hierarchy
CUT sync should be layered, not monolithic.

1. `timecode sync` is the first hard-sync path when reliable metadata exists.
2. `waveform sync` is the second hard-sync path when timecode is absent, broken, or incomplete.
3. `meta_sync` is a later intelligence layer that may refine or suggest alignment from scenario semantics, visual similarity, and rhythm.
4. `meta_sync` must not replace hard sync; it can only rank, propose, or refine after `timecode` and `waveform` evaluation.

## Editorial identity rules
These rules keep `player`, `CUT`, and `VETKA Core` aligned so the same media item does not gain conflicting meanings across products.

1. There is no primary file-level `favorite` in editorial flows.
2. Canonical cognitive unit is a bounded `time marker`, not a file star.
3. `favorite`, `comment`, `CAM`, and `chat` actions all resolve to the same time-marker family with different `kind` payloads.
4. Media ranking derives from weighted marked moments, not from a persistent file-level star field.
5. `CAM` attaches to time markers and their context slices; it does not create a second parallel favorite system.

### Player/CUT status-gated action rule
Player donor UI must not expose `VETKA action` and `star` as equal permanent buttons.

1. `not in VETKA -> show VETKA ingest/save action`
2. `already in VETKA -> hide ingest action and enable moment-star / comment / CAM marker actions`
3. star in player/editor UI means `favorite moment`, never `favorite file`
4. player-lab stays a donor preview surface, not the orchestration owner for CUT cognition

This rule is architectural, not cosmetic. It prevents endpoint churn and keeps player-lab adoption compatible with `CUT` contracts.

## Memory strategy
CUT should use VETKA memory as differentiator, but with controlled boundaries.

### Use directly
1. `ENGRAM` for persistent project/user/editor context,
2. `STM` for current session/editor state summaries,
3. `MGC` for multi-layer cache and prefetch,
4. `ELISION` for compact context handoff,
5. `CAM` as contextual scoring signal and marker enrichment source.

### Caution
1. do not assume old CAM wiring is fully integrated everywhere,
2. do not duplicate MGC/STM implementations in CUT,
3. keep memory namespaces per sandbox/project where needed,
4. use feature flags for experimental memory-driven editorial actions,
5. keep CAM-linked cognition anchored to time markers so memory signals remain timeline-addressable.

## Import and search strategy
The CUT ingest path should start from existing VETKA patterns, not custom one-off import code.

Flow:
1. watcher/import registers files,
2. extractor registry emits multimodal records,
3. vectors and payloads land in namespaced storage,
4. CUT MCP resolves scenes/lanes/takes from shared contracts,
5. CUT UI consumes assembled editorial state.

## Sandbox sync strategy
### Goal
Keep CUT close to upstream core without losing isolation.

### Mechanism
1. define `core-mirror` directories that are regularly synced from main VETKA,
2. keep CUT-specific code in dedicated namespaces/folders,
3. avoid editing mirrored core files unless a patch is intended for upstream too,
4. maintain a sync manifest describing mirrored modules.

### Recommended sync groups
1. `src/api/routes/watcher_*` and related import stack,
2. `src/scanners/*` relevant to multimodal ingest,
3. `src/memory/*` and context dependencies,
4. shared contracts/docs/tests,
5. MCP/job primitives needed by CUT.

## Stability rules
1. No production VETKA process depends on unstable CUT worker lanes.
2. No CUT experiment writes into shared prod collections by default.
3. Every heavy task must be resumable or retryable.
4. CUT failures degrade inside sandbox; they do not cascade into VETKA mainline.
5. Reintegration happens only through already-frozen contracts.

## Exit criteria for reintegration
1. CUT MCP stable on repeated real projects.
2. Worker crash profile acceptable.
3. Timeline/editor state contract stable.
4. Shared core sync process proven.
5. Mainline VETKA can mount CUT as `edit mode` without importing unstable internals.
