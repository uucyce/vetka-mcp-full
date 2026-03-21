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
