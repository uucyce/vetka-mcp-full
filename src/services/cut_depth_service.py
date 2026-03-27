"""
MARKER_DEPTH_SERVICE — CUT Depth Map Generation Service.

Generates depth maps for timeline clips using AI models or FFmpeg luma extraction.
Depth maps are stored as sidecar PNG files alongside source media.

Two backends:
  1. AI (depth-pro / depth-anything-v2): High quality, requires transformers
  2. FFmpeg luma: Fast fallback, extracts brightness as pseudo-depth proxy

Convention: white=near (255), black=far (0) — matches DaVinci Resolve.

@status: active
@phase: D2
@task: tb_1774603064_1
@depends: cut_effects_engine (depth effects), photo_parallax_depth_bakeoff (AI backend)
"""
from __future__ import annotations

import hashlib
import json
import logging
import subprocess
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Default cache directory name for depth maps
DEPTH_CACHE_DIR = ".cut_depth"


@dataclass
class DepthResult:
    """Result of depth map generation for one source file."""
    source_path: str
    depth_path: str = ""          # path to uint16/uint8 depth PNG
    preview_path: str = ""        # path to 8-bit preview PNG
    success: bool = False
    skipped: bool = False         # True if depth already exists and force=False
    error: str = ""
    backend: str = ""             # "depth-pro", "depth-anything-v2-small", "ffmpeg-luma"
    polarity: str = "white_near"  # depth convention
    elapsed_ms: float = 0.0
    stats: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class DepthMetadata:
    """Depth metadata stored on a clip."""
    source: str = "none"         # "auto", "sidecar", "manual", "none"
    depth_path: str = ""         # path to depth map PNG
    preview_path: str = ""       # path to preview PNG
    model: str = ""              # "depth-pro", "depth-anything-v2-small", "ffmpeg-luma"
    polarity: str = "white_near" # convention: white=near, black=far
    generated_at: str = ""       # ISO timestamp

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @staticmethod
    def from_dict(d: dict[str, Any]) -> DepthMetadata:
        return DepthMetadata(
            source=str(d.get("source", "none")),
            depth_path=str(d.get("depth_path", "")),
            preview_path=str(d.get("preview_path", "")),
            model=str(d.get("model", "")),
            polarity=str(d.get("polarity", "white_near")),
            generated_at=str(d.get("generated_at", "")),
        )


def get_depth_cache_dir(source_path: str) -> Path:
    """Get the depth cache directory for a source file.

    Creates .cut_depth/ directory next to the source file.
    Uses content hash prefix for uniqueness.
    """
    src = Path(source_path)
    cache_dir = src.parent / DEPTH_CACHE_DIR
    # Hash source filename for subdirectory (avoids collision)
    name_hash = hashlib.md5(src.name.encode()).hexdigest()[:8]
    sub_dir = cache_dir / f"{src.stem}_{name_hash}"
    return sub_dir


def get_depth_paths(source_path: str) -> tuple[Path, Path]:
    """Get expected paths for depth map and preview.

    Returns: (depth_map_path, preview_path)
    """
    cache_dir = get_depth_cache_dir(source_path)
    return (
        cache_dir / "depth_map.png",
        cache_dir / "depth_preview.png",
    )


def generate_depth_ffmpeg_luma(
    source_path: str,
    output_dir: Path | None = None,
    frame_time: float = 0.0,
) -> DepthResult:
    """
    Generate pseudo-depth from luma channel using FFmpeg.

    Fast fallback when AI models aren't available.
    Extracts a single frame's luma channel as a greyscale depth proxy.
    Convention: bright areas → near, dark areas → far.
    """
    t0 = time.monotonic()

    if output_dir is None:
        output_dir = get_depth_cache_dir(source_path)

    output_dir.mkdir(parents=True, exist_ok=True)
    depth_path = output_dir / "depth_map.png"
    preview_path = output_dir / "depth_preview.png"

    try:
        # Extract single frame, convert to greyscale (luma), output as PNG
        cmd = [
            "ffmpeg", "-v", "error",
            "-ss", str(max(0.0, frame_time)),
            "-i", str(source_path),
            "-vframes", "1",
            "-vf", "format=gray",
            "-y",
            str(depth_path),
        ]
        result = subprocess.run(cmd, capture_output=True, timeout=30)
        if result.returncode != 0:
            return DepthResult(
                source_path=source_path,
                error=f"FFmpeg failed: {result.stderr.decode()[:200]}",
                backend="ffmpeg-luma",
            )

        # Create preview (same as depth for luma mode)
        if depth_path.exists():
            # Copy as preview (or could resize)
            cmd_preview = [
                "ffmpeg", "-v", "error",
                "-i", str(depth_path),
                "-vf", "scale=512:-1",
                "-y",
                str(preview_path),
            ]
            subprocess.run(cmd_preview, capture_output=True, timeout=10)

        elapsed = (time.monotonic() - t0) * 1000
        return DepthResult(
            source_path=source_path,
            depth_path=str(depth_path),
            preview_path=str(preview_path) if preview_path.exists() else "",
            success=True,
            backend="ffmpeg-luma",
            elapsed_ms=round(elapsed, 1),
        )

    except Exception as e:
        elapsed = (time.monotonic() - t0) * 1000
        return DepthResult(
            source_path=source_path,
            error=str(e),
            backend="ffmpeg-luma",
            elapsed_ms=round(elapsed, 1),
        )


def generate_depth_ai(
    source_path: str,
    backend: str = "depth-anything-v2-small",
    output_dir: Path | None = None,
    frame_time: float = 0.0,
) -> DepthResult:
    """
    Generate depth map using AI model (depth-pro or depth-anything).

    Requires transformers + torch. Falls back to FFmpeg luma if unavailable.
    Calls the existing bakeoff pipeline functions.
    """
    t0 = time.monotonic()

    if output_dir is None:
        output_dir = get_depth_cache_dir(source_path)

    output_dir.mkdir(parents=True, exist_ok=True)
    depth_path = output_dir / "depth_map.png"
    preview_path = output_dir / "depth_preview.png"

    # First extract a frame from video to work with
    frame_path = output_dir / "_frame_for_depth.png"
    try:
        cmd = [
            "ffmpeg", "-v", "error",
            "-ss", str(max(0.0, frame_time)),
            "-i", str(source_path),
            "-vframes", "1",
            "-y",
            str(frame_path),
        ]
        subprocess.run(cmd, capture_output=True, timeout=30)
        if not frame_path.exists():
            return DepthResult(
                source_path=source_path,
                error="Failed to extract frame for depth analysis",
                backend=backend,
            )
    except Exception as e:
        return DepthResult(
            source_path=source_path,
            error=f"Frame extraction failed: {e}",
            backend=backend,
        )

    # Try importing the bakeoff pipeline
    try:
        from scripts.photo_parallax_depth_bakeoff import (
            load_pipeline,
            normalize_to_16bit,
        )
        from PIL import Image
        import numpy as np

        model_ids = {
            "depth-pro": "apple/DepthPro-hf",
            "depth-anything-v2-small": "depth-anything/Depth-Anything-V2-Small-hf",
        }
        model_id = model_ids.get(backend, model_ids["depth-anything-v2-small"])

        pipe = load_pipeline(model_id)
        img = Image.open(frame_path).convert("RGB")
        output = pipe(img)
        predicted = output.get("predicted_depth") or output.get("depth")

        _, depth16, stats = normalize_to_16bit(predicted)

        # Save uint16 depth map
        depth_img = Image.fromarray(depth16)
        depth_img.save(str(depth_path))

        # Save 8-bit preview
        preview_8bit = (depth16 / 256).astype(np.uint8)
        Image.fromarray(preview_8bit).save(str(preview_path))

        # Cleanup temp frame
        frame_path.unlink(missing_ok=True)

        elapsed = (time.monotonic() - t0) * 1000
        return DepthResult(
            source_path=source_path,
            depth_path=str(depth_path),
            preview_path=str(preview_path),
            success=True,
            backend=backend,
            elapsed_ms=round(elapsed, 1),
            stats=stats,
        )

    except ImportError:
        logger.info("AI depth backend unavailable, falling back to FFmpeg luma")
        frame_path.unlink(missing_ok=True)
        return generate_depth_ffmpeg_luma(source_path, output_dir, frame_time)
    except Exception as e:
        frame_path.unlink(missing_ok=True)
        elapsed = (time.monotonic() - t0) * 1000
        return DepthResult(
            source_path=source_path,
            error=f"AI depth failed: {e}",
            backend=backend,
            elapsed_ms=round(elapsed, 1),
        )


def generate_depth(
    source_path: str,
    backend: str = "auto",
    force: bool = False,
    frame_time: float = 0.0,
) -> DepthResult:
    """
    Generate depth map for a source file.

    Args:
        source_path: Path to video/image file
        backend: "auto", "depth-pro", "depth-anything-v2-small", "ffmpeg-luma"
        force: Regenerate even if cached depth exists
        frame_time: Time offset for frame extraction (videos)

    Returns:
        DepthResult with paths and status
    """
    src = Path(source_path)
    if not src.exists():
        return DepthResult(source_path=source_path, error="source_not_found")

    # Check cache
    depth_path, preview_path = get_depth_paths(source_path)
    if not force and depth_path.exists():
        return DepthResult(
            source_path=source_path,
            depth_path=str(depth_path),
            preview_path=str(preview_path) if preview_path.exists() else "",
            success=True,
            skipped=True,
            backend="cached",
        )

    # Route to backend
    if backend == "ffmpeg-luma":
        return generate_depth_ffmpeg_luma(source_path, frame_time=frame_time)
    elif backend in ("depth-pro", "depth-anything-v2-small"):
        return generate_depth_ai(source_path, backend, frame_time=frame_time)
    else:
        # Auto: try AI first, fall back to FFmpeg
        return generate_depth_ai(source_path, "depth-anything-v2-small", frame_time=frame_time)


def build_depth_metadata(result: DepthResult) -> DepthMetadata:
    """Convert a DepthResult into clip metadata."""
    if not result.success:
        return DepthMetadata(source="none")

    return DepthMetadata(
        source="auto",
        depth_path=result.depth_path,
        preview_path=result.preview_path,
        model=result.backend,
        polarity=result.polarity,
        generated_at=datetime.now(timezone.utc).isoformat(),
    )
