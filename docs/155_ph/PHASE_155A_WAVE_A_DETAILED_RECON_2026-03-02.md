# PHASE 155A — Wave A Detailed Recon (2026-03-02)

Protocol stage: `RECON + markers` (no implementation in this step).

Source baseline:
- `docs/155_ph/PHASE_155A_GRANDMA_MODE_ROADMAP_2026-03-02.md`
- `docs/155_ph/PHASE_155A_GRANDMA_MODE_RECON_MARKERS_2026-03-02.md`

User constraints locked for Wave A:
1. `grandma mode`: max 3 primary actions.
2. Remove visual noise and duplicated context strips.
3. Add universal node/file context window (`MiniContext` / artifact-style eye).
4. Architect model binding must follow key selected by user in `MiniBalance`.
5. Red color on primary surface is forbidden (until explicit approval).
6. Reuse VETKA visual assets/icons first; fallback to simple white SVG.

---

## A) Recon map by Wave A markers

### `MARKER_155A.WA.UI_NOISE_CLEANUP.V1`

Confirmed noise surfaces in current MCC runtime canvas:

1) Top-left source controls (visible in normal runtime, not debug-only):
- `client/src/components/mcc/MyceliumCommandCenter.tsx:3360`
- `runtime/design/predict` segmented buttons at `:3377-3399`
- Source badge at `:3405-3429`

2) Redundant debug overlays in roadmap mode (hidden by `debugMode`, but still present and visually dense in debug screenshots):
- LOD hint: `:3433-3452`
- Focus view hint: `:3455-3474`
- Focus restore policy bar: `:3477-3517`
- Verifier/JEPA badges: `:3522-3582`
- DAG versions + compare controls/matrix:
  - toolbar `:2928-3078`
  - matrix `:3080-3219`

3) Footer actions are debug-gated today:
- `client/src/components/mcc/MyceliumCommandCenter.tsx:3587`

Risk:
- Useful runtime controls (source mode, stream toggle) are mixed with debug ergonomics.
- Need split policy: user-surface minimal vs dev-only panel.

Decision for impl:
- Keep user-surface minimal by default; move all diagnostics/compare controls to dev-only plane.

---

### `MARKER_155A.WA.DUPLICATE_TASK_STRIP_REMOVE.V1`

Duplicate task context rendering confirmed:

1) Extra task strip in canvas body:
- `client/src/components/mcc/MyceliumCommandCenter.tsx:3222-3255`

2) Breadcrumb already carries task context in roadmap:
- `client/src/components/mcc/MCCBreadcrumb.tsx:72-76`

Result:
- The strip at `:3222-3255` is true duplication and should be removed.

---

### `MARKER_155A.WA.MINICONTEXT_SHELL.V1`

`MiniContext` shell is absent; currently there is no node/file universal context mini-window in MCC.

Evidence:
1) Existing mini windows mounted:
- `MiniChat`, `MiniTasks`, `MiniStats`, `MiniBalance`
- `client/src/components/mcc/MyceliumCommandCenter.tsx:3324-3332`

2) `NodeStreamView` exists but is not wired in main MCC runtime:
- file exists: `client/src/components/mcc/NodeStreamView.tsx`
- no import/use in `MyceliumCommandCenter.tsx` (imports at `:12-53`)

3) Artifact viewer currently implemented as full-screen overlay, not mini-window:
- state + loader: `MyceliumCommandCenter.tsx:1229-1258`
- overlay render: `:3769-3844`

4) Reusable artifact infrastructure already present outside MCC:
- `client/src/components/artifact/ArtifactWindow.tsx`
- `client/src/components/artifact/ArtifactPanel.tsx`

Decision for impl:
- Build `MiniContext` as separate mini-window shell (same framework as `MiniWindow`) and route file/artifact/agent/task context into it.
- Prefer reuse of `ArtifactPanel/ArtifactWindow` patterns for content rendering.

---

### `MARKER_155A.WA.SELECTION_ROUTER_BASE.V1`

Base selection primitives are present and stable:

1) Node selection state:
- `selectedNode`, `selectedNodeIds` in `MyceliumCommandCenter.tsx:1209-1210`
- selection handler: `:2604-2639`

2) Store focus memory hooks:
- `focusedNodeId` in MCC store type and state:
  - `client/src/store/useMCCStore.ts:255`
  - setter `:695`

3) Task selection coupling already exists for overlay tasks:
- `MyceliumCommandCenter.tsx:2635-2638`

Gap:
- No normalized “selection-to-context” router object (scope/type/payload) consumed by MiniChat/MiniStats/Stream/Context panel.

Decision for impl:
- Add a canonical selection router (node kind -> context envelope) before wiring each mini-window.

---

### `MARKER_155A.WA.COLOR_POLICY_NO_RED.V1`

Wave A surface violations of no-red policy:

1) Source badge error color:
- `MyceliumCommandCenter.tsx:3416` uses `#ef8d8d`

2) Diagnostics/health badges use red on failures:
- `MiniStats.tsx:241,247`
- `MyceliumCommandCenter.tsx:1703,1788,1817,1875`

3) Compare matrix decision color includes red fail state:
- `MyceliumCommandCenter.tsx:3141`

4) Additional mcc files still use red-ish fallback (`#a66`, `#aa7373`) including deprecated or optional surfaces:
- examples: `MiniTasks.tsx:25`, `NodeStreamView.tsx:192,346-347`, `PlaygroundBadge.tsx:181`

Decision for impl:
- Introduce neutral warning/fail palette tokens for MCC user surface and swap direct red literals in active Wave A surfaces.
- Keep strict rule scoped to user-facing runtime plane first; debug-only can be normalized in later wave if needed.

---

## B) Related gaps discovered during Wave A recon

1) `MARKER_155A.P3.NODE_CONTEXT_WINDOW` status remains `NOT DONE`.
- Evidence: no mounted context mini-window, only legacy artifact overlay and isolated `NodeStreamView`.

2) `MARKER_155A.P3.STATS_CONTEXT` remains `PARTIAL`.
- `MiniStats` loads global endpoints only:
  - summary `MiniStats.tsx:87`
  - agents summary `MiniStats.tsx:130`
- no node/task/agent context input.

3) `MARKER_155A.P3.STREAM_CONTEXT` remains `PARTIAL/NOT DONE` for node scope.
- `StreamPanel` filters only by `selectedTaskId`:
  - `StreamPanel.tsx:19-27`
- no selected-node/agent filter.

4) `MARKER_155A.P3.MODEL_EDIT_BIND` still not on active surface.
- Model edit logic exists in legacy/deprecated detail surfaces, not in active mini context path.

---

## C) Wave A implementation-ready scope (narrow)

1) Remove duplicate task strip.
2) Move/hide UI noise on user surface:
- source mode + source badge + debug overlays/compare controls out of default runtime plane.
3) Add `MiniContext` shell only (without full deep content matrix yet):
- empty-state + selected-node basic metadata.
4) Introduce selection router base object for downstream mini windows.
5) Apply no-red token policy to active Wave A surface components.

Out of Wave A (keep for Wave B/C):
- full chat scope routing,
- full stats context fanout,
- architect model/preprompt editor in context window,
- runtime-truth overlay and user edge editing.

---

## D) Verification checklist for Wave A impl

1) No duplicate task strip visible in roadmap/workflow (`selectedTaskId` only shown via breadcrumb/context window).
2) Default runtime surface has no unexplained top-left controls (`RUNTIME/DESIGN/PREDICT`, `SOURCE: ...`) unless explicitly opened via dev mode.
3) Clicking any DAG node updates a unified selection context envelope (inspectable in dev logs).
4) `MiniContext` auto-opens on node selection and closes/empties on pane deselect.
5) Active Wave A user surface uses no red literals for status/error.

---

## E) Asset reuse reality check

Requested: reuse VETKA icons (`png/svg`) first.

Current repo inventory (UI-ready icon sets) is limited:
- no dedicated MCC icon pack in `client/src/assets` (only `vetka_gpt_1_UP1_PHalfa.png`)
- available SVGs are mostly vite/react/tauri app icons, not workflow UI glyphs.

Implementation consequence:
- For Wave A, use existing iconography already in MCC (emoji/text) or simple white SVG controls.
- If external VETKA icon pack exists in another repo/workspace, add as explicit import task in separate step.
