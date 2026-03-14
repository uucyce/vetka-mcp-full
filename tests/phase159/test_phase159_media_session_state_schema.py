from pathlib import Path

import json
import jsonschema
import pytest


SCHEMA_PATH = Path("/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/docs/contracts/artifact_media_session_state_v1.schema.json")


def _schema() -> dict:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def _base_state() -> dict:
    return {
        "schema_version": "artifact_media_session_state_v1",
        "path": "/Users/danilagulin/work/teletape_temp/berlin/video_gen/clip01.mp4",
        "current_time": 8.25,
        "is_playing": False,
        "volume": 0.7,
        "is_muted": False,
        "quality_scale": "quarter",
        "playback_rate": 1.25,
        "window_mode": "detached",
        "fullscreen_mode": "native_window",
        "updated_at_ms": 1762230000999,
    }


def test_phase159_media_session_state_accepts_valid_payload():
    payload = _base_state()
    jsonschema.validate(instance=payload, schema=_schema())


def test_phase159_media_session_state_rejects_invalid_quality_scale():
    payload = _base_state()
    payload["quality_scale"] = "preview"
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(instance=payload, schema=_schema())


def test_phase159_media_session_state_rejects_out_of_range_volume():
    payload = _base_state()
    payload["volume"] = 1.5
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(instance=payload, schema=_schema())

