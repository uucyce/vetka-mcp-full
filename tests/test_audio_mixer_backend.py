"""
MARKER_MIXER_STATE — Tests for Audio Mixer backend.

Covers:
  - MixerState.to_dict / from_dict with master_pan
  - MixerStateStore CRUD (get/set/update_lane/update_master)
  - apply_mixer_levels (mute/solo/volume math)
  - REST: GET/POST /audio/mixer, PATCH /audio/mixer/track/{id}, PATCH /audio/mixer/master
  - Timeline ops: set_track_volume/pan/mute/solo, set_master_volume/pan
  - WebSocket: mixer_levels_request → mixer_levels_data

@phase MIXER_STATE
@task tb_1774755549_97753_1
"""
from __future__ import annotations

import sys
import os
import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

_ROOT = os.path.dirname(os.path.dirname(__file__))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)


# ===========================================================================
# MixerState model tests
# ===========================================================================

class TestMixerStateModel:
    def test_to_dict_includes_master_pan(self):
        from src.services.cut_audio_engine import MixerState, LaneMixerState
        state = MixerState(master_volume=0.8, master_pan=0.3)
        d = state.to_dict()
        assert d["master_volume"] == 0.8
        assert d["master_pan"] == 0.3
        assert d["lanes"] == {}

    def test_to_dict_lane_uses_muted_key(self):
        from src.services.cut_audio_engine import MixerState, LaneMixerState
        state = MixerState()
        state.lanes["A1"] = LaneMixerState(lane_id="A1", volume=0.5, pan=-0.3, mute=True, solo=False)
        d = state.to_dict()
        lane = d["lanes"]["A1"]
        assert lane["muted"] is True  # API key is "muted"
        assert lane["volume"] == 0.5
        assert lane["pan"] == -0.3

    def test_from_dict_parses_muted_and_mute_keys(self):
        from src.services.cut_audio_engine import MixerState
        d = {
            "lanes": {
                "A1": {"volume": 0.7, "pan": 0.1, "muted": True, "solo": False},
                "A2": {"volume": 1.0, "pan": 0.0, "mute": True},  # legacy key
            },
            "master_volume": 1.2,
            "master_pan": -0.5,
        }
        state = MixerState.from_dict(d)
        assert state.master_volume == 1.2
        assert state.master_pan == -0.5
        assert state.lanes["A1"].mute is True
        assert state.lanes["A2"].mute is True

    def test_from_dict_defaults(self):
        from src.services.cut_audio_engine import MixerState
        state = MixerState.from_dict({})
        assert state.master_volume == 1.0
        assert state.master_pan == 0.0
        assert len(state.lanes) == 0


# ===========================================================================
# MixerStateStore CRUD
# ===========================================================================

class TestMixerStateStore:
    def setup_method(self):
        """Reset store before each test."""
        import src.services.cut_audio_engine as eng
        with eng._mixer_state_lock:
            eng._mixer_state_store.clear()

    def test_get_returns_default(self):
        from src.services.cut_audio_engine import get_mixer_state
        state = get_mixer_state("proj_x")
        assert state.master_volume == 1.0
        assert state.master_pan == 0.0
        assert state.lanes == {}

    def test_set_and_get(self):
        from src.services.cut_audio_engine import MixerState, LaneMixerState, set_mixer_state, get_mixer_state
        state = MixerState(master_volume=0.5)
        state.lanes["A1"] = LaneMixerState(lane_id="A1", volume=0.8)
        set_mixer_state("proj_1", state)
        retrieved = get_mixer_state("proj_1")
        assert retrieved.master_volume == 0.5
        assert retrieved.lanes["A1"].volume == 0.8

    def test_update_lane_creates_lane(self):
        from src.services.cut_audio_engine import update_lane_mixer, get_mixer_state
        state = update_lane_mixer("proj_2", "B1", volume=0.6, pan=0.2, muted=True)
        assert state.lanes["B1"].volume == pytest.approx(0.6)
        assert state.lanes["B1"].pan == pytest.approx(0.2)
        assert state.lanes["B1"].mute is True

    def test_update_lane_partial(self):
        from src.services.cut_audio_engine import update_lane_mixer
        update_lane_mixer("proj_3", "C1", volume=0.5, pan=0.3)
        state = update_lane_mixer("proj_3", "C1", muted=True)  # only update muted
        assert state.lanes["C1"].volume == pytest.approx(0.5)  # unchanged
        assert state.lanes["C1"].pan == pytest.approx(0.3)
        assert state.lanes["C1"].mute is True

    def test_update_lane_clamps_volume(self):
        from src.services.cut_audio_engine import update_lane_mixer
        state = update_lane_mixer("proj_4", "D1", volume=2.0)  # over max
        assert state.lanes["D1"].volume <= 1.5

    def test_update_master_volume(self):
        from src.services.cut_audio_engine import update_master_mixer
        state = update_master_mixer("proj_5", volume=0.3, pan=0.7)
        assert state.master_volume == pytest.approx(0.3)
        assert state.master_pan == pytest.approx(0.7)

    def test_update_master_partial(self):
        from src.services.cut_audio_engine import update_master_mixer
        update_master_mixer("proj_6", volume=0.5, pan=0.4)
        state = update_master_mixer("proj_6", volume=0.8)  # only volume
        assert state.master_pan == pytest.approx(0.4)  # unchanged


# ===========================================================================
# apply_mixer_levels
# ===========================================================================

class TestApplyMixerLevels:
    def test_unity_gain_passthrough(self):
        from src.services.cut_audio_engine import apply_mixer_levels
        eff_l, eff_r = apply_mixer_levels(0.5, 0.4, 1.0, 1.0, False, False, False)
        assert eff_l == pytest.approx(0.5)
        assert eff_r == pytest.approx(0.4)

    def test_muted_lane_returns_zero(self):
        from src.services.cut_audio_engine import apply_mixer_levels
        eff_l, eff_r = apply_mixer_levels(0.5, 0.5, 1.0, 1.0, muted=True, solo=False, any_solo=False)
        assert eff_l == 0.0
        assert eff_r == 0.0

    def test_solo_silences_non_soloed(self):
        from src.services.cut_audio_engine import apply_mixer_levels
        # any_solo=True, this lane not soloed → silent
        eff_l, eff_r = apply_mixer_levels(0.5, 0.5, 1.0, 1.0, muted=False, solo=False, any_solo=True)
        assert eff_l == 0.0
        assert eff_r == 0.0

    def test_solo_passes_soloed_lane(self):
        from src.services.cut_audio_engine import apply_mixer_levels
        # any_solo=True, this lane IS soloed → passes
        eff_l, eff_r = apply_mixer_levels(0.5, 0.5, 1.0, 1.0, muted=False, solo=True, any_solo=True)
        assert eff_l == pytest.approx(0.5)
        assert eff_r == pytest.approx(0.5)

    def test_volume_scales_rms(self):
        from src.services.cut_audio_engine import apply_mixer_levels
        eff_l, eff_r = apply_mixer_levels(1.0, 0.8, 0.5, 1.0, False, False, False)
        assert eff_l == pytest.approx(0.5)
        assert eff_r == pytest.approx(0.4)

    def test_master_volume_scales(self):
        from src.services.cut_audio_engine import apply_mixer_levels
        eff_l, eff_r = apply_mixer_levels(1.0, 1.0, 1.0, 0.5, False, False, False)
        assert eff_l == pytest.approx(0.5)
        assert eff_r == pytest.approx(0.5)

    def test_mute_overrides_solo(self):
        from src.services.cut_audio_engine import apply_mixer_levels
        # muted + soloed → still muted (FCP7 rule)
        eff_l, eff_r = apply_mixer_levels(0.5, 0.5, 1.0, 1.0, muted=True, solo=True, any_solo=True)
        assert eff_l == 0.0
        assert eff_r == 0.0


# ===========================================================================
# REST endpoints via FastAPI TestClient
# ===========================================================================

@pytest.fixture
def audio_client():
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from src.api.routes.cut_routes_audio import audio_router
    app = FastAPI()
    app.include_router(audio_router)
    return TestClient(app)


@pytest.fixture(autouse=True)
def reset_mixer_store():
    import src.services.cut_audio_engine as eng
    with eng._mixer_state_lock:
        eng._mixer_state_store.clear()
    yield
    with eng._mixer_state_lock:
        eng._mixer_state_store.clear()


class TestMixerRestGet:
    def test_get_default_state(self, audio_client):
        resp = audio_client.get("/audio/mixer?project_id=p1")
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["master_volume"] == 1.0
        assert data["master_pan"] == 0.0
        assert data["lanes"] == {}

    def test_get_after_set(self, audio_client):
        audio_client.post("/audio/mixer", json={
            "project_id": "p2",
            "lanes": {"A1": {"volume": 0.7, "pan": 0.1, "muted": False, "solo": False}},
            "master_volume": 0.9,
            "master_pan": 0.2,
        })
        resp = audio_client.get("/audio/mixer?project_id=p2")
        assert resp.status_code == 200
        data = resp.json()
        assert data["master_volume"] == pytest.approx(0.9)
        assert data["master_pan"] == pytest.approx(0.2)
        assert "A1" in data["lanes"]


class TestMixerRestPost:
    def test_post_saves_full_state(self, audio_client):
        resp = audio_client.post("/audio/mixer", json={
            "project_id": "p3",
            "lanes": {
                "A1": {"volume": 0.8, "pan": -0.3, "muted": True, "solo": False},
                "A2": {"volume": 1.0, "pan": 0.0, "muted": False, "solo": True},
            },
            "master_volume": 1.1,
            "master_pan": 0.0,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["lanes"]["A1"]["muted"] is True
        assert data["lanes"]["A2"]["solo"] is True

    def test_post_requires_valid_volume_range(self, audio_client):
        resp = audio_client.post("/audio/mixer", json={
            "project_id": "p4",
            "master_volume": 2.0,  # > 1.5
        })
        assert resp.status_code == 422


class TestMixerRestPatchTrack:
    def test_patch_track_volume(self, audio_client):
        resp = audio_client.patch("/audio/mixer/track/A1", json={
            "project_id": "p5",
            "volume": 0.6,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["lane_id"] == "A1"
        assert data["lanes"]["A1"]["volume"] == pytest.approx(0.6)

    def test_patch_track_mute(self, audio_client):
        resp = audio_client.patch("/audio/mixer/track/B2", json={
            "project_id": "p6",
            "muted": True,
        })
        assert resp.status_code == 200
        assert resp.json()["lanes"]["B2"]["muted"] is True

    def test_patch_track_solo(self, audio_client):
        resp = audio_client.patch("/audio/mixer/track/C3", json={
            "project_id": "p7",
            "solo": True,
        })
        assert resp.status_code == 200
        assert resp.json()["lanes"]["C3"]["solo"] is True

    def test_patch_track_partial_doesnt_reset_others(self, audio_client):
        audio_client.patch("/audio/mixer/track/A1", json={
            "project_id": "p8",
            "volume": 0.5,
            "pan": 0.3,
        })
        resp = audio_client.patch("/audio/mixer/track/A1", json={
            "project_id": "p8",
            "muted": True,  # only muted
        })
        assert resp.json()["lanes"]["A1"]["volume"] == pytest.approx(0.5)  # unchanged
        assert resp.json()["lanes"]["A1"]["pan"] == pytest.approx(0.3)

    def test_patch_track_rejects_invalid_pan(self, audio_client):
        resp = audio_client.patch("/audio/mixer/track/A1", json={
            "project_id": "p9",
            "pan": 2.0,  # > 1.0
        })
        assert resp.status_code == 422


class TestMixerRestPatchMaster:
    def test_patch_master_volume(self, audio_client):
        resp = audio_client.patch("/audio/mixer/master", json={
            "project_id": "p10",
            "volume": 0.75,
        })
        assert resp.status_code == 200
        assert resp.json()["master_volume"] == pytest.approx(0.75)

    def test_patch_master_pan(self, audio_client):
        resp = audio_client.patch("/audio/mixer/master", json={
            "project_id": "p11",
            "pan": -0.5,
        })
        assert resp.status_code == 200
        assert resp.json()["master_pan"] == pytest.approx(-0.5)

    def test_patch_master_partial(self, audio_client):
        audio_client.patch("/audio/mixer/master", json={"project_id": "p12", "volume": 0.8, "pan": 0.4})
        resp = audio_client.patch("/audio/mixer/master", json={"project_id": "p12", "volume": 0.6})
        assert resp.json()["master_pan"] == pytest.approx(0.4)  # unchanged


# ===========================================================================
# Timeline ops: set_track_volume/pan/mute/solo, set_master_volume/pan
# ===========================================================================

class TestMixerTimelineOps:
    """Test mixer timeline ops via _apply_timeline_ops."""

    def _apply(self, state, ops):
        from src.api.routes.cut_routes import _apply_timeline_ops
        return _apply_timeline_ops(state, ops)

    def _base_state(self, lanes=None):
        return {
            "lanes": lanes or [{"lane_id": "A1", "clips": []}],
            "project_id": "test_proj",
        }

    def test_set_track_volume(self):
        state, applied = self._apply(self._base_state(), [
            {"op": "set_track_volume", "lane_id": "A1", "volume": 0.7},
        ])
        assert state["mixer"]["lanes"]["A1"]["volume"] == pytest.approx(0.7)
        assert applied[0]["op"] == "set_track_volume"

    def test_set_track_pan(self):
        state, _ = self._apply(self._base_state(), [
            {"op": "set_track_pan", "lane_id": "A1", "pan": -0.5},
        ])
        assert state["mixer"]["lanes"]["A1"]["pan"] == pytest.approx(-0.5)

    def test_set_track_mute(self):
        state, _ = self._apply(self._base_state(), [
            {"op": "set_track_mute", "lane_id": "A1", "muted": True},
        ])
        assert state["mixer"]["lanes"]["A1"]["muted"] is True

    def test_set_track_solo(self):
        state, _ = self._apply(self._base_state(), [
            {"op": "set_track_solo", "lane_id": "A1", "solo": True},
        ])
        assert state["mixer"]["lanes"]["A1"]["solo"] is True

    def test_set_master_volume(self):
        state, _ = self._apply(self._base_state(), [
            {"op": "set_master_volume", "volume": 1.2},
        ])
        assert state["mixer"]["master_volume"] == pytest.approx(1.2)

    def test_set_master_pan(self):
        state, _ = self._apply(self._base_state(), [
            {"op": "set_master_pan", "pan": 0.4},
        ])
        assert state["mixer"]["master_pan"] == pytest.approx(0.4)

    def test_volume_clamped_to_range(self):
        state, _ = self._apply(self._base_state(), [
            {"op": "set_track_volume", "lane_id": "A1", "volume": 3.0},
        ])
        assert state["mixer"]["lanes"]["A1"]["volume"] <= 1.5

    def test_pan_clamped_to_range(self):
        state, _ = self._apply(self._base_state(), [
            {"op": "set_track_pan", "lane_id": "A1", "pan": -5.0},
        ])
        assert state["mixer"]["lanes"]["A1"]["pan"] >= -1.0

    def test_missing_lane_id_raises(self):
        with pytest.raises(ValueError, match="lane_id"):
            self._apply(self._base_state(), [
                {"op": "set_track_volume", "volume": 0.5},  # no lane_id
            ])

    def test_multiple_mixer_ops_sequence(self):
        state, applied = self._apply(self._base_state(), [
            {"op": "set_track_volume", "lane_id": "A1", "volume": 0.8},
            {"op": "set_track_pan", "lane_id": "A1", "pan": 0.2},
            {"op": "set_master_volume", "volume": 0.9},
        ])
        assert state["mixer"]["lanes"]["A1"]["volume"] == pytest.approx(0.8)
        assert state["mixer"]["lanes"]["A1"]["pan"] == pytest.approx(0.2)
        assert state["mixer"]["master_volume"] == pytest.approx(0.9)
        assert len(applied) == 3


# ===========================================================================
# WebSocket mixer_levels_request
# ===========================================================================

class TestMixerWebSocket:
    """Test mixer_levels_request handler in isolation."""

    def _make_sio_mock(self):
        """Return a mock socketio with event registry."""
        sio = MagicMock()
        handlers = {}

        def on_decorator(event_name):
            def decorator(fn):
                handlers[event_name] = fn
                return fn
            return decorator

        sio.on.side_effect = on_decorator
        sio.emit = AsyncMock()
        sio._handlers = handlers
        return sio

    def test_mixer_levels_emitted_for_each_lane(self):
        from src.api.handlers.audio_scope_socket_handler import register_audio_scope_socket_handlers
        import src.services.cut_audio_engine as eng

        # Set up mixer state with two lanes
        with eng._mixer_state_lock:
            eng._mixer_state_store.clear()
        eng.update_lane_mixer("proj_ws", "A1", volume=0.8, muted=False)
        eng.update_lane_mixer("proj_ws", "A2", volume=1.0, muted=True)

        sio = self._make_sio_mock()
        register_audio_scope_socket_handlers(sio)

        mock_levels = {"success": True, "rms_left": 0.3, "rms_right": 0.25, "peak_left": 0.4, "peak_right": 0.35}

        with patch("src.services.cut_ffmpeg_waveform.compute_audio_levels", return_value=mock_levels):
            handler = sio._handlers["mixer_levels_request"]
            asyncio.get_event_loop().run_until_complete(handler("sid1", {
                "project_id": "proj_ws",
                "sources": [
                    {"source_path": "/mock/clip1.mov", "lane_id": "A1", "time": 1.0},
                    {"source_path": "/mock/clip2.mov", "lane_id": "A2", "time": 2.0},
                ],
            }))

        sio.emit.assert_called_once()
        call_args = sio.emit.call_args
        event_name = call_args[0][0]
        payload = call_args[0][1]

        assert event_name == "mixer_levels_data"
        assert payload["success"] is True
        assert "A1" in payload["lanes"]
        assert "A2" in payload["lanes"]
        assert payload["lanes"]["A2"]["muted"] is True
        assert payload["lanes"]["A2"]["effective_rms_left"] == 0.0  # muted
        assert payload["lanes"]["A1"]["effective_rms_left"] > 0.0  # not muted
        assert "master" in payload

    def test_mixer_levels_empty_sources_no_emit(self):
        from src.api.handlers.audio_scope_socket_handler import register_audio_scope_socket_handlers
        sio = self._make_sio_mock()
        register_audio_scope_socket_handlers(sio)

        handler = sio._handlers["mixer_levels_request"]
        asyncio.get_event_loop().run_until_complete(handler("sid2", {
            "project_id": "p",
            "sources": [],
        }))
        sio.emit.assert_not_called()

    def test_mixer_levels_non_dict_ignored(self):
        from src.api.handlers.audio_scope_socket_handler import register_audio_scope_socket_handlers
        sio = self._make_sio_mock()
        register_audio_scope_socket_handlers(sio)

        handler = sio._handlers["mixer_levels_request"]
        asyncio.get_event_loop().run_until_complete(handler("sid3", "bad_payload"))
        sio.emit.assert_not_called()
