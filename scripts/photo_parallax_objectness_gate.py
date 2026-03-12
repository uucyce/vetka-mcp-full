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
    parser = argparse.ArgumentParser(description="Choose the mask variant that best preserves a whole object as one layer.")
    parser.add_argument("--input", type=Path, default=LAYERED_DIR)
    parser.add_argument("--prefer-coherent", action="store_true", default=False)
    return parser.parse_args()


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def save_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2)


def decision_rank(decision: str) -> int:
    return {"coherent": 3, "partial": 2, "fragmented": 1}.get(decision, 0)


def choose_variant(record: dict[str, Any], prefer_coherent: bool) -> dict[str, Any]:
    variants = list(record["variants"])
    if prefer_coherent:
        variants.sort(key=lambda item: (decision_rank(item["decision"]), float(item["score"])), reverse=True)
    else:
        variants.sort(key=lambda item: float(item["score"]), reverse=True)
    return variants[0]


def copy_if_exists(source: str | None, target: Path) -> str | None:
    if not source:
        return None
    source_path = Path(source)
    if not source_path.exists():
        return None
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source_path, target)
    return str(target)


def process_record(record: dict[str, Any], base_dir: Path, prefer_coherent: bool) -> dict[str, Any]:
    sample_dir = base_dir / record["sampleId"]
    winner = choose_variant(record, prefer_coherent)
    final_mask_path = sample_dir / "selection_mask_objectness_final.png"
    final_overlay_path = sample_dir / "selection_overlay_objectness_final.png"

    copied_mask = copy_if_exists(winner.get("maskPath"), final_mask_path)
    copied_overlay = copy_if_exists(winner.get("overlayPath"), final_overlay_path)

    result = {
        "sampleId": record["sampleId"],
        "goal": record["goal"],
        "winnerVariant": winner["variant"],
        "winnerDecision": winner["decision"],
        "winnerScore": winner["score"],
        "reason": winner["reason"],
        "files": {
            "compareSheet": record["files"]["compareSheet"],
            "objectnessFinalMask": copied_mask,
            "objectnessFinalOverlay": copied_overlay,
        },
    }
    save_json(sample_dir / "objectness_gate.json", result)
    return result


def aggregate(records: list[dict[str, Any]]) -> dict[str, Any]:
    winner_counts: dict[str, int] = {}
    decision_counts: dict[str, int] = {}
    for record in records:
        winner_counts[record["winnerVariant"]] = winner_counts.get(record["winnerVariant"], 0) + 1
        decision_counts[record["winnerDecision"]] = decision_counts.get(record["winnerDecision"], 0) + 1
    return {
        "entries": len(records),
        "winner_counts": winner_counts,
        "winner_decision_counts": decision_counts,
        "avg_winner_score": round(sum(float(record["winnerScore"]) for record in records) / max(1, len(records)), 5),
    }


def main() -> None:
    args = parse_args()
    summary_path = args.input / "object_selection_summary.json"
    if not summary_path.exists():
        raise FileNotFoundError(f"Missing object selection summary: {summary_path}")
    summary = load_json(summary_path)
    results = [process_record(record, args.input, args.prefer_coherent) for record in summary["records"]]
    aggregate_summary = aggregate(results)
    aggregate_summary["records"] = results
    save_json(args.input / "objectness_gate_summary.json", aggregate_summary)


if __name__ == "__main__":
    main()
