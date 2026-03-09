# PHASE 170 P170.1 Sandbox Foundation Implementation
**Date:** 2026-03-09  
**Status:** Ready for narrow execution  
**Scope:** bootstrap `VETKA CUT` sandbox without touching mainline runtime

## Goal
Собрать минимальный, безопасный и повторяемый фундамент для `VETKA CUT` как standalone sandbox на mirrored `VETKA Core`.

P170.1 не делает полноценную монтажку.
P170.1 делает основу, на которой монтажка сможет запускаться отдельно и синхронизироваться с upstream.

## What P170.1 must deliver
1. Отдельный sandbox root для `VETKA CUT`.
2. Namespaced runtime/data/cache/log directories.
3. Mirror manifest для копирования core-модулей.
4. Повторяемый bootstrap script.
5. Повторяемый sync script для `VETKA Core -> CUT core_mirror`.
6. Явные границы: где mirror, где CUT-owned code.

## Deliverables in this step
1. `config/cut/cut_core_mirror_manifest.example.json`
2. `scripts/cut/bootstrap_cut_sandbox.py`
3. `scripts/cut/sync_cut_core_mirror.py`
4. `scripts/cut/README.md`

## Sandbox layout
Recommended layout:
```text
<VETKA_CUT_SANDBOX>/
├─ core_mirror/
├─ cut_runtime/
│  ├─ configs/
│  ├─ jobs/
│  ├─ logs/
│  ├─ cache/
│  └─ preview_cache/
├─ cut_storage/
│  ├─ imports/
│  ├─ artifacts/
│  ├─ exports/
│  └─ temp/
├─ docs/
├─ reports/
└─ config/
   ├─ cut.env.example
   └─ cut_core_mirror_manifest.json
```

## Ownership rules
### Mirrored
1. `src/api/routes/watcher_routes.py`
2. relevant `src/scanners/*`
3. relevant `src/memory/*`
4. selected contracts/docs/tests
5. selected MCP/job primitives

### CUT-owned
1. `cut_runtime/*`
2. CUT MCP server code
3. CUT worker MCP code
4. CUT contracts
5. CUT UI shell
6. CUT-specific storage and telemetry

## Marker set for P170.1
1. `MARKER_170.SANDBOX.CREATE`
2. `MARKER_170.SANDBOX.ENV_ISOLATION`
3. `MARKER_170.SANDBOX.CORE_MIRROR_MANIFEST`
4. `MARKER_170.SANDBOX.STORAGE_NAMESPACE`
5. `MARKER_170.SANDBOX.BOOTSTRAP_SCRIPT`
6. `MARKER_170.SANDBOX.SYNC_SCRIPT`

## Decisions fixed in this step
1. Sandbox root is outside the main repo by default.
2. `core_mirror` is copied from upstream VETKA, not edited casually.
3. CUT runtime data is namespaced and local to sandbox.
4. Sync is explicit/scripted, not ad hoc drag-and-drop.
5. Early CUT work prefers mirrored modules over fresh rewrites.

## Environment isolation
The sandbox should use separate values for:
1. ports,
2. cache dirs,
3. logs,
4. temp files,
5. qdrant collection prefix / namespace,
6. local artifacts/output directories.

Suggested env names:
1. `VETKA_CUT_SANDBOX_ROOT`
2. `VETKA_CUT_CORE_MIRROR_ROOT`
3. `VETKA_CUT_RUNTIME_ROOT`
4. `VETKA_CUT_STORAGE_ROOT`
5. `VETKA_CUT_QDRANT_PREFIX`
6. `VETKA_CUT_PROFILE`

## Sync policy
### Allowed
1. Pull mirrored files from upstream main VETKA.
2. Keep local CUT-owned code separate.
3. Track missing source files as warnings, not silent failures.

### Not allowed
1. Manual uncontrolled edits directly inside mirrored tree.
2. Shared prod collections by default.
3. Implicit sync logic with no manifest.

## Immediate next step after P170.1
After sandbox foundation is in place:
1. create `CUT MCP` bootstrap contract,
2. define `cut_project_v1`,
3. stand up the first async job loop,
4. only then begin editor-shell wiring.
