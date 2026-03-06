from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.services.mcc_dag_compare import run_dag_auto_compare


FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures" / "trm_golden"


def _load_fixture(name: str) -> dict:
    return json.loads((FIXTURES_DIR / name).read_text(encoding="utf-8"))


def test_trm_compare_profiles_matrix_has_variant_policy_and_meta() -> None:
    """
    MARKER_161.TRM.TEST.COMPARE.V1
    """
    payload = _load_fixture("realish_medium.json")
    out = run_dag_auto_compare(
        project_id="w6_compare_profiles",
        source_kind="array",
        records=payload["records"],
        relations=payload["relations"],
        scope_name=payload["scope_name"],
        persist_versions=False,
        set_primary_best=False,
        variants=[
            {"name": "baseline", "max_nodes": 220, "trm_profile": "off"},
            {"name": "trm_light", "max_nodes": 220, "trm_profile": "light", "trm_policy": {"enabled": True, "seed": 17}},
            {"name": "trm_balanced", "max_nodes": 220, "trm_profile": "balanced", "trm_policy": {"enabled": True, "seed": 17}},
        ],
    )

    assert out["success"] is True
    assert out["count"] == 3
    assert "MARKER_161.TRM.COMPARE.VARIANT_POLICY.V1" in out["markers"]
    assert "MARKER_161.TRM.COMPARE.SCORECARD_EXT.V1" in out["markers"]

    names = {str(v.get("name") or "") for v in out["variants"]}
    assert {"baseline", "trm_light", "trm_balanced"}.issubset(names)
    for row in out["variants"]:
        assert row["graph_source"] in {"baseline", "trm_refined"}
        assert isinstance(row.get("trm_meta"), dict)
        assert isinstance((row.get("scorecard") or {}).get("score"), float | int)

