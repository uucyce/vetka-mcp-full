#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont


ROOT = Path("/Users/danilagulin/Documents/VETKA_Project/vetka_live_03")
DEFAULT_INPUT = ROOT / "photo_parallax_playground/output/layered_edit_flow"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build compare sheets and gate summary for layered AI blend flow.")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--outdir", type=Path, default=None)
    return parser.parse_args()


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def draw_tile(image_path: Path, label: str, note: str, size: tuple[int, int]) -> Image.Image:
    image = Image.open(image_path).convert("RGB").resize(size, Image.Resampling.LANCZOS)
    font = ImageFont.load_default()
    header_h = 52
    tile = Image.new("RGB", (size[0], size[1] + header_h), "#0c0d11")
    tile.paste(image, (0, header_h))
    draw = ImageDraw.Draw(tile)
    draw.text((12, 10), label, fill="#eef2f7", font=font)
    draw.text((12, 28), note, fill="#b7c0ce", font=font)
    return tile


def build_compare_sheet(record: dict[str, Any], sample_dir: Path, out_path: Path) -> None:
    tile_size = (540, 304)
    decision = record["layered"]["gateDecision"]
    delta = record["layered"]["selectionCoverageDelta"]
    before_note = f"selection {record['layered']['selectionCoverageBeforeAi']:.4f}"
    after_note = f"selection {record['layered']['selectionCoverageAfterAi']:.4f} delta {delta:+.4f}"
    tiles = [
        draw_tile(sample_dir / "layered_before_ai.png", "before AI blend", before_note, tile_size),
        draw_tile(sample_dir / "layered_after_ai.png", f"after AI blend ({decision})", after_note, tile_size),
    ]

    canvas = Image.new("RGB", (tile_size[0] * 2, tile_size[1] + 96), "#08090b")
    for index, tile in enumerate(tiles):
        canvas.paste(tile, (index * tile.width, 0))

    draw = ImageDraw.Draw(canvas)
    font = ImageFont.load_default()
    reason = record["layered"]["gateReason"]
    draw.text((14, tile_size[1] + 66), f"sample: {record['sampleId']}  decision: {decision}", fill="#eef2f7", font=font)
    draw.text((14, tile_size[1] + 80), reason, fill="#c9d0db", font=font)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(out_path)


def build_batch_sheet(records: list[dict[str, Any]], out_path: Path) -> None:
    font = ImageFont.load_default()
    tile_size = (420, 236)
    header_h = 66
    rows = max(1, math.ceil(len(records) / 2))
    sheet = Image.new("RGB", (tile_size[0] * 2, rows * (tile_size[1] + header_h)), "#07080b")
    draw = ImageDraw.Draw(sheet)

    for index, record in enumerate(records):
        x = (index % 2) * tile_size[0]
        y = (index // 2) * (tile_size[1] + header_h)
        poster = Image.open(Path(record["files"]["afterAiScreenshot"])).convert("RGB").resize(tile_size, Image.Resampling.LANCZOS)
        sheet.paste(poster, (x, y + header_h))
        decision = record["layered"]["gateDecision"]
        delta = record["layered"]["selectionCoverageDelta"]
        color = "#8fd18e" if decision == "accept" else "#f38b7a" if decision == "reject" else "#f3c86b"
        draw.text((x + 12, y + 10), record["sampleId"], fill="#eef2f7", font=font)
        draw.text((x + 12, y + 28), f"decision={decision}", fill=color, font=font)
        draw.text((x + 12, y + 44), f"delta={delta:+.4f} aiGroups={record['layered']['aiGroupCount']}", fill="#c9d0db", font=font)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out_path)


def aggregate(records: list[dict[str, Any]]) -> dict[str, Any]:
    decision_counts = {"accept": 0, "reject": 0, "keep-manual": 0}
    for record in records:
        decision_counts[record["layered"]["gateDecision"]] += 1

    return {
        "entries": len(records),
        "decision_counts": decision_counts,
        "avg_selection_delta": round(
            sum(float(record["layered"]["selectionCoverageDelta"]) for record in records) / max(1, len(records)),
            5,
        ),
    }


def main() -> None:
    args = parse_args()
    input_dir = args.input
    outdir = args.outdir or input_dir
    summary_path = input_dir / "layered_edit_flow_summary.json"
    records: list[dict[str, Any]] = load_json(summary_path)

    for record in records:
      sample_dir = input_dir / record["sampleId"]
      compare_sheet_path = sample_dir / "layered_gate_compare_sheet.png"
      build_compare_sheet(record, sample_dir, compare_sheet_path)
      record["files"]["gateCompareSheet"] = str(compare_sheet_path)

    batch_sheet_path = outdir / "layered_gate_batch_sheet.png"
    build_batch_sheet(records, batch_sheet_path)

    gate_summary = aggregate(records)
    gate_summary["batch_sheet_path"] = str(batch_sheet_path)

    with (outdir / "layered_gate_summary.json").open("w", encoding="utf-8") as fh:
        json.dump(gate_summary, fh, indent=2)
    with summary_path.open("w", encoding="utf-8") as fh:
        json.dump(records, fh, indent=2)

    print(f"MARKER_180.PARALLAX.LAYERED_GATE.BATCH_SHEET={batch_sheet_path}")
    print(f"MARKER_180.PARALLAX.LAYERED_GATE.SUMMARY={outdir / 'layered_gate_summary.json'}")


if __name__ == "__main__":
    main()
