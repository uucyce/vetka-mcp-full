#!/usr/bin/env python3
"""Phase 157.1 probe: measure ContextPacker trigger/hysteresis on scenarios.

Usage:
  python scripts/context_packer_probe.py --synthetic --runs 40 --output /tmp/jepa_probe.jsonl
  python scripts/context_packer_probe.py --scenarios data/context_probe_scenarios.jsonl
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import random
import sys
import types
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _install_fake_message_utils() -> None:
    fake_message_utils = types.ModuleType("src.api.handlers.message_utils")
    fake_message_utils.build_pinned_context = (
        lambda pinned_files, **_kwargs: "\n".join(
            f"[PINNED] {pf.get('path','')}" for pf in (pinned_files or [])
        )
    )
    fake_message_utils.build_viewport_summary = lambda viewport_context: json.dumps(viewport_context or {})
    fake_message_utils.build_json_context = (
        lambda pinned_files, viewport_context, **_kwargs: json.dumps(
            {"pinned_count": len(pinned_files or []), "viewport": viewport_context or {}}
        )
    )
    sys.modules["src.api.handlers.message_utils"] = fake_message_utils


def _install_fake_jepa_adapter() -> None:
    fake_adapter = types.ModuleType("src.services.mcc_jepa_adapter")

    class _Result:
        provider_mode = "probe-fake-jepa"
        detail = "synthetic"

    fake_adapter.embed_texts_for_overlay = lambda **_kwargs: _Result()
    sys.modules["src.services.mcc_jepa_adapter"] = fake_adapter


def _synthetic_scenarios(runs: int) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for i in range(runs):
        docs = random.choice([2, 4, 8, 16, 24, 40])
        q_len = random.choice([20, 80, 250, 600, 1500, 2800])
        session = "probe-session-a" if i < runs // 2 else "probe-session-b"
        rows.append(
            {
                "session_id": session,
                "model_name": random.choice(["grok-4", "qwen2:7b", "claude-sonnet-4-5"]),
                "query": ("Q " * q_len).strip(),
                "pinned_files": [{"path": f"/tmp/doc_{i}_{k}.md"} for k in range(docs)],
                "viewport_context": {"zoom": random.choice([1, 3, 7]), "visible_nodes": random.randint(5, 50)},
            }
        )
    return rows


def _load_jsonl(path: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if not s:
            continue
        rows.append(json.loads(s))
    return rows


async def _run(scenarios: List[Dict[str, Any]]) -> Dict[str, Any]:
    from src.orchestration.context_packer import ContextPacker

    packer = ContextPacker()
    out_rows: List[Dict[str, Any]] = []
    for row in scenarios:
        result = await packer.pack(
            user_query=str(row.get("query", "")),
            pinned_files=list(row.get("pinned_files", [])),
            viewport_context=dict(row.get("viewport_context", {})),
            session_id=str(row.get("session_id", "default")),
            model_name=str(row.get("model_name", "grok-4")),
            user_id=str(row.get("user_id", "probe")),
            zoom_level=float(row.get("zoom_level", 1.0)),
        )
        out_rows.append(result.trace)
    return {
        "summary": packer.get_recent_stats(limit=len(out_rows)),
        "rows": out_rows,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--synthetic", action="store_true", help="Use generated synthetic scenarios")
    ap.add_argument("--runs", type=int, default=30, help="Synthetic scenario count")
    ap.add_argument("--scenarios", type=str, default="", help="JSONL with scenarios")
    ap.add_argument("--output", type=str, default="", help="Write traces JSONL to path")
    args = ap.parse_args()

    if not args.synthetic and not args.scenarios:
        print("Use --synthetic or --scenarios <file.jsonl>", file=sys.stderr)
        return 2

    _install_fake_message_utils()
    _install_fake_jepa_adapter()
    os.environ.setdefault("VETKA_CONTEXT_PACKER_ENABLED", "true")
    os.environ.setdefault("VETKA_CONTEXT_PACKER_JEPA_ENABLE", "true")

    scenarios = _synthetic_scenarios(args.runs) if args.synthetic else _load_jsonl(Path(args.scenarios))
    result = asyncio.run(_run(scenarios))

    if args.output:
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with out_path.open("w", encoding="utf-8") as f:
            for row in result["rows"]:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")

    print(json.dumps(result["summary"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
