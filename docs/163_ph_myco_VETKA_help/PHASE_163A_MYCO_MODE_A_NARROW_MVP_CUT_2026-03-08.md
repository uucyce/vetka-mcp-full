MARKER_163A.MYCO.MODE_A.NARROW_MVP.V1
LAYER: L3
DOMAIN: UI|CHAT|TOOLS
STATUS: PLANNED
SOURCE_OF_TRUTH: docs/163_ph_myco_VETKA_help/PHASE_163A_MYCO_MODE_A_NARROW_MVP_CUT_2026-03-08.md
LAST_VERIFIED: 2026-03-08

# PHASE_163A_MYCO_MODE_A_NARROW_MVP_CUT_2026-03-08

## Synopsis
Narrow MVP cut for Mode A. The goal is to ship a reliable deterministic guide lane for the main VETKA workspace before any richer helper behavior.

## Table of Contents
1. MVP scope
2. Explicit exclusions
3. Success criteria
4. Cross-links
5. Status matrix

## Treatment
The MVP is intentionally smaller than "all surfaces". It covers only the surfaces and events needed to prove the contract in runtime without introducing noise.

## Short Narrative
The right MVP is not "teach everything". It is "always know where the user is, show one good next step, and never get stale". That requires a small surface set, a strict dedupe model, and a visible lane in `App.tsx`.

## Full Spec
### In scope
1. Main tree idle state.
2. Selected node state.
3. Chat open state.
4. Model directory open state.
5. Unified search idle state.
6. Unified search `vetka/web/file` context transitions.
7. Artifact open state for VETKA file.
8. Artifact open state for external file.
9. Hotkey hinting for `G`, `Esc`, `Ctrl/Cmd+S`, `Ctrl/Cmd+Z`, `Cmd/Ctrl+Shift+D`.
10. One render lane in VETKA main surface when input/search is empty.

### Explicit exclusions
1. No LLM call in default hint loop.
2. No voice-triggered proactive speech in Mode A MVP.
3. No long-tail overlays in first cut.
4. No cloud/social execution.
5. No group-chat-specific MYCO behaviors.
6. No full 336-control hint emission at runtime.

### Proposed file touch points after GO
- `client/src/App.tsx`
- `client/src/store/useStore.ts`
- `client/src/components/myco/MycoGuideLane.tsx` new
- `client/src/components/myco/mycoModeARules.ts` new
- `client/src/components/myco/mycoModeATypes.ts` new
- `client/src/components/myco/useMycoModeA.ts` new
- `tests/phase163a/test_phase163a_mode_a_contract.py` new
- `tests/phase163a/test_phase163a_mode_a_ui_contract.py` new

### Success criteria
- Hint appears on initial tree idle state.
- Hint changes on node selection, search context switch, chat open, artifact open.
- Hint disappears or freezes while user types.
- Hint does not duplicate for same state key.
- Hint for external artifact offers ingest action and clears after ingest/open-state change.

## Cross-links
See also:
- [PHASE_163A_MYCO_MODE_A_ARCHITECTURE_PROPOSAL_2026-03-08](./PHASE_163A_MYCO_MODE_A_ARCHITECTURE_PROPOSAL_2026-03-08.md)
- [PHASE_163A_MYCO_MODE_A_SCENARIO_MATRIX_2026-03-08](./PHASE_163A_MYCO_MODE_A_SCENARIO_MATRIX_2026-03-08.md)
- [PHASE_163A_MYCO_MODE_A_IMPLEMENTATION_PLAN_2026-03-08](./PHASE_163A_MYCO_MODE_A_IMPLEMENTATION_PLAN_2026-03-08.md)

## Status matrix
| Area | Status | Notes |
|---|---|---|
| MVP surface list | Planned | narrow enough for first runtime bind |
| LLM-free loop | Planned | hard requirement for MVP |
| Testable contract | Planned | bounded by explicit state keys and transitions |
