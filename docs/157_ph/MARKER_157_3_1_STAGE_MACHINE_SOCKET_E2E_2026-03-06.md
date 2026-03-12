# MARKER 157.3.1 — Stage-Machine Socket E2E (2026-03-06)

## Implemented

### 1) Full Jarvis socket e2e benchmark harness
Added:
- `scripts/voice_stage_machine_e2e.py`

What it measures (real socket path):
- `jarvis_listen_start` -> `jarvis_listen_stop(transcript_hint)`
- first filler response (`status=filler`)
- first non-filler response
- first audio chunk (`jarvis_audio`)
- return to `jarvis_state=idle`
- stage sequence from `jarvis_stage`

Outputs:
- `docs/157_ph/benchmarks/phase157_stage_machine_e2e_<ts>.json`
- `docs/157_ph/benchmarks/phase157_stage_machine_e2e_<ts>.csv`
- `docs/157_ph/benchmarks/phase157_stage_machine_e2e_<ts>.md`

### 2) Minimal UI progress indicator
Updated:
- `client/src/components/search/UnifiedSearchBar.tsx`

Behavior:
- when `voiceState === 'thinking'`, input area shows
  - `ВЕТКА думает...` (animated dots, no extra buttons)
- existing mic/wave behavior preserved.

## Current E2E run result
Run command:
- `python scripts/voice_stage_machine_e2e.py --runs-per-prompt 1 --timeout-sec 50`

Artifact:
- `docs/157_ph/benchmarks/phase157_stage_machine_e2e_20260306_020353.*`

Observed:
- success `0/3`
- no `jarvis_response` / `jarvis_audio` / `jarvis_stage` events received
- all runs timed out.

Interpretation:
- benchmark harness is working (connect + timeout tracking + artifact export),
- but runtime did not produce Jarvis events in that session.

Likely runtime prerequisite mismatch:
- Jarvis handler disabled in backend startup (`VETKA_JARVIS_ENABLE` not set), or
- running server instance differs from expected `http://127.0.0.1:5001` process/session.

## Next check in live runtime
1. Start backend with Jarvis enabled.
2. Re-run:
   - `python scripts/voice_stage_machine_e2e.py --runs-per-prompt 3 --timeout-sec 60`
3. Validate non-zero:
   - `ttfr_filler_ms_p50`
   - `ttfr_response_ms_p50`
   - `ttfa_audio_ms_p50`
