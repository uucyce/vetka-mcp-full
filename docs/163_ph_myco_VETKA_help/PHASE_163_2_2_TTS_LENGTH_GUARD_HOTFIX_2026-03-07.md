# PHASE_163_2_2_TTS_LENGTH_GUARD_HOTFIX_2026-03-07

MARKER_163.P2.HOTFIX.TTS_LENGTH_GUARD.V1

## Issue
Single MYCO_HELP turns could produce overlong responses, causing long speech playback
(`tts_duration_ms` spikes up to ~19s).

## Fix
File: `src/api/handlers/jarvis_handler.py`

1. Added `_normalize_myco_help_response(text)`:
- removes formatting noise/newlines
- keeps max 3 short sentences
- hard caps response length to 260 chars

2. Applied normalization in MYCO_HELP path before TTS.

3. Added correction-turn shortcut:
- for phrases like `ответ неверный`, `повтори`, `не услышал`
- bypasses expensive re-generation and returns compact corrected fallback.

## Expected effect
- no 10-20s speech tails for MYCO_HELP turns
- more stable short actionable guidance

## Validation
- `python -m py_compile src/api/handlers/jarvis_handler.py` -> OK
