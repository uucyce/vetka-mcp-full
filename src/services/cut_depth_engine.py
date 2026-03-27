"""
MARKER_PARALLAX_MOTION — CUT Parallax Motion Engine.

Generates FFmpeg filter expressions for depth-driven parallax motion.
Converts a static image + depth map into a moving camera shot.

Camera model: pinhole projection.
  delta_x = -(zoom_px * camera_tx) / Z
  Z = z_near + (1 - depth_norm) * (z_far - z_near)

Three depth bands (near/mid/far) with per-band motion scaling.
Bands are isolated via luma thresholding on the depth map, then composited
with per-band parallax motion via FFmpeg overlay expressions.

@status: active
@phase: D9
@task: tb_1774603073_1
@depends: cut_effects_engine (parallax_motion effect def)
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any


# ---------------------------------------------------------------------------
# Motion type normalization (Alpha compat shim)
# ---------------------------------------------------------------------------
# Alpha/playground uses: "orbit", "portrait-base", "dolly-out + zoom-in", etc.
# Engine uses: "orbit", "dolly_zoom_in", "dolly_zoom_out", "linear"

_MOTION_TYPE_NORMALIZE: dict[str, str] = {
    "orbit": "orbit",
    "portrait-base": "orbit",       # portrait-base is orbit variant
    "dolly-out + zoom-in": "dolly_zoom_in",
    "dolly-in + zoom-out": "dolly_zoom_out",
    "dolly_zoom_in": "dolly_zoom_in",
    "dolly_zoom_out": "dolly_zoom_out",
    "linear": "linear",
}


def normalize_motion_type(motion_type: str) -> str:
    """Normalize motion type from any format to engine canonical form."""
    return _MOTION_TYPE_NORMALIZE.get(motion_type, "orbit")


# ---------------------------------------------------------------------------
# Camera geometry
# ---------------------------------------------------------------------------

@dataclass
class CameraGeometry:
    """Virtual camera parameters for parallax rendering."""
    focal_length_mm: float = 50.0
    film_width_mm: float = 36.0    # 35mm full frame
    z_near: float = 0.72
    z_far: float = 1.85
    travel_x: float = 5.0         # pixels of camera travel (horizontal)
    travel_y: float = 0.0         # pixels of camera travel (vertical)
    zoom: float = 1.0             # 1.0 = no zoom, >1 = zoom in
    motion_type: str = "orbit"    # orbit, dolly_zoom_in, dolly_zoom_out, linear
    duration_sec: float = 4.0
    overscan_pct: float = 20.0    # extra canvas to avoid black edges

    @property
    def aov_rad(self) -> float:
        """Angle of view in radians."""
        return 2.0 * math.atan(self.film_width_mm / max(1e-6, 2.0 * self.focal_length_mm))

    @property
    def reference_z(self) -> float:
        return (self.z_near + self.z_far) / 2.0

    def zoom_px(self, source_width: int) -> float:
        """Compute zoom in pixels from focal length and frame width."""
        return source_width / max(1e-6, 2.0 * math.tan(self.aov_rad / 2.0))

    def camera_tx(self, source_width: int) -> float:
        """Camera translation X derived from travel pixels."""
        zp = self.zoom_px(source_width)
        motion_scale = 0.42  # empirical scale from parallax lab
        return -((self.travel_x * self.reference_z * motion_scale) / max(1e-6, zp))

    def camera_ty(self, source_height: int) -> float:
        """Camera translation Y derived from travel pixels."""
        # Use same zoom_px basis but from height
        zp = self.zoom_px(source_height)  # approximation
        motion_scale = 0.42
        return -((self.travel_y * self.reference_z * motion_scale) / max(1e-6, zp))

    @staticmethod
    def from_camera_contract(
        contract: Any,
        source_width: int,
        source_height: int,
    ) -> CameraGeometry:
        """Create from a CameraContract (layer manifest camera).

        Converts percentage-based travel to pixel-based travel.
        Normalizes motion_type from Alpha kebab-case to engine underscore.
        """
        travel_x_px = source_width * float(contract.travel_x_pct) / 100.0
        travel_y_px = source_height * float(contract.travel_y_pct) / 100.0

        return CameraGeometry(
            focal_length_mm=float(contract.focal_length_mm),
            film_width_mm=float(contract.film_width_mm),
            z_near=float(contract.z_near),
            z_far=float(contract.z_far),
            travel_x=travel_x_px,
            travel_y=travel_y_px,
            zoom=float(contract.zoom),
            motion_type=normalize_motion_type(str(contract.motion_type)),
            duration_sec=float(contract.duration_sec),
            overscan_pct=float(contract.overscan_pct),
        )

    @staticmethod
    def from_effect_params(params: dict[str, Any]) -> CameraGeometry:
        """Create from parallax_motion effect params."""
        return CameraGeometry(
            focal_length_mm=float(params.get("focal_length_mm", 50.0)),
            travel_x=float(params.get("travel_x", 5.0)),
            travel_y=float(params.get("travel_y", 0.0)),
            zoom=float(params.get("zoom", 1.0)),
            z_near=float(params.get("z_near", 0.72)),
            z_far=float(params.get("z_far", 1.85)),
            motion_type=normalize_motion_type(str(params.get("motion_type", "orbit"))),
            duration_sec=float(params.get("duration_sec", 4.0)),
            overscan_pct=float(params.get("overscan_pct", 20.0)),
        )


# ---------------------------------------------------------------------------
# Depth bands — 3-layer parallax
# ---------------------------------------------------------------------------

DEPTH_BANDS: list[dict[str, Any]] = [
    {"name": "near", "min": 170, "max": 255, "motion_scale": 1.18, "zoom_scale": 1.08},
    {"name": "mid",  "min": 96,  "max": 169, "motion_scale": 1.0,  "zoom_scale": 1.0},
    {"name": "far",  "min": 1,   "max": 95,  "motion_scale": 0.72, "zoom_scale": 0.94},
]


def depth_byte_to_z(depth_byte: float, z_near: float, z_far: float) -> float:
    """Convert a depth byte value (0-255) to Z-distance.

    Convention: white (255) = near, black (0) = far.
    """
    depth_norm = max(0.0, min(1.0, depth_byte / 255.0))
    return z_near + (1.0 - depth_norm) * (z_far - z_near)


# ---------------------------------------------------------------------------
# FFmpeg expression builders
# ---------------------------------------------------------------------------

def _progress_expr(duration: float) -> str:
    """Normalized time progress 0→1."""
    return f"min(1,max(0,t/{duration:.2f}))"


def _signed_expr(duration: float) -> str:
    """Sinusoidal signed curve (-1 → 0 → +1)."""
    progress = _progress_expr(duration)
    return f"sin((({progress})-0.5)*PI)"


def _cosine_expr(duration: float) -> str:
    """Cosine curve for vertical orbit sway."""
    progress = _progress_expr(duration)
    return f"cos(({progress})*PI)"


def compute_motion_pixels(
    camera: CameraGeometry,
    source_width: int,
    depth_byte: float,
    axis: str = "x",
    strength_scale: float = 1.0,
) -> float:
    """Compute parallax displacement in pixels for a given depth value."""
    zoom_px = camera.zoom_px(source_width)
    if axis == "x":
        camera_shift = camera.camera_tx(source_width)
    else:
        camera_shift = camera.camera_ty(source_width)

    z_value = depth_byte_to_z(depth_byte, camera.z_near, camera.z_far)
    return (-(zoom_px * camera_shift) / max(1e-6, z_value)) * strength_scale


def build_band_motion_expr(
    camera: CameraGeometry,
    source_width: int,
    depth_byte: float,
    axis: str = "x",
    strength_scale: float = 1.0,
) -> str:
    """Build FFmpeg expression for parallax motion at a given depth."""
    pixels = compute_motion_pixels(camera, source_width, depth_byte, axis, strength_scale)
    signed = _signed_expr(camera.duration_sec)
    cosine = _cosine_expr(camera.duration_sec)

    if camera.motion_type == "orbit":
        if axis == "x":
            return f"{pixels:.4f}*{signed}"
        return f"{(pixels * 0.52):.4f}*{cosine}"
    elif camera.motion_type.startswith("dolly"):
        return f"{(pixels * 0.72):.4f}*{signed}"
    else:  # linear
        return f"{pixels:.4f}*{signed}"


def build_band_zoom_expr(
    camera: CameraGeometry,
    strength: float,
    zoom_scale: float = 1.0,
) -> str:
    """Build FFmpeg zoom expression for a depth band."""
    zoom_delta = camera.zoom - 1.0
    progress = _progress_expr(camera.duration_sec)
    cosine = _cosine_expr(camera.duration_sec)
    scaled = strength * zoom_scale

    if camera.motion_type == "orbit":
        return f"(1+({zoom_delta:.6f})*{scaled:.4f}*0.14*(1-({cosine}*{cosine})))"
    elif camera.motion_type == "dolly_zoom_in":
        return f"(1+({zoom_delta:.6f})*{progress}*{scaled:.4f})"
    elif camera.motion_type == "dolly_zoom_out":
        return f"(1+({zoom_delta:.6f})*(1-{progress})*{scaled:.4f})"
    else:
        return f"(1+({zoom_delta:.6f})*{scaled:.4f}*0.32)"


# ---------------------------------------------------------------------------
# Full parallax filter chain
# ---------------------------------------------------------------------------

def build_parallax_filter(
    camera: CameraGeometry,
    source_width: int,
    source_height: int,
    depth_input: str = "1:v",
    source_input: str = "0:v",
    output_label: str = "parallax_out",
) -> str:
    """
    Build complete FFmpeg filter_complex for depth-driven parallax.

    Takes a source image/video and a depth map, produces a moving parallax video.
    Uses 3 depth bands (near/mid/far) with per-band motion and zoom.

    Args:
        camera: Camera geometry parameters
        source_width: Source frame width
        source_height: Source frame height
        depth_input: FFmpeg input index for depth map (default "1:v")
        source_input: FFmpeg input index for source image (default "0:v")
        output_label: Label for final output stream

    Returns:
        FFmpeg filter_complex string
    """
    overscan = 1.0 + camera.overscan_pct / 100.0
    internal_w = max(2, int(round(source_width * overscan / 2) * 2))
    internal_h = max(2, int(round(source_height * overscan / 2) * 2))

    lines: list[str] = []
    band_outputs: list[str] = []

    # Create base canvas
    lines.append(
        f"color=c=black:s={internal_w}x{internal_h}:r=25:d={camera.duration_sec:.2f}[base]"
    )

    # Scale source to internal resolution
    lines.append(f"[{source_input}]scale={internal_w}:{internal_h}:flags=lanczos[src_scaled]")
    lines.append(f"[{depth_input}]scale={internal_w}:{internal_h}:flags=lanczos,format=gray[depth_scaled]")

    # Split source and depth for each band
    n_bands = len(DEPTH_BANDS)
    src_labels = [f"src_b{i}" for i in range(n_bands)]
    depth_labels = [f"dep_b{i}" for i in range(n_bands)]

    lines.append(
        f"[src_scaled]split={n_bands}" + "".join(f"[{l}]" for l in src_labels)
    )
    lines.append(
        f"[depth_scaled]split={n_bands}" + "".join(f"[{l}]" for l in depth_labels)
    )

    # Process each depth band
    prev_composite = "base"
    for i, band in enumerate(DEPTH_BANDS):
        sl = src_labels[i]
        dl = depth_labels[i]
        band_name = band["name"]
        band_min = band["min"]
        band_max = band["max"]
        motion_scale = band["motion_scale"]
        zoom_scale = band["zoom_scale"]

        # Center depth byte for motion calculation
        center_byte = (band_min + band_max) / 2.0

        # Create band mask from depth
        mask_label = f"mask_{band_name}"
        lines.append(
            f"[{dl}]lut=y='if(between(val,{band_min},{band_max}),255,0)',"
            f"gblur=sigma=0.8[{mask_label}]"
        )

        # Apply mask to source alpha
        masked_label = f"masked_{band_name}"
        lines.append(
            f"[{sl}]format=rgba,alphaextract[{sl}_alpha];"
            f"[{sl}_alpha][{mask_label}]blend=all_mode=multiply[{sl}_masked_alpha];"
            f"[{sl}]format=rgba[{sl}_rgba];"
            f"[{sl}_rgba][{sl}_masked_alpha]alphamerge[{masked_label}]"
        )

        # Compute motion expressions
        x_motion = build_band_motion_expr(camera, source_width, center_byte, "x", motion_scale)
        y_motion = build_band_motion_expr(camera, source_width, center_byte, "y", motion_scale)
        zoom_expr = build_band_zoom_expr(camera, motion_scale, zoom_scale)

        # Scale with zoom
        zoomed_label = f"zoomed_{band_name}"
        lines.append(
            f"[{masked_label}]scale='iw*{zoom_expr}':'ih*{zoom_expr}':flags=lanczos[{zoomed_label}]"
        )

        # Overlay with motion
        composite_label = f"comp_{band_name}"
        cx = f"(W-w)/2+{x_motion}"
        cy = f"(H-h)/2+{y_motion}"
        lines.append(
            f"[{prev_composite}][{zoomed_label}]overlay=x='{cx}':y='{cy}':shortest=1[{composite_label}]"
        )
        prev_composite = composite_label

    # Final: crop to output size and set fps
    lines.append(
        f"[{prev_composite}]crop={source_width}:{source_height}:"
        f"(iw-{source_width})/2:(ih-{source_height})/2,"
        f"fps=25,format=yuv420p[{output_label}]"
    )

    return ";\n".join(lines)


def build_parallax_ffmpeg_cmd(
    source_path: str,
    depth_path: str,
    output_path: str,
    camera: CameraGeometry,
    source_width: int = 1920,
    source_height: int = 1080,
    crf: int = 20,
) -> list[str]:
    """
    Build complete FFmpeg command for parallax render.

    Args:
        source_path: Path to source image/video
        depth_path: Path to depth map PNG
        output_path: Path for output video
        camera: Camera geometry
        source_width: Output width
        source_height: Output height
        crf: Video quality (lower = better)

    Returns:
        FFmpeg command as list of strings
    """
    filter_complex = build_parallax_filter(
        camera, source_width, source_height,
        depth_input="1:v", source_input="0:v",
        output_label="v",
    )

    return [
        "ffmpeg", "-v", "warning",
        "-loop", "1", "-i", str(source_path),
        "-loop", "1", "-i", str(depth_path),
        "-filter_complex", filter_complex,
        "-map", "[v]",
        "-t", str(camera.duration_sec),
        "-c:v", "libx264",
        "-crf", str(crf),
        "-preset", "slower",
        "-pix_fmt", "yuv420p",
        "-y",
        str(output_path),
    ]
