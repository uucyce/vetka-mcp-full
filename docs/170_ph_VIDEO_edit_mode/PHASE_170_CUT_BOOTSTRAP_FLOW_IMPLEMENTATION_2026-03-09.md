# PHASE 170 CUT Bootstrap Flow Implementation
**Date:** 2026-03-09  
**Status:** narrow implementation draft  
**Scope:** first service/handler flow for `POST /api/cut/bootstrap`

## Goal
Определить узкий, безопасный и реалистичный flow для первого `CUT MCP` endpoint:
- создать или открыть `cut_project_v1`,
- проверить sandbox/core mirror,
- сделать quick scan,
- вернуть bootstrap payload без запуска тяжелых media jobs inline.

## Marker
- `MARKER_170.MCP.BOOTSTRAP.FLOW_V1`

## Endpoint
- `POST /api/cut/bootstrap`

## Dependency baseline
This flow assumes:
1. `P170.1` sandbox foundation exists,
2. Tier 1 mirror closure is available when `use_core_mirror=true`,
3. `cut_project_v1` is the canonical project record,
4. heavy analyze jobs are deferred to async lanes after bootstrap.

## Request handling sequence
### Step 1: validate request
Validate:
1. `source_path` absolute and exists,
2. `sandbox_root` absolute,
3. `mode` allowed,
4. `quick_scan_limit` sane,
5. `bootstrap_profile` accepted.

Failure here returns immediate recoverable error.

### Step 2: resolve sandbox state
Check sandbox root:
1. exists,
2. has `config/cut_core_mirror_manifest.json` when `use_core_mirror=true`,
3. has expected runtime/storage directories,
4. does not collide with forbidden paths.

If layout is missing but recoverable, return degraded bootstrap or explicit `sandbox_missing_layout` error.

### Step 3: resolve existing project or create new one
Branch by mode:
1. `open_existing` -> load persisted `cut_project_v1`
2. `create_new` -> create fresh `cut_project_v1`
3. `create_or_open` -> load if already present for this source/sandbox, else create

Rule:
- project creation must happen before heavy worker jobs.

### Step 4: verify core mirror readiness
Only if `use_core_mirror=true`:
1. resolve `core_mirror_root`,
2. verify manifest file exists,
3. optionally check required Tier 0/Tier 1 paths,
4. set `degraded_mode=true` if mirror is incomplete but bootstrap can continue in limited mode.

### Step 5: perform quick scan
Use lightweight scan only:
1. count media files,
2. detect broad modality mix,
3. detect montage/script/transcript presence,
4. compute missing inputs and fallback questions,
5. estimate ready time.

Rule:
- no FFmpeg transcode,
- no JEPA full pass,
- no transcript generation inline.

### Step 6: prepare bootstrap phases
Return minimal deterministic phases:
1. `discover`
2. `project`
3. `align`

Optional future extension:
- if async startup job is spawned, include `job_id` and switch final phase to `queued`/`running`.

### Step 7: persist project + bootstrap metadata
Persist:
1. `cut_project_v1`
2. bootstrap metadata file
3. optional registry/index pointer for reopen flow

### Step 8: return response
Return `cut_bootstrap_v1` response with:
1. `project`
2. `bootstrap`
3. `stats`
4. `missing_inputs`
5. `fallback_questions`
6. `phases`
7. `next_actions`
8. `degraded_mode`

## Minimal service split
Recommended first implementation split:
1. `CutBootstrapRequestValidator`
2. `CutSandboxResolver`
3. `CutProjectStore`
4. `CutBootstrapService`
5. route handler as thin wrapper

## Recommended pseudo-flow
```text
POST /api/cut/bootstrap
  -> validate body
  -> resolve sandbox
  -> load/create cut_project_v1
  -> verify core mirror readiness
  -> run quick scan
  -> persist bootstrap state
  -> return cut_bootstrap_v1
```

## Non-goals for V1 flow
1. no timeline state generation inline
2. no scene graph generation inline
3. no direct worker execution in request thread
4. no export wiring in bootstrap step

## First implementation decision
The first real code path should prefer:
1. sync quick bootstrap,
2. async heavy follow-up,
3. stable project persistence before worker orchestration.
