# PHASE 170 - CUT Scene Graph Edge Taxonomy
**Date:** 2026-03-12  
**Status:** frozen for architecture chain step A2  
**References:**
- `PHASE_170_CUT_SCENE_GRAPH_ARCHITECTURE_PLAN_2026-03-12.md`
- `PHASE_170_CUT_SCENE_GRAPH_NODE_TAXONOMY_2026-03-12.md`
- `PHASE_170_CUT_SCENE_GRAPH_V1_DRAFT_2026-03-09.md`

## Goal
Freeze structural and intelligence edge families so the scene graph can stay readable while still accepting semantic and rhythm overlays later.

## Edge family rule
There are two canonical families:
- structural edges: define editorial structure and order
- intelligence edges: define suggested similarity, rhythm, context, or risk relationships

These families must stay visually separable.

## V1 structural edges
### `contains`
Use when a parent node owns a child node structurally.
Examples:
- `scene -> take`
- `scene -> note`
- `take -> asset`

### `follows`
Use for primary editorial or narrative ordering.
Examples:
- `scene_01 -> scene_02`
- `take_a -> take_b` only when representing sequence, not alternates

### `alt_take`
Use when two takes are alternatives for the same editorial position.

### `references`
Use for loose but explicit human-linked references.
Examples:
- `note -> scene`
- `note -> take`
- `asset -> scene`

## V1 intelligence edge
### `semantic_match`
Use for meaning-based affinity or suggested relation.
This is allowed in V1, but should be rendered secondary to structural edges.

## Approved future intelligence edges
- `rhythm_match`
- `visual_match`
- `dialogue_callback`
- `continuity_risk`
- `cam_context`
- `sync_dependency`
- `narrative_branch`

## Label and inspector rules
- edge labels should be human-readable where possible
- structural edges may omit labels if type is visually obvious
- intelligence edges should expose confidence and source in inspector overlays, not crowd the default graph view

## Visual separation policy
- structural edges: primary weight, stable routing, highest readability priority
- intelligence edges: lighter/dimmer/optional visibility, collapsible by filter or zoom level
- no graph state should allow intelligence edges to obscure structural flow

## Mapping guidance
- `follows` should dominate Sugiyama ordering
- `contains` should dominate parent-child grouping
- `semantic_match` and other intelligence edges should not control primary rank placement

## Anti-rules
- no worker orchestration edges in the editorial scene graph
- no hidden edge families produced only by model internals
- no untyped generic relation edge in frozen taxonomy

## Markers
- `MARKER_170.SCENE_GRAPH.EDGE_TAXONOMY_FROZEN`
- `MARKER_170.SCENE_GRAPH.STRUCTURAL_EDGE_FAMILY`
- `MARKER_170.SCENE_GRAPH.INTELLIGENCE_EDGE_FAMILY`
