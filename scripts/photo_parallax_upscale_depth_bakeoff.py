#!/usr/bin/env python3
"""Run Real-ESRGAN x2 -> depth A/B bake-off against native depth outputs."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import subprocess
import sys
import time
import types
from pathlib import Path
from typing import Any


SAMPLE_PRIORS: dict[str, dict[str, float]] = {
    "cassette-closeup": {"x": 0.50, "y": 0.51, "w": 0.48, "h": 0.56},
    "keyboard-hands": {"x": 0.51, "y": 0.58, "w": 0.60, "h": 0.52},
    "drone-portrait": {"x": 0.50, "y": 0.44, "w": 0.42, "h": 0.72},
    "hover-politsia": {"x": 0.53, "y": 0.46, "w": 0.46, "h": 0.48},
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compare native depth vs upscaled->depth.")
    parser.add_argument(
        "--sample-root",
        default="/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/public/samples",
        help="Directory with original sample images.",
    )
    parser.add_argument(
        "--native-depth-root",
        default="/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/output/depth_bakeoff",
        help="Existing native depth bake-off root.",
    )
    parser.add_argument(
        "--native-mask-root",
        default="/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/output/mask_bakeoff",
        help="Existing native mask bake-off root.",
    )
    parser.add_argument(
        "--outdir",
        default="/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/output/upscale_depth_bakeoff",
        help="Output directory for upscale A/B artifacts.",
    )
    parser.add_argument(
        "--checkpoint-path",
        default="/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/checkpoints/realesrgan/RealESRGAN_x2plus.pth",
        help="Real-ESRGAN x2plus checkpoint path.",
    )
    parser.add_argument(
        "--backend",
        action="append",
        dest="backends",
        help="Limit run to one or more depth backends.",
    )
    parser.add_argument(
        "--outscale",
        type=float,
        default=2.0,
        help="Requested output scale for Real-ESRGAN.",
    )
    parser.add_argument(
        "--device",
        default="auto",
        choices=["auto", "cpu", "mps"],
        help="Upscale inference device.",
    )
    parser.add_argument(
        "--skip-upscale",
        action="store_true",
        help="Reuse existing upscaled inputs and rerun only downstream stages.",
    )
    return parser.parse_args()


def save_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def shim_torchvision_for_realesrgan() -> None:
    from torchvision.transforms import functional as F

    if "torchvision.transforms.functional_tensor" in sys.modules:
        return
    module = types.ModuleType("torchvision.transforms.functional_tensor")
    module.rgb_to_grayscale = F.rgb_to_grayscale
    sys.modules["torchvision.transforms.functional_tensor"] = module


def resolve_device(requested: str):
    import torch

    if requested == "cpu":
        return torch.device("cpu")
    if requested == "mps":
        return torch.device("mps")
    if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        return torch.device("mps")
    return torch.device("cpu")


def load_upscaler(checkpoint_path: Path, requested_device: str):
    shim_torchvision_for_realesrgan()

    from basicsr.archs.rrdbnet_arch import RRDBNet
    from realesrgan import RealESRGANer

    device = resolve_device(requested_device)
    model = RRDBNet(num_in_ch=3, num_out_ch=3, scale=2, num_feat=64, num_block=23, num_grow_ch=32)
    upsampler = RealESRGANer(
        scale=2,
        model_path=str(checkpoint_path),
        model=model,
        tile=0,
        tile_pad=10,
        pre_pad=10,
        half=False,
        device=device,
    )
    return upsampler, device


def upscale_samples(sample_root: Path, upscaled_dir: Path, checkpoint_path: Path, outscale: float, requested_device: str) -> dict[str, Any]:
    import numpy as np
    from PIL import Image

    upsampler, device = load_upscaler(checkpoint_path, requested_device)
    entries: list[dict[str, Any]] = []

    for image_path in sorted(path for path in sample_root.iterdir() if path.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"}):
        sample_dir = upscaled_dir
        sample_dir.mkdir(parents=True, exist_ok=True)
        out_path = sample_dir / f"{image_path.stem}.png"

        image = Image.open(image_path).convert("RGB")
        source = np.asarray(image)

        started = time.perf_counter()
        upscaled, _ = upsampler.enhance(source, outscale=outscale)
        elapsed_ms = round((time.perf_counter() - started) * 1000.0, 2)
        Image.fromarray(upscaled).save(out_path)

        entries.append(
            {
                "sample": image_path.name,
                "input_path": str(image_path),
                "output_path": str(out_path),
                "source_width": image.width,
                "source_height": image.height,
                "upscaled_width": int(upscaled.shape[1]),
                "upscaled_height": int(upscaled.shape[0]),
                "elapsed_ms": elapsed_ms,
            }
        )

    summary = {
        "generated_at": dt.datetime.now(dt.UTC).isoformat(),
        "checkpoint_path": str(checkpoint_path),
        "outscale": outscale,
        "device": str(device),
        "entries": entries,
    }
    save_json(upscaled_dir / "upscale_summary.json", summary)
    return summary


def run_subprocess(args: list[str], cwd: Path) -> None:
    subprocess.run(args, cwd=str(cwd), check=True)


def build_box_mask(height: int, width: int, prior: dict[str, float], scale: float) -> "np.ndarray":
    import numpy as np

    x0 = max(0, int((prior["x"] - prior["w"] * scale / 2) * width))
    x1 = min(width, int((prior["x"] + prior["w"] * scale / 2) * width))
    y0 = max(0, int((prior["y"] - prior["h"] * scale / 2) * height))
    y1 = min(height, int((prior["y"] + prior["h"] * scale / 2) * height))
    mask = np.zeros((height, width), dtype=bool)
    mask[y0:y1, x0:x1] = True
    return mask


def load_rgb(path: Path) -> "np.ndarray":
    import numpy as np
    from PIL import Image

    return np.asarray(Image.open(path).convert("RGB"))


def load_depth_resized(path: Path, size: tuple[int, int]) -> "np.ndarray":
    import numpy as np
    from PIL import Image

    image = Image.open(path)
    if image.size != size:
        image = image.resize(size, Image.Resampling.BILINEAR)
    return np.asarray(image, dtype=np.float32) / 65535.0


def gradient_map(array: "np.ndarray") -> "np.ndarray":
    import numpy as np

    gx = np.abs(np.diff(array, axis=1, prepend=array[:, :1]))
    gy = np.abs(np.diff(array, axis=0, prepend=array[:1, :]))
    return gx + gy


def compute_depth_metrics(image_path: Path, depth_path: Path, prior: dict[str, float]) -> dict[str, float]:
    import numpy as np

    rgb = load_rgb(image_path)
    depth = load_depth_resized(depth_path, (rgb.shape[1], rgb.shape[0]))

    gray = rgb.astype(np.float32).mean(axis=2) / 255.0
    image_grad = gradient_map(gray)
    depth_grad = gradient_map(depth)

    edge_threshold = float(np.quantile(image_grad, 0.90))
    edge_mask = image_grad >= edge_threshold
    depth_grad_norm = max(1e-6, float(np.quantile(depth_grad, 0.95)))
    depth_edge_alignment = float(depth_grad[edge_mask].mean() / depth_grad_norm) if edge_mask.any() else 0.0

    focus = build_box_mask(rgb.shape[0], rgb.shape[1], prior, 1.0)
    context = build_box_mask(rgb.shape[0], rgb.shape[1], prior, 1.72)
    ring = context & ~focus

    focus_depth = float(np.median(depth[focus])) if focus.any() else 0.0
    ring_depth = float(np.median(depth[ring])) if ring.any() else 0.0
    focus_separation = abs(focus_depth - ring_depth)
    focus_spread = float(np.quantile(depth[focus], 0.95) - np.quantile(depth[focus], 0.05)) if focus.any() else 0.0

    return {
        "depth_edge_alignment": round(depth_edge_alignment, 5),
        "focus_separation": round(focus_separation, 5),
        "focus_spread": round(focus_spread, 5),
    }


def compare_runs(
    sample_root: Path,
    upscaled_root: Path,
    native_depth_root: Path,
    native_mask_root: Path,
    upscaled_depth_root: Path,
    upscaled_mask_root: Path,
    backends: list[str],
) -> dict[str, Any]:
    entries: list[dict[str, Any]] = []

    for backend in backends:
        for sample_name, prior in SAMPLE_PRIORS.items():
            native_image = next(sample_root.glob(f"{sample_name}.*"), None)
            upscaled_image = upscaled_root / f"{sample_name}.png"
            native_report_path = native_depth_root / backend / sample_name / "report.json"
            native_mask_path = native_mask_root / backend / sample_name / "mask_summary.json"
            upscaled_report_path = upscaled_depth_root / backend / sample_name / "report.json"
            upscaled_mask_path = upscaled_mask_root / backend / sample_name / "mask_summary.json"
            if (
                native_image is None
                or not upscaled_image.exists()
                or not native_report_path.exists()
                or not native_mask_path.exists()
                or not upscaled_report_path.exists()
                or not upscaled_mask_path.exists()
            ):
                continue

            native_report = load_json(native_report_path)
            native_mask = load_json(native_mask_path)
            upscaled_report = load_json(upscaled_report_path)
            upscaled_mask = load_json(upscaled_mask_path)

            native_depth_metrics = compute_depth_metrics(native_image, Path(native_report["depth_master_path"]), prior)
            upscaled_depth_metrics = compute_depth_metrics(native_image, Path(upscaled_report["depth_master_path"]), prior)

            mask_score_delta = round(float(upscaled_mask["best"]["score"] - native_mask["best"]["score"]), 5)
            depth_edge_delta = round(float(upscaled_depth_metrics["depth_edge_alignment"] - native_depth_metrics["depth_edge_alignment"]), 5)
            focus_separation_delta = round(float(upscaled_depth_metrics["focus_separation"] - native_depth_metrics["focus_separation"]), 5)

            entries.append(
                {
                    "backend": backend,
                    "sample": sample_name,
                    "native": {
                        "depth_elapsed_ms": native_report["elapsed_ms"],
                        "mask_best_score": native_mask["best"]["score"],
                        "mask_best_family": native_mask["best"]["method"],
                        **native_depth_metrics,
                    },
                    "upscaled": {
                        "depth_elapsed_ms": upscaled_report["elapsed_ms"],
                        "mask_best_score": upscaled_mask["best"]["score"],
                        "mask_best_family": upscaled_mask["best"]["method"],
                        **upscaled_depth_metrics,
                    },
                    "delta": {
                        "mask_score": mask_score_delta,
                        "depth_edge_alignment": depth_edge_delta,
                        "focus_separation": focus_separation_delta,
                    },
                    "verdict": {
                        "mask_improved": mask_score_delta > 0.05,
                        "mask_degraded": mask_score_delta < -0.05,
                        "depth_edges_improved": depth_edge_delta > 0.02,
                    },
                }
            )

    aggregate: dict[str, Any] = {}
    for backend in backends:
        backend_entries = [entry for entry in entries if entry["backend"] == backend]
        if not backend_entries:
            continue
        aggregate[backend] = {
            "entries": len(backend_entries),
            "mask_improved": sum(1 for entry in backend_entries if entry["verdict"]["mask_improved"]),
            "mask_degraded": sum(1 for entry in backend_entries if entry["verdict"]["mask_degraded"]),
            "depth_edges_improved": sum(1 for entry in backend_entries if entry["verdict"]["depth_edges_improved"]),
            "avg_mask_delta": round(sum(entry["delta"]["mask_score"] for entry in backend_entries) / len(backend_entries), 5),
            "avg_depth_edge_delta": round(sum(entry["delta"]["depth_edge_alignment"] for entry in backend_entries) / len(backend_entries), 5),
            "avg_focus_separation_delta": round(sum(entry["delta"]["focus_separation"] for entry in backend_entries) / len(backend_entries), 5),
        }

    return {"entries": entries, "aggregate": aggregate}


def main() -> int:
    args = parse_args()
    root = Path("/Users/danilagulin/Documents/VETKA_Project/vetka_live_03").resolve()
    sample_root = Path(args.sample_root).expanduser().resolve()
    native_depth_root = Path(args.native_depth_root).expanduser().resolve()
    native_mask_root = Path(args.native_mask_root).expanduser().resolve()
    outdir = Path(args.outdir).expanduser().resolve()
    checkpoint_path = Path(args.checkpoint_path).expanduser().resolve()
    requested_backends = args.backends or ["depth-anything-v2-small", "depth-pro"]

    if not checkpoint_path.exists():
        raise SystemExit(f"Missing checkpoint: {checkpoint_path}. Run ./scripts/photo_parallax_realesrgan_bootstrap.sh first.")

    upscaled_root = outdir / "upscaled_inputs"
    upscaled_depth_root = outdir / "depth_bakeoff"
    upscaled_mask_root = outdir / "mask_bakeoff"

    if not args.skip_upscale:
        upscale_summary = upscale_samples(sample_root, upscaled_root, checkpoint_path, args.outscale, args.device)
    else:
        upscale_summary = load_json(upscaled_root / "upscale_summary.json")

    base_cmd = [sys.executable]
    depth_cmd = base_cmd + [
        str(root / "scripts/photo_parallax_depth_bakeoff.py"),
        "--sample-dir",
        str(upscaled_root),
        "--outdir",
        str(upscaled_depth_root),
    ]
    for backend in requested_backends:
        depth_cmd.extend(["--backend", backend])
    run_subprocess(depth_cmd, cwd=root)

    mask_cmd = base_cmd + [
        str(root / "scripts/photo_parallax_mask_bakeoff.py"),
        "--sample-root",
        str(upscaled_root),
        "--depth-root",
        str(upscaled_depth_root),
        "--outdir",
        str(upscaled_mask_root),
    ]
    for backend in requested_backends:
        mask_cmd.extend(["--backend", backend])
    run_subprocess(mask_cmd, cwd=root)

    comparison = compare_runs(
        sample_root=sample_root,
        upscaled_root=upscaled_root,
        native_depth_root=native_depth_root,
        native_mask_root=native_mask_root,
        upscaled_depth_root=upscaled_depth_root,
        upscaled_mask_root=upscaled_mask_root,
        backends=requested_backends,
    )

    summary = {
        "generated_at": dt.datetime.now(dt.UTC).isoformat(),
        "sample_root": str(sample_root),
        "native_depth_root": str(native_depth_root),
        "native_mask_root": str(native_mask_root),
        "outdir": str(outdir),
        "backends": requested_backends,
        "upscale": upscale_summary,
        **comparison,
    }
    save_json(outdir / "upscale_depth_bakeoff_summary.json", summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
