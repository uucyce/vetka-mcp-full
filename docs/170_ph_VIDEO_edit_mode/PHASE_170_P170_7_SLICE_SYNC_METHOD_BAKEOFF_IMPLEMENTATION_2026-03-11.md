# PHASE 170 P170.7 Slice + Sync Method Bakeoff Implementation
**Date:** 2026-03-11  
**Status:** implementation/recon capture  
**Scope:** pause-aware marker slicing and audio-sync method evaluation for `VETKA CUT`

## Why this doc exists
We now have three layers for CUT marker windows:
1. `preview_window_v1`
2. `transcript_pause_window_v1`
3. future full `pause/silence-aware` and `audio-sync` worker logic

Before introducing heavier worker dependencies, CUT needs a narrow bakeoff plan to compare candidate methods on controlled fixtures and synthetic signals.

## External recon captured
### Pause/silence-aware slicing shortlist
1. `pydub.split_on_silence` / `detect_silence`
   - threshold-driven, fast, CPU-friendly
   - best baseline for local editorial chunking
2. `pyannote.audio`
   - stronger VAD/segmentation accuracy
   - better for noisy speech and speaker-aware editorial slicing
   - heavier runtime and model cost

### Audio sync shortlist
1. `scipy.signal.correlate + find_peaks`
   - minimal baseline
   - good first CUT worker candidate
2. `audalign`
   - rough fingerprint + refinement
   - better fallback for noisier multicam material
3. `Aurio`
   - valid research/production reference, but heavier to adopt

## Recommended CUT direction
### Marker slicing
1. keep current `transcript_pause_window_v1` as interim shell heuristic
2. add worker-backed `energy_pause_v1` baseline with `pydub`-style silence detection
3. compare `transcript_pause_v1` vs `energy_pause_v1` on the same fixtures
4. if both disagree, prefer hybrid union/merge rules for editorial windows
5. reserve `pyannote` for premium/noisy material later

### Audio sync
1. start with `peaks + correlation` baseline
2. compare against peak-only heuristic on noisy synthetic fixtures
3. keep `audalign` as optional fallback if the baseline underperforms on real multicam footage
4. freeze CUT sync contract only after bakeoff metrics are stable

## Hybrid recommendation
### Slice hybrid
- transcript segments define semantic anchors
- silence windows define hard stop boundaries
- merged window becomes the editorial marker slice
- use transcript when available, silence-only fallback when transcript is absent

### Sync hybrid
- detect rough candidate offset from large peaks / envelope
- refine offset with correlation around the candidate lag window
- if peak-only and correlation disagree sharply, use confidence gate and mark degraded reason

## Special tests to add
### Slicing bakeoff
1. synthetic speech/pause fixture with clean silence
2. noisy speech fixture where transcript windows are still stable but threshold slicing drifts
3. merged transcript chunk fixture where hybrid should produce fewer, more editorial windows than raw threshold-only splitting

### Sync bakeoff
1. exact shifted signal pair
2. noisy shifted signal pair
3. peak-only false positive case where hybrid/correlation should outperform raw peak matching

## Narrow implementation rule
- do not pull heavy external dependencies into CUT runtime yet
- first comparison tests may use reference/pure-python implementations to validate decision logic
- once the bakeoff confirms a winner, replace reference logic with worker-backed libraries

## Immediate implementation slice
1. [x] add pure-python reference evaluators for slicing and sync
2. [x] add focused phase170 tests for the bakeoff
3. [x] store recommendation in docs and roadmap markers
4. [x] freeze `cut_audio_sync_result_v1` and add first worker-backed `audio_sync_v1`
5. [x] start the real worker-backed `energy_pause_v1`
6. [ ] connect `slice_bundle` into marker creation and selected-shot UI

## Markers
1. `MARKER_170.INTEL.SLICE_METHOD_BAKEOFF`
2. `MARKER_170.WORKER.AUDIO_SYNC_BAKEOFF`
3. `MARKER_170.INTEL.HYBRID_SLICE_SYNC_RECOMMENDATION`
