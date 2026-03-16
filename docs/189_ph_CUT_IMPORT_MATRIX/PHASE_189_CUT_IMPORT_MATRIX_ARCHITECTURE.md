# Phase 189: CUT Import Matrix Architecture
**Date:** 2026-03-17
**Status:** Draft for execution
**Author:** Opus (Architect-Commander) + Danila
**Scope:** VETKA CUT import pipeline through triple memory with PULSE-JEPA enrichment

---

## 0. Lineage — where this comes from

This document **extends and unifies** prior architectural decisions:

| Source | Phase | What it provides |
|--------|-------|-----------------|
| `input_matrix_idea.txt` | 72/136 | Universal scanner family concept: every content type has its own "imports" (code=require, video=timecodes, audio=topics, script=scenes) |
| `MARKER_155_INPUT_MATRIX_SCANNER_CONTRACT` | 155 | Scanner interface, SignalEdge contract, 5-channel scoring (structural/semantic/temporal/reference/contextual), pair-weight matrix |
| `17.6_Knowledge Mode=Directory Mode` | 17.6 | Hierarchical semantic tree (not flat tags), Sugiyama for knowledge DAG, Y=depth X=angular spread |
| `PHASE_170_VETKA_CUT_ARCHITECTURE` | 170 | L0-L4 topology, CUT MCP + Media Worker MCP, import through watcher/extractor/vectors |
| `PHASE_170_COGNITIVE_TIME_MARKERS_CONTRACT` | 170 | `cut_time_marker_v1`, favorite=moment not file, player-lab bridge |
| `VJepaPulseIntegration` | 169 | Extractor registry hooks, JEPA vector embeddings, PULSE rhythm enrichment |
| `PULSE_McKee_Triangle_Calibration_v0.2` | PULSE-JEPA | Triangle position (arch/mini/anti), genre→scale→BPM→pendulum mapping |
| `pulse_cinema_matrix.csv` | PULSE-JEPA | 24 scales mapped to cinema scene types, dramatic functions, triangle positions |
| `CODEX_RECON_phase153_media_import_qdrant_audit` | 153 | F1-F8 findings: media files NOT indexed, text-only pipeline, OCR unreachable |
| `vetka_montage_sheet_v1.schema.json` | contracts | Record structure: scene_id/take_id/timecode/hero_entities/dialogue/action_tags |
| `cut_bootstrap_v1.schema.json` | contracts | Bootstrap with `missing_inputs` (script, montage_sheet, transcript) and `fallback_questions` |
| `cut_scene_graph_v1.schema.json` | contracts | Nodes (scene/take/asset/note) + edges (contains/follows/semantic_match/alt_take/references) |

---

## 1. Problem statement

### What exists now (Phase 188)
```
User → Cmd+I → POST /import-files → files in /tmp/sandbox/
     → POST /bootstrap-async → count files, create metadata
     → POST /scene-assembly-async → placeholder clips (duration=5.0s), basic scene graph
     → GET /project-state → render in ProjectPanel bins
```

### What's wrong
1. **No media analysis** — clips get placeholder durations, no codec/resolution/timecode
2. **No triple memory** — files bypass Qdrant/Weaviate/JSON entirely (Phase 153 F1-F8)
3. **No semantic extraction** — no speech-to-text, no entity recognition, no scene detection
4. **No PULSE-JEPA enrichment** — rhythm/energy/motion features not extracted
5. **No montage sheet population** — `vetka_montage_sheet_v1` fields stay empty
6. **No bidirectional flow** — can't go from montage sheet → material selection (documentary)
7. **No time markers** — player-lab `cut_time_marker_v1` not connected to import
8. **Import is CUT-only** — should go through VETKA/MCC scanner family per Phase 155

### What this document defines
The **Import Matrix** — a systematic pipeline that routes every imported file through the appropriate scanners, enrichers, and memory stores before it becomes a CUT clip.

---

## 2. Core thesis — Import IS the differentiator

> "Сила VETKA CUT не в том, что он умеет резать клипы, а в том, что он режет клипы поверх scan/search/memory/import core." — Phase 170 Vision Spec

Import is not a transport step. **Import is the intelligence step.** When a file enters CUT, it must be:
1. **Scanned** (metadata, duration, codec, timecode)
2. **Extracted** (speech, entities, visual features, rhythm)
3. **Indexed** (vectors in Qdrant, semantic links in Weaviate, metadata in JSON)
4. **Linked** (to existing project context: scenes, characters, locations)
5. **Scored** (CAM relevance, quality flags, PULSE energy profile)

Only then does it become a clip on the timeline.

---

## 3. Architecture — Import Matrix pipeline

### 3.1 Two entry points, one pipeline

```
┌─────────────────────────────────────────────────────┐
│ ENTRY POINT A: Desktop (Tauri)                      │
│ Cmd+I → native file dialog → local file paths       │
│ No upload needed — direct fs access                  │
├─────────────────────────────────────────────────────┤
│ ENTRY POINT B: SaaS (Browser / API)                 │
│ Drag-drop / POST /import-files → upload to sandbox  │
│ Files land in server filesystem, then same pipeline  │
└─────────────┬───────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────────────┐
│ STAGE 1: BOOTSTRAP (existing, extend)               │
│ POST /api/cut/bootstrap-async                       │
│                                                     │
│ • Discover media files in source folder             │
│ • Extract basic metadata (ffprobe: duration, codec, │
│   resolution, timecode, fps, channels)              │
│ • Detect missing_inputs (script? montage_sheet?     │
│   transcript?)                                      │
│ • Generate fallback_questions if needed             │
│ • Create project skeleton in sandbox                │
│ • → bootstrap_state.json (cut_bootstrap_v1)         │
└─────────────┬───────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────────────┐
│ STAGE 2: SCANNER MATRIX (NEW — Phase 155 contract)  │
│ Async job: scan-matrix                              │
│                                                     │
│ Per file, dispatch to typed scanner:                │
│ ┌──────────────────────────────────────────────┐    │
│ │ VideoScanner                                  │    │
│ │ • ffprobe metadata (duration, TC, fps)        │    │
│ │ • scene-cut detection (PySceneDetect/ffmpeg)  │    │
│ │ • thumbnail grid extraction                    │    │
│ │ • V-JEPA visual embeddings (fps=2, win=8s)    │    │
│ │ • Output: segments[], thumbnails[], vectors[]  │    │
│ ├──────────────────────────────────────────────┤    │
│ │ AudioScanner                                  │    │
│ │ • waveform extraction (peaks for UI)          │    │
│ │ • speech-to-text (Whisper)                     │    │
│ │ • speaker diarization (optional)               │    │
│ │ • PULSE rhythm features (BPM, energy contour, │    │
│ │   cut_density, motion_volatility)              │    │
│ │ • Output: transcript[], waveform, rhythm{}     │    │
│ ├──────────────────────────────────────────────┤    │
│ │ DocumentScanner                               │    │
│ │ • Text extraction (PDF/DOCX/TXT/SRT)          │    │
│ │ • Structure: headings, sections, timecodes     │    │
│ │ • Entity extraction (characters, locations)    │    │
│ │ • Output: text, entities[], structure[]         │    │
│ ├──────────────────────────────────────────────┤    │
│ │ ScriptScanner                                 │    │
│ │ • Scene/act/character parsing                  │    │
│ │ • Montage sheet generation from script         │    │
│ │ • Output: scenes[], characters[], montage_sh[] │    │
│ ├──────────────────────────────────────────────┤    │
│ │ ImageScanner                                  │    │
│ │ • EXIF metadata                                │    │
│ │ • V-JEPA visual embedding (single frame)       │    │
│ │ • OCR if text detected                         │    │
│ │ • Output: metadata{}, vector[], text?           │    │
│ └──────────────────────────────────────────────┘    │
│                                                     │
│ Each scanner returns unified SignalEdge[] per 155:   │
│ {source, target, channel, evidence, confidence}      │
└─────────────┬───────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────────────┐
│ STAGE 3: TRIPLE MEMORY WRITE (NEW)                  │
│ Async job: triple-memory-ingest                     │
│                                                     │
│ For each scanned file:                              │
│                                                     │
│ ┌─ QDRANT (vector store) ────────────────────────┐  │
│ │ Collection: media_chunks_v1                     │  │
│ │ • V-JEPA visual embeddings (per segment)        │  │
│ │ • Whisper transcript embeddings (per utterance)  │  │
│ │ • Document text embeddings (per section)        │  │
│ │ • Payload: scene_id, take_id, timecodes,        │  │
│ │   hero_entities, action_tags, quality_flags      │  │
│ │ Purpose: semantic search ("find all shots of X") │  │
│ └────────────────────────────────────────────────┘  │
│                                                     │
│ ┌─ WEAVIATE (knowledge graph) ───────────────────┐  │
│ │ Classes: MediaAsset, Scene, Character, Location │  │
│ │ • Cross-references between entities              │  │
│ │ • Temporal edges (A before B)                    │  │
│ │ • Semantic similarity edges                      │  │
│ │ • Script↔footage matching                        │  │
│ │ Purpose: graph queries ("all scenes with X at Y")│  │
│ └────────────────────────────────────────────────┘  │
│                                                     │
│ ┌─ JSON FALLBACK (local metadata) ───────────────┐  │
│ │ Files in sandbox:                               │  │
│ │ • montage_sheet.json (vetka_montage_sheet_v1)   │  │
│ │ • scene_graph.json (cut_scene_graph_v1)          │  │
│ │ • time_markers.json (cut_time_marker_bundle_v1) │  │
│ │ • bootstrap_state.json                           │  │
│ │ Purpose: offline-first, Qdrant/Weaviate down     │  │
│ └────────────────────────────────────────────────┘  │
│                                                     │
│ Degraded-safe: if Qdrant/Weaviate unavailable,      │
│ JSON fallback always works. Status: degraded_mode.   │
└─────────────┬───────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────────────┐
│ STAGE 4: SCENE ASSEMBLY (existing, extend)          │
│ POST /api/cut/scene-assembly-async                  │
│                                                     │
│ Now with REAL data from scanner matrix:              │
│ • Timeline lanes with actual durations/timecodes    │
│ • Scene graph with semantic edges from Weaviate      │
│ • Montage sheet records with entities/dialogue       │
│ • Thumbnail bundle from extracted keyframes          │
│ • Waveform bundle for audio display                  │
│ • Time markers from CAM/PULSE scoring                │
└─────────────┬───────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────────────┐
│ STAGE 5: ENRICHMENT (async background, non-blocking)│
│                                                     │
│ After scene assembly, Media Worker MCP continues:    │
│ • PULSE energy profiling per scene                   │
│ • McKee triangle position estimation                 │
│ • CAM scoring (contextual relevance per segment)     │
│ • Cross-project semantic linking                     │
│ • Montage suggestions (if montage sheet exists)      │
│                                                     │
│ Results stream back via WebSocket → UI updates       │
└─────────────────────────────────────────────────────┘
```

### 3.2 Timing budget

| Stage | Blocking? | Budget per file | Budget per 100 files |
|-------|-----------|-----------------|---------------------|
| Bootstrap | Yes (fast) | 50ms | 2s |
| Scanner: ffprobe | Yes | 200ms | 10s |
| Scanner: thumbnails | Background | 500ms | 30s |
| Scanner: scene detection | Background | 2s | 3min |
| Scanner: Whisper STT | Background | 1x realtime | varies |
| Scanner: V-JEPA | Background | 3s/segment | varies |
| Scanner: PULSE rhythm | Background | 500ms | 30s |
| Triple memory write | Background | 100ms | 5s |
| Scene assembly | Yes | N/A | 2s total |
| Enrichment | Background | minutes | 5-15min |

**UX rule:** User sees bins within 3-5 seconds. Real metadata arrives progressively. Heavy enrichment is fully async.

---

## 4. Scanner family — Phase 155 integration

### 4.1 Base interface (from MARKER_155)

```python
class Scanner:
    scanner_type: str  # "video", "audio", "document", "script", "image"

    def scan(self, scope_root: str) -> tuple[list[Node], list[SignalEdge]]:
        """Return nodes and typed signal edges."""
        ...
```

### 4.2 SignalEdge contract (from Phase 155)

```json
{
  "source": "node_a",
  "target": "node_b",
  "channel": "structural|semantic|temporal|reference|contextual",
  "evidence": ["timecode overlap", "same speaker", "visual similarity 0.87"],
  "confidence": 0.85,
  "weight": 0.7,
  "source_type": "video",
  "target_type": "audio",
  "time_delta_days": 0.0
}
```

### 4.3 CUT-specific pair weights

Extending Phase 155 input matrix for editorial domain:

```python
CUT_PAIR_WEIGHTS = {
    # Same camera, different takes
    ("video", "video"): {
        "structural": 0.2,   # timecode overlap
        "semantic": 0.5,     # V-JEPA visual similarity
        "temporal": 0.3,     # shot order
        "reference": 0.1,    # montage sheet scene_id match
        "contextual": 0.4,   # CAM scoring
    },
    # Video + its audio
    ("video", "audio"): {
        "structural": 0.9,   # same source file
        "semantic": 0.3,     # transcript ↔ visual content
        "temporal": 0.8,     # timecode alignment
        "reference": 0.1,
        "contextual": 0.2,
    },
    # Script/document → footage matching
    ("document", "video"): {
        "structural": 0.1,
        "semantic": 0.7,     # script scene ↔ footage content
        "temporal": 0.2,     # script order ↔ shot order
        "reference": 0.8,    # scene_id/take_id explicit match
        "contextual": 0.3,
    },
    # Footage → montage sheet (documentary reverse)
    ("video", "document"): {
        "structural": 0.1,
        "semantic": 0.6,     # content similarity
        "temporal": 0.5,     # temporal clustering
        "reference": 0.2,
        "contextual": 0.5,   # CAM suggests grouping
    },
}
```

---

## 5. Triple memory detail

### 5.1 Qdrant — vector semantic search

**Collection:** `media_chunks_v1` (shared with VETKA Core per Phase 170)

Point payload per media chunk:
```json
{
  "chunk_id": "mc_001",
  "project_id": "cut_demo",
  "source_file": "/path/to/video.mp4",
  "media_type": "video",
  "start_sec": 12.5,
  "end_sec": 20.3,
  "start_tc": "01:00:12:12",
  "end_tc": "01:00:20:07",
  "scene_id": "scene_003",
  "take_id": "take_003_02",
  "hero_entities": ["Katya", "Ivan"],
  "location_entities": ["office", "Berlin"],
  "action_tags": ["interview", "talking_head"],
  "dialogue_text": "Мне кажется что это было...",
  "quality_flags": ["good_audio", "slightly_overexposed"],
  "intra_motion_score": 0.2,
  "cut_rhythm_hint": 0.4,
  "pulse_energy": 0.6,
  "pulse_bpm": 95,
  "triangle_position": {"arch": 0.4, "mini": 0.5, "anti": 0.1},
  "extraction_status": "complete",
  "extraction_method": "vjepa+whisper+ffprobe"
}
```

**Vector:** V-JEPA visual embedding (768d) OR Whisper transcript embedding (384d) — multi-vector per point.

**Search use cases:**
- "Найди все кадры с Катей в офисе" → filter hero_entities + location_entities + semantic search
- "Найди энергичные моменты для трейлера" → filter pulse_energy > 0.8
- "Найди кадры похожие на этот" → vector similarity on V-JEPA embedding

### 5.2 Weaviate — knowledge graph

**Classes:**
```
MediaAsset (source file-level)
├── hasSegment → MediaChunk (time-bounded segment)
├── hasTranscript → TranscriptUtterance
├── inScene → Scene
├── features → Character
└── shotAt → Location

Scene
├── hasTake → MediaChunk
├── follows → Scene
└── describedIn → ScriptSection

Character
├── appearsIn → MediaChunk[]
├── speaks → TranscriptUtterance[]
└── relatedTo → Character

Location
├── appearsIn → MediaChunk[]
└── partOf → Location (hierarchy)
```

**Purpose:** Graph traversal queries that Qdrant can't do:
- "Все сцены с Катей, отсортированные по сюжетному порядку"
- "Какие персонажи пересекаются в локации X?"
- "Построить монтажный лист из материала — кластеризовать по сценам"

### 5.3 JSON fallback — offline-first

Always written. Files in sandbox project directory:
- `montage_sheet.json` — `vetka_montage_sheet_v1` records
- `scene_graph.json` — `cut_scene_graph_v1` nodes + edges
- `time_markers.json` — `cut_time_marker_bundle_v1`
- `media_index.json` — per-file metadata (ffprobe results, scanner status)
- `extraction_status.json` — per-file extraction progress/errors

**Rule:** JSON is always source of truth for offline/degraded mode. Qdrant/Weaviate are acceleration layers. If they're down, CUT still works — just without semantic search.

---

## 6. Bidirectional flow — montage sheet ↔ material

### 6.1 Forward: Script/sheet → material selection

```
Montage sheet (vetka_montage_sheet_v1)
  → parse scene_id, take_id, dialogue_text, hero_entities
  → semantic search in Qdrant: find matching footage chunks
  → rank by: confidence + CAM score + quality_flags
  → propose timeline assembly
  → user approves/adjusts
```

This is the **scripted film** workflow: you have a plan, CUT finds the footage.

### 6.2 Reverse: Material → montage sheet (documentary)

```
Import footage (no script, no sheet)
  → VideoScanner: scene-cut detection → segments
  → AudioScanner: speech-to-text → topics, speakers
  → Cluster by: visual similarity + temporal proximity + speaker continuity
  → Generate candidate scenes (auto scene_id)
  → Extract hero_entities, location_entities from transcript + vision
  → Build montage_sheet.json from clusters
  → Present to user: "Here's a suggested structure"
  → User edits structure → becomes authoritative montage sheet
```

This is the **documentary** workflow: CUT analyzes the material and proposes structure.

### 6.3 Hybrid mode

Most real projects live between forward and reverse:
- Partial script + raw footage → match what exists, cluster the rest
- Interview-based doc + b-roll → structure from interviews, fill with b-roll by semantic match
- Music video → PULSE rhythm drives the montage sheet (BPM → cut points)

---

## 7. PULSE-JEPA enrichment during import

### 7.1 V-JEPA at import

Per Phase 158 contract:
- `fps=2.0`, `window_sec=8.0`, `stride_sec=2.0`
- Output: 768d visual embeddings per window → stored in `media_chunks_v1`
- Purpose: visual scene similarity, shot matching, duplicate detection
- Budget: ~3s per 8-second window on Apple Silicon

### 7.2 PULSE at import

Per PULSE-JEPA docs:
- Extract: BPM, energy contour, cut_density, motion_volatility, phase_markers
- Map to `pulse_cinema_matrix.csv` scales → triangle_position estimate
- Store per-chunk: `pulse_energy`, `pulse_bpm`, `triangle_position`
- Purpose: rhythm-driven montage, genre-aware editing suggestions

### 7.3 Integration point

PULSE-JEPA enrichment plugs into **Stage 2 (Scanner Matrix)** and **Stage 5 (Enrichment)**:

- **Stage 2** (blocking): Basic V-JEPA embeddings + PULSE rhythm extraction — needed for meaningful scene assembly
- **Stage 5** (async): Full McKee triangle calibration, cross-scene pendulum analysis, genre-specific critics — nice-to-have, runs in background

---

## 8. Player-lab time markers bridge

Per `PHASE_170_COGNITIVE_TIME_MARKERS_CONTRACT`:

### 8.1 Import creates initial markers

When footage is imported and scanned:
- Scene cut points → `kind=insight` markers at cut boundaries
- High-energy PULSE moments → `kind=cam` markers with `cam_payload`
- Existing SRT/subtitle files → `kind=comment` markers with text

### 8.2 Player-lab markers import

If user previously used player-lab and created `kind=favorite` or `kind=comment` markers:
- Import reads player-lab marker storage
- Maps markers to `cut_time_marker_v1` format
- Markers appear on CUT timeline immediately
- Previous `VETKA logo` provisional events migrate to canonical records

### 8.3 Marker-driven ranking

Per contract rule #5:
```
media_rank = weighted_sum(
    favorite_count * 3.0,
    comment_count * 2.0,
    cam_count * 1.5,
    insight_count * 1.0,
    pulse_energy * 0.5
)
```

Ranking feeds: bin sort order, montage suggestion priority, auto-assembly clip selection.

---

## 9. Tauri vs SaaS — same pipeline, different entry

| Aspect | Tauri (Desktop) | SaaS (Browser/API) |
|--------|----------------|-------------------|
| File access | Direct fs path | Upload → sandbox |
| Heavy processing | Local FFmpeg/Whisper | Server-side |
| Qdrant | Local instance | Cloud instance |
| Weaviate | Local instance | Cloud instance |
| JSON fallback | Local sandbox | Server sandbox |
| Scanner matrix | Same code | Same code |
| MCP | Same CUT MCP | Same CUT MCP (HTTP) |

**Key insight:** Tauri adds ZERO overhead to the pipeline. It only provides native file dialog and direct fs access. Everything else is identical FastAPI.

For SaaS, the only addition is `POST /import-files` upload step. After files are in sandbox, the pipeline is byte-for-byte the same.

---

## 10. Implementation phases

### Phase 189.1: Bootstrap with real metadata (ffprobe)
- Replace placeholder `duration=5.0` with real ffprobe data
- Extract: duration, codec, resolution, fps, timecode, audio channels
- Populate `cut_bootstrap_v1.stats` with actual counts
- **FastAPI only, no Tauri dependency**

### Phase 189.2: VideoScanner + AudioScanner basic
- Scene-cut detection (PySceneDetect or ffmpeg scene filter)
- Thumbnail grid extraction (poster frames)
- Waveform extraction (peaks for timeline display)
- Speech-to-text (Whisper, async job)
- Scanner returns `SignalEdge[]` per Phase 155 contract

### Phase 189.3: Triple memory write
- Qdrant: `media_chunks_v1` point upsert with real payload
- JSON fallback: montage_sheet.json, media_index.json
- Weaviate: deferred (Phase 189.5) — start with Qdrant + JSON

### Phase 189.4: Scene assembly with real data
- Timeline lanes with actual durations/timecodes
- Scene graph with edges from scanner SignalEdge[]
- Montage sheet records populated from scanners
- Thumbnails and waveforms displayed in UI

### Phase 189.5: PULSE-JEPA enrichment
- V-JEPA visual embeddings per segment
- PULSE rhythm features per chunk
- McKee triangle position estimation
- CAM scoring integration

### Phase 189.6: Bidirectional montage flow
- Forward: script → material matching (semantic search)
- Reverse: material → montage sheet generation (clustering)
- Hybrid mode: partial script + raw footage

### Phase 189.7: Player-lab time markers bridge
- Import existing player-lab markers
- Create insight markers from scene cuts
- Create cam markers from PULSE highlights
- Marker-driven media ranking

### Phase 189.8: Weaviate knowledge graph
- MediaAsset/Scene/Character/Location classes
- Cross-reference edges from scanner matrix
- Graph queries for complex editorial questions

---

## 11. Contracts to extend

### Existing (no breaking changes, add optional fields):

| Contract | New fields |
|----------|-----------|
| `cut_bootstrap_v1` | `scanner_status{}`, `extraction_progress` |
| `cut_scene_graph_v1` | Node metadata: `vector_id`, `pulse_energy`, `transcript_ref` |
| `vetka_montage_sheet_v1` | Already has all fields; just need to populate them |

### New contracts needed:

| Contract | Purpose |
|----------|---------|
| `cut_scanner_result_v1` | Per-file scanner output (metadata + edges + vectors) |
| `cut_extraction_status_v1` | Per-file extraction progress tracking |
| `cut_media_index_v1` | Lightweight per-file metadata (ffprobe results + scanner state) |

---

## 12. Relation to Phase 153 audit (closing findings)

| Finding | Status after 189 |
|---------|-----------------|
| F1: Text-only extension gate | **CLOSED** — Scanner matrix handles all media types |
| F2: Browser metadata-only | **CLOSED** — Upload pipeline leads to same scanner matrix |
| F3: Binary placeholder | **CLOSED** — Each type has typed extractor |
| F4: Artifact text-read only | **PARTIAL** — CUT import path fixed; general artifact viewer separate |
| F5: OCR unreachable | **CLOSED** — ImageScanner + DocumentScanner activate OCR |
| F6: Triple-write text-only | **CLOSED** — Triple memory write handles media chunks |
| F7: Artifact batch dead | **DEFERRED** — CUT uses own collection, not artifact batch |
| F8: Viewer gap | **PARTIAL** — CUT gets proper media display; general viewer separate |

---

## 13. Markers

- `MARKER_189.IMPORT_MATRIX.ARCHITECTURE_FROZEN`
- `MARKER_189.IMPORT_MATRIX.SCANNER_FAMILY_V1`
- `MARKER_189.IMPORT_MATRIX.TRIPLE_MEMORY_WRITE`
- `MARKER_189.IMPORT_MATRIX.PULSE_JEPA_ENRICHMENT`
- `MARKER_189.IMPORT_MATRIX.BIDIRECTIONAL_MONTAGE`
- `MARKER_189.IMPORT_MATRIX.TIME_MARKERS_BRIDGE`
- `MARKER_189.IMPORT_MATRIX.PHASE_153_CLOSURE`
