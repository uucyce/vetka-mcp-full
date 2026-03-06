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


def test_trm_contract_fixture_exposes_build_contract_fields() -> None:
    """
    MARKER_161.TRM.TEST.CONTRACT.V1
    """
    payload = _load_fixture("synthetic_small.json")
    out = build_design_dag_from_arrays(
        records=payload["records"],
        relations=payload["relations"],
        scope_name=payload["scope_name"],
        max_nodes=220,
        trm_profile="off",
        trm_policy={},
    )

    assert out["graph_source"] in {"baseline", "trm_refined"}
    assert isinstance(out.get("trm_meta"), dict)
    assert out["trm_meta"]["status"] in {"disabled", "applied", "rejected", "degraded", "ready"}
    assert out["verifier"]["decision"] in {"pass", "warn", "fail"}
    assert isinstance((out["design_graph"] or {}).get("nodes"), list)
    assert isinstance((out["design_graph"] or {}).get("edges"), list)

