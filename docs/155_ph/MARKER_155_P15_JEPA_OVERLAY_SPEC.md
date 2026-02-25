# MARKER_155 P1.5 JEPA Overlay Spec

Date: 2026-02-22
Status: Implemented (Stub Contract Active)
Owners: MCC Backend + UI

## Goal

Add predictive graph evolution without replacing current SCC DAG backend.

Base stack remains:
- L0 raw graph
- L1 SCC condensed DAG
- L2 view graph

New in P1.5:
- L3 predictive overlay (`predicted_edges`) for in-place MCC drill.

---

## MARKER_155.MODE_ARCH.V11.P15.SCOPE

### Included now

1. New endpoint: `POST /api/mcc/graph/predict`
2. Deterministic heuristic predictor (JEPA contract stub)
3. Explainable predicted edges with confidence/evidence
4. Mode layer tagging for UI merge (`mode_layer=1`)

### Deferred (P2+)

1. Real JEPA model inference
2. Multimodal predictor adapter (V-JEPA / I-JEPA)
3. Online model feedback loop from accepted/rejected predictions

---

## MARKER_155.MODE_ARCH.V11.P15.API

### Request

```json
{
  "scope_path": "",
  "max_nodes": 600,
  "max_predicted_edges": 120,
  "include_artifacts": false,
  "min_confidence": 0.55
}
```

### Response

```json
{
  "scope_root": "...",
  "base_signature": "...",
  "overlay_signature": "...",
  "generated_at": 1771730000,
  "stats": {
    "base_l2_nodes": 0,
    "base_l2_edges": 0,
    "candidate_edges": 0,
    "predicted_edges": 0,
    "min_confidence": 0.55,
    "max_predicted_edges": 120
  },
  "predicted_edges": [
    {
      "source": "scc_1",
      "target": "scc_2",
      "sourcePort": "out.pred",
      "targetPort": "in.future",
      "type": "predicted",
      "mode_layer": 1,
      "weight": 0.77,
      "confidence": 0.77,
      "evidence": ["layer+1 progression: 2->3", "path_token_overlap=0.640"],
      "is_condensed": true
    }
  ],
  "markers": [
    "MARKER_155.MODE_ARCH.V11.P15",
    "MARKER_155.MODE_ARCH.V11.MODE_OVERLAY",
    "MARKER_155.MODE_ARCH.V11.WHY_EDGE_EXPLAINABILITY"
  ]
}
```

---

## MARKER_155.MODE_ARCH.V11.P15.HEURISTIC_LOGIC

Current predictor (deterministic):

1. Build base graph from `/api/mcc/graph/condensed` contract.
2. Evaluate candidate edges only between adjacent layers (`k -> k+1`).
3. Score by path-token overlap (Jaccard) + same-parent bonus.
4. Penalize oversized SCC nodes to reduce noisy predictions.
5. Return top-N by confidence.

This keeps output stable and testable while model integration is pending.

---

## MARKER_155.MODE_ARCH.V11.P15.UI_MERGE_RULE

UI should merge overlay edges into current graph without scene switch:

1. Keep L2 nodes unchanged.
2. Add `predicted_edges` with dashed style and lower opacity.
3. Show confidence + evidence on hover/click.
4. Toggle layer visibility (`Base`, `Predicted`, `All`).

---

## MARKER_155.MODE_ARCH.V11.P15.ACCEPTANCE

1. Endpoint responds < 1.5s on current repo scope.
2. Returned overlay is deterministic for same base signature.
3. Every predicted edge has evidence and confidence.
4. Overlay contract is JEPA-ready (drop-in model replacement).

---

## MARKER_155.MODE_ARCH.V11.P15.NEXT

P2 steps:

1. Replace heuristic scorer with JEPA adapter.
2. Extend candidates with artifact/chat multimodal relations.
3. Add user feedback channel (`accept/reject prediction`) to improve ranking.
