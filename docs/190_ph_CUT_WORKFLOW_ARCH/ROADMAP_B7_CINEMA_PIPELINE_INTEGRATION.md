# ROADMAP B7: Cinema Pipeline Integration (PULSE + Logger + Media)
**Date:** 2026-03-24
**Author:** Beta (Media/Color Pipeline Architect)
**Status:** PROPOSED
**Depends on:** B5 (Audio Playback), B6 (Color Grading), B4 (Export MVP)

---

## Context

PULSE AI pipeline is 70% implemented (9 services, 4190 LOC). Logger/Scene Graph is 80%.
But **feedback signals are stubs** — visual and audio analysis assume pre-computed data.
The cinema pipeline (Script -> Logger -> PULSE -> Auto-montage -> Timeline) cannot run
end-to-end without these missing integrations.

**Key Gap:** PULSE conductor fuses 3 signals (NarrativeBPM, VisualBPM, AudioBPM).
NarrativeBPM works. VisualBPM and AudioBPM are stubs.

---

## Phase 1: Audio Signal Chain (P0 — blocks auto-montage)

### B7.1: librosa BPM + key detection service
- **Owner:** Beta
- **What:** New `src/services/cut_audio_analyzer.py`
- **Input:** Audio file path
- **Output:** `{ bpm: float, key: str, camelot_key: str, energy_contour: float[], onset_times: float[] }`
- **Tech:** librosa for BPM/onset, madmom for key detection, map to Camelot wheel
- **Why:** PULSE conductor needs AudioBPM to score scenes. Currently stub.
- **Priority:** P1 (enables music-driven montage mode)
- **Complexity:** Medium

### B7.2: Integrate audio analyzer into scan-matrix worker
- **Owner:** Beta
- **What:** scan-matrix-async calls cut_audio_analyzer for each audio/video file
- **Output:** audio_scan section gets `bpm`, `camelot_key`, `onset_times`
- **Depends on:** B7.1
- **Priority:** P1

### B7.3: Wire AudioBPM into PULSE conductor
- **Owner:** Beta
- **What:** pulse_conductor reads audio_scan.camelot_key + bpm from scan_matrix_result
- **Gap:** Currently hardcoded NarrativeBPM weight=1.0 when audio missing
- **Priority:** P2

---

## Phase 2: Visual Signal Chain (P1 — improves montage quality)

### B7.4: Motion intensity extraction from video
- **Owner:** Beta
- **What:** New method in VideoScanner: compute optical flow magnitude per segment
- **Input:** Video file path + segments from scene detection
- **Output:** `{ motion_intensity: float, cut_density: float, avg_shot_length: float }` per segment
- **Tech:** OpenCV optical flow (Farneback), no GPU needed
- **Why:** PULSE conductor needs VisualBPM for script-visual match energy
- **Priority:** P2
- **Complexity:** Medium

### B7.5: Shot scale detection (CU/MCU/MS/WS/EWS)
- **Owner:** Beta
- **What:** Face detection + frame analysis to classify shot scale
- **Tech:** MediaPipe face detection (no GPU) + heuristic (face ratio → scale)
- **Output:** `shot_scale` field per clip in scene graph
- **Why:** CUT_TARGET_ARCHITECTURE requires it for DAG media nodes
- **Priority:** P3
- **Complexity:** Medium

---

## Phase 3: Screenplay Pipeline (P1 — enables script-driven montage)

### B7.6: Fountain screenplay parser
- **Owner:** Beta
- **What:** Parse .fountain files into scene chunks with timing
- **Tech:** afterwriting-labs fountain parser (Python port) or regex
- **Output:** `{ scenes: [{ heading, content, start_sec, duration_sec }] }`
- **Rule:** 55 lines = 1 page = 60 seconds (industry standard)
- **Priority:** P2
- **Complexity:** Low

### B7.7: Final Draft FDX parser
- **Owner:** Beta
- **What:** Parse .fdx XML into same scene chunk format
- **Tech:** ElementTree XML parsing, <Scene> tag extraction
- **Priority:** P3
- **Complexity:** Low

### B7.8: Page-to-seconds timing calculator
- **Owner:** Beta
- **What:** `screenplay_timing.py` — compute start_sec/duration_sec per scene
- **Rule:** Courier 12pt, 55 lines/page, 1800-2000 chars/page = 60 sec
- **Integrates with:** pulse_script_analyzer.py (provides NarrativeBPM)
- **Priority:** P2
- **Complexity:** Low (~150 lines as per CUT_TARGET_ARCHITECTURE)

---

## Phase 4: Scene Semantics (P2 — enables intelligent material matching)

### B7.9: Character/face recognition per clip
- **Owner:** Beta (backend) + Gamma (UI)
- **What:** Detect and cluster faces across clips → character IDs
- **Tech:** face_recognition library or InsightFace (CPU-compatible)
- **Output:** `characters: [{ face_id, name, appearances: [clip_id, time_sec] }]`
- **Why:** CUT_TARGET_ARCHITECTURE requires lore nodes with character appearances
- **Priority:** P3
- **Complexity:** High

### B7.10: Material semantic similarity
- **Owner:** Beta
- **What:** Embed scene descriptions + clip metadata → vector search for matching
- **Tech:** sentence-transformers (CPU) or existing Qdrant embeddings
- **Output:** `similarity_edges` in scene graph (SCENE_GRAPH_EDGE_SEMANTIC_MATCH)
- **Why:** Auto-montage material matching currently stub (simple score comparison)
- **Priority:** P3
- **Complexity:** High

---

## Phase 5: Genre Calibration (P3 — improves montage quality)

### B7.11: Genre profile loader for energy critics
- **Owner:** Beta
- **What:** Complete GenreCalibrationProfile in pulse_energy_critics.py
- **Input:** Film genre (action, drama, documentary, horror, etc.)
- **Output:** Adjusted critic weights (e.g., action → low pendulum penalty)
- **Why:** Without calibration, counterpoint films (Nights of Cabiria) flagged as "bad"
- **Priority:** P3
- **Complexity:** Low

### B7.12: Editor feedback → critic learning
- **Owner:** Beta
- **What:** Store editor corrections (e.g., "this cut is good despite high energy")
- **Output:** Updated genre profiles based on accumulated corrections
- **Why:** Closes the feedback loop between human and AI montage
- **Priority:** P4 (someday)
- **Complexity:** High

---

## Cross-Agent Dependencies

| Task | Needs from | Description |
|------|-----------|-------------|
| B7.5 (shot scale) | Alpha | Store shot_scale in useCutEditorStore clip model |
| B7.9 (characters) | Gamma | Character panel UI in Inspector |
| B7.6 (fountain) | Alpha | Script Panel import button |
| B7.3 (AudioBPM) | Alpha | PULSE overlay in timeline (Camelot keys per clip) |
| ALL | Delta | QA verification after each phase |

---

## Priority Summary

| Phase | Items | Priority | Blocks |
|-------|-------|----------|--------|
| 1: Audio signal | B7.1-B7.3 | P1 | Music-driven auto-montage |
| 2: Visual signal | B7.4-B7.5 | P2 | Script-visual match energy |
| 3: Screenplay | B7.6-B7.8 | P2 | Script-driven auto-montage |
| 4: Semantics | B7.9-B7.10 | P3 | Intelligent material matching |
| 5: Calibration | B7.11-B7.12 | P3-P4 | Genre-aware montage quality |

---

*"PULSE is the brain. Logger is the memory. Media pipeline is the nervous system. All three must connect for CUT to think."*
