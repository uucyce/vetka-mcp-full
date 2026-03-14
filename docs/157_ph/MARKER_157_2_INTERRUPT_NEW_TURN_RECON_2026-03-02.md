# MARKER_157_2_INTERRUPT_NEW_TURN_RECON_2026-03-02

## Scope
Phase 157.2 recon for:
- interrupt + new turn architecture
- tool-loop transparency in chat
- voice low-latency handoff (Jarvis/live mode)
- JEPA role in pre-context and voice path

Date: 2026-03-02
Status: VERIFIED FROM CODE + DOCS

## Sources Audited
- `docs/150_ph/stream_GROK.txt`
- `docs/157_ph/MARKER_157_*`
- `src/api/handlers/user_message_handler.py`
- `src/api/handlers/voice_router.py`
- `src/api/handlers/voice_socket_handler.py`
- `src/services/progressive_tts_service.py`
- `src/orchestration/context_packer.py`
- `src/services/mcc_jepa_adapter.py`
- `src/services/jepa_runtime.py`
- `client/src/hooks/useSocket.ts`
- `client/src/hooks/useRealtimeVoice.ts`
- tests under `tests/` for stream/voice/jepa

---

## MARKER_157.2A Current Runtime Map (What Exists)

### A1. Text stream and tool visibility
Implemented:
- server emits `stream_start`, `stream_token`, `stream_end`
- pre-stream tool phase exists when provider does not support in-stream tool calling
- tool results can be emitted to UI (`tool_result`/`tool_error` paths)
- capability matrix explicitly tracks `tool_calling_in_stream`

Evidence:
- `src/api/handlers/user_message_handler.py` (stream events + pre-stream tool phase)
- `tests/test_capability_matrix.py`

### A2. Realtime voice interrupt (separate pipeline)
Implemented:
- dedicated state machine: `IDLE -> LISTENING -> PROCESSING -> GENERATING -> SPEAKING`
- `voice_interrupt` cancels current task and emits `voice_interrupted`
- frontend auto-interrupt when user speaks during model response

Evidence:
- `src/api/handlers/voice_router.py`
- `src/api/handlers/voice_socket_handler.py`
- `client/src/hooks/useRealtimeVoice.ts`

### A3. Chat voice stream (solo voice events)
Implemented:
- emits `chat_voice_stream_start/chunk/end`
- emits JEPA trace in `chat_voice_stream_end`
- sentence-level chunking + optional JEPA-assisted condensation

Evidence:
- `src/api/handlers/user_message_handler.py`
- `src/services/progressive_tts_service.py`

### A4. Context packer + JEPA
Implemented:
- hybrid context packer with trigger/hysteresis
- JEPA fallback semantic core for overflow risk
- trace stats + tests

Evidence:
- `src/orchestration/context_packer.py`
- `tests/test_phase157_context_packer.py`

---

## MARKER_157.2B Gaps (What Is Missing)

### B1. Missing unified interrupt+restart for chat stream
Current behavior:
- chat path streams LLM tokens to end, then schedules voice output from final text
- no first-class cancellation + context-delta restart for same message generation

Impact:
- cannot inject newly arrived tool/JEPA/context updates into an active generation
- slower perceived voice interactivity for long responses

### B2. Missing explicit tool-loop control protocol in chat UI/backend contract
Current behavior:
- partial support exists, but no single stable state machine for:
  - `tool_call_proposed -> approve/edit/reject -> execute -> resume stream`

Impact:
- transparency present but fragmented
- hard to guarantee deterministic behavior across providers

### B3. Missing benchmark harness for A/B/C voice modes
Need production-grade metrics for:
- mode A: qwen-only voice loop
- mode B: API-LLM + qwen-tts
- mode C: API-LLM + JEPA assist + qwen-tts

Impact:
- decisions currently heuristic; no strict SLO gates

---

## MARKER_157.2C JEPA Placement (Decision)

JEPA is useful in two places only:
1. **Pre-LLM context packing** (primary): reduce overflow risk and keep semantic core.
2. **Post-text/pre-TTS compression** (secondary): shorten spoken output while preserving opening and salient sentences.

JEPA should **not** be treated as direct token generator replacing LLM reasoning.

For active stream updates, use:
- interrupt current stream
- rebuild context (including JEPA delta)
- restart stream with continuity marker

---

## MARKER_157.2D Existing Tests (with and without JEPA)

Without JEPA / baseline coverage already exists:
- stream events and visibility (`tests/test_phase104_stream.py`)
- capability routing and tool mode (`tests/test_capability_matrix.py`)
- realtime voice interrupt flow (`voice_router` behavior + frontend hook paths)

With JEPA coverage:
- context packer JEPA trigger/hysteresis/fallback (`tests/test_phase157_context_packer.py`)
- voice JEPA assist + no-JEPA baseline (`tests/test_voice_jepa_assist.py`)

Conclusion:
- baseline tests exist; JEPA did not replace baseline coverage.

---

## MARKER_157.2E Proposed Architecture Delta (Minimal-Risk)

### E1. Introduce unified Stream Session FSM (chat+voice)
States:
- `RUNNING`
- `INTERRUPT_REQUESTED`
- `CANCELLED`
- `REBUILDING_CONTEXT`
- `RESTARTED`
- `COMPLETED`

### E2. Add control events (Socket contract)
- `stream_interrupt_request`
- `stream_interrupt_ack`
- `stream_restart_start`
- `stream_restart_token`
- `stream_restart_end`
- `tool_call_proposed`
- `tool_call_decision` (`approve|edit|reject`)

### E3. Preserve transparency in chat
Every tool action visible in timeline with args/result summary and status transitions.

### E4. Keep realtime voice router untouched initially
Phase 157.2 should first upgrade chat stream+voice bridge, not replace Phase 60.5.1 realtime pipeline.

---

## MARKER_157.2F SLO/Acceptance Targets

- Text TTFT p50 < 700 ms, p95 < 1800 ms
- Voice TTFA (first audio chunk) p50 < 1200 ms, p95 < 2500 ms
- Interrupt reaction p95 < 250 ms (ack + cancel path)
- Restart after interrupt p95 < 1200 ms to first new token
- No hidden tool execution: 100% tool calls reflected in UI stream log

---

## Recommendation on Docs Structure

Use **new docs in `docs/157_ph`** instead of rewriting old ones.
Reason:
- preserves auditability and marker chronology
- avoids breaking previous phase references
- keeps rollout decisions explicit per date

Keep `docs/150_ph` as historical research input; add forward-only implementation docs in `157_ph`.

