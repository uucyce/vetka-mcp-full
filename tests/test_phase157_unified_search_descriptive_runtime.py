from __future__ import annotations

from pathlib import Path

import pytest

from src.api.handlers.unified_search import run_unified_search


REPO_ROOT = Path(__file__).resolve().parents[1]
DOCS_ROOT = REPO_ROOT / "docs"


def _doc_exists(name: str) -> bool:
    return any(p.name == name for p in DOCS_ROOT.rglob("*") if p.is_file())


def test_unified_search_auto_adds_file_source_for_descriptive_query() -> None:
    expected = "VETKA_MEMORY_DAG_ABBREVIATIONS_2026-02-22.md"
    if not _doc_exists(expected):
        pytest.skip(f"fixture doc not found: {expected}")

    result = run_unified_search(
        query="Найди файл где все абревиатуры с памятью связано",
        limit=20,
        sources=["semantic"],
        mode="hybrid",
    )

    assert result.get("success") is True
    assert "file" in result.get("sources", [])

    file_rows = result.get("by_source", {}).get("file", [])
    names = {Path(str(row.get("title", ""))).name for row in file_rows}
    assert expected in names
