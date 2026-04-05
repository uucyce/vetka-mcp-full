"""
MARKER_B18 — CUT Color Pipeline.

Camera log decoding, gamut conversion, LUT import/apply.
Two-tier implementation:
  1. numpy-only fallback: builtin log curves + .cube parser (always works)
  2. colour-science: full gamut conversion + LUT formats (when installed)

Per Beta-1 feedback: "FFmpeg CLI for render, PyAV for preview/scopes/LUT."
This module is for preview/scopes path — operates on numpy float32 frames.

@status: active
@phase: B18
@task: tb_1773995016_3
@depends: cut_scope_renderer (frame extraction), cut_effects_engine (effect defs)
"""
from __future__ import annotations

import logging
import os
import re
import shutil
from pathlib import Path
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)

# Try importing colour-science (optional dependency)
try:
    import colour as colour_lib
    HAS_COLOUR = True
except ImportError:
    colour_lib = None  # type: ignore[assignment]
    HAS_COLOUR = False


# ---------------------------------------------------------------------------
# Camera Log Profiles — builtin numpy implementations (no colour-science)
# ---------------------------------------------------------------------------

# Registry: profile_name → { "log_func": str, "gamut": str | None, "decode": callable }
CAMERA_LOG_PROFILES: dict[str, dict[str, Any]] = {}


def _register_log_profile(
    name: str,
    aliases: list[str],
    gamut: str | None,
    decode_fn: Any,
    encode_fn: Any = None,
) -> None:
    """Register a camera log profile with decode function."""
    entry = {"name": name, "gamut": gamut, "decode": decode_fn, "encode": encode_fn}
    CAMERA_LOG_PROFILES[name] = entry
    for alias in aliases:
        CAMERA_LOG_PROFILES[alias] = entry


# --- V-Log (Panasonic GH5/GH6/S5) ---
def _decode_vlog(x: np.ndarray) -> np.ndarray:
    """V-Log → Linear. Panasonic spec."""
    cut1 = 0.181
    b = 0.00873
    c = 0.241514
    d = 0.598206
    out = np.where(
        x < cut1,
        (x - 0.125) / 5.6,
        np.power(10.0, (x - d) / c) - b,
    )
    return np.clip(out, 0, 1).astype(np.float32)


# --- S-Log3 (Sony FX6/A7S III) ---
def _decode_slog3(x: np.ndarray) -> np.ndarray:
    """S-Log3 → Linear. Sony spec."""
    a = 0.01125000
    b = 420.0 / 261.5
    c = 95.0 / 261.5
    cut_point = 171.2102946929 / 1023.0

    out = np.where(
        x >= cut_point,
        np.power(10.0, (x * 1023.0 - 420.0) / 261.5) * (0.18 + 0.01) - 0.01,
        (x * 1023.0 - 95.0) * 0.01125000 / (171.2102946929 - 95.0),
    )
    return np.clip(out, 0, 1).astype(np.float32)


# --- ARRI LogC3 (Alexa) ---
def _decode_logc3(x: np.ndarray) -> np.ndarray:
    """ARRI LogC3 EI800 → Linear."""
    a = 5.555556
    b = 0.052272
    c = 0.247190
    d = 0.385537
    e = 5.367655
    f = 0.092809
    cut = 0.010591

    out = np.where(
        x > e * cut + f,
        (np.power(10.0, (x - d) / c) - b) / a,
        (x - f) / e,
    )
    return np.clip(out, 0, 1).astype(np.float32)


# --- Canon Log 3 ---
def _decode_clog3(x: np.ndarray) -> np.ndarray:
    """Canon Log 3 → Linear. Canon spec."""
    # Simplified linearization
    cut = 0.04076162
    a = 14.98325
    b = 0.99510
    c = 0.12783
    d = 0.36726

    out = np.where(
        x < d,
        -(np.power(10.0, (d - x) / c) - 1.0) / a,
        (np.power(10.0, (x - d) / c) - 1.0) / a,
    )
    return np.clip(out, 0, 1).astype(np.float32)


# --- Generic sRGB (for Rec.709 content) ---
def _decode_srgb(x: np.ndarray) -> np.ndarray:
    """sRGB EOTF → Linear."""
    return np.where(
        x <= 0.04045,
        x / 12.92,
        np.power((x + 0.055) / 1.055, 2.4),
    ).astype(np.float32)


# Register all profiles
_register_log_profile("V-Log", ["vlog", "v-log", "panasonic"], "V-Gamut", _decode_vlog)
_register_log_profile("S-Log3", ["slog3", "s-log3", "sony"], "S-Gamut3.Cine", _decode_slog3)
_register_log_profile("ARRI LogC3", ["logc3", "logc", "arri", "alexa"], "ARRI Wide Gamut 3", _decode_logc3)
_register_log_profile("Canon Log 3", ["clog3", "c-log3", "canon"], None, _decode_clog3)
_register_log_profile("sRGB", ["rec709", "bt709", "linear"], None, _decode_srgb)


def list_log_profiles() -> list[dict[str, Any]]:
    """List available camera log profiles."""
    seen = set()
    result = []
    for name, entry in CAMERA_LOG_PROFILES.items():
        canonical = entry["name"]
        if canonical in seen:
            continue
        seen.add(canonical)
        result.append({
            "name": canonical,
            "gamut": entry["gamut"],
            "has_colour_science": HAS_COLOUR,
        })
    return result


def decode_log(frame_float32: np.ndarray, profile: str) -> np.ndarray:
    """Decode camera log → linear light.

    Args:
        frame_float32: float32 frame in [0, 1] range, shape (H, W, 3)
        profile: camera log profile name (e.g., "V-Log", "S-Log3")

    Returns:
        Linear light frame, float32 [0, 1]
    """
    key = profile.lower().replace(" ", "").replace("-", "").replace("_", "")

    # Try builtin profiles first (normalized key matching)
    for pname, entry in CAMERA_LOG_PROFILES.items():
        pkey = pname.lower().replace(" ", "").replace("-", "").replace("_", "")
        if pkey == key or pname.lower() == profile.lower():
            return entry["decode"](frame_float32)

    # Fallback: try colour-science
    if HAS_COLOUR:
        try:
            return colour_lib.log_decoding(frame_float32, function=profile).astype(np.float32)
        except Exception as e:
            logger.warning("colour.log_decoding failed for %s: %s", profile, e)

    logger.warning("Unknown log profile: %s, returning input unchanged", profile)
    return frame_float32


def convert_gamut(
    frame_linear: np.ndarray,
    input_gamut: str,
    output_gamut: str = "ITU-R BT.709",
) -> np.ndarray:
    """Convert gamut (requires colour-science).

    Falls back to identity if colour-science not available.
    """
    if not HAS_COLOUR:
        logger.debug("colour-science not available, skipping gamut conversion")
        return frame_linear

    try:
        return colour_lib.RGB_to_RGB(
            frame_linear,
            input_colourspace=input_gamut,
            output_colourspace=output_gamut,
        ).astype(np.float32)
    except Exception as e:
        logger.warning("Gamut conversion failed (%s → %s): %s", input_gamut, output_gamut, e)
        return frame_linear


# ---------------------------------------------------------------------------
# LUT Parser — pure numpy .cube parser (no colour-science needed)
# ---------------------------------------------------------------------------

class LUT3D:
    """3D LUT loaded from .cube file. Pure numpy implementation."""

    def __init__(self, title: str, size: int, table: np.ndarray):
        self.title = title
        self.size = size  # e.g., 17, 33, 65
        self.table = table  # shape (size, size, size, 3), float32

    def apply(self, frame: np.ndarray) -> np.ndarray:
        """Apply 3D LUT to frame using trilinear interpolation.

        Args:
            frame: float32 [0, 1], shape (H, W, 3)

        Returns:
            Graded frame, float32 [0, 1]
        """
        h, w, _ = frame.shape
        s = self.size - 1

        # Scale to LUT coordinates
        rgb = np.clip(frame, 0, 1) * s
        r0 = np.floor(rgb).astype(int)
        r1 = np.minimum(r0 + 1, s)
        frac = rgb - r0.astype(np.float32)

        ri0, gi0, bi0 = r0[:, :, 0], r0[:, :, 1], r0[:, :, 2]
        ri1, gi1, bi1 = r1[:, :, 0], r1[:, :, 1], r1[:, :, 2]
        fr, fg, fb = frac[:, :, 0], frac[:, :, 1], frac[:, :, 2]

        # Trilinear interpolation
        # .cube format: R varies fastest → reshape gives table[B, G, R, 3]
        c000 = self.table[bi0, gi0, ri0]
        c001 = self.table[bi1, gi0, ri0]
        c010 = self.table[bi0, gi1, ri0]
        c011 = self.table[bi1, gi1, ri0]
        c100 = self.table[bi0, gi0, ri1]
        c101 = self.table[bi1, gi0, ri1]
        c110 = self.table[bi0, gi1, ri1]
        c111 = self.table[bi1, gi1, ri1]

        fr3 = fr[:, :, np.newaxis]
        fg3 = fg[:, :, np.newaxis]
        fb3 = fb[:, :, np.newaxis]

        c00 = c000 * (1 - fr3) + c100 * fr3
        c01 = c001 * (1 - fr3) + c101 * fr3
        c10 = c010 * (1 - fr3) + c110 * fr3
        c11 = c011 * (1 - fr3) + c111 * fr3

        c0 = c00 * (1 - fg3) + c10 * fg3
        c1 = c01 * (1 - fg3) + c11 * fg3

        result = c0 * (1 - fb3) + c1 * fb3

        return np.clip(result, 0, 1).astype(np.float32)

    @staticmethod
    def from_cube_file(path: str) -> "LUT3D":
        """Parse a .cube LUT file (Resolve/Premiere standard)."""
        title = ""
        size = 0
        values: list[list[float]] = []

        with open(path, "r") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if line.startswith("TITLE"):
                    title = line.split('"')[1] if '"' in line else line.split(None, 1)[1]
                elif line.startswith("LUT_3D_SIZE"):
                    size = int(line.split()[-1])
                elif line.startswith(("DOMAIN_MIN", "DOMAIN_MAX", "LUT_1D_SIZE",
                                      "LUT_1D_INPUT_RANGE", "LUT_3D_INPUT_RANGE")):
                    continue  # skip metadata lines
                else:
                    parts = line.split()
                    if len(parts) >= 3:
                        try:
                            values.append([float(parts[0]), float(parts[1]), float(parts[2])])
                        except ValueError:
                            continue

        if size == 0:
            raise ValueError(f"No LUT_3D_SIZE found in {path}")
        expected = size ** 3
        if len(values) < expected:
            raise ValueError(f"Expected {expected} entries for size {size}, got {len(values)}")

        table = np.array(values[:expected], dtype=np.float32).reshape(size, size, size, 3)
        return LUT3D(title=title, size=size, table=table)


def read_lut(path: str) -> LUT3D | None:
    """Read a LUT file. Supports .cube (builtin) and other formats via colour-science."""
    p = Path(path)
    if not p.exists():
        return None

    ext = p.suffix.lower()

    if ext == ".cube":
        try:
            return LUT3D.from_cube_file(str(p))
        except Exception as e:
            logger.error("Failed to parse .cube LUT %s: %s", path, e)
            return None

    # For other formats, try colour-science
    if HAS_COLOUR:
        try:
            lut = colour_lib.read_LUT(str(p))
            # Wrap colour-science LUT in our interface
            return _ColourScienceLUTWrapper(lut)
        except Exception as e:
            logger.error("Failed to read LUT %s via colour-science: %s", path, e)
            return None

    logger.warning("Unsupported LUT format %s (install colour-science for support)", ext)
    return None


class _ColourScienceLUTWrapper(LUT3D):
    """Wrapper around colour-science LUT to match our LUT3D interface."""

    def __init__(self, colour_lut: Any):
        self._colour_lut = colour_lut
        super().__init__(
            title=str(getattr(colour_lut, "name", "Untitled")),
            size=getattr(colour_lut, "size", 33),
            table=np.zeros((1, 1, 1, 3)),  # placeholder
        )

    def apply(self, frame: np.ndarray) -> np.ndarray:
        result = self._colour_lut.apply(frame)
        return np.clip(result, 0, 1).astype(np.float32)


# ---------------------------------------------------------------------------
# LUT storage — import/list/delete for project
# ---------------------------------------------------------------------------

def get_lut_storage_dir(sandbox_root: str) -> str:
    """Get the LUT storage directory for a project."""
    d = os.path.join(sandbox_root, "cut_storage", "luts")
    os.makedirs(d, exist_ok=True)
    return d


def import_lut(sandbox_root: str, source_path: str) -> dict[str, Any]:
    """Import a LUT file into project storage."""
    p = Path(source_path)
    if not p.exists():
        return {"success": False, "error": "file_not_found"}

    # Validate it's parseable
    lut = read_lut(source_path)
    if lut is None:
        return {"success": False, "error": "invalid_lut_format"}

    dest_dir = get_lut_storage_dir(sandbox_root)
    dest = os.path.join(dest_dir, p.name)
    shutil.copy2(source_path, dest)

    return {
        "success": True,
        "lut_name": p.stem,
        "lut_path": dest,
        "lut_size": lut.size,
        "lut_title": lut.title,
    }


def list_project_luts(sandbox_root: str) -> list[dict[str, str]]:
    """List LUT files in project storage."""
    d = get_lut_storage_dir(sandbox_root)
    result = []
    for fname in sorted(os.listdir(d)):
        if fname.lower().endswith((".cube", ".spi1d", ".spi3d", ".csp", ".lut")):
            result.append({
                "name": Path(fname).stem,
                "filename": fname,
                "path": os.path.join(d, fname),
            })
    return result


# ---------------------------------------------------------------------------
# High-level: apply full color pipeline to a frame
# ---------------------------------------------------------------------------

# LUT cache — avoid re-parsing on every frame
_lut_cache: dict[str, LUT3D] = {}


def apply_color_pipeline(
    frame_uint8: np.ndarray,
    log_profile: str | None = None,
    lut_path: str | None = None,
) -> np.ndarray:
    """Apply full color pipeline: log decode → gamut → LUT.

    Args:
        frame_uint8: uint8 RGB frame (H, W, 3)
        log_profile: camera log profile name (e.g., "V-Log"), None = skip
        lut_path: path to .cube LUT file, None = skip

    Returns:
        Graded uint8 RGB frame (H, W, 3)
    """
    # Convert to float32 [0, 1]
    frame = frame_uint8.astype(np.float32) / 255.0

    # Step 1: Log decode
    if log_profile:
        frame = decode_log(frame, log_profile)

        # Step 1.5: Gamut conversion (if profile has known gamut)
        profile_entry = CAMERA_LOG_PROFILES.get(log_profile)
        if profile_entry and profile_entry.get("gamut"):
            frame = convert_gamut(frame, profile_entry["gamut"])

    # Step 2: LUT apply
    if lut_path:
        if lut_path not in _lut_cache:
            lut = read_lut(lut_path)
            if lut:
                _lut_cache[lut_path] = lut
        lut = _lut_cache.get(lut_path)
        if lut:
            frame = lut.apply(frame)

    # Convert back to uint8
    return (np.clip(frame, 0, 1) * 255).astype(np.uint8)


# ---------------------------------------------------------------------------
# Secondary Color Correction — HSL Qualifier + masked correction
# MARKER_SEC_COLOR: FCP7 Ch.28 — isolate color range, apply correction only there
# ---------------------------------------------------------------------------

def rgb_to_hsl(frame: np.ndarray) -> np.ndarray:
    """Convert float32 RGB [0,1] → HSL [0,1].

    H in [0,1] (0=red, 1/3=green, 2/3=blue), S and L in [0,1].
    Works on any shape (…, 3).
    """
    r, g, b = frame[..., 0], frame[..., 1], frame[..., 2]
    c_max = np.maximum(np.maximum(r, g), b)
    c_min = np.minimum(np.minimum(r, g), b)
    delta = c_max - c_min

    # Lightness
    l_val = (c_max + c_min) * 0.5

    # Saturation
    denom = 1.0 - np.abs(2.0 * l_val - 1.0)
    s_val = np.where(denom < 1e-8, 0.0, np.clip(delta / (denom + 1e-8), 0.0, 1.0))

    # Hue in [0,1]
    nz = delta > 1e-8
    h_r = np.where(nz & (c_max == r), ((g - b) / (delta + 1e-8)) % 6.0 / 6.0, 0.0)
    h_g = np.where(nz & (c_max == g), ((b - r) / (delta + 1e-8) + 2.0) / 6.0, 0.0)
    h_b = np.where(nz & (c_max == b), ((r - g) / (delta + 1e-8) + 4.0) / 6.0, 0.0)
    h_val = (h_r + h_g + h_b) % 1.0

    return np.stack([h_val, s_val, l_val], axis=-1).astype(np.float32)


def hsl_to_rgb(frame: np.ndarray) -> np.ndarray:
    """Convert float32 HSL [0,1] → RGB [0,1]. Works on any shape (…, 3)."""
    h, s, l = frame[..., 0], frame[..., 1], frame[..., 2]
    c = (1.0 - np.abs(2.0 * l - 1.0)) * s
    h6 = h * 6.0
    x = c * (1.0 - np.abs(h6 % 2.0 - 1.0))
    m = l - c * 0.5

    r = np.zeros_like(h)
    g_ch = np.zeros_like(h)
    b = np.zeros_like(h)

    for i, (rc, gc, bc) in enumerate([
        (c, x, 0), (x, c, 0), (0, c, x),
        (0, x, c), (x, 0, c), (c, 0, x),
    ]):
        mask = (h6 >= i) & (h6 < i + 1)
        r = np.where(mask, rc if isinstance(rc, (int, float)) else rc, r)
        g_ch = np.where(mask, gc if isinstance(gc, (int, float)) else gc, g_ch)
        b = np.where(mask, bc if isinstance(bc, (int, float)) else bc, b)

    return np.clip(np.stack([r + m, g_ch + m, b + m], axis=-1), 0.0, 1.0).astype(np.float32)


def build_hsl_mask(
    hsl_frame: np.ndarray,
    hue_center: float = 120.0,
    hue_width: float = 30.0,
    sat_min: float = 0.0,
    sat_max: float = 1.0,
    luma_min: float = 0.0,
    luma_max: float = 1.0,
    softness: float = 0.1,
) -> np.ndarray:
    """Compute soft HSL qualifier mask. Returns float32 [0..1] array (...).

    Soft edges extend OUTWARD from selection boundaries (zone qualifier model):
      - Hue: fully selected within ±hue_width; soft falloff extends ±(hue_width * softness) beyond.
      - Sat/Luma: fully inside [min, max]; soft falloff in [min-soft, min] and [max, max+soft].
    """
    h_norm = hsl_frame[..., 0]  # 0..1
    s = hsl_frame[..., 1]
    l = hsl_frame[..., 2]

    # ── Hue (circular) ──
    hc_norm = (hue_center % 360.0) / 360.0
    hw_norm = max(hue_width, 0.5) / 360.0
    soft_h = hw_norm * max(softness, 0.0)

    diff = np.abs(h_norm - hc_norm)
    diff = np.minimum(diff, 1.0 - diff)  # circular wrap

    # Fully selected: diff <= hw_norm; soft zone: hw_norm < diff <= hw_norm + soft_h
    h_mask = np.where(
        diff <= hw_norm,
        1.0,
        np.where(
            diff <= hw_norm + soft_h,
            np.clip(1.0 - (diff - hw_norm) / (soft_h + 1e-8), 0.0, 1.0),
            0.0,
        ),
    )

    # ── Saturation ──  fully in [sat_min, sat_max]; soft fade below sat_min and above sat_max
    s_range = max(sat_max - sat_min, 1e-4)
    s_soft = s_range * max(softness, 0.0)
    s_mask = np.where(
        (s >= sat_min) & (s <= sat_max),
        1.0,
        np.where(
            s < sat_min,
            np.clip((s - (sat_min - s_soft)) / (s_soft + 1e-8), 0.0, 1.0),
            np.clip(((sat_max + s_soft) - s) / (s_soft + 1e-8), 0.0, 1.0),
        ),
    )

    # ── Luma ──  same zone model
    l_range = max(luma_max - luma_min, 1e-4)
    l_soft = l_range * max(softness, 0.0)
    l_mask = np.where(
        (l >= luma_min) & (l <= luma_max),
        1.0,
        np.where(
            l < luma_min,
            np.clip((l - (luma_min - l_soft)) / (l_soft + 1e-8), 0.0, 1.0),
            np.clip(((luma_max + l_soft) - l) / (l_soft + 1e-8), 0.0, 1.0),
        ),
    )

    return (h_mask * s_mask * l_mask).astype(np.float32)


def apply_secondary_correction(
    frame: np.ndarray,
    qualifier: "dict[str, Any]",
    correction: "dict[str, Any]",
) -> np.ndarray:
    """Apply secondary color correction using HSL qualifier mask.

    Args:
        frame: float32 [0,1], shape (H, W, 3) or (N, 1, 3)
        qualifier: {hue_center, hue_width, sat_min, sat_max, luma_min, luma_max, softness}
        correction: {hue_shift, saturation, exposure}

    Returns:
        Corrected frame, same shape, float32 [0,1]
    """
    hsl = rgb_to_hsl(frame)
    mask = build_hsl_mask(
        hsl,
        hue_center=float(qualifier.get("hue_center", 120.0)),
        hue_width=float(qualifier.get("hue_width", 30.0)),
        sat_min=float(qualifier.get("sat_min", 0.0)),
        sat_max=float(qualifier.get("sat_max", 1.0)),
        luma_min=float(qualifier.get("luma_min", 0.0)),
        luma_max=float(qualifier.get("luma_max", 1.0)),
        softness=float(qualifier.get("softness", 0.1)),
    )
    mask3 = mask[..., np.newaxis]  # broadcast to RGB

    result = frame.copy()

    # Hue shift
    hue_shift = float(correction.get("hue_shift", 0.0))
    if abs(hue_shift) > 0.01:
        h_new = (hsl[..., 0] + hue_shift / 360.0) % 1.0
        hsl_shifted = np.stack([h_new, hsl[..., 1], hsl[..., 2]], axis=-1)
        rgb_shifted = hsl_to_rgb(hsl_shifted)
        result = result * (1.0 - mask3) + rgb_shifted * mask3
        hsl = rgb_to_hsl(result)

    # Saturation
    sat_adj = float(correction.get("saturation", 1.0))
    if abs(sat_adj - 1.0) > 0.01:
        s_new = np.clip(hsl[..., 1] * sat_adj, 0.0, 1.0)
        hsl_adj = np.stack([hsl[..., 0], s_new, hsl[..., 2]], axis=-1)
        rgb_adj = hsl_to_rgb(hsl_adj)
        result = result * (1.0 - mask3) + rgb_adj * mask3
        hsl = rgb_to_hsl(result)

    # Exposure (stops)
    exposure = float(correction.get("exposure", 0.0))
    if abs(exposure) > 0.01:
        factor = 2.0 ** exposure
        result = result * (1.0 - mask3) + (result * factor) * mask3

    return np.clip(result, 0.0, 1.0).astype(np.float32)


def write_secondary_lut_cube(
    qualifier: "dict[str, Any]",
    correction: "dict[str, Any]",
    size: int = 17,
) -> "str | None":
    """Generate a .cube 3D LUT implementing HSL-qualified secondary correction.

    Returns path to temp .cube file, or None if correction is trivial / error.
    .cube format: LUT_3D_SIZE N, R varies fastest (outer B, mid G, inner R).
    """
    import tempfile

    hue_shift = float(correction.get("hue_shift", 0.0))
    sat_adj = float(correction.get("saturation", 1.0))
    exposure = float(correction.get("exposure", 0.0))
    if abs(hue_shift) < 0.01 and abs(sat_adj - 1.0) < 0.01 and abs(exposure) < 0.01:
        return None  # Identity — skip

    try:
        s = size
        vals = np.linspace(0.0, 1.0, s, dtype=np.float32)
        # .cube order: R fastest → meshgrid gives entries for all (B,G,R) combos
        # Store as (s^3, 1, 3) to feed into apply_secondary_correction
        b_idx, g_idx, r_idx = np.meshgrid(np.arange(s), np.arange(s), np.arange(s), indexing="ij")
        colors = np.stack(
            [vals[r_idx.ravel()], vals[g_idx.ravel()], vals[b_idx.ravel()]],
            axis=-1,
        ).reshape(s * s * s, 1, 3)

        corrected = apply_secondary_correction(colors, qualifier, correction)
        corrected = corrected.reshape(s * s * s, 3)

        fd, path = tempfile.mkstemp(suffix=".cube", prefix="vetka_sec_")
        with os.fdopen(fd, "w") as f:
            f.write('TITLE "vetka_secondary_correction"\n')
            f.write(f"LUT_3D_SIZE {s}\n\n")
            for i in range(s * s * s):
                rv, gv, bv = corrected[i]
                f.write(f"{rv:.6f} {gv:.6f} {bv:.6f}\n")
        return path
    except Exception as e:
        logger.error("write_secondary_lut_cube failed: %s", e)
        return None
