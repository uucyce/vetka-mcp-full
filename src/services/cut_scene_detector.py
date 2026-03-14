"""
MARKER_172.19 — Scene boundary detection from media files.
Uses FFmpeg to extract frames at intervals, computes color histograms,
detects scene cuts via histogram difference threshold.
Groups clips into scenes by temporal proximity + visual similarity.
"""
from __future__ import annotations

import math
import os
import struct
import subprocess
import tempfile
from dataclasses import dataclass, field
from typing import Any

from src.services.cut_ffmpeg_waveform import HAS_FFMPEG, FFMPEG


@dataclass
class SceneBoundary:
    """Detected scene cut point."""
    time_sec: float
    diff_score: float  # 0.0 = identical, 1.0 = completely different
    method: str = "histogram_diff_v1"


@dataclass
class DetectedScene:
    """A group of clips forming a scene."""
    scene_id: str
    start_sec: float
    end_sec: float
    clip_indices: list[int] = field(default_factory=list)
    boundary_score: float = 0.0  # avg diff score at boundaries


def extract_frame_rgb(
    media_path: str,
    time_sec: float,
    width: int = 64,
    height: int = 48,
    *,
    timeout_sec: float = 10.0,
) -> bytes | None:
    """Extract a single RGB frame from video at given timestamp via FFmpeg.

    Returns raw RGB24 bytes (width * height * 3) or None on failure.
    """
    if not HAS_FFMPEG or not os.path.isfile(media_path):
        return None

    cmd = [
        FFMPEG,  # type: ignore[list-item]
        "-ss", str(time_sec),
        "-i", media_path,
        "-vframes", "1",
        "-s", f"{width}x{height}",
        "-f", "rawvideo",
        "-pix_fmt", "rgb24",
        "pipe:1",
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, timeout=timeout_sec)
        if result.returncode != 0 or not result.stdout:
            return None
        expected = width * height * 3
        if len(result.stdout) < expected:
            return None
        return result.stdout[:expected]
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return None


def compute_color_histogram(rgb_data: bytes, bins: int = 16) -> list[int]:
    """Compute a simple RGB color histogram from raw RGB24 data.

    Returns flattened histogram: [R_bin0..R_binN, G_bin0..G_binN, B_bin0..B_binN]
    Total length = bins * 3.
    """
    histogram = [0] * (bins * 3)
    num_pixels = len(rgb_data) // 3
    bin_width = 256 / bins

    for i in range(num_pixels):
        r = rgb_data[i * 3]
        g = rgb_data[i * 3 + 1]
        b = rgb_data[i * 3 + 2]
        histogram[int(r / bin_width)] += 1
        histogram[bins + int(g / bin_width)] += 1
        histogram[bins * 2 + int(b / bin_width)] += 1

    # Normalize to [0, 1]
    total = max(1, num_pixels)
    return histogram  # Keep raw counts for chi-squared


def histogram_diff(hist_a: list[int], hist_b: list[int]) -> float:
    """Chi-squared distance between two histograms, normalized to [0, 1]."""
    if len(hist_a) != len(hist_b) or not hist_a:
        return 1.0
    chi_sq = 0.0
    for a, b in zip(hist_a, hist_b):
        if a + b > 0:
            chi_sq += (a - b) ** 2 / (a + b)
    # Normalize: max possible chi-sq is 2*num_pixels (when completely disjoint)
    max_possible = sum(hist_a) + sum(hist_b)
    if max_possible == 0:
        return 0.0
    return min(1.0, chi_sq / max(1.0, max_possible * 0.5))


def detect_scene_boundaries(
    media_path: str,
    *,
    interval_sec: float = 1.0,
    max_duration_sec: float = 300.0,
    threshold: float = 0.3,
    frame_width: int = 64,
    frame_height: int = 48,
    hist_bins: int = 16,
) -> list[SceneBoundary]:
    """Detect scene boundaries in a video file using histogram differences.

    Samples frames at `interval_sec` intervals and compares adjacent histograms.
    Returns list of detected scene cut points where diff exceeds threshold.
    """
    if not HAS_FFMPEG:
        return []

    # Probe duration if not provided
    duration = _probe_duration(media_path)
    if duration is None or duration <= 0:
        duration = max_duration_sec
    duration = min(duration, max_duration_sec)

    boundaries: list[SceneBoundary] = []
    prev_hist: list[int] | None = None

    t = 0.0
    while t < duration:
        rgb = extract_frame_rgb(media_path, t, frame_width, frame_height)
        if rgb is None:
            t += interval_sec
            continue

        hist = compute_color_histogram(rgb, bins=hist_bins)

        if prev_hist is not None:
            diff = histogram_diff(prev_hist, hist)
            if diff >= threshold:
                boundaries.append(SceneBoundary(
                    time_sec=round(t, 3),
                    diff_score=round(diff, 4),
                ))

        prev_hist = hist
        t += interval_sec

    return boundaries


def group_clips_into_scenes(
    clips: list[dict[str, Any]],
    boundaries: list[SceneBoundary],
    *,
    min_scene_gap_sec: float = 2.0,
) -> list[DetectedScene]:
    """Group clips into scenes using detected boundaries.

    Each scene spans from one boundary to the next. Clips are assigned
    to the scene that contains their start time.
    """
    if not clips:
        return []

    # Build scene time ranges from boundaries
    boundary_times = sorted(b.time_sec for b in boundaries)

    # If no boundaries detected, everything is one scene
    if not boundary_times:
        all_indices = list(range(len(clips)))
        max_end = max(
            (float(c.get("end_sec", 0) or c.get("start_sec", 0) or 0) for c in clips),
            default=0.0,
        )
        return [DetectedScene(
            scene_id="scene_01",
            start_sec=0.0,
            end_sec=max_end,
            clip_indices=all_indices,
        )]

    # Create scene ranges: [0, b1), [b1, b2), ..., [bN, end)
    scenes: list[DetectedScene] = []
    all_starts = [0.0] + boundary_times
    max_clip_end = max(
        (float(c.get("end_sec", 0) or c.get("start_sec", 0) or 0) for c in clips),
        default=0.0,
    )
    all_ends = boundary_times + [max_clip_end + 1.0]

    for i in range(len(all_starts)):
        scene_start = all_starts[i]
        scene_end = all_ends[i]
        scene_clips = []
        for ci, clip in enumerate(clips):
            clip_start = float(clip.get("start_sec", 0) or 0)
            if scene_start <= clip_start < scene_end:
                scene_clips.append(ci)

        if scene_clips:
            # Find boundary score for this scene
            b_score = 0.0
            if i > 0 and i - 1 < len(boundaries):
                b_score = boundaries[i - 1].diff_score

            scenes.append(DetectedScene(
                scene_id=f"scene_{len(scenes) + 1:02d}",
                start_sec=round(scene_start, 3),
                end_sec=round(scene_end, 3),
                clip_indices=scene_clips,
                boundary_score=round(b_score, 4),
            ))

    # Assign orphan clips (before first boundary) if not already assigned
    assigned = set()
    for s in scenes:
        assigned.update(s.clip_indices)
    orphans = [i for i in range(len(clips)) if i not in assigned]
    if orphans and scenes:
        scenes[0].clip_indices = sorted(set(scenes[0].clip_indices) | set(orphans))
    elif orphans:
        scenes.append(DetectedScene(
            scene_id="scene_01",
            start_sec=0.0,
            end_sec=max_clip_end,
            clip_indices=orphans,
        ))

    return scenes


def _probe_duration(media_path: str) -> float | None:
    """Get media duration in seconds via ffprobe."""
    ffprobe = (FFMPEG or "").replace("ffmpeg", "ffprobe")
    if not ffprobe or not os.path.isfile(media_path):
        return None
    try:
        result = subprocess.run(
            [ffprobe, "-v", "quiet", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", media_path],
            capture_output=True, text=True, timeout=10.0,
        )
        if result.returncode == 0 and result.stdout.strip():
            return float(result.stdout.strip())
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError, ValueError):
        pass
    return None


def detect_and_group(
    media_path: str,
    clips: list[dict[str, Any]],
    *,
    interval_sec: float = 1.0,
    threshold: float = 0.3,
    max_duration_sec: float = 300.0,
) -> tuple[list[SceneBoundary], list[DetectedScene]]:
    """Full pipeline: detect boundaries + group clips.

    Returns (boundaries, scenes). Falls back to single scene if FFmpeg unavailable.
    """
    boundaries = detect_scene_boundaries(
        media_path,
        interval_sec=interval_sec,
        threshold=threshold,
        max_duration_sec=max_duration_sec,
    )
    scenes = group_clips_into_scenes(clips, boundaries)
    return boundaries, scenes
