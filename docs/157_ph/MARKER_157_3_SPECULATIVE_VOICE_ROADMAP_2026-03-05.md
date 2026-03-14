# MARKER_157_3_SPECULATIVE_VOICE_ROADMAP_2026-03-05

Date: 2026-03-05  
Scope: Jarvis voice runtime in VETKA (single search bar voice mode), local-first optimization on Apple Silicon (M4), with fallback-safe UX.

## 0) Objective and constraints

Primary objective:
- Reduce perceived voice reaction delay to near-real-time by combining:
  - speculative text path (`draft -> target`) for early tokens/chunks,
  - robust chunk-to-TTS streaming,
  - adaptive filler safety-net (Plan B) only when needed.

Non-negotiable constraints:
- No new UI buttons.
- Do not break existing chat-panel voice behavior (multi-model voice messages in chat context).
- Maintain transparent telemetry and traceability in logs/artifacts.
- Keep JEPA as context-compression assistant, not hard-required on every turn.

---

## 1) Architecture tracks

### Track A: Speculative Voice Stack (main path)

Goal:
- Start speech fast with draft model output while target model validates/continues.

Conceptual flow:
1. User utterance endpoint detected.
2. Context pack assembly (viewport + pins + history + ENGRAM/CAM/ARC + optional JEPA compression).
3. Draft model starts streaming tokens immediately.
4. Target model starts in parallel and validates/overrides chunk boundaries.
5. Prosody-safe chunker emits TTS-ready text chunks.
6. TTS streams audio with interruption support.

### Track B: Plan B Filler Safety-Net (auxiliary path)

Goal:
- Avoid dead air when first meaningful chunk is delayed.

Behavior:
- If no TTS-ready content by threshold, emit short adaptive filler phrase.
- Continue with real content as soon as first validated chunk is ready.
- Fillers are language-aware and user-style-adaptive, but bounded/safe.

---

## 2) Phase plan

### Phase 157.3.1 — Speculative baseline harness (isolated)

Deliverables:
- Experimental runner for `draft+target` outside production Jarvis path.
- Telemetry schema for acceptance-rate and correction-rate.

Files:
- `scripts/voice_speculative_benchmark.py` (new)
- `docs/157_ph/benchmarks/` (new JSON/CSV outputs)
- `docs/157_ph/MARKER_157_3_SPECULATIVE_BASELINE_REPORT_2026-03-05.md` (new)

Work items:
- Implement two-stream orchestrator:
  - draft stream (fast model)
  - target stream (quality model)
- Add merge policy:
  - token acceptance window
  - correction handling before chunk commit to TTS
- Add hard timeout guards per stage.

Exit criteria:
- Harness runs all scenarios without runtime crashes.
- Metrics export complete for every run.

### Phase 157.3.2 — Prosody-safe commit policy for chunk audio

Deliverables:
- Stable chunk commit logic minimizing stretched syllables and broken words.

Files:
- `src/voice/jarvis_tts_bridge.py` (or current TTS bridge module)
- `src/voice/prosody_chunker.py` (new or extension)
- `docs/157_ph/MARKER_157_3_PROSODY_POLICY_2026-03-05.md` (new)

Work items:
- Commit only sentence-like safe boundaries.
- Add punctuation-aware buffering and minimum token span.
- Add anti-fragment rules for RU/EN.

Exit criteria:
- Audio QC metrics improve vs current chunker:
  - lower longest pause
  - fewer stretch events

### Phase 157.3.3 — Integrate speculative path into Jarvis runtime (feature-flagged)

Deliverables:
- Production integration with kill-switch.

Files:
- `src/api/handlers/jarvis_handler.py`
- `src/voice/jarvis_llm.py`
- `src/voice/jarvis_runtime_state.py` (if absent, new)
- `client/src/...` voice status indicators (no new buttons)

Feature flags:
- `VETKA_JARVIS_SPECULATIVE_ENABLE`
- `VETKA_JARVIS_FILLER_ENABLE`
- `VETKA_JARVIS_SPECULATIVE_MODELS` (draft/target pair config)

Work items:
- Preserve existing interrupt/new-turn behavior.
- Ensure single search bar voice mode only (no chat-panel regressions).
- Add visible “thinking/listening/responding” state transitions (existing UI surface).

Exit criteria:
- No regressions in non-Jarvis chat voice mode.
- Controlled enable/disable in runtime.

### Phase 157.3.4 — Plan B adaptive filler bank

Deliverables:
- Filler bank management and trigger policy.

Files:
- `data/jarvis_filler_bank.json` (existing; formalize schema)
- `src/voice/jarvis_filler_policy.py` (new)
- `docs/157_ph/MARKER_157_3_FILLER_POLICY_2026-03-05.md` (new)

Work items:
- Keep phrases short, neutral, multilingual-safe.
- Trigger only when chunk delay threshold breached.
- Post-stream learning update (async, non-blocking).

Exit criteria:
- Reduced silent gaps without degrading perceived quality.

### Phase 157.3.5 — Model-pair race and selection

Deliverables:
- Pair leaderboard for local models on your machine/runtime.

Candidate pairs (initial):
- draft `gemma3:1b` -> target `llama3.2:3b`
- draft `gemma3:1b` -> target `deepseek-r1:8b`
- draft `qwen2.5:3b` -> target `qwen2.5:7b`
- draft `phi4-mini:latest` -> target `llama3.2:3b`

Files:
- `docs/157_ph/MARKER_157_3_MODEL_PAIR_LEADERBOARD_2026-03-05.md` (new)
- `docs/157_ph/benchmarks/phase157_speculative_pair_*.json` (new)

Exit criteria:
- At least one pair beats current baseline on TTFA + quality simultaneously.

---

## 3) Test matrix

## 3.1 Functional scenarios

1. Short greeting turn (`"привет ты тут?"`)
- Expect immediate reaction and concise answer.

2. Context-grounded query (viewport + pinned docs)
- Expect answer references real project context.

3. Long prompt with high context pressure
- Expect JEPA-assisted compression path when thresholds hit.

4. Interrupt scenario
- User interrupts mid-response, system switches turn without deadlock.

5. Mixed language scenario (RU user + EN model tendency)
- Expect RU output preference in Jarvis mode.

## 3.2 Performance scenarios

1. Cold run after model load.
2. Warm run (cached model).
3. Consecutive dialogue turns (>=5 turns).
4. High churn background (`/api/tree/data`, watchers active).

## 3.3 Audio quality scenarios

1. Stretch detection.
2. Long pause detection.
3. Chunk-boundary naturalness (subjective + heuristic).

---

## 4) Metrics (must log)

Core latency:
- `ttft_text_ms`
- `ttfa_audio_ms`
- `e2e_ms`

Speculative-specific:
- `draft_first_token_ms`
- `target_first_token_ms`
- `acceptance_rate` (draft tokens accepted by target)
- `correction_rate` (target overrides)
- `chunk_commit_delay_ms`

Audio QC:
- `pause_count`
- `longest_pause_ms`
- `stretch_events`

Quality:
- `semantic_success`
- `quality_proxy`
- RU language ratio in response (Jarvis mode target)

Stability:
- timeout count
- interrupt recovery success
- fallback invocation count

---

## 5) Go / No-Go criteria

## GO (move to wider rollout)

Required (all):
1. `ttfa_audio_ms p50 <= 2500` on warm runs.
2. `interrupt recovery success >= 0.95`.
3. `success_rate >= 0.95` for E-like speculative mode in matrix.
4. Audio QC no worse than current best baseline:
- `longest_pause_ms` not increased >15%
- `stretch_events` not increased >10%
5. No regressions in chat-panel voice scenario.

## NO-GO (stop and rollback)

Any one:
1. Frequent chunk corruption or unstable speech boundaries.
2. Timeout rate > 10% in warm run scenarios.
3. Interrupt mode deadlocks or loses turn state.
4. Severe context drift (answers detached from viewport/pins/history).

---

## 6) Roadmap for model strategy

Stage 1 (now):
- Local-first validated pair with best TTFA/quality tradeoff.

Stage 2:
- Optional API target model only when explicitly selected (no hidden fallback model switching).

Stage 3:
- Phonebook model pinning for Jarvis role (explicit user-controlled persona/model choice).

---

## 7) Immediate next execution batch

1. Build `voice_speculative_benchmark.py` minimal harness.
2. Run pair race on 4 initial draft/target pairs.
3. Produce `MARKER_157_3_SPECULATIVE_BASELINE_REPORT_2026-03-05.md`.
4. Decide integration pair for feature-flag runtime.
5. Implement Plan B filler policy as strict safety-net.

---

## 8) Notes on JEPA role

JEPA remains:
- Context pack/compression accelerator under pressure.
- Not a direct text generator replacement.
- Triggered adaptively by context pressure and query type.

This roadmap keeps JEPA useful without forcing it into every turn.
