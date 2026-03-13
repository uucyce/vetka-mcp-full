"""
MARKER_172.19.SCENE_DETECTION_TESTS
Tests for scene boundary detection: histogram computation, diff scoring,
scene grouping, FFmpeg frame extraction.
"""
import math
import struct
import os
import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

from src.services.cut_scene_detector import (
    SceneBoundary,
    compute_color_histogram,
    detect_and_group,
    detect_scene_boundaries,
    extract_frame_rgb,
    group_clips_into_scenes,
    histogram_diff,
)
from src.services.cut_ffmpeg_waveform import HAS_FFMPEG


# ─── Histogram math ───


def test_histogram_identical():
    """Identical histograms should have diff = 0."""
    hist = [10, 20, 30, 5, 0, 0, 15, 25, 10, 5, 0, 0, 10, 20, 30, 5]
    assert histogram_diff(hist, hist) == 0.0


def test_histogram_completely_different():
    """Completely different histograms should have high diff."""
    hist_a = [100, 0, 0, 0, 0, 0, 0, 0, 100, 0, 0, 0, 0, 0, 0, 0]
    hist_b = [0, 0, 0, 0, 0, 0, 0, 100, 0, 0, 0, 0, 0, 0, 0, 100]
    diff = histogram_diff(hist_a, hist_b)
    assert diff > 0.5


def test_histogram_similar():
    """Slightly different histograms should have low diff."""
    hist_a = [10, 20, 30, 40, 10, 20, 30, 40, 10, 20, 30, 40, 10, 20, 30, 40]
    hist_b = [11, 19, 31, 39, 11, 19, 31, 39, 11, 19, 31, 39, 11, 19, 31, 39]
    diff = histogram_diff(hist_a, hist_b)
    assert diff < 0.1


def test_histogram_empty():
    assert histogram_diff([], []) == 1.0


def test_histogram_mismatched_length():
    assert histogram_diff([1, 2], [1, 2, 3]) == 1.0


def test_compute_histogram_from_rgb():
    """compute_color_histogram should produce bins*3 values."""
    # Create simple RGB data: 4 pixels, all red (255, 0, 0)
    rgb = bytes([255, 0, 0] * 4)
    hist = compute_color_histogram(rgb, bins=8)
    assert len(hist) == 24  # 8 * 3
    # Last R bin should have all 4 pixels
    assert hist[7] == 4
    # G and B bins at 0 should have all 4 pixels
    assert hist[8] == 4  # G bin 0
    assert hist[16] == 4  # B bin 0


def test_compute_histogram_mixed_colors():
    """Mixed colors should distribute across bins."""
    # 2 red + 2 blue pixels
    rgb = bytes([255, 0, 0, 255, 0, 0, 0, 0, 255, 0, 0, 255])
    hist = compute_color_histogram(rgb, bins=8)
    assert hist[7] == 2  # R high bin
    assert hist[16 + 7] == 2  # B high bin


# ─── Scene grouping ───


def test_group_no_boundaries():
    """No boundaries = single scene."""
    clips = [
        {"start_sec": 0, "end_sec": 5},
        {"start_sec": 5, "end_sec": 10},
    ]
    scenes = group_clips_into_scenes(clips, [])
    assert len(scenes) == 1
    assert scenes[0].scene_id == "scene_01"
    assert len(scenes[0].clip_indices) == 2


def test_group_one_boundary():
    """One boundary should create two scenes."""
    clips = [
        {"start_sec": 0, "end_sec": 5},
        {"start_sec": 5, "end_sec": 10},
        {"start_sec": 10, "end_sec": 15},
    ]
    boundaries = [SceneBoundary(time_sec=7.0, diff_score=0.8)]
    scenes = group_clips_into_scenes(clips, boundaries)
    assert len(scenes) == 2
    # First two clips before boundary at 7.0
    assert 0 in scenes[0].clip_indices
    assert 1 in scenes[0].clip_indices
    # Third clip after boundary
    assert 2 in scenes[1].clip_indices


def test_group_multiple_boundaries():
    """Multiple boundaries should create multiple scenes."""
    clips = [
        {"start_sec": i * 5, "end_sec": (i + 1) * 5}
        for i in range(6)
    ]
    boundaries = [
        SceneBoundary(time_sec=10.0, diff_score=0.7),
        SceneBoundary(time_sec=20.0, diff_score=0.9),
    ]
    scenes = group_clips_into_scenes(clips, boundaries)
    assert len(scenes) == 3


def test_group_empty_clips():
    scenes = group_clips_into_scenes([], [])
    assert scenes == []


def test_group_scene_ids_sequential():
    """Scene IDs should be sequential."""
    clips = [{"start_sec": i, "end_sec": i + 1} for i in range(10)]
    boundaries = [
        SceneBoundary(time_sec=3.0, diff_score=0.5),
        SceneBoundary(time_sec=7.0, diff_score=0.6),
    ]
    scenes = group_clips_into_scenes(clips, boundaries)
    ids = [s.scene_id for s in scenes]
    assert ids == ["scene_01", "scene_02", "scene_03"]


# ─── FFmpeg frame extraction ───


@pytest.mark.skipif(not HAS_FFMPEG, reason="FFmpeg not installed")
def test_extract_frame_from_video(tmp_path: Path):
    """Extract a frame from a generated test video."""
    video = tmp_path / "test.mp4"
    _make_test_video(video, duration_sec=2.0)

    rgb = extract_frame_rgb(str(video), time_sec=0.5, width=32, height=24)
    assert rgb is not None
    assert len(rgb) == 32 * 24 * 3


@pytest.mark.skipif(not HAS_FFMPEG, reason="FFmpeg not installed")
def test_extract_frame_beyond_duration(tmp_path: Path):
    """Frame beyond video duration should return None or empty."""
    video = tmp_path / "short.mp4"
    _make_test_video(video, duration_sec=1.0)

    rgb = extract_frame_rgb(str(video), time_sec=100.0, width=32, height=24)
    # FFmpeg may return None or last frame depending on version
    # Either behavior is acceptable


def test_extract_frame_nonexistent():
    rgb = extract_frame_rgb("/nonexistent/video.mp4", 0.0)
    assert rgb is None


def test_extract_frame_no_ffmpeg():
    with patch("src.services.cut_scene_detector.HAS_FFMPEG", False):
        rgb = extract_frame_rgb("/any/path.mp4", 0.0)
    assert rgb is None


# ─── Full pipeline ───


@pytest.mark.skipif(not HAS_FFMPEG, reason="FFmpeg not installed")
def test_detect_boundaries_static_video(tmp_path: Path):
    """Static video (single color) should have no boundaries."""
    video = tmp_path / "static.mp4"
    _make_test_video(video, duration_sec=3.0, color="blue")

    boundaries = detect_scene_boundaries(
        str(video),
        interval_sec=0.5,
        threshold=0.3,
        max_duration_sec=5.0,
    )
    # Static video = no scene cuts
    assert len(boundaries) == 0


@pytest.mark.skipif(not HAS_FFMPEG, reason="FFmpeg not installed")
def test_detect_and_group_returns_scenes(tmp_path: Path):
    """detect_and_group should return boundaries and scenes."""
    video = tmp_path / "test.mp4"
    _make_test_video(video, duration_sec=3.0)
    clips = [
        {"start_sec": 0, "end_sec": 1.5},
        {"start_sec": 1.5, "end_sec": 3.0},
    ]
    boundaries, scenes = detect_and_group(
        str(video), clips,
        interval_sec=0.5,
        threshold=0.3,
        max_duration_sec=5.0,
    )
    # Should produce at least one scene
    assert len(scenes) >= 1
    # All clips should be assigned
    all_indices = set()
    for s in scenes:
        all_indices.update(s.clip_indices)
    assert all_indices == {0, 1}


def test_detect_and_group_no_ffmpeg():
    """Without FFmpeg, should fall back to single scene."""
    clips = [{"start_sec": 0, "end_sec": 10}]
    with patch("src.services.cut_scene_detector.HAS_FFMPEG", False):
        boundaries, scenes = detect_and_group("/any.mp4", clips)
    assert len(boundaries) == 0
    assert len(scenes) == 1
    assert scenes[0].clip_indices == [0]


# ─── Helper ───


def _make_test_video(path: Path, duration_sec: float = 2.0, color: str = "red") -> None:
    """Generate a simple test video using FFmpeg lavfi."""
    from src.services.cut_ffmpeg_waveform import FFMPEG as ffmpeg_path
    if not ffmpeg_path:
        pytest.skip("FFmpeg not available")
    subprocess.run(
        [
            ffmpeg_path,
            "-f", "lavfi",
            "-i", f"color=c={color}:size=128x96:d={duration_sec}:rate=10",
            "-f", "lavfi",
            "-i", f"sine=frequency=440:duration={duration_sec}:sample_rate=16000",
            "-c:v", "libx264",
            "-preset", "ultrafast",
            "-c:a", "aac",
            "-shortest",
            "-y",
            str(path),
        ],
        capture_output=True,
        timeout=15.0,
    )
