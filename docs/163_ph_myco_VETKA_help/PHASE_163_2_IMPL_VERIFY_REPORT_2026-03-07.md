# PHASE_163_2_IMPL_VERIFY_REPORT_2026-03-07

MARKER_163.P2.REPORT.V1

## Scope
Phase 163.2 implemented in VETKA voice/backend path only.
No MCC UI files changed.

## Implemented

1. MYCO_HELP intent routing in voice stage-machine
- File: `src/api/handlers/jarvis_handler.py`
- Added `_is_myco_help_intent(...)` for help/system/UI queries.
- Added `_build_myco_help_stage_hint(...)` to enforce response contract.
- On MYCO_HELP turns:
  - stage2 uses MYCO_HELP contract hint
  - stage3/stage4 are skipped to reduce noise/latency

2. MYCO_HELP response contract (backend-driven)
- Contract enforced via stage hint:
  - what user sees now
  - what user can do next
  - exact next click/step

3. RU language guard for MYCO_HELP turns
- If user speech is RU but model returns EN:
  - one fast rewrite pass on stage2 model with strict RU instruction

4. Prompt policy reinforcement
- File: `src/voice/jarvis_llm.py`
- Added MYCO_HELP policy block in system prompt when `myco_help_mode=true`.

## Verification
- `python -m py_compile src/api/handlers/jarvis_handler.py src/voice/jarvis_llm.py` -> OK

## Manual runtime checks
1. Ask (RU):
- "что я сейчас вижу"
- "что можно сделать с этим файлом"
- "как закрепить несколько файлов"

Expected:
- mostly `chunk2_fast`
- short actionable answer with see-now + next actions + next click
- no English drift on RU turns

2. Traces (`/api/debug/jarvis/traces?limit=10`):
- `myco_help_mode=true`
- `planb_filler_effective=false`
- `voice_lock_edge_ru_female=true`
- stage list mostly `['chunk2_fast']` for help queries
