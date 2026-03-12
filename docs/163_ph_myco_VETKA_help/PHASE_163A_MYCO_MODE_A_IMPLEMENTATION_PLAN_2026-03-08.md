MARKER_163A.MYCO.MODE_A.IMPLEMENTATION_PLAN.V1
LAYER: L4
DOMAIN: UI|CHAT|TOOLS
STATUS: PLANNED
SOURCE_OF_TRUTH: docs/163_ph_myco_VETKA_help/PHASE_163A_MYCO_MODE_A_IMPLEMENTATION_PLAN_2026-03-08.md
LAST_VERIFIED: 2026-03-08

# PHASE_163A_MYCO_MODE_A_IMPLEMENTATION_PLAN_2026-03-08

## Synopsis
Marker-based plan for implementing `MYCO Mode A` in narrow phases. This plan respects the protocol: `RECON+markers -> REPORT -> WAIT GO -> IMPL NARROW -> VERIFY TEST`.

## Table of Contents
1. Protocol
2. Phase plan
3. File plan
4. Go/no-go
5. Cross-links
6. Status matrix

## Treatment
The plan assumes no code changes until explicit GO. The implementation is constrained to VETKA main surface.

## Short Narrative
The correct first implementation is not a full assistant subsystem. It is a thin deterministic layer mounted in `App.tsx`, driven by existing state and events, with tests that prove state freshness and non-noisy behavior.

## Full Spec
## MARKER_163A.P0.PROTOCOL.V1
Current phase output:
- RECON complete
- REPORT complete
- WAIT GO

## MARKER_163A.P1.PHASES.V1
### Phase 163.A.1
Goal:
- add canonical focus snapshot builder

Planned touch points:
- `client/src/components/myco/mycoModeATypes.ts`
- `client/src/components/myco/mycoModeARules.ts`
- `client/src/components/myco/useMycoModeA.ts`

Exit criteria:
- snapshot object covers tree/chat/search/artifact/model-directory states
- stable state key builder exists

### Phase 163.A.2
Goal:
- mount deterministic hint lane in `App.tsx`
- prepare future relocation from floating card into unified search lane

Planned touch points:
- `client/src/components/myco/MycoGuideLane.tsx`
- `client/src/App.tsx`

Exit criteria:
- hint renders in main surface
- hidden when user types
- no duplicate hint on same state key

### Phase 163.A.3
Goal:
- wire event normalization for important app transitions

Planned touch points:
- `client/src/App.tsx`
- `client/src/hooks/useSocket.ts`

Exit criteria:
- tree/chat/search/artifact/scanner transitions update Mode A
- disabled search contexts produce one explicit fallback hint

### Phase 163.A.4
Goal:
- add tests

Planned touch points:
- `tests/phase163a/test_phase163a_mode_a_contract.py`
- `tests/phase163a/test_phase163a_mode_a_ui_contract.py`

Exit criteria:
- positive and negative hint scenarios covered
- stale/noise guards covered

### Phase 163.A.5
Goal:
- browser verification

Planned path:
- Playwright against local Vite runtime after implementation

Exit criteria:
- hint follows real user flow across at least 6 transitions

### Phase 163.A.6
Goal:
- optional desktop-shell verification on the same scenario contract

Planned path:
- WebDriver-compatible Tauri automation behind the same agent DSL

Exit criteria:
- browser and desktop runs share one scenario vocabulary
- no desktop-only stale hint regression

### Phase 163.A.7
Goal:
- move deterministic MYCO hints from bottom-left card into the unified search/search-scan input lane
- make MYCO the default no-text state of the single search window

Planned touch points:
- `client/src/components/search/UnifiedSearchBar.tsx`
- `client/src/App.tsx`
- `client/src/components/myco/MycoGuideLane.tsx` or successor renderer
- `client/src/components/myco/useMycoModeA.ts`

Exit criteria:
- when search input is empty, MYCO hint text is rendered in the search lane instead of the floating card
- mode selector on `vetka/` still works and disables MYCO when explicit search mode is selected
- typing into the search field hides deterministic MYCO hinting
- no duplicate simultaneous bottom-card + search-lane rendering

### Phase 163.A.8
Goal:
- convert deterministic MYCO hints into ticker-style/typed guidance inside the search lane
- keep UI density low without growing the main search box aggressively

Planned touch points:
- `client/src/components/search/UnifiedSearchBar.tsx`
- preview/hover helper used for long text reveal
- animation timing constants

Exit criteria:
- hint text can render progressively at roughly 120-180 words per minute
- full hint remains accessible through compact preview interaction instead of permanent height growth
- search box may grow by one extra line only if needed; avoid adding new visible controls

### Phase 163.A.9
Goal:
- replace passive microphone icon in the unified search lane with MYCO presence/avatar behavior
- use stateful MYCO visual states instead of a separate labeled helper block
- preserve an explicit path from `vetka/` word/context into `JARVIS-VETKA` voice mode for future stronger/adult model conversations

Planned touch points:
- search lane icon slot
- ready/idle/question MYCO assets from prepared MCC runtime set
- click-to-replay hint affordance

Exit criteria:
- idle MYCO shows question-state visual
- on new deterministic hint after user action, MYCO appears as active/speaking
- clicking MYCO can replay/read current hint without adding a new button row
- clicking the `vetka/` word still opens the explicit mode selector, and in `vetka/` mode keeps a discoverable handoff into voice/JARVIS-VETKA instead of removing that capability
- after deterministic MYCO hint playback ends, lane falls back to an idle helper placeholder instead of staying in active-speaking state
- idle helper placeholder should communicate two actions clearly:
  - tap MYCO to talk
  - tap text to search
- when explicit `vetka/` agent mode is selected, placeholder wording should switch from MYCO-helper language to VETKA/JARVIS_VETKA language

### Phase 163.A.10
Goal:
- remove top-right instructional noise and route guidance responsibility to MYCO

Planned touch points:
- main HUD/status strip in `App.tsx`

Exit criteria:
- only node count remains in the top informational strip
- click/select/pin/drag usage guidance is removed from the strip
- guidance is available through MYCO instead of duplicated static chrome

### Phase 163.A.11
Goal:
- keep deterministic MYCO coherent across `web -> result -> artifact -> save to VETKA` flow
- keep deterministic MYCO coherent across active group chat + `@mention` fixture
- debug and eliminate intermittent preview stalls/freezes in both main and chat surfaces

Planned path:
- browser fixture completion on the remaining two runtime gaps already identified by verify work
- preview lifecycle/debug pass across portal mount, unmount, hover-leave, and stacked-window transitions

Exit criteria:
- `web result -> artifact -> SAVE TO VETKA` verified
- active group chat + `@mention` verified
- phase-163A browser matrix is functionally complete for main-surface guidance
- preview panels do not remain partially or fully stuck after hover transitions or stacked-surface changes

### Phase 163.A.12
Goal:
- add deterministic onboarding and recovery hints for API key setup
- suppress setup noise when keys are already configured
- keep `web/` guidance truthful to current Tavily-backed runtime

Planned touch points:
- `client/src/components/myco/mycoModeATypes.ts`
- `client/src/components/myco/mycoModeARules.ts`
- `client/src/components/myco/useMycoModeA.ts`
- `client/src/components/ModelDirectory.tsx`
- `client/src/components/search/UnifiedSearchBar.tsx`
- `src/api/routes/config_routes.py`
- `src/api/handlers/unified_search.py`

Exit criteria:
- first-run zero-key state produces one deterministic onboarding hint
- if keys exist, onboarding hint is suppressed
- `web/` shows Tavily-specific remediation when search key is missing or unhealthy
- auth, billing, rate-limit, and timeout-style search failures map to distinct MYCO hints
- soft VETKA subscription fallback is present but not the primary instruction

### Phase 163.A.13
Goal:
- extend canonical unified search-lane behavior into scanner-related surfaces
- avoid fragmented scan-context entry points by reusing the same lane contract for scan/setup/help states

Planned touch points:
- scanner/chat surfaces that currently expose scan-specific context and actions
- unified search lane state adapter
- deterministic MYCO rules for scan-context switching

Exit criteria:
- scanner panel can host the same unified search lane pattern used in main/chat
- multiple scan-context types can feed deterministic MYCO guidance through the same lane
- no separate ad hoc helper bubble is needed for scanner-specific guidance

## MARKER_163A.P1.SEARCH_LANE_IDLE_PLACEHOLDER_SPLIT.V1
Idle unified-lane contract after deterministic hint playback:
- default helper lane:
  - MYCO avatar stays visible
  - placeholder wording target: `tap MYCO to talk or tap text to search`
- explicit `vetka/` agent lane:
  - VETKA branch identity replaces helper identity
  - placeholder wording target: `tap VETKA to talk or tap text to search`

Rule:
- this is not only wording polish
- it is a role split between:
  - MYCO fast helper/advisor
  - JARVIS_VETKA explicit stronger-agent path

## MARKER_163A.P1.SEARCH_LANE_PLAYBACK_END_IDLE.V1
When deterministic MYCO hint playback ends:
- marquee/typed playback stops
- active-speaking posture ends
- lane returns to idle helper placeholder
- the lane must not remain in speaking state after the text has finished rendering

## MARKER_163A.P1.UNIFIED_LANE_SEVERITY_MODEL.V1
MYCO must remain in the unified lane even for error/help escalations.

Severity model:
- `normal`
  - regular contextual MYCO guidance
  - no special error chrome
- `warning`
  - degraded or recoverable condition
  - same lane, but with warning-level emphasis
- `blocking`
  - action cannot continue without intervention
  - same lane temporarily prioritizes the blocking message

Rule:
- do not create a second permanent MYCO placement on the right just for errors
- do not split product guidance into:
  - normal hints in the unified lane
  - error hints in some other corner
- if a right-side rail is ever introduced later, it should be diagnostics/system-status oriented, not the canonical MYCO helper surface

## MARKER_163A.P1.SCANNER_UNIFIED_LANE_EXPANSION.V1
Scanner-related surfaces are part of the canonical lane roadmap:
- scan setup
- local file scan
- cloud connector scan
- scan/recovery/help contexts

Requirement:
- scanner should eventually use the same unified lane contract as main/chat
- no separate permanent helper bubble should survive there once the lane path is complete

## MARKER_163A.P1.PREVIEW_STUCK_DEBUG.V1
Preview debug remains an explicit roadmap item:
- investigate cases where preview partially or fully remains visible after hover/state change
- treat this as lifecycle/stacking/portal-state debugging, not cosmetic CSS cleanup

## MARKER_163A.P1.MODE_PREFIX_CLICK_ROUTING_BUG.V1
Known UI/runtime bug:
- clicking the visible mode prefix text (`myco/`, `vetka/`, `web/`, `file/`, etc.) can incorrectly trigger the lane voice/mic action instead of opening or switching the mode selector

Requirement:
- prefix click must remain a mode-selection interaction
- voice trigger must stay bound to the explicit voice affordance only
- lane text/prefix interactions must not accidentally activate microphone or spoken path

## MARKER_163A.P1.WEB_RUNTIME_MODE_BUG.V1
Known runtime gap:
- `web/` mode is still not considered functionally healthy in real runtime even when the lane and selector semantics are present

Requirement:
- treat `web/` as an open runtime defect until browser/live search flow is verified end-to-end
- MYCO guidance should not overstate `web/` readiness if the actual runtime remains broken or degraded

## MARKER_163A.P2.FILE_PLAN.V1
Expected narrow file set:
- `client/src/App.tsx`
- `client/src/hooks/useSocket.ts`
- `client/src/store/useStore.ts` only if additional selector fields are required
- `client/src/components/myco/MycoGuideLane.tsx`
- `client/src/components/myco/mycoModeATypes.ts`
- `client/src/components/myco/mycoModeARules.ts`
- `client/src/components/myco/useMycoModeA.ts`
- `tests/phase163a/*`
- `tests/e2e/phase163a/*` or equivalent agent-runner folder after GO

Explicit non-goals for first implementation:
- no edits to `client/src/components/mcc/*`
- no edits to `/api/chat/quick` default loop
- no edits to Jarvis voice runtime unless explicit secondary contour handoff is added later
- no desktop-only automation framework in the first browser MVP unless user explicitly extends scope

Roadmap correction after browser verify:
- deterministic MYCO guidance is no longer just a corner widget concern
- canonical destination is the unified search lane when the field is empty
- floating lane is now an implementation bridge, not the target UX
- asset reuse should prefer already prepared MCC runtime MYCO assets
- active hint transport must remain buttonless and low-noise
- MYCO lane display should suppress redundant filename/title repetition in user-facing text when the file is already visible in the UI; keep raw title/context available underneath for model context, preview, and internal state
- intermittent preview freeze/stick behavior must be debugged at the lane/portal lifecycle level before the UX is considered stable
- scanner-related scan/setup contexts should eventually adopt the same unified lane instead of keeping separate helper entry points
- default empty-lane contract is split:
  - MYCO = fast helper/advisor by default
  - explicit `vetka/` agent mode = future JARVIS_VETKA super-agent path
- runtime bug backlog explicitly includes:
  - prefix-click misrouting into voice trigger
  - `web/` mode still broken/degraded in real runtime

## MARKER_163A.P3.GO_NO_GO.V1
GO if:
- user approves narrow implementation
- scope stays within VETKA main surface
- no need to refactor MCC helper contracts

NO-GO if:
- implementation starts depending on LLM in default loop
- the first cut tries to cover all long-tail windows
- runtime signal quality requires large backend changes
- the search lane grows into a second control panel with extra permanent buttons

## Cross-links
See also:
- [PHASE_163A_MYCO_MODE_A_RECON_REPORT_2026-03-08](./PHASE_163A_MYCO_MODE_A_RECON_REPORT_2026-03-08.md)
- [PHASE_163A_MYCO_MODE_A_ARCHITECTURE_PROPOSAL_2026-03-08](./PHASE_163A_MYCO_MODE_A_ARCHITECTURE_PROPOSAL_2026-03-08.md)
- [PHASE_163A_MYCO_MODE_A_NARROW_MVP_CUT_2026-03-08](./PHASE_163A_MYCO_MODE_A_NARROW_MVP_CUT_2026-03-08.md)
- [PHASE_163A_MYCO_MODE_A_TEST_STRATEGY_2026-03-08](./PHASE_163A_MYCO_MODE_A_TEST_STRATEGY_2026-03-08.md)

## Status matrix
| Phase | Status |
|---|---|
| 163.A.1 snapshot/rules | Planned |
| 163.A.2 render lane | Planned |
| 163.A.3 event normalization | Planned |
| 163.A.4 tests | Planned |
| 163.A.5 browser verify | Planned |
| 163.A.6 desktop verify | Optional |
