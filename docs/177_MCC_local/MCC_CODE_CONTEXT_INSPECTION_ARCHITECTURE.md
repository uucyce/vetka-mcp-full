# MCC Code Context Inspection Architecture

Date: 2026-03-12
Tag: `localguys`, `mcc`, `context`, `dag`, `ux`

## Problem

Current MCC graph and context UX still mixes three different concerns:

1. topology overview
2. task/workflow control
3. code and document inspection

That creates visible friction:

- directory/code branches still look too much like task cards
- structural edge labels like `struct` leak implementation vocabulary into the main canvas
- MiniContext can preview files, but the path from graph node -> actual code reading is still indirect
- deeper descendants are not yet modeled as a first-class inspection flow; users want children, grandchildren, and great-grandchildren on demand
- selecting a code node can still feel like "I selected a task" instead of "I selected a code scope"

## Recon findings

### 1. Structural edge labels are explicit in UI code

The short label `struct` is hardcoded as a visible edge label in:

- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/client/src/utils/dagLayout.ts`
- `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/client/src/components/mcc/TaskDAGView.tsx`

That is technically correct for graph internals, but wrong for human-facing MCC reading mode.

### 2. Code topology and task topology are not visually separated enough

`MyceliumCommandCenter` still normalizes several node kinds into task/workflow-oriented context, and MiniContext still uses task packet sections as the most mature surface.

Result: when the selected node is really a code directory or file scope, the surrounding UX still feels task-first.

### 3. MiniContext improved, but it is still a bridge, not a full inspection surface

Current state is better than before:

- linked docs can preview
- linked docs can focus in DAG
- linked docs can open in pane
- directory tree now lazy-loads descendants level by level
- file rows can preview/open/focus

But the full inspection loop is still incomplete:

- no dedicated code-inspection mode
- no explicit "this is code, not task" projection
- no clean distinction between topology metadata and code content metadata
- no full descendant browsing contract across all levels

## Design goal

Make MCC graph topology-first and inspection-second, but let code/document inspection become a first-class path.

The user should be able to do this without ambiguity:

1. select a code node
2. understand whether it is a directory, file, aggregate, or task
3. expand children, grandchildren, and great-grandchildren on demand
4. open actual code/doc content immediately
5. keep task/workflow surfaces available, but not forced onto code navigation

## Proposed solution

## Layer 1 - Split topology semantics from human labels

Keep internal edge type `structural`, but do not render `struct` in the main MCC graph by default.

Policy:

- topology view: edge label hidden unless it carries meaningful semantic distinction
- debug/diagnostic view: edge label can be shown
- if shown to humans, use readable labels such as:
  - `contains`
  - `calls`
  - `depends`
  - `feeds`

For simple directory containment edges, default should be no label.

## Layer 2 - Introduce explicit code-scope node projection

Code-related nodes need a separate presentation contract from task nodes.

Human node classes should be projected as:

- `task`
- `workflow agent`
- `workflow artifact`
- `directory`
- `file`
- `code aggregate`
- `document`

This matters both for:

- node card chrome
- MiniContext section ordering
- MYCO/context hints

A directory like `pulse/src/music` should not read like a pending task card unless it actually is a task.

## Fractal scale policy

I agree with the direction, with one adjustment: the useful part for MCC is not strict golden-ratio dogma, but a stable fractal scale rule.

That means:

- each deeper level is visually smaller than its parent
- the reduction factor is consistent across levels
- target scale step is phi-based: about `1 / 1.6` per descendant level (`1 / 1.618` if we keep the exact constant)
- spacing, font, chrome weight, and edge emphasis all follow the same rule
- deeper descendants stay legible, but clearly read as nested context, not peers of the parent

For MCC this should apply to:

- node card width/height
- title font size
- secondary metadata opacity
- handle/anchor prominence
- edge weight and label visibility

Recommended policy:

- root / current focus level = scale `1.0`
- child = scale `1 / 1.6`
- grandchild = scale `1 / 1.6^2`
- great-grandchild = scale `1 / 1.6^3`
- if we need exact math, use `phi ~= 1.618`, but the product requirement is stable self-similarity near `1.6`
- further descendants keep shrinking until a readable floor, then switch to browse-on-demand rather than full visual expansion

Important constraint:

- fractal scaling should be applied to code-topology exploration
- it should not make active task/workflow nodes too tiny to operate
- interaction targets must keep a minimum clickable size even when visual chrome shrinks
- generation bands should not share one global mini-floor; daughters, grandchildren, and great-grandchildren need separate floor policies
- layout geometry should also scale by generation band so spacing reads as nested, not flat

So the right MCC rule is:

- semantic hierarchy follows fractal scaling
- interaction affordances keep minimum usability bounds
- depth bands (`1`, `2`, `3+`) get separate floor policies for node size, font, handles, and edges
- depth bands (`1`, `2`, `3+`) get separate spacing policy for `xGap/yGap`

## Layer 3 - Make descendant browsing first-class

Lazy loading should not stop at one expansion gesture. The browsing contract should explicitly support:

- children
- grandchildren
- great-grandchildren
- further descendants as needed
- explicit presets for the first three generations
- `+1 deeper` browsing beyond those presets
- no return to eager recursive dump mode

The model should be:

- one level loaded per expand action
- each expanded directory becomes its own lazy root
- path breadcrumbs remain visible
- expansion state survives local inspection session where possible
- each deeper level follows the MCC fractal scale rule instead of staying visually flat

This is better than eager recursive dumping and better than a fixed depth cap pretending to be full navigation.

### Infinite fractal zoom rule

This should not be implemented as hardcoded `depth1/depth2/depth3`.

The correct model is:

- click on a node -> one deeper level is born for that branch
- click on a child -> one deeper level is born under that child
- the system can continue recursively without a fixed upper depth bound

So MCC should support:

- logically unbounded descendant depth
- visually bounded rendering
- branch-local lazy expansion

That means:

- the graph does **not** render "infinite nodes at once"
- the graph **does** support infinite recursive inspection on demand
- one expand gesture should materialize one generation, not children+grandchildren together
- deeper levels follow the same fractal rule (`1 / 1.6^n`) until usable floors are reached
- after that, the UI switches to condensed/inspection/viewer modes instead of shrinking forever

This is the key path to "any folder or document is reachable if the user wants to zoom in enough".

## Layer 3B - Balance symbolic MCC vs full VETKA visualization

VETKA solves some of this through fuller 3D presence and stronger visual ontology.

MCC should not try to copy that literally. It should keep a symbolic/lightweight graph, but the symbolic layer must still make these classes visually distinct:

- project root
- directory
- file
- document
- task
- workflow

Current `DIR/FILE/ROOT` labels are not enough by themselves.

Recommended balance:

- keep cards lightweight and symbolic
- use stronger semantics in border style, chrome weight, header treatment, and metadata ordering
- do not make directories and files read as the same "pending task card"
- let `DOC` and `CODE` diverge chromatically without turning MCC into a full 3D object scene
- let geometry also express generation band so deeper descendants cluster more tightly than daughters

The user should be able to distinguish "folder vs document vs task" without reading multiple metadata lines.

Recommended symbolic split for MCC graph cards:

- `ROOT` - project or branch root
- `DIR` - directory/module container
- `DOC` - human-facing document
- `CODE` - source file / implementation file
- task/workflow nodes keep their own operational styling

This keeps MCC lighter than full VETKA 3D while still preserving semantic readability.

## Layer 3C - Avoid projection echo and duplicate truth

When a node already exists in the upper projection, deeper drill should not create a second "truth copy"
that reads like a separate object at another scale.

The rule should be:

- the graph keeps one canonical semantic node identity
- drill adds descendant context, not a second authoritative duplicate
- if the same entity is already visible at a larger layer, deeper expansion should reference/focus it rather
  than create a contradictory clone
- overlays may be used for local descendant context, but their lineage must stay branch-local and visually secondary

In practice this means MCC should avoid:

- one large node and one tiny node pretending to be the same entity in parallel
- a child projection appearing under the wrong open branch
- two open branches fighting over the same inline descendants

Recommended rule:

- when a semantic node is represented by an active inline descendant projection, the duplicate canonical node
  should be suppressed or visually demoted in that view
- the overlay remains branch-local
- only the current branch root may stay as the dominant canonical anchor while descendants are projected inline
- the canonical identity remains the same through `rd_origin_id`

## Layer 3D - Branch ownership and expansion correctness

Branch drill must be local and deterministic.

Correct behavior:

- clicking a root or top-level node opens that node's descendants
- clicking another top-level node switches branch ownership to that node
- clicking a child inside the currently open branch deepens that same branch
- clicking an ancestor truncates only its descendants
- clicking the current deepest node may collapse only that branch

Incorrect behavior:

- clicking node B while node A is open causes descendants to appear under node A
- one shared expansion chain appends unrelated top-level anchors as if they were descendants

So the drill chain model must distinguish:

- branch switch
- ancestor truncation
- inline descendant deepen

These are different operations and should not share one fallback append rule.

## Layer 3C - Avoid projection echo / duplicated hierarchy

Another required rule:

- if a node is already present as a large/top-level graph entity,
- and the user opens a deeper drill,
- the system must not create a confusing second projection of the same semantic entity in a way that looks like duplicate truth

This "projection echo" was already observed in recent behavior.

Policy:

- one semantic node may have multiple projections
- but only one projection should be visually dominant at a time
- inline descendants must read as descendants of the currently drilled branch, not as parallel competing copies

This requires explicit projection discipline in the graph engine.

## Layer 3D - Branch ownership and expansion correctness

Current expansion must respect branch ownership:

- clicking one branch must expand that branch
- clicking another top-level branch must switch branch ownership cleanly
- descendants must not accidentally be born under the previously expanded branch

This is not only a UI bug; it is a graph-state contract bug.

The drill state must therefore be:

- branch-local
- ancestor-aware
- root-switch safe

If the user clicks a different top-level branch, MCC should not append it as a child of the existing chain unless there is a real ancestry relation.

## Layer 4 - Separate inspection modes inside MiniContext

MiniContext should render one of several inspection modes depending on selected node class:

### Code mode
For `directory`, `file`, `code aggregate`:

- path/breadcrumbs first
- descendant tree second
- code preview/open actions third
- linked tasks/docs as supporting material, not the main headline

### Task mode
For `task`:

- task packet first
- workflow/runtime status second
- linked docs/code scope third

### Workflow mode
For agents/artifacts/gates:

- runtime/stream/artifacts first
- supporting docs/context second

This removes the current feeling that everything is ultimately a task card.

## Layer 5 - Add a real code viewer path

Today we have preview and artifact-style pane opening, but MCC still needs a more explicit code inspection route.

Target:

- `preview` = inline quick read inside MiniContext
- `open in pane` = docked file/code viewer inside MCC
- later optional `open fullscreen` = dedicated reading/debugging surface

The key requirement is that users can clearly see actual code content, not just metadata.

## Layer 6 - Breadcrumb and path discipline

For code inspection, path context matters more than task status.

Required UX elements:

- breadcrumb header for selected code node
- visible root/scope origin
- explicit current node type (`directory`, `file`, `code aggregate`)
- path copy/open/focus actions near the top

## Recommended implementation order

1. hide `struct` labels in normal MCC mode
2. add explicit code-scope visual projection contract
3. reorder MiniContext into `code mode / task mode / workflow mode`
4. add breadcrumb header for code inspection
5. apply fractal descendant scaling to code-topology browsing
6. add docked code viewer contract
7. only then revisit deeper DAG/file-tree parity

## What should go into roadmap/tasks

### Track A - graph readability
- suppress low-value structural labels in normal mode
- only surface semantic edge labels when they help reading
- clean visual distinction between task nodes and code nodes

### Track B - code inspection UX
- descendant browsing across children/grandchildren/great-grandchildren
- breadcrumb header and path tools
- code-first MiniContext rendering for file/directory nodes
- docked code viewer path

### Track C - architecture alignment
- stop treating code scope as task scope in human-facing context surfaces
- keep task packet available as supporting context instead of default headline
- preserve task/workflow power without making code browsing feel task-shaped

## Success criteria

The gap is closed when all of the following are true:

- a code directory no longer reads like a task card by default
- users do not see `struct` in normal graph reading mode
- any expanded directory can reveal deeper descendants level by level
- selecting a file or directory gives immediate path to actual content
- MiniContext clearly tells the user whether they are inspecting code, task, or workflow

## Non-goal

This is not about copying VETKA chat-context UX into MCC.

This is specifically about making MCC better at graph-native code inspection, then later upstreaming the proven pieces back into VETKA where useful.
