# PHASE_163_2_1_HOTFIX_REPORT_2026-03-07

MARKER_163.P2.HOTFIX.VOICE_LANG_GROUNDING.V1

## Trigger
Observed runtime issues after 163.2:
- perceived multi-voice / male voice drift
- English response drift in RU turns
- weak grounding on "what can I do" queries when retrieval hits=0

## Fixes applied (VETKA voice/backend only)

1. Fixed edge voice call path
- File: `src/api/handlers/jarvis_handler.py`
- Changed edge synthesis from `synthesize_auto(response_text)` to `synthesize(response_text)`.
- Reason: `synthesize_auto` forces `*-male` voice based on language detection.
- Effect: keeps configured `vetka_ru_female` consistently.

2. Added global RU language guard (not only MYCO_HELP intent)
- File: `src/api/handlers/jarvis_handler.py`
- If session/user preference indicates RU and model output is EN:
  - run short RU rewrite pass on stage2 model.

3. Added deterministic MYCO_HELP fallback when retrieval grounding is empty
- File: `src/api/handlers/jarvis_handler.py`
- If MYCO_HELP turn and `hidden_retrieval_hits == 0`:
  - produce safe action-pack response tied to VETKA operations
    (open in Artifact / edit+save / pin via Shift + next click).

4. Expanded MYCO_HELP intent matcher
- Added cues like `ответ невер`, `не услышал`, `повтори` to keep helper mode active in correction turns.

## Verification
- `python -m py_compile src/api/handlers/jarvis_handler.py` -> OK

## What to check in live traces
1. `tts_provider` should remain `fast_tts_edge` and no male drift from auto voice.
2. RU turns should keep `response_lang=ru` even for corrective follow-ups.
3. For help turns with empty retrieval, answer should still be actionable and not hallucinated.
