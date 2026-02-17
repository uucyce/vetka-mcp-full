# CODEX RECON REPORT: Full Gap Closure (Independent Audit)

MARKER_153.RECON.FULL_GAP_CLOSURE.INDEPENDENT

Date: 2026-02-17  
Protocol: RECON + markers -> REPORT -> WAIT GO -> IMPL NARROW -> VERIFY  
Status: REPORT READY, WAITING FOR GO

## Scope

Independent code-first audit to close ambiguity before implementation:
1. Verify all known Phase 153/72 ingestion and relation gaps.
2. Resolve pipeline relationship question:
   - `/api/watcher/add-from-browser` vs unified `web/` save/import path.
3. Identify additional operational gaps causing iterative regressions.

---

## Key Answer: Is `web/` Import Connected to `/add-from-browser`?

MARKER_153.RECON.WEB_VS_BROWSER_PIPELINES

Short answer: **they are different pipelines** with partial convergence only in tree rendering.

### Pipeline A: Browser FileSystem metadata ingest
- Entry: `/api/watcher/add-from-browser`  
  `src/api/routes/watcher_routes.py:376`
- Input: metadata only (`name`, `relativePath`, `size`, `type`, `lastModified`)  
  `src/api/routes/watcher_routes.py:47`
- Embedding source: filename/path/type placeholder text  
  `src/api/routes/watcher_routes.py:441`
- Stored content is placeholder  
  `src/api/routes/watcher_routes.py:466`

### Pipeline B: Unified search `web/` -> save webpage artifact
- Search endpoint: `/api/search/unified` with source `web`  
  `src/api/routes/unified_search_routes.py:129`, `src/api/handlers/unified_search.py:127`
- Save endpoint: `/api/artifacts/save-webpage`  
  `src/api/routes/artifact_routes.py:140`
- Save behavior: writes `.md`/`.html` into `data/artifacts/...` (disk artifact), does not call watcher index route directly  
  `src/api/handlers/artifact_routes.py:207`

### Convergence point
- Tree API builds artifact nodes by scanning artifact directories from disk (`scan_artifacts`), not from watcher browser metadata path.  
  `src/api/routes/tree_routes.py:810`

Conclusion:
- `add-from-browser` != `save-webpage`.
- They converge visually in tree only via artifact scan, not via a unified ingestion contract.

---

## Gap Closure Matrix (Code-verified)

### G01. Extension/MIME gate for non-text ingest
MARKER_153.RECON.G01
- **Status**: OPEN
- Evidence: watcher/local scanner extension gates are text/code-centric.  
  `src/scanners/file_watcher.py:79`, `src/scanners/local_scanner.py:46`
- Risk: media files are skipped before extraction path.

### G02. Browser mixed payload contract
MARKER_153.RECON.G02
- **Status**: OPEN
- Evidence: `/add-from-browser` accepts metadata only; no content-bearing payload field.  
  `src/api/routes/watcher_routes.py:47`, `src/api/routes/watcher_routes.py:56`
- Risk: browser imports cannot index real content semantically.

### G03. `/index-file` binary placeholder fallback
MARKER_153.RECON.G03
- **Status**: OPEN
- Evidence: binary path falls back to `"[Binary file]"`.  
  `src/api/routes/watcher_routes.py:632`
- Risk: non-text files are indexed as low-value placeholders.

### G04. Artifact content API text-centric
MARKER_153.RECON.G04
- **Status**: OPEN
- Evidence: artifact content route reads text with `read_text(...)` only.  
  `src/api/routes/artifact_routes.py:216`
- Note: `/api/files/read` supports base64 binary, but artifact content route does not reuse this model.

### G05. OCR path routing inconsistency
MARKER_153.RECON.G05
- **Status**: OPEN
- Evidence: OCR branch exists in embedding pipeline but input scanners/routes often don't route media there.  
  `src/scanners/embedding_pipeline.py:306`, `src/scanners/local_scanner.py:46`, `src/scanners/qdrant_updater.py:280`

### G06. Triple-write reindex text-only
MARKER_153.RECON.G06
- **Status**: OPEN
- Evidence: hardcoded `TEXT_EXTENSIONS` in reindex.  
  `src/api/routes/triple_write_routes.py:227`, `src/api/routes/triple_write_routes.py:245`

### G07. Artifact batch indexing path drift
MARKER_153.RECON.G07
- **Status**: OPEN
- Evidence:
  - Queue method exists but no production call sites outside tests.  
    `src/memory/qdrant_batch_manager.py:150`
  - Collection map lookup for `artifacts` has fallback key, but base collection map does not define `artifacts`.  
    `src/memory/qdrant_batch_manager.py:375`, `src/memory/qdrant_client.py:85`

### G08. Frontend decode/render policy incomplete for binary/media
MARKER_153.RECON.G08
- **Status**: OPEN
- Evidence:
  - Backend returns `{encoding, mimeType}`.  
    `src/api/routes/files_routes.py:152`
  - Artifact viewer type model is narrow (`code|markdown|image|unknown`).  
    `client/src/components/artifact/utils/fileTypes.ts:11`
  - ArtifactPanel loads `data.content` without full modality branch by `encoding/mimeType`.  
    `client/src/components/artifact/ArtifactPanel.tsx:245`

### G09. Universal scanner architecture not implemented beyond Python
MARKER_153.RECON.G09
- **Status**: OPEN
- Evidence: base abstractions exist; concrete non-Python scanners absent in active pipeline.  
  `src/scanners/base_scanner.py:35`, `src/scanners/python_scanner.py:73`

### G10. REF/CITATION/FOOTNOTE extraction missing in production path
MARKER_153.RECON.G10
- **Status**: OPEN
- Evidence: dependency enum includes types, but no document extractor wiring for citation/footnote parsing in scanners.  
  `src/scanners/dependency.py:42`

### G11. `classify_edge` not wired into final knowledge graph payload
MARKER_153.RECON.G11
- **Status**: OPEN
- Evidence:
  - `classify_edge` exists in layout module.  
    `src/layout/knowledge_layout.py:409`
  - Final exported edges include only `{source,target,type,weight}` without style fields from `classify_edge`.  
    `src/layout/knowledge_layout.py:2680`

### G12. End-to-end universal relation pipeline (all modalities -> Qdrant -> graph)
MARKER_153.RECON.G12
- **Status**: OPEN
- Evidence: current flows remain split (watcher metadata path, index-file text path, artifact disk scan path).

---

## Additional Gaps Discovered (Operational)

### G13. Streaming transparency gap: terminal-only provider stream diagnostics
MARKER_153.RECON.G13_STREAM_CHAT_GAP
- **Status**: OPEN
- Evidence:
  - Provider stream emits diagnostic logs via `print` (`[STREAM_V2]`, provider retries) in backend.  
    `src/elisya/provider_registry.py:1752`
  - Chat socket currently streams only `stream_start/token/end`, not provider/tool decision telemetry.  
    `src/api/handlers/user_message_handler.py:696`, `client/src/hooks/useSocket.ts:940`
- Impact: user cannot see "thinking/tool choice/provider retry" inside Vetka chat, only in terminal logs.

### G14. Tooling reality gap in direct streaming path
MARKER_153.RECON.G14_STREAM_TOOL_EXEC_GAP
- **Status**: OPEN
- Evidence:
  - Streaming path sends a prompt saying tools are available, but uses `call_model_v2_stream` token stream (no tool call execution loop in this path).  
    `src/api/handlers/user_message_handler.py:725`, `src/api/handlers/user_message_handler.py:738`
  - Tool execution exists in non-stream direct call branches only.  
    `src/api/handlers/user_message_handler.py:1064`
- Impact: model can claim tool-based validation without actual tool execution in streamed mode.

### G15. BM25 GraphQL escaping gap (multiline query breakage)
MARKER_153.RECON.G15_BM25_ESCAPE_GAP
- **Status**: OPEN
- Evidence:
  - Weaviate BM25 string escaping handles quotes only, not newline/backslash normalization.  
    `src/memory/weaviate_helper.py:251`
  - Can produce GraphQL unterminated string on multiline user text (matches observed logs).

### G16. Web save indexing gap (artifact saved, semantic index path non-unified)
MARKER_153.RECON.G16_WEB_SAVE_INDEX_GAP
- **Status**: OPEN
- Evidence:
  - `/save-webpage` persists file to disk and returns metadata, but route does not index that file through `/watcher/index-file` or equivalent ingestion contract.
  - Tree visibility may still occur due to disk artifact scanner, creating mismatch between visual availability and semantic retrieval path.
  - Save endpoints: `src/api/routes/artifact_routes.py:140`, persistence: `src/api/handlers/artifact_routes.py:207`, tree artifact scan: `src/api/routes/tree_routes.py:810`

### G17. Watcher throughput/robustness gap under non-hidden high-volume dirs
MARKER_153.RECON.G17_WATCHER_THROUGHPUT_GAP
- **Status**: OPEN
- Evidence:
  - Spam auto-mute applies only to hidden dirs; regular dirs are never muted even at high event rates.  
    `src/scanners/file_watcher.py:106`, `src/scanners/file_watcher.py:141`
- Impact: with broad media ingest, event pressure on regular dirs can still overload processing pipeline.

---

## Dependency Order (to avoid correction loops)

MARKER_153.RECON.DEPENDENCY_ORDER

1. Freeze contracts first:
   - extraction contract (modality/encoding/status)
   - relation contract (explicit/temporal/reference)
   - stream telemetry contract (provider/tool events)
2. Unify ingest entrypoints (`/index-file`, `/add-from-browser`, web-save post-processing).
3. Align storage semantics (Qdrant collections + triple-write + artifact batch path).
4. Wire graph edge semantics (`classify_edge` integration).
5. Scale controls (watcher backpressure + BM25 escaping + structured errors).

Rationale: steps 2-5 depend on step 1 contracts; doing them earlier causes repeated rewrites.

---

## Final Research State

MARKER_153.REPORT.WAIT_GO

- Unknowns materially affecting architecture decisions: **none**.
- Open items are now implementation gaps (not research gaps).
- Recommendation: proceed only with IMPL NARROW in dependency order above.

---

## External Multimodal Addendum (Feb 2026)

MARKER_153.RECON.EXTERNAL_MULTIMODAL_2026_02_17

Source: user-provided external research report (image/video/audio OCR/transcription/embedding ecosystem, Feb 17, 2026).  
Verification level in this section: **EXTERNAL / NOT CODE-VERIFIED**.  
Policy: treat as strategic input; validate provider/library claims during integration tests.

### External claims mapped to VETKA gaps

1. OCR stack maturity (DeepSeek/Qwen/GLM + OSS OCR):
   - Directly relevant to `G05` (OCR routing inconsistency).
   - Confirms need for non-PDF OCR path (images + video frames + structured output).

2. Audio/video transcription + timestamps:
   - Directly relevant to `G12` (end-to-end multimodal relation pipeline).
   - Enables temporal edges from media timeline payload (timestamp-based dependencies).

3. Multimodal embeddings (Qwen3-VL / MiniCPM-V / CLIP family):
   - Relevant to `G07` (artifact batch/index path) and `G12`.
   - Requires explicit payload schema for frame/chunk embeddings in Qdrant.

4. Agentic montage/editing tools:
   - Extension target after ingestion stabilization.
   - Should be implemented as optional MCP-heavy mode, not base ingestion blocker.

### Architecture delta (accepted for Phase 153+ planning)

MARKER_153.RECON.MULTIMODAL_DELTA_ACCEPTED

Add three contracts before deep implementation:

1. `OCRResult` contract (image/PDF/frame):
   - `{text, confidence, boxes[], timestamp?, source_path, extractor}`.

2. `MediaChunk` contract (audio/video timeline):
   - `{start_sec, end_sec, text, speaker?, frame_ref?, confidence}`.

3. `QdrantPayload` multimodal extension:
   - `{mime_type, modality, timestamp_sec?, chunk_id?, source_artifact_id, extraction_version}`.

These contracts become mandatory in:
- `src/api/routes/watcher_routes.py`
- `src/scanners/qdrant_updater.py`
- `src/services/artifact_scanner.py`
- `src/layout/knowledge_layout.py` (temporal edge rendering)

### Recommended stack policy (implementation-safe)

MARKER_153.RECON.STACK_POLICY_2026Q1

- Base fallback (local-first): `Whisper + EasyOCR/Tesseract` for guaranteed offline operation.
- Optional high-quality path: pluggable VL model adapter (`Qwen/GLM/DeepSeek`) behind feature flags.
- MCP/video-editing tools (`montage`) only after ingestion contracts + Qdrant schema are stable.

### Updated execution order (with external inputs)

MARKER_153.RECON.EXEC_ORDER_REFRESH

1. Finalize multimodal contracts (`OCRResult`, `MediaChunk`, `QdrantPayload`).
2. Implement scanner routing:
   - image/pdf -> OCR
   - audio -> transcript chunks
   - video -> frame OCR + transcript chunks
3. Store timestamped chunks in Qdrant and expose edge evidence in graph payload.
4. Add MCP montage tools as separate opt-in mode.
5. Benchmark on Apple Silicon (M4) and freeze defaults by latency/quality budget.

---

## Implementation Update (2026-02-17)

MARKER_153.IMPL.UPDATE_2026_02_17

This section tracks what is already implemented after RECON, with code-level status.

### Gap status refresh

- `G02` Browser mixed payload contract: **IMPLEMENTED**
  - `/api/watcher/add-from-browser` now supports `mode=metadata_only|content_small`
  - Optional `contentBase64/contentHash` added to browser file model.
  - File: `src/api/routes/watcher_routes.py`

- `G03` `/index-file` binary fallback: **IMPLEMENTED**
  - Replaced raw `"[Binary file]"` with binary summary + OCR route for image/PDF.
  - File: `src/api/routes/watcher_routes.py`

- `G04` Artifact content API text-centric: **IMPLEMENTED**
  - Artifact content endpoint now returns `utf-8` for text and `base64 + mimeType` for binary.
  - File: `src/api/routes/artifact_routes.py`

- `G05` OCR routing inconsistency: **PARTIAL**
  - OCR now explicitly used in `/index-file` for image/PDF.
  - Local scanner includes media files so embedding pipeline OCR path can process them.
  - Audio/video transcription path added in embedding pipeline with local Whisper fallback + chunk metadata.
  - Long-media chunk persistence is now routed into Qdrant via TripleWrite `write_media_chunks`.
  - Remaining: ranking strategy / retrieval API for chunk-first queries.
  - Files: `src/api/routes/watcher_routes.py`, `src/scanners/local_scanner.py`, `src/scanners/embedding_pipeline.py`

- `G06` Triple-write reindex text-only: **IMPLEMENTED**
  - `/api/triple-write/reindex` now supports `multimodal=true` for OCR + media summary ingest.
  - File: `src/api/routes/triple_write_routes.py`

- `G07` Artifact batch indexing path drift: **IMPLEMENTED**
  - Added `artifacts` collection mapping in Qdrant client.
  - Batch artifact payload now carries modality + extension.
  - Files: `src/memory/qdrant_client.py`, `src/memory/qdrant_batch_manager.py`

- `G08` Frontend decode/render policy: **PARTIAL (CORE IMPLEMENTED)**
  - `ArtifactPanel` now branches by `mimeType/encoding` and renders image/audio/video/pdf from base64 or raw URL.
  - Remaining: dedicated advanced viewers/policies (e.g. richer PDF controls, timeline waveform UX).

- `G10` REF/CITATION/FOOTNOTE extraction: **IMPLEMENTED (artifact-level references)**
  - Added document link parsing and artifact->artifact `reference` edges.
  - File: `src/services/artifact_scanner.py`

- `G11` classify_edge wiring: **IMPLEMENTED**
  - Final graph payload now includes `style/color/opacity/width/visual_type/description`.
  - File: `src/layout/knowledge_layout.py`

- `G13` Stream transparency gap: **IMPLEMENTED**
  - Added `stream_meta` socket events and chat display for stream diagnostics.
  - Files: `src/elisya/provider_registry.py`, `src/api/handlers/user_message_handler.py`, `client/src/hooks/useSocket.ts`

- `G14` Stream tooling reality gap: **PARTIAL**
  - Chat noise removed (`stream_meta` moved out of chat UI; stream path cleaned).
  - Remaining: true tool execution loop for streaming path.

- `G15` BM25 escaping gap: **IMPLEMENTED**
  - Added newline/backslash normalization + robust quote escaping.
  - File: `src/memory/weaviate_helper.py`

- `G16` Web save indexing gap: **IMPLEMENTED**
  - `/api/artifacts/save-webpage` now triggers semantic indexing bridge.
  - File: `src/api/routes/artifact_routes.py`

- `G17` Watcher throughput gap: **IMPLEMENTED**
  - Added soft burst-throttle for regular directories (high threshold, short cooldown).
  - File: `src/scanners/file_watcher.py`

### Remaining priorities

1. `G01` finalize unified extension/MIME policy with explicit allow/deny + size limits.  
   Status: **PARTIAL IMPLEMENTED** (`src/scanners/mime_policy.py` + watcher/reindex integration).
2. `G09/G12` full universal multimodal scanner chain (audio/video chunk extraction + temporal relation persistence).  
   Status: **PARTIAL IMPLEMENTED** (artifact temporal edges + multimodal ingest + AV extraction contracts + chunk-level Qdrant writes), retrieval strategy still pending.
3. `G14` add true streaming tool execution loop (not only advisory telemetry).  
   Status: **PARTIAL IMPLEMENTED** (chat cleanup done; execution loop still pending).
