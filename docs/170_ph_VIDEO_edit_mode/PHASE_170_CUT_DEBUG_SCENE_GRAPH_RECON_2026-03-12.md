# PHASE 170 - CUT Debug Scene Graph Surface Recon

## Scope
- Screen: `/cut` debug shell
- Card: `Scene Graph Surface`
- Architecture anchor: `PHASE_170_CUT_SCENE_GRAPH_ARCHITECTURE_PLAN_2026-03-12.md`

## Stable anchors
- `VETKA CUT`
- `Scene Graph Surface`
- empty state: `Scene graph not ready.`
- empty graph state: `No graph nodes available.`
- representative node labels, for example `Opening Scene`, `Take A`, `Director Note`
- representative node identity rows, for example `scene_01 · scene`

## Visible row structure
Each rendered row shows:
- primary line: `node.label`
- secondary line: `node.node_id · node.node_type`

## Hydration behavior
- when `graph_ready` is false, the card must show `Scene graph not ready.`
- when `graph_ready` becomes true and `scene_graph.nodes[]` is empty, the card must show `No graph nodes available.`
- when nodes arrive after refresh, the card must render one row per node without runtime errors

## Current product meaning
This is the first contract-level CUT projection of the editorial DAG.
The current surface is list-form, but the architecture plan treats it as the precursor to a full MCC-style editorial DAG viewport, not as a throwaway debug widget.
