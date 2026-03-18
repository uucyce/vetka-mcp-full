#!/usr/bin/env python3
"""Build one machine-readable QA summary for gated multi-plate batch outputs."""

from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build QA summary for gated parallax batch outputs.")
    parser.add_argument("--export-root", required=True)
    parser.add_argument("--render-summary", required=True)
    parser.add_argument("--compare-summary", required=True)
    parser.add_argument("--outdir", required=True)
    parser.add_argument("--sample", action="append", dest="samples")
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def summarize_entry(
    sample_id: str,
    readiness: dict[str, Any] | None,
    render_entry: dict[str, Any] | None,
    compare_entry: dict[str, Any] | None,
) -> dict[str, Any]:
    reasons: list[str] = []
    status = "pass"

    if not readiness:
      status = "fail"
      reasons.append("missing readiness diagnostics")
    else:
      if not readiness.get("ready", False):
        status = "fail"
        reasons.append("source readiness never reached")
      if readiness.get("attempts", 0) > 1 and status != "fail":
        status = "caution"
        reasons.append("readiness required more than one poll")
      if readiness.get("assetHydrateCalls", 0) > 0 and status != "fail":
        status = "caution"
        reasons.append("asset hydrate fallback was required")

    if not render_entry:
      status = "fail"
      reasons.append("missing render summary entry")
    else:
      camera_safe = (render_entry.get("camera_safe") or {}).get("ok")
      if camera_safe is False and status != "fail":
        status = "caution"
        reasons.append("camera-safe gate is not fully satisfied")

    if not compare_entry:
      status = "fail"
      reasons.append("missing compare summary entry")

    return {
      "sample": sample_id,
      "status": status,
      "reasons": reasons,
      "readiness": readiness,
      "render": render_entry,
      "compare": compare_entry,
    }


def main() -> int:
    args = parse_args()
    export_root = Path(args.export_root).expanduser().resolve()
    render_summary_path = Path(args.render_summary).expanduser().resolve()
    compare_summary_path = Path(args.compare_summary).expanduser().resolve()
    outdir = Path(args.outdir).expanduser().resolve()
    outdir.mkdir(parents=True, exist_ok=True)

    render_summary = load_json(render_summary_path)
    compare_summary = load_json(compare_summary_path)
    allowed = set(args.samples or [])

    render_by_sample = {entry["sample"]: entry for entry in render_summary.get("entries", [])}
    compare_by_sample = {entry["sample"]: entry for entry in compare_summary.get("entries", [])}

    sample_ids = sorted(set(render_by_sample) | set(compare_by_sample))
    if allowed:
      sample_ids = [sample_id for sample_id in sample_ids if sample_id in allowed]

    entries: list[dict[str, Any]] = []
    counts = {"pass": 0, "caution": 0, "fail": 0}
    for sample_id in sample_ids:
      readiness_path = export_root / sample_id / "plate_export_readiness_diagnostics.json"
      readiness = load_json(readiness_path) if readiness_path.exists() else None
      entry = summarize_entry(
        sample_id=sample_id,
        readiness=readiness,
        render_entry=render_by_sample.get(sample_id),
        compare_entry=compare_by_sample.get(sample_id),
      )
      counts[entry["status"]] += 1
      entries.append(entry)

    payload = {
      "created_at": dt.datetime.now(dt.timezone.utc).isoformat(),
      "export_root": str(export_root),
      "render_summary_path": str(render_summary_path),
      "compare_summary_path": str(compare_summary_path),
      "entries": entries,
      "counts": counts,
      "count": len(entries),
      "overall_status": "fail" if counts["fail"] else "caution" if counts["caution"] else "pass",
    }
    out_path = outdir / "gated_batch_qa_summary.json"
    out_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"MARKER_180.PARALLAX.GATED_BATCH_QA.SUMMARY={out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
