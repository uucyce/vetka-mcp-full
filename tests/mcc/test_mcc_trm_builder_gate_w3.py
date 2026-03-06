from __future__ import annotations

from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.services.mcc_architect_builder import build_design_dag_from_arrays


def _records() -> list[dict]:
    return [
        {"id": "src", "path": "src", "kind": "dir"},
        {"id": "api", "path": "src/api/routes.py", "kind": "file"},
        {"id": "svc", "path": "src/services/builder.py", "kind": "file"},
        {"id": "ui", "path": "client/src/app.tsx", "kind": "file"},
    ]


def _relations() -> list[dict]:
    return [
        {"source": "svc", "target": "api", "weight": 0.9},
        {"source": "api", "target": "ui", "weight": 0.7},
    ]


def test_w3_builder_gate_applies_safe_trm_candidates(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    MARKER_161.TRM.BUILDER.REFINE_GATE.V1
    """
    import src.services.mcc_architect_builder as builder

    def _mock_candidates(runtime_graph, design_graph, trm_profile, trm_policy):
        edges = list(design_graph.get("edges") or [])
        assert edges
        first = edges[0]
        return {
            "status": "ready",
            "profile": "light",
            "policy": {"enabled": True, "max_refine_steps": 4, "max_candidate_edges": 8, "seed": 7},
            "features": {"node_count": len(design_graph.get("nodes") or []), "edge_count": len(edges)},
            "candidates": {
                "edge_rerank": [
                    {"source": str(first.get("source")), "target": str(first.get("target")), "confidence": 0.91, "reason": "test_rerank"}
                ],
                "edge_insertions": [],
                "node_rank_adjustments": [],
                "root_adjustments": [],
            },
            "accepted_count": 1,
            "markers": [],
        }

    monkeypatch.setattr(builder, "propose_trm_candidates", _mock_candidates)

    out = build_design_dag_from_arrays(
        records=_records(),
        relations=_relations(),
        scope_name="w3_apply_scope",
        trm_profile="light",
        trm_policy={"enabled": True, "max_refine_steps": 4},
    )
    assert out["graph_source"] == "trm_refined"
    assert out["trm_meta"]["applied"] is True
    assert out["trm_meta"]["status"] == "applied"
    assert out["verifier"]["decision"] in {"pass", "warn"}

    edges = out["design_graph"]["edges"]
    assert any(float(e.get("trm_confidence", 0.0)) > 0 for e in edges)


def test_w3_builder_gate_rejects_invalid_candidates_and_rolls_back(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    MARKER_161.TRM.BUILDER.REFINE_GATE.V1
    """
    import src.services.mcc_architect_builder as builder

    def _mock_bad_candidates(runtime_graph, design_graph, trm_profile, trm_policy):
        nodes = list(design_graph.get("nodes") or [])
        assert len(nodes) >= 2
        # Deliberately non-monotonic candidate: from deeper layer to root layer.
        sorted_nodes = sorted(nodes, key=lambda n: int(n.get("layer", 0)))
        low = sorted_nodes[0]
        high = sorted_nodes[-1]
        return {
            "status": "ready",
            "profile": "balanced",
            "policy": {"enabled": True, "max_refine_steps": 4, "max_candidate_edges": 8, "seed": 7},
            "features": {"node_count": len(nodes), "edge_count": len(design_graph.get("edges") or [])},
            "candidates": {
                "edge_rerank": [],
                "edge_insertions": [
                    {"source": str(high.get("id")), "target": str(low.get("id")), "confidence": 0.99, "reason": "bad_monotonic"}
                ],
                "node_rank_adjustments": [],
                "root_adjustments": [],
            },
            "accepted_count": 1,
            "markers": [],
        }

    monkeypatch.setattr(builder, "propose_trm_candidates", _mock_bad_candidates)

    out = build_design_dag_from_arrays(
        records=_records(),
        relations=_relations(),
        scope_name="w3_reject_scope",
        trm_profile="balanced",
        trm_policy={"enabled": True, "max_refine_steps": 4},
    )
    assert out["graph_source"] == "baseline"
    assert out["trm_meta"]["applied"] is False
    assert out["trm_meta"]["status"] == "rejected"
    assert out["verifier"]["decision"] in {"pass", "warn"}

