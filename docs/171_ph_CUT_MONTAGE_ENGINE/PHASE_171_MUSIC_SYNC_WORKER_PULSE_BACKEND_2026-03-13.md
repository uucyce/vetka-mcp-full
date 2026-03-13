# Phase 171 Music Sync Worker PULSE Backend

Task IDs:
- `tb_1773368490_9`
- `tb_1773368493_10`

Implemented:
- `POST /api/cut/worker/music-sync-async` in [src/api/routes/cut_routes.py](/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/src/api/routes/cut_routes.py)
- standard CUT async job envelope with duplicate-job suppression and persisted output at `cut_runtime/state/music_sync_result.latest.json`
- PULSE-backed tempo resolution for known tracks via `pulse/data/processed/jepa_training_manifest.jsonl`
- native beat/onset path via the existing librosa-compatible analysis pattern
- degraded-safe fallback proxy when native/runtime analysis is unavailable

Result shape:
- `schema_version = cut_music_sync_result_v1`
- `tempo { bpm, confidence }`
- `downbeats[]`
- `phrases[]`
- `cue_points[]`
- `derived_from`

Verification:
- `pytest -q tests/phase170/test_cut_music_sync_worker_api.py`
