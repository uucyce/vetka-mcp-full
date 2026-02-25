# Mode Architecture v1.1 Addendum (Backend SCC DAG Layer)

Date: 2026-02-22  
Status: Proposed (RECON addendum to v1)
Parent: `/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/docs/155_ph/MODE_ARCHITECTURE_V1.md`

## Purpose

This addendum extends v1 with a strict backend graph pipeline:

`module graph -> SCC condensation DAG -> layered UI graph`

It does **not** replace `input_matrix`; it operationalizes it for stable, readable rendering.

---

## MARKER_155.MODE_ARCH.V11.INPUT_MATRIX_TO_BACKEND

`input_matrix` remains the canonical relation source:

- explicit/import
- temporal
- reference/citation
- semantic

New rule:
- Raw relation graph may contain cycles.
- UI DAG must be produced from SCC-condensed graph, not from raw graph directly.

This gives deterministic readability without discarding relation evidence.

---

## MARKER_155.MODE_ARCH.V11.GRAPH_LEVELS

Three backend graph levels are mandatory.

### L0 Raw Module Graph (analysis graph)

Nodes:
- module/file/package (configurable granularity)

Edges:
- typed edges from `input_matrix`

Properties:
- cycles allowed
- max evidence retained

### L1 SCC Condensed Graph (structural DAG)

Build:
- run Tarjan or Kosaraju on L0
- each SCC -> one supernode

Properties:
- guaranteed DAG
- each supernode keeps member list and cycle metadata

### L2 View Graph (UI contract graph)

Build:
- apply scope filter, budgets, top-k thinning, level policy
- optionally expand selected SCC in-place for drill

Properties:
- readable and bounded graph for MCC
- still traceable to L0 evidence

---

## MARKER_155.MODE_ARCH.V11.CYCLE_POLICY

Cycle policy is explicit:

1. Never silently drop cycle edges in backend truth.
2. Collapse cycle into SCC supernode for base DAG view.
3. Provide drill action: "open SCC internals" in same canvas.
4. Inside SCC drill, allow local non-DAG mini-view with warning badge `CYCLIC`.

This keeps one-window UX while preserving technical truth.

---

## MARKER_155.MODE_ARCH.V11.LAYER_POLICY

After SCC condensation, apply deterministic layering:

1. Topological sort (Kahn or equivalent).
2. Primary rank = longest path from roots.
3. Tie-breakers (stable):
- relation priority score
- node degree
- lexical path

Optional policy mode:
- enforce domain layers (`UI -> App -> Domain -> Infra`).
- cross-layer violations are marked as `violation` edges, not hidden.

---

## MARKER_155.MODE_ARCH.V11.INPUT_OUTPUT_PORT_MODEL

To support vector-style edges (n8n/Comfy intuition), UI node contract adds ports:

- node has `inputs[]` and `outputs[]`
- edge attaches `sourcePort` and `targetPort`
- architecture level can auto-map ports from dependency type
- workflow level allows user/architect edit of port bindings

This removes ambiguous edge routing and makes causality legible.

---

## MARKER_155.MODE_ARCH.V11.ARTIFACT_LAYER

L0 extends beyond code modules and includes runtime artifacts:

- `kind: artifact|chat` from `data/artifacts` and staging metadata
- auto-edges:
- `chat -> artifact` (`contains`)
- temporal links by creation/update time
- semantic links by embedding similarity

Port defaults:

- chat: `out.message`
- artifact image: `in.source_chat`, `out.texture`
- artifact json/log: `in.source_chat`, `out.data`

This prevents "ghost knowledge" where artifacts exist in storage but are absent in graph truth.

---

## MARKER_155.MODE_ARCH.V11.SCC_HEALTH

Each SCC node exposes health metrics for drill safety:

```json
{
  "scc_health": {
    "size": 42,
    "density": 0.8,
    "max_cycle_len": 5,
    "warning": "dense"
  }
}
```

Policy:

- if `scc_size` exceeds budget, use hierarchical in-SCC mini-DAG for first drill view
- show badge `SCC:<size>/<warning>`
- keep explicit toggle to flatten all SCC members

This avoids unusable "fat" supernodes on large cyclic subsystems.

---

## MARKER_155.MODE_ARCH.V11.MODE_OVERLAY

Mode overlays are first-class L2 layers (without scene switch):

- base architecture edges: `mode_layer = 0`
- workflow/MCP overlay edges: `mode_layer = 1`
- overlay edge prefix: `mcp.*` for mode-specific relations

Trigger contract:

- mode producers emit `mcc_graph_updated` with `{ mode, delta_nodes, delta_edges }`
- MCC merges delta into current L2 snapshot in-place

Violations across governance boundaries are marked as `type: violation` and never hidden.

---

## MARKER_155.MODE_ARCH.V11.DATA_CONTRACT_EXT

Extended node contract:

```json
{
  "id": "string",
  "kind": "module|scc|task|agent|artifact",
  "scc_id": "string|null",
  "scc_size": 0,
  "members": ["node_id"],
  "scc_health": {
    "size": 0,
    "density": 0.0,
    "max_cycle_len": 0,
    "warning": "acyclic|singleton|dense"
  },
  "ports": {
    "inputs": ["in.default"],
    "outputs": ["out.default"]
  },
  "layer": 0,
  "scope": "root|folder|file|task|workflow",
  "metadata": {}
}
```

Extended edge contract:

```json
{
  "source": "node_id",
  "target": "node_id",
  "sourcePort": "out.default",
  "targetPort": "in.default",
  "type": "explicit|temporal|reference|semantic|violation|contains",
  "mode_layer": 0,
  "weight": 0.0,
  "confidence": 0.0,
  "evidence": ["string"],
  "is_condensed": false
}
```

---

## MARKER_155.MODE_ARCH.V11.MCC_ONE_WINDOW_RULE

For MCC:

- single canvas only
- drill = camera + dataset transition in-place
- no route-level scene swap for architecture/tasks/workflow
- SCC internals open as overlay subgraph in same canvas

This directly addresses the "new room" cognitive reset issue.

---

## MARKER_155.MODE_ARCH.V11.BACKEND_PIPELINE_STEPS

1. Build L0 module graph from scanner + parser + `input_matrix` relations.
2. Extend L0 with artifact/chat nodes and typed edges.
3. Compute SCC map.
4. Build L1 condensed DAG.
5. Compute SCC health metrics and fallback flags.
6. Apply scope/budget/layer policy -> L2 view graph.
7. Merge mode overlays (`mode_layer`) into L2.
8. Emit explainability bundle for every non-contains edge.
9. Cache by `(project_hash, scope, mode, budget_profile)`.
10. Publish trigger event `mcc_graph_updated` (no fixed polling).

---

## MARKER_155.MODE_ARCH.V11.IMPLEMENTATION_PHASES

### P0 Gate

- freeze UI contract v1.1
- add feature flag `MCC_SCC_DAG_BACKEND`

### P1 Backend Graph Contract

- implement L0 extractor adapter
- add artifact/chat integration into L0
- implement SCC condensation
- implement SCC health metrics
- expose `/api/mcc/graph/condensed`

### P2 LOD Render Binding

- bind MCC architecture LOD to L2 graph
- deterministic camera fit for root/folder/file

### P3 Node Windows + Explainability

- node mini/full windows for model/stats/messages
- edge "Why" panel uses evidence bundle

### P4 Orchestration / Merge

- merge task/workflow overlays with architecture DAG
- add MCP mode overlays with `mode_layer`
- trigger-based sync only

---

## MARKER_155.MODE_ARCH.V11.ACCEPTANCE

1. Large projects no longer flatten into unreadable horizontal train by default.
2. Any cycle is visible as SCC (and drillable), never hidden.
3. Every rendered edge has source evidence.
4. Same snapshot -> same SCC DAG layout (deterministic).
5. MCC updates by triggers (`mcc_graph_updated`, task/pipeline events), not interval polling.

---

## MARKER_155.MODE_ARCH.V11.NOTES

Perplexity research is aligned with this addendum in one key point:
- SCC condensation is the mathematically correct bridge between real dependency graphs and a readable DAG UI.

In VETKA terms:
- `input_matrix` defines relation truth,
- SCC DAG defines renderable structure,
- MCC LOD/drill defines human navigation.
