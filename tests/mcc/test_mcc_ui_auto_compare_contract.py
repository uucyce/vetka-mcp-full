from __future__ import annotations

import os


ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MCC_FILE = os.path.join(ROOT, "client", "src", "components", "mcc", "MyceliumCommandCenter.tsx")


def _read(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def test_mcc_ui_has_auto_compare_action() -> None:
    code = _read(MCC_FILE)
    assert "auto-compare" in code
    assert "runDagAutoCompare" in code


def test_mcc_ui_calls_auto_compare_endpoint() -> None:
    code = _read(MCC_FILE)
    assert "/mcc/dag-versions/auto-compare" in code
    assert "persist_versions: true" in code


def test_mcc_ui_shows_best_compare_score() -> None:
    code = _read(MCC_FILE)
    assert "best:" in code
    assert "dagCompareBest" in code


def test_mcc_ui_has_compare_matrix_toggle_and_rows() -> None:
    code = _read(MCC_FILE)
    assert "showDagCompareMatrix" in code
    assert "matrix" in code
    assert "variant" in code and "score" in code and "decision" in code
    assert "orph" in code and "dens" in code


def test_mcc_ui_has_promote_best_and_variant_params() -> None:
    code = _read(MCC_FILE)
    assert "promote best" in code
    assert "selectedDagCompareRow" in code
    assert "max_nodes=" in code
    assert "min_conf=" in code
    assert "overlay=" in code
