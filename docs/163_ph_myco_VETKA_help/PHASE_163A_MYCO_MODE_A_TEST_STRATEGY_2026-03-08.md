MARKER_163A.MYCO.MODE_A.TEST_STRATEGY.V1
LAYER: L4
DOMAIN: UI|TOOLS|CHAT
STATUS: PLANNED
SOURCE_OF_TRUTH: docs/163_ph_myco_VETKA_help/PHASE_163A_MYCO_MODE_A_TEST_STRATEGY_2026-03-08.md
LAST_VERIFIED: 2026-03-08

# PHASE_163A_MYCO_MODE_A_TEST_STRATEGY_2026-03-08

## Synopsis
Self-test strategy for deterministic hints in VETKA main surface. Focus: correctness, state freshness, dedupe, silence during typing, and explicit fallback behavior on disabled/future surfaces.

## Table of Contents
1. Test layers
2. Core assertions
3. Browser automation path
4. Proposed scenarios
5. Cross-links
6. Status matrix

## Treatment
Mode A should be tested as a UI contract, not as prompt quality. The main unit under test is the state-to-hint pipeline.

## Short Narrative
Good tests for Mode A should prove that the hint is tied to the visible surface and changes only when the surface meaning changes. They should also prove the negative cases: no duplicate hint, no stale hint, no noise while typing.

## Full Spec
### Test layers
#### Layer 1: Pure rule tests
- Test input:
  - canonical focus snapshot
- Test output:
  - hint payload
- Target:
  - `mycoModeARules.ts`

#### Layer 2: Hook/reducer tests
- Test input:
  - event stream + store state changes
- Test output:
  - derived state key, dedupe behavior, mute behavior
- Target:
  - `useMycoModeA.ts`

#### Layer 3: UI contract tests
- Test input:
  - rendered `App` or isolated `MycoGuideLane`
- Test output:
  - hint visibility, content family, dismiss behavior

#### Layer 4: Browser flow tests
- Test input:
  - real click/keyboard/navigation flow in Chromium
- Test output:
  - hint appears, updates, clears, does not duplicate

#### Layer 5: Desktop Tauri flow tests
- Test input:
  - real desktop-window flow in Tauri runtime
- Test output:
  - same hint contract passes in desktop shell, not only in browser shell

### Core assertions
1. Hint appears on initial idle tree state.
2. Same state key does not re-emit same hint.
3. New selection changes hint within one render cycle.
4. Typing in search suppresses proactive emission.
5. Opening chat replaces tree hint with chat hint.
6. Opening external artifact shows ingest-oriented hint.
7. Switching to disabled `cloud/` or `social/` shows one fallback hint only.
8. Closing surface removes stale hint or reverts to prior surface-derived hint.

### Browser automation path
- Preferred first path: Playwright in browser mode for the MVP.
- Reason:
  - user explicitly asked for a self-test path in Chromium
  - project already uses Vite frontend scripts in `client/package.json:7`
  - fastest path to prove deterministic state-to-hint contract before desktop-shell hardening
- Practical path after implementation:
  1. run frontend in browser mode with `npm run dev` inside `client/`
  2. use Playwright to drive:
     - tree click
     - chat open
     - model directory open
     - search context switch
     - artifact open
  3. assert DOM text or `data-testid` values on `MycoGuideLane`

### Desktop automation path
- Recommended second path: WebDriver-compatible Tauri runner behind the same agent-facing DSL.
- Goal:
  - keep browser and desktop tests on one semantic contract
  - avoid teaching the agent two different testing languages
- Practical path after implementation:
  1. expose a thin driver layer with operations such as `click`, `fill`, `press`, `expectVisible`, `expectText`
  2. bind that layer to Playwright for web runtime
  3. bind the same layer to Tauri desktop automation for desktop runtime
  4. keep scenario specs identical across both runtimes

### Agent-facing DSL
- The agent should not work directly with raw selectors everywhere.
- Recommended wrapper contract:
  - `openSurface(surfaceId)`
  - `click(targetId)`
  - `fill(targetId, text)`
  - `press(key)`
  - `expectHintContains(text)`
  - `expectHintSilent()`
  - `expectStateKeyChanged()`
  - `expectNoDuplicateHint()`
- This keeps Codex/Claude Code focused on scenario authoring, not runner plumbing.

### Proposed browser scenarios
1. Initial load with empty search:
  - expect tree-idle hint
2. Click a file node:
  - expect selection-oriented next actions
3. Open chat:
  - expect chat hint
4. Open model directory:
  - expect phonebook hint
5. Switch search to `web/`:
  - expect web-source hint
6. Switch search to `cloud/`:
  - expect disabled-mode fallback hint
7. Open external artifact:
  - expect ingest hint
8. Type into search:
  - expect no new proactive hint while typing

### Suggested marker/test IDs
- `MARKER_163A.MODE_A.HINT_LANE.MOUNT.V1`
- `MARKER_163A.MODE_A.STATE_KEY.DEDUPE.V1`
- `MARKER_163A.MODE_A.SILENCE.ON_TYPING.V1`
- `MARKER_163A.MODE_A.EXTERNAL_ARTIFACT.INGEST_HINT.V1`
- `MARKER_163A.MODE_A.SEARCH.DISABLED_CONTEXT_REDIRECT.V1`
- `MARKER_163A.MODE_A.AGENT_DSL.CROSS_RUNTIME.V1`

## Cross-links
See also:
- [PHASE_163A_MYCO_MODE_A_SCENARIO_MATRIX_2026-03-08](./PHASE_163A_MYCO_MODE_A_SCENARIO_MATRIX_2026-03-08.md)
- [PHASE_163A_MYCO_MODE_A_NARROW_MVP_CUT_2026-03-08](./PHASE_163A_MYCO_MODE_A_NARROW_MVP_CUT_2026-03-08.md)
- [PHASE_163A_MYCO_MODE_A_IMPLEMENTATION_PLAN_2026-03-08](./PHASE_163A_MYCO_MODE_A_IMPLEMENTATION_PLAN_2026-03-08.md)

## Status matrix
| Test layer | Status | Notes |
|---|---|---|
| Rule tests | Planned | highest leverage, low runtime cost |
| Hook/reducer tests | Planned | validates dedupe/mute semantics |
| UI contract tests | Planned | validates render and visibility |
| Browser automation | Proposed | preferred first e2e layer via Playwright |
| Desktop automation | Proposed | second e2e layer via WebDriver-compatible Tauri path |
