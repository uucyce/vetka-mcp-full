"""
MARKER_170.8.MARKER_BUNDLE_CONTRACT
Tests for music-sync marker bundle creation.

Tests:
1. create_marker_bundle_from_slices — basic marker creation
2. hybrid_merge_slices — overlapping window merge
3. Sync offset application
4. Empty/edge cases
"""
import pytest

from src.services.cut_audio_intel_eval import SliceWindow, SyncResult
from src.services.cut_marker_bundle_service import (
    create_marker_bundle_from_slices,
    hybrid_merge_slices,
)


# --- Test 1: hybrid_merge_slices ---

def test_hybrid_merge_non_overlapping():
    """Non-overlapping windows should remain separate."""
    windows = [
        SliceWindow(start_sec=0.0, end_sec=1.0, confidence=0.8, method="energy_pause_v1"),
        SliceWindow(start_sec=2.0, end_sec=3.0, confidence=0.9, method="energy_pause_v1"),
        SliceWindow(start_sec=5.0, end_sec=6.0, confidence=0.7, method="transcript_pause_v1"),
    ]
    merged = hybrid_merge_slices(windows)
    assert len(merged) == 3
    assert merged[0]["start_sec"] == 0.0
    assert merged[0]["end_sec"] == 1.0
    assert merged[1]["start_sec"] == 2.0
    assert merged[2]["start_sec"] == 5.0


def test_hybrid_merge_overlapping():
    """Overlapping windows should merge, keeping best confidence."""
    windows = [
        SliceWindow(start_sec=0.0, end_sec=1.5, confidence=0.8, method="energy_pause_v1"),
        SliceWindow(start_sec=1.0, end_sec=2.5, confidence=0.95, method="transcript_pause_v1"),
        SliceWindow(start_sec=5.0, end_sec=6.0, confidence=0.7, method="energy_pause_v1"),
    ]
    merged = hybrid_merge_slices(windows)
    assert len(merged) == 2
    # First merged window spans 0.0–2.5 with hybrid method
    assert merged[0]["start_sec"] == 0.0
    assert merged[0]["end_sec"] == 2.5
    assert merged[0]["confidence"] == 0.95
    assert merged[0]["method"] == "hybrid"
    # Second window unchanged
    assert merged[1]["start_sec"] == 5.0


def test_hybrid_merge_adjacent_within_threshold():
    """Adjacent windows within threshold should merge."""
    windows = [
        SliceWindow(start_sec=0.0, end_sec=1.0, confidence=0.8, method="energy_pause_v1"),
        SliceWindow(start_sec=1.1, end_sec=2.0, confidence=0.85, method="energy_pause_v1"),
    ]
    merged = hybrid_merge_slices(windows, overlap_threshold_sec=0.15)
    assert len(merged) == 1
    assert merged[0]["end_sec"] == 2.0


def test_hybrid_merge_empty():
    """Empty input returns empty list."""
    assert hybrid_merge_slices([]) == []


# --- Test 2: create_marker_bundle_from_slices ---

def test_create_marker_bundle_basic():
    """Create a marker bundle from 3 slice windows."""
    windows = [
        SliceWindow(start_sec=0.0, end_sec=1.5, confidence=0.82, method="energy_pause_v1"),
        SliceWindow(start_sec=3.0, end_sec=4.5, confidence=0.82, method="energy_pause_v1"),
        SliceWindow(start_sec=7.0, end_sec=8.2, confidence=0.82, method="energy_pause_v1"),
    ]
    bundle = create_marker_bundle_from_slices(
        project_id="test_project",
        timeline_id="main",
        track_id="track_punch",
        media_path="/test/punch.wav",
        slice_windows=windows,
        sync_result=None,
        slice_method="energy_only",
    )

    assert bundle["schema_version"] == "cut_time_marker_bundle_v1"
    assert bundle["project_id"] == "test_project"
    assert len(bundle["items"]) == 3

    # Each marker should be a valid cut_time_marker_v1
    for item in bundle["items"]:
        assert item["schema_version"] == "cut_time_marker_v1"
        assert item["kind"] == "music_sync"
        assert item["media_path"] == "/test/punch.wav"
        assert item["status"] == "active"
        assert "marker_id" in item
        assert item["start_sec"] >= 0.0
        assert item["end_sec"] > item["start_sec"]
        # Check context_slice has source info
        ctx = item["context_slice"]
        assert ctx is not None
        assert ctx["source"] == "energy_pause"
        assert "music" in ctx["tags"]

    # music_sync_meta should exist
    meta = bundle.get("music_sync_meta")
    assert meta is not None
    assert meta["marker_count"] == 3
    assert meta["slice_method"] == "energy_only"
    assert meta["source_track_id"] == "track_punch"


def test_create_marker_bundle_with_sync_offset():
    """Sync offset should shift all marker times."""
    windows = [
        SliceWindow(start_sec=1.0, end_sec=2.0, confidence=0.82, method="energy_pause_v1"),
        SliceWindow(start_sec=5.0, end_sec=6.0, confidence=0.82, method="energy_pause_v1"),
    ]
    sync = SyncResult(
        detected_offset_sec=0.15,
        confidence=0.92,
        method="peaks+correlation_v1",
        peak_value=0.85,
    )
    bundle = create_marker_bundle_from_slices(
        project_id="test_project",
        timeline_id="main",
        track_id="track_punch",
        media_path="/test/punch.wav",
        slice_windows=windows,
        sync_result=sync,
        slice_method="hybrid_merge",
    )

    # Markers should be offset by +0.15s
    items = bundle["items"]
    assert len(items) == 2
    assert abs(items[0]["start_sec"] - 1.15) < 0.001
    assert abs(items[0]["end_sec"] - 2.15) < 0.001
    assert abs(items[1]["start_sec"] - 5.15) < 0.001

    # Sync status should be populated
    meta = bundle["music_sync_meta"]
    assert meta["sync_status"]["method"] == "peaks+correlation_v1"
    assert meta["sync_status"]["confidence"] == 0.92
    assert meta["sync_status"]["offset_sec"] == 0.15


def test_create_marker_bundle_empty_windows():
    """Empty slice windows should produce empty bundle."""
    bundle = create_marker_bundle_from_slices(
        project_id="test_project",
        timeline_id="main",
        track_id="track_punch",
        media_path="/test/punch.wav",
        slice_windows=[],
    )
    assert bundle["schema_version"] == "cut_time_marker_bundle_v1"
    assert len(bundle["items"]) == 0
    meta = bundle["music_sync_meta"]
    assert meta["marker_count"] == 0


def test_create_marker_bundle_hybrid_sources():
    """Mixed sources should produce hybrid markers when overlapping."""
    windows = [
        SliceWindow(start_sec=0.0, end_sec=1.5, confidence=0.8, method="energy_pause_v1"),
        SliceWindow(start_sec=1.0, end_sec=2.5, confidence=0.95, method="transcript_pause_v1"),
        SliceWindow(start_sec=5.0, end_sec=6.0, confidence=0.7, method="energy_pause_v1"),
    ]
    bundle = create_marker_bundle_from_slices(
        project_id="test_project",
        timeline_id="main",
        track_id="track_punch",
        media_path="/test/punch.wav",
        slice_windows=windows,
        slice_method="hybrid_merge",
    )

    items = bundle["items"]
    assert len(items) == 2  # Two merged windows (first two overlap)

    # First marker should be hybrid source
    assert items[0]["context_slice"]["source"] == "hybrid"
    assert items[0]["score"] == 0.95  # Best confidence

    # Second marker should be energy_pause
    assert items[1]["context_slice"]["source"] == "energy_pause"
