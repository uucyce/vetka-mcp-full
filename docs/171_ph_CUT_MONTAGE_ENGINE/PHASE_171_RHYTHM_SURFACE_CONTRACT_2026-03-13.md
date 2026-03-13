# Phase 171 Rhythm Surface Contract

Task ID:
- `tb_1773368495_11`

Implemented:
- new contract [docs/contracts/cut_rhythm_surface_v1.schema.json](/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/docs/contracts/cut_rhythm_surface_v1.schema.json)
- `project-state` now returns `rhythm_surface` and `rhythm_surface_ready`
- `rhythm_surface` merges:
  - music cue anchors from `cut_music_sync_result_v1`
  - scene target BPM proxy derived from CUT timeline density
  - recommendation labels per cue (`accent_cut`, `phrase_bridge`, `micro_hit`, `downbeat_lock`)

Shape:
- `music_tempo_bpm`
- `scene_target_bpm`
- `bpm_delta`
- `rhythm_profile`
- `cut_density_per_min`
- `source_engine`
- `items[]`

Verification:
- `pytest -q tests/phase170/test_cut_music_sync_worker_api.py tests/phase170/test_cut_music_sync_summary.py tests/phase170/test_cut_project_state_api.py tests/phase170/test_cut_contract_schemas.py`
