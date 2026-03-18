#!/usr/bin/env python3
"""Build release-level regression summary for gated parallax outputs."""

from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build regression quality summary for parallax release pack.")
    parser.add_argument("--qa-summary", required=True)
    parser.add_argument("--compare-summary", required=True)
    parser.add_argument("--preset-summary", action="append", dest="preset_summaries", required=True)
    parser.add_argument("--outdir", required=True)
    parser.add_argument("--sample", action="append", dest="samples")
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def collect_preset_entries(summary_paths: list[Path]) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]]]:
    preset_entries: dict[str, dict[str, Any]] = {}
    preset_summaries: list[dict[str, Any]] = []
    for summary_path in summary_paths:
        summary = load_json(summary_path)
        preset_name = summary.get("preset") or summary.get("render_settings", {}).get("name") or summary_path.parent.name
        preset_summaries.append(
            {
                "preset": preset_name,
                "summary_path": str(summary_path),
                "overall_status": summary.get("overall_status"),
                "validation_counts": summary.get("validation_counts"),
                "render_settings": summary.get("render_settings"),
            }
        )
        by_sample = {entry["sample"]: entry for entry in summary.get("entries", [])}
        preset_entries[preset_name] = by_sample
    return preset_entries, preset_summaries


def summarize_sample(
    sample_id: str,
    qa_entry: dict[str, Any] | None,
    compare_entry: dict[str, Any] | None,
    preset_entries: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    status = "pass"
    reasons: list[str] = []

    if not qa_entry:
        status = "fail"
        reasons.append("missing gated batch QA entry")
    else:
        qa_status = qa_entry.get("status", "fail")
        if qa_status == "fail":
            status = "fail"
        elif qa_status == "caution" and status != "fail":
            status = "caution"
        reasons.extend(qa_entry.get("reasons", []))

    if not compare_entry:
        status = "fail"
        reasons.append("missing manual vs gated compare evidence")
    else:
        required_evidence = [
            compare_entry.get("sheet_path"),
            compare_entry.get("compare_video_path"),
            compare_entry.get("manual_mid_path"),
            compare_entry.get("qwen_mid_path"),
        ]
        if not all(required_evidence):
            status = "fail"
            reasons.append("manual vs gated compare evidence is incomplete")

    preset_reports: dict[str, Any] = {}
    for preset_name, by_sample in preset_entries.items():
        preset_entry = by_sample.get(sample_id)
        preset_reports[preset_name] = preset_entry
        if not preset_entry:
            status = "fail"
            reasons.append(f"missing {preset_name} preset render summary")
            continue
        preset_status = (preset_entry.get("validation") or {}).get("status", "fail")
        if preset_status == "fail":
            status = "fail"
        elif preset_status == "caution" and status != "fail":
            status = "caution"
        reasons.extend((preset_entry.get("validation") or {}).get("reasons", []))

    deduped_reasons: list[str] = []
    for reason in reasons:
        if reason not in deduped_reasons:
            deduped_reasons.append(reason)

    evidence = {
        "compare_sheet_path": compare_entry.get("sheet_path") if compare_entry else None,
        "compare_video_path": compare_entry.get("compare_video_path") if compare_entry else None,
        "manual_mid_path": compare_entry.get("manual_mid_path") if compare_entry else None,
        "qwen_mid_path": compare_entry.get("qwen_mid_path") if compare_entry else None,
        "manual_preview_path": compare_entry.get("manual_preview_path") if compare_entry else None,
        "qwen_preview_path": compare_entry.get("qwen_preview_path") if compare_entry else None,
    }

    return {
        "sample": sample_id,
        "status": status,
        "reasons": deduped_reasons,
        "qa": qa_entry,
        "compare": compare_entry,
        "preset_renders": preset_reports,
        "evidence": evidence,
    }


def main() -> int:
    args = parse_args()
    qa_summary_path = Path(args.qa_summary).expanduser().resolve()
    compare_summary_path = Path(args.compare_summary).expanduser().resolve()
    preset_summary_paths = [Path(item).expanduser().resolve() for item in args.preset_summaries]
    outdir = Path(args.outdir).expanduser().resolve()
    outdir.mkdir(parents=True, exist_ok=True)
    allowed = set(args.samples or [])

    qa_summary = load_json(qa_summary_path)
    compare_summary = load_json(compare_summary_path)
    preset_entries, preset_summaries = collect_preset_entries(preset_summary_paths)

    qa_by_sample = {entry["sample"]: entry for entry in qa_summary.get("entries", [])}
    compare_by_sample = {entry["sample"]: entry for entry in compare_summary.get("entries", [])}
    sample_ids = sorted(set(qa_by_sample) | set(compare_by_sample))
    if allowed:
        sample_ids = [sample_id for sample_id in sample_ids if sample_id in allowed]

    entries: list[dict[str, Any]] = []
    counts = {"pass": 0, "caution": 0, "fail": 0}
    for sample_id in sample_ids:
        entry = summarize_sample(sample_id, qa_by_sample.get(sample_id), compare_by_sample.get(sample_id), preset_entries)
        counts[entry["status"]] += 1
        entries.append(entry)

    payload = {
        "created_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "qa_summary_path": str(qa_summary_path),
        "compare_summary_path": str(compare_summary_path),
        "preset_summaries": preset_summaries,
        "entries": entries,
        "counts": counts,
        "count": len(entries),
        "overall_status": "fail" if counts["fail"] else ("caution" if counts["caution"] else "pass"),
    }
    out_path = outdir / "regression_quality_summary.json"
    out_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"MARKER_180.PARALLAX.REGRESSION_QUALITY.SUMMARY={out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
