from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.services.mcc_architect_builder import build_design_dag_from_arrays


FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures" / "trm_golden"


def _load_fixture(name: str) -> dict:
    return json.loads((FIXTURES_DIR / name).read_text(encoding="utf-8"))


def _topology_signature(out: dict) -> tuple[list[tuple[str, int]], list[tuple[str, str, str]], dict]:
    design = out.get("design_graph") or {}
    nodes = sorted(
        (str(n.get("id") or ""), int(n.get("layer", 0) or 0))
        for n in (design.get("nodes") or [])
    )
    edges = sorted(
        (
            str(e.get("source") or ""),
            str(e.get("target") or ""),
            str(e.get("type") or "structural"),
        )
        for e in (design.get("edges") or [])
    )
    meta = dict(out.get("trm_meta") or {})
    meta_compact = {
        "status": str(meta.get("status") or ""),
        "applied": bool(meta.get("applied")),
        "accepted_count": int(meta.get("accepted_count") or 0),
        "rejected_count": int(meta.get("rejected_count") or 0),
        "profile": str(meta.get("profile") or ""),
    }
    return nodes, edges, meta_compact


def test_trm_determinism_fixed_fixture_seed() -> None:
    """
    MARKER_161.TRM.TEST.DETERMINISM.V1
    """
    payload = _load_fixture("realish_medium.json")
    args = dict(
        records=payload["records"],
        relations=payload["relations"],
        scope_name=payload["scope_name"],
        max_nodes=260,
        trm_profile="balanced",
        trm_policy={"enabled": True, "seed": 77, "max_refine_steps": 6, "max_candidate_edges": 60},
    )
    out1 = build_design_dag_from_arrays(**args)
    out2 = build_design_dag_from_arrays(**args)

    assert _topology_signature(out1) == _topology_signature(out2)
    assert out1["graph_source"] == out2["graph_source"]
    assert out1["verifier"]["decision"] == out2["verifier"]["decision"]

