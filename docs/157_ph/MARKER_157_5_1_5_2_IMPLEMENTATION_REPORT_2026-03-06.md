# MARKER 157.5.1 + 157.5.2 Implementation Report

Date: 2026-03-06
Status: Implemented

## Scope
- 157.5.1: Jarvis observability hardening (per-turn trace)
- 157.5.2: Memory contract for language/session continuity

## Implemented

### A. Jarvis traceability (157.5.1)
1. Added in-memory per-turn trace ring buffer in `src/api/handlers/jarvis_handler.py`.
2. Added trace API accessor:
   - `get_jarvis_turn_traces(limit=...)`
3. Added detailed trace payload recording at end of voice turn with:
   - stt language/confidence
   - response language/status
   - stages hit and selected models
   - context keys/size
   - first response latency and total turn latency
   - tts provider/format/duration/success
4. Added log line:
   - `[JARVIS][TRACE] {...}`
5. Added debug endpoint:
   - `GET /api/debug/jarvis/traces?limit=20`
   - file: `src/api/routes/debug_routes.py`

### B. Memory contract (157.5.2)
1. Extended `get_jarvis_context` in `src/voice/jarvis_llm.py` with:
   - `preferred_language` (Engram)
   - `last_assistant_language` (Engram)
   - `session_summary` (STM-derived, ELISION-compressed)
2. Updated system prompt builder to include these fields as soft policy hints.
3. Added persistence of assistant language in `jarvis_handler.py`:
   - `_remember_last_assistant_language(...)`

## Tests
- Added: `tests/test_phase157_5_memory_contract.py`
  - trace buffer getter
  - context includes memory contract fields
- Regression suite executed:
  - `tests/test_phase157_planb_filler.py`
  - `tests/test_phase157_3_1_stage_machine_basics.py`
  - `tests/test_phase157_5_memory_contract.py`
  - `tests/jarvis_live/test_jarvis_live_context.py`
- Result: 11 passed

## Notes
- Hard language lock/rewrite path is removed in favor of memory-driven soft guidance.
- Next phase should add action router (camera/file/workflow) so Jarvis does real actions, not generic voice replies.

