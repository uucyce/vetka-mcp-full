from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.services.mcc_architect_builder import build_design_dag_from_arrays
from src.services.mcc_dag_compare import _score_verifier, run_dag_auto_compare


def _records() -> list[dict]:
    return [
        {"id": "root_src", "path": "src", "kind": "dir", "label": "src"},
        {"id": "svc", "path": "src/services/mcc_architect_builder.py", "kind": "file", "label": "builder"},
        {"id": "cmp", "path": "src/services/mcc_dag_compare.py", "kind": "file", "label": "compare"},
        {"id": "ui", "path": "client/src/hooks/useRoadmapDAG.ts", "kind": "file", "label": "ui"},
    ]


def _relations() -> list[dict]:
    return [
        {"source": "svc", "target": "cmp", "weight": 0.9},
        {"source": "cmp", "target": "ui", "weight": 0.7},
    ]


def test_trm_baseline_verifier_has_spectral_contract() -> None:
    """
    MARKER_161.TRM.TEST.CONTRACT.V1
    """
    out = build_design_dag_from_arrays(
        records=_records(),
        relations=_relations(),
        scope_name="trm_contract_scope",
        max_nodes=180,
        use_predictive_overlay=False,
    )
    verifier = out.get("verifier") or {}
    spectral = verifier.get("spectral") or {}

    assert verifier.get("decision") in {"pass", "warn", "fail"}
    assert isinstance(verifier.get("acyclic"), bool)
    assert isinstance(verifier.get("monotonic_layers"), bool)
    assert isinstance(verifier.get("orphan_rate"), float)
    assert isinstance(verifier.get("density"), float)

    assert spectral.get("status") in {"ok", "warn", "fail"}
    assert isinstance(spectral.get("lambda2"), float)
    assert isinstance(spectral.get("eigengap"), float)
    assert isinstance(spectral.get("component_count"), int)


def test_trm_baseline_topology_is_deterministic_for_same_input() -> None:
    """
    MARKER_161.TRM.TEST.DETERMINISM.V1
    """
    out1 = build_design_dag_from_arrays(
        records=_records(),
        relations=_relations(),
        scope_name="trm_determinism_scope",
        max_nodes=180,
        use_predictive_overlay=False,
    )
    out2 = build_design_dag_from_arrays(
        records=_records(),
        relations=_relations(),
        scope_name="trm_determinism_scope",
        max_nodes=180,
        use_predictive_overlay=False,
    )

    d1 = out1.get("design_graph") or {}
    d2 = out2.get("design_graph") or {}
    nodes1 = sorted((str(n.get("id")), int(n.get("layer", 0))) for n in (d1.get("nodes") or []))
    nodes2 = sorted((str(n.get("id")), int(n.get("layer", 0))) for n in (d2.get("nodes") or []))
    edges1 = sorted((str(e.get("source")), str(e.get("target"))) for e in (d1.get("edges") or []))
    edges2 = sorted((str(e.get("source")), str(e.get("target"))) for e in (d2.get("edges") or []))

    assert nodes1 == nodes2
    assert edges1 == edges2


def test_trm_baseline_score_weights_are_locked() -> None:
    """
    MARKER_161.TRM.TEST.CONTRACT.V1
    Locks current scorecard math as safety baseline before TRM integration.
    """
    perfect = {
        "decision": "pass",
        "acyclic": True,
        "monotonic_layers": True,
        "orphan_rate": 0.0,
        "density": 0.12,
        "spectral": {"status": "ok", "component_count": 1},
    }
    scored = _score_verifier(perfect, node_count=200, edge_count=180)
    assert scored["score"] == 100.0
    assert scored["breakdown"]["decision"] == 30.0
    assert scored["breakdown"]["acyclic"] == 18.0
    assert scored["breakdown"]["monotonic"] == 14.0
    assert scored["breakdown"]["orphan_rate"] == 14.0
    assert scored["breakdown"]["spectral_status"] == 12.0
    assert scored["breakdown"]["components"] == 6.0
    assert scored["breakdown"]["density"] == 6.0
    assert scored["breakdown"]["size"] == 4.0

    warnish = {
        "decision": "warn",
        "acyclic": True,
        "monotonic_layers": True,
        "orphan_rate": 0.5,
        "density": 0.2,
        "spectral": {"status": "warn", "component_count": 2},
    }
    scored_warn = _score_verifier(warnish, node_count=300, edge_count=190)
    assert scored_warn["score"] == 73.2


def test_trm_baseline_compare_includes_verifier_and_spectral() -> None:
    """
    MARKER_161.TRM.TEST.COMPARE.V1
    """
    out = run_dag_auto_compare(
        project_id="trm_test_project",
        variants=[
            {"name": "baseline_a", "max_nodes": 140, "use_predictive_overlay": False},
            {"name": "baseline_b", "max_nodes": 220, "use_predictive_overlay": False},
        ],
        source_kind="array",
        records=_records(),
        relations=_relations(),
        scope_name="trm_compare_scope",
        persist_versions=False,
        set_primary_best=False,
    )
    assert out["success"] is True
    assert out["count"] == 2
    assert out["variants"][0]["scorecard"]["score"] >= out["variants"][1]["scorecard"]["score"]
    for row in out["variants"]:
        verifier = row.get("verifier") or {}
        spectral = verifier.get("spectral") or {}
        assert verifier.get("decision") in {"pass", "warn", "fail"}
        assert spectral.get("status") in {"ok", "warn", "fail"}
