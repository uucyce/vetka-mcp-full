#!/usr/bin/env python3
"""MARKER_LAYERPACK: Offline explicit layer extraction for parallax scenes.

Extracts semantic scene layers from:
  - source RGB image
  - real depth raster (16-bit Depth Pro)
  - plate stack metadata (z-values, bboxes, roles)
  - LaMa/clean plate for hole-filled background

Outputs canonical layer_space.json (Beta spec v1.0.0) + prototype.json sidecar.

Usage:
    python3 scripts/photo_parallax_layer_extract.py --sample hover-politsia
    python3 scripts/photo_parallax_layer_extract.py --sample hover-politsia --outdir /custom/path
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
# Resolve to main repo root (not worktree) for reading input assets
_script_root = Path(__file__).resolve().parent.parent
# Walk up from worktree to find the real repo root
ROOT = _script_root
if ".claude/worktrees" in str(ROOT):
    # We're in a git worktree — inputs live in the main repo
    ROOT = Path(str(ROOT).split(".claude/worktrees")[0].rstrip("/"))
LAB = ROOT / "photo_parallax_playground"


def _resolve_paths(sample_id: str) -> dict[str, Path]:
    return {
        "source": LAB / "public" / "samples" / f"{sample_id}.jpg",
        "depth_16": LAB / "output" / "depth_bakeoff" / "depth-pro" / sample_id / "depth_master_16.png",
        "depth_preview": LAB / "public" / "depth_bakeoff" / "depth-pro" / sample_id / "depth_preview.png",
        "plate_stack": LAB / "output" / "plate_exports_qwen_gated" / sample_id / "plate_stack.json",
        "plate_layout": LAB / "output" / "plate_exports_qwen_gated" / sample_id / "plate_layout.json",
        "lama_clean": LAB / "output" / "lama_plate_bakeoff" / "depth-pro" / sample_id / "clean_plate.png",
        "subject_rgba": LAB / "output" / "subject_plate_bakeoff" / "depth-pro" / sample_id / "subject_rgba.png",
        "subject_mask": LAB / "output" / "subject_plate_bakeoff" / "depth-pro" / sample_id / "subject_mask.png",
        "clean_no_vehicle": LAB / "output" / "plate_exports_qwen_gated" / sample_id / "plate_05_clean.png",
        "clean_no_people": LAB / "output" / "plate_exports_qwen_gated" / sample_id / "plate_06_clean.png",
    }


# ---------------------------------------------------------------------------
# Depth utilities
# ---------------------------------------------------------------------------

def load_depth_16(path: Path, target_size: tuple[int, int]) -> np.ndarray:
    """Load 16-bit depth and normalise to [0, 1] float32. Bright=near."""
    img = Image.open(path)
    if img.size != target_size:
        img = img.resize(target_size, Image.LANCZOS)
    arr = np.array(img, dtype=np.float32)
    if arr.max() > 1.0:
        arr = arr / arr.max()
    return arr


def depth_band_mask(depth: np.ndarray, lo: float, hi: float, feather: float = 0.03) -> np.ndarray:
    """Soft mask for depth values in [lo, hi] with feathered edges."""
    mask = np.ones_like(depth, dtype=np.float32)
    # Soft lower edge
    below = depth < lo
    transition_lo = (depth >= lo - feather) & (depth < lo)
    mask[below & ~transition_lo] = 0.0
    if feather > 0:
        mask[transition_lo] = (depth[transition_lo] - (lo - feather)) / feather
    # Soft upper edge
    above = depth > hi
    transition_hi = (depth <= hi + feather) & (depth > hi)
    mask[above & ~transition_hi] = 0.0
    if feather > 0:
        mask[transition_hi] = ((hi + feather) - depth[transition_hi]) / feather
    return np.clip(mask, 0, 1)


def bbox_mask(shape: tuple[int, int], bbox: dict, feather_px: int = 12) -> np.ndarray:
    """Soft rectangular mask from normalised bbox {x, y, width, height}."""
    h, w = shape
    mask = np.zeros((h, w), dtype=np.float32)
    x0 = int(bbox["x"] * w)
    y0 = int(bbox["y"] * h)
    x1 = int((bbox["x"] + bbox["width"]) * w)
    y1 = int((bbox["y"] + bbox["height"]) * h)
    x0 = max(0, x0 - feather_px)
    y0 = max(0, y0 - feather_px)
    x1 = min(w, x1 + feather_px)
    y1 = min(h, y1 + feather_px)
    mask[y0:y1, x0:x1] = 1.0
    if feather_px > 0:
        mask_img = Image.fromarray((mask * 255).astype(np.uint8), "L")
        mask_img = mask_img.filter(ImageFilter.GaussianBlur(radius=feather_px))
        mask = np.array(mask_img, dtype=np.float32) / 255.0
    return mask


# ---------------------------------------------------------------------------
# Layer extraction
# ---------------------------------------------------------------------------

def extract_layer(
    source: np.ndarray,
    depth: np.ndarray,
    alpha: np.ndarray,
    depth_band: tuple[float, float],
) -> dict[str, np.ndarray]:
    """Extract RGBA + alpha + depth slice for a layer."""
    h, w = source.shape[:2]
    # RGBA
    rgba = np.zeros((h, w, 4), dtype=np.uint8)
    rgba[:, :, :3] = source[:, :, :3]
    alpha_u8 = (np.clip(alpha, 0, 1) * 255).astype(np.uint8)
    rgba[:, :, 3] = alpha_u8
    # Depth slice (depth within band, masked by alpha)
    band_depth = depth_band_mask(depth, depth_band[0], depth_band[1], feather=0.05)
    depth_vis = (np.clip(depth, 0, 1) * 255).astype(np.uint8)
    depth_slice = np.zeros((h, w, 4), dtype=np.uint8)
    depth_slice[:, :, 0] = depth_vis
    depth_slice[:, :, 1] = depth_vis
    depth_slice[:, :, 2] = depth_vis
    depth_slice[:, :, 3] = alpha_u8
    return {"rgba": rgba, "alpha": alpha_u8, "depth": depth_slice}


def run_extraction(sample_id: str, outdir: Path) -> dict:
    """Main extraction pipeline."""
    paths = _resolve_paths(sample_id)

    # Validate inputs
    missing = [k for k, v in paths.items() if k not in ("lama_clean", "clean_no_vehicle", "clean_no_people") and not v.exists()]
    if missing:
        print(f"ERROR: Missing inputs: {missing}", file=sys.stderr)
        sys.exit(1)

    # Load source
    source_img = Image.open(paths["source"]).convert("RGB")
    w, h = source_img.size
    source = np.array(source_img)
    print(f"[load] source: {w}x{h}")

    # Load depth
    depth = load_depth_16(paths["depth_16"], (w, h))
    print(f"[load] depth: range [{depth.min():.3f}, {depth.max():.3f}]")

    # Load plate stack
    stack = json.loads(paths["plate_stack"].read_text())
    plates = stack if isinstance(stack, list) else stack.get("plates", stack.get("sampleId") and [])
    if isinstance(stack, dict) and "plates" in stack:
        plates = stack["plates"]
    print(f"[load] plate_stack: {len(plates)} plates")

    # Load camera params from plate_layout.json for space{} block
    layout = json.loads(paths["plate_layout"].read_text()) if paths["plate_layout"].exists() else {}
    camera = layout.get("camera", {})

    # Build layer definitions from plate stack
    visible_plates = [p for p in plates if p.get("visible", True)]
    z_values = [p.get("z", 0) for p in visible_plates]
    z_min, z_max = min(z_values), max(z_values)
    layers_out = []
    proto_layers = []
    layer_alphas = []

    for plate in sorted(visible_plates, key=lambda p: -p.get("z", 0)):
        pid = plate["id"]
        label = plate.get("label", pid)
        role = plate.get("role", "unknown")
        z = plate.get("z", 0)
        # Bbox is flat fields x, y, width, height at plate level
        if "x" in plate and "width" in plate:
            bbox = {"x": plate["x"], "y": plate["y"], "width": plate["width"], "height": plate["height"]}
        else:
            bbox = plate.get("bbox", plate.get("boundingBox", None))

        # Sample actual depth values within the plate bbox to find the real band
        # Depth map: LOW values = near, HIGH values = far
        if bbox:
            bx0 = max(0, int(bbox["x"] * w))
            by0 = max(0, int(bbox["y"] * h))
            bx1 = min(w, int((bbox["x"] + bbox["width"]) * w))
            by1 = min(h, int((bbox["y"] + bbox["height"]) * h))
            region = depth[by0:by1, bx0:bx1]
            if region.size > 0:
                depth_lo = float(np.percentile(region, 10))
                depth_hi = float(np.percentile(region, 90))
                # Widen band slightly for soft edges
                band_range = max(0.005, depth_hi - depth_lo)
                depth_lo = max(0, depth_lo - band_range * 0.15)
                depth_hi = min(1, depth_hi + band_range * 0.15)
            else:
                depth_lo, depth_hi = 0.0, 1.0
        else:
            depth_lo, depth_hi = 0.0, 1.0

        # Build alpha from depth band + bbox
        d_mask = depth_band_mask(depth, depth_lo, depth_hi, feather=0.005)
        if bbox:
            b_mask = bbox_mask((h, w), bbox, feather_px=16)
            alpha = d_mask * b_mask
        else:
            alpha = d_mask

        # Special handling per role
        if role == "foreground-subject" and paths["subject_mask"].exists():
            # Use bakeoff subject mask as primary signal
            subj_mask = Image.open(paths["subject_mask"]).convert("L").resize((w, h), Image.LANCZOS)
            subj_arr = np.array(subj_mask, dtype=np.float32) / 255.0
            # Combine: subject mask OR depth-based, weighted toward subject
            alpha = np.clip(subj_arr * 0.85 + alpha * 0.35, 0, 1)
            print(f"  [{pid}] {label}: subject_mask bakeoff + depth [{depth_lo:.4f}, {depth_hi:.4f}]")

        elif role == "background-far":
            # Background = complement of all foreground alphas
            if layer_alphas:
                union = np.maximum.reduce(layer_alphas)
                alpha = np.clip(1.0 - union * 0.92, 0.08, 1.0)
            else:
                alpha = np.ones((h, w), dtype=np.float32)
            print(f"  [{pid}] {label}: complement alpha (hole-fill candidate)")
        else:
            print(f"  [{pid}] {label}: depth band [{depth_lo:.4f}, {depth_hi:.4f}] + bbox, coverage={float(np.mean(alpha)):.4f}")

        layer_data = extract_layer(source, depth, alpha, (depth_lo, depth_hi))

        # Save layer files (canonical: mask not alpha)
        layer_prefix = f"layer_{pid}_{label.replace(' ', '_').lower()}"
        rgba_path = outdir / f"{layer_prefix}_rgba.png"
        mask_path = outdir / f"{layer_prefix}_mask.png"
        depth_path = outdir / f"{layer_prefix}_depth.png"

        Image.fromarray(layer_data["rgba"]).save(rgba_path)
        Image.fromarray(layer_data["alpha"], "L").save(mask_path)
        Image.fromarray(layer_data["depth"]).save(depth_path)

        coverage = float(np.mean(alpha))
        depth_priority = plate.get("depthPriority", 0.5)

        # Compute order: 0=back (lowest z), N=front (highest z)
        order_idx = len(visible_plates) - 1 - sorted(
            [p.get("z", 0) for p in visible_plates], reverse=True
        ).index(z)

        # Compute parallaxStrength from z normalised to [zNear, zFar]
        z_norm = (z - z_min) / max(1, z_max - z_min)
        parallax_strength = round(0.4 + z_norm * 1.2, 3)

        # Canonical layer entry (camelCase per Beta spec)
        layers_out.append({
            "id": layer_prefix,
            "role": role,
            "label": label,
            "order": order_idx,
            "depthPriority": round(depth_priority, 3),
            "z": z,
            "visible": True,
            "rgba": rgba_path.name,
            "mask": mask_path.name,
            "depth": depth_path.name,
            "coverage": round(coverage, 4),
            "parallaxStrength": parallax_strength,
            "motionDamping": 1.0,
        })

        # Prototype sidecar data
        proto_layers.append({
            "id": layer_prefix,
            "depthBand": [round(depth_lo, 4), round(depth_hi, 4)],
            "distanceHint": "near" if z > 10 else ("mid" if z > -10 else "far"),
            "holeFilled": False,
            "maskMethod": "subject_mask_bakeoff+depth" if role == "foreground-subject" else (
                "complement" if role == "background-far" else "depth_band+bbox"
            ),
        })

        # Track non-background alphas for complement computation
        if role != "background-far":
            layer_alphas.append(alpha)

        print(f"  [{pid}] {label}: coverage={coverage:.4f}, z={z}, role={role}")

    # --- Hole-fill background ---
    bg_layer = next((l for l in layers_out if l["role"] == "background-far"), None)
    bg_proto = next((p for p in proto_layers if p["id"] == (bg_layer or {}).get("id")), None)
    holefill_done = False
    if bg_layer and paths["lama_clean"].exists():
        print("[hole-fill] Using LaMa clean plate for background")
        lama = Image.open(paths["lama_clean"]).convert("RGB").resize((w, h), Image.LANCZOS)
        lama_arr = np.array(lama)

        bg_mask_path = outdir / bg_layer["mask"]
        bg_alpha = np.array(Image.open(bg_mask_path), dtype=np.float32) / 255.0

        bg_rgba = np.zeros((h, w, 4), dtype=np.uint8)
        bg_rgba[:, :, :3] = lama_arr
        bg_rgba[:, :, 3] = (bg_alpha * 255).astype(np.uint8)

        holefill_path = outdir / f"{bg_layer['id']}_holefill_rgba.png"
        Image.fromarray(bg_rgba).save(holefill_path)
        holefill_done = True
        if bg_proto:
            bg_proto["holeFilled"] = True
            bg_proto["holefillRgba"] = holefill_path.name
        print(f"  background hole-fill saved: {holefill_path.name}")
    elif bg_layer:
        print("[hole-fill] SKIP: no LaMa clean plate available")

    # --- Write canonical layer_space.json (Beta spec v1.0.0) ---
    canonical = {
        "contract_version": "1.0.0",
        "sampleId": sample_id,
        "source": {
            "path": str(paths["source"]),
            "width": w,
            "height": h,
        },
        "layers": layers_out,
        "space": {
            "focalLengthMm": camera.get("focalLengthMm", 50),
            "filmWidthMm": camera.get("filmWidthMm", 36),
            "zNear": camera.get("zNear", 0.72),
            "zFar": camera.get("zFar", 1.85),
            "motionType": camera.get("motionType", "orbit"),
            "durationSec": camera.get("durationSec", 4.0),
            "travelXPct": camera.get("travelXPct", 3.0),
            "travelYPct": camera.get("travelYPct", 0.0),
            "zoom": camera.get("zoom", 1.0),
            "overscanPct": camera.get("overscanPct", 20.0),
        },
        "provenance": {
            "depth_backend": "depth-pro",
            "grouping_backend": "qwen-vl",
        },
    }

    canonical_path = outdir / "layer_space.json"
    canonical_path.write_text(json.dumps(canonical, indent=2))

    # --- Write prototype.json sidecar (non-canonical metadata) ---
    prototype = {
        "_note": "Prototype-only sidecar. NOT part of canonical layer_space.json spec.",
        "createdAt": datetime.now(timezone.utc).isoformat(),
        "depthSource": {
            "kind": "real_depth_raster",
            "model": "depth-pro",
            "polarity": "low_near_high_far_in_16bit",
            "path": str(paths["depth_16"]),
        },
        "holeFill": {
            "method": "lama_inpaint" if holefill_done else "none",
            "source": str(paths["lama_clean"]) if paths["lama_clean"].exists() else None,
        },
        "layers": proto_layers,
        "qualityCaveats": [
            "walker mask is bbox+depth only — needs SAM instance segmentation",
            "vehicle mask has building geometry spill on left side (subject_mask bakeoff, not pixel-perfect)",
            "hole-fill is LaMa-only, no generative inpaint for complex occlusions",
            "steam/vehicle depth bands overlap ([0.005,0.053] vs [0.005,0.056]) — potential double-compositing",
        ],
    }

    proto_path = outdir / "prototype.json"
    proto_path.write_text(json.dumps(prototype, indent=2))

    print(f"\n[done] Layer pack: {outdir}")
    print(f"  canonical: {canonical_path.name}")
    print(f"  sidecar:   {proto_path.name}")
    print(f"  layers:    {len(layers_out)}")
    print(f"  hole_fill: {holefill_done}")

    return canonical


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Offline explicit layer extraction for parallax scenes")
    parser.add_argument("--sample", default="hover-politsia", help="Sample ID")
    parser.add_argument("--outdir", default=None, help="Output directory (default: output/layer_packs/<sample>)")
    args = parser.parse_args()

    if args.outdir:
        outdir = Path(args.outdir)
    else:
        outdir = LAB / "output" / "layer_packs" / args.sample

    outdir.mkdir(parents=True, exist_ok=True)
    run_extraction(args.sample, outdir)


if __name__ == "__main__":
    main()
