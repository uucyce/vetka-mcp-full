#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
from collections import deque
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image, ImageDraw, ImageFont


ROOT = Path("/Users/danilagulin/Documents/VETKA_Project/vetka_live_03")
LAYERED_DIR = ROOT / "photo_parallax_playground/output/layered_edit_flow"
SAMPLES_DIR = ROOT / "photo_parallax_playground/public/samples"

SAMPLE_SPECS: dict[str, dict[str, Any]] = {
    "cassette-closeup": {
        "goal": "Both hands and the cassette should live in one foreground layer.",
        "target_boxes": [
            {"label": "left-hand", "x": 0.08, "y": 0.45, "width": 0.2, "height": 0.34},
            {"label": "cassette", "x": 0.31, "y": 0.33, "width": 0.36, "height": 0.31},
            {"label": "right-hand", "x": 0.7, "y": 0.39, "width": 0.18, "height": 0.34},
        ],
        "background_boxes": [
            {"label": "top-rig", "x": 0.37, "y": 0.03, "width": 0.28, "height": 0.12},
            {"label": "bottom-left", "x": 0.02, "y": 0.82, "width": 0.18, "height": 0.16},
            {"label": "bottom-right", "x": 0.8, "y": 0.8, "width": 0.18, "height": 0.16},
        ],
    },
    "keyboard-hands": {
        "goal": "Hands and keyboard deck should stay together instead of splitting along perspective lines.",
        "target_boxes": [
            {"label": "left-hand", "x": 0.08, "y": 0.47, "width": 0.18, "height": 0.25},
            {"label": "center-deck", "x": 0.28, "y": 0.48, "width": 0.28, "height": 0.24},
            {"label": "right-keys", "x": 0.54, "y": 0.42, "width": 0.28, "height": 0.27},
        ],
        "background_boxes": [
            {"label": "left-monitor", "x": 0.0, "y": 0.0, "width": 0.28, "height": 0.24},
            {"label": "right-monitor", "x": 0.67, "y": 0.0, "width": 0.33, "height": 0.26},
            {"label": "bottom-corner", "x": 0.0, "y": 0.86, "width": 0.18, "height": 0.14},
        ],
    },
    "hover-politsia": {
        "goal": "Hovercar should be one coherent foreground object without dragging the whole street with it.",
        "target_boxes": [
            {"label": "car-front", "x": 0.49, "y": 0.33, "width": 0.14, "height": 0.13},
            {"label": "car-body", "x": 0.58, "y": 0.36, "width": 0.19, "height": 0.16},
            {"label": "car-lower", "x": 0.54, "y": 0.5, "width": 0.18, "height": 0.12},
        ],
        "background_boxes": [
            {"label": "left-street", "x": 0.03, "y": 0.54, "width": 0.22, "height": 0.24},
            {"label": "top-right-sky", "x": 0.8, "y": 0.0, "width": 0.2, "height": 0.2},
            {"label": "bottom-right-road", "x": 0.78, "y": 0.74, "width": 0.22, "height": 0.2},
        ],
    },
    "drone-portrait": {
        "goal": "The man and the binocular rig should stay in one foreground object against the soft city background.",
        "target_boxes": [
            {"label": "head", "x": 0.29, "y": 0.07, "width": 0.32, "height": 0.25},
            {"label": "torso", "x": 0.24, "y": 0.32, "width": 0.46, "height": 0.39},
            {"label": "binoculars", "x": 0.31, "y": 0.57, "width": 0.22, "height": 0.19},
        ],
        "background_boxes": [
            {"label": "left-bokeh", "x": 0.0, "y": 0.58, "width": 0.18, "height": 0.24},
            {"label": "right-drone", "x": 0.72, "y": 0.16, "width": 0.22, "height": 0.16},
            {"label": "bottom-right-city", "x": 0.78, "y": 0.76, "width": 0.22, "height": 0.2},
        ],
    },
    "punk-rooftop": {
        "goal": "The seated punk figure should remain one foreground object without dragging the whole city with it.",
        "target_boxes": [
            {"label": "head", "x": 0.13, "y": 0.03, "width": 0.2, "height": 0.23},
            {"label": "torso", "x": 0.09, "y": 0.23, "width": 0.27, "height": 0.37},
            {"label": "leg", "x": 0.25, "y": 0.39, "width": 0.22, "height": 0.38},
        ],
        "background_boxes": [
            {"label": "right-city", "x": 0.71, "y": 0.1, "width": 0.27, "height": 0.52},
            {"label": "center-smoke", "x": 0.48, "y": 0.24, "width": 0.15, "height": 0.16},
            {"label": "bottom-right-road", "x": 0.73, "y": 0.72, "width": 0.25, "height": 0.22},
        ],
    },
    "truck-driver": {
        "goal": "The driver, hands and steering wheel should stay together inside the cab frame.",
        "target_boxes": [
            {"label": "head", "x": 0.49, "y": 0.12, "width": 0.19, "height": 0.22},
            {"label": "torso", "x": 0.47, "y": 0.33, "width": 0.24, "height": 0.37},
            {"label": "wheel-hands", "x": 0.22, "y": 0.35, "width": 0.24, "height": 0.31},
        ],
        "background_boxes": [
            {"label": "left-door-frame", "x": 0.0, "y": 0.0, "width": 0.15, "height": 0.84},
            {"label": "rear-truck", "x": 0.0, "y": 0.04, "width": 0.46, "height": 0.25},
            {"label": "right-seat", "x": 0.78, "y": 0.28, "width": 0.2, "height": 0.44},
        ],
    },
}

VARIANTS = {
    "before-ai": "selection_mask_before_ai.png",
    "after-ai": "selection_mask_after_ai.png",
    "internal-final": "selection_mask_internal_final.png",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate whole-object layer cohesion instead of only edge quality.")
    parser.add_argument("--input", type=Path, default=LAYERED_DIR)
    parser.add_argument("--samples", type=Path, default=SAMPLES_DIR)
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


def load_mask(mask_path: Path, size: tuple[int, int]) -> np.ndarray:
    image = Image.open(mask_path)
    if image.mode in {"RGBA", "LA"}:
        image = image.getchannel("A")
    else:
        image = image.convert("L")
    image = image.resize(size, Image.Resampling.LANCZOS)
    return np.asarray(image, dtype=np.float32) / 255.0


def box_slice(box: dict[str, float], width: int, height: int) -> tuple[slice, slice]:
    x0 = max(0, min(width - 1, int(round(box["x"] * width))))
    y0 = max(0, min(height - 1, int(round(box["y"] * height))))
    x1 = max(x0 + 1, min(width, int(round((box["x"] + box["width"]) * width))))
    y1 = max(y0 + 1, min(height, int(round((box["y"] + box["height"]) * height))))
    return slice(y0, y1), slice(x0, x1)


def box_mean(mask: np.ndarray, box: dict[str, float]) -> float:
    sy, sx = box_slice(box, mask.shape[1], mask.shape[0])
    region = mask[sy, sx]
    return float(region.mean()) if region.size else 0.0


def build_union_mask(shape: tuple[int, int], boxes: list[dict[str, float]], pad: float = 0.03) -> np.ndarray:
    height, width = shape
    union = np.zeros((height, width), dtype=bool)
    for box in boxes:
        padded = {
            "x": max(0.0, box["x"] - pad),
            "y": max(0.0, box["y"] - pad),
            "width": min(1.0, box["width"] + pad * 2),
            "height": min(1.0, box["height"] + pad * 2),
        }
        sy, sx = box_slice(padded, width, height)
        union[sy, sx] = True
    return union


def connected_components(binary: np.ndarray) -> list[int]:
    height, width = binary.shape
    seen = np.zeros_like(binary, dtype=bool)
    components: list[int] = []
    for y in range(height):
        for x in range(width):
            if not binary[y, x] or seen[y, x]:
                continue
            q: deque[tuple[int, int]] = deque([(y, x)])
            seen[y, x] = True
            size = 0
            while q:
                cy, cx = q.popleft()
                size += 1
                for ny, nx in ((cy - 1, cx), (cy + 1, cx), (cy, cx - 1), (cy, cx + 1)):
                    if ny < 0 or nx < 0 or ny >= height or nx >= width:
                        continue
                    if not binary[ny, nx] or seen[ny, nx]:
                        continue
                    seen[ny, nx] = True
                    q.append((ny, nx))
            components.append(size)
    components.sort(reverse=True)
    return components


def score_variant(mask: np.ndarray, spec: dict[str, Any]) -> dict[str, Any]:
    target_boxes = spec["target_boxes"]
    background_boxes = spec["background_boxes"]

    target_coverages = [round(box_mean(mask, box), 5) for box in target_boxes]
    background_leaks = [round(box_mean(mask, box), 5) for box in background_boxes]
    hit_threshold = 0.33
    hit_ratio = sum(value >= hit_threshold for value in target_coverages) / max(1, len(target_coverages))

    target_union = build_union_mask(mask.shape, target_boxes, pad=0.035)
    active = mask >= 0.45
    target_active = active & target_union
    target_components = connected_components(target_active)

    component_count = len(target_components)
    largest_component = target_components[0] if target_components else 0
    total_target_active = int(target_active.sum())
    largest_share = largest_component / max(1, total_target_active)
    fragmentation_penalty = max(0, component_count - 1) * 0.16
    spill_penalty = float(np.mean(background_leaks)) * 1.3
    balance_penalty = float(np.std(target_coverages)) * 0.75 if len(target_coverages) > 1 else 0.0
    avg_target_coverage = float(np.mean(target_coverages))

    score = (
        avg_target_coverage * 2.5
        + hit_ratio * 1.9
        + largest_share * 0.9
        - spill_penalty
        - fragmentation_penalty
        - balance_penalty
    )
    score = round(score, 5)

    if hit_ratio >= 1.0 and component_count <= 2 and largest_share >= 0.7 and spill_penalty < 0.18:
        decision = "coherent"
        reason = "Target boxes are covered together with limited spill and low fragmentation."
    elif hit_ratio >= 0.67 and largest_share >= 0.5:
        decision = "partial"
        reason = "Object grouping is usable but still uneven or fragmented."
    else:
        decision = "fragmented"
        reason = "The mask still misses target parts or breaks the object into weak pieces."

    return {
        "score": score,
        "decision": decision,
        "reason": reason,
        "avgTargetCoverage": round(avg_target_coverage, 5),
        "targetBoxHitRatio": round(hit_ratio, 5),
        "targetBoxCoverages": target_coverages,
        "backgroundLeakMean": round(float(np.mean(background_leaks)), 5),
        "backgroundLeaks": background_leaks,
        "componentCount": component_count,
        "largestComponentShare": round(float(largest_share), 5),
        "fragmentationPenalty": round(float(fragmentation_penalty), 5),
        "balancePenalty": round(float(balance_penalty), 5),
    }


def overlay_mask(source: Image.Image, mask: np.ndarray, color: tuple[int, int, int], spec: dict[str, Any]) -> Image.Image:
    rgba = source.convert("RGBA")
    mask_image = Image.fromarray(np.uint8(np.clip(mask, 0.0, 1.0) * 180), mode="L")
    tint = Image.new("RGBA", source.size, (*color, 0))
    tint.putalpha(mask_image)
    composited = Image.alpha_composite(rgba, tint).convert("RGB")
    draw = ImageDraw.Draw(composited)
    for box in spec["target_boxes"]:
        sy, sx = box_slice(box, composited.width, composited.height)
        draw.rectangle((sx.start, sy.start, sx.stop, sy.stop), outline="#8cf3b2", width=2)
    for box in spec["background_boxes"]:
        sy, sx = box_slice(box, composited.width, composited.height)
        draw.rectangle((sx.start, sy.start, sx.stop, sy.stop), outline="#ff907d", width=2)
    return composited


def labeled_tile(image: Image.Image, title: str, note: str, size: tuple[int, int]) -> Image.Image:
    tile = image.convert("RGB").resize(size, Image.Resampling.LANCZOS)
    font = ImageFont.load_default()
    header_h = 54
    canvas = Image.new("RGB", (size[0], size[1] + header_h), "#0b0d11")
    canvas.paste(tile, (0, header_h))
    draw = ImageDraw.Draw(canvas)
    draw.text((12, 10), title, fill="#eef2f7", font=font)
    draw.text((12, 28), note, fill="#b9c2ce", font=font)
    return canvas


def build_compare_sheet(source: Image.Image, sample_goal: str, variant_tiles: list[tuple[str, str, Image.Image]], out_path: Path) -> None:
    tile_size = (400, 226)
    tiles = [labeled_tile(source, "source", sample_goal, tile_size)]
    for title, note, image in variant_tiles:
        tiles.append(labeled_tile(image, title, note, tile_size))
    cols = 2
    rows = math.ceil(len(tiles) / cols)
    sheet = Image.new("RGB", (tile_size[0] * cols, (tile_size[1] + 54) * rows), "#07080b")
    for index, tile in enumerate(tiles):
        x = (index % cols) * tile.width
        y = (index // cols) * tile.height
        sheet.paste(tile, (x, y))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out_path)


def build_batch_sheet(records: list[dict[str, Any]], out_path: Path) -> None:
    tile_size = (400, 226)
    header_h = 68
    rows = max(1, math.ceil(len(records) / 2))
    font = ImageFont.load_default()
    sheet = Image.new("RGB", (tile_size[0] * 2, rows * (tile_size[1] + header_h)), "#07080b")
    draw = ImageDraw.Draw(sheet)

    for index, record in enumerate(records):
        x = (index % 2) * tile_size[0]
        y = (index // 2) * (tile_size[1] + header_h)
        poster = Image.open(Path(record["files"]["compareSheet"])).convert("RGB").resize(tile_size, Image.Resampling.LANCZOS)
        sheet.paste(poster, (x, y + header_h))
        color = "#8fd18e" if record["winnerDecision"] == "coherent" else "#f3c86b" if record["winnerDecision"] == "partial" else "#f38b7a"
        draw.text((x + 12, y + 10), record["sampleId"], fill="#eef2f7", font=font)
        draw.text((x + 12, y + 28), f"winner={record['winnerVariant']}", fill="#c9d0db", font=font)
        draw.text((x + 12, y + 46), f"{record['winnerDecision']} score={record['winnerScore']:.4f}", fill=color, font=font)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out_path)


def review_sample(sample_dir: Path, source_path: Path, spec: dict[str, Any]) -> dict[str, Any]:
    source = Image.open(source_path).convert("RGB")
    variants: list[dict[str, Any]] = []
    variant_tiles: list[tuple[str, str, Image.Image]] = []

    for variant_id, filename in VARIANTS.items():
        path = sample_dir / filename
        if not path.exists():
            continue
        mask = load_mask(path, source.size)
        metrics = score_variant(mask, spec)
        overlay = overlay_mask(source, mask, (82, 227, 196), spec)
        overlay_path = sample_dir / f"object_selection_{variant_id}.png"
        overlay.save(overlay_path)
        variants.append(
            {
                "variant": variant_id,
                "maskPath": str(path),
                "overlayPath": str(overlay_path),
                **metrics,
            }
        )
        variant_tiles.append(
            (
                variant_id,
                f"{metrics['decision']} score {metrics['score']:.4f}",
                overlay,
            )
        )

    if not variants:
        raise FileNotFoundError(f"No mask variants found in {sample_dir}")

    winner = max(variants, key=lambda item: item["score"])
    compare_path = sample_dir / "object_selection_compare_sheet.png"
    build_compare_sheet(source, spec["goal"], variant_tiles, compare_path)

    return {
        "sampleId": sample_dir.name,
        "goal": spec["goal"],
        "winnerVariant": winner["variant"],
        "winnerDecision": winner["decision"],
        "winnerScore": winner["score"],
        "variants": variants,
        "files": {
            "source": str(source_path),
            "compareSheet": str(compare_path),
        },
    }


def aggregate(records: list[dict[str, Any]]) -> dict[str, Any]:
    winner_counts: dict[str, int] = {}
    decision_counts = {"coherent": 0, "partial": 0, "fragmented": 0}
    for record in records:
        winner_counts[record["winnerVariant"]] = winner_counts.get(record["winnerVariant"], 0) + 1
        decision_counts[record["winnerDecision"]] += 1
    return {
        "entries": len(records),
        "winner_counts": winner_counts,
        "winner_decision_counts": decision_counts,
        "avg_winner_score": round(sum(float(record["winnerScore"]) for record in records) / max(1, len(records)), 5),
    }


def main() -> None:
    args = parse_args()
    records: list[dict[str, Any]] = []
    for sample_id, spec in SAMPLE_SPECS.items():
        sample_dir = args.input / sample_id
        if not sample_dir.exists():
            continue
        source_path = find_source_image(sample_id, args.samples)
        record = review_sample(sample_dir, source_path, spec)
        save_json(sample_dir / "object_selection_report.json", record)
        records.append(record)

    summary = aggregate(records)
    summary["records"] = records
    batch_sheet_path = args.input / "object_selection_batch_sheet.png"
    build_batch_sheet(records, batch_sheet_path)
    summary["batch_sheet_path"] = str(batch_sheet_path)
    save_json(args.input / "object_selection_summary.json", summary)


if __name__ == "__main__":
    main()
