# PHASE 158 — Multimedia Import + QDRANT Marker Recon
**Created:** 2026-03-02
**Updated:** 2026-03-02 (Codex re-verify + unified IO alignment)

---

## CHANGELOG_2026-03-02_Codex
1. Исправлены статусы F2/F3/F5/F6: это не full-gap, а partial-implementation.
2. Исправлены/уточнены code refs в `watcher_routes.py` и pipeline.
3. Добавлены marker'ы для целевого V1: media tokenization + timeline contract + playback-ready payload.
4. Добавлены marker'ы под anti-freeze контур (`media_edit_mode`, `media-mcp`).
5. Синхронизировано с `VETKA_UNIFIED_IO_MATRIX_V1.md`.

## 1. Endpoint/Input Matrix — Re-verified in Codebase

### 1.1 Watcher Routes (`/api/watcher/*`)
| Endpoint | File:Line | Status | Marker |
|----------|-----------|--------|--------|
| `POST /api/watcher/add` | watcher_routes.py:81 | ✅ ACTIVE | `MARKER_158.WATCHER.ADD_DIR` |
| `POST /api/watcher/add-from-browser` | watcher_routes.py:388 | ⚠️ PARTIAL | `MARKER_158.WATCHER.BROWSER_METADATA_ONLY_PARTIAL` |
| `POST /api/watcher/index-file` | watcher_routes.py:637 | ⚠️ PARTIAL (OCR+AV exists) | `MARKER_158.WATCHER.SINGLE_FILE_MULTIMODAL_PARTIAL` |
| `POST /api/watcher/remove` | watcher_routes.py:289 | ✅ ACTIVE | `MARKER_158.WATCHER.REMOVE_DIR` |
| `GET /api/watcher/status` | watcher_routes.py:330 | ✅ ACTIVE | `MARKER_158.WATCHER.STATUS` |
| `GET /api/watcher/heat` | watcher_routes.py:355 | ✅ ACTIVE | `MARKER_158.WATCHER.HEAT` |

### 1.2 Scanner Entry Points
| Entry Point | File:Line | Extensions | Status | Marker |
|-------------|-----------|------------|--------|--------|
| `LocalScanner.SUPPORTED_EXTENSIONS` | local_scanner.py:46 | Includes pdf/img/audio/video (code exists) | ⚠️ PARTIAL | `MARKER_158.SCANNER.LOCAL_MULTIMEDIA_CODE` |
| `file_watcher.SUPPORTED_EXTENSIONS` | file_watcher.py:111 | Includes pdf/img/audio/video | ✅ RESOLVED (branch) | `MARKER_158.SCANNER.EXT_WATCHER_ADD_MEDIA` |
| `embedding_pipeline` OCR/AV branch | embedding_pipeline.py:306 | pdf/img + audio/video transcript | ⚠️ PARTIAL | `MARKER_158.SCANNER.OCR_AV_EXISTS` |

### 1.3 Triple Write Routes
| Endpoint | File:Line | Feature | Status | Marker |
|----------|-----------|---------|--------|--------|
| `POST /api/triple-write/reindex` | triple_write_routes.py:238 | TEXT_EXTENSIONS | ✅ ACTIVE | `MARKER_158.TRIPLEWRITE.TEXT_ONLY` |
| `POST /api/triple-write/reindex` (multimedia) | triple_write_routes.py:266 | `req.multimodal=true` | ⚠️ PARTIAL (off by default) | `MARKER_158.TRIPLEWRITE.MULTIMEDIA_FLAG` |
| OCR processing in reindex | triple_write_routes.py:279 | pdf/image OCR | ⚠️ REACHABLE | `MARKER_158.TRIPLEWRITE.OCR_PROCESS` |
| AV transcription in reindex | triple_write_routes.py:294 | audio/video Whisper path | ⚠️ REACHABLE | `MARKER_158.TRIPLEWRITE.AV_PROCESS` |

### 1.4 QDRANT Integration Points
| Function | File:Line | Status | Marker |
|----------|-----------|--------|--------|
| `QdrantIncrementalUpdater.update_file()` | qdrant_updater.py:324 | ⚠️ PARTIAL (binary fallback empty) | `MARKER_158.QDRANT.INCREMENTAL_UPDATER_PARTIAL` |
| `qdrant_batch_manager.queue_artifact()` | qdrant_batch_manager.py:151 | ✅ WIRED (artifact_routes bridge) | `MARKER_158.QDRANT.ARTIFACT_BATCH_WIRE` |
| QDRANT collections init | qdrant_client.py | ✅ ACTIVE | `MARKER_158.QDRANT.COLLECTIONS` |

### 1.5 OCR/Multimedia Contracts
| Contract | File:Line | Status | Marker |
|----------|-----------|--------|--------|
| `OCRResult` dataclass | multimodal_contracts.py:12 | ✅ EXISTS | `MARKER_158.CONTRACT.OCR_RESULT` |
| OCR processor | ocr_processor.py | ✅ EXISTS | `MARKER_158.OCR.PROCESSOR` |

---

## 2. Gap Analysis with Markers

### GAP F1: Scanner Extension-Gated (resolved in current branch)
| Item | Value |
|------|-------|
| **Marker** | `MARKER_158.GAP.F1_SCANNER_EXTENSION_GATE` |
| **Location** | `file_watcher.py:111` |
| **Issue** | Исторически `SUPPORTED_EXTENSIONS` был text/code only |
| **Impact** | Исторически media события могли не попадать в ingest |
| **Current State** | ✅ Media extensions добавлены; есть regression тест `tests/test_phase158_watcher_multimedia_extensions.py` |
| **Fix Required** | Keep regression guard; no further code fix required for F1 |

### GAP F2: Browser Import Mostly Metadata-Only
| Item | Value |
|------|-------|
| **Marker** | `MARKER_158.GAP.F2_BROWSER_METADATA_ONLY` |
| **Location** | `watcher_routes.py:465-490` |
| **Issue** | Есть `content_small`, но full extraction pipeline не подключен |
| **Impact** | Semantic depth нестабильна, особенно на media/blob данных |
| **Fix Required** | Add browser-side media extraction contract + server ingest normalization |

### GAP F3: Single-File Index has fallback placeholders
| Item | Value |
|------|-------|
| **Marker** | `MARKER_158.GAP.F3_BINARY_PLACEHOLDER` |
| **Location** | `watcher_routes.py:717-763` |
| **Issue** | OCR+AV есть, но при ошибке падает в summary placeholder |
| **Impact** | Качество retrieval зависит от успешности extraction runtime |
| **Fix Required** | Unified extractor service + deterministic extraction metadata |

### GAP F5: OCR/AV path fragmented across entry points
| Item | Value |
|------|-------|
| **Marker** | `MARKER_158.GAP.F5_OCR_UNREACHABLE` |
| **Location** | `embedding_pipeline.py:306`, `watcher_routes.py:717`, `qdrant_updater.py:284` |
| **Issue** | Разные входы имеют разную глубину extraction (не единый contract) |
| **Impact** | Непредсказуемый результат в зависимости от route |
| **Fix Required** | Unify extraction policy for watcher/index/reindex/updater |

### GAP F6: Triple-Write Text-Only Default
| Item | Value |
|------|-------|
| **Marker** | `MARKER_158.GAP.F6_TRIPLEWRITE_DEFAULT_TEXT` |
| **Location** | `triple_write_routes.py:266` |
| **Issue** | Multimedia requires explicit `req.multimodal=true` flag |
| **Impact** | By default reindex cannot recover/expand media coverage |
| **Fix Required** | Default multimodal=true or smart-detect |

### GAP F7: Artifact Batch Indexing Dead Path (resolved in current branch)
| Item | Value |
|------|-------|
| **Marker** | `MARKER_158.GAP.F7_ARTIFACT_BATCH_DEAD` |
| **Location** | `qdrant_batch_manager.py:151` |
| **Issue** | Исторически `queue_artifact()` не имел production call-site |
| **Impact** | Исторически artifact-specific vector lane был не подключен |
| **Current State** | ✅ Wired via `src/api/routes/artifact_routes.py` (`_try_index_saved_artifact`), с `queue_artifact()` + `force_flush()` |
| **Fix Required** | Keep regression test coverage for artifact routing path |

---

## 3. Implementation Markers — Proposed

### Category: Scanner Extensions
| Proposed Marker | Target | Description |
|-----------------|--------|-------------|
| `MARKER_158.SCANNER.EXT_WATCHER_ADD_MEDIA` | file_watcher.py | Add img/audio/video extensions to watcher |
| `MARKER_158.SCANNER.EXT_WATCHER_ADD_PDF` | file_watcher.py | Add PDF to watcher extensions |

### Category: Ingestion Pipeline
| Proposed Marker | Target | Description |
|-----------------|--------|-------------|
| `MARKER_158.INGEST.BROWSER_WIRE_CONTENT` | watcher_routes.py | Wire actual file content in browser import |
| `MARKER_158.INGEST.BINARY_ROUTE_OCR` | watcher_routes.py | Route binary files through OCR |
| `MARKER_158.INGEST.OCR_DEFAULT_PATH` | embedding_pipeline.py | Enable OCR in default scan path |
| `MARKER_158.INGEST.MEDIA_EXTRACTOR_REGISTRY` | new service | Unified OCR/STT extractor registry |
| `MARKER_158.INGEST.MEDIA_TIMECODE_SCHEMA` | contracts + routes | Segment schema for timeline/timecode |
| `MARKER_158.INGEST.JEPA_PULSE_ENRICH` | extractor registry | Optional semantic/audio enrichment layer |

### Category: QDRANT
| Proposed Marker | Target | Description |
|-----------------|--------|-------------|
| `MARKER_158.QDRANT.ARTIFACT_BATCH_WIRE` | qdrant_batch_manager.py | Wire artifact batch indexing |
| `MARKER_158.QDRANT.SCHEMA_ADD_MODALITY` | qdrant_updater.py | Add modality/mime_type fields |
| `MARKER_158.QDRANT.SCHEMA_MEDIA_CHUNKS_V1` | qdrant payload | Canonical chunk payload with timestamps |
| `MARKER_158.QDRANT.SCHEMA_TIMELINE_REF_V1` | qdrant payload | Keep source timeline refs for montage sheet |
| `MARKER_158.QDRANT.SCHEMA_SCENE_BINDING_V1` | qdrant payload | Scene/treatment/music binding fields |

### Category: Triple-Write
| Proposed Marker | Target | Description |
|-----------------|--------|-------------|
| `MARKER_158.TRIPLEWRITE.MULTIMEDIA_DEFAULT` | triple_write_routes.py | Default multimodal=true |
| `MARKER_158.TRIPLEWRITE.MEDIA_CHUNK_RETRIEVAL` | triple_write_routes.py | Stable retrieval over `media_chunks` lane |

### Category: Runtime Isolation
| Proposed Marker | Target | Description |
|-----------------|--------|-------------|
| `MARKER_158.RUNTIME.MEDIA_EDIT_MODE` | mode router | Dedicated mode for edit/preview workflows |
| `MARKER_158.RUNTIME.MEDIA_MCP_SPLIT` | orchestration config | Separate heavy media worker/MCP process |
| `MARKER_158.RUNTIME.MEDIA_BACKPRESSURE` | queue manager | Backpressure and timeout policy for AV jobs |

---

## 4. Current State Matrix (Verified)

| Type | Scanner | Browser | Index-File | TripleWrite | OCR Code |
|------|---------|---------|------------|-------------|----------|
| text/code | ✅ | ⚠️ metadata/content_small | ✅ | ✅ | N/A |
| images | ⚠️ partial | ⚠️ partial | ✅ OCR fallback | ⚠️ flag | ✅ |
| PDF | ⚠️ partial | ⚠️ partial | ✅ OCR fallback | ⚠️ flag | ✅ |
| audio/video | ⚠️ partial | ⚠️ partial | ✅ STT fallback | ⚠️ flag | ✅ partial |

---

## 5. Recommended Implementation Order (Narrow V1)

1. **P0:** Add media extensions to `file_watcher.SUPPORTED_EXTENSIONS`  
   → `MARKER_158.SCANNER.EXT_WATCHER_ADD_MEDIA` (done in current branch; keep test guard)

2. **P1:** Introduce unified extractor registry (`OCR/STT/media-summary`)  
   → `MARKER_158.INGEST.MEDIA_EXTRACTOR_REGISTRY`

3. **P2:** Normalize timeline chunk schema (`start/end/text/confidence/source`)  
   → `MARKER_158.INGEST.MEDIA_TIMECODE_SCHEMA`

4. **P3:** Wire browser import to extractor-aware ingestion  
   → `MARKER_158.INGEST.BROWSER_WIRE_CONTENT`

5. **P4:** Fix incremental updater binary path + artifact batch lane  
   → `MARKER_158.QDRANT.INCREMENTAL_UPDATER_PARTIAL` + `MARKER_158.QDRANT.ARTIFACT_BATCH_WIRE`

---

## 6. Related Documents

- `docs/153_ph/CODEX_RECON_phase153_media_import_qdrant_audit.md` — Original audit
- `docs/156_ph/QDRANT_RECOVERY_REPORT_2026-03-01.md` — QDRANT v1.16.2 lock
- `docs/158_ph/V-JEPA_MULTIMEDIA_QDRANT_RECON_2026-03-02.md` — This recon base
- `docs/158_ph/VETKA_UNIFIED_IO_MATRIX_V1.md` — Canonical unified IO contract (JSON-first + XML adapters)
