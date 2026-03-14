"""
MARKER_170.9.PLAYER_LAB_BRIDGE_TESTS
Tests for Player Lab → CUT marker import bridge and SRT export.
"""
import json
import os
import pytest
import tempfile
from pathlib import Path

from src.api.routes.cut_routes import (
    CutPlayerLabImportRequest,
    CutPlayerLabImportItem,
    _srt_timecode,
    _compute_time_marker_ranking_summary,
)
from src.services.cut_project_store import CutProjectStore


def _bootstrap_sandbox(root: Path) -> None:
    (root / "config").mkdir(parents=True, exist_ok=True)
    (root / "cut_runtime").mkdir(parents=True, exist_ok=True)
    (root / "cut_storage").mkdir(parents=True, exist_ok=True)
    (root / "core_mirror").mkdir(parents=True, exist_ok=True)
    (root / "config" / "cut_core_mirror_manifest.json").write_text("{}\n", encoding="utf-8")


@pytest.fixture
def sandbox_with_project(tmp_path: Path):
    """Create a sandbox directory with an initialized CUT project."""
    sandbox_root = tmp_path / "sandbox"
    _bootstrap_sandbox(sandbox_root)
    source_dir = tmp_path / "source"
    source_dir.mkdir()

    store = CutProjectStore(str(sandbox_root))
    project = store.create_project(
        source_path=str(source_dir),
        display_name="Test Project",
        bootstrap_profile="default",
        use_core_mirror=True,
    )
    store.save_project(project)
    project_id = project["project_id"]
    return str(sandbox_root), project_id


def test_srt_timecode_formatting():
    """SRT timecode formatting: seconds → HH:MM:SS,mmm"""
    assert _srt_timecode(0.0) == "00:00:00,000"
    assert _srt_timecode(1.5) == "00:00:01,500"
    assert _srt_timecode(65.123) == "00:01:05,123"
    assert _srt_timecode(3662.0) == "01:01:02,000"
    assert _srt_timecode(0.05) == "00:00:00,050"


def test_player_lab_import_request_validation():
    """Validate Pydantic model for player lab import."""
    req = CutPlayerLabImportRequest(
        sandbox_root="/tmp/test",
        project_id="proj1",
        events=[
            CutPlayerLabImportItem(start_sec=0.0, end_sec=3.0, text="Hello"),
            CutPlayerLabImportItem(start_sec=5.0, end_sec=8.0, text="World", kind="favorite"),
        ],
    )
    assert len(req.events) == 2
    assert req.events[0].kind == "comment"
    assert req.events[1].kind == "favorite"
    assert req.source_engine == "player_lab_srt"


def test_player_lab_import_creates_markers(sandbox_with_project):
    """Import Player Lab events and verify they become CUT markers."""
    import asyncio
    from src.api.routes.cut_routes import cut_import_player_lab_markers

    sandbox_root, project_id = sandbox_with_project
    body = CutPlayerLabImportRequest(
        sandbox_root=sandbox_root,
        project_id=project_id,
        media_path="/media/test.mp4",
        events=[
            CutPlayerLabImportItem(start_sec=0.0, end_sec=2.5, text="First comment"),
            CutPlayerLabImportItem(start_sec=5.0, end_sec=7.0, text="Second comment"),
            CutPlayerLabImportItem(start_sec=10.0, end_sec=12.0, text="Fav spot", kind="favorite"),
        ],
    )
    result = asyncio.get_event_loop().run_until_complete(cut_import_player_lab_markers(body))
    assert result["success"] is True
    assert result["imported_count"] == 3
    assert len(result["imported_markers"]) == 3

    # Verify markers have correct schema
    marker = result["imported_markers"][0]
    assert marker["schema_version"] == "cut_time_marker_v1"
    assert marker["kind"] == "comment"
    assert marker["start_sec"] == 0.0
    assert marker["end_sec"] == 2.5
    assert marker["text"] == "First comment"
    assert marker["source_engine"] == "player_lab_srt"
    assert marker["context_slice"]["migration_status"] == "migrated"
    assert marker["status"] == "active"

    # Third marker should be favorite
    fav = result["imported_markers"][2]
    assert fav["kind"] == "favorite"


def test_player_lab_import_with_cam_payload(sandbox_with_project):
    """Import with CAM payload attached to marker."""
    import asyncio
    from src.api.routes.cut_routes import cut_import_player_lab_markers

    sandbox_root, project_id = sandbox_with_project
    cam_data = {"node_id": "cam_123", "relevance": 0.9, "tags": ["interview"]}
    body = CutPlayerLabImportRequest(
        sandbox_root=sandbox_root,
        project_id=project_id,
        media_path="/test/media/video.mp4",
        events=[
            CutPlayerLabImportItem(
                start_sec=3.0, end_sec=6.0, text="CAM-linked marker",
                cam_payload=cam_data,
            ),
        ],
    )
    result = asyncio.get_event_loop().run_until_complete(cut_import_player_lab_markers(body))
    assert result["success"] is True
    marker = result["imported_markers"][0]
    assert marker["cam_payload"]["node_id"] == "cam_123"
    assert marker["cam_payload"]["relevance"] == 0.9


def test_player_lab_import_bad_project():
    """Import should fail gracefully for nonexistent project."""
    import asyncio
    from src.api.routes.cut_routes import cut_import_player_lab_markers

    body = CutPlayerLabImportRequest(
        sandbox_root="/tmp/nonexistent",
        project_id="no_such_project",
        events=[CutPlayerLabImportItem(start_sec=0.0, end_sec=1.0, text="test")],
    )
    result = asyncio.get_event_loop().run_until_complete(cut_import_player_lab_markers(body))
    assert result.get("success") is not True or result.get("error") is not None


def test_srt_export_empty(sandbox_with_project):
    """SRT export with no markers returns empty string."""
    import asyncio
    from src.api.routes.cut_routes import cut_export_markers_srt

    sandbox_root, project_id = sandbox_with_project
    result = asyncio.get_event_loop().run_until_complete(
        cut_export_markers_srt(sandbox_root=sandbox_root, project_id=project_id)
    )
    assert result["success"] is True
    assert result["srt_content"] == ""
    assert result["marker_count"] == 0


def test_srt_export_with_markers(sandbox_with_project):
    """SRT export formats markers as valid SRT content."""
    import asyncio
    from src.api.routes.cut_routes import cut_import_player_lab_markers, cut_export_markers_srt

    sandbox_root, project_id = sandbox_with_project
    # First import some markers
    body = CutPlayerLabImportRequest(
        sandbox_root=sandbox_root,
        project_id=project_id,
        media_path="/test/media/video.mp4",
        events=[
            CutPlayerLabImportItem(start_sec=0.0, end_sec=3.0, text="Hello world"),
            CutPlayerLabImportItem(start_sec=5.5, end_sec=8.0, text="Second subtitle"),
        ],
    )
    asyncio.get_event_loop().run_until_complete(cut_import_player_lab_markers(body))

    # Now export as SRT
    result = asyncio.get_event_loop().run_until_complete(
        cut_export_markers_srt(sandbox_root=sandbox_root)
    )
    assert result["success"] is True
    assert result["marker_count"] == 2

    srt = result["srt_content"]
    assert "1\n" in srt
    assert "00:00:00,000 --> 00:00:03,000" in srt
    assert "Hello world" in srt
    assert "2\n" in srt
    assert "00:00:05,500 --> 00:00:08,000" in srt
    assert "Second subtitle" in srt


def test_srt_export_filtered_by_kind(sandbox_with_project):
    """SRT export can filter by marker kind."""
    import asyncio
    from src.api.routes.cut_routes import cut_import_player_lab_markers, cut_export_markers_srt

    sandbox_root, project_id = sandbox_with_project
    body = CutPlayerLabImportRequest(
        sandbox_root=sandbox_root,
        project_id=project_id,
        media_path="/test/media/video.mp4",
        events=[
            CutPlayerLabImportItem(start_sec=0.0, end_sec=2.0, text="Comment A", kind="comment"),
            CutPlayerLabImportItem(start_sec=3.0, end_sec=5.0, text="Fav B", kind="favorite"),
            CutPlayerLabImportItem(start_sec=6.0, end_sec=8.0, text="Comment C", kind="comment"),
        ],
    )
    asyncio.get_event_loop().run_until_complete(cut_import_player_lab_markers(body))

    # Export only comments
    result = asyncio.get_event_loop().run_until_complete(
        cut_export_markers_srt(sandbox_root=sandbox_root, kind="comment")
    )
    assert result["marker_count"] == 2
    assert "Comment A" in result["srt_content"]
    assert "Fav B" not in result["srt_content"]
    assert "Comment C" in result["srt_content"]
