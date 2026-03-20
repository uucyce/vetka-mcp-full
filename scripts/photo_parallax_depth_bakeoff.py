#!/usr/bin/env python3
"""Run depth bake-off on the parallax sandbox sample set."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class BackendSpec:
    slug: str
    model_id: str
    kind: str


BACKENDS: dict[str, BackendSpec] = {
    "depth-anything-v2-small": BackendSpec(
        slug="depth-anything-v2-small",
        model_id="depth-anything/Depth-Anything-V2-Small-hf",
        kind="relative",
    ),
    "depth-pro": BackendSpec(
        slug="depth-pro",
        model_id="apple/DepthPro-hf",
        kind="metric",
    ),
}


def save_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run depth bake-off on still image samples.")
    parser.add_argument(
        "--backend",
        action="append",
        dest="backends",
        help="Backend slug to run. Repeat for multiple backends. Defaults to both.",
    )
    parser.add_argument(
        "--sample-dir",
        default="/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/public/samples",
        help="Directory with sample images.",
    )
    parser.add_argument(
        "--outdir",
        default="/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/output/depth_bakeoff",
        help="Output directory for bake-off artifacts.",
    )
    parser.add_argument(
        "--pred-only",
        action="store_true",
        help="Save only depth outputs and JSON, skip copying source previews.",
    )
    return parser.parse_args()


def load_pipeline(model_id: str):
    from transformers import pipeline

    return pipeline(task="depth-estimation", model=model_id)


def normalize_to_16bit(predicted_depth) -> tuple["np.ndarray", "np.ndarray", dict[str, float]]:
    import numpy as np
    import torch

    if isinstance(predicted_depth, torch.Tensor):
        array = predicted_depth.detach().cpu().squeeze().numpy().astype("float32")
    else:
        array = np.asarray(predicted_depth, dtype="float32")

    minimum = float(array.min())
    maximum = float(array.max())
    spread = max(1e-6, maximum - minimum)
    # Canonical convention for the sandbox is white = near, black = far.
    # The raw model outputs are normalized here once so downstream UI/export/render
    # do not need to guess or invert polarity independently.
    normalized = 1.0 - ((array - minimum) / spread)
    depth16 = (normalized * 65535.0).clip(0, 65535).astype("uint16")
    return array, depth16, {
        "min": round(minimum, 6),
        "max": round(maximum, 6),
        "spread": round(spread, 6),
    }


def normalize_to_preview_minmax(depth16) -> "Image.Image":
    import numpy as np
    from PIL import Image

    preview = (depth16.astype("float32") / 257.0).clip(0, 255).astype("uint8")
    return Image.fromarray(preview, mode="L")


def normalize_to_preview_percentile(array) -> tuple["Image.Image", dict[str, float]]:
    import numpy as np
    from PIL import Image

    p2 = float(np.percentile(array, 2))
    p98 = float(np.percentile(array, 98))
    spread = max(1e-6, p98 - p2)
    normalized = (1.0 - ((array - p2) / spread)).clip(0, 1)
    preview = (normalized * 255.0).astype("uint8")
    return Image.fromarray(preview, mode="L"), {
        "p2": round(p2, 6),
        "p98": round(p98, 6),
        "spread": round(spread, 6),
    }


def run_backend(backend: BackendSpec, image_paths: list[Path], outdir: Path, pred_only: bool) -> dict[str, Any]:
    from PIL import Image

    backend_dir = outdir / backend.slug
    backend_dir.mkdir(parents=True, exist_ok=True)
    pipeline_obj = load_pipeline(backend.model_id)
    results: list[dict[str, Any]] = []

    for image_path in image_paths:
        image = Image.open(image_path).convert("RGB")
        started = time.perf_counter()
        output = pipeline_obj(image)
        elapsed_ms = round((time.perf_counter() - started) * 1000.0, 2)

        predicted_depth = output.get("predicted_depth")
        depth_image = output.get("depth")
        array, depth16, stats = normalize_to_16bit(
            predicted_depth if predicted_depth is not None else depth_image
        )
        preview_minmax = normalize_to_preview_minmax(depth16)
        preview_p2p98, percentile_stats = normalize_to_preview_percentile(array)

        sample_dir = backend_dir / image_path.stem
        sample_dir.mkdir(parents=True, exist_ok=True)
        master_path = sample_dir / "depth_master_16.png"
        preview_path = sample_dir / "depth_preview.png"
        preview_minmax_path = sample_dir / "depth_preview_minmax.png"
        preview_minmax.save(preview_minmax_path)
        preview_p2p98.save(preview_path)
        Image.fromarray(depth16).save(master_path)

        if not pred_only:
            image.save(sample_dir / "source.png")

        sample_result = {
            "sample": image_path.name,
            "backend": backend.slug,
            "model_id": backend.model_id,
            "kind": backend.kind,
            "elapsed_ms": elapsed_ms,
            "source_width": image.width,
            "source_height": image.height,
            "depth_master_path": str(master_path),
            "depth_preview_path": str(preview_path),
            "depth_preview_minmax_path": str(preview_minmax_path),
            "tensor_stats": stats,
            "percentile_stats": percentile_stats,
        }
        save_json(sample_dir / "report.json", sample_result)
        results.append(sample_result)

    return {
        "backend": backend.slug,
        "model_id": backend.model_id,
        "kind": backend.kind,
        "samples": results,
    }


def main() -> int:
    args = parse_args()
    requested = args.backends or list(BACKENDS.keys())
    unknown = [slug for slug in requested if slug not in BACKENDS]
    if unknown:
        raise SystemExit(f"Unknown backends: {', '.join(unknown)}")

    sample_dir = Path(args.sample_dir).expanduser().resolve()
    outdir = Path(args.outdir).expanduser().resolve()
    image_paths = sorted(
        [
            path
            for path in sample_dir.iterdir()
            if path.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"}
        ]
    )
    if not image_paths:
        raise SystemExit(f"No sample images found in {sample_dir}")

    started = time.perf_counter()
    backend_reports = []
    failures = []

    for slug in requested:
        spec = BACKENDS[slug]
        try:
            backend_reports.append(run_backend(spec, image_paths, outdir, args.pred_only))
        except Exception as error:  # pragma: no cover - external model/runtime failures
            failures.append({"backend": slug, "error": str(error)})

    summary = {
        "generated_at": dt.datetime.now(dt.UTC).isoformat(),
        "sample_dir": str(sample_dir),
        "outdir": str(outdir),
        "backends_requested": requested,
        "backends_succeeded": [report["backend"] for report in backend_reports],
        "failures": failures,
        "elapsed_sec": round(time.perf_counter() - started, 2),
        "reports": backend_reports,
    }
    save_json(outdir / "bakeoff_summary.json", summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
