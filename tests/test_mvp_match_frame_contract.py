"""
MARKER_MVP-MATCH-FRAME-CONTRACT: Contract tests for FCP7 Match Frame / Reverse Match Frame.

FCP7 Ch.27: F = forward match (timeline pos → source clip + timecode),
Shift+F = reverse match (source path + timecode → timeline position).

Tests use a synthetic timeline state seeded from real GH5 clip paths.
Match-frame logic operates purely on stored timeline data — no actual decoding.

Tests written by Epsilon [task:tb_1774837856_2394_1]
"""
import importlib
import json
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Skip entire module if match-frame endpoint is not present in this branch
_routes_mod = importlib.import_module("src.api.routes.cut_routes")
if not hasattr(_routes_mod, "MatchFrameRequest"):
    pytest.skip(
        "match-frame endpoint (MatchFrameRequest) not present in this branch",
        allow_module_level=True,
    )

from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.routes.cut_routes import router  # type: ignore[attr-defined]

# ── Footage fixtures ──────────────────────────────────────────────────────────

GH5_DIR = "/Users/danilagulin/work/teletape_temp/berlin/source_gh5"
GH5_CLIP_A = os.path.join(GH5_DIR, "P1733379.MOV")  # starts at 0s, dur 1.44s
GH5_CLIP_B = os.path.join(GH5_DIR, "P1733380.MOV")  # starts at 2s, dur 1.44s

PROJECT_ID = "mvp_mf_test"
TIMELINE_ID = "main"

pytestmark = pytest.mark.integration


def _make_client() -> TestClient:
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


def _seed_sandbox(sandbox_root: Path, project_id: str) -> str:
    """Seed minimal project + timeline state with two GH5 clips placed on timeline."""
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
        "display_name": "MVP Match Frame Test",
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

    # Timeline: clip_a at 0.0–1.44s, clip_b at 2.0–3.44s
    timeline = {
        "schema_version": "cut_timeline_state_v1",
        "project_id": project_id,
        "timeline_id": TIMELINE_ID,
        "revision": 1,
        "fps": 25.0,
        "lanes": [
            {
                "lane_id": "v1",
                "lane_type": "video",
                "label": "Video 1",
                "clips": [
                    {
                        "clip_id": "clip_a",
                        "source_path": GH5_CLIP_A,
                        "start_sec": 0.0,
                        "duration_sec": 1.44,
                        "source_in": 0.0,
                        "lane_id": "v1",
                    },
                    {
                        "clip_id": "clip_b",
                        "source_path": GH5_CLIP_B,
                        "start_sec": 2.0,
                        "duration_sec": 1.44,
                        "source_in": 0.0,
                        "lane_id": "v1",
                    },
                ],
            }
        ],
        "selection": {},
        "view": {},
        "updated_at": "2026-01-01T00:00:00Z",
    }
    (state_dir / "timeline_state.latest.json").write_text(json.dumps(timeline), encoding="utf-8")
    return sb


# ── Forward match (timeline position → source) ────────────────────────────────


class TestMatchFrameForward:
    def test_forward_match_inside_clip_a(self, tmp_path):
        sandbox = tmp_path / "sandbox"
        sb = _seed_sandbox(sandbox, PROJECT_ID)
        client = _make_client()
        resp = client.post(
            "/api/cut/match-frame",
            json={
                "project_id": PROJECT_ID,
                "sandbox_root": sb,
                "timeline_position": 0.5,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data.get("success") is True
        assert data.get("match") == "forward"
        assert data.get("source_path") == GH5_CLIP_A

    def test_forward_match_returns_correct_source_timecode(self, tmp_path):
        sandbox = tmp_path / "sandbox"
        sb = _seed_sandbox(sandbox, PROJECT_ID)
        client = _make_client()
        resp = client.post(
            "/api/cut/match-frame",
            json={
                "project_id": PROJECT_ID,
                "sandbox_root": sb,
                "timeline_position": 0.5,  # 0.5s into clip_a (source_in=0)
            },
        )
        data = resp.json()
        # source_timecode = source_in + (timeline_pos - start_sec) = 0 + (0.5 - 0) = 0.5
        assert abs(data.get("source_timecode", -1) - 0.5) < 0.01

    def test_forward_match_inside_clip_b(self, tmp_path):
        sandbox = tmp_path / "sandbox"
        sb = _seed_sandbox(sandbox, PROJECT_ID)
        client = _make_client()
        resp = client.post(
            "/api/cut/match-frame",
            json={
                "project_id": PROJECT_ID,
                "sandbox_root": sb,
                "timeline_position": 2.3,
            },
        )
        data = resp.json()
        assert data.get("success") is True
        assert data.get("source_path") == GH5_CLIP_B

    def test_forward_match_gap_returns_no_clip_error(self, tmp_path):
        sandbox = tmp_path / "sandbox"
        sb = _seed_sandbox(sandbox, PROJECT_ID)
        client = _make_client()
        resp = client.post(
            "/api/cut/match-frame",
            json={
                "project_id": PROJECT_ID,
                "sandbox_root": sb,
                "timeline_position": 1.6,  # gap between clips
            },
        )
        data = resp.json()
        assert data.get("success") is False
        assert "no_clip" in (data.get("error") or "")

    def test_forward_match_beyond_timeline_returns_error(self, tmp_path):
        sandbox = tmp_path / "sandbox"
        sb = _seed_sandbox(sandbox, PROJECT_ID)
        client = _make_client()
        resp = client.post(
            "/api/cut/match-frame",
            json={
                "project_id": PROJECT_ID,
                "sandbox_root": sb,
                "timeline_position": 99.0,
            },
        )
        data = resp.json()
        assert data.get("success") is False


# ── Reverse match (source → timeline position) ────────────────────────────────


class TestMatchFrameReverse:
    def test_reverse_match_clip_a_finds_timeline_pos(self, tmp_path):
        sandbox = tmp_path / "sandbox"
        sb = _seed_sandbox(sandbox, PROJECT_ID)
        client = _make_client()
        resp = client.post(
            "/api/cut/match-frame",
            json={
                "project_id": PROJECT_ID,
                "sandbox_root": sb,
                "source_path": GH5_CLIP_A,
                "source_timecode": 0.3,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data.get("success") is True
        assert data.get("match") == "reverse"
        # timeline_pos = start_sec + (source_timecode - source_in) = 0 + 0.3 = 0.3
        assert abs(data.get("timeline_position", -1) - 0.3) < 0.01

    def test_reverse_match_clip_b_finds_timeline_pos(self, tmp_path):
        sandbox = tmp_path / "sandbox"
        sb = _seed_sandbox(sandbox, PROJECT_ID)
        client = _make_client()
        resp = client.post(
            "/api/cut/match-frame",
            json={
                "project_id": PROJECT_ID,
                "sandbox_root": sb,
                "source_path": GH5_CLIP_B,
                "source_timecode": 0.5,
            },
        )
        data = resp.json()
        assert data.get("success") is True
        # timeline_pos = 2.0 + (0.5 - 0) = 2.5
        assert abs(data.get("timeline_position", -1) - 2.5) < 0.01

    def test_reverse_match_out_of_range_returns_error(self, tmp_path):
        sandbox = tmp_path / "sandbox"
        sb = _seed_sandbox(sandbox, PROJECT_ID)
        client = _make_client()
        resp = client.post(
            "/api/cut/match-frame",
            json={
                "project_id": PROJECT_ID,
                "sandbox_root": sb,
                "source_path": GH5_CLIP_A,
                "source_timecode": 5.0,  # beyond clip duration
            },
        )
        data = resp.json()
        assert data.get("success") is False

    def test_reverse_match_returns_clip_id_and_lane_id(self, tmp_path):
        sandbox = tmp_path / "sandbox"
        sb = _seed_sandbox(sandbox, PROJECT_ID)
        client = _make_client()
        resp = client.post(
            "/api/cut/match-frame",
            json={
                "project_id": PROJECT_ID,
                "sandbox_root": sb,
                "source_path": GH5_CLIP_A,
                "source_timecode": 0.1,
            },
        )
        data = resp.json()
        assert data.get("clip_id") == "clip_a"
        assert data.get("lane_id") == "v1"

    def test_invalid_request_no_position_or_source_returns_error(self, tmp_path):
        sandbox = tmp_path / "sandbox"
        sb = _seed_sandbox(sandbox, PROJECT_ID)
        client = _make_client()
        resp = client.post(
            "/api/cut/match-frame",
            json={
                "project_id": PROJECT_ID,
                "sandbox_root": sb,
                # neither timeline_position nor source_path
            },
        )
        data = resp.json()
        assert data.get("success") is False
        assert "invalid_request" in (data.get("error") or "")
