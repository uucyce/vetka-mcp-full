"""
Manual debug test for Phase 157.1 context packing on REAL docs corpus.

This test is for local calibration of trigger/hysteresis and latency metrics.
It is intentionally skipped by default.

Run:
  VETKA_DEBUG_REAL_DOCS=1 pytest -q tests/test_phase157_context_packer_real_docs_debug.py -s

Optional:
  VETKA_DEBUG_METRICS_OUT=/tmp/vetka_phase157_real_docs_metrics.jsonl
  VETKA_DEBUG_DOCS_LIMIT=200
"""

from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
from typing import Any, Dict, List

import pytest

from src.orchestration.context_packer import ContextPacker


def _collect_docs(limit: int) -> List[str]:
    root = Path(__file__).resolve().parents[1]
    docs_dir = root / "docs"
    if not docs_dir.exists():
        return []

    exts = {".md", ".txt", ".rtf", ".json", ".yaml", ".yml"}
    items: List[str] = []
    for p in docs_dir.rglob("*"):
        if not p.is_file():
            continue
        if p.suffix.lower() not in exts:
            continue
        try:
            rel = p.relative_to(root)
        except Exception:
            continue
        items.append(str(rel))
        if len(items) >= limit:
            break
    return items


def _pinned(paths: List[str]) -> List[Dict[str, Any]]:
    return [{"path": p, "name": Path(p).name, "type": "file"} for p in paths]


@pytest.mark.skipif(
    os.getenv("VETKA_DEBUG_REAL_DOCS", "0") != "1",
    reason="Manual debug test (set VETKA_DEBUG_REAL_DOCS=1)",
)
def test_phase157_context_packer_real_docs_metrics_dump() -> None:
    docs_limit = int(os.getenv("VETKA_DEBUG_DOCS_LIMIT", "160"))
    docs = _collect_docs(docs_limit)
    assert docs, "No docs files found for real-corpus debug run"

    packer = ContextPacker()
    session_id = "phase157-real-docs-debug"

    # Gradient sequence: ramp up docs + query size, then cool down.
    scenario_sizes = [6, 10, 14, 18, 24, 30, 40, 55, 75, 55, 30, 12]
    traces: List[Dict[str, Any]] = []

    for i, size in enumerate(scenario_sizes):
        chunk = docs[:size]
        query = (
            "Сделай сжатую выжимку по архитектуре памяти CAM ARC ELISION JEPA, "
            "выдели риски, зависимости, конфликтующие зоны и следующие шаги. "
            + ("Контекст: " + ("важно " * (size * 10)))
        )
        res = asyncio.run(
            packer.pack(
                user_query=query,
                pinned_files=_pinned(chunk),
                viewport_context={"zoom": 6 if size >= 20 else 2, "visible_nodes": min(size, 80)},
                session_id=session_id,
                model_name="claude-sonnet-4-5",
                user_id="debug",
                zoom_level=6.0 if size >= 20 else 2.0,
            )
        )
        row = {
            "scenario_idx": i,
            "docs_count": size,
            "jepa_context_preview": (res.jepa_context[:180] if res.jepa_context else ""),
            **res.trace,
        }
        traces.append(row)

    out_path = Path(os.getenv("VETKA_DEBUG_METRICS_OUT", "/tmp/vetka_phase157_real_docs_metrics.jsonl"))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        for row in traces:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    stats = packer.get_recent_stats(limit=100)
    print("\n[PHASE157 REAL DOCS] summary:", json.dumps(stats, ensure_ascii=False))
    print("[PHASE157 REAL DOCS] metrics file:", str(out_path))

    # Sanity checks: trace shape and at least one raw trigger on larger scenarios.
    assert all("jepa_trigger_raw" in t for t in traces)
    assert any(t["docs_count"] > packer.docs_threshold and t["jepa_trigger_raw"] for t in traces)
    assert "pack_latency_ms_p95" in stats
