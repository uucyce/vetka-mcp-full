# MARKER_156.S6_AUTOSTART_AND_REGRESSION_TEST

Date: 2026-02-26

## Implemented

1. `MARKER_156.VOICE.S6_TTS_AUTOSTART_PYTHON_RESOLVE`
- File: `src/voice/tts_server_manager.py`
- Added resilient python resolver for TTS server startup:
  - env override: `VETKA_TTS_PYTHON`
  - candidates: `venv_voice`, `.venv`, `venv`, `sys.executable`, `python3/python`
  - strict validation: `from mlx_audio.tts import load_model`
- Startup now fails gracefully with explicit diagnostics instead of hard path failure.

2. Added S6 tests:
- File: `tests/test_phase156_voice_s6.py`
- Covers:
  - resolver selection behavior
  - no-candidate fallback behavior
  - start_tts_server interpreter usage
  - group role voice lock stability
  - voice_auto persistence in group policy

## Runtime verification (current machine)

- Resolver searched interpreters and did not find a valid `mlx_audio.tts.load_model` runtime.
- `start_tts_server(wait_ready=False)` returns `None` with actionable warning.
- This confirms autostart logic is fixed and deterministic, but environment still lacks a working mlx-audio install.

## Regression test runs

### Targeted (related to S6 changes)
- `tests/test_phase156_voice_s6.py` -> **5 passed**
- `tests/test_model_autodetect_api.py tests/test_phase124_3_auto_read.py` -> **21 passed**

### Full suite status snapshot
- `pytest -q` fails at collection due invalid `tests/test_agents_routes.py` (markdown fence syntax).
- `pytest -q --ignore=tests/test_agents_routes.py`:
  - **3047 passed**, **195 failed**, **17 skipped**, **1 error**
  - Failures are broad pre-existing regressions outside S6 scope.

## Notes
- Because network package install is unavailable in current environment (pip DNS resolution errors), automatic dependency repair for mlx-audio could not be completed.
- To fully enable local Qwen TTS autostart, a valid Python environment with `mlx_audio` and model runtime is still required.

## Follow-up execution (same day, with network enabled)

After network-enabled install in `venv_voice`, runtime blockers were resolved iteratively:

1. Installed base stack:
- `mlx-audio fastapi uvicorn numpy`

2. Startup error fixed:
- Missing `PIL.Image` -> installed `pillow`

3. Startup error fixed:
- `packaging.version.InvalidVersion: 'N/A'` from accelerate detection -> installed `accelerate` (and deps)

4. Final smoke result:
- `GET http://127.0.0.1:5003/health` returned healthy:
  - `profile=4bit`
  - `model=mlx-community/Qwen3-TTS-12Hz-0.6B-CustomVoice-4bit`
- `POST /tts/generate` succeeded:
  - `format=wav`
  - `sample_rate=24000`
  - `duration=5.92`
  - non-empty audio payload

Conclusion: autostart path and S6 profile switch are functionally valid; local Qwen 4bit TTS is operational in this environment.
