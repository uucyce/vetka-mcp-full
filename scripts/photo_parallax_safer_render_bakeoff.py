#!/usr/bin/env python3
"""Generate safer reduced-motion preview renders for flagged cases."""

from __future__ import annotations

import argparse
import copy
import datetime as dt
import json
from pathlib import Path
from typing import Any

from photo_parallax_render_preview import render_case
from photo_parallax_subject_plate_bakeoff import save_json


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build reduced-motion preview renders for review-flagged cases.")
    parser.add_argument(
        "--render-review-root",
        default="/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/output/render_review",
        help="Root directory with render review summary.",
    )
    parser.add_argument(
        "--render-preview-root",
        default="/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/output/render_preview",
        help="Root directory with original preview render summary.",
    )
    parser.add_argument(
        "--outdir",
        default="/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/output/render_preview_safer",
        help="Output directory for reduced-motion renders.",
    )
    parser.add_argument(
        "--status",
        action="append",
        dest="statuses",
        choices=("caution", "needs_3_layer"),
        help="Only rerender selected review statuses.",
    )
    parser.add_argument(
        "--backend",
        action="append",
        dest="backends",
        help="Limit run to one or more depth backends.",
    )
    parser.add_argument(
        "--codec",
        default="libx264",
        help="Video codec for preview render.",
    )
    parser.add_argument(
        "--crf",
        type=int,
        default=18,
        help="CRF for preview render.",
    )
    return parser.parse_args()


def load_summary(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def map_render_entries(summary: dict[str, Any]) -> dict[tuple[str, str], dict[str, Any]]:
    return {(entry["backend"], entry["sample"]): entry for entry in summary["entries"]}


def safer_layout(layout: dict[str, Any], status: str) -> tuple[dict[str, Any], dict[str, Any]]:
    camera = copy.deepcopy(layout["camera"])
    reductions = {
        "caution": {"travel": 0.78, "zoom_delta": 0.55},
        "needs_3_layer": {"travel": 0.62, "zoom_delta": 0.35},
    }[status]

    original = copy.deepcopy(camera)
    camera["travel_x_pct"] = round(float(camera["travel_x_pct"]) * reductions["travel"], 2)
    camera["travel_y_pct"] = round(float(camera["travel_y_pct"]) * reductions["travel"], 2)
    zoom_delta = float(camera["zoom"]) - 1.0
    camera["zoom"] = round(1.0 + zoom_delta * reductions["zoom_delta"], 3)
    return {
        **layout,
        "camera": camera,
        "safe_variant": {
            "source_status": status,
            "original_camera": original,
            "reductions": reductions,
        },
    }, {
        "travel_x_delta": round(float(original["travel_x_pct"]) - float(camera["travel_x_pct"]), 2),
        "travel_y_delta": round(float(original["travel_y_pct"]) - float(camera["travel_y_pct"]), 2),
        "zoom_delta": round(float(original["zoom"]) - float(camera["zoom"]), 3),
    }


def main() -> int:
    args = parse_args()
    render_review_root = Path(args.render_review_root).expanduser().resolve()
    render_preview_root = Path(args.render_preview_root).expanduser().resolve()
    outdir = Path(args.outdir).expanduser().resolve()
    requested_statuses = set(args.statuses or ["caution", "needs_3_layer"])
    requested_backends = set(args.backends or [])

    review_summary = load_summary(render_review_root / "render_review_summary.json")
    render_summary = load_summary(render_preview_root / "render_preview_summary.json")
    render_entries = map_render_entries(render_summary)

    reports: list[dict[str, Any]] = []
    for review in review_summary["entries"]:
        if review["status"] not in requested_statuses:
            continue
        if requested_backends and review["backend"] not in requested_backends:
            continue

        base_entry = copy.deepcopy(render_entries[(review["backend"], review["sample"])])
        safe_layout_payload, deltas = safer_layout(base_entry["layout"], review["status"])

        sample_stem = Path(review["sample"]).stem
        case_out_dir = outdir / review["backend"] / sample_stem
        case_out_dir.mkdir(parents=True, exist_ok=True)
        safe_layout_path = case_out_dir / "layout_safe.json"
        save_json(safe_layout_path, safe_layout_payload)

        base_entry["layout"] = safe_layout_payload
        base_entry["subject_rgba_path"] = base_entry["source_subject_rgba_path"]
        base_entry["best"] = {
            "layout_path": str(safe_layout_path),
            "overscan_plate_path": base_entry["source_overscan_plate_path"],
        }

        report = render_case(
            entry=base_entry,
            out_dir=case_out_dir,
            codec=args.codec,
            crf=args.crf,
        )
        report["source_review_status"] = review["status"]
        report["reduction"] = deltas
        save_json(case_out_dir / "render_report_safe.json", report)
        reports.append(report)

    summary = {
        "generated_at": dt.datetime.now(dt.UTC).isoformat(),
        "render_review_root": str(render_review_root),
        "render_preview_root": str(render_preview_root),
        "outdir": str(outdir),
        "entries": reports,
    }
    save_json(outdir / "render_preview_safer_summary.json", summary)
    save_json(outdir / "render_preview_summary.json", summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
