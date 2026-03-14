#!/usr/bin/env python3
"""Generate synthetic guided hint overlays for sandbox samples."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


SAMPLE_PRIORS: dict[str, dict[str, float]] = {
    "cassette-closeup": {"x": 0.50, "y": 0.51, "w": 0.48, "h": 0.56},
    "keyboard-hands": {"x": 0.51, "y": 0.58, "w": 0.60, "h": 0.52},
    "drone-portrait": {"x": 0.50, "y": 0.44, "w": 0.42, "h": 0.72},
    "hover-politsia": {"x": 0.53, "y": 0.46, "w": 0.46, "h": 0.48},
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create sample mask_hint overlays.")
    parser.add_argument(
        "--sample-root",
        default="/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/public/samples",
        help="Directory with source images.",
    )
    parser.add_argument(
        "--outdir",
        default="/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/photo_parallax_playground/public/sample_hints",
        help="Directory for generated hint PNGs.",
    )
    return parser.parse_args()


def resolve_sample_path(sample_root: Path, sample_name: str) -> Path | None:
    for suffix in ("png", "jpg", "jpeg", "webp"):
        candidate = sample_root / f"{sample_name}.{suffix}"
        if candidate.exists():
            return candidate
    return None


def main() -> int:
    from PIL import Image, ImageDraw

    args = parse_args()
    sample_root = Path(args.sample_root).expanduser().resolve()
    outdir = Path(args.outdir).expanduser().resolve()
    outdir.mkdir(parents=True, exist_ok=True)

    manifest: list[dict[str, object]] = []
    for sample_name, prior in SAMPLE_PRIORS.items():
        sample_path = resolve_sample_path(sample_root, sample_name)
        if sample_path is None:
            continue

        with Image.open(sample_path) as image:
            width, height = image.size

        canvas = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(canvas, "RGBA")

        cx = int(prior["x"] * width)
        cy = int(prior["y"] * height)
        rx = max(16, int(prior["w"] * width * 0.12))
        ry = max(16, int(prior["h"] * height * 0.12))

        draw.ellipse((cx - rx, cy - ry, cx + rx, cy + ry), fill=(236, 74, 64, 220))

        protect_rx = max(12, int(rx * 0.55))
        protect_ry = max(12, int(ry * 0.55))
        draw.ellipse(
            (cx - protect_rx, cy - protect_ry // 2, cx + protect_rx, cy + protect_ry),
            fill=(78, 194, 103, 160),
        )

        corner_points = [
            (int(width * 0.14), int(height * 0.14)),
            (int(width * 0.86), int(height * 0.14)),
            (int(width * 0.14), int(height * 0.86)),
            (int(width * 0.86), int(height * 0.86)),
        ]
        neg_r = max(14, int(min(width, height) * 0.045))
        for px, py in corner_points:
            draw.ellipse((px - neg_r, py - neg_r, px + neg_r, py + neg_r), fill=(63, 118, 242, 190))

        out_path = outdir / f"{sample_name}.png"
        canvas.save(out_path)
        manifest.append(
            {
                "sample": sample_name,
                "path": str(out_path),
                "colors": {
                    "red": "closer",
                    "blue": "farther",
                    "green": "protect",
                },
            }
        )

    (outdir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"outdir": str(outdir), "entries": manifest}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
