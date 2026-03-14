MARKER_163.MYCO.VETKA.HELP_IMPLEMENTATION_PLAN.V1
LAYER: L4
DOMAIN: UI|VOICE|MEMORY|TOOLS|RAG|CHAT|AGENTS
STATUS: PARTIAL
SOURCE_OF_TRUTH: docs/163_ph_myco_VETKA_help/PHASE_163_MYCO_VETKA_HELP_IMPLEMENTATION_PLAN_2026-03-07.md
LAST_VERIFIED: 2026-03-07

# PHASE_163_MYCO_VETKA_HELP_IMPLEMENTATION_PLAN_2026-03-07

Status: RECON+REPORT complete, WAIT GO
Owner: VETKA-JARVIS voice/backend path only
Scope boundary: DO NOT modify MCC UI logic/components for this phase.

---

## MARKER_163.P0.PROTOCOL.V1
Protocol for this phase:
RECON+markers -> REPORT -> WAIT GO -> IMPL NARROW -> VERIFY

---

## MARKER_163.P1.RECON.BASELINE.V1
Current baseline (from code/docs state):

1. Jarvis voice path already has unified context stack hooks in backend:
- ContextPacker integration in voice context build.
- STM + ENGRAM + CAM + viewport/pinned/open_chat context fields.
- state-key retrieval bridge via MYCO hidden retrieval service.

2. Jarvis stage-machine and TTS path exist, but UX quality is unstable:
- filler/Plan B path still present in runtime.
- voice profile consistency requires strict lock to one baseline voice.

3. MCC has MYCO helper logic and docs, but this phase must not rework MCC UI.
- We copy patterns, not code that changes MCC behavior.

4. Risk identified:
- accidental cross-edits of MCC and VETKA paths in one pass.
- regression risk if context packing policy diverges between stages/models.

---

## MARKER_163.P2.GOAL.DEFINITION.V1
Product goal for this phase:

Deliver a narrow MYCO_HELP mode in VETKA-JARVIS voice assistant focused on interface guidance:
- "What do I see right now?"
- "What can I do next with these files/nodes?"
- "How do I perform the next action in VETKA?"

Primary principle:
MYCO_HELP = proactive guide for VETKA interface usage, not generic open-domain chat.

---

## MARKER_163.P3.SCOPE.GUARDRAILS.V1
In-scope:
- backend/voice Jarvis context and response policy
- MYCO_HELP persona/profile for response shaping
- MYCO_HELP RAG corpus for VETKA UI workflows
- action-pack response format (see + do-next)
- stable voice baseline (`edge_ru_female`)
- e2e verification for interface-guidance scenarios

Out-of-scope:
- MCC visual/UI refactors (MiniChat/MiniWindow/MyceliumCommandCenter)
- new speculative decoding architecture in this phase
- broad super-agent tool orchestration (future phase)

---

## MARKER_163.P4.TARGET_ARCHITECTURE.V1
Target runtime flow (VETKA voice button path):

1. STT transcript + client runtime context
2. Unified context build:
- ContextPacker + JEPA + ELISION
- STM + ENGRAM + CAM
- viewport + pinned_files + open_chat_context
3. MYCO_HELP intent policy layer
4. MYCO_HELP RAG retrieval (VETKA-only instruction corpus)
5. Fast local model answer (Gemma) in MYCO_HELP response contract
6. Stable TTS output (`edge_ru_female`)
7. trace logging for explainability and verification

## MARKER_163.P4A.ROADMAP_CORRECTION_NOTE.V1
Roadmap correction after runtime verification:

- `MYCO` should converge toward deterministic speech delivery of selected guidance/instructions
- `MYCO` does not need free-form LLM generation as its primary value layer
- LLM remains optional/fallback-only for `MYCO`
- `vetka/` remains a separate stronger future agent path and should not be collapsed into the MYCO helper contract

Implication:
- continue separating:
  - deterministic MYCO guidance and speech
  - broader VETKA/JARVIS agent behavior

---

## MARKER_163.P5.MYCO_HELP.RESPONSE_CONTRACT.V1
For MYCO_HELP mode every answer should follow this compact structure:

1. See-now summary (1-2 short lines)
- what node/file/panel/user-focus is currently active

2. Next actions (2-4 practical actions)
- open/view/edit/pin/compare/run/context actions

3. How-to shortcut (1 concise instruction)
- specific interaction hint (click/shift/select/open context)

4. Optional clarification prompt (1 short question)
- ask user what exactly to do next

No long essays. No generic "I am Jarvis" repetition.
Assistant display identity for user: VETKA (internal codename can remain Jarvis).

---

## MARKER_163.P6.MYCO_HELP.RAG_CORPUS.V1
Create dedicated VETKA help corpus (separate from MCC docs), e.g.:

`docs/163_ph_myco_VETKA_help/rag/`

Planned docs in corpus:
1. `VETKA_HELP_CORE_ACTIONS_V1.md`
2. `VETKA_HELP_FILES_AND_ARTIFACTS_V1.md`
3. `VETKA_HELP_CHAT_PIN_VIEWPORT_V1.md`
4. `VETKA_HELP_NODE_AND_CAMERA_V1.md`
5. `VETKA_HELP_TROUBLESHOOTING_SHORT_V1.md`

Each doc format:
- intent
- when to use
- canonical steps
- anti-patterns
- short RU/EN phrase templates

---

## MARKER_163.P7.IMPLEMENTATION.PHASES.V1

### Phase 163.1 (Narrow infra hardening)
- Enforce scope boundary in code comments/markers for VETKA path.
- Ensure stage context packing is model-aware and unified in Jarvis voice path.
- Remove/disable Plan B filler emission in MYCO_HELP mode.
- Ensure identity output is VETKA-facing.

Exit criteria:
- no filler events in traces for MYCO_HELP mode
- stable context trace fields present on each turn

### Phase 163.2 (MYCO_HELP profile)
- Add explicit MYCO_HELP response policy layer in voice backend.
- Bind intent triggers for help/system/UI questions.
- Force response contract: see-now + next-actions + shortcut.

Exit criteria:
- responses consistently include actionable steps tied to visible context

### Phase 163.3 (RAG for help)
- Build VETKA help corpus and retrieval glue in Jarvis path.
- Keep retrieval compact and state-key aware (focus/path/node/panel).
- Merge retrieval snippets into model prompt with strict ordering.

Exit criteria:
- assistant references relevant VETKA actions instead of generic answers

### Phase 163.4 (Voice baseline stabilization)
- Lock `edge_ru_female` as default in MYCO_HELP mode.
- Verify no voice switching across turns.

Exit criteria:
- traces show one provider/voice profile across turns

### Phase 163.5 (E2E verify)
- run scripted checks:
  - "что я вижу"
  - "что можно сделать с этим файлом"
  - "как закрепить несколько файлов"
  - "как открыть/редактировать в artifact"
- capture traces + pass/fail report.

Exit criteria:
- >= 80% turns produce correct context-bound action-pack response
- no silent turn on follow-up for at least 6 consecutive turns

---

## MARKER_163.P8.FILE_PLAN.V1
Planned touch-points (VETKA path only):

Backend/runtime:
- `src/api/handlers/jarvis_handler.py`
- `src/voice/jarvis_llm.py`
- `src/voice/tts_engine.py` (only if needed for strict voice lock behavior)

Docs/new corpus:
- `docs/163_ph_myco_VETKA_help/PHASE_163_MYCO_VETKA_HELP_IMPLEMENTATION_PLAN_2026-03-07.md`
- `docs/163_ph_myco_VETKA_help/rag/*.md` (new)
- `docs/163_ph_myco_VETKA_help/PHASE_163_VERIFY_REPORT_YYYY-MM-DD.md` (new)

Explicitly no changes in this phase to:
- `client/src/components/mcc/*`
- MCC quick routes/UI behavior

---

## MARKER_163.P9.TEST_MATRIX.V1

Functional:
1. Detect visible focus correctly (node/file/path/panel)
2. Action-pack relevance to current focus
3. Follow-up continuity over 6+ turns
4. No language drift when user speaks RU
5. No filler voice emissions

Trace/metrics:
1. `context_keys` include runtime focus fields
2. `context_chars` stable (no runaway growth)
3. `first_response_ms` and `total_turn_ms` reported
4. stable `tts_provider` + voice profile

Regression:
1. Chat panel voice mode behavior unchanged
2. MCC mini chat behavior unchanged

---

## MARKER_163.P10.GO_NO_GO.V1
GO if:
- scope boundary is enforced (VETKA-only changes)
- response contract implemented and validated
- edge_ru_female stable in traces
- follow-up turns do not die after 3-4 messages

NO-GO if:
- MCC behavior regresses
- context binding remains generic/non-actionable
- silent turns persist on follow-ups

---

## MARKER_163.P11.NEXT_STEP_REQUEST.V1
REPORT delivered.
WAIT GO for `IMPL NARROW` start at **Phase 163.1**.
