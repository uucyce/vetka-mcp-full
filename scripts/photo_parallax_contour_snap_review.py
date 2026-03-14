#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont


ROOT = Path("/Users/danilagulin/Documents/VETKA_Project/vetka_live_03")
LAYERED_DIR = ROOT / "photo_parallax_playground/output/layered_edit_flow"
SAMPLES_DIR = ROOT / "photo_parallax_playground/public/samples"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run internal RGB contour snap + feather cleanup on layered masks.")
    parser.add_argument("--input", type=Path, default=LAYERED_DIR)
    parser.add_argument("--samples", type=Path, default=SAMPLES_DIR)
    parser.add_argument("--outdir", type=Path, default=None)
    return parser.parse_args()


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def save_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2)


def find_source_image(sample_id: str, samples_dir: Path) -> Path:
    matches = sorted(samples_dir.glob(f"{sample_id}.*"))
    if not matches:
        raise FileNotFoundError(f"Missing source image for {sample_id}")
    return matches[0]


def load_mask_alpha(mask_path: Path, size: tuple[int, int]) -> Image.Image:
    image = Image.open(mask_path)
    if image.mode in {"RGBA", "LA"}:
      alpha = image.getchannel("A")
    else:
      alpha = image.convert("L")
    return alpha.resize(size, Image.Resampling.LANCZOS)


def edge_strength_from_source(source: Image.Image) -> np.ndarray:
    gray = np.asarray(source.convert("L"), dtype=np.float32) / 255.0
    gx = np.zeros_like(gray)
    gy = np.zeros_like(gray)
    gx[:, 1:] = np.abs(gray[:, 1:] - gray[:, :-1])
    gy[1:, :] = np.abs(gray[1:, :] - gray[:-1, :])
    grad = np.sqrt(gx * gx + gy * gy)
    norm = np.percentile(grad, 95) or 1.0
    return np.clip(grad / norm, 0.0, 1.0)


def boundary_band(alpha_image: Image.Image, radius: int = 5) -> np.ndarray:
    dilated = alpha_image.filter(ImageFilter.MaxFilter(radius if radius % 2 == 1 else radius + 1))
    eroded = alpha_image.filter(ImageFilter.MinFilter(radius if radius % 2 == 1 else radius + 1))
    band = np.asarray(dilated, dtype=np.float32) - np.asarray(eroded, dtype=np.float32)
    return np.clip(band / 255.0, 0.0, 1.0)


def contour_snap(source: Image.Image, alpha_image: Image.Image) -> tuple[Image.Image, dict[str, float]]:
    alpha = np.asarray(alpha_image, dtype=np.float32) / 255.0
    edges = edge_strength_from_source(source)
    band = boundary_band(alpha_image, radius=7)

    snapped = alpha.copy()
    band_weight = np.clip(band * (0.55 + edges * 0.9), 0.0, 1.0)
    snapped = np.where(
        band > 0.01,
        np.clip(alpha * (1.0 - band_weight * 0.48) + edges * (band_weight * 0.72), 0.0, 1.0),
        snapped,
    )

    snapped = np.where(alpha > 0.94, 1.0, snapped)
    snapped = np.where(alpha < 0.04, snapped * 0.2, snapped)

    snapped_img = Image.fromarray(np.uint8(np.clip(snapped, 0.0, 1.0) * 255.0), mode="L")
    feathered = snapped_img.filter(ImageFilter.GaussianBlur(radius=1.6))
    feather = np.asarray(feathered, dtype=np.float32) / 255.0
    final = np.maximum(feather * 0.92, alpha * 0.72)
    final = np.where(alpha > 0.97, 1.0, final)
    final = np.clip(final, 0.0, 1.0)

    metrics = {
        "alpha_mean_before": round(float(alpha.mean()), 5),
        "alpha_mean_after": round(float(final.mean()), 5),
    }
    return Image.fromarray(np.uint8(final * 255.0), mode="L"), metrics


def boundary_score(source: Image.Image, alpha_image: Image.Image) -> float:
    edges = edge_strength_from_source(source)
    band = boundary_band(alpha_image, radius=5)
    weight = band > 0.02
    if not np.any(weight):
        return 0.0
    return round(float(edges[weight].mean()), 5)


def composite_overlay(source: Image.Image, alpha_image: Image.Image, color: tuple[int, int, int]) -> Image.Image:
    source_rgba = source.convert("RGBA")
    overlay = Image.new("RGBA", source.size, (*color, 0))
    overlay.putalpha(alpha_image)
    return Image.alpha_composite(source_rgba, overlay).convert("RGB")


def labeled_tile(image: Image.Image, label: str, note: str, size: tuple[int, int]) -> Image.Image:
    tile = image.convert("RGB").resize(size, Image.Resampling.LANCZOS)
    font = ImageFont.load_default()
    header_h = 52
    canvas = Image.new("RGB", (size[0], size[1] + header_h), "#0b0d11")
    canvas.paste(tile, (0, header_h))
    draw = ImageDraw.Draw(canvas)
    draw.text((12, 10), label, fill="#eef2f7", font=font)
    draw.text((12, 28), note, fill="#b9c2ce", font=font)
    return canvas


def make_compare_sheet(
    source: Image.Image,
    before_mask: Image.Image,
    snapped_mask: Image.Image,
    before_overlay: Image.Image,
    snapped_overlay: Image.Image,
    record: dict[str, Any],
    out_path: Path,
) -> None:
    tile_size = (420, 236)
    tiles = [
        labeled_tile(source, "source", record["sampleId"], tile_size),
        labeled_tile(before_mask, "mask before", f"score {record['boundaryScoreBefore']:.5f}", tile_size),
        labeled_tile(snapped_mask, "mask snapped", f"score {record['boundaryScoreAfter']:.5f}", tile_size),
        labeled_tile(before_overlay, "overlay before", f"delta {record['boundaryScoreDelta']:+.5f}", tile_size),
        labeled_tile(snapped_overlay, "overlay snapped", record["decision"], tile_size),
    ]
    width = tile_size[0] * 3
    height = (tile_size[1] + 52) * 2
    sheet = Image.new("RGB", (width, height), "#060709")
    for index, tile in enumerate(tiles):
        x = (index % 3) * tile.width
        y = (index // 3) * tile.height
        sheet.paste(tile, (x, y))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out_path)


def build_batch_sheet(records: list[dict[str, Any]], out_path: Path) -> None:
    tile_size = (420, 236)
    header_h = 68
    rows = max(1, math.ceil(len(records) / 2))
    font = ImageFont.load_default()
    sheet = Image.new("RGB", (tile_size[0] * 2, rows * (tile_size[1] + header_h)), "#07080b")
    draw = ImageDraw.Draw(sheet)

    for index, record in enumerate(records):
        x = (index % 2) * tile_size[0]
        y = (index // 2) * (tile_size[1] + header_h)
        poster = Image.open(Path(record["files"]["snappedOverlay"])).convert("RGB").resize(tile_size, Image.Resampling.LANCZOS)
        sheet.paste(poster, (x, y + header_h))
        color = "#8fd18e" if record["decision"] == "improved" else "#f3c86b" if record["decision"] == "neutral" else "#f38b7a"
        draw.text((x + 12, y + 10), record["sampleId"], fill="#eef2f7", font=font)
        draw.text((x + 12, y + 28), f"decision={record['decision']}", fill=color, font=font)
        draw.text((x + 12, y + 46), f"edge delta={record['boundaryScoreDelta']:+.5f}", fill="#c9d0db", font=font)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out_path)


def review_record(record: dict[str, Any], samples_dir: Path, outdir: Path) -> dict[str, Any]:
    sample_id = record["sampleId"]
    sample_dir = outdir / sample_id
    source_path = find_source_image(sample_id, samples_dir)
    source = Image.open(source_path).convert("RGB")

    before_mask_path = Path(record["files"].get("afterAiMask", sample_dir / "selection_mask_after_ai.png"))
    if not before_mask_path.exists():
        before_mask_path = sample_dir / "selection_mask_after_ai.png"

    before_mask = load_mask_alpha(before_mask_path, source.size)
    snapped_mask, metrics = contour_snap(source, before_mask)

    before_score = boundary_score(source, before_mask)
    after_score = boundary_score(source, snapped_mask)
    delta = round(after_score - before_score, 5)

    alpha_mean_delta = round(metrics["alpha_mean_after"] - metrics["alpha_mean_before"], 5)
    if delta > 0.01 and abs(alpha_mean_delta) <= 0.03:
        decision = "improved"
        reason = "Contour snap increased boundary alignment without a large alpha area shift."
    elif delta < -0.005:
        decision = "regressed"
        reason = "Contour snap reduced boundary alignment."
    else:
        decision = "neutral"
        reason = "Contour snap changed edges, but the gain is too small to call it a clear win."

    before_overlay = composite_overlay(source, before_mask, (242, 126, 44))
    snapped_overlay = composite_overlay(source, snapped_mask, (86, 214, 172))

    sample_dir.mkdir(parents=True, exist_ok=True)
    snapped_mask_path = sample_dir / "selection_mask_contour_snapped.png"
    before_overlay_path = sample_dir / "selection_overlay_before_snap.png"
    snapped_overlay_path = sample_dir / "selection_overlay_contour_snapped.png"
    compare_sheet_path = sample_dir / "contour_snap_compare_sheet.png"

    before_mask.save(sample_dir / "selection_mask_before_snap.png")
    snapped_mask.save(snapped_mask_path)
    before_overlay.save(before_overlay_path)
    snapped_overlay.save(snapped_overlay_path)

    review = {
        "sampleId": sample_id,
        "boundaryScoreBefore": before_score,
        "boundaryScoreAfter": after_score,
        "boundaryScoreDelta": delta,
        "alphaMeanBefore": metrics["alpha_mean_before"],
        "alphaMeanAfter": metrics["alpha_mean_after"],
        "alphaMeanDelta": alpha_mean_delta,
        "decision": decision,
        "reason": reason,
        "files": {
            "source": str(source_path),
            "beforeMask": str(sample_dir / "selection_mask_before_snap.png"),
            "snappedMask": str(snapped_mask_path),
            "beforeOverlay": str(before_overlay_path),
            "snappedOverlay": str(snapped_overlay_path),
            "compareSheet": str(compare_sheet_path),
        },
    }
    make_compare_sheet(source, before_mask, snapped_mask, before_overlay, snapped_overlay, review, compare_sheet_path)
    save_json(sample_dir / "contour_snap_report.json", review)
    return review


def aggregate(records: list[dict[str, Any]]) -> dict[str, Any]:
    decision_counts = {"improved": 0, "neutral": 0, "regressed": 0}
    for record in records:
        decision_counts[record["decision"]] += 1
    return {
        "entries": len(records),
        "decision_counts": decision_counts,
        "avg_boundary_score_delta": round(
            sum(float(record["boundaryScoreDelta"]) for record in records) / max(1, len(records)),
            5,
        ),
    }


def main() -> None:
    args = parse_args()
    input_dir = args.input
    outdir = args.outdir or input_dir
    summary_path = input_dir / "layered_edit_flow_summary.json"
    summary = load_json(summary_path)

    records: list[dict[str, Any]] = []
    for item in summary:
        sample_dir = outdir / item["sampleId"]
        record = review_record(item, args.samples, outdir)
        item.setdefault("files", {})
        item["files"]["contourSnapReport"] = str(sample_dir / "contour_snap_report.json")
        item["files"]["contourSnapCompareSheet"] = record["files"]["compareSheet"]
        item["contourSnap"] = {
            "decision": record["decision"],
            "reason": record["reason"],
            "boundaryScoreBefore": record["boundaryScoreBefore"],
            "boundaryScoreAfter": record["boundaryScoreAfter"],
            "boundaryScoreDelta": record["boundaryScoreDelta"],
            "alphaMeanDelta": record["alphaMeanDelta"],
        }
        records.append(record)

    batch_sheet_path = outdir / "contour_snap_batch_sheet.png"
    build_batch_sheet(records, batch_sheet_path)
    aggregate_summary = aggregate(records)
    aggregate_summary["batch_sheet_path"] = str(batch_sheet_path)

    save_json(outdir / "contour_snap_summary.json", aggregate_summary)
    save_json(summary_path, summary)

    print(f"MARKER_180.PARALLAX.CONTOUR_SNAP.SUMMARY={outdir / 'contour_snap_summary.json'}")
    print(f"MARKER_180.PARALLAX.CONTOUR_SNAP.BATCH_SHEET={batch_sheet_path}")


if __name__ == "__main__":
    main()
