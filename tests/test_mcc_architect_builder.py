from __future__ import annotations

from pathlib import Path

from src.services.mcc_architect_builder import build_design_dag


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_build_design_dag_returns_contract(tmp_path: Path) -> None:
    # Tiny deterministic project graph.
    _write(tmp_path / "src" / "core.py", "import src.util\n")
    _write(tmp_path / "src" / "util.py", "def util():\n    return 1\n")
    _write(tmp_path / "client" / "app.ts", "import '../src/core.py'\n")

    result = build_design_dag(
        scope_root=str(tmp_path),
        max_nodes=200,
        include_artifacts=False,
        problem_statement="stabilize architecture",
        target_outcome="readable project DAG",
        use_predictive_overlay=True,
        max_predicted_edges=50,
        min_confidence=0.4,
    )

    assert "runtime_graph" in result
    assert "design_graph" in result
    assert "predictive_overlay" in result
    assert "verifier" in result
    assert "markers" in result

    verifier = result["verifier"]
    assert verifier["decision"] in {"pass", "warn", "fail"}
    assert isinstance(verifier.get("acyclic"), bool)
    assert isinstance(verifier.get("monotonic_layers"), bool)
    assert "spectral" in verifier
    assert "lambda2" in verifier["spectral"]
    assert "eigengap" in verifier["spectral"]

    # Architect context must be preserved.
    ctx = result["architect_context"]
    assert ctx["problem_statement"] == "stabilize architecture"
    assert ctx["target_outcome"] == "readable project DAG"


def test_build_design_dag_overlay_toggle(tmp_path: Path) -> None:
    _write(tmp_path / "a.py", "import b\n")
    _write(tmp_path / "b.py", "x = 1\n")

    result = build_design_dag(
        scope_root=str(tmp_path),
        max_nodes=200,
        use_predictive_overlay=False,
    )

    overlay = result["predictive_overlay"]
    assert overlay["stats"]["enabled"] is False
    assert overlay["stats"]["predicted_edges"] == 0
    assert overlay["predicted_edges"] == []
