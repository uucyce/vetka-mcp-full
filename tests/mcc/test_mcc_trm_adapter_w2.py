from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.services.mcc_architect_builder import build_design_dag_from_arrays
from src.services.mcc_trm_adapter import propose_trm_candidates


def _records() -> list[dict]:
    return [
        {"id": "root", "path": "src", "kind": "dir", "label": "src"},
        {"id": "api", "path": "src/api/routes/mcc_routes.py", "kind": "file", "label": "api"},
        {"id": "builder", "path": "src/services/mcc_architect_builder.py", "kind": "file", "label": "builder"},
        {"id": "adapter", "path": "src/services/mcc_trm_adapter.py", "kind": "file", "label": "adapter"},
        {"id": "ui", "path": "client/src/components/mcc/MyceliumCommandCenter.tsx", "kind": "file", "label": "ui"},
    ]


def _relations() -> list[dict]:
    return [
        {"source": "builder", "target": "api", "weight": 0.9},
        {"source": "adapter", "target": "builder", "weight": 0.8},
        {"source": "api", "target": "ui", "weight": 0.5},
    ]


def _graphs() -> tuple[dict, dict]:
    out = build_design_dag_from_arrays(
        records=_records(),
        relations=_relations(),
        scope_name="w2_adapter_scope",
        max_nodes=180,
        use_predictive_overlay=False,
    )
    return dict(out.get("runtime_graph") or {}), dict(out.get("design_graph") or {})


def test_trm_adapter_disabled_returns_noop_candidates() -> None:
    """
    MARKER_161.TRM.ADAPTER.ENTRY.V1
    MARKER_161.TRM.ADAPTER.CANDIDATES.V1
    """
    runtime_graph, design_graph = _graphs()
    runtime_before = deepcopy(runtime_graph)
    design_before = deepcopy(design_graph)

    out = propose_trm_candidates(
        runtime_graph=runtime_graph,
        design_graph=design_graph,
        trm_profile="off",
        trm_policy={},
    )

    assert out["status"] == "disabled"
    assert out["profile"] == "off"
    assert out["accepted_count"] == 0
    assert out["candidates"]["edge_rerank"] == []
    assert out["candidates"]["edge_insertions"] == []
    assert out["candidates"]["node_rank_adjustments"] == []
    assert out["candidates"]["root_adjustments"] == []
    assert "MARKER_161.TRM.ADAPTER.FEATURE_BRIDGE.V1" in out["markers"]
    assert runtime_graph == runtime_before
    assert design_graph == design_before


def test_trm_adapter_enabled_is_deterministic() -> None:
    """
    MARKER_161.TRM.ADAPTER.FEATURE_BRIDGE.V1
    MARKER_161.TRM.ADAPTER.CANDIDATES.V1
    """
    runtime_graph, design_graph = _graphs()

    policy = {"enabled": True, "profile": "light", "seed": 7, "max_candidate_edges": 32}
    out1 = propose_trm_candidates(
        runtime_graph=runtime_graph,
        design_graph=design_graph,
        trm_profile="light",
        trm_policy=policy,
    )
    out2 = propose_trm_candidates(
        runtime_graph=runtime_graph,
        design_graph=design_graph,
        trm_profile="light",
        trm_policy=policy,
    )

    assert out1["status"] == "ready"
    assert out1 == out2
    assert out1["features"]["node_count"] > 0
    assert out1["features"]["edge_count"] >= 0
    assert isinstance(out1["candidates"]["edge_rerank"], list)
    assert isinstance(out1["candidates"]["edge_insertions"], list)
    assert isinstance(out1["candidates"]["node_rank_adjustments"], list)
    assert isinstance(out1["candidates"]["root_adjustments"], list)

