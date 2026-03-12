#!/usr/bin/env python3
"""Route scenes between two-layer, safe two-layer, and three-layer modes."""

from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont

from photo_parallax_subject_plate_bakeoff import save_json


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build routing decisions from render/mask/layer summaries.")
    parser.add_argument(
        "--sample-root",
        default="/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/public/samples",
        help="Directory with original sample images.",
    )
    parser.add_argument(
        "--render-review-root",
        default="/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/output/render_review",
        help="Root directory with original review summary.",
    )
    parser.add_argument(
        "--render-preview-root",
        default="/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/output/render_preview",
        help="Root directory with original preview summary.",
    )
    parser.add_argument(
        "--render-preview-safer-root",
        default="/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/output/render_preview_safer",
        help="Root directory with safer preview summary.",
    )
    parser.add_argument(
        "--three-layer-root",
        default="/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/output/three_layer_plan",
        help="Root directory with three-layer plan summary.",
    )
    parser.add_argument(
        "--render-preview-3layer-root",
        default="/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/output/render_preview_3layer",
        help="Root directory with three-layer preview summary.",
    )
    parser.add_argument(
        "--outdir",
        default="/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/output/mode_routing_review",
        help="Output directory for routing review artifacts.",
    )
    return parser.parse_args()


def load_summary(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def map_entries(entries: list[dict[str, Any]]) -> dict[tuple[str, str], dict[str, Any]]:
    return {(entry["backend"], entry["sample"]): entry for entry in entries}


def decision_for(
    review: dict[str, Any],
    safe: dict[str, Any] | None,
    plan: dict[str, Any] | None,
    render3: dict[str, Any] | None,
) -> tuple[str, str, dict[str, Any]]:
    status = review["status"]
    if status == "two_layer_ok":
        return "two_layer", "original review already passed", {"confidence": "high"}

    if plan is None:
        return "safe_two_layer" if safe else "two_layer", "three-layer plan missing", {"confidence": "low"}

    cluster_gap = float(plan["depth"]["cluster_gap"])
    mid_ratio = float(plan["metrics"]["midground_area_ratio"])
    safe_edge = None
    if safe:
        safe_edge = abs(float(safe["reduction"]["travel_x_delta"])) + abs(float(safe["reduction"]["travel_y_delta"]))

    if status == "caution":
        if cluster_gap >= 0.28 and mid_ratio >= 0.14 and render3:
            return "three_layer", "caution scene has usable midground separation", {"confidence": "medium"}
        return "safe_two_layer", "caution scene benefits more from reduced motion than weak layer split", {
            "confidence": "medium",
            "safe_edge_reduction": round(safe_edge or 0.0, 3),
        }

    if cluster_gap >= 0.12 and mid_ratio >= 0.08 and render3:
        return "three_layer", "needs_3_layer scene has sufficient separability for three-layer render", {
            "confidence": "high" if cluster_gap >= 0.2 else "medium",
        }
    return "three_layer_low_confidence", "scene still requires three layers, but depth separability is weak", {
        "confidence": "low",
    }


def fit_tile(path: Path | None, size: tuple[int, int], label: str) -> Image.Image:
    tile = Image.new("RGB", size, "#202020")
    draw = ImageDraw.Draw(tile)
    font = ImageFont.load_default()
    if path and path.exists():
        image = Image.open(path).convert("RGB")
        image.thumbnail((size[0], size[1] - 16))
        tile.paste(image, ((size[0] - image.width) // 2, (size[1] - 16 - image.height) // 2))
    else:
        draw.text((12, size[1] // 2 - 6), "n/a", fill="#9b9486", font=font)
    draw.text((10, size[1] - 14), label, fill="#f5f1e6", font=font)
    return tile


def build_sheet(
    source_path: Path,
    two_layer_poster: Path,
    safe_poster: Path | None,
    three_layer_poster: Path | None,
    title: str,
    subtitle: str,
) -> Image.Image:
    tile_w = 300
    tile_h = 190
    margin = 16
    font = ImageFont.load_default()
    canvas = Image.new("RGB", (margin * 5 + tile_w * 4, 60 + margin * 3 + tile_h), "#111111")
    draw = ImageDraw.Draw(canvas)
    draw.text((margin, 12), title, fill="#f5f1e6", font=font)
    draw.text((margin, 28), subtitle, fill="#b0aa9b", font=font)
    tiles = [
        fit_tile(source_path, (tile_w, tile_h), "source"),
        fit_tile(two_layer_poster, (tile_w, tile_h), "2-layer"),
        fit_tile(safe_poster, (tile_w, tile_h), "safe 2-layer"),
        fit_tile(three_layer_poster, (tile_w, tile_h), "3-layer"),
    ]
    for index, tile in enumerate(tiles):
        x = margin + index * (tile_w + margin)
        y = 60
        canvas.paste(tile, (x, y))
    return canvas


def main() -> int:
    args = parse_args()
    sample_root = Path(args.sample_root).expanduser().resolve()
    render_review_root = Path(args.render_review_root).expanduser().resolve()
    render_preview_root = Path(args.render_preview_root).expanduser().resolve()
    render_preview_safer_root = Path(args.render_preview_safer_root).expanduser().resolve()
    three_layer_root = Path(args.three_layer_root).expanduser().resolve()
    render_preview_3layer_root = Path(args.render_preview_3layer_root).expanduser().resolve()
    outdir = Path(args.outdir).expanduser().resolve()

    review_entries = load_summary(render_review_root / "render_review_summary.json")["entries"]
    preview_entries = map_entries(load_summary(render_preview_root / "render_preview_summary.json")["entries"])
    safer_entries = map_entries(load_summary(render_preview_safer_root / "render_preview_summary.json")["entries"])
    plan_entries = map_entries(load_summary(three_layer_root / "three_layer_plan_summary.json")["entries"])
    render3_entries = map_entries(load_summary(render_preview_3layer_root / "render_preview_3layer_summary.json")["entries"])

    decisions: list[dict[str, Any]] = []
    counts: dict[str, int] = {}
    batch_tiles: list[Image.Image] = []

    for review in review_entries:
        key = (review["backend"], review["sample"])
        preview = preview_entries[key]
        safe = safer_entries.get(key)
        plan = plan_entries.get(key)
        render3 = render3_entries.get(key)
        mode, reason, extra = decision_for(review, safe, plan, render3)
        counts[mode] = counts.get(mode, 0) + 1

        source_path = sample_root / review["sample"]
        case_out = outdir / review["backend"] / Path(review["sample"]).stem
        case_out.mkdir(parents=True, exist_ok=True)
        sheet = build_sheet(
            source_path=source_path,
            two_layer_poster=Path(preview["poster_path"]),
            safe_poster=Path(safe["poster_path"]) if safe else None,
            three_layer_poster=Path(render3["poster_path"]) if render3 else None,
            title=f"{review['backend']} / {review['sample']}",
            subtitle=f"{review['status']} -> {mode} | {reason}",
        )
        sheet_path = case_out / "mode_routing_sheet.png"
        sheet.save(sheet_path)
        batch_tiles.append(sheet.resize((420, int(sheet.height * 420 / sheet.width))))

        decision = {
            "backend": review["backend"],
            "sample": review["sample"],
            "source_status": review["status"],
            "recommended_mode": mode,
            "reason": reason,
            "sheet_path": str(sheet_path),
            "source_two_layer_preview_path": preview["preview_path"],
            "source_safe_preview_path": safe["preview_path"] if safe else None,
            "source_three_layer_preview_path": render3["preview_path"] if render3 else None,
            "metrics": {
                "review_score": review["review_score"],
                "edge_margin_px": review["edge_margin_px"],
                "cluster_gap": plan["depth"]["cluster_gap"] if plan else None,
                "midground_area_ratio": plan["metrics"]["midground_area_ratio"] if plan else None,
            },
            **extra,
        }
        save_json(case_out / "mode_routing_decision.json", decision)
        decisions.append(decision)

    if batch_tiles:
        width = max(tile.width for tile in batch_tiles)
        height = sum(tile.height for tile in batch_tiles) + 16 * (len(batch_tiles) + 1)
        batch = Image.new("RGB", (width + 32, height), "#0f0f10")
        y = 16
        for tile in batch_tiles:
            batch.paste(tile, (16, y))
            y += tile.height + 16
        batch_path = outdir / "mode_routing_batch_sheet.png"
        batch.save(batch_path)
    else:
        batch_path = outdir / "mode_routing_batch_sheet.png"

    summary = {
        "generated_at": dt.datetime.now(dt.UTC).isoformat(),
        "outdir": str(outdir),
        "counts": counts,
        "batch_sheet_path": str(batch_path),
        "entries": decisions,
    }
    save_json(outdir / "mode_routing_summary.json", summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
