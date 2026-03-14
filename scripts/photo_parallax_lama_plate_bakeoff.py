#!/usr/bin/env python3
"""Run LaMa clean-plate bake-off against the OpenCV baseline."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import time
from pathlib import Path
from typing import Any

from photo_parallax_subject_plate_bakeoff import (
    build_hole_mask,
    candidate_score,
    export_images,
    load_rgb,
    load_selected_mask,
    load_mask,
    make_sheet,
    mask_bbox,
    save_json,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build LaMa clean-plate outputs and compare them to the OpenCV baseline.")
    parser.add_argument(
        "--sample-root",
        default="/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/public/samples",
        help="Directory with original sample images.",
    )
    parser.add_argument(
        "--mask-refine-root",
        default="/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/output/mask_refine_bakeoff",
        help="Root directory of refine outputs.",
    )
    parser.add_argument(
        "--mask-root",
        default="/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/output/mask_bakeoff",
        help="Root directory of coarse mask outputs.",
    )
    parser.add_argument(
        "--baseline-root",
        default="/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/output/subject_plate_bakeoff",
        help="Root directory of the OpenCV subject/plate baseline outputs.",
    )
    parser.add_argument(
        "--outdir",
        default="/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/output/lama_plate_bakeoff",
        help="Output directory for LaMa plate artifacts.",
    )
    parser.add_argument(
        "--model-path",
        default="/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/checkpoints/lama/big-lama.pt",
        help="Local path to the LaMa torchscript model.",
    )
    parser.add_argument(
        "--device",
        default="auto",
        choices=("auto", "mps", "cpu"),
        help="Torch device for LaMa inference.",
    )
    parser.add_argument(
        "--backend",
        action="append",
        dest="backends",
        help="Limit run to one or more depth backends.",
    )
    parser.add_argument(
        "--dilation-size",
        action="append",
        dest="dilation_sizes",
        type=int,
        help="Override one or more hole-mask dilation sizes.",
    )
    return parser.parse_args()


def choose_device(value: str) -> str:
    import torch

    if value == "cpu":
        return "cpu"
    if value == "mps":
        return "mps"
    if torch.backends.mps.is_available():
        return "mps"
    return "cpu"


def load_baseline_summary(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def run_lama_candidate(
    lama: Any,
    source_rgb: "np.ndarray",
    hole_mask: "np.ndarray",
) -> "np.ndarray":
    import numpy as np
    from PIL import Image

    image = Image.fromarray(source_rgb, mode="RGB")
    mask = Image.fromarray((hole_mask.astype("uint8") * 255), mode="L")
    return np.asarray(lama(image, mask).convert("RGB"))


def make_compare_sheet(
    source_rgb: "np.ndarray",
    subject_preview_path: Path,
    baseline_clean_path: Path,
    baseline_hole_overlay_path: Path,
    lama_clean_path: Path,
    lama_hole_overlay_path: Path,
    out_path: Path,
) -> None:
    from PIL import Image

    tiles = [
        Image.fromarray(source_rgb, mode="RGB"),
        Image.open(subject_preview_path).convert("RGB"),
        Image.open(baseline_clean_path).convert("RGB"),
        Image.open(lama_clean_path).convert("RGB"),
        Image.open(baseline_hole_overlay_path).convert("RGB"),
        Image.open(lama_hole_overlay_path).convert("RGB"),
    ]
    width = max(tile.width for tile in tiles)
    height = max(tile.height for tile in tiles)
    sheet = Image.new("RGB", (width * 3, height * 2), "#07080b")
    for index, tile in enumerate(tiles):
        x = (index % 3) * width
        y = (index // 3) * height
        if tile.size != (width, height):
            tile = tile.resize((width, height), Image.Resampling.LANCZOS)
        sheet.paste(tile, (x, y))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out_path)


def comparison_payload(best: dict[str, Any], baseline_summary: dict[str, Any]) -> dict[str, Any]:
    baseline_best = baseline_summary["best"]
    score_delta = round(float(best["score"] - baseline_best["score"]), 5)
    return {
        "baseline_method": baseline_best["method"],
        "baseline_key": baseline_best["key"],
        "baseline_score": baseline_best["score"],
        "baseline_clean_plate_path": baseline_best["clean_plate_path"],
        "baseline_hole_overlay_path": baseline_best["hole_overlay_path"],
        "score_delta_vs_baseline": score_delta,
        "color_gap_delta_vs_baseline": round(float(best["color_gap"] - baseline_best["color_gap"]), 5),
        "grad_gap_delta_vs_baseline": round(float(best["grad_gap"] - baseline_best["grad_gap"]), 5),
        "texture_gap_delta_vs_baseline": round(float(best["texture_gap"] - baseline_best["texture_gap"]), 5),
        "residual_delta_vs_baseline": round(float(best["residual_delta"] - baseline_best["residual_delta"]), 5),
        "hole_area_delta_vs_baseline": round(float(best["hole_area_ratio"] - baseline_best["hole_area_ratio"]), 5),
        "border_touch_delta_vs_baseline": round(float(best["border_touch_ratio"] - baseline_best["border_touch_ratio"]), 5),
        "improved_vs_baseline": score_delta > 0.0,
    }


def run_for_sample(
    sample_path: Path,
    selected_mask_path: Path,
    selected_mask_family: str,
    baseline_summary_path: Path,
    out_dir: Path,
    lama: Any,
    dilation_sizes: list[int],
    device_name: str,
    model_path: Path,
) -> dict[str, Any]:
    from PIL import Image

    source_rgb = load_rgb(sample_path)
    final_mask = load_mask(selected_mask_path)
    baseline_summary = load_baseline_summary(baseline_summary_path)

    candidate_records: list[dict[str, Any]] = []
    best: dict[str, Any] | None = None
    candidate_dir = out_dir / "candidates"
    candidate_dir.mkdir(parents=True, exist_ok=True)

    for dilation_size in dilation_sizes:
        hole_mask = build_hole_mask(final_mask, dilation_size)
        started = time.perf_counter()
        plate_rgb = run_lama_candidate(lama, source_rgb, hole_mask)
        runtime_sec = time.perf_counter() - started
        metrics = candidate_score(plate_rgb, hole_mask, source_rgb)

        candidate_key = f"lama_d{dilation_size}"
        plate_path = candidate_dir / f"{candidate_key}.png"
        hole_path = candidate_dir / f"{candidate_key}_hole.png"

        Image.fromarray(plate_rgb, mode="RGB").save(plate_path)
        Image.fromarray((hole_mask.astype("uint8") * 255), mode="L").save(hole_path)

        record = {
            "key": candidate_key,
            "method": "lama",
            "dilation_size": dilation_size,
            "runtime_sec": round(float(runtime_sec), 5),
            "device": device_name,
            "model_path": str(model_path),
            "plate_path": str(plate_path),
            "hole_mask_path": str(hole_path),
            **metrics,
        }
        candidate_records.append(record)
        if best is None or record["score"] > best["score"]:
            best = {**record, "plate_rgb": plate_rgb, "hole_mask": hole_mask}

    assert best is not None
    export_paths = export_images(source_rgb, final_mask, best["plate_rgb"], best["hole_mask"], out_dir)
    make_sheet(
        source_rgb,
        Path(export_paths["subject_preview"]),
        Path(export_paths["clean_plate"]),
        Path(export_paths["hole_overlay"]),
        Path(export_paths["subject_mask"]),
        Path(export_paths["hole_mask"]),
        out_dir / "subject_plate_debug_sheet.png",
    )

    compare_sheet_path = out_dir / "baseline_vs_lama_debug_sheet.png"
    make_compare_sheet(
        source_rgb=source_rgb,
        subject_preview_path=Path(export_paths["subject_preview"]),
        baseline_clean_path=Path(baseline_summary["best"]["clean_plate_path"]),
        baseline_hole_overlay_path=Path(baseline_summary["best"]["hole_overlay_path"]),
        lama_clean_path=Path(export_paths["clean_plate"]),
        lama_hole_overlay_path=Path(export_paths["hole_overlay"]),
        out_path=compare_sheet_path,
    )

    bbox = mask_bbox(final_mask)
    bbox_values = list(bbox) if bbox is not None else None

    candidate_records.sort(key=lambda item: item["score"], reverse=True)
    compare = comparison_payload(best, baseline_summary)
    summary = {
        "sample": sample_path.name,
        "selected_mask_path": str(selected_mask_path),
        "selected_mask_family": selected_mask_family,
        "baseline_summary_path": str(baseline_summary_path),
        "source_width": int(source_rgb.shape[1]),
        "source_height": int(source_rgb.shape[0]),
        "subject_bbox": bbox_values,
        "subject_area_ratio": round(float(final_mask.mean()), 5),
        "best": {
            "key": best["key"],
            "method": best["method"],
            "dilation_size": best["dilation_size"],
            "score": best["score"],
            "runtime_sec": best["runtime_sec"],
            "device": best["device"],
            "model_path": best["model_path"],
            "subject_rgba_path": export_paths["subject_rgba"],
            "foreground_rgba_path": export_paths["foreground_rgba"],
            "background_rgba_path": export_paths["background_rgba"],
            "subject_trimap_path": export_paths["subject_trimap"],
            "subject_preview_path": export_paths["subject_preview"],
            "subject_mask_path": export_paths["subject_mask"],
            "clean_plate_path": export_paths["clean_plate"],
            "hole_mask_path": export_paths["hole_mask"],
            "hole_overlay_path": export_paths["hole_overlay"],
            "source_cutout_debug_path": export_paths["source_cutout_debug"],
            "debug_sheet_path": str(out_dir / "subject_plate_debug_sheet.png"),
            "compare_sheet_path": str(compare_sheet_path),
            "color_gap": best["color_gap"],
            "grad_gap": best["grad_gap"],
            "texture_gap": best["texture_gap"],
            "residual_delta": best["residual_delta"],
            "hole_area_ratio": best["hole_area_ratio"],
            "border_touch_ratio": best["border_touch_ratio"],
        },
        "comparison": compare,
        "candidates": candidate_records,
    }
    save_json(out_dir / "lama_plate_summary.json", summary)
    return summary


def aggregate_by_backend(entries: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for entry in entries:
        grouped.setdefault(entry["backend"], []).append(entry)

    aggregate: dict[str, dict[str, Any]] = {}
    for backend, rows in grouped.items():
        deltas = [float(row["comparison"]["score_delta_vs_baseline"]) for row in rows]
        runtimes = [float(row["best"]["runtime_sec"]) for row in rows]
        improved = sum(1 for row in rows if row["comparison"]["improved_vs_baseline"])
        aggregate[backend] = {
            "entries": len(rows),
            "improved_vs_baseline": improved,
            "avg_score_delta_vs_baseline": round(sum(deltas) / len(deltas), 5),
            "avg_runtime_sec": round(sum(runtimes) / len(runtimes), 5),
            "best_score_delta_vs_baseline": round(max(deltas), 5),
            "worst_score_delta_vs_baseline": round(min(deltas), 5),
        }
    return aggregate


def main() -> int:
    args = parse_args()
    sample_root = Path(args.sample_root).expanduser().resolve()
    mask_refine_root = Path(args.mask_refine_root).expanduser().resolve()
    mask_root = Path(args.mask_root).expanduser().resolve()
    baseline_root = Path(args.baseline_root).expanduser().resolve()
    outdir = Path(args.outdir).expanduser().resolve()
    model_path = Path(args.model_path).expanduser().resolve()
    requested_backends = set(args.backends or [])
    dilation_sizes = sorted({value for value in (args.dilation_sizes or [11, 21, 31]) if value > 0})

    if not model_path.exists():
        raise FileNotFoundError(f"LaMa model not found: {model_path}")

    import os
    import torch
    from simple_lama_inpainting import SimpleLama

    device_name = choose_device(args.device)
    os.environ["LAMA_MODEL"] = str(model_path)
    lama = SimpleLama(device=torch.device(device_name))

    summaries: list[dict[str, Any]] = []
    for backend_dir in sorted(path for path in mask_root.iterdir() if path.is_dir()):
        if requested_backends and backend_dir.name not in requested_backends:
            continue
        for sample_dir in sorted(path for path in backend_dir.iterdir() if path.is_dir()):
            sample_name = sample_dir.name
            sample_path = next(sample_root.glob(f"{sample_name}.*"), None)
            if sample_path is None:
                continue
            baseline_summary_path = baseline_root / backend_dir.name / sample_name / "subject_plate_summary.json"
            if not baseline_summary_path.exists():
                continue
            selected_mask_path, selected_mask_family = load_selected_mask(
                mask_refine_root,
                mask_root,
                backend_dir.name,
                sample_name,
            )
            summaries.append(
                {
                    "backend": backend_dir.name,
                    **run_for_sample(
                        sample_path=sample_path,
                        selected_mask_path=selected_mask_path,
                        selected_mask_family=selected_mask_family,
                        baseline_summary_path=baseline_summary_path,
                        out_dir=outdir / backend_dir.name / sample_name,
                        lama=lama,
                        dilation_sizes=dilation_sizes,
                        device_name=device_name,
                        model_path=model_path,
                    ),
                }
            )

    summary = {
        "generated_at": dt.datetime.now(dt.UTC).isoformat(),
        "sample_root": str(sample_root),
        "mask_refine_root": str(mask_refine_root),
        "mask_root": str(mask_root),
        "baseline_root": str(baseline_root),
        "outdir": str(outdir),
        "model_path": str(model_path),
        "device": device_name,
        "dilation_sizes": dilation_sizes,
        "aggregate_by_backend": aggregate_by_backend(summaries),
        "entries": summaries,
    }
    save_json(outdir / "lama_plate_bakeoff_summary.json", summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
