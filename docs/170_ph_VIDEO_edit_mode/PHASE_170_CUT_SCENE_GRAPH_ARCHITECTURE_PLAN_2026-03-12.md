# PHASE 170 — CUT Scene Graph Architecture Plan
**Date:** 2026-03-12  
**Status:** execution plan frozen for long-track delivery  
**Scope:** turn `Scene Graph Surface` from debug-shell list into a first-class VETKA editorial DAG surface

## Decision
`Scene Graph Surface` is not a debug-only feature.

It is the editorial projection of VETKA's core DAG worldview.
The current debug-shell list is only the first implementation shell used to freeze contracts and hydration behavior.

## Markers
- `MARKER_170.SCENE_GRAPH.MCC_AS_MASTER_DAG_LANGUAGE`
- `MARKER_170.SCENE_GRAPH.CUT_AS_EDITORIAL_DAG_VIEWPORT`
- `MARKER_170.SCENE_GRAPH.SUGIYAMA_BT_REQUIRED`
- `MARKER_170.SCENE_GRAPH.INTEL_AS_OVERLAY_NOT_BASE`
- `MARKER_170.SCENE_GRAPH.LOD_CLUSTERING_PLAN`
- `MARKER_170.SCENE_GRAPH.NODE_EDGE_TAXONOMY_PLAN`
- `MARKER_170.SCENE_GRAPH.DEBUG_TO_PRODUCT_PATH`

## Why this exists
VETKA already exposes knowledge and workflow structure through DAG surfaces rather than hiding them.
CUT should follow the same principle.

The product rule is:
- timeline explains time,
- storyboard explains shot browsing,
- scene graph explains narrative and semantic structure,
- MCC provides the master DAG visual grammar.

## Core architectural stance
### 1. MCC is the donor grammar
Use MCC as the main visual and structural donor for graph interaction:
- Sugiyama BT layering,
- monochrome `NOLAN_PALETTE`,
- compact contextual inspector logic,
- readable DAG labels and edge semantics.

CUT should adapt that grammar to editorial entities instead of inventing a second graph system.

### 2. CUT Scene Graph is a domain-specific DAG viewport
`Scene Graph Surface` should become a specialized editorial DAG view, not merely a panel with node rows.

It should answer:
- what scenes exist,
- what takes/assets/notes belong to them,
- which scenes follow or mirror each other,
- what semantic or rhythm relations the intelligence stack suggests,
- which nodes deserve editor attention now.

### 3. Intelligence stays additive
`JEPA`, `V-JEPA`, `TTR`, `PULSE`, `HDBSCAN`, spectral analysis and similar systems must enrich the graph, not replace it.

They may provide:
- proposed nodes,
- proposed edges,
- confidence scores,
- cluster suggestions,
- overlays and attention hints.

They must not become opaque black-box UI that bypasses the DAG.

## Canonical surface model
### Layer A — Contract / hydration layer
This is the current wave.

Goal:
- freeze read model,
- freeze hydration behavior,
- freeze empty/loading/ready states,
- verify debug-shell rendering and refresh.

Artifacts:
- `cut_scene_graph_v1`
- debug-shell smoke/recon/mock-matrix docs

### Layer B — Taxonomy layer
Define stable editorial graph semantics.

Required outputs:
- node taxonomy doc
- edge taxonomy doc
- graph-to-timeline/storyboard mapping doc

### Layer C — View adapter layer
Adapt MCC DAG view conventions to CUT.

Required outputs:
- adapter plan from `cut_scene_graph_v1` -> MCC DAG node/edge shapes
- styling/alignment rules for editorial DAG nodes
- interaction rules for focus/select/inspect actions

### Layer D — Intelligence overlay layer
Attach enrichment systems as overlays.

Required outputs:
- JEPA/V-JEPA proposal mapping
- TTR/PULSE rhythm-edge mapping
- HDBSCAN/spectral clustering and LOD policy
- confidence/fallback rules

### Layer E — Product surface layer
Promote from debug-shell card to real editorial viewport.

Required outputs:
- CUT scene graph viewport in product NLE shell
- contextual inspector and drilldowns
- collapse/expand and cluster navigation
- selected-shot / timeline / storyboard cross-highlighting

## Required node taxonomy
V1 draft already starts with:
- `scene`
- `take`
- `asset`
- `note`

Planned V2 editorial types:
- `beat`
- `transition`
- `marker_group`
- `sync_anchor`
- `semantic_anchor`
- `cam_anchor`
- `alt_branch`

Rule:
- do not add types without an interaction or inspection use case.

## Required edge taxonomy
V1 draft already starts with:
- `contains`
- `follows`
- `semantic_match`
- `alt_take`
- `references`

Planned V2/V3 overlays:
- `rhythm_match`
- `visual_match`
- `dialogue_callback`
- `continuity_risk`
- `cam_context`
- `sync_dependency`
- `narrative_branch`

Rule:
- structural edges and intelligence edges must stay visually separable.

## Visual rules
### Layout
- keep Sugiyama bottom-to-top as default DAG layout
- preserve editorial readability over graph density
- scene hierarchy and narrative flow should dominate rank placement
- overlay edges may bend or soften, but must not destroy structural readability

### Styling
- reuse `NOLAN_PALETTE`
- avoid bright chroma except for semantic/alert states
- preserve MCC-like compact cards/labels/inspectors
- no emoji in graph runtime surface

### Level of detail
- far zoom: clusters and scene-level aggregates
- medium zoom: scene + take relationships
- near zoom: markers, semantic anchors, sync anchors, note details

## Intelligence integration rules
### JEPA / V-JEPA
Use for:
- semantic scene similarity,
- visual motif recurrence,
- shot/scene proposal links,
- candidate narrative anchors.

Do not use as hard blocker for base graph rendering.

### TTR / PULSE
Use for:
- rhythm adjacency,
- pacing clusters,
- transition confidence,
- beat alignment suggestions.

Treat as overlay edge families, not as replacement of timeline sync.

### HDBSCAN / spectral
Use for:
- cluster collapse/expand,
- semantic region grouping,
- zoom-level simplification,
- optional side-panel grouping.

These should support graph navigation and LOD, not hide core scene structure.

## Mapping between CUT surfaces
### Storyboard -> Scene Graph
Storyboard cards are shot-first.
Scene graph should group those shots into scene/beat/take structure.

### Timeline -> Scene Graph
Timeline clips are temporal instances.
Scene graph nodes are structural identities.

### Selected Shot / Inspector -> Scene Graph
Selection in storyboard or timeline should focus the related scene graph node and inspector section.

## Execution order
### Step 1
Finish Wave 18 contract pass for `Scene Graph Surface` in debug shell.

### Step 2
Freeze taxonomy and adapter docs.

### Step 3
Design MCC-to-CUT DAG adapter for editorial node and edge types.

### Step 4
Define clustering / LOD / overlay policies.

### Step 5
Implement first product-grade scene graph viewport in CUT shell.

## Required follow-up documents
These documents are now part of the architecture chain and future tasks should reference them explicitly.

1. `PHASE_170_CUT_SCENE_GRAPH_NODE_TAXONOMY_2026-03-12.md`
2. `PHASE_170_CUT_SCENE_GRAPH_EDGE_TAXONOMY_2026-03-12.md`
3. `PHASE_170_CUT_SCENE_GRAPH_MCC_ADAPTER_PLAN_2026-03-12.md`
4. `PHASE_170_CUT_SCENE_GRAPH_LOD_CLUSTERING_PLAN_2026-03-12.md`
5. `PHASE_170_CUT_SCENE_GRAPH_INTEL_OVERLAYS_2026-03-12.md`
6. `PHASE_170_CUT_SCENE_GRAPH_PRODUCT_VIEWPORT_PLAN_2026-03-12.md`

## Long-track rule for TaskBoard
Every new Scene Graph task should reference:
1. this architecture plan,
2. the specific follow-up doc it creates or implements,
3. the current CUT surface it touches (`debug shell`, `NLE shell`, `MCC adapter`, `overlay layer`).

This keeps the project incremental and prevents graph work from fragmenting into unrelated experiments.
