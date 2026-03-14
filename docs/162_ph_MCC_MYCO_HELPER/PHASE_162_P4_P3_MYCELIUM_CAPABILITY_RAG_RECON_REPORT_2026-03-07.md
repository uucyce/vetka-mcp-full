# PHASE 162 — P4.P3 MYCELIUM Capability + RAG/Proactive Recon (2026-03-07)

Status: `RECON COMPLETE`
Protocol: `RECON -> REPORT -> WAIT GO -> IMPL NARROW -> VERIFY`

## Questions answered
1. Is `MYCO_AGENT_INSTRUCTIONS_GUIDE_V1_2026-03-06.md` exhaustive?
- No. It is strong on TRM and phase-161 diagnostics, but not exhaustive for current MYCELIUM runtime UX states (drill lifecycle, workflow-open actions, task/node unfold branches).

2. Is MYCO RAG ready?
- Base ready: hidden index + retrieval bridge + glossary alias expansion + quality gate exist.
- Gap: retrieval query was mostly message-based and not strongly state-keyed by UI drill state.

3. Are proactive MYCO messages reactive enough?
- Improved but incomplete before this step:
  - P4.P2 fixed top-hint stale drill prompt.
  - Chat quick path still needed stronger state-key coupling and action-pack consistency.

## What MYCELIUM can do (runtime capability map)
1. Multi-project tabs and first-run bootstrap.
2. Roadmap DAG select/focus/drill.
3. Task overlay and workflow drill into runtime pipeline.
4. Node-aware Context (models/prompts/status/stream/artifacts).
5. Stats/Balance diagnostics.
6. Hidden MYCO memory retrieval + ENGRAM + orchestration snapshot.

## Gap matrix (before P4.P3 impl)
1. Instructions gap:
- no explicit capability matrix for MYCO grounding.
2. Proactive guidance gap:
- no single state matrix contract bridging top-hint/chat/retrieval key.
3. Retrieval gap:
- query not enriched by drill-state key terms.
4. Payload gap:
- quick chat context did not always carry drill-state fields to backend.

## P4.P3 markers
1. `MARKER_162.P4.P3.MYCO.MYCELIUM_CAPABILITY_MATRIX.V1`
2. `MARKER_162.P4.P3.MYCO.PROACTIVE_MESSAGE_STATE_MATRIX.V1`
3. `MARKER_162.P4.P3.MYCO.RAG_STATE_KEY_ENRICHMENT.V1`
4. `MARKER_162.P4.P3.MYCO.CHAT_CONTEXT_DRILL_FIELDS.V1`

## Narrow implementation target
1. Add capability/state-key sections to MYCO instructions guide.
2. Pass drill-state fields from MiniChat to `/chat/quick` context.
3. Enrich retrieval query with state key terms (`nav_level`, drill states, `node_kind`).
4. Align quick reply output to include state-aware next-action pack.

## Verify plan
1. Add tests for:
- marker presence in guide/routes/chat,
- drill-state context fields in MiniChat request payload,
- state-key retrieval enrichment path.

GO token used: `GO 162-P4.P3`
