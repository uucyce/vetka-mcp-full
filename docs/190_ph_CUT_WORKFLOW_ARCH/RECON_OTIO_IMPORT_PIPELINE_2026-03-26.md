# RECON: OTIO Import Pipeline
**Date:** 2026-03-26
**Task:** tb_1774423967_1
**Agent:** Beta (Media/Color Pipeline Architect)
**Branch:** claude/cut-media

---

## Summary

Implements bidirectional NLE timeline interchange for VETKA CUT.
CUT previously exported to 5 formats (Premiere XML, FCPXML, OTIO JSON, EDL, AAF)
but had zero import capability. This recon documents the implemented import pipeline.

---

## Supported Input Formats

| Format | Extension(s) | Source App | Adapter |
|--------|-------------|------------|---------|
| VETKA OTIO JSON | `.otio`, `.otio.json` | VETKA CUT export | `_parse_otio_json` |
| Premiere Pro XMEML v5 | `.xml` | Adobe Premiere Pro | `_parse_premiere_xml` |
| FCPXML v1.x | `.fcpxml` | Final Cut Pro, DaVinci Resolve | `_parse_fcpxml` |
| CMX 3600 EDL | `.edl` | Any NLE | `_parse_edl` |

### Format Detection Logic

Detection is multi-signal — uses file extension first, then content sniffing:
- `.otio` → always OTIO JSON
- `.json` → sniff for `OTIO_SCHEMA` key in first 512 bytes
- `.xml` → sniff for `<xmeml` or `<fcpxml` in first 512 bytes
- `.fcpxml` → always FCPXML
- `.edl` → always EDL
- Unknown → check content for TITLE: / event line pattern

---

## Data Mapping Table

### OTIO JSON → CUT

| OTIO Concept | CUT Concept | Notes |
|---|---|---|
| `Timeline.1` | `cut_timeline_state_v1` | Root mapping |
| `Track.1 (Video)` | Lane (kind=video) | lane_id from track name |
| `Track.1 (Audio)` | Lane (kind=audio) | |
| `Clip.2` | Clip | name, duration from source_range |
| `source_range.duration` | `duration_sec` | value/rate → seconds |
| `metadata.vetka.source_path` | `source_path` | Preserved from export |
| `metadata.vetka.timeline_start_sec` | `start_sec` | Exact position |
| `Transition.*` | Skipped | Warning emitted |

### Premiere XML (XMEML v5) → CUT

| XMEML Concept | CUT Concept | Notes |
|---|---|---|
| `<project/name>` | project_name | |
| `<sequence/name>` | sequence_name | |
| `<rate/timebase>` | fps | NTSC correction applied |
| `<video/track>` | Lane (V1, V2, ...) | One lane per track element |
| `<audio/track>` | Lane (A1, A2, ...) | |
| `<clipitem>` | Clip | start/end/in in frames |
| `<file id="...">` | source_path | Via file-index lookup |
| `<markers/marker>` | Imported markers | Both sequence and clip level |

### FCPXML v1.x → CUT

| FCPXML Concept | CUT Concept | Notes |
|---|---|---|
| `<library/event/project name>` | project_name | |
| `<resources/format frameDuration>` | fps | Rational time: `1/25s` → 25 fps |
| `<resources/asset src>` | source_path | Via asset-index lookup |
| `<spine/asset-clip>` | Lane V1 clip | offset/duration in rational time |
| `<marker value>` | Imported marker | Time relative to clip start |
| Connected clips (lane attr) | Warning only | Secondary lane mapping TBD |

### EDL (CMX 3600) → CUT

| EDL Concept | CUT Concept | Notes |
|---|---|---|
| `TITLE:` | sequence_name | |
| `FCM:` | fps | 25/30/24 detected |
| Event line rec_in/rec_out | start_sec, end_sec | TC converted to seconds |
| Event line src_in/src_out | source_in_sec | |
| `* FROM CLIP NAME:` | name | Clip display name |
| Reel name | metadata.edl_reel | Source path is EMPTY (see limitations) |

---

## Architecture

```
Upload (multipart/form-data)
    │
    ▼
POST /api/cut/import/otio
    │
    ▼
parse_otio_file(file_path, content, project_id)
    │
    ├── _detect_format()  → fmt string
    │
    ├── fmt == "otio_json"     → _parse_otio_json()
    ├── fmt == "premiere_xml"  → _parse_premiere_xml()
    ├── fmt == "fcpxml"        → _parse_fcpxml()
    └── fmt == "edl"           → _parse_edl()
             │
             ▼
         CutImportResult
         ├── timeline_state  (cut_timeline_state_v1)
         ├── markers         (list[dict])
         ├── warnings        (list[str])
         └── metadata        (fps, duration_sec, clip_count, ...)

POST /api/cut/import/otio/apply  (parse + save)
    │
    ├── parse_otio_file()
    ├── CutProjectStore.save_timeline_by_id()
    └── CutProjectStore.save_time_marker_bundle()  (if markers present)
```

### File Locations

| File | Purpose |
|------|---------|
| `src/services/cut_otio_import.py` | Core import service (all adapters) |
| `src/api/routes/cut_routes_import.py` | FastAPI routes |
| `src/api/routes/cut_routes.py` | Router registration (MARKER_BOTIO block) |

### Router Registration

The `import_router` is registered in `cut_routes.py` as:
```python
from src.api.routes.cut_routes_import import import_router
router.include_router(import_router)
```

All endpoints share the `/api/cut/` prefix from the parent router.

---

## API Endpoints

### GET /api/cut/import/formats
Returns supported format manifest with capabilities and limitations per format.

### POST /api/cut/import/otio
Parse-only. Returns timeline_state + markers JSON without writing to disk.
Use for preview/confirmation before applying.

Request: `multipart/form-data`
- `file`: timeline file (any supported format)
- `project_id`: optional, embedded in result

Response: `cut_import_result_v1`
```json
{
  "success": true,
  "source_format": "premiere_xml",
  "project_name": "...",
  "sequence_name": "...",
  "fps": 25.0,
  "duration_sec": 120.5,
  "clip_count": 14,
  "lane_count": 2,
  "marker_count": 3,
  "warnings": [],
  "timeline_state": { ... },
  "markers": [ ... ]
}
```

### POST /api/cut/import/otio/apply
Parse + write to sandbox store. Supports merge modes.

Request: `multipart/form-data`
- `file`: timeline file
- `sandbox_root`: absolute path to CUT sandbox
- `project_id`: CUT project ID
- `timeline_id`: target timeline ID (default: auto-generated)
- `merge_mode`: `"replace"` (default) | `"append_lanes"`

---

## Merge Modes

| Mode | Behavior |
|------|---------|
| `replace` | Overwrites existing timeline state at `timeline_id` |
| `append_lanes` | Reads existing timeline, appends imported lanes (suffixes conflicting lane IDs with `_imp`) |

---

## Limitations and Unsupported Features

### All Formats
- Transitions (dissolves, dips) are parsed as warnings but not mapped to CUT transitions (not yet implemented in CUT)
- Speed changes / time remapping are not preserved
- Effects (color grades, filters) are not imported
- Nested sequences are not followed (treated as clips)

### OTIO JSON
- Only VETKA CUT's hand-rolled OTIO JSON subset is supported
- Full `opentimelineio` Python library adapters (OTIOZ, cmx_3600, etc.) are NOT used — no external dependency
- `ExternalReference` media references with missing source_path show as empty strings

### Premiere XML
- Only XMEML v5 (`<xmeml version="5">`) tested
- Older XMEML v4 or Premiere 6.0 format may parse with reduced fidelity
- `<link>` elements (clip cross-references) are not followed
- Audio sync offsets are not preserved

### FCPXML
- FCPXML v1.6–v1.10 tested (frameDuration rational format)
- Connected clips (secondary storylines) emit warnings but lane positions are not mapped
- Roles (audio roles / subroles) are not imported
- Multicam clips are treated as regular clips

### EDL
- CMX 3600 format only
- Source file paths are ALWAYS empty — EDLs store reel names, not file system paths
- Media relinking is required after import
- Audio-only events (AA tracks) are skipped
- Dissolve/transition events are ignored
- Only V (video) events are imported to Lane V1

---

## Design Decisions

1. **No opentimelineio dependency**: The `opentimelineio` Python library is not in `requirements.txt` and is not available in the runtime. The VETKA OTIO export is a hand-rolled JSON subset. All parsing uses stdlib `json` and `xml.etree.ElementTree`.

2. **Separate parse and apply endpoints**: `/import/otio` (parse-only) lets the frontend show a preview before committing. `/import/otio/apply` writes to the store.

3. **CutImportResult dataclass**: Clean separation between parsing logic and HTTP layer. Service returns a structured result; route converts it to JSON response.

4. **Non-fatal warnings**: Unsupported features (transitions, connected clips) produce warnings in the response rather than errors, allowing partial imports to succeed.

5. **Timeline ID generation**: Each import creates a new `import_<hex>` timeline ID by default. The caller can specify a target `timeline_id` in the apply endpoint.

---

## Test Plan

### Unit Tests (recommended)

1. `test_otio_import_vetka_json.py`
   - Round-trip: export via `_build_otio_export()` → import via `parse_otio_file()` → verify clip positions match

2. `test_otio_import_premiere_xml.py`
   - Parse XMEML v5 fixture with 3 clips, 2 markers → verify lane/clip/marker counts
   - Verify frame→second conversion at 25 fps and 29.97 fps

3. `test_otio_import_fcpxml.py`
   - Parse FCPXML v1.10 fixture → verify rational time parsing
   - `1/25s` → 0.04s, `100/25s` → 4.0s

4. `test_otio_import_edl.py`
   - Parse CMX 3600 fixture → verify rec_in/rec_out → start_sec/end_sec
   - Verify empty source_path + edl_reel metadata
   - Verify warning about media relinking

5. `test_otio_import_format_detection.py`
   - `.otio` → otio_json
   - `.xml` with `<xmeml` → premiere_xml
   - `.xml` with `<fcpxml` → fcpxml
   - `.edl` → edl
   - Unknown → ValueError

### Integration Tests (route layer)

6. `test_cut_import_route.py`
   - POST `/api/cut/import/formats` → 200, list of 4 formats
   - POST `/api/cut/import/otio` with OTIO fixture → 200, timeline_state present
   - POST `/api/cut/import/otio` empty file → 400
   - POST `/api/cut/import/otio` unknown format → 422
   - POST `/api/cut/import/otio/apply` → 200, applied=true, file written to sandbox

### UI Test (Control Chrome)

7. Navigate to `/cut` → File menu → Import Timeline → upload `.otio.json`
   - Verify import result modal shows clip_count, duration_sec
   - Confirm → verify timeline lanes populated
