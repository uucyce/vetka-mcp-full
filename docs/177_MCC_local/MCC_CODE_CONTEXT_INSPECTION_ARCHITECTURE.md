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

So the right MCC rule is:

- semantic hierarchy follows fractal scaling
- interaction affordances keep minimum usability bounds

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
