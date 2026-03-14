# MARKER_157_2_INTERRUPT_NEW_TURN_IMPLEMENTATION_CHECKLIST_2026-03-02

## Goal
Deliver interrupt + new turn for chat/voice with full tool transparency and measurable JEPA impact.

## Phase 157.2.1 - Recon Freeze
- [x] Audit current stream/tool/voice/jepa paths
- [x] Record current gaps and SLO targets
- [ ] Freeze event contract v1

## Phase 157.2.2 - Protocol Layer
- [ ] Add backend stream session registry (`session_id`, `generation_id`, state)
- [ ] Add socket events:
  - [ ] `stream_interrupt_request`
  - [ ] `stream_interrupt_ack`
  - [ ] `stream_restart_start`
  - [ ] `stream_restart_token`
  - [ ] `stream_restart_end`
- [ ] Add typed frontend handlers in `useSocket.ts`

## Phase 157.2.3 - Tool Loop Transparency
- [ ] Adaptive tool-loop policy by model capabilities:
  - [ ] if `tool_calling_in_stream=true`: use native stream tool path
  - [ ] else: enforce pre/post tool phase with explicit UI step visualization
- [ ] Standardize `tool_call_proposed` payload
- [ ] Add `tool_call_decision` command (`approve|edit|reject`)
- [ ] Persist tool timeline entries in chat history metadata
- [ ] Ensure all tool paths emit status transitions

## Phase 157.2.4 - Voice Bridge (Jarvis chat mode)
- [ ] Allow early sentence buffer from partial LLM stream
- [ ] Start progressive TTS from sentence-ready partials
- [ ] On interrupt: stop queued TTS chunks + cancel active generation
- [ ] On restart: attach continuity marker in UI

## Phase 157.2.5 - JEPA Triggered Context Delta
- [ ] Add context-delta builder on restart
- [ ] Re-run JEPA only when trigger satisfied (token pressure/docs/entropy)
- [ ] Include JEPA trace in restart metadata

## Phase 157.2.6 - Benchmarks & Tests
- [ ] Build benchmark harness for 3 modes:
  - [ ] A: qwen-only
  - [ ] B: api-llm + qwen-tts
  - [ ] C: api-llm + jepa + qwen-tts
- [ ] Persist metrics JSON + CSV in `docs/157_ph/benchmarks/`
- [ ] Add tests:
  - [ ] interrupt cancels and restarts stream
  - [ ] tool-call decision affects execution path
  - [ ] voice first-chunk under partial streaming
  - [ ] no hidden tool execution in timeline

## Test Matrix (Required)
- [ ] `test_phase157_stream_interrupt_restart.py`
- [ ] `test_phase157_tool_loop_visibility.py`
- [ ] `test_phase157_voice_partial_tts_handoff.py`
- [ ] `test_phase157_benchmark_modes.py`

## Acceptance Gates
- [ ] all new tests pass
- [ ] no regression in existing `phase104_stream`, `capability_matrix`, `voice_jepa_assist`, `phase157_context_packer`
- [ ] benchmark evidence for chosen default mode (A/B/C)

## Phase 157.2.7 - TTS Runtime Hardening (Apple Silicon MLX, no migration)
- [ ] Add proxy-safe loopback policy for local TTS calls (`trust_env=False`)
- [ ] Add readiness gate + warmup before live benchmark runs
- [ ] Run decision-grade benchmark:
  - [ ] `python scripts/voice_mode_benchmark.py --runs-per-prompt 3 --per-run-timeout-sec 25`
- [ ] Capture TTFT / TTFA / E2E deltas for A/B/C after stabilization
- [ ] Evaluate external references and port only proven runtime practices:
  - [ ] `kapi2800/qwen3-tts-apple-silicon` (MLX launch/runtime patterns)
  - [ ] `TrevorS/qwen3-tts-rs` as R&D only (future ultra-low-latency backend)

## Phase 157.2.8 - Reaction-First Voice Metrics + Endpointing
- [ ] Benchmark KPI priority update:
  - [ ] `reaction_text_ms` (user end-of-speech -> first model token)
  - [ ] `reaction_audio_ms` (user end-of-speech -> first playable audio chunk)
  - [ ] `quality_proxy` (non-empty, non-error response signal)
- [ ] Verify endpoint trigger chain in runtime:
  - [ ] `silence -> auto-stop -> response start` (Jarvis VAD path)
  - [ ] `voice_utterance_end` path (realtime pipeline)
- [ ] Add tuning controls for endpointing:
  - [ ] silence duration threshold tuning
  - [ ] min speech duration tuning
- [ ] Add exploratory policy for question-ending utterances:
  - [ ] if user utterance likely ends with `?`, allow earlier endpointing profile in test mode
  - [ ] compare false-cut rate vs latency gain

## Phase 157.2.9 - Plan B (Sub-5s UX Guard)
- [ ] Add pre-response fillers (non-blocking) if reaction exceeds 5s:
  - [ ] "Секунду, думаю..."
  - [ ] "Хороший вопрос..."
  - [ ] "Сейчас соберу контекст..."
- [ ] Gate fillers behind strict conditions:
  - [ ] only once per turn
  - [ ] cancel immediately when real TTS starts
  - [ ] disable for very short turns where model already responds fast

## Phase 157.2.10 - Jarvis Model Phonebook (Explicit User Choice)
- [ ] Add Jarvis model selector in phonebook UI (no hidden auto-switching)
- [ ] Persist selected Jarvis model/source per user/session
- [ ] Show active Jarvis model/source clearly in voice mode UI
- [ ] Route Jarvis requests strictly through selected model until user changes it
