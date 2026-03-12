# PHASE 170 - CUT Scene Graph MCC Adapter Plan
**Date:** 2026-03-12  
**Status:** frozen for architecture chain step B1  
**References:**
- `PHASE_170_CUT_SCENE_GRAPH_ARCHITECTURE_PLAN_2026-03-12.md`
- `PHASE_170_CUT_SCENE_GRAPH_NODE_TAXONOMY_2026-03-12.md`
- `PHASE_170_CUT_SCENE_GRAPH_EDGE_TAXONOMY_2026-03-12.md`
- `client/src/utils/dagLayout.ts`
- `client/src/components/mcc/DAGView.tsx`

## Goal
Define how `cut_scene_graph_v1` becomes a CUT-flavored MCC DAG surface without forking graph grammar or layout logic.

## Adapter principle
- MCC owns DAG grammar and layout behavior
- CUT provides editorial node/edge semantics and inspector meaning
- adapter layer maps CUT graph payloads into MCC-style node/edge display primitives

## Required adapter outputs
### Nodes
Map each CUT node to an MCC DAG node with:
- stable id from `node_id`
- type bucket derived from `node_type`
- human label from `label`
- compact metadata payload for inspector rendering

Suggested visual buckets:
- `scene` -> primary structural node
- `take` -> media candidate node
- `asset` -> support/media node
- `note` -> annotation node
- future `beat` / `transition` / `sync_anchor` -> overlay-capable specialized nodes

### Edges
Map each CUT edge to an MCC edge with:
- stable id from `edge_id`
- source/target passthrough
- primary type bucket from edge taxonomy
- readable label only when it increases clarity

## Layout rules
- use `layoutSugiyamaBT()` as the default layout engine
- rank placement should be driven by structural edges, especially `follows` and `contains`
- intelligence edges must not drive rank placement
- adapter may precompute structural edge subsets for layout before reinserting overlay edges for rendering

## Inspector rules
The CUT inspector should answer editorial questions, not generic graph questions.

For nodes:
- scene summary and order
- take membership and alternates
- asset linkage
- notes and marker context

For edges:
- relation type
- why the relation exists
- confidence and source when the edge is intelligence-derived

## Cross-surface bindings
- selecting a storyboard card should focus the related `take` or `scene` node
- selecting a timeline clip should focus the linked `take` node and parent `scene`
- selecting a scene graph node should be able to highlight related storyboard/timeline entities later

## Implementation boundary
Do not copy MCC DAG logic into CUT.
Instead:
- reuse layout primitives
- reuse visual grammar
- add CUT-specific mapping and inspector layers

## Deliverables that depend on this doc
- LOD/clustering plan
- intelligence overlays plan
- product viewport plan

## Markers
- `MARKER_170.SCENE_GRAPH.MCC_ADAPTER_PLAN_FROZEN`
- `MARKER_170.SCENE_GRAPH.MCC_DAG_GRAMMAR_REUSE`
- `MARKER_170.SCENE_GRAPH.EDITORIAL_INSPECTOR_BINDING`
