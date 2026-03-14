from __future__ import annotations

import json
import os
import time
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.services.mcc_architect_builder import build_design_dag
from src.services.mcc_dag_compare import _score_verifier


def _bool_env(name: str, default: bool = False) -> bool:
    raw = str(os.getenv(name, "")).strip().lower()
    if not raw:
        return default
    return raw in {"1", "true", "yes", "on"}


def _run_variant(scope_root: str, *, use_predictive_overlay: bool, max_nodes: int) -> dict:
    started = time.perf_counter()
    out = build_design_dag(
        scope_root=scope_root,
        max_nodes=max_nodes,
        include_artifacts=False,
        problem_statement="Architect requested to build readable project DAG.",
        target_outcome="Stable architecture DAG for planning/drill.",
        use_predictive_overlay=use_predictive_overlay,
        max_predicted_edges=120,
        min_confidence=0.55,
    )
    elapsed = time.perf_counter() - started

    design = out.get("design_graph") or {}
    verifier = out.get("verifier") or {}
    overlay = out.get("predictive_overlay") or {}
    nodes = design.get("nodes") or []
    edges = design.get("edges") or []
    score = _score_verifier(verifier, node_count=len(nodes), edge_count=len(edges))

    return {
        "duration_sec": round(elapsed, 4),
        "node_count": len(nodes),
        "edge_count": len(edges),
        "decision": str(verifier.get("decision") or ""),
        "spectral": verifier.get("spectral") or {},
        "score": score,
        "overlay_enabled": bool((overlay.get("stats") or {}).get("enabled", False)),
        "overlay_predicted_edges": int((overlay.get("stats") or {}).get("predicted_edges", 0) or 0),
        "markers": list(out.get("markers") or []),
    }


@pytest.mark.integration
def test_real_repo_benchmark_architect_dag_pipeline() -> None:
    """
    MARKER_161.TRM.TEST.REAL_REPO_BENCH.V1

    Real-repo benchmark harness:
    - scenario: "Architect: build DAG"
    - source: current VETKA codebase
    - compare: predictive overlay off vs on (JEPA-path capable)
    - TRM: reserved slot in report (pending integration)
    """
    if not _bool_env("MCC_REAL_REPO_BENCH", False):
        pytest.skip("Set MCC_REAL_REPO_BENCH=1 to run real-repo DAG benchmark.")

    scope_root = str(Path(os.getenv("MCC_REAL_REPO_SCOPE", str(ROOT))).resolve())
    assert os.path.isdir(scope_root), f"Invalid benchmark scope: {scope_root}"

    max_nodes = int(os.getenv("MCC_REAL_REPO_MAX_NODES", "320"))
    max_nodes = max(80, min(max_nodes, 5000))

    baseline = _run_variant(
        scope_root,
        use_predictive_overlay=False,
        max_nodes=max_nodes,
    )
    overlay = _run_variant(
        scope_root,
        use_predictive_overlay=True,
        max_nodes=max_nodes,
    )

    report = {
        "scope_root": scope_root,
        "max_nodes": max_nodes,
        "baseline_no_overlay": baseline,
        "overlay_on_jepa_path": overlay,
        "trm_status": {
            "implemented": False,
            "note": "TRM integration is planned in Phase 161; benchmark slot reserved.",
        },
    }

    out_path = Path(
        os.getenv(
            "MCC_REAL_REPO_BENCH_OUT",
            str(ROOT / "docs" / "161_ph_MCC_TRM" / "TRM_REAL_REPO_BENCH_LATEST.json"),
        )
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    # Safety checks for "architect can build DAG on real repo".
    assert baseline["node_count"] > 0
    assert baseline["edge_count"] > 0
    assert baseline["decision"] in {"pass", "warn", "fail"}
    assert baseline["duration_sec"] > 0
    assert overlay["node_count"] > 0
    assert overlay["edge_count"] > 0
