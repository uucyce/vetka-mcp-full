#!/usr/bin/env python3
"""
Lightweight screenshot sanity audit for MCC drill-down snapshots.

Reports:
- mean luminance
- edge energy ratio (proxy for visual noise/clutter)
- bright pixel ratio
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

def _load_gray(path: Path):
    try:
        from PIL import Image  # type: ignore
    except Exception as exc:  # pragma: no cover
        raise RuntimeError(
            "Pillow is required for mcc_spectral_audit.py. Install with: python3 -m pip install pillow"
        ) from exc
    img = Image.open(path).convert("L")
    return img


def _edge_energy(gray) -> float:
    w, h = gray.size
    px = gray.load()
    total = 0.0
    count = 0
    for y in range(h - 1):
        for x in range(w - 1):
            gx = abs(px[x + 1, y] - px[x, y])
            gy = abs(px[x, y + 1] - px[x, y])
            total += gx + gy
            count += 2
    return (total / count) if count else 0.0


def audit(path: Path) -> dict:
    gray = _load_gray(path)
    w, h = gray.size
    px = list(gray.getdata())
    mean_luma = sum(px) / max(1, len(px))
    bright_ratio = sum(1 for v in px if v >= 180) / max(1, len(px))
    edge_energy = _edge_energy(gray)
    return {
        "path": str(path),
        "width": w,
        "height": h,
        "mean_luma": round(mean_luma, 3),
        "bright_ratio": round(bright_ratio, 6),
        "edge_energy": round(edge_energy, 3),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("image", type=Path)
    parser.add_argument("--json-out", type=Path, default=None)
    args = parser.parse_args()

    metrics = audit(args.image)
    text = json.dumps(metrics, ensure_ascii=True, indent=2)
    print(text)

    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(text + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
