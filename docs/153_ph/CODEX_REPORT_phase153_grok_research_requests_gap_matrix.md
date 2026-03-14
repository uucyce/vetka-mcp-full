# CODEX REPORT: Grok Research Requests for All Gaps (Phase 153 + Phase 72)

MARKER_153.REPORT.GROK_REQUESTS.GAP_MATRIX

Date: 2026-02-16  
Protocol: RECON + markers -> REPORT -> WAIT GO -> IMPL NARROW -> VERIFY  
Status: REPORT READY, WAITING FOR GO

## Scope

This document provides copy-paste ready Grok research requests for all identified gaps:
- Media/data import + Qdrant ingestion gaps (Phase 153 audit)
- Universal dependency/relationship extraction gaps (Phase 72 intent vs implementation)

Each request includes linked code files, research target, and required output format.

---

## Global Instructions for Grok (prepend to every prompt)

Use these constraints in every research response:
1. Propose implementation options in order: `minimal patch`, `balanced`, `full architecture`.
2. For each option, include: complexity, migration risk, performance impact, rollback plan.
3. Return concrete code-level plan with touched modules and API contracts.
4. Keep backward compatibility for existing text/code indexing.
5. Mark assumptions explicitly and separate from verified facts.
6. Output sections: `Findings`, `Recommended Option`, `Patch Plan`, `Test Plan`, `Risks`.

---

## GAP-01: Extension Gate Blocks Non-Text Media

MARKER_153.GROK.GAP01_EXTENSION_GATE

**Related files**
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/scanners/local_scanner.py:46`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/scanners/file_watcher.py:79`

**Prompt for Grok**
```text
Audit the current extension-gated scanner and watcher, then design a safe expansion path for all media/data types (image, pdf, office docs, audio, video, archives).

Files:
- src/scanners/local_scanner.py (SUPPORTED_EXTENSIONS)
- src/scanners/file_watcher.py (SUPPORTED_EXTENSIONS)

Required:
1) Propose new extension/MIME policy (allowlist + denylist + size caps).
2) Define modality routing rules (text -> direct, image/pdf -> OCR, audio/video -> transcription/metadata extraction, office -> parser).
3) Include backpressure strategy for watcher events.
4) Provide exact patch points and config schema.
5) Provide regression tests for existing text flow.
```

---

## GAP-02: Browser Import Indexes Only Metadata Placeholder

MARKER_153.GROK.GAP02_BROWSER_METADATA

**Related files**
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/api/routes/watcher_routes.py:376`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/api/routes/watcher_routes.py:441`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/api/routes/watcher_routes.py:466`

**Prompt for Grok**
```text
Design a browser-import ingestion protocol that supports real file content (when available) and explicit metadata-only mode (when content is unavailable).

Files:
- src/api/routes/watcher_routes.py (/api/watcher/add-from-browser)

Required:
1) API contract for mixed payloads: metadata-only + content-bearing items.
2) Security model for browser-provided blobs/files.
3) Extraction status model in payload (metadata_only, extracted, failed, skipped).
4) Triple-write compatibility.
5) Migration plan from current placeholder content behavior.
```

---

## GAP-03: Single-File Indexing Falls Back to "[Binary file]"

MARKER_153.GROK.GAP03_INDEX_FILE_BINARY

**Related files**
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/api/routes/watcher_routes.py:579`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/api/routes/watcher_routes.py:632`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/api/routes/watcher_routes.py:634`

**Prompt for Grok**
```text
Design replacement for /api/watcher/index-file binary placeholder logic with modality-aware extraction pipeline.

Files:
- src/api/routes/watcher_routes.py (/api/watcher/index-file)

Required:
1) Determine file modality via MIME + extension + magic bytes fallback.
2) Extraction adapter interface and timeout strategy.
3) Qdrant payload fields for extraction traceability.
4) Failure handling: partial extraction and safe fallback semantics.
5) Benchmarks target for latency and throughput.
```

---

## GAP-04: Artifact Content Route Reads Text Only

MARKER_153.GROK.GAP04_ARTIFACT_TEXT_ONLY

**Related files**
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/services/artifact_scanner.py:63`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/api/routes/artifact_routes.py:216`

**Prompt for Grok**
```text
Design artifact content retrieval that supports binary/media payloads consistently with scanner classification.

Files:
- src/services/artifact_scanner.py (type mapping)
- src/api/routes/artifact_routes.py (content endpoint)

Required:
1) Unified artifact read contract (text, base64, stream URL, metadata).
2) Large file strategy and pagination/chunking for content previews.
3) Compatibility with existing artifact list API.
4) Security and path validation considerations.
5) Contract tests.
```

---

## GAP-05: OCR Exists But Is Not Reliably Activated

MARKER_153.GROK.GAP05_OCR_ROUTING

**Related files**
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/scanners/embedding_pipeline.py:306`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/scanners/local_scanner.py:46`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/scanners/qdrant_updater.py:280`

**Prompt for Grok**
```text
Create routing design to ensure OCR is deterministically triggered for image/pdf sources in all ingestion entrypoints.

Files:
- src/scanners/embedding_pipeline.py (OCR branch)
- src/scanners/local_scanner.py
- src/scanners/qdrant_updater.py (_read_file_content)

Required:
1) Single source of truth for modality routing.
2) Decision graph for OCR vs plain text vs skip.
3) Caching strategy for OCR results.
4) Error taxonomy (ocr_unavailable, ocr_timeout, low_confidence, etc.).
5) Unit + integration tests.
```

---

## GAP-06: Triple-Write Reindex Is Text-Only

MARKER_153.GROK.GAP06_TRIPLEWRITE_TEXT_ONLY

**Related files**
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/api/routes/triple_write_routes.py:227`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/api/routes/triple_write_routes.py:245`

**Prompt for Grok**
```text
Design Triple-Write reindex v2 that supports multimodal ingestion while preserving current text behavior.

Files:
- src/api/routes/triple_write_routes.py

Required:
1) Replace TEXT_EXTENSIONS-only logic with extractor registry.
2) Define memory and size guardrails.
3) Add progress reporting with per-modality counters.
4) Idempotency strategy for repeated reindex runs.
5) Rollback strategy.
```

---

## GAP-07: Artifact Batch Queue Path Is Partially Dead + Collection Mapping Drift

MARKER_153.GROK.GAP07_BATCH_ARTIFACT_WIRING

**Related files**
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/memory/qdrant_batch_manager.py:150`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/memory/qdrant_batch_manager.py:375`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/memory/qdrant_client.py:85`

**Prompt for Grok**
```text
Investigate artifact batching architecture and propose final wiring plan with consistent collection mapping.

Files:
- src/memory/qdrant_batch_manager.py
- src/memory/qdrant_client.py

Required:
1) Decide whether artifact vectors should be in dedicated or shared collection.
2) Resolve COLLECTION_NAMES drift.
3) Identify call sites that should queue_artifact and lifecycle hooks.
4) Add observability metrics for queue health and flush outcomes.
5) Migration plan for existing points.
```

---

## GAP-08: UI Viewer Model Is Narrow vs Backend Binary Support

MARKER_153.GROK.GAP08_UI_VIEWER_ENCODING

**Related files**
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/api/routes/files_routes.py:140`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/client/src/components/artifact/utils/fileTypes.ts:11`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/client/src/components/artifact/ArtifactPanel.tsx:245`

**Prompt for Grok**
```text
Design minimal UI/contract upgrade so ArtifactPanel can correctly handle utf-8 text, base64 binary, and media mime types.

Files:
- src/api/routes/files_routes.py (/api/files/read)
- client/src/components/artifact/utils/fileTypes.ts
- client/src/components/artifact/ArtifactPanel.tsx

Required:
1) Extend viewer type model (pdf/audio/video/office/binary).
2) Define decode/render policy from {encoding, mimeType}.
3) Keep V1 scope: robust preview/fallback badges, not full media suite.
4) Error states and UX behavior.
5) Frontend test matrix.
```

---

## GAP-09: Universal Scanner Architecture Exists, Concrete Non-Python Scanners Missing

MARKER_153.GROK.GAP09_SCANNER_IMPLEMENTATIONS

**Related files**
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/scanners/base_scanner.py:35`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/scanners/python_scanner.py:73`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/scanners/__init__.py:66`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/docs/136_ph_Knowledge level_from_Phase 72/input_matrix_idea.txt:1`

**Prompt for Grok**
```text
Propose phased implementation roadmap for concrete scanners beyond Python: DocumentScanner, VideoScanner, AudioScanner, BookScanner, ScriptScanner.

Files:
- src/scanners/base_scanner.py
- src/scanners/python_scanner.py
- src/scanners/__init__.py
- docs/136_ph_Knowledge level_from_Phase 72/input_matrix_idea.txt

Required:
1) Prioritized order by impact/cost.
2) Per-scanner extraction targets (timestamps, chapters, citations, entities, references).
3) Unified Dependency output schema compatibility.
4) MVP vs production maturity criteria.
5) Library/tooling candidates and operational constraints.
```

---

## GAP-10: No Production Extraction of Reference/Citation/Footnote Dependencies

MARKER_153.GROK.GAP10_DOC_RELATION_EXTRACTION

**Related files**
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/scanners/dependency.py:42`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/scanners/dependency_calculator.py:13`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/scanners/local_scanner.py:159`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/docs/136_ph_Knowledge level_from_Phase 72/input_matrix_idea.txt:11`

**Prompt for Grok**
```text
Design explicit reference/citation/footnote extraction pipeline for documents (md/txt/pdf/docx) and map outputs to DependencyType.{REFERENCE,CITATION,FOOTNOTE}.

Files:
- src/scanners/dependency.py
- src/scanners/dependency_calculator.py
- src/scanners/local_scanner.py
- docs/136_ph_Knowledge level_from_Phase 72/input_matrix_idea.txt

Required:
1) Parser strategies by format.
2) Confidence scoring for explicit vs inferred links.
3) Conflict resolution when links are ambiguous.
4) Storage model in Qdrant payload.
5) Evaluation dataset proposal.
```

---

## GAP-11: Edge Classification Logic Not Integrated Into Main Graph Flow

MARKER_153.GROK.GAP11_EDGE_CLASSIFICATION_WIRING

**Related files**
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/layout/knowledge_layout.py:409`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/layout/knowledge_layout.py:2123`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/api/routes/tree_routes.py:1118`

**Prompt for Grok**
```text
Analyze how to wire classify_edge output into the final graph payload consumed by frontend without breaking current layout performance.

Files:
- src/layout/knowledge_layout.py (classify_edge and coordinate stages)
- src/api/routes/tree_routes.py (knowledge payload response)

Required:
1) Integration points and data contract for edge styling metadata.
2) Backward compatibility for clients expecting old edge schema.
3) Performance impact estimate on large graphs.
4) Controlled rollout plan with feature flag.
5) Validation checks.
```

---

## GAP-12: No End-to-End Universal Relationship Pipeline (All Modalities -> Qdrant)

MARKER_153.GROK.GAP12_E2E_UNIVERSAL_PIPELINE

**Related files**
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/scanners/dependency.py:31`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/scanners/dependency_calculator.py:20`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/api/handlers/message_utils.py:1607`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/orchestration/semantic_dag_builder.py:434`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/docs/136_ph_Knowledge level_from_Phase 72/input_matrix_idea.txt:21`

**Prompt for Grok**
```text
Design end-to-end universal relationship extraction architecture (all modalities) where outputs are indexed in Qdrant and consumed by DAG/knowledge layout.

Files:
- src/scanners/dependency.py
- src/scanners/dependency_calculator.py
- src/api/handlers/message_utils.py
- src/orchestration/semantic_dag_builder.py
- docs/136_ph_Knowledge level_from_Phase 72/input_matrix_idea.txt

Required:
1) Canonical schema for relation extraction output.
2) How explicit, temporal-semantic, and citation/reference links coexist.
3) Qdrant payload/index strategy for relation-aware retrieval.
4) DAG builder contract changes.
5) Incremental rollout sequence (narrow implementation slices).
```

---

## Consolidated Deliverables to Request from Grok

For each gap, require Grok to output:
1. Problem restatement in current code terms.
2. 2-3 architecture options with tradeoffs.
3. Chosen recommendation with concrete file-level patch map.
4. API schema changes (request/response/payload).
5. Test plan (unit/integration/e2e) with acceptance checks.
6. Risk register + rollback.

## GO Gate (after Grok responses)

Proceed to IMPL NARROW only after:
- all 12 gap responses are collected,
- conflicting recommendations are resolved,
- one prioritized implementation sequence is approved.

MARKER_153.REPORT.COMPLETE.WAIT_GO

---

## Grok Response Integration (2026-02-16)

MARKER_153.REPORT.GROK_RESPONSES.SUMMARY_V1

Интегрирован внешний ответ Grok "VETKA Architecture Map: Universal Data Nodes + Modes + MCP Extensibility".
Ниже отражено покрытие по нашим 12 гэпам.

### Coverage Matrix

1. GAP-01 Extension Gate: covered at architecture level.
   - Подтверждено расширение на media/doc типы и модальный routing.
   - Нет точного extension/MIME списка и guardrail лимитов.
2. GAP-02 Browser metadata-only ingest: partially covered.
   - Признан split: base ingest в Core и metadata/content distinction.
   - Нет готового API schema с mixed payload.
3. GAP-03 index-file binary placeholder: covered conceptually.
   - Прямо предложен universal scanner path вместо text fallback.
   - Нет детального failure contract и timeout policy.
4. GAP-04 artifact text-only read path: partially covered.
   - Подтверждена media-oriented preview strategy.
   - Нет полного backend контракта artifact content endpoint.
5. GAP-05 OCR routing: partially covered.
   - Подтвержден media modality routing.
   - Нет конкретной стратегии OCR-cache/error taxonomy.
6. GAP-06 triple-write text-only reindex: not covered in detail.
   - Упомянут coherence/focus around Qdrant path.
   - Нет patch-level плана по `/api/routes/triple_write_routes.py`.
7. GAP-07 artifact batch wiring/collection drift: covered conceptually.
   - Подтверждена роль `qdrant_batch_manager.py` как universal batch base.
   - Нет решения по collection policy and migration.
8. GAP-08 UI viewer encoding gap: covered conceptually.
   - Подтверждены media-specific previews and mode-aware UI behavior.
   - Нет точного decode/render policy from `{encoding, mimeType}`.
9. GAP-09 missing non-Python scanners: covered.
   - Предложен `UniversalScanner` + modular scanners.
10. GAP-10 ref/citation/footnote extraction: partially covered.
   - Подтверждена универсальная связность explicit + referential.
   - Нет parser-level strategy by format.
11. GAP-11 classify_edge wiring: partially covered.
   - Уточнен mode-level semantics (Directed/Knowledge).
   - Нет file-level integration path в final graph payload.
12. GAP-12 end-to-end universal relation pipeline: covered.
   - Полностью подтверждена целевая схема: scanner -> qdrant batch -> layout -> 3D.

### Decisions Captured from Grok

1. Core-first: multimodal ingest/rels must work without MCP.
2. MCP-later: heavy operations as optional mode extensions.
3. Universal relation formula remains tri-part:
   - explicit import/reference,
   - temporal-semantic relation,
   - referential link relation.
4. Directed and Knowledge modes should be explicit in architecture and payload semantics.

### Follow-up Required Before GO

1. Convert conceptual coverage into patch-level specs for GAP-02/03/04/05/06/07/08/10/11.
2. Freeze extraction contract and edge payload schema.
3. Approve narrow implementation slice (Wave 1.5 in roadmap).
