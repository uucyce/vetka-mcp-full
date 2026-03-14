from __future__ import annotations

from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.services.mcc_dag_compare import run_dag_auto_compare


def _sample_records() -> list[dict]:
    return [
        {"id": "root_src", "path": "src", "kind": "dir", "label": "src"},
        {"id": "core", "path": "src/core.py", "kind": "file", "label": "core"},
        {"id": "api", "path": "src/api.py", "kind": "file", "label": "api"},
        {"id": "ui", "path": "client/app.tsx", "kind": "file", "label": "ui"},
    ]


def _sample_relations() -> list[dict]:
    return [
        {"source": "core", "target": "api", "weight": 0.9},
        {"source": "api", "target": "ui", "weight": 0.7},
    ]


def test_auto_compare_array_ranks_variants() -> None:
    out = run_dag_auto_compare(
        project_id="test_project",
        variants=[
            {"name": "v_clean", "max_nodes": 140, "use_predictive_overlay": False},
            {"name": "v_overlay", "max_nodes": 180, "use_predictive_overlay": False},
        ],
        source_kind="array",
        records=_sample_records(),
        relations=_sample_relations(),
        scope_name="array_scope",
        persist_versions=False,
        set_primary_best=False,
    )

    assert out["success"] is True
    assert out["count"] == 2
    assert len(out["variants"]) == 2
    assert "markers" in out
    assert "MARKER_155.ARCHITECT_BUILD.DAG_COMPARE.AUTORUN.V1" in out["markers"]
    assert out["variants"][0]["scorecard"]["score"] >= out["variants"][1]["scorecard"]["score"]


def test_auto_compare_array_persist_and_set_primary(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # Isolate DAG version store for this test.
    from src.services import mcc_dag_versions as dag_versions_module

    monkeypatch.setattr(
        dag_versions_module,
        "DAG_VERSIONS_PATH",
        str(tmp_path / "mcc_dag_versions.json"),
    )

    out = run_dag_auto_compare(
        project_id="project_x",
        variants=[
            {"name": "v1", "max_nodes": 120, "use_predictive_overlay": False},
            {"name": "v2", "max_nodes": 200, "use_predictive_overlay": False},
        ],
        source_kind="array",
        records=_sample_records(),
        relations=_sample_relations(),
        scope_name="array_scope",
        persist_versions=True,
        set_primary_best=True,
    )

    assert out["success"] is True
    assert out["count"] == 2
    assert out["best"]["version_id"]
    assert out["set_primary_best"] is True
    assert out["primary_update"] is not None


def test_auto_compare_rejects_invalid_source_kind() -> None:
    with pytest.raises(ValueError):
        run_dag_auto_compare(
            project_id="p",
            variants=[{"name": "x"}],
            source_kind="invalid",
            records=_sample_records(),
            relations=_sample_relations(),
        )


def test_auto_compare_supports_trm_profiles_and_emits_graph_source() -> None:
    out = run_dag_auto_compare(
        project_id="trm_compare_project",
        variants=[
            {"name": "baseline", "max_nodes": 140, "use_predictive_overlay": False, "trm_profile": "off"},
            {"name": "trm_light", "max_nodes": 140, "use_predictive_overlay": False, "trm_profile": "light", "trm_policy": {"enabled": True, "seed": 11}},
            {"name": "trm_balanced", "max_nodes": 140, "use_predictive_overlay": False, "trm_profile": "balanced", "trm_policy": {"enabled": True, "seed": 11}},
        ],
        source_kind="array",
        records=_sample_records(),
        relations=_sample_relations(),
        scope_name="array_scope",
        persist_versions=False,
        set_primary_best=False,
    )
    assert out["success"] is True
    assert out["count"] == 3
    assert "MARKER_161.TRM.COMPARE.VARIANT_POLICY.V1" in out["markers"]
    assert "MARKER_161.TRM.COMPARE.SCORECARD_EXT.V1" in out["markers"]
    for row in out["variants"]:
        assert row["graph_source"] in {"baseline", "trm_refined"}
        assert isinstance(row.get("trm_meta"), dict)
