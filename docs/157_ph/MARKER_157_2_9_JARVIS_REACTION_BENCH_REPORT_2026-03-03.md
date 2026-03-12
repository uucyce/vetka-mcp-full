# MARKER_157_2_9: Jarvis Reaction Bench Report (2026-03-03)

## Scope
- Added test-mode question-end endpointing hooks.
- Integrated Plan B filler guard in Jarvis LLM path (delayed draft phrase if response is slow).
- Measured live voice benchmark on 3 modes with decision-grade settings.

## Code Changes
- `src/api/handlers/jarvis_handler.py`
  - Added Plan B config/env:
    - `VETKA_JARVIS_PLANB_FILLER_ENABLE`
    - `VETKA_JARVIS_PLANB_FILLER_DELAY_SEC`
  - Added helper methods:
    - `_pick_planb_filler(...)`
    - `_emit_planb_filler_if_slow(...)`
  - Integrated filler task lifecycle in `jarvis_listen_stop`:
    - start at THINKING/LLM start
    - auto-cancel when LLM completes
  - Added question-end endpointing test-mode controls:
    - `VETKA_JARVIS_QEND_TEST_MODE`
    - `VETKA_JARVIS_QEND_SILENCE_DURATION`
    - `VETKA_JARVIS_QEND_MIN_WORDS`
  - Added A/B helper: `compute_question_endpointing_ab(...)`.

- `tests/test_phase157_planb_filler.py`
  - verifies filler disabled path
  - verifies no filler when ready-event already set
  - verifies single filler emission on slow path

## Validation
- `pytest -q tests/test_phase157_question_endpointing.py tests/test_phase157_planb_filler.py tests/test_phase157_voice_benchmark_harness.py`
- Result: **7 passed**.

## Live Benchmark Run
Command:
```bash
python scripts/voice_mode_benchmark.py --runs-per-prompt 3 --per-run-timeout-sec 25
```
Artifacts:
- `docs/157_ph/benchmarks/phase157_voice_ab_test_live_20260303_011914.json`
- `docs/157_ph/benchmarks/phase157_voice_ab_test_live_20260303_011914.csv`

Summary (p50):
- **A_qwen_only**
  - reaction_text: **174 ms**
  - reaction_audio: **3365 ms**
- **B_api_tts**
  - reaction_text: **6879 ms**
  - reaction_audio: **14034 ms**
- **C_api_jepa_tts**
  - reaction_text: **6084 ms**
  - reaction_audio: **13359 ms**

Interpretation:
- Target `<=1s` for immediate reaction is currently met only by Qwen-only text reaction (p50 174ms).
- API paths remain above 5s on p50 reaction_text.
- Plan B filler is justified for API voice mode to keep conversation feeling responsive.

## JEPA Probe (Gradient)
Command:
```bash
python scripts/voice_jepa_probe.py --min-words 6 --max-words 75 --step 7 --runs-per-bucket 3 --out docs/157_ph/voice_jepa_probe_latest.json
```
Result:
- total runs: 30
- trigger rate: 6.67%
- latency p50: 0.55 ms
- latency p95: 0.55 ms

## Recommended Runtime Settings (next live pass)
```bash
export VETKA_JARVIS_PLANB_FILLER_ENABLE=1
export VETKA_JARVIS_PLANB_FILLER_DELAY_SEC=5.0
# optional test-only endpointing experiment
export VETKA_JARVIS_QEND_TEST_MODE=1
export VETKA_JARVIS_QEND_SILENCE_DURATION=0.9
export VETKA_JARVIS_QEND_MIN_WORDS=3
```

## Decision
- Keep Plan B filler support in codebase (already integrated, env-controlled).
- For production-like voice sessions with API model path, enable Plan B until reaction_text p50 drops below 5s.
- Keep question-end endpointing in test mode and run dedicated false-cut A/B before enabling by default.
