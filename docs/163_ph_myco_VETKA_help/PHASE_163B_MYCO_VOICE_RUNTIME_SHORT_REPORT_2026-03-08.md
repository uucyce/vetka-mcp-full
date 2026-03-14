MARKER_163B.MYCO.VOICE.RUNTIME.SHORT_REPORT.V1
LAYER: L4
DOMAIN: VOICE|LLM|TTS|RAG|MEMORY|PERSONA
STATUS: REPORT
SOURCE_OF_TRUTH: docs/163_ph_myco_VETKA_help/PHASE_163B_MYCO_VOICE_RUNTIME_SHORT_REPORT_2026-03-08.md
LAST_VERIFIED: 2026-03-08

# PHASE_163B_MYCO_VOICE_RUNTIME_SHORT_REPORT_2026-03-08

Status: REPORT delivered, WAIT GO
Owner: VETKA-JARVIS voice/runtime path
Dependency: Phase 163.A deterministic MYCO track is running in parallel

## MARKER_163B.P0.PROTOCOL.V1
Protocol for this subphase:
RECON+markers -> REPORT -> WAIT GO -> IMPL NARROW -> VERIFY TEST

## MARKER_163B.P1.BASELINE.V1
Current reality after Phase 163.3:

1. Voice-path MYCO_HELP retrieval is connected.
- `hidden_retrieval_hits` is no longer always zero.
- Phase-163 help corpus is reachable from voice path.

2. Response quality is still weak.
- Answers remain generic or only superficially intelligent.
- Retrieval presence does not yet guarantee fact-grounded reply.

3. Context stack exists, but not all layers are active in practice.
- trace shows ContextPacker fields present.
- `jepa_mode=false` and `docs_count=0` in observed turns.
- JEPA is not removed, but currently not visibly contributing in these MYCO_HELP traces.

4. TTS and persona path need separation from the old adult-assistant baseline.
- `edge_ru_female` is stable but mismatched with MYCO character direction.
- `espeak` exists and already supports fast local robotic presets.

## MARKER_163B.P2.GOAL.V1
Goal of 163.B:

Stabilize the MYCO voice/runtime layer as a narrow, character-driven, fact-bound helper path for VETKA.

This is not the deterministic proactive guide layer itself.
That work belongs to Phase 163.A and proceeds separately.

163.B is the spoken/runtime companion layer that should:
- sound like MYCO, not like a generic assistant;
- answer from visible/runtime facts;
- stay fast;
- avoid generic abstraction;
- preserve compatibility with broader VETKA memory/context architecture.

## MARKER_163B.P3.NON_GOALS.V1
Not in scope for 163.B:

- redesigning JEPA or changing its core behavior
- removing chunk3 forever by policy
- full plugin-host audio FX integration in PULSE
- MBROLA revival/rewrite
- deterministic proactive surface logic (owned by 163.A)

## MARKER_163B.P4.JEPA.POSITION.V1
JEPA position for this phase:

- verify presence
- verify it is still wired into the shared context architecture
- verify that MYCO/JARVIS path does not accidentally bypass it when overload conditions should activate

Do not redesign JEPA in this phase.
Do not force JEPA activation artificially.

## MARKER_163B.P5.PERSONA_AND_VOICE.V1
New voice/persona direction:

1. MYCO should move toward a compact character guide.
2. Character fit is more important than naturalism.
3. Speed + clarity of intent are more important than “human quality”.

Current preferred technical candidate:
- `espeak-ng` with `chip`-style preset tuning

Reference only, not automatic fallback:
- `edge_ru_female`

Important:
- `edge` remains available as future selectable voice/reference option.
- It should not auto-take over when MYCO character voice is the chosen baseline.

## MARKER_163B.P6.PULSE_AND_PLUGIN_RECON.V1
PULSE/plugin conclusion for this phase:

1. `Transformant` can be installed into standard plugin folders and scanned by PULSE-facing inventory.
2. Current PULSE stack appears to support plugin discovery/rack state and external MIDI orchestration.
3. Current PULSE stack is not yet a proven TTS audio FX host for MYCO runtime.

Conclusion:
- plugin placement is acceptable as preparation
- plugin-host audio processing is not a narrow 163.B execution path

## MARKER_163B.P7.RUNTIME_CONTRACT.V1
Narrow runtime contract for MYCO spoken mode:

1. Use facts first:
- `viewport_context`
- `open_chat_context`
- `pinned_files`
- retrieval snippets
- role/model-aware shared context stack

2. Avoid abstract helper prose.

3. Preserve option to evaluate:
- `chunk2_fast` only
- `chunk2_fast + chunk3_smart`

Status of chunk3:
- under evaluation
- not globally banned
- should be judged by measured latency and reply integrity, not assumption

## MARKER_163B.P8.DEPENDENCY_ON_163A.V1
Parallel dependency:

Phase 163.A is building the deterministic MYCO guide layer:
- event sources
- state selectors
- rule engine
- hint payload
- render slot
- test strategy

163.B must align with that work.
Rule:
- 163.A owns deterministic proactive guidance
- 163.B owns spoken/runtime MYCO companion behavior

New UI alignment constraint:
- deterministic hints should ultimately be rendered in the unified search lane, not remain a separate floating helper forever
- spoken/runtime behavior in 163.B must follow this surface decision instead of creating a second MYCO UI

## MARKER_163B.P9.NARROW_NEXT_STEPS.V1
Planned narrow next steps after GO:

1. Persona/asset alignment
- reuse ready MYCO assets already prepared for MCC where possible
- avoid reprocessing raw source icons if production-ready assets exist
- make MCC-derived MYCO reaction assets/animations an explicit migration item, not just an implied reuse note

2. Voice baseline experiment
- evaluate `espeak chip` as MYCO character voice baseline
- compare against current `c3po/clean` only on speed, intelligibility, and character fit
- keep `chip` baseline active for now, but add a later voice-polish pass to slow playback/rate slightly if live turns still sound clipped or under-articulated

3. Runtime answer contract tightening
- facts-only MYCO_HELP answer shaping
- clarify on weak STT
- preserve JEPA as shared architecture component, verify-only

4. Chunk policy verification
- measure whether chunk3 helps or harms MYCO_HELP spoken turns

5. Spoken handoff from deterministic lane
- when unified search is empty, MYCO may stay silent by default and expose deterministic hint text
- click on MYCO avatar can replay/read the current deterministic hint
- deterministic speech replay must not depend on microphone/STT/LLM; it should use direct TTS routing
- role split for deterministic replay:
  - `myco/` -> `espeak chip`
  - `vetka/` -> `edge female`
- once user enters explicit voice mode, MYCO shifts into spoken companion mode with the selected character voice
- after deterministic hint playback ends, lane should show an idle placeholder instead of leaving MYCO in active-speaking posture
- default MYCO idle wording target:
  - `tap MYCO to talk or tap text to search`
- explicit VETKA/JARVIS_VETKA idle wording target:
  - `tap VETKA to talk or tap text to search`
- this wording split is product-significant because MYCO and JARVIS_VETKA are different roles, not just different voices

6. Serious-answer visual state
- if LLM path is engaged for a more complex answer, MYCO should switch to a thinking/speaking animation state
- prefer already prepared MCC MYCO assets/animations over raw source packs

7. Explicit animation migration slice
- copy and wire the prepared MCC MYCO runtime reaction states into VETKA as a dedicated step
- include at minimum:
  - idle/question
  - active/speaking
  - thinking/waiting for LLM
  - replay/read-current-hint affordance state
- `thinking` source may come from `icons/myco_logos/think/myco_think_kling3.mp4`, but this is not a drop-in runtime asset:
  - needs a narrow preparation slice
  - extract frames or convert to a web/runtime-safe animated format
  - preserve transparency/alpha if possible
  - keep this as an explicit asset-pipeline task, not an inline UI hack
- reference tool/prep note:
  - `/Users/danilagulin/Documents/CinemaFactory/docs/08_MEDIA_PIPELINE/MP4_TO_APNG_ALPHA_TOOL.md`

8. Agent-role split in lane UX
- MYCO remains the default fast helper persona in the unified lane
- explicit `vetka/` selection should route to the more serious `JARVIS_VETKA` path
- future routing may use phonebook-based model assignment and external API models
- this separation should be represented visually:
  - MYCO avatar/logo for helper mode
  - VETKA branch logo for JARVIS_VETKA mode

## MARKER_163B.P9A.IDLE_PLACEHOLDER_ROLE_SPLIT.V1
Idle placeholder contract for spoken/runtime lane:
- MYCO default helper placeholder:
  - `tap MYCO to talk or tap text to search`
- explicit VETKA/JARVIS_VETKA placeholder:
  - `tap VETKA to talk or tap text to search`

Reason:
- the product must show that MYCO and JARVIS_VETKA are distinct roles, not just different voices

## MARKER_163B.P9D.UNIFIED_LANE_SEVERITY_ALIGNMENT.V1
Spoken/runtime MYCO must align with the unified-lane severity model instead of inventing a second MYCO surface.

Alignment rule:
- `normal`
  - regular hint/help playback
- `warning`
  - spoken/runtime guidance may become more explicit, but stays inside the same lane contract
- `blocking`
  - spoken/runtime path may temporarily prioritize error remediation, but still uses the canonical unified lane surface

## MARKER_163B.P9F.MODE_PREFIX_CLICK_ROUTING_BUG.V1
Voice/runtime guardrail:
- clicking lane mode prefixes (`myco/`, `vetka/`, `web/`, `file/`) must not trigger microphone or spoken path
- spoken entry must remain bound to explicit voice affordances

## MARKER_163B.P9G.WEB_RUNTIME_HEALTH_GAP.V1
Runtime voice/path planning must treat `web/` as degraded until real runtime confirms it is healthy.
Voice and helper layers must not assume `web/` is production-ready only because the selector and lane mode exist.

## MARKER_163B.P9H.TADA_RND_CANDIDATE.V1
TADA is tracked as the primary experimental voice/runtime R&D candidate for future local spoken path work.
Status:
- promising
- open source
- not a drop-in replacement for the current MYCO/JARVIS voice path
Constraint:
- keep TADA in a separate R&D branch/task until current runtime contract is stable

## MARKER_163B.P9I.LITERT_RUNTIME_ACCEL_CANDIDATE.V1
LiteRT is tracked as a future local inference/runtime acceleration candidate, especially for Apple Silicon local agent execution.
Status:
- infra/runtime candidate
- not a current-slice fix

## MARKER_163B.P9J.BARL_RESEARCH_NOTE.V1
BARL is tracked only as a long-horizon research note for future reasoning/self-reflection work.
Status:
- do not mix into current MYCO/JARVIS runtime stabilization
- delegate to MCC/local-models research direction instead of the active voice path

## MARKER_163B.P9E.FIRST_AID_ALIGNMENT_171A.V1
163.B must align with the Phase 171A MYCO first-aid package.
Direction split:
- TADA belongs to the active VETKA voice/runtime research direction
- BARL and LiteRT belong to the MCC/local-models research direction


Alignment rule:
- spoken/runtime MYCO should eventually consume the same normalized first-aid taxonomy used by lane/UI remediation
- severity language should stay compatible with:
  - `normal`
  - `warning`
  - `blocking`
- runtime spoken behavior should distinguish:
  - user-fixable advice
  - operator-side issues
  - explicit escalation paths such as `@doctor`

Not in scope for this slice:
- implementing the full first-aid runtime envelope
- replacing existing search/socket/connector errors with the Phase 171A schema immediately

In scope for planning:
- keep 163.B compatible with the future normalized search/runtime error contract so voice MYCO does not diverge from lane MYCO when first-aid states are wired in

Non-goal:
- do not move spoken MYCO into a separate right-side helper placement just for error cases
- if a future right-side rail exists, it belongs to diagnostics/status, not to canonical MYCO conversation flow

## MARKER_163B.P9K.MYCO_DETERMINISTIC_SPEECH_PATH.V1
Roadmap correction:
- MYCO spoken behavior should move toward a deterministic instruction-to-speech path
- primary flow:
  - state/context selection
  - deterministic scenario or first-aid lookup
  - direct TTS playback
- MYCO should not depend on free-form LLM generation for its core guidance value

Planning consequence:
- MYCO LLM usage becomes optional
- if used at all, it should be fallback/enrichment only
- deterministic hints, first-aid advice, and scenario guidance should prefer direct speech rendering over open generation

## MARKER_163B.P9L.LLM_OPTIONAL_FALLBACK_ONLY.V1
Correction note for runtime planning:
- MYCO is not the place to force a weak local LLM to improvise interface guidance
- if local model help is retained, it should be:
  - optional
  - bounded
  - fallback-only
- deterministic retrieval/selection remains primary for MYCO

Non-goal:
- do not spend the current stabilization phase trying to make MYCO sound intelligent through freer prompting alone

## MARKER_163B.P9M.VETKA_AGENT_PATH_REMAINS_SEPARATE.V1
`vetka/` remains the separate stronger agent path.

Role rule:
- `myco/`
  - fast local helper
  - deterministic speech preferred
  - lightweight guidance and first aid
- `vetka/`
  - explicit stronger agent contour
  - future phonebook/API routing belongs here
  - may keep broader agentic behavior separate from MYCO

Planning rule:
- do not collapse MYCO and VETKA into one voice/runtime behavior contract
- do not let MYCO roadmap work erase the separate `vetka/` agent direction

## MARKER_163B.P9B.JARVIS_VETKA_EXPLICIT_PATH.V1
`vetka/` selection is the explicit path to the stronger future agent contour:
- JARVIS_VETKA may later route via phonebook/model assignment
- future external API models belong to this contour
- MYCO remains the fast local helper by default

## MARKER_163B.P9C.THINKING_ASSET_PIPELINE_REF.V1
Thinking animation pipeline reference:
- source candidate:
  - `icons/myco_logos/think/myco_think_kling3.mp4`
- preparation reference:
  - `/Users/danilagulin/Documents/CinemaFactory/docs/08_MEDIA_PIPELINE/MP4_TO_APNG_ALPHA_TOOL.md`
- when the thinking visual is finally integrated, increase its apparent display size slightly (about 10%) and keep the same small uplift for related lane icons so the state reads clearly in the available search-lane space

## MARKER_163B.P10.SUCCESS_CRITERIA.V1
163.B is successful if:

- MYCO spoken output feels like one consistent character
- runtime answers become visibly more fact-bound
- no accidental auto-fallback to unrelated voice baseline
- JEPA remains present in architecture and verified, without redesign
- this layer does not conflict with Phase 163.A deterministic guide work
- spoken MYCO does not introduce a second competing HUD if the unified search lane becomes the canonical MYCO surface

## MARKER_163B.P11.CROSS_LINKS.V1
See also:
- `docs/163_ph_myco_VETKA_help/PHASE_163_MYCO_VETKA_HELP_IMPLEMENTATION_PLAN_2026-03-07.md`
- `docs/163_ph_myco_VETKA_help/PHASE_163_3_IMPL_REPORT_2026-03-07.md`
- `docs/163_ph_myco_VETKA_help/MYCO_VETKA_CONTEXT_MEMORY_STACK_V1.md`
- `docs/163_ph_myco_VETKA_help/MYCO_VETKA_GAP_AND_REMINDERS_V1.md`
- `docs/163_ph_myco_VETKA_help/MYCO_VETKA_MASTER_INDEX_V1.md`
