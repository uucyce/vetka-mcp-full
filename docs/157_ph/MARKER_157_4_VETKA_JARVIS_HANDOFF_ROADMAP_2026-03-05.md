# MARKER_157_4_VETKA_JARVIS_HANDOFF_ROADMAP_2026-03-05

Date: 2026-03-05  
Phase: 157.4 (planning)  
Status: Proposed and aligned with current benchmark evidence.

## 1) Product naming and identity (approved)

Final naming split:
- UI/Chat identity: `VETKA`
- Mention alias in chat: `@VETKA`
- Runtime codename in code: `JARVIS`
- Infra/orchestration layer: `MYCELIUM`
- Helper/context layer codename (optional internal): `MYCO`

Rationale:
- User perceives one assistant brand (`VETKA`).
- Engineering keeps technical continuity (`Jarvis runtime`).
- No user confusion between internal services and UI persona.

---

## 2) Voice response architecture (handoff-first, not pure speculative)

Target behavior:
- No dead-air at turn start.
- Fast emotional reaction first, then meaningful response expansion.
- Single TTS voice, no visible model-switch complexity for user.

## Runtime response stages

Stage 0 (Plan B safety starter):
- Trigger when no spoken content is ready by threshold.
- Emit ultra-short adaptive filler phrase (language-aware, style-safe).
- Must be cancellable immediately when real content arrives.

Stage 1 (fast semantic chunk):
- Model: `gemma3:1b` (current speed leader for fast start).
- Goal: first useful chunk quickly, not full answer.
- Context profile: lightweight, low-latency context assembly.

Stage 2 (quality continuation chunk):
- Model: selected “smart continuation” model from local leaderboard.
- Initial preferred candidates (ordered by quality/speed balance):
  1. `deepseek-r1:8b` (quality-first)
  2. `llama3.2:3b` (latency/balance)
  3. `phi4-mini:latest` (backup)
- Goal: continue/complete answer with stronger coherence.

Stage 3 (deep escalation, optional):
- Trigger for research/deep read/workflow intent.
- Model source: API from Favorites (explicitly selected provider/model, no hidden fallback switching).
- Goal: high-depth analysis beyond local stage limits.

Important:
- This is handoff pipeline, not strict speculative token verification.
- We optimize perceived responsiveness and dialogue continuity.

---

## 3) Context policy per stage

Stage 0 filler:
- No heavy context; pure UX safety response.

Stage 1 fast chunk (`gemma3:1b`):
- Include only cheap context:
  - current viewport summary,
  - active pin list summary,
  - short tail of active chat history.
- JEPA usage:
  - default OFF for Stage 1,
  - ON only if context pressure threshold is crossed and measured overhead is acceptable.

Stage 2 quality chunk:
- Full context profile (same as text chat message path):
  - viewport + pins + history + ENGRAM/CAM/ARC.
- JEPA usage:
  - ON by adaptive trigger under token/context pressure.

Stage 3 API deep mode:
- Full context + optional tool path + explicit long-form behavior.

---

## 4) Phase 157.4 implementation roadmap

### 157.4.1 Handoff runtime skeleton

Files:
- `src/voice/jarvis_llm.py`
- `src/api/handlers/jarvis_handler.py`
- `src/voice/jarvis_runtime_state.py` (new if needed)

Tasks:
- Implement stage orchestrator (0->1->2->3).
- Add strict cancellation and interrupt handoff.
- Keep single TTS stream identity.

### 157.4.2 Plan B adaptive filler bank

Files:
- `src/voice/jarvis_filler_policy.py` (new)
- `data/jarvis_filler_bank.json` (existing, schema formalization)

Tasks:
- Add multilingual neutral templates.
- Add post-response async bank learning updates.
- Add anti-repetition window.

### 157.4.3 Stage context profiles + JEPA gating

Files:
- `src/orchestration/context_packer.py`
- `src/api/handlers/message_utils.py`
- `src/voice/jepa_trigger_policy.py` (new optional)

Tasks:
- Lightweight context mode for Stage 1.
- Full context mode for Stage 2/3.
- JEPA trigger contract by stage (latency guardrail).

### 157.4.4 Smart continuation model selection

Files:
- `src/voice/jarvis_model_selector.py` (new)
- `docs/157_ph/MARKER_157_4_MODEL_ROLE_MATRIX_2026-03-05.md` (new)

Tasks:
- Define role mapping:
  - `fast_start_model`
  - `quality_model`
  - `deep_api_model`
- Keep user-visible identity as `VETKA`.

### 157.4.5 Mention and assistant surface unification

Files:
- `src/api/handlers/mention/mention_handler.py`
- `src/api/routes/chat_routes.py`

Tasks:
- Restore/upgrade `@VETKA` mention behavior from historical Hostess capability set.
- Keep explicit skill/tool trace transparency in chat.

---

## 5) Metrics and acceptance (handoff-specific)

Primary KPIs:
- `time_to_first_audible_response_ms` (including filler if used)
- `time_to_first_semantic_chunk_ms` (Stage 1)
- `time_to_quality_continuation_ms` (Stage 2)
- interrupt recovery success rate
- perceived coherence score across stage transitions

Go criteria for rollout:
1. First audible response <= 1200ms p50.
2. First semantic chunk <= 2500ms p50.
3. Interrupt recovery >= 95%.
4. No chat-panel voice regressions.
5. Stage transition artifacts (stretched syllables/pause spikes) within existing QC bounds.

No-Go criteria:
- Repeated silent gaps > 3s in warm run.
- Frequent language mismatch at Stage 1/2 transition.
- Loss of context grounding versus text chat path.

---

## 6) Future phase backlog (VETKA superagent track)

Planned future capabilities:
- `@VETKA` can run tools/skills and launch workflows in MYCELIUM.
- Camera control by intent (focus/move/zoom presets).
- Graph/tree operations by natural language commands.
- Contextual file finding + open + explain flow.
- Group-chat orchestration with transparent tool/event logs.

Backlog items to carry forward:
1. Reintroduce advanced Hostess-era control functions via modern mention pipeline.
2. Build explicit `tool-loop + interrupt/new-turn` semantics for voice and text parity.
3. Add “phonebook” model role configuration UI:
- fast start model,
- quality continuation model,
- deep API model.

---

## 7) Immediate next execution batch

1. Implement 157.4.1 skeleton (handoff stage machine, no UI additions).
2. Implement 157.4.2 filler policy with strict latency threshold.
3. Wire 157.4.3 stage-aware context profiles and JEPA gating.
4. Run controlled A/B:
- with filler ON/OFF,
- with Stage2 candidate models.
5. Freeze first production candidate pair and open validation cycle.

