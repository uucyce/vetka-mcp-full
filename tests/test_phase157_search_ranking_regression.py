from __future__ import annotations

from pathlib import Path

import pytest

from src.search.file_search_service import search_files


REPO_ROOT = Path(__file__).resolve().parents[1]
DOCS_ROOT = REPO_ROOT / "docs"


def _names(results: dict) -> list[str]:
    return [Path(str(r.get("path", ""))).name for r in results.get("results", [])]


def _assert_exists(name: str) -> None:
    if not any(p.name == name for p in DOCS_ROOT.rglob("*")):
        pytest.skip(f"fixture doc not found: {name}")


def test_filename_intent_exact_match_prioritized() -> None:
    expected = "input_matrix_idea.txt"
    _assert_exists(expected)

    out = search_files(expected, limit=10, mode="filename")

    assert out["success"] is True
    assert out.get("intent") == "name_like"
    names = _names(out)
    assert names, "no search results"
    assert names[0] == expected


def test_filename_intent_marker_exact_match_prioritized() -> None:
    expected = "MARKER_157_ABBREVIATIONS_RUNTIME_MAP_2026-03-01.md"
    _assert_exists(expected)

    out = search_files(expected, limit=10, mode="keyword")

    assert out["success"] is True
    assert out.get("intent") == "name_like"
    names = _names(out)
    assert expected in names[:3]


def test_descriptive_intent_returns_memory_abbreviations_doc() -> None:
    expected = "VETKA_MEMORY_DAG_ABBREVIATIONS_2026-02-22.md"
    _assert_exists(expected)

    out = search_files(
        "Найди файл где все абревиатуры с памятью связано",
        limit=15,
        mode="keyword",
    )

    assert out["success"] is True
    assert out.get("intent") == "descriptive"
    names = _names(out)
    assert expected in names[:5]


def test_descriptive_intent_returns_input_matrix_related_set() -> None:
    expected = {
        "input_matrix_idea.txt",
        "MARKER_155_INPUT_MATRIX_SCANNER_CONTRACT.md",
    }
    for name in expected:
        _assert_exists(name)

    out = search_files(
        "Найди файл где все матрицы инпутов, не помню как точно называется",
        limit=20,
        mode="keyword",
    )

    assert out["success"] is True
    assert out.get("intent") == "descriptive"
    top = set(_names(out)[:10])
    assert expected.issubset(top)
