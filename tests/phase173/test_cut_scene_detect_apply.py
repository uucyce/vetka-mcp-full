"""
MARKER_173.3 — Scene detection → timeline auto-apply tests.

Tests:
- POST /scene-detect-and-apply endpoint
- Boundary detection integration (mocked FFmpeg)
- Clip creation on target lane
- Scene graph node generation
- Edge cases: missing files, empty timelines, no boundaries
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.services.cut_scene_detector import SceneBoundary


def _make_timeline_state(
    clips: list[dict] | None = None,
    lanes: list[dict] | None = None,
) -> dict[str, Any]:
    """Build a minimal timeline state."""
    default_clips = [
        {"clip_id": "c1", "source_path": "/media/a.mp4", "start_sec": 0.0, "duration_sec": 10.0},
        {"clip_id": "c2", "source_path": "/media/b.mp4", "start_sec": 10.0, "duration_sec": 8.0},
    ]
    if lanes is not None:
        return {
            "schema_version": "cut_timeline_state_v1",
            "project_id": "proj_1",
            "timeline_id": "tl_1",
            "revision": 0,
            "lanes": lanes,
        }
    return {
        "schema_version": "cut_timeline_state_v1",
        "project_id": "proj_1",
        "timeline_id": "tl_1",
        "revision": 0,
        "lanes": [
            {"lane_id": "main", "type": "video_main", "clips": clips or default_clips},
        ],
    }


def _make_project() -> dict[str, Any]:
    return {"project_id": "proj_1"}


# ── Unit: detect_scene_boundaries mock ───────────────────


class TestSceneDetectEndpointBasic:
    """Test the endpoint via FastAPI TestClient with mocked scene detector."""

    @pytest.fixture(autouse=True)
    def _setup(self, tmp_path):
        self.sandbox = str(tmp_path)

        # Create mock media files so os.path.isfile passes
        media_dir = tmp_path / "media"
        media_dir.mkdir()
        (media_dir / "a.mp4").write_bytes(b"fake")
        (media_dir / "b.mp4").write_bytes(b"fake")

        self.media_a = str(media_dir / "a.mp4")
        self.media_b = str(media_dir / "b.mp4")

    def _get_client(self):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from src.api.routes.cut_routes import router

        app = FastAPI()
        app.include_router(router)
        return TestClient(app)

    @patch("src.api.routes.cut_routes.CutProjectStore")
    @patch("src.api.routes.cut_routes.detect_scene_boundaries")
    def test_basic_scene_detect(self, mock_detect, MockStore):
        """Detect boundaries → create clips on scene lane."""
        # Setup mocks
        instance = MagicMock()
        instance.load_project.return_value = _make_project()
        instance.load_timeline_state.return_value = _make_timeline_state(
            clips=[
                {"clip_id": "c1", "source_path": self.media_a, "start_sec": 0.0, "duration_sec": 10.0},
            ]
        )
        instance.load_scene_graph.return_value = None
        instance.save_timeline_state = MagicMock()
        instance.save_scene_graph = MagicMock()
        MockStore.return_value = instance

        # Scene detector returns 2 boundaries
        mock_detect.return_value = [
            SceneBoundary(time_sec=3.0, diff_score=0.45),
            SceneBoundary(time_sec=7.0, diff_score=0.52),
        ]

        client = self._get_client()
        resp = client.post("/api/cut/scene-detect-and-apply", json={
            "sandbox_root": self.sandbox,
            "project_id": "proj_1",
            "source_paths": [self.media_a],
            "threshold": 0.3,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["boundary_count"] == 2
        # 2 boundaries → 3 scene clips: [0,3), [3,7), [7,10)
        assert data["clip_count"] == 3
        assert data["lane_id"] == "scenes"

        # Verify clips
        clips = data["created_clips"]
        assert clips[0]["start_sec"] == 0.0
        assert clips[0]["duration_sec"] == 3.0
        assert clips[1]["start_sec"] == 3.0
        assert clips[1]["duration_sec"] == 4.0
        assert clips[2]["start_sec"] == 7.0
        assert clips[2]["duration_sec"] == 3.0

        # Verify scene graph was saved
        instance.save_scene_graph.assert_called_once()
        assert len(data["scene_graph_updates"]) == 3  # 3 scene nodes added

    @patch("src.api.routes.cut_routes.CutProjectStore")
    @patch("src.api.routes.cut_routes.detect_scene_boundaries")
    def test_no_boundaries_single_scene(self, mock_detect, MockStore):
        """No boundaries detected → single clip spanning entire duration."""
        instance = MagicMock()
        instance.load_project.return_value = _make_project()
        instance.load_timeline_state.return_value = _make_timeline_state(
            clips=[
                {"clip_id": "c1", "source_path": self.media_a, "start_sec": 0.0, "duration_sec": 5.0},
            ]
        )
        instance.load_scene_graph.return_value = None
        instance.save_timeline_state = MagicMock()
        instance.save_scene_graph = MagicMock()
        MockStore.return_value = instance

        mock_detect.return_value = []

        client = self._get_client()
        resp = client.post("/api/cut/scene-detect-and-apply", json={
            "sandbox_root": self.sandbox,
            "project_id": "proj_1",
            "source_paths": [self.media_a],
        })
        data = resp.json()
        assert data["success"] is True
        assert data["boundary_count"] == 0
        assert data["clip_count"] == 1  # single clip for entire duration
        assert data["created_clips"][0]["start_sec"] == 0.0
        assert data["created_clips"][0]["duration_sec"] == 5.0

    @patch("src.api.routes.cut_routes.CutProjectStore")
    def test_project_not_found(self, MockStore):
        instance = MagicMock()
        instance.load_project.return_value = None
        MockStore.return_value = instance

        client = self._get_client()
        resp = client.post("/api/cut/scene-detect-and-apply", json={
            "sandbox_root": self.sandbox,
            "project_id": "proj_1",
        })
        data = resp.json()
        assert data["success"] is False
        assert data["error"] == "project_not_found"

    @patch("src.api.routes.cut_routes.CutProjectStore")
    def test_timeline_not_ready(self, MockStore):
        instance = MagicMock()
        instance.load_project.return_value = _make_project()
        instance.load_timeline_state.return_value = None
        MockStore.return_value = instance

        client = self._get_client()
        resp = client.post("/api/cut/scene-detect-and-apply", json={
            "sandbox_root": self.sandbox,
            "project_id": "proj_1",
        })
        data = resp.json()
        assert data["success"] is False
        assert data["error"] == "timeline_not_ready"

    @patch("src.api.routes.cut_routes.CutProjectStore")
    def test_no_source_media(self, MockStore):
        """Empty timeline with no clips → no source media error."""
        instance = MagicMock()
        instance.load_project.return_value = _make_project()
        instance.load_timeline_state.return_value = _make_timeline_state(
            lanes=[{"lane_id": "main", "type": "video_main", "clips": []}]
        )
        MockStore.return_value = instance

        client = self._get_client()
        resp = client.post("/api/cut/scene-detect-and-apply", json={
            "sandbox_root": self.sandbox,
            "project_id": "proj_1",
        })
        data = resp.json()
        assert data["success"] is False
        assert data["error"] == "no_source_media"

    @patch("src.api.routes.cut_routes.CutProjectStore")
    @patch("src.api.routes.cut_routes.detect_scene_boundaries")
    def test_auto_discover_sources(self, mock_detect, MockStore):
        """When no source_paths given, discovers from timeline clips."""
        instance = MagicMock()
        instance.load_project.return_value = _make_project()
        instance.load_timeline_state.return_value = _make_timeline_state(
            clips=[
                {"clip_id": "c1", "source_path": self.media_a, "start_sec": 0.0, "duration_sec": 10.0},
                {"clip_id": "c2", "source_path": self.media_b, "start_sec": 10.0, "duration_sec": 8.0},
            ]
        )
        instance.load_scene_graph.return_value = None
        instance.save_timeline_state = MagicMock()
        instance.save_scene_graph = MagicMock()
        MockStore.return_value = instance

        mock_detect.return_value = []  # no boundaries for either file

        client = self._get_client()
        resp = client.post("/api/cut/scene-detect-and-apply", json={
            "sandbox_root": self.sandbox,
            "project_id": "proj_1",
            # No source_paths — should discover from timeline
        })
        data = resp.json()
        assert data["success"] is True
        # Called detect for each discovered file
        assert mock_detect.call_count == 2
        assert len(data["source_paths_analysed"]) == 2

    @patch("src.api.routes.cut_routes.CutProjectStore")
    @patch("src.api.routes.cut_routes.detect_scene_boundaries")
    def test_custom_lane_id(self, mock_detect, MockStore):
        """Custom lane_id for scene clips."""
        instance = MagicMock()
        instance.load_project.return_value = _make_project()
        instance.load_timeline_state.return_value = _make_timeline_state(
            clips=[{"clip_id": "c1", "source_path": self.media_a, "start_sec": 0.0, "duration_sec": 5.0}]
        )
        instance.load_scene_graph.return_value = None
        instance.save_timeline_state = MagicMock()
        instance.save_scene_graph = MagicMock()
        MockStore.return_value = instance

        mock_detect.return_value = [SceneBoundary(time_sec=2.5, diff_score=0.4)]

        client = self._get_client()
        resp = client.post("/api/cut/scene-detect-and-apply", json={
            "sandbox_root": self.sandbox,
            "project_id": "proj_1",
            "source_paths": [self.media_a],
            "lane_id": "auto_scenes",
        })
        data = resp.json()
        assert data["success"] is True
        assert data["lane_id"] == "auto_scenes"

    @patch("src.api.routes.cut_routes.CutProjectStore")
    @patch("src.api.routes.cut_routes.detect_scene_boundaries")
    def test_skip_scene_graph_update(self, mock_detect, MockStore):
        """update_scene_graph=False skips graph modification."""
        instance = MagicMock()
        instance.load_project.return_value = _make_project()
        instance.load_timeline_state.return_value = _make_timeline_state(
            clips=[{"clip_id": "c1", "source_path": self.media_a, "start_sec": 0.0, "duration_sec": 5.0}]
        )
        instance.save_timeline_state = MagicMock()
        instance.save_scene_graph = MagicMock()
        MockStore.return_value = instance

        mock_detect.return_value = [SceneBoundary(time_sec=2.0, diff_score=0.5)]

        client = self._get_client()
        resp = client.post("/api/cut/scene-detect-and-apply", json={
            "sandbox_root": self.sandbox,
            "project_id": "proj_1",
            "source_paths": [self.media_a],
            "update_scene_graph": False,
        })
        data = resp.json()
        assert data["success"] is True
        instance.save_scene_graph.assert_not_called()
        assert data["scene_graph_updates"] == []

    @patch("src.api.routes.cut_routes.CutProjectStore")
    @patch("src.api.routes.cut_routes.detect_scene_boundaries")
    def test_revision_increments(self, mock_detect, MockStore):
        """Timeline revision should bump after detect-and-apply."""
        state = _make_timeline_state(
            clips=[{"clip_id": "c1", "source_path": self.media_a, "start_sec": 0.0, "duration_sec": 5.0}]
        )
        state["revision"] = 7

        instance = MagicMock()
        instance.load_project.return_value = _make_project()
        instance.load_timeline_state.return_value = state
        instance.load_scene_graph.return_value = None
        instance.save_timeline_state = MagicMock()
        instance.save_scene_graph = MagicMock()
        MockStore.return_value = instance

        mock_detect.return_value = []

        client = self._get_client()
        resp = client.post("/api/cut/scene-detect-and-apply", json={
            "sandbox_root": self.sandbox,
            "project_id": "proj_1",
            "source_paths": [self.media_a],
        })
        assert resp.json()["success"] is True

        # Check that save_timeline_state was called with bumped revision
        saved_state = instance.save_timeline_state.call_args[0][0]
        assert saved_state["revision"] == 8

    @patch("src.api.routes.cut_routes.CutProjectStore")
    @patch("src.api.routes.cut_routes.detect_scene_boundaries")
    def test_missing_file_skipped(self, mock_detect, MockStore):
        """Missing media files are skipped gracefully."""
        instance = MagicMock()
        instance.load_project.return_value = _make_project()
        instance.load_timeline_state.return_value = _make_timeline_state()
        instance.load_scene_graph.return_value = None
        instance.save_timeline_state = MagicMock()
        instance.save_scene_graph = MagicMock()
        MockStore.return_value = instance

        mock_detect.return_value = []

        client = self._get_client()
        resp = client.post("/api/cut/scene-detect-and-apply", json={
            "sandbox_root": self.sandbox,
            "project_id": "proj_1",
            "source_paths": ["/nonexistent/video.mp4", self.media_a],
        })
        data = resp.json()
        assert data["success"] is True
        # Only the existing file should be analysed
        assert len(data["source_paths_analysed"]) == 1
        assert data["source_paths_analysed"][0] == self.media_a


class TestSceneDetectEdgeCases:
    """Edge cases for scene detection."""

    @pytest.fixture(autouse=True)
    def _setup(self, tmp_path):
        self.sandbox = str(tmp_path)
        media_dir = tmp_path / "media"
        media_dir.mkdir()
        (media_dir / "a.mp4").write_bytes(b"fake")
        self.media_a = str(media_dir / "a.mp4")

    def _get_client(self):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from src.api.routes.cut_routes import router

        app = FastAPI()
        app.include_router(router)
        return TestClient(app)

    @patch("src.api.routes.cut_routes.CutProjectStore")
    @patch("src.api.routes.cut_routes.detect_scene_boundaries")
    def test_multiple_boundaries_many_clips(self, mock_detect, MockStore):
        """5 boundaries → 6 scene clips."""
        instance = MagicMock()
        instance.load_project.return_value = _make_project()
        instance.load_timeline_state.return_value = _make_timeline_state(
            clips=[{"clip_id": "c1", "source_path": self.media_a, "start_sec": 0.0, "duration_sec": 60.0}]
        )
        instance.load_scene_graph.return_value = None
        instance.save_timeline_state = MagicMock()
        instance.save_scene_graph = MagicMock()
        MockStore.return_value = instance

        mock_detect.return_value = [
            SceneBoundary(time_sec=10.0, diff_score=0.4),
            SceneBoundary(time_sec=20.0, diff_score=0.5),
            SceneBoundary(time_sec=30.0, diff_score=0.35),
            SceneBoundary(time_sec=40.0, diff_score=0.6),
            SceneBoundary(time_sec=50.0, diff_score=0.45),
        ]

        client = self._get_client()
        resp = client.post("/api/cut/scene-detect-and-apply", json={
            "sandbox_root": self.sandbox,
            "project_id": "proj_1",
            "source_paths": [self.media_a],
        })
        data = resp.json()
        assert data["success"] is True
        assert data["boundary_count"] == 5
        assert data["clip_count"] == 6  # 5 boundaries → 6 segments

    @patch("src.api.routes.cut_routes.CutProjectStore")
    @patch("src.api.routes.cut_routes.detect_scene_boundaries")
    def test_existing_scene_graph_preserved(self, mock_detect, MockStore):
        """Existing scene graph nodes are not duplicated."""
        existing_graph = {
            "schema_version": "cut_scene_graph_v1",
            "project_id": "proj_1",
            "graph_id": "main",
            "nodes": [{"node_id": "scene_01", "node_type": "scene", "label": "Existing"}],
            "edges": [],
        }
        instance = MagicMock()
        instance.load_project.return_value = _make_project()
        instance.load_timeline_state.return_value = _make_timeline_state(
            clips=[{"clip_id": "c1", "source_path": self.media_a, "start_sec": 0.0, "duration_sec": 10.0}]
        )
        instance.load_scene_graph.return_value = existing_graph
        instance.save_timeline_state = MagicMock()
        instance.save_scene_graph = MagicMock()
        MockStore.return_value = instance

        mock_detect.return_value = [SceneBoundary(time_sec=5.0, diff_score=0.4)]

        client = self._get_client()
        resp = client.post("/api/cut/scene-detect-and-apply", json={
            "sandbox_root": self.sandbox,
            "project_id": "proj_1",
            "source_paths": [self.media_a],
        })
        data = resp.json()
        assert data["success"] is True
        # scene_01 already exists, so it should not be added again
        # scene_02 is new
        saved_graph = instance.save_scene_graph.call_args[0][0]
        node_ids = [n["node_id"] for n in saved_graph["nodes"]]
        assert node_ids.count("scene_01") == 1  # not duplicated
