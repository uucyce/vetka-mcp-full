"""
MARKER_B47: Tests for conform/relink system (FCP7 Ch.44).
Tests MediaLinker, fuzzy matching, and path remapping.
"""
import os
from pathlib import Path

import pytest

from src.services.cut_conform import (
    check_project_media,
    relink_media,
    _collect_source_paths,
    _fuzzy_match_score,
    MediaStatus,
)


# ─── _collect_source_paths ───


def test_collect_empty_timeline():
    assert _collect_source_paths({}) == {}
    assert _collect_source_paths({"lanes": []}) == {}


def test_collect_paths_from_clips():
    timeline = {
        "lanes": [
            {
                "clips": [
                    {"source_path": "/media/a.mp4", "clip_id": "c1"},
                    {"source_path": "/media/b.mp4", "clip_id": "c2"},
                    {"source_path": "/media/a.mp4", "clip_id": "c3"},  # dupe
                ]
            }
        ]
    }
    paths = _collect_source_paths(timeline)
    assert len(paths) == 2
    assert set(paths["/media/a.mp4"]) == {"c1", "c3"}
    assert paths["/media/b.mp4"] == ["c2"]


# ─── _fuzzy_match_score ───


def test_fuzzy_exact_name(tmp_path: Path):
    f = tmp_path / "clip_001.mp4"
    f.write_bytes(b"\x00" * 1000)
    score, reason = _fuzzy_match_score("clip_001.mp4", 1000, str(f))
    assert score >= 0.8
    assert "exact_name" in reason
    assert "size_match" in reason


def test_fuzzy_stem_match(tmp_path: Path):
    f = tmp_path / "clip_001.mov"
    f.write_bytes(b"\x00" * 100)
    score, reason = _fuzzy_match_score("clip_001.mp4", 500, str(f))
    assert 0.3 < score < 0.7
    assert "stem_match" in reason


def test_fuzzy_no_match(tmp_path: Path):
    f = tmp_path / "totally_different.mp4"
    f.write_bytes(b"\x00" * 100)
    score, reason = _fuzzy_match_score("clip_001.mp4", 100, str(f))
    assert score == 0.0


def test_fuzzy_zero_original_size(tmp_path: Path):
    f = tmp_path / "clip.mp4"
    f.write_bytes(b"\x00" * 100)
    score, reason = _fuzzy_match_score("clip.mp4", 0, str(f))
    assert score > 0.5  # exact name match still works


# ─── check_project_media ───


def test_check_all_online(tmp_path: Path):
    """All files exist → all online."""
    f1 = tmp_path / "a.mp4"
    f2 = tmp_path / "b.mp4"
    f1.write_bytes(b"\x00" * 100)
    f2.write_bytes(b"\x00" * 200)

    timeline = {
        "lanes": [{"clips": [
            {"source_path": str(f1), "clip_id": "c1"},
            {"source_path": str(f2), "clip_id": "c2"},
        ]}]
    }
    results, _ = check_project_media(timeline)
    assert len(results) == 2
    assert all(r.status == "online" for r in results)
    assert results[0].file_size > 0


def test_check_offline_no_search():
    """Missing file, no search roots → offline with no suggestions."""
    timeline = {
        "lanes": [{"clips": [
            {"source_path": "/nonexistent/clip.mp4", "clip_id": "c1"},
        ]}]
    }
    results, _ = check_project_media(timeline)
    assert len(results) == 1
    assert results[0].status == "offline"
    assert results[0].suggestions == []


def test_check_offline_with_search(tmp_path: Path):
    """Missing file, search root with matching filename → moved + suggestion."""
    # Create the "moved" file in search root
    search_dir = tmp_path / "new_location"
    search_dir.mkdir()
    moved_file = search_dir / "clip_001.mp4"
    moved_file.write_bytes(b"\x00" * 500)

    timeline = {
        "lanes": [{"clips": [
            {"source_path": "/old_location/clip_001.mp4", "clip_id": "c1"},
        ]}]
    }
    results, _ = check_project_media(timeline, search_roots=[str(search_dir)])
    assert len(results) == 1
    r = results[0]
    assert r.status == "moved"  # high confidence match
    assert len(r.suggestions) >= 1
    assert r.suggestions[0]["path"] == str(moved_file)
    assert r.suggestions[0]["score"] >= 0.5


# ─── relink_media ───


def test_relink_basic(tmp_path: Path):
    """Remap one path → clips updated."""
    new_file = tmp_path / "new_clip.mp4"
    new_file.write_bytes(b"\x00" * 100)

    timeline = {
        "lanes": [{"clips": [
            {"source_path": "/old/clip.mp4", "clip_id": "c1"},
            {"source_path": "/old/clip.mp4", "clip_id": "c2"},
            {"source_path": "/other/file.mp4", "clip_id": "c3"},
        ]}]
    }
    result = relink_media(timeline, {"/old/clip.mp4": str(new_file)})
    assert result["remapped_count"] == 2
    assert "c1" in result["clip_ids_affected"]
    assert "c2" in result["clip_ids_affected"]
    # Verify timeline mutated
    assert timeline["lanes"][0]["clips"][0]["source_path"] == str(new_file)
    assert timeline["lanes"][0]["clips"][2]["source_path"] == "/other/file.mp4"


def test_relink_target_not_found():
    """Remap to nonexistent file → not_found."""
    timeline = {
        "lanes": [{"clips": [
            {"source_path": "/old/clip.mp4", "clip_id": "c1"},
        ]}]
    }
    result = relink_media(timeline, {"/old/clip.mp4": "/nonexistent/new.mp4"})
    assert result["remapped_count"] == 0
    assert "/nonexistent/new.mp4" in result["not_found"]


def test_relink_empty_remap():
    """Empty remap → no changes."""
    timeline = {"lanes": [{"clips": [{"source_path": "/a.mp4", "clip_id": "c1"}]}]}
    result = relink_media(timeline, {})
    assert result["remapped_count"] == 0


# ─── MARKER_B49: Auto-relink + duration matching ───


def test_auto_relink_above_threshold(tmp_path: Path):
    """High-confidence match + threshold → auto_remap populated."""
    search_dir = tmp_path / "moved"
    search_dir.mkdir()
    moved = search_dir / "clip.mp4"
    moved.write_bytes(b"\x00" * 500)

    timeline = {
        "lanes": [{"clips": [
            {"source_path": "/old/clip.mp4", "clip_id": "c1", "duration_sec": 10.0},
        ]}]
    }
    results, auto_remap = check_project_media(
        timeline, search_roots=[str(search_dir)],
        auto_relink_threshold=0.5,
    )
    assert len(results) == 1
    # Should have auto-remap since exact name match scores 0.6+
    assert "/old/clip.mp4" in auto_remap
    assert auto_remap["/old/clip.mp4"] == str(moved)


def test_auto_relink_below_threshold(tmp_path: Path):
    """Low score + high threshold → no auto_remap."""
    search_dir = tmp_path / "moved"
    search_dir.mkdir()
    moved = search_dir / "clip.mov"  # different extension
    moved.write_bytes(b"\x00" * 100)

    timeline = {
        "lanes": [{"clips": [
            {"source_path": "/old/clip.mp4", "clip_id": "c1"},
        ]}]
    }
    _, auto_remap = check_project_media(
        timeline, search_roots=[str(search_dir)],
        auto_relink_threshold=0.9,  # very high threshold
    )
    assert len(auto_remap) == 0
