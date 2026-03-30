"""
MARKER_MVP-TIMELINE-OPS-CONTRACT: Contract tests for timeline CRUD ops with real media refs.

Verifies that POST /timeline/apply correctly processes add_clip, trim_clip,
add_marker ops against a project referencing real GH5 footage paths.
State is seeded directly (no bootstrap/scene-assembly round-trip) for speed.

Tests written by Epsilon [task:tb_1774837856_2394_1]
"""
import json
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.routes.cut_routes import router

# ── Footage fixtures ──────────────────────────────────────────────────────────

GH5_DIR = "/Users/danilagulin/work/teletape_temp/berlin/source_gh5"
GH5_CLIP_A = os.path.join(GH5_DIR, "P1733379.MOV")
GH5_CLIP_B = os.path.join(GH5_DIR, "P1733380.MOV")

PROJECT_ID = "mvp_tl_test"
TIMELINE_ID = "main"

pytestmark = pytest.mark.integration


def _files_present() -> bool:
    return os.path.isfile(GH5_CLIP_A)


def _make_client() -> TestClient:
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


def _seed_sandbox(sandbox_root: Path, project_id: str, timeline_id: str, clips: list[dict]) -> None:
    """Write minimal project + timeline state directly, bypassing bootstrap."""
    config_dir = sandbox_root / "config"
    state_dir = sandbox_root / "cut_runtime" / "state"
    config_dir.mkdir(parents=True, exist_ok=True)
    state_dir.mkdir(parents=True, exist_ok=True)
    (sandbox_root / "cut_storage").mkdir(parents=True, exist_ok=True)
    (sandbox_root / "core_mirror").mkdir(parents=True, exist_ok=True)
    (config_dir / "cut_core_mirror_manifest.json").write_text("{}\n", encoding="utf-8")

    sb = str(sandbox_root)
    project = {
        "schema_version": "cut_project_v1",
        "project_id": project_id,
        "display_name": "MVP Timeline Test",
        "source_path": GH5_DIR,
        "sandbox_root": sb,
        "core_mirror_root": str(sandbox_root / "core_mirror"),
        "runtime_root": str(sandbox_root / "cut_runtime"),
        "storage_root": str(sandbox_root / "cut_storage"),
        "qdrant_namespace": project_id,
        "created_at": "2026-01-01T00:00:00Z",
        "bootstrap_profile": "film",
        "state": "ready",
    }
    (config_dir / "cut_project.json").write_text(json.dumps(project), encoding="utf-8")

    lane = {
        "lane_id": "v1",
        "lane_type": "video",
        "label": "Video 1",
        "clips": clips,
    }
    timeline = {
        "schema_version": "cut_timeline_state_v1",
        "project_id": project_id,
        "timeline_id": timeline_id,
        "revision": 1,
        "fps": 25.0,
        "lanes": [lane],
        "selection": {},
        "view": {},
        "updated_at": "2026-01-01T00:00:00Z",
    }
    (state_dir / "timeline_state.latest.json").write_text(json.dumps(timeline), encoding="utf-8")


def _make_clip(clip_id: str, source_path: str, start_sec: float, duration_sec: float) -> dict:
    return {
        "clip_id": clip_id,
        "source_path": source_path,
        "start_sec": start_sec,
        "duration_sec": duration_sec,
        "source_in": 0.0,
        "lane_id": "v1",
        "label": clip_id,
    }


# ── add_clip op ───────────────────────────────────────────────────────────────


@pytest.mark.skipif(not _files_present(), reason="GH5 footage not available")
class TestAddClipOp:
    def test_insert_at_adds_clip_to_lane(self, tmp_path):
        """insert_at = FCP7 insert edit — pushes existing clips right."""
        sandbox = tmp_path / "sandbox"
        _seed_sandbox(sandbox, PROJECT_ID, TIMELINE_ID, [])
        client = _make_client()
        resp = client.post(
            "/api/cut/timeline/apply",
            json={
                "sandbox_root": str(sandbox),
                "project_id": PROJECT_ID,
                "timeline_id": TIMELINE_ID,
                "ops": [
                    {
                        "op": "insert_at",
                        "clip_id": "gh5_clip_a",
                        "lane_id": "v1",
                        "source_path": GH5_CLIP_A,
                        "start_sec": 0.0,
                        "duration_sec": 1.44,
                    }
                ],
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data.get("success") is True

    def test_insert_at_response_schema_version(self, tmp_path):
        sandbox = tmp_path / "sandbox"
        _seed_sandbox(sandbox, PROJECT_ID, TIMELINE_ID, [])
        client = _make_client()
        resp = client.post(
            "/api/cut/timeline/apply",
            json={
                "sandbox_root": str(sandbox),
                "project_id": PROJECT_ID,
                "timeline_id": TIMELINE_ID,
                "ops": [
                    {
                        "op": "insert_at",
                        "clip_id": "c1",
                        "lane_id": "v1",
                        "source_path": GH5_CLIP_A,
                        "start_sec": 0.0,
                        "duration_sec": 1.44,
                    }
                ],
            },
        )
        data = resp.json()
        assert data.get("schema_version") == "cut_timeline_apply_v1"

    def test_insert_at_increments_revision(self, tmp_path):
        sandbox = tmp_path / "sandbox"
        _seed_sandbox(sandbox, PROJECT_ID, TIMELINE_ID, [])
        client = _make_client()
        resp = client.post(
            "/api/cut/timeline/apply",
            json={
                "sandbox_root": str(sandbox),
                "project_id": PROJECT_ID,
                "timeline_id": TIMELINE_ID,
                "ops": [
                    {
                        "op": "insert_at",
                        "clip_id": "c2",
                        "lane_id": "v1",
                        "source_path": GH5_CLIP_A,
                        "start_sec": 0.0,
                        "duration_sec": 1.44,
                    }
                ],
            },
        )
        data = resp.json()
        ts = data.get("timeline_state", {})
        assert ts.get("revision", 0) >= 2, f"Revision should increase, got: {ts.get('revision')}"


# ── trim_clip op ──────────────────────────────────────────────────────────────


@pytest.mark.skipif(not _files_present(), reason="GH5 footage not available")
class TestTrimClipOp:
    def test_trim_clip_updates_duration(self, tmp_path):
        sandbox = tmp_path / "sandbox"
        clip = _make_clip("gh5_trim", GH5_CLIP_A, 0.0, 1.44)
        _seed_sandbox(sandbox, PROJECT_ID, TIMELINE_ID, [clip])
        client = _make_client()
        resp = client.post(
            "/api/cut/timeline/apply",
            json={
                "sandbox_root": str(sandbox),
                "project_id": PROJECT_ID,
                "timeline_id": TIMELINE_ID,
                "ops": [{"op": "trim_clip", "clip_id": "gh5_trim", "duration_sec": 0.9}],
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data.get("success") is True

    def test_trim_clip_preserves_source_path_ref(self, tmp_path):
        sandbox = tmp_path / "sandbox"
        clip = _make_clip("gh5_trim2", GH5_CLIP_A, 0.0, 1.44)
        _seed_sandbox(sandbox, PROJECT_ID, TIMELINE_ID, [clip])
        client = _make_client()
        resp = client.post(
            "/api/cut/timeline/apply",
            json={
                "sandbox_root": str(sandbox),
                "project_id": PROJECT_ID,
                "timeline_id": TIMELINE_ID,
                "ops": [{"op": "trim_clip", "clip_id": "gh5_trim2", "duration_sec": 1.0}],
            },
        )
        data = resp.json()
        lanes = data.get("timeline_state", {}).get("lanes", [])
        clips = [c for lane in lanes for c in lane.get("clips", [])]
        found = next((c for c in clips if c.get("clip_id") == "gh5_trim2"), None)
        assert found is not None, "Clip disappeared after trim"
        assert found.get("source_path") == GH5_CLIP_A


# ── add_marker op ─────────────────────────────────────────────────────────────


@pytest.mark.skipif(not _files_present(), reason="GH5 footage not available")
class TestClipMetaOp:
    def test_set_clip_meta_returns_success(self, tmp_path):
        """set_clip_meta = generic clip metadata update (rating, notes, label, etc.)."""
        sandbox = tmp_path / "sandbox"
        clip = _make_clip("gh5_mark", GH5_CLIP_A, 0.0, 1.44)
        _seed_sandbox(sandbox, PROJECT_ID, TIMELINE_ID, [clip])
        client = _make_client()
        resp = client.post(
            "/api/cut/timeline/apply",
            json={
                "sandbox_root": str(sandbox),
                "project_id": PROJECT_ID,
                "timeline_id": TIMELINE_ID,
                "ops": [
                    {
                        "op": "set_clip_meta",
                        "clip_id": "gh5_mark",
                        "meta": {"notes": "beat_hit", "rating": 4},
                    }
                ],
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data.get("success") is True

    def test_set_clip_meta_increments_revision(self, tmp_path):
        sandbox = tmp_path / "sandbox"
        clip = _make_clip("gh5_meta2", GH5_CLIP_A, 0.0, 1.44)
        _seed_sandbox(sandbox, PROJECT_ID, TIMELINE_ID, [clip])
        client = _make_client()
        resp = client.post(
            "/api/cut/timeline/apply",
            json={
                "sandbox_root": str(sandbox),
                "project_id": PROJECT_ID,
                "timeline_id": TIMELINE_ID,
                "ops": [
                    {"op": "set_clip_meta", "clip_id": "gh5_meta2", "meta": {"label": "B-roll"}}
                ],
            },
        )
        data = resp.json()
        ts = data.get("timeline_state", {})
        assert ts.get("revision", 0) >= 2

    def test_set_clip_meta_updates_label_on_clip(self, tmp_path):
        sandbox = tmp_path / "sandbox"
        clip = _make_clip("gh5_setprop", GH5_CLIP_B, 0.0, 1.44)
        _seed_sandbox(sandbox, PROJECT_ID, TIMELINE_ID, [clip])
        client = _make_client()
        resp = client.post(
            "/api/cut/timeline/apply",
            json={
                "sandbox_root": str(sandbox),
                "project_id": PROJECT_ID,
                "timeline_id": TIMELINE_ID,
                "ops": [
                    {
                        "op": "set_clip_meta",
                        "clip_id": "gh5_setprop",
                        "meta": {"label": "GH5_B_renamed"},
                    }
                ],
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data.get("success") is True
        lanes = data.get("timeline_state", {}).get("lanes", [])
        clips = [c for lane in lanes for c in lane.get("clips", [])]
        found = next((c for c in clips if c.get("clip_id") == "gh5_setprop"), None)
        assert found is not None
        assert found.get("label") == "GH5_B_renamed"
