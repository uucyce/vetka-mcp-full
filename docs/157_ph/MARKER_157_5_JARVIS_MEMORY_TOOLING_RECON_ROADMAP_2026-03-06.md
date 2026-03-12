# MARKER 157.5 - VETKA-JARVIS Memory/Chunk/Tooling Recon + Roadmap

Date: 2026-03-06
Status: Recon complete, implementation roadmap approved candidate
Scope: VETKA-JARVIS in unified search bar voice mode

---

## 1. Recon Snapshot (What works now)

### 1.1 Chunk pipeline
- Stage-machine exists in `src/api/handlers/jarvis_handler.py`:
  - Chunk1: Plan B filler (`_emit_planb_filler_if_slow`)
  - Chunk2: fast model (`JARVIS_STAGE2_MODEL`, default `gemma3:1b`)
  - Chunk3: smart model (`JARVIS_STAGE3_PRIMARY_MODEL` / secondary)
  - Chunk4: deep model (conditional)
- Stage3 already gated by `_should_run_stage3(...)` to reduce latency.

### 1.2 Runtime context is passed into Jarvis
- Client (`useJarvis`) sends:
  - `viewport_context`
  - `pinned_files`
  - `open_chat_context`
  - `cam_context`
  - `llm_model`
- Server stores this in `session.client_context` and forwards via `get_jarvis_context(..., extra_context=...)`.

### 1.3 Memory integration is partially active
- `get_jarvis_context` includes:
  - STM (`stm_context`)
  - Engram preferences (`formality`, `prefers_russian`)
  - CAM summary (`overall_surprise`, etc.)
  - client runtime context
- Jarvis writes conversation back to STM (`stm.add_message(...)`).

### 1.4 Plan B bank
- 50 RU + 50 EN fillers are embedded in code.
- File override disabled by default (`JARVIS_FILLER_BANK_USE_FILE=0`), so deterministic behavior.

---

## 2. Recon Findings (Critical gaps)

### 2.1 Observability gap
- User logs mostly show tree/mcc/file activity, not Jarvis stages.
- Without `[JARVIS]` stage/tts logs, perceived behavior cannot be traced to root cause.

### 2.2 Language drift gap
- Drift to EN still possible from model behavior.
- Root cause is not memory absence only; may be model prior + weak stage prompt + unstable STT language evidence.

### 2.3 Action/tool gap (major)
- Current Jarvis is mostly voice QA response path.
- No explicit action planner/router in Jarvis for:
  - camera control
  - file open/focus
  - workflow/agent launch
  - explicit MCP tool execution
- This is why user gets generic responses like "show file" without real action.

### 2.4 Quality under turn depth
- After 3-5 turns quality decays:
  - accumulated context not compacted strongly enough for voice path
  - stage prompts remain generic and do not enforce action-oriented output schema

### 2.5 TTS reliability
- Historic `tts_engine timeout` and occasional noise indicates audio-path fragility under mixed providers.
- Stability improved, but needs formal guardrails and telemetry.

---

## 3. Target Contract (Speed + Quality + Actions)

### 3.1 Voice latency target
- TTFA (first audible) <= 1.2s p50, <= 2.0s p95.
- End-to-end first meaningful sentence <= 3.0s p95.

### 3.2 Response quality target
- Language adherence >= 95% (user language continuity per session).
- Hallucination-like generic fallback < 5%.
- Actionability score >= 0.8 on action-intent queries.

### 3.3 Action target
For action intent, Jarvis must either:
1. Execute action (camera/tool/workflow), or
2. Return explicit structured refusal with reason + next step.

---

## 4. Architecture Direction (No hardcoded language lock)

### 4.1 Language policy (memory-driven)
- Source-of-truth priority:
  1. Engram `communication_style.prefers_russian` (or future `preferred_language`)
  2. STT inferred language for current utterance
  3. last successful assistant language in session state
- Prompt instruction remains soft (prefer language), not hard lock.

### 4.2 Context packing for voice turns
- Voice-specific compact context builder:
  - current utterance
  - last 4 dialog turns (compressed)
  - viewport summary
  - top pinned files (by recency and relevance)
  - STM highlights
  - CAM salience hints
- ELISION always-on for voice path (fast profile).

### 4.3 Action router layer before LLM long answer
- Detect intent classes:
  - `query` / `file_lookup` / `camera_control` / `run_workflow` / `agent_mention` / `tool_call`
- For deterministic actions, call tool/command first, then verbalize result.

---

## 5. Implementation Roadmap

## Phase 157.5.1 - Voice Observability Hardening
- Add compact session trace for each utterance:
  - stt_lang, context_size, stages hit, selected models, ttfa_ms, tts_provider, audio_format
- Add explicit `[JARVIS][TRACE]` line per turn.
- Add debug endpoint to fetch last N Jarvis traces.

Acceptance:
- One voice turn can be fully reconstructed from logs without scanning MCC/tree logs.

## Phase 157.5.2 - Memory Contract Enforcement
- Add `preferred_language` field in Engram communication_style (string `ru|en|auto`).
- Update `get_jarvis_context` to include:
  - `preferred_language`
  - `last_assistant_language`
  - compressed `session_summary` from STM/ELISION
- Add tests for language continuity across 5+ turns.

Acceptance:
- Same user gets stable language on 10-turn run unless explicit switch request.

## Phase 157.5.3 - Action Router for VETKA-JARVIS
- Add pre-LLM action router in `jarvis_handler`:
  - camera intents -> camera command emit
  - file intents -> search/open API calls
  - workflow intents -> workflow handler calls
  - agent intents -> forward to existing agent pipeline
- LLM handles only narrative/explanatory output when router does not match deterministic action.

Acceptance:
- On action prompts, Jarvis performs action and narrates result.

## Phase 157.5.4 - Voice Context Packer (ELISION/CAM/STM)
- Implement `build_jarvis_voice_context()`:
  - budgeted token packing
  - deterministic order
  - ELISION compression metadata
- Keep JEPA optional only under pressure thresholds (docs_count/entropy/token pressure).

Acceptance:
- Context overflow errors disappear in 20-turn stress run.

## Phase 157.5.5 - TTS Stability + Quality Gate
- Add audio validation before emit (already partially done) + provider fallback trace.
- Add no-audio/noise detector and auto-retry once with alternate provider.
- Add RU voice quality check gate in benchmark script.

Acceptance:
- No critical noise artifacts in 30-turn soak test.

---

## 6. Test Matrix (must-have)

1. 10-turn RU dialog, no explicit language switch.
2. 10-turn EN dialog, no explicit language switch.
3. Mixed language turn (explicit switch request).
4. Action intents:
   - "покажи файл ..."
   - "приблизь камеру к ..."
   - "запусти workflow ..."
5. Interrupt test: user interrupts during speaking.
6. Long-session test (30 turns) for drift and latency regression.

Metrics captured:
- ttfa_audio_ms
- end_to_end_ms
- language_match_rate
- action_success_rate
- fallback_rate
- tts_error_rate

---

## 7. GO / NO-GO for next implementation sprint

GO if:
- trace visibility added,
- language continuity test passes >=95%,
- action router executes >=80% deterministic intents in test set,
- no severe audio artifacts in soak test.

NO-GO if:
- no traceability,
- language drift persists >10% after memory contract,
- action intents still return generic text-only replies.

---

## 8. Immediate next step (recommended)

Start with **Phase 157.5.1 + 157.5.2** (observability + memory contract) before further model swapping.
This will prevent blind tuning and avoid accumulating hardcoded patches.

