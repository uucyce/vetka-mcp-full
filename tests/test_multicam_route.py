"""
MARKER_B48 — Unit tests for POST /api/cut/multicam/create route (cut_routes_media.py).

Tests cover:
  - waveform sync (mocked)
  - timecode sync (mocked)
  - marker sync
  - validation: < 2 source_paths
  - validation: missing files
  - validation: marker_times length mismatch
  - unknown sync_method
  - response schema: success, multicam_id, angles, total_duration_sec
"""
from __future__ import annotations

import os
import tempfile
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.services.cut_multicam_sync import MulticamAngle, MulticamClip

URL = "/api/cut/multicam/create"


# ---------------------------------------------------------------------------
# Client fixture
# ---------------------------------------------------------------------------

def _get_client() -> TestClient:
    from src.api.routes.cut_routes import router
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_clip(n_angles: int = 2) -> MulticamClip:
    angles = [
        MulticamAngle(
            angle_index=i,
            source_path=f"/fake/angle_{i}.mp4",
            label=f"angle_{i}",
            offset_sec=float(i),
            duration_sec=10.0,
            sync_confidence=0.9,
            is_reference=(i == 0),
        )
        for i in range(n_angles)
    ]
    return MulticamClip(
        multicam_id="test-uuid-1234",
        angles=angles,
        sync_method="waveform",
        reference_index=0,
        total_duration_sec=11.0,
    )


def _real_files(n: int = 2) -> list[str]:
    files = []
    for _ in range(n):
        f = tempfile.NamedTemporaryFile(suffix=".mp4", delete=False)
        f.close()
        files.append(f.name)
    return files


# ---------------------------------------------------------------------------
# Validation tests
# ---------------------------------------------------------------------------

class TestValidation:
    def test_single_source_path_rejected(self):
        """< 2 sources → success=False, error=need_at_least_2_sources"""
        files = _real_files(1)
        try:
            resp = _get_client().post(URL, json={"source_paths": files})
            assert resp.status_code == 200
            data = resp.json()
            assert data["success"] is False
            assert data["error"] == "need_at_least_2_sources"
        finally:
            for f in files:
                os.unlink(f)

    def test_empty_source_paths_rejected(self):
        resp = _get_client().post(URL, json={"source_paths": []})
        assert resp.status_code == 200
        assert resp.json()["success"] is False

    def test_missing_files_rejected(self):
        resp = _get_client().post(URL, json={
            "source_paths": ["/does/not/exist_a.mp4", "/does/not/exist_b.mp4"],
        })
        data = resp.json()
        assert data["success"] is False
        assert "files_not_found" in data.get("error", "")

    def test_marker_length_mismatch_rejected(self):
        files = _real_files(2)
        try:
            resp = _get_client().post(URL, json={
                "source_paths": files,
                "sync_method": "marker",
                "marker_times": [0.0],  # wrong length
            })
            data = resp.json()
            assert data["success"] is False
            assert "marker_times" in data.get("error", "")
        finally:
            for f in files:
                os.unlink(f)

    def test_unknown_sync_method_rejected(self):
        files = _real_files(2)
        try:
            resp = _get_client().post(URL, json={
                "source_paths": files,
                "sync_method": "telepathy",
            })
            data = resp.json()
            assert data["success"] is False
            assert "unknown_sync_method" in data.get("error", "")
        finally:
            for f in files:
                os.unlink(f)


# ---------------------------------------------------------------------------
# Waveform sync
# ---------------------------------------------------------------------------

class TestWaveformSync:
    def test_waveform_returns_success(self):
        files = _real_files(2)
        clip = _make_clip(2)
        try:
            with patch("src.services.cut_multicam_sync.sync_by_waveform", return_value=clip):
                resp = _get_client().post(URL, json={
                    "source_paths": files,
                    "sync_method": "waveform",
                })
            assert resp.status_code == 200
            assert resp.json()["success"] is True
        finally:
            for f in files:
                os.unlink(f)

    def test_waveform_response_has_multicam_id(self):
        files = _real_files(2)
        clip = _make_clip(2)
        try:
            with patch("src.services.cut_multicam_sync.sync_by_waveform", return_value=clip):
                resp = _get_client().post(URL, json={"source_paths": files})
            assert resp.json()["multicam_id"] == "test-uuid-1234"
        finally:
            for f in files:
                os.unlink(f)

    def test_waveform_response_has_angles(self):
        files = _real_files(2)
        clip = _make_clip(2)
        try:
            with patch("src.services.cut_multicam_sync.sync_by_waveform", return_value=clip):
                resp = _get_client().post(URL, json={"source_paths": files})
            assert len(resp.json()["angles"]) == 2
        finally:
            for f in files:
                os.unlink(f)

    def test_waveform_angle_has_offset_sec(self):
        files = _real_files(2)
        clip = _make_clip(2)
        try:
            with patch("src.services.cut_multicam_sync.sync_by_waveform", return_value=clip):
                resp = _get_client().post(URL, json={"source_paths": files})
            for a in resp.json()["angles"]:
                assert "offset_sec" in a
        finally:
            for f in files:
                os.unlink(f)

    def test_waveform_response_has_total_duration_sec(self):
        files = _real_files(2)
        clip = _make_clip(2)
        try:
            with patch("src.services.cut_multicam_sync.sync_by_waveform", return_value=clip):
                resp = _get_client().post(URL, json={"source_paths": files})
            assert "total_duration_sec" in resp.json()
        finally:
            for f in files:
                os.unlink(f)

    def test_waveform_reference_index_passed(self):
        files = _real_files(3)
        clip = _make_clip(3)
        try:
            with patch("src.services.cut_multicam_sync.sync_by_waveform", return_value=clip) as mock_fn:
                _get_client().post(URL, json={
                    "source_paths": files,
                    "sync_method": "waveform",
                    "reference_index": 2,
                })
                args, kwargs = mock_fn.call_args
                assert kwargs.get("reference_index") == 2
        finally:
            for f in files:
                os.unlink(f)

    def test_waveform_max_lag_passed(self):
        files = _real_files(2)
        clip = _make_clip(2)
        try:
            with patch("src.services.cut_multicam_sync.sync_by_waveform", return_value=clip) as mock_fn:
                _get_client().post(URL, json={
                    "source_paths": files,
                    "sync_method": "waveform",
                    "max_lag_sec": 60.0,
                })
                args, kwargs = mock_fn.call_args
                assert kwargs.get("max_lag_sec") == 60.0
        finally:
            for f in files:
                os.unlink(f)


# ---------------------------------------------------------------------------
# Timecode sync
# ---------------------------------------------------------------------------

class TestTimecodeSync:
    def test_timecode_returns_success(self):
        files = _real_files(2)
        clip = _make_clip(2)
        clip.sync_method = "timecode"
        try:
            with patch("src.services.cut_multicam_sync.sync_by_timecode", return_value=clip):
                resp = _get_client().post(URL, json={
                    "source_paths": files,
                    "sync_method": "timecode",
                    "fps": 25.0,
                })
            assert resp.status_code == 200
            assert resp.json()["success"] is True
        finally:
            for f in files:
                os.unlink(f)

    def test_timecode_fps_passed(self):
        files = _real_files(2)
        clip = _make_clip(2)
        try:
            with patch("src.services.cut_multicam_sync.sync_by_timecode", return_value=clip) as mock_fn:
                _get_client().post(URL, json={
                    "source_paths": files,
                    "sync_method": "timecode",
                    "fps": 29.97,
                })
                args, kwargs = mock_fn.call_args
                assert kwargs.get("fps") == 29.97
        finally:
            for f in files:
                os.unlink(f)

    def test_timecode_returns_angles(self):
        files = _real_files(2)
        clip = _make_clip(2)
        try:
            with patch("src.services.cut_multicam_sync.sync_by_timecode", return_value=clip):
                resp = _get_client().post(URL, json={
                    "source_paths": files,
                    "sync_method": "timecode",
                })
            assert len(resp.json()["angles"]) == 2
        finally:
            for f in files:
                os.unlink(f)


# ---------------------------------------------------------------------------
# Marker sync
# ---------------------------------------------------------------------------

class TestMarkerSync:
    def test_marker_sync_returns_success(self):
        files = _real_files(2)
        clip = _make_clip(2)
        clip.sync_method = "marker"
        try:
            with patch("src.services.cut_multicam_sync.sync_by_markers", return_value=clip):
                resp = _get_client().post(URL, json={
                    "source_paths": files,
                    "sync_method": "marker",
                    "marker_times": [0.0, 3.5],
                })
            assert resp.status_code == 200
            assert resp.json()["success"] is True
        finally:
            for f in files:
                os.unlink(f)

    def test_marker_times_passed_to_sync(self):
        files = _real_files(2)
        clip = _make_clip(2)
        try:
            with patch("src.services.cut_multicam_sync.sync_by_markers", return_value=clip) as mock_fn:
                _get_client().post(URL, json={
                    "source_paths": files,
                    "sync_method": "marker",
                    "marker_times": [1.0, 4.5],
                })
                args, _ = mock_fn.call_args
                assert args[1] == [1.0, 4.5]
        finally:
            for f in files:
                os.unlink(f)

    def test_marker_sync_angle_has_label(self):
        files = _real_files(2)
        clip = _make_clip(2)
        try:
            with patch("src.services.cut_multicam_sync.sync_by_markers", return_value=clip):
                resp = _get_client().post(URL, json={
                    "source_paths": files,
                    "sync_method": "marker",
                    "marker_times": [0.0, 2.0],
                })
            for a in resp.json()["angles"]:
                assert "label" in a
        finally:
            for f in files:
                os.unlink(f)


# ---------------------------------------------------------------------------
# Response schema invariants
# ---------------------------------------------------------------------------

class TestResponseSchema:
    def test_created_at_present(self):
        files = _real_files(2)
        clip = _make_clip(2)
        try:
            with patch("src.services.cut_multicam_sync.sync_by_waveform", return_value=clip):
                resp = _get_client().post(URL, json={"source_paths": files})
            assert resp.json()["created_at"]  # non-empty
        finally:
            for f in files:
                os.unlink(f)

    def test_sync_method_in_response(self):
        files = _real_files(2)
        clip = _make_clip(2)
        try:
            with patch("src.services.cut_multicam_sync.sync_by_waveform", return_value=clip):
                resp = _get_client().post(URL, json={"source_paths": files})
            assert resp.json()["sync_method"] == "waveform"
        finally:
            for f in files:
                os.unlink(f)

    def test_reference_index_in_response(self):
        files = _real_files(2)
        clip = _make_clip(2)
        try:
            with patch("src.services.cut_multicam_sync.sync_by_waveform", return_value=clip):
                resp = _get_client().post(URL, json={"source_paths": files})
            assert "reference_index" in resp.json()
        finally:
            for f in files:
                os.unlink(f)

    def test_angle_schema_fields(self):
        files = _real_files(2)
        clip = _make_clip(2)
        try:
            with patch("src.services.cut_multicam_sync.sync_by_waveform", return_value=clip):
                resp = _get_client().post(URL, json={"source_paths": files})
            angle = resp.json()["angles"][0]
            for field_name in ("angle_index", "source_path", "label", "offset_sec",
                               "duration_sec", "sync_confidence", "is_reference"):
                assert field_name in angle, f"Missing field: {field_name}"
        finally:
            for f in files:
                os.unlink(f)

    def test_reference_angle_has_is_reference_true(self):
        files = _real_files(2)
        clip = _make_clip(2)
        try:
            with patch("src.services.cut_multicam_sync.sync_by_waveform", return_value=clip):
                resp = _get_client().post(URL, json={"source_paths": files})
            angles = resp.json()["angles"]
            ref_angles = [a for a in angles if a["is_reference"]]
            assert len(ref_angles) == 1
        finally:
            for f in files:
                os.unlink(f)

    def test_multicam_stored_in_registry(self):
        """Multicam clip should be retrievable via GET /api/cut/multicam/{id}."""
        files = _real_files(2)
        clip = _make_clip(2)
        try:
            with patch("src.services.cut_multicam_sync.sync_by_waveform", return_value=clip):
                client = _get_client()
                resp = client.post(URL, json={"source_paths": files})
            mc_id = resp.json()["multicam_id"]
            get_resp = client.get(f"/api/cut/multicam/{mc_id}")
            assert get_resp.status_code == 200
            assert get_resp.json()["success"] is True
        finally:
            for f in files:
                os.unlink(f)
