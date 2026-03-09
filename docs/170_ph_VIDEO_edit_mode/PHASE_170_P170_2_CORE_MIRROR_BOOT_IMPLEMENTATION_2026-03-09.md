# PHASE 170 P170.2 Core Mirror Boot Implementation
**Date:** 2026-03-09  
**Status:** Ready for narrow execution  
**Scope:** identify the minimal mirrored core needed to boot `VETKA CUT` beyond sandbox scaffolding

## Goal
После `P170.1 Sandbox Foundation` следующий узкий шаг — не копировать весь VETKA, а зафиксировать минимальный mirrored core slice, который реально нужен CUT для старта.

`P170.2` отвечает на вопрос:
- какие shared core модули обязательны для boot,
- какие являются транзитивными зависимостями,
- что уже mirrored,
- что еще нужно добавить до запуска `CUT MCP`.

## What this step delivers
1. Dependency audit for current mirror manifest.
2. Tiered boot policy for mirrored modules.
3. Marker set for Core Mirror Boot.
4. Scriptable report generation for future manifest updates.

## Current mirrored entry set
Current manifest groups:
1. `watcher_core`
2. `multimodal_ingest`
3. `memory_core`
4. `media_contracts`
5. `media_runtime`

These are entrypoints, not the full transitive closure.

## Recon result: transitive internal dependencies
Current mirrored entrypoints pull additional internal modules from upstream VETKA.

Observed transitive internal deps:
1. `src/scanners/mime_policy.py`
2. `src/memory/qdrant_client.py`
3. `src/orchestration/triple_write_manager.py`
4. `src/ocr/ocr_processor.py`
5. `src/voice/stt_engine.py`
6. `src/utils/embedding_service.py`
7. `src/services/activity_hub.py`
8. `src/services/mcc_jepa_adapter.py`
9. `src/api/handlers/artifact_routes.py`
10. `src/services/artifact_scanner.py`
11. `src/orchestration/cam_event_handler.py`
12. `src/services/premiere_adapter.py`
13. `src/initialization/components_init.py`
14. `src/memory/elision.py`

Implication:
- current manifest is good as a seed,
- but not yet sufficient as a fully bootable closure for all mirrored runtime paths.

## Tier policy
### Tier 0: bootstrap-safe minimum
Needed to keep foundational sync narrow:
1. watcher/import entrypoints,
2. multimodal contracts,
3. memory primitives,
4. shared docs/contracts,
5. job store baseline.

### Tier 1: transitive boot closure
Needed before realistic CUT MCP boot from mirrored code:
1. `mime_policy`
2. `qdrant_client`
3. `triple_write_manager`
4. `embedding_service`
5. `activity_hub`
6. `activity_emitter`
7. `elision`
8. `surprise_detector`
9. `qdrant_auto_retry`
10. `ocr_processor`
11. `stt_engine`

### Tier 2: media route compatibility slice
Needed if CUT reuses existing media runtime/server logic directly:
1. `artifact_scanner`
2. `cam_event_handler`
3. `premiere_adapter`
4. `api/handlers/artifact_routes.py`
5. `mcc_jepa_adapter`
6. `initialization/components_init.py`

## Recommended execution rule
1. Do not jump to Tier 2 immediately unless CUT is directly booting existing media routes.
2. First extend manifest to cover Tier 1 closure.
3. Treat Tier 2 as selective compatibility layer, not default cargo-cult copy.
4. Keep CUT-owned runtime logic outside `core_mirror/` even after Tier 2.

## Marker set for P170.2
1. `MARKER_170.CORE.BOOT_AUDIT`
2. `MARKER_170.CORE.TIER0_ENTRYSET`
3. `MARKER_170.CORE.TIER1_TRANSITIVE_CLOSURE`
4. `MARKER_170.CORE.TIER2_ROUTE_COMPAT`
5. `MARKER_170.CORE.DEP_AUDIT_SCRIPT`
6. `MARKER_170.CORE.BOOT_REPORT`

## Narrow implementation target
P170.2 should produce:
1. a dependency audit script,
2. a generated boot report artifact,
3. a clear decision whether Tier 1 gets merged into the next manifest revision.

## Decision for next step
Recommended next move after this doc:
1. run dependency audit on every manifest change,
2. create `CUT MCP` around Tier 0 + Tier 1 modules,
3. only borrow Tier 2 modules when specific reuse is justified.
