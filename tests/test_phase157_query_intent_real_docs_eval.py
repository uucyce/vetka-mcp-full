"""
Phase 157 preliminary real-docs evaluation for descriptive query search.

Purpose:
- Build a reproducible benchmark before implementing intent-gated JEPA search.
- Evaluate current baseline (file_search + hybrid_search) on real user-like queries.

Run manually:
  VETKA_DEBUG_QUERY_EVAL=1 pytest -q tests/test_phase157_query_intent_real_docs_eval.py -s

Optional env:
  VETKA_DEBUG_QUERY_EVAL_OUT=/tmp/vetka_phase157_query_eval.json
"""

from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
from typing import Any, Dict, List

import pytest

from src.search.file_search_service import search_files
from src.search.hybrid_search import get_hybrid_search


def _scenarios() -> List[Dict[str, Any]]:
    # Real user-style descriptive queries + expected docs from current docs corpus.
    return [
        {
            "query": "Найди файл где все абревиатуры с памятью связано",
            "expected_any": [
                "VETKA_MEMORY_DAG_ABBREVIATIONS_2026-02-22.md",
            ],
            "related_patterns": ["ABBREVIATIONS", "MEMORY", "RUNTIME_MAP"],
            "expected_intent": "descriptive",
        },
        {
            "query": "Найди файл где все матрицы инпутов, не помню как точно называется",
            "expected_any": [
                "input_matrix_idea.txt",
                "MARKER_155_INPUT_MATRIX_SCANNER_CONTRACT.md",
            ],
            "related_patterns": ["INPUT_MATRIX", "MATRIX", "SCANNER_CONTRACT"],
            "expected_intent": "descriptive",
        },
        {
            "query": "Где документ с runtime map аббревиатур по фазе 157",
            "expected_any": [
                "MARKER_157_ABBREVIATIONS_RUNTIME_MAP_2026-03-01.md",
            ],
            "related_patterns": ["157", "RUNTIME_MAP", "ABBREVIATIONS"],
            "expected_intent": "descriptive",
        },
        {
            "query": "Нужен документ анализ интеграции памяти CAM ARC ELISION",
            "expected_any": [
                "MEMORY_INTEGRATION_ANALYSIS.md",
                "MEMORY_SYSTEMS_SUMMARY.md",
            ],
            "related_patterns": ["MEMORY", "ARC", "ELISION", "CAM"],
            "expected_intent": "descriptive",
        },
        {
            "query": "Найди стрим док по GROK для выбора инструментов модели",
            "expected_any": [
                "stream_GROK.txt",
            ],
            "related_patterns": ["GROK", "stream", "tool", "search"],
            "expected_intent": "descriptive",
        },
    ]


def _basename(path_like: str) -> str:
    return Path(path_like or "").name


def _collect_paths_from_results(results: List[Dict[str, Any]]) -> List[str]:
    out: List[str] = []
    for item in results or []:
        p = str(item.get("path") or item.get("title") or item.get("url") or "")
        if p:
            out.append(p)
    return out


def _intent_heuristic(query: str) -> str:
    q = (query or "").lower().strip()
    words = [w for w in q.split() if w]
    file_like = any(x in q for x in [".md", ".txt", ".py", "/", "\\", "marker_"])
    desc_markers = [
        "найди файл где",
        "не помню",
        "документ с",
        "нужен документ",
        "про ",
    ]
    if (len(words) >= 6 and not file_like) or any(m in q for m in desc_markers):
        return "descriptive"
    return "name_like"


def _find_expected_hits(paths: List[str], expected_any: List[str]) -> Dict[str, Any]:
    names = [_basename(p).lower() for p in paths]
    expected_l = [e.lower() for e in expected_any]
    matched = [e for e in expected_any if e.lower() in names]
    return {
        "expected_count": len(expected_any),
        "matched_count": len(matched),
        "matched": matched,
        "hit_any": len(matched) > 0,
    }


def _related_hits(paths: List[str], patterns: List[str]) -> int:
    all_text = " ".join(paths).lower()
    count = 0
    for p in patterns:
        if p.lower() in all_text:
            count += 1
    return count


@pytest.mark.skipif(
    os.getenv("VETKA_DEBUG_QUERY_EVAL", "0") != "1",
    reason="Manual real-docs benchmark (set VETKA_DEBUG_QUERY_EVAL=1)",
)
def test_phase157_pre_impl_query_eval_real_docs() -> None:
    root = Path(__file__).resolve().parents[1]
    docs_root = root / "docs"
    assert docs_root.exists(), "docs/ not found"

    scenarios = _scenarios()
    # Validate target docs exist (benchmark integrity).
    docs_set = {p.name for p in docs_root.rglob("*") if p.is_file()}
    for sc in scenarios:
        assert any(name in docs_set for name in sc["expected_any"]), (
            f"No expected docs exist for query: {sc['query']}"
        )

    hs = get_hybrid_search()

    report_rows: List[Dict[str, Any]] = []
    for sc in scenarios:
        q = sc["query"]
        keyword_res = search_files(q, limit=25, mode="keyword")
        filename_res = search_files(q, limit=25, mode="filename")
        hybrid_res = asyncio.run(hs.search(q, limit=25, mode="hybrid", skip_cache=True))

        keyword_paths = _collect_paths_from_results(keyword_res.get("results", []))
        filename_paths = _collect_paths_from_results(filename_res.get("results", []))
        hybrid_paths = _collect_paths_from_results(hybrid_res.get("results", []))

        combined = []
        seen = set()
        for p in keyword_paths + filename_paths + hybrid_paths:
            b = _basename(p).lower()
            if b in seen:
                continue
            seen.add(b)
            combined.append(p)

        hits = _find_expected_hits(combined, sc["expected_any"])
        row = {
            "query": q,
            "intent_expected": sc["expected_intent"],
            "intent_heuristic": _intent_heuristic(q),
            "expected_any": sc["expected_any"],
            "hit_any": hits["hit_any"],
            "matched": hits["matched"],
            "related_hits": _related_hits(combined[:20], sc["related_patterns"]),
            "keyword_count": keyword_res.get("count", 0),
            "filename_count": filename_res.get("count", 0),
            "hybrid_count": hybrid_res.get("count", 0),
            "keyword_took_ms": keyword_res.get("took_ms", 0),
            "filename_took_ms": filename_res.get("took_ms", 0),
            "hybrid_timing_ms": hybrid_res.get("timing_ms", 0),
            "top10": [_basename(p) for p in combined[:10]],
        }
        report_rows.append(row)

    hit_rate = sum(1 for r in report_rows if r["hit_any"]) / max(1, len(report_rows))
    summary = {
        "scenario_count": len(report_rows),
        "hit_rate_any": round(hit_rate, 4),
        "descriptive_queries": sum(1 for r in report_rows if r["intent_heuristic"] == "descriptive"),
        "rows": report_rows,
    }

    out = Path(os.getenv("VETKA_DEBUG_QUERY_EVAL_OUT", "/tmp/vetka_phase157_query_eval.json"))
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    print("\n[PHASE157 PRE-IMPL QUERY EVAL] summary:", json.dumps(summary, ensure_ascii=False))
    print("[PHASE157 PRE-IMPL QUERY EVAL] report:", str(out))

    # Pre-implementation sanity only: benchmark generated and heuristic consistent.
    assert len(report_rows) >= 5
    assert all(r["intent_expected"] == "descriptive" for r in report_rows)
