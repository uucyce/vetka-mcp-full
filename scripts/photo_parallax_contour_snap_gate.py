#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path
from typing import Any


ROOT = Path("/Users/danilagulin/Documents/VETKA_Project/vetka_live_03")
LAYERED_DIR = ROOT / "photo_parallax_playground/output/layered_edit_flow"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Choose base layered mask or contour-snapped mask via an internal gate.")
    parser.add_argument("--input", type=Path, default=LAYERED_DIR)
    parser.add_argument("--min-delta", type=float, default=0.008)
    parser.add_argument("--max-alpha-shift", type=float, default=0.03)
    return parser.parse_args()


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def save_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2)


def choose_variant(report: dict[str, Any], min_delta: float, max_alpha_shift: float) -> tuple[str, str]:
    delta = float(report.get("boundaryScoreDelta", 0.0))
    alpha_shift = abs(float(report.get("alphaMeanDelta", 0.0)))
    decision = report.get("decision", "neutral")

    if decision == "improved" and delta >= min_delta and alpha_shift <= max_alpha_shift:
        return (
            "accept-snapped",
            "Contour snap improved boundary alignment and stayed within the safe alpha shift window.",
        )
    if decision == "regressed":
        return ("keep-base", "Contour snap reduced boundary alignment.")
    if delta < min_delta:
        return ("keep-base", "Contour snap gain is below the internal boundary delta threshold.")
    if alpha_shift > max_alpha_shift:
        return ("keep-base", "Contour snap changed mask area too much for automatic acceptance.")
    return ("keep-base", "Contour snap did not clear the internal accept gate.")


def copy_if_exists(source: str | None, target: Path) -> str | None:
    if not source:
        return None
    source_path = Path(source)
    if not source_path.exists():
        return None
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source_path, target)
    return str(target)


def process_sample(sample_record: dict[str, Any], args: argparse.Namespace) -> dict[str, Any]:
    sample_id = sample_record["sampleId"]
    sample_dir = args.input / sample_id
    contour_report_path = sample_dir / "contour_snap_report.json"
    if not contour_report_path.exists():
        raise FileNotFoundError(f"Missing contour snap report for {sample_id}: {contour_report_path}")

    contour_report = load_json(contour_report_path)
    gate_decision, reason = choose_variant(contour_report, args.min_delta, args.max_alpha_shift)

    use_snapped = gate_decision == "accept-snapped"
    final_mask_source = contour_report["files"]["snappedMask"] if use_snapped else contour_report["files"]["beforeMask"]
    final_overlay_source = contour_report["files"]["snappedOverlay"] if use_snapped else contour_report["files"]["beforeOverlay"]

    final_mask_path = sample_dir / "selection_mask_internal_final.png"
    final_overlay_path = sample_dir / "selection_overlay_internal_final.png"

    copied_mask = copy_if_exists(final_mask_source, final_mask_path)
    copied_overlay = copy_if_exists(final_overlay_source, final_overlay_path)

    record = {
        "sampleId": sample_id,
        "gateDecision": gate_decision,
        "gateReason": reason,
        "variantSelected": "contour-snapped" if use_snapped else "layered-base",
        "boundaryScoreBefore": contour_report.get("boundaryScoreBefore"),
        "boundaryScoreAfter": contour_report.get("boundaryScoreAfter"),
        "boundaryScoreDelta": contour_report.get("boundaryScoreDelta"),
        "alphaMeanDelta": contour_report.get("alphaMeanDelta"),
        "thresholds": {
            "minBoundaryScoreDelta": args.min_delta,
            "maxAlphaMeanShift": args.max_alpha_shift,
        },
        "files": {
            "baseMask": contour_report["files"].get("beforeMask"),
            "snappedMask": contour_report["files"].get("snappedMask"),
            "finalMask": copied_mask,
            "baseOverlay": contour_report["files"].get("beforeOverlay"),
            "snappedOverlay": contour_report["files"].get("snappedOverlay"),
            "finalOverlay": copied_overlay,
            "compareSheet": contour_report["files"].get("compareSheet"),
        },
    }
    save_json(sample_dir / "contour_snap_gate.json", record)
    return record


def aggregate(records: list[dict[str, Any]]) -> dict[str, Any]:
    counts = {"accept-snapped": 0, "keep-base": 0}
    for record in records:
        counts[record["gateDecision"]] += 1
    return {
        "entries": len(records),
        "decision_counts": counts,
        "accepted_rate": round(counts["accept-snapped"] / max(1, len(records)), 5),
        "avg_boundary_score_delta": round(
            sum(float(record["boundaryScoreDelta"]) for record in records) / max(1, len(records)),
            5,
        ),
    }


def main() -> None:
    args = parse_args()
    summary_path = args.input / "layered_edit_flow_summary.json"
    if not summary_path.exists():
        raise FileNotFoundError(f"Missing layered flow summary: {summary_path}")

    sample_records = load_json(summary_path)
    results = [process_sample(record, args) for record in sample_records]
    summary = aggregate(results)
    summary["records"] = results
    save_json(args.input / "contour_snap_gate_summary.json", summary)


if __name__ == "__main__":
    main()
