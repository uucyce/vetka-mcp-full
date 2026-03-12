# PHASE 170 CUT Scene Graph Screenshot Review (2026-03-12)

## Scope

Screenshot/self-review pass for the current CUT Scene Graph promotion work:
- NLE surface with Scene Graph pane mounted in the main editor
- debug shell with Scene Graph controls and promotion buttons

Artifacts:
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/docs/170_ph_VIDEO_edit_mode/screenshots/cut-nle-scene-graph-review.png`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/docs/170_ph_VIDEO_edit_mode/screenshots/cut-debug-scene-graph-review.png`

## What is working

- `Graph Ready` is visible in the main CUT transport, so Scene Graph readiness is now explicit in the primary NLE surface.
- The NLE layout now reserves a dedicated `Scene Graph Surface` pane between `Program Monitor` and the right inspector.
- The debug shell exposes `Embed In Flow` and `Promote To Peer Pane`, which makes the promotion path visible and testable.
- The current monochrome styling is coherent with the existing CUT language.

## Findings

### MARKER_170.SCREENSHOT.OK.NLE_PANE
The NLE pane insertion is visually correct. The graph surface reads as a peer editing surface instead of a hidden debug artifact.

### MARKER_170.SCREENSHOT.OK.DEBUG_CONTROLS
The debug shell still provides the right bootstrap controls and does not conflict with the NLE promotion path.

### MARKER_170.SCREENSHOT.GAP.EMPTY_STATE
The screenshots show an empty project state. Without a bootstrapped project, the Scene Graph pane stops at `No graph nodes available.` and does not demonstrate the graph payload quality.

Action taken in this pass:
- upgraded empty-state copy to `Open a CUT project and run scene assembly.` in both NLE and debug graph surfaces.

### MARKER_170.SCREENSHOT.NEXT.LOADED_PROJECT_PASS
The next screenshot pass should use a mocked or bootstrapped project so the review captures:
- DAG viewport with real nodes/edges
- compact media-native card with poster/sync signals
- cross-highlighting between Selected Shot and Scene Graph

## Practical conclusion

The Scene Graph promotion work is visually on the right track. The current limitation is not layout quality; it is the absence of a loaded project state in the screenshot pass. The next high-value visual review should happen after a deterministic bootstrap fixture is available for `/cut`.

## Loaded-state follow-up

Additional artifact:
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/docs/170_ph_VIDEO_edit_mode/screenshots/cut-nle-scene-graph-loaded-review.png`

### MARKER_170.SCREENSHOT.OK.LOADED_FIXTURE
The loaded fixture confirms the promoted NLE Scene Graph pane now renders:
- real DAG viewport content
- compact media-native card with poster preview
- sync badge and bucket metadata
- crosslinked selection summary

### MARKER_170.SCREENSHOT.FIX.REACTFLOW_PROVIDER
During the first loaded-state pass, the pane crashed because `DAGView` was mounted without `ReactFlowProvider`. This pass fixed that wiring in `CutStandalone`, and the loaded-state smoke now passes.

## Debug loaded-state follow-up

Additional artifact:
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/docs/170_ph_VIDEO_edit_mode/screenshots/cut-debug-scene-graph-loaded-review.png`

### MARKER_170.SCREENSHOT.OK.DEBUG_LOADED
The loaded debug shell now proves the broader CUT shell still hydrates correctly with the same Scene Graph payload used by NLE review.

### MARKER_170.SCREENSHOT.OK.PROMOTION_CONTINUITY
The same loaded payload can be inspected in both surfaces:
- debug shell keeps bootstrap and worker context visible
- NLE keeps the promoted graph pane visible
- the promotion path is now reviewable from both sides without changing payload shape
