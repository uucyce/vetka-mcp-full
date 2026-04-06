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
from PIL import Image, ImageChops, ImageFilter

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


def _largest_component(mask: np.ndarray) -> tuple[np.ndarray, dict] | tuple[None, None]:
    """Return the largest connected component from a boolean mask.
    Uses scipy.ndimage.label when available (O(N)), falls back to
    pure-Python BFS with a 4M-pixel guard for safety.
    Returned meta always contains: score, area, aspect, fill."""
    h, w = mask.shape

    # Fast path: scipy connected components (O(N))
    try:
        from scipy.ndimage import label as _scipy_label
        labeled, num_features = _scipy_label(mask.astype(np.uint8))
        if num_features == 0:
            return None, None
        comp_sizes = np.bincount(labeled.ravel())
        comp_sizes[0] = 0  # ignore background
        best_label = int(comp_sizes.argmax())
        best_comp_mask = labeled == best_label
        ys, xs = np.where(best_comp_mask)
        area = len(ys)
        x0, y0, x1, y1 = int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())
        comp_h = y1 - y0 + 1
        comp_w = x1 - x0 + 1
        aspect = comp_h / max(1, comp_w)
        fill = area / max(1, comp_h * comp_w)
        score = min(area / 3000, 1.5) + min(aspect / 3, 1.5)
        return best_comp_mask, {
            "score": float(score), "area": area,
            "aspect": float(aspect), "fill": float(fill),
            "bbox": {"x": x0, "y": y0, "width": comp_w, "height": comp_h},
        }
    except ImportError:
        pass

    # Guard: pure-Python BFS on >4M pixels will be too slow — return whole mask
    if h * w > 4_000_000:
        ys, xs = np.where(mask)
        if len(ys) == 0:
            return None, None
        x0, y0, x1, y1 = int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())
        comp_h = y1 - y0 + 1
        comp_w = x1 - x0 + 1
        area = int(mask.sum())
        aspect = comp_h / max(1, comp_w)
        fill = area / max(1, comp_h * comp_w)
        return mask, {"score": 0.0, "area": area, "aspect": float(aspect), "fill": float(fill),
                      "bbox": {"x": x0, "y": y0, "width": comp_w, "height": comp_h}}

    visited = np.zeros((h, w), dtype=bool)
    best_mask: np.ndarray | None = None
    best_meta: dict | None = None

    for yy in range(h):
        for xx in range(w):
            if not mask[yy, xx] or visited[yy, xx]:
                continue
            stack = [(yy, xx)]
            visited[yy, xx] = True
            points: list[tuple[int, int]] = []
            while stack:
                cy, cx = stack.pop()
                points.append((cy, cx))
                for ny, nx in ((cy - 1, cx), (cy + 1, cx), (cy, cx - 1), (cy, cx + 1)):
                    if 0 <= ny < h and 0 <= nx < w and mask[ny, nx] and not visited[ny, nx]:
                        visited[ny, nx] = True
                        stack.append((ny, nx))

            ys = np.array([p[0] for p in points])
            xs = np.array([p[1] for p in points])
            area = len(points)
            x0, y0 = int(xs.min()), int(ys.min())
            x1, y1 = int(xs.max()), int(ys.max())
            comp_h = y1 - y0 + 1
            comp_w = x1 - x0 + 1
            aspect = comp_h / max(1, comp_w)
            fill = area / max(1, comp_h * comp_w)
            score = min(area / 3000, 1.5) + min(aspect / 3, 1.5)
            if fill < 0.08 or fill > 0.9:
                score -= 2.0

            if best_meta is None or score > best_meta["score"]:
                comp_mask = np.zeros((h, w), dtype=bool)
                comp_mask[ys, xs] = True
                best_mask = comp_mask
                best_meta = {
                    "score": float(score), "area": area,
                    "aspect": float(aspect), "fill": float(fill),
                    "bbox": (x0, y0, x1, y1),
                }

    return best_mask, best_meta


def walker_mask_from_clean_diff(
    source_img: Image.Image,
    clean_img: Image.Image,
    depth: np.ndarray,
    bbox: dict,
) -> tuple[np.ndarray | None, dict]:
    """Build a walker silhouette from source-vs-clean diff inside the search window."""
    w, h = source_img.size
    x0 = max(0, int(bbox["x"] * w))
    y0 = max(0, int(bbox["y"] * h))
    x1 = min(w, int((bbox["x"] + bbox["width"]) * w))
    y1 = min(h, int((bbox["y"] + bbox["height"]) * h))
    if x1 <= x0 or y1 <= y0:
        return None, {"reason": "empty_bbox"}

    diff = np.array(ImageChops.difference(source_img, clean_img), dtype=np.float32).mean(axis=2)
    lum = np.array(source_img.convert("L"), dtype=np.float32)
    win = diff[y0:y1, x0:x1]
    win_lum = lum[y0:y1, x0:x1]
    win_depth = depth[y0:y1, x0:x1]

    seed = (
        (win > np.percentile(win, 92))
        & (win_lum < np.percentile(win_lum, 55))
        & (win_depth < np.percentile(win_depth, 45))
    )
    seed_img = (
        Image.fromarray((seed.astype(np.uint8) * 255), "L")
        .filter(ImageFilter.MaxFilter(3))
        .filter(ImageFilter.GaussianBlur(1.5))
    )
    seed_mask = np.array(seed_img) > 140
    component, meta = _largest_component(seed_mask)
    if component is None or meta is None:
        return None, {"reason": "no_component"}

    area = meta["area"]
    aspect = meta["aspect"]
    fill = meta["fill"]
    if area < 1200 or area > 12000 or aspect < 1.8 or fill < 0.08 or fill > 0.65:
        return None, {
            "reason": "component_rejected",
            "area": area,
            "aspect": round(aspect, 3),
            "fill": round(fill, 3),
            "score": round(meta["score"], 3),
        }

    comp_img = Image.fromarray((component.astype(np.uint8) * 255), "L")
    comp_img = comp_img.filter(ImageFilter.MaxFilter(5)).filter(ImageFilter.GaussianBlur(2.0))
    alpha_local = np.array(comp_img, dtype=np.float32) / 255.0

    out = np.zeros((h, w), dtype=np.float32)
    out[y0:y1, x0:x1] = alpha_local
    return out, {
        "reason": "ok",
        "area": area,
        "aspect": round(aspect, 3),
        "fill": round(fill, 3),
        "score": round(meta["score"], 3),
    }


def vehicle_mask_from_clean_diff(
    source_img: Image.Image,
    clean_img: Image.Image,
    depth: np.ndarray,
    subject_alpha: np.ndarray,
    bbox: dict,
) -> tuple[np.ndarray | None, dict]:
    """Refine the main subject mask by intersecting it with a clean-plate diff seed."""
    w, h = source_img.size
    x0 = max(0, int(bbox["x"] * w))
    y0 = max(0, int(bbox["y"] * h))
    x1 = min(w, int((bbox["x"] + bbox["width"]) * w))
    y1 = min(h, int((bbox["y"] + bbox["height"]) * h))
    if x1 <= x0 or y1 <= y0:
        return None, {"reason": "empty_bbox"}

    diff = np.array(ImageChops.difference(source_img, clean_img), dtype=np.float32).mean(axis=2)
    win = diff[y0:y1, x0:x1]
    win_depth = depth[y0:y1, x0:x1]
    seed = (
        (win > np.percentile(win, 88))
        & (win_depth < np.percentile(win_depth, 70))
    )
    seed_img = (
        Image.fromarray((seed.astype(np.uint8) * 255), "L")
        .filter(ImageFilter.MaxFilter(7))
        .filter(ImageFilter.GaussianBlur(4.0))
    )
    seed_full = np.zeros((h, w), dtype=np.float32)
    seed_full[y0:y1, x0:x1] = np.array(seed_img, dtype=np.float32) / 255.0

    combined = np.minimum(subject_alpha, np.clip(seed_full * 1.25, 0, 1))

    core = combined[
        max(0, y0 + int((y1 - y0) * 0.08)):min(h, y0 + int((y1 - y0) * 0.92)),
        max(0, x0 + int((x1 - x0) * 0.12)):min(w, x0 + int((x1 - x0) * 0.92)),
    ]
    if core.size == 0:
        return None, {"reason": "empty_core"}
    core_cover = float(np.mean(core > 0.08))
    total_cover = float(np.mean(combined > 0.08))
    if core_cover < 0.35 or total_cover < 0.06:
        return None, {
            "reason": "coverage_rejected",
            "coreCoverage": round(core_cover, 4),
            "totalCoverage": round(total_cover, 4),
        }

    return combined, {
        "reason": "ok",
        "coreCoverage": round(core_cover, 4),
        "totalCoverage": round(total_cover, 4),
    }


def atmospheric_mask_from_color_depth(
    source_img: Image.Image,
    depth: np.ndarray,
    bbox: dict,
) -> tuple[np.ndarray | None, dict]:
    """Build a soft atmospheric mask from color statistics + depth inside a search window."""
    w, h = source_img.size
    x0 = max(0, int(bbox["x"] * w))
    y0 = max(0, int(bbox["y"] * h))
    x1 = min(w, int((bbox["x"] + bbox["width"]) * w))
    y1 = min(h, int((bbox["y"] + bbox["height"]) * h))
    if x1 <= x0 or y1 <= y0:
        return None, {"reason": "empty_bbox"}

    rgb = np.array(source_img, dtype=np.float32)[y0:y1, x0:x1]
    win_depth = depth[y0:y1, x0:x1]
    lum = rgb.mean(axis=2)
    mx = rgb.max(axis=2)
    mn = rgb.min(axis=2)
    sat = (mx - mn) / np.maximum(mx, 1e-3)
    blue = rgb[:, :, 2]

    seed = (
        (lum > np.percentile(lum, 65))
        & (sat < np.percentile(sat, 40))
        & (blue > np.percentile(blue, 60))
        & (win_depth < np.percentile(win_depth, 75))
    )
    seed_img = (
        Image.fromarray((seed.astype(np.uint8) * 255), "L")
        .filter(ImageFilter.MaxFilter(5))
        .filter(ImageFilter.GaussianBlur(5.0))
    )
    alpha_local = np.array(seed_img, dtype=np.float32) / 255.0

    out = np.zeros((h, w), dtype=np.float32)
    out[y0:y1, x0:x1] = alpha_local
    cover = float(np.mean(out > 0.06))
    if cover < 0.01 or cover > 0.08:
        return None, {"reason": "coverage_rejected", "coverage": round(cover, 4)}

    return out, {"reason": "ok", "coverage": round(cover, 4)}


def expanded_mask(mask: np.ndarray, max_filter_size: int = 31, blur_radius: float = 10.0) -> np.ndarray:
    """Expand a mask for soft local compositing."""
    img = Image.fromarray((np.clip(mask, 0, 1) * 255).astype(np.uint8), "L")
    img = img.filter(ImageFilter.MaxFilter(max_filter_size)).filter(ImageFilter.GaussianBlur(blur_radius))
    return np.array(img, dtype=np.float32) / 255.0


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
    lama_clean_img = None
    if paths["lama_clean"].exists():
        lama_clean_img = Image.open(paths["lama_clean"]).convert("RGB").resize((w, h), Image.LANCZOS)
    clean_no_vehicle_img = None
    if paths["clean_no_vehicle"].exists():
        clean_no_vehicle_img = Image.open(paths["clean_no_vehicle"]).convert("RGB").resize((w, h), Image.LANCZOS)
    clean_no_people_img = None
    if paths["clean_no_people"].exists():
        clean_no_people_img = Image.open(paths["clean_no_people"]).convert("RGB").resize((w, h), Image.LANCZOS)

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

    for i_plate, plate in enumerate(sorted(visible_plates, key=lambda p: -p.get("z", 0))):
        pid = plate.get("id") or f"plate_{i_plate}"
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
        mask_method = "depth_band_only"
        canonical_ready = False
        if role == "foreground-subject" and paths["subject_mask"].exists():
            # Use bakeoff subject mask as primary signal
            subj_mask = Image.open(paths["subject_mask"]).convert("L").resize((w, h), Image.LANCZOS)
            subj_arr = np.array(subj_mask, dtype=np.float32) / 255.0
            # Combine: subject mask OR depth-based, weighted toward subject
            alpha = np.clip(subj_arr * 0.85 + alpha * 0.35, 0, 1)
            if clean_no_vehicle_img is not None and bbox:
                vehicle_alpha, vehicle_meta = vehicle_mask_from_clean_diff(
                    source_img,
                    clean_no_vehicle_img,
                    depth,
                    alpha,
                    bbox,
                )
                if vehicle_alpha is not None:
                    alpha = vehicle_alpha
                    mask_method = "subject_mask_bakeoff+clean_no_vehicle_diff+depth"
                    canonical_ready = True
                    print(
                        f"  [{pid}] {label}: subject_mask + clean_no_vehicle diff "
                        f"(core={vehicle_meta['coreCoverage']}, total={vehicle_meta['totalCoverage']})"
                    )
                else:
                    mask_method = "subject_mask_bakeoff+depth"
                    canonical_ready = True
                    print(f"  [{pid}] {label}: subject_mask fallback ({vehicle_meta.get('reason')})")
            else:
                mask_method = "subject_mask_bakeoff+depth"
                canonical_ready = True
                print(f"  [{pid}] {label}: subject_mask bakeoff + depth [{depth_lo:.4f}, {depth_hi:.4f}]")

        elif role == "secondary-subject" and clean_no_people_img is not None and bbox:
            walker_alpha, walker_meta = walker_mask_from_clean_diff(source_img, clean_no_people_img, depth, bbox)
            if walker_alpha is not None:
                alpha = np.clip(walker_alpha, 0, 1)
                mask_method = "clean_no_people_diff+depth"
                canonical_ready = True
                print(
                    f"  [{pid}] {label}: clean_no_people diff silhouette "
                    f"(area={walker_meta['area']}, aspect={walker_meta['aspect']}, score={walker_meta['score']})"
                )
            else:
                mask_method = "depth_band+bbox"
                canonical_ready = False
                print(f"  [{pid}] {label}: walker diff rejected ({walker_meta.get('reason')})")

        elif role == "environment-mid" and bbox:
            steam_alpha, steam_meta = atmospheric_mask_from_color_depth(source_img, depth, bbox)
            if steam_alpha is not None:
                alpha = np.clip(steam_alpha, 0, 1)
                mask_method = "atmospheric_color_depth"
                canonical_ready = False
                print(f"  [{pid}] {label}: atmospheric soft mask (coverage={steam_meta['coverage']})")
            else:
                mask_method = "depth_band+bbox"
                canonical_ready = False
                print(f"  [{pid}] {label}: atmospheric path rejected ({steam_meta.get('reason')})")

        elif role == "background-far":
            if lama_clean_img is not None:
                alpha = np.ones((h, w), dtype=np.float32)
                mask_method = "lama_clean_fullframe"
                canonical_ready = True
                print(f"  [{pid}] {label}: LaMa clean full-frame background")
            else:
                # Fallback only when no clean background exists.
                if layer_alphas:
                    union = np.maximum.reduce(layer_alphas)
                    alpha = np.clip(1.0 - union * 0.92, 0.08, 1.0)
                else:
                    alpha = np.ones((h, w), dtype=np.float32)
                mask_method = "complement"
                canonical_ready = False
                print(f"  [{pid}] {label}: complement alpha (hole-fill candidate)")
        else:
            mask_method = "depth_band+bbox"
            canonical_ready = False
            print(f"  [{pid}] {label}: depth band [{depth_lo:.4f}, {depth_hi:.4f}] + bbox, coverage={float(np.mean(alpha)):.4f}")

        layer_data = extract_layer(source, depth, alpha, (depth_lo, depth_hi))
        if role == "background-far" and lama_clean_img is not None:
            layer_data["rgba"][:, :, :3] = np.array(lama_clean_img)

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
        # Use enumerate + plate id to handle duplicate z values with unique order
        sorted_plates_by_z = sorted(
            enumerate(visible_plates),
            key=lambda ip: (-ip[1].get("z", 0), ip[0]),  # descending z, then original index
        )
        order_idx = next(
            (rank for rank, (_, p) in enumerate(sorted_plates_by_z) if p.get("id") == pid),
            0,
        )

        # Compute parallaxStrength from z normalised to [zNear, zFar]
        z_norm = (z - z_min) / max(0.001, z_max - z_min)
        parallax_strength = round(0.4 + z_norm * 1.2, 3)

        # Canonical layer entry (camelCase per Beta spec)
        layers_out.append({
            "id": layer_prefix,
            "role": role,
            "label": label,
            "order": order_idx,
            "depthPriority": round(depth_priority, 3),
            "z": z,
            "visible": True,  # always visible in layer_space.json; canonicalReady tracks validation
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
            "maskMethod": mask_method,
            "canonicalReady": canonical_ready,
            "cleanupScope": "no_vehicle_only" if role == "background-far" and mask_method == "lama_clean_fullframe" else "n/a",
            "foregroundUnionCleared": False if role == "background-far" and mask_method == "lama_clean_fullframe" else None,
        })

        # Track non-background alphas for complement computation
        if role != "background-far":
            layer_alphas.append(alpha)

        print(
            f"  [{pid}] {label}: coverage={coverage:.4f}, z={z}, role={role}, "
            f"canonical_ready={canonical_ready}, mask_method={mask_method}"
        )

    # --- Hole-fill background ---
    bg_layer = next((l for l in layers_out if l["role"] == "background-far"), None)
    bg_proto = next((p for p in proto_layers if p["id"] == (bg_layer or {}).get("id")), None)
    holefill_done = False
    if bg_layer and paths["lama_clean"].exists():
        print("[hole-fill] Using union-clean background assembly")
        lama = Image.open(paths["lama_clean"]).convert("RGB").resize((w, h), Image.LANCZOS)
        lama_arr = np.array(lama, dtype=np.float32)
        bg_rgb = lama_arr.copy()
        bg_cleanup_scope = "lama_only"
        foreground_union_cleared = False

        vehicle_layer = next((l for l in layers_out if "vehicle" in l["id"]), None)
        vehicle_proto = next((p for p in proto_layers if "vehicle" in p["id"]), None)
        if paths["clean_no_vehicle"].exists() and vehicle_layer and vehicle_proto and vehicle_proto.get("canonicalReady"):
            vehicle_mask = np.array(Image.open(outdir / vehicle_layer["mask"]), dtype=np.float32) / 255.0
            vehicle_blend = expanded_mask(vehicle_mask, max_filter_size=35, blur_radius=12.0)
            no_vehicle = Image.open(paths["clean_no_vehicle"]).convert("RGB").resize((w, h), Image.LANCZOS)
            no_vehicle_arr = np.array(no_vehicle, dtype=np.float32)
            bg_rgb = bg_rgb * (1.0 - vehicle_blend[:, :, None]) + no_vehicle_arr * vehicle_blend[:, :, None]
            bg_cleanup_scope = "vehicle_partial"
            if bg_proto:
                bg_proto["vehicleBlendMask"] = vehicle_layer["mask"]

        walker_proto = next((p for p in proto_layers if "walker" in p["id"]), None)
        walker_layer = next((l for l in layers_out if "walker" in l["id"]), None)
        if paths["clean_no_people"].exists() and walker_proto and walker_proto.get("canonicalReady") and walker_layer:
            walker_mask = np.array(Image.open(outdir / walker_layer["mask"]), dtype=np.float32) / 255.0
            walker_blend = expanded_mask(walker_mask, max_filter_size=31, blur_radius=10.0)
            no_people = Image.open(paths["clean_no_people"]).convert("RGB").resize((w, h), Image.LANCZOS)
            no_people_arr = np.array(no_people, dtype=np.float32)
            bg_rgb = bg_rgb * (1.0 - walker_blend[:, :, None]) + no_people_arr * walker_blend[:, :, None]
            bg_cleanup_scope = "vehicle_and_walker_partial"
            if bg_proto:
                bg_proto["walkerBlendMask"] = walker_layer["mask"]

        if bg_proto:
            bg_proto["cleanupScope"] = bg_cleanup_scope
            bg_proto["foregroundUnionCleared"] = foreground_union_cleared

        bg_mask_path = outdir / bg_layer["mask"]
        bg_alpha = np.array(Image.open(bg_mask_path), dtype=np.float32) / 255.0

        bg_rgba = np.zeros((h, w, 4), dtype=np.uint8)
        bg_rgba[:, :, :3] = np.clip(bg_rgb, 0, 255).astype(np.uint8)
        bg_rgba[:, :, 3] = (bg_alpha * 255).astype(np.uint8)

        holefill_path = outdir / f"{bg_layer['id']}_holefill_rgba.png"
        Image.fromarray(bg_rgba).save(holefill_path)
        holefill_done = True
        if bg_proto:
            bg_proto["holeFilled"] = True
            bg_proto["holefillRgba"] = holefill_path.name
            if bg_proto.get("maskMethod") == "lama_clean_fullframe":
                bg_proto.setdefault("cleanupScope", "lama_only")
                bg_proto.setdefault("foregroundUnionCleared", False)
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
            "walker silhouette uses clean_no_people diff when available; fallback bbox+depth still needs SAM-quality segmentation",
            "vehicle mask is constrained by clean_no_vehicle diff, reducing building spill but still not SAM-quality at fine edges",
            "street steam uses atmospheric color+depth soft mask when available; still provisional and not a stable semantic cutout",
            "background city is now assembled from LaMa plus clean-no-vehicle and clean-no-people blends, but suspended cables and other foreground residue can still remain",
            "hole-fill is LaMa-only, no generative inpaint for complex occlusions",
            "layers with canonicalReady=false are provisional debug layers, not clean semantic cutouts",
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
