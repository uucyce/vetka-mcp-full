MARKER_163A.SEARCH_LANE.MODE_REFACTOR.RECON_REPORT.V1
LAYER: L4
DOMAIN: UI|MYCO|CHAT|VOICE
STATUS: RECON
SOURCE_OF_TRUTH: docs/163_ph_myco_VETKA_help/PHASE_163A_SEARCH_LANE_MODE_REFACTOR_RECON_REPORT_2026-03-08.md
LAST_VERIFIED: 2026-03-08

# PHASE_163A_SEARCH_LANE_MODE_REFACTOR_RECON_REPORT_2026-03-08

## Synopsis
MYCO guidance is not reaching a true unified search lane because the current UI is built around two independent `UnifiedSearchBar` instances and an input-first rendering contract. The problem is architectural, not Tauri-specific and not solvable by further CSS repositioning.

## Short Narrative
Current implementation adds MYCO as a secondary visual layer inside the search container. That can make the text appear close to the input, but it does not turn the lane itself into a MYCO-speaking surface. At the same time, chat and main surfaces instantiate separate `UnifiedSearchBar` components with different props, so behavior diverges. The correct next step is a mode-driven lane contract shared by both surfaces.

## Confirmed Findings
### MARKER_163A.SEARCH_LANE.DUAL_INSTANCE_ROOT_CAUSE.V1
- Main-surface search lane is mounted in:
  - `client/src/App.tsx`
- Chat-surface search lane is mounted in:
  - `client/src/components/chat/ChatPanel.tsx`
- These are separate instances with separate prop contracts.

### MARKER_163A.SEARCH_LANE.MYCO_PROPS_MAIN_ONLY.V1
- Main-surface `UnifiedSearchBar` receives:
  - `mycoHint`
  - `mycoStateKey`
  - `mycoSurfaceScope`
- Chat-surface `UnifiedSearchBar` currently does not receive those props.
- Result: MYCO can appear in the main lane while chat lane remains unaware of deterministic MYCO state.

### MARKER_163A.SEARCH_LANE.INPUT_FIRST_CONTRACT.V1
- `UnifiedSearchBar` still renders an input row as the primary control.
- MYCO guidance is injected as an extra visual layer within the same wrapper.
- Result: MYCO is rendered as an accessory to the input, not as the search lane's own active mode.

### MARKER_163A.SEARCH_LANE.NOT_A_TAURI_LIMIT.V1
- Runtime behavior shows no evidence of Tauri-native rendering limitations.
- The issue reproduces as a normal React component-ownership problem:
  - duplicated instantiation
  - mismatched props
  - input-first JSX contract

## Root Cause
The lane has no explicit state machine for:
- input
- deterministic MYCO guidance
- voice listening
- voice thinking
- voice speaking

Instead, these states are approximated by conditional decorations layered around the input. That makes it impossible to guarantee a single canonical lane behavior across main and chat surfaces.

## Required Refactor Direction
### MARKER_163A.SEARCH_LANE.MODE_CONTRACT.V1
Introduce a canonical `SearchLaneMode` contract:
- `input`
- `myco_guidance`
- `voice_listening`
- `voice_thinking`
- `voice_speaking`

And a paired `SearchLanePayload`:
- `title`
- `body`
- `previewBody`
- `stateKey`
- `editable`
- `source`
- `interactive`

### MARKER_163A.SEARCH_LANE.ADAPTER_LAYER.V1
Add a lane adapter/resolver that normalizes:
- query state
- search context
- voice state
- MYCO deterministic hint
- surface ownership (`main` vs `chat`)
- selector open/closed state

This adapter should produce one lane mode + one lane payload, instead of letting JSX combine independent booleans ad hoc.

### MARKER_163A.SEARCH_LANE.SHARED_SURFACE_CONTRACT.V1
Both `App.tsx` and `ChatPanel.tsx` must bind to the same lane contract.

Expected outcome:
- empty lane shows MYCO consistently in both surfaces
- typing collapses MYCO and returns to editable input
- voice mode uses the same lane, not a competing UI path
- preview logic stays attached to the same canonical payload

## Narrow Implementation Sequence
### Phase 163.A.11R
- freeze recon and ownership boundaries
- no runtime behavior changes

### Phase 163.A.12R
- introduce lane mode types + adapter layer
- keep current visuals initially

### Phase 163.A.13R
- wire both search-bar instances to the same lane contract

### Phase 163.A.14R
- replace input-first rendering with mode-first rendering
- lane renders either:
  - input
  - MYCO guidance
  - voice state
  and never “input plus a decorative MYCO second layer”

### Phase 163.A.15R
- verify in:
  - main surface
  - chat surface
  - empty lane
  - typing transition
  - `vetka/web/file` selector
  - hover preview
  - voice handoff

## Do Not Do
- no further padding/absolute-position micro-patches as a substitute for contract refactor
- no chat-only MYCO special case
- no third helper component that duplicates search-lane logic
- no Tauri-specific workaround without evidence of native-runtime limitation

## Go/No-Go
Go if:
- lane ownership is documented once
- adapter boundary is explicit
- main and chat can be migrated to the same contract

No-Go if:
- MYCO remains a second visual row/layer under or inside an input-first lane
- chat and main receive different semantic contracts
- voice and MYCO continue to compete for the same space through independent booleans

## Cross-links
- [PHASE_163A_MYCO_MODE_A_IMPLEMENTATION_PLAN_2026-03-08](./PHASE_163A_MYCO_MODE_A_IMPLEMENTATION_PLAN_2026-03-08.md)
- [PHASE_163A_MYCO_MODE_A_VERIFY_REPORT_2026-03-08](./PHASE_163A_MYCO_MODE_A_VERIFY_REPORT_2026-03-08.md)
- [PHASE_163B_MYCO_VOICE_RUNTIME_SHORT_REPORT_2026-03-08](./PHASE_163B_MYCO_VOICE_RUNTIME_SHORT_REPORT_2026-03-08.md)
- [PHASE_163B1_MYCO_PERSONA_VOICE_BASELINE_REPORT_2026-03-08](./PHASE_163B1_MYCO_PERSONA_VOICE_BASELINE_REPORT_2026-03-08.md)
