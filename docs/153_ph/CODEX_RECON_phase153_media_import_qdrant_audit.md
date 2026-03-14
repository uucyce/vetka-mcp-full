# CODEX RECON: Media Import + Qdrant Audit (Phase 153)

MARKER_153.RECON.MEDIA_IMPORT_QDRANT

Date: 2026-02-16
Protocol: RECON + markers -> REPORT -> WAIT GO -> IMPL NARROW -> VERIFY
Status: REPORT READY, WAITING FOR GO

## Scope

Audit of current VETKA import/ingestion pipeline for:
- local files
- browser drag/drop files
- artifact panel file loading
- indexing and retrieval in Qdrant

Goal of audit:
- verify current limitation ("mostly text import")
- map real support for media/data types
- identify exact code-level gaps before implementation

## Current Pipeline (as implemented)

1. Local scanning/indexing:
- `/api/watcher/add` -> `QdrantIncrementalUpdater.scan_directory()` ->
  `update_file()` -> embedding -> Qdrant upsert (`vetka_elisya`).

2. Browser scan/indexing:
- `/api/watcher/add-from-browser` receives metadata list from browser,
  creates embeddings from name/path/type only, stores placeholder content.

3. Single file drag-drop indexing:
- `/api/watcher/index-file` reads file as text with UTF-8 replace;
  binary falls back to `"[Binary file]"`; embeds that text and stores preview.

4. Artifact panel read:
- `/api/files/read` supports binary via base64, but viewer stack is code/markdown/image-centric.

5. Artifact batch indexing:
- `QdrantBatchManager.queue_artifact()` exists but no call sites found in repo.

## Findings

### F1. Scanner indexing is extension-gated to text/code sets
MARKER_153.RECON.F1_TEXT_EXTENSION_GATE

Evidence:
- `LocalScanner.SUPPORTED_EXTENSIONS` is text/code/config only (no audio/video/office/archive):  
  `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/scanners/local_scanner.py:46`
- watcher supported extensions are also text/code only:  
  `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/scanners/file_watcher.py:79`

Impact:
- most media types never enter main scan->embed->index pipeline.

### F2. Browser import does not ingest file content
MARKER_153.RECON.F2_BROWSER_METADATA_ONLY

Evidence:
- browser ingest builds embedding from file name/path/type only and stores placeholder content:
  `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/api/routes/watcher_routes.py:441`
  `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/api/routes/watcher_routes.py:466`

Impact:
- semantic quality for browser-imported data is low; no true content indexing.

### F3. Single-file indexing degrades binary to placeholder text
MARKER_153.RECON.F3_BINARY_PLACEHOLDER

Evidence:
- `/index-file` reads as UTF-8 text; on failure uses `"[Binary file]"`:
  `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/api/routes/watcher_routes.py:632`
  `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/api/routes/watcher_routes.py:634`

Impact:
- binary/media gets indexed without extracted semantic payload.

### F4. Artifact listing "supports many types" but content API reads text only
MARKER_153.RECON.F4_ARTIFACT_TEXT_READ_ONLY

Evidence:
- artifact scanner maps many extensions (including pdf/docx/image) for classification:
  `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/services/artifact_scanner.py:80`
- artifact content endpoint reads via `read_text(...)` only:
  `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/api/routes/artifact_routes.py:216`

Impact:
- classification exists, but retrieval/processing path is text-only for many artifact types.

### F5. OCR path exists but is effectively unreachable from local scanner for images/PDF
MARKER_153.RECON.F5_OCR_UNREACHABLE_FOR_LOCAL_SCAN

Evidence:
- embedding pipeline has OCR branch for image/pdf:
  `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/scanners/embedding_pipeline.py:306`
- but local scanner does not output those extensions:
  `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/scanners/local_scanner.py:46`

Impact:
- OCR support is present in code, but not activated by default local scan input set.

### F6. Triple-write reindex explicitly indexes only text extensions
MARKER_153.RECON.F6_TRIPLEWRITE_TEXT_ONLY

Evidence:
- reindex route has `TEXT_EXTENSIONS` hardcoded and skips others:
  `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/api/routes/triple_write_routes.py:227`
  `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/api/routes/triple_write_routes.py:243`

Impact:
- reindex cannot recover/expand media ingestion coverage.

### F7. Artifact batch indexing path is dead/partial
MARKER_153.RECON.F7_ARTIFACT_BATCH_DEAD_PATH

Evidence:
- `queue_artifact()` exists:
  `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/memory/qdrant_batch_manager.py:150`
- no usages found in repo for `queue_artifact(`.
- batch manager tries `COLLECTION_NAMES['artifacts']`, but base client collection map has no `artifacts` key:
  `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/memory/qdrant_batch_manager.py:375`
  `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/memory/qdrant_client.py:85`

Impact:
- artifact-specific vector lane is not reliably wired as a first-class path.

### F8. Viewer capabilities are narrow relative to binary read support
MARKER_153.RECON.F8_VIEWER_GAP

Evidence:
- backend read endpoint supports base64 for binary:
  `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/api/routes/files_routes.py:140`
- artifact viewer type system is `code | markdown | image | unknown`:
  `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/client/src/components/artifact/utils/fileTypes.ts:11`
- panel sets `content` directly from `/api/files/read`, no decode/branch by `encoding`:
  `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/client/src/components/artifact/ArtifactPanel.tsx:254`

Impact:
- backend can return binary payloads, but UI/processing path for audio/video/pdf/office is incomplete.

## Summary Matrix (Current State)

- text/code/config: mostly supported end-to-end
- images/pdf: partial (raw read yes, OCR code exists, ingestion path inconsistent)
- office docs (docx/xlsx/pptx): mostly unsupported for extraction/indexing
- audio/video: unsupported for semantic extraction/indexing in file ingest path
- archives/binaries: placeholder-only indexing or skipped

## Recommended IMPL NARROW (after GO)

MARKER_153.PLAN.NARROW_V1

Proposed narrow implementation slice (minimal blast radius):

1. Introduce unified ingestion service for non-text files:
- new module: media extractor registry by MIME/extension
- extractor output contract: `{text, modality, metadata, quality_score, warnings}`

2. Wire ingestion into existing entry points only:
- `/api/watcher/index-file`
- `QdrantIncrementalUpdater.update_file()`
- `/api/watcher/add-from-browser` (where content is available; otherwise mark as metadata-only)

3. Activate existing OCR path safely:
- allow image/pdf extensions into scanner lane or route these through extractor service.

4. Store richer payload in Qdrant:
- keep current point schema compatible
- add fields: `modality`, `mime_type`, `extraction_method`, `extraction_status`, `text_excerpt`.

5. Keep UI scope minimal in this step:
- no full media player refactor in V1
- add robust fallback display and metadata badges only.

## Risks to control in implementation

- extraction latency and event-loop blocking (must remain async/non-blocking)
- oversized payloads in Qdrant (strict text excerpt limits)
- dependency availability (OCR/audio/video libs may be optional)
- false confidence from placeholder content (must mark extraction status explicitly)

## Decision Gate

REPORT complete.
Waiting for explicit GO before implementation.

