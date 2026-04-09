"""
MARKER_189.2 — VideoScanner: media analysis for video files.
Wraps existing ffprobe, scene detection, and thumbnail extraction.
Returns ScanResult with segments, metadata, thumbnails, and SignalEdge[].

@status: active
@phase: 189
@depends: cut_scene_detector, cut_ffmpeg_waveform, scan_types
@used_by: cut_routes (scan-matrix-async)
"""
from __future__ import annotations

import json
import logging
import os
import subprocess
import time
from pathlib import Path
from typing import Any

from src.scanners.scan_types import (
    MediaMetadata,
    ScanResult,
    SceneSegment,
    SignalEdge,
)
from src.services.cut_ffmpeg_waveform import FFMPEG, HAS_FFMPEG
from src.services.cut_scene_detector import (
    SceneBoundary,
    detect_scene_boundaries,
)

logger = logging.getLogger(__name__)

VIDEO_EXTENSIONS = {
    ".mp4", ".mov", ".m4v", ".avi", ".mkv", ".webm",
    ".mxf", ".r3d", ".braw", ".prores", ".mts", ".m2ts",
}

FFPROBE = (FFMPEG or "").replace("ffmpeg", "ffprobe") if FFMPEG else None
HAS_FFPROBE = bool(FFPROBE and os.path.isfile(FFPROBE))


def _ffprobe_metadata(media_path: str) -> MediaMetadata | None:
    """Extract full metadata via ffprobe JSON output."""
    if not HAS_FFPROBE or not os.path.isfile(media_path):
        return None
    try:
        result = subprocess.run(
            [
                FFPROBE,  # type: ignore[list-item]
                "-v", "quiet",
                "-print_format", "json",
                "-show_format",
                "-show_streams",
                media_path,
            ],
            capture_output=True, text=True, timeout=15.0,
        )
        if result.returncode != 0:
            return None
        data = json.loads(result.stdout)
    except (subprocess.TimeoutExpired, json.JSONDecodeError, OSError):
        return None

    fmt = data.get("format") or {}
    duration = float(fmt.get("duration") or 0)
    file_size = int(fmt.get("size") or 0)
    container = (fmt.get("format_name") or "").split(",")[0]

    # Find video stream
    video_stream: dict[str, Any] = {}
    audio_stream: dict[str, Any] = {}
    for stream in data.get("streams") or []:
        codec_type = stream.get("codec_type", "")
        if codec_type == "video" and not video_stream:
            video_stream = stream
        elif codec_type == "audio" and not audio_stream:
            audio_stream = stream

    # FPS from video stream
    fps = 0.0
    r_frame_rate = video_stream.get("r_frame_rate", "")
    if "/" in r_frame_rate:
        parts = r_frame_rate.split("/")
        try:
            fps = round(int(parts[0]) / max(1, int(parts[1])), 3)
        except (ValueError, ZeroDivisionError):
            pass

    # Timecode from tags
    tc = ""
    tags = video_stream.get("tags") or {}
    tc = tags.get("timecode", "") or tags.get("TIMECODE", "")

    return MediaMetadata(
        path=media_path,
        duration_sec=round(duration, 3),
        codec=video_stream.get("codec_name", ""),
        width=int(video_stream.get("width") or 0),
        height=int(video_stream.get("height") or 0),
        fps=fps,
        sample_rate=int(audio_stream.get("sample_rate") or 0),
        channels=int(audio_stream.get("channels") or 0),
        timecode_start=tc,
        file_size_bytes=file_size,
        media_type="video",
        container=container,
    )


def _extract_thumbnail(
    media_path: str,
    time_sec: float,
    output_dir: str,
    index: int,
    *,
    width: int = 320,
    height: int = 180,
) -> str | None:
    """Extract a single thumbnail frame at given timestamp."""
    if not HAS_FFMPEG:
        return None
    os.makedirs(output_dir, exist_ok=True)
    basename = Path(media_path).stem
    out_path = os.path.join(output_dir, f"{basename}_thumb_{index:04d}.jpg")
    if os.path.isfile(out_path):
        return out_path
    try:
        result = subprocess.run(
            [
                FFMPEG,  # type: ignore[list-item]
                "-ss", str(time_sec),
                "-i", media_path,
                "-vframes", "1",
                "-s", f"{width}x{height}",
                "-q:v", "3",
                "-y",
                out_path,
            ],
            capture_output=True, timeout=10.0,
        )
        if result.returncode == 0 and os.path.isfile(out_path):
            return out_path
    except (subprocess.TimeoutExpired, OSError):
        pass
    return None


def _extract_thumbnail_grid(
    media_path: str,
    duration_sec: float,
    output_dir: str,
    *,
    max_thumbs: int = 12,
    width: int = 320,
    height: int = 180,
) -> list[str]:
    """Extract evenly-spaced thumbnails across the video duration."""
    if duration_sec <= 0 or not HAS_FFMPEG:
        return []
    interval = duration_sec / max(1, max_thumbs)
    paths: list[str] = []
    for i in range(max_thumbs):
        t = interval * i + interval * 0.5  # mid-point of each interval
        if t >= duration_sec:
            break
        thumb = _extract_thumbnail(media_path, t, output_dir, i, width=width, height=height)
        if thumb:
            paths.append(thumb)
    return paths


def _boundaries_to_segments(
    boundaries: list[SceneBoundary],
    total_duration: float,
    source_path: str,
) -> list[SceneSegment]:
    """Convert scene boundaries to segment list."""
    if not boundaries:
        return [
            SceneSegment(
                segment_id="seg_001",
                start_sec=0.0,
                end_sec=round(total_duration, 3),
                duration_sec=round(total_duration, 3),
            )
        ]
    segments: list[SceneSegment] = []
    starts = [0.0] + [b.time_sec for b in boundaries]
    ends = [b.time_sec for b in boundaries] + [total_duration]
    for i, (s, e) in enumerate(zip(starts, ends)):
        seg_dur = round(e - s, 3)
        if seg_dur <= 0:
            continue
        diff = boundaries[i - 1].diff_score if i > 0 and i - 1 < len(boundaries) else 0.0
        segments.append(
            SceneSegment(
                segment_id=f"seg_{i + 1:03d}",
                start_sec=round(s, 3),
                end_sec=round(e, 3),
                duration_sec=seg_dur,
                diff_score=round(diff, 4),
            )
        )
    return segments


def _build_structural_edges(
    source_path: str,
    segments: list[SceneSegment],
) -> list[SignalEdge]:
    """Build structural + temporal SignalEdge[] between adjacent segments."""
    edges: list[SignalEdge] = []
    basename = Path(source_path).stem
    for i in range(len(segments) - 1):
        a = segments[i]
        b = segments[i + 1]
        edges.append(SignalEdge(
            source=f"{basename}:{a.segment_id}",
            target=f"{basename}:{b.segment_id}",
            channel="temporal",
            evidence=[f"sequential segments, gap={round(b.start_sec - a.end_sec, 3)}s"],
            confidence=0.95,
            weight=0.8,
            source_type="video",
            target_type="video",
        ))
    return edges


def scan_video(
    media_path: str,
    *,
    thumbnail_dir: str = "",
    max_thumbs: int = 12,
    scene_interval_sec: float = 1.0,
    scene_threshold: float = 0.3,
    max_scan_duration_sec: float = 600.0,
) -> ScanResult:
    """Run full VideoScanner pipeline on a single video file.

    Steps:
    1. ffprobe metadata extraction
    2. Scene boundary detection
    3. Thumbnail grid extraction
    4. SignalEdge generation

    Returns ScanResult with all extracted data.
    """
    t0 = time.monotonic()
    result = ScanResult(scanner_type="video", source_path=media_path)

    if not os.path.isfile(media_path):
        result.extraction_status = "error"
        result.extraction_error = "file_not_found"
        result.elapsed_sec = time.monotonic() - t0
        return result

    ext = Path(media_path).suffix.lower()
    if ext not in VIDEO_EXTENSIONS:
        result.extraction_status = "error"
        result.extraction_error = f"unsupported_extension:{ext}"
        result.elapsed_sec = time.monotonic() - t0
        return result

    result.extraction_status = "running"

    # Step 1: ffprobe metadata
    meta = _ffprobe_metadata(media_path)
    if meta is None:
        # Fallback: file exists but ffprobe failed
        meta = MediaMetadata(
            path=media_path,
            media_type="video",
            file_size_bytes=os.path.getsize(media_path),
        )
        result.extraction_error = "ffprobe_failed"
    result.metadata = meta

    duration = meta.duration_sec
    if duration <= 0:
        # Can't do much without duration
        result.segments = [
            SceneSegment(segment_id="seg_001", start_sec=0.0, end_sec=0.0, duration_sec=0.0)
        ]
        result.extraction_status = "complete"
        result.elapsed_sec = time.monotonic() - t0
        return result

    # Step 2: Scene detection
    scan_dur = min(duration, max_scan_duration_sec)
    try:
        boundaries = detect_scene_boundaries(
            media_path,
            interval_sec=scene_interval_sec,
            threshold=scene_threshold,
            max_duration_sec=scan_dur,
        )
    except Exception as exc:
        logger.warning("Scene detection failed for %s: %s", media_path, exc)
        boundaries = []

    result.segments = _boundaries_to_segments(boundaries, duration, media_path)

    # Step 3: Thumbnails
    thumb_dir = thumbnail_dir or os.path.join(
        os.path.dirname(media_path), ".vetka_thumbs"
    )
    try:
        result.thumbnail_paths = _extract_thumbnail_grid(
            media_path, duration, thumb_dir, max_thumbs=max_thumbs,
        )
    except Exception as exc:
        logger.warning("Thumbnail extraction failed for %s: %s", media_path, exc)

    # Attach thumbnail paths to segments
    if result.thumbnail_paths and result.segments:
        thumbs_per_seg = max(1, len(result.thumbnail_paths) // len(result.segments))
        for i, seg in enumerate(result.segments):
            thumb_idx = min(i * thumbs_per_seg, len(result.thumbnail_paths) - 1)
            seg.thumbnail_path = result.thumbnail_paths[thumb_idx]

    # Step 4: SignalEdge generation
    result.edges = _build_structural_edges(media_path, result.segments)

    result.extraction_status = "complete"
    result.elapsed_sec = time.monotonic() - t0
    logger.info(
        "VideoScanner complete: %s — %d segments, %d thumbs, %.1fs",
        Path(media_path).name, len(result.segments),
        len(result.thumbnail_paths), result.elapsed_sec,
    )
    return result
