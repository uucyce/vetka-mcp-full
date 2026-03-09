from pathlib import Path

import json
import jsonschema
import pytest


SCHEMA_PATH = Path("/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/docs/contracts/artifact_media_window_contract_v1.schema.json")


def _schema() -> dict:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def _base_payload() -> dict:
    return {
        "schema_version": "artifact_media_window_contract_v1",
        "request_id": "3cc6e8e2-6b53-4efb-8d66-a1d9fbb3f4a5",
        "action": "open_media_window",
        "target_window": "detached",
        "payload": {
            "path": "/Users/danilagulin/work/teletape_temp/berlin/video_gen/clip01.mp4"
        },
        "timestamp_ms": 1762230000123,
    }


def test_phase159_media_window_contract_accepts_open_media_window():
    payload = _base_payload()
    jsonschema.validate(instance=payload, schema=_schema())


def test_phase159_media_window_contract_rejects_missing_required_action_payload():
    payload = _base_payload()
    payload["action"] = "set_quality_scale"
    payload["payload"] = {}
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(instance=payload, schema=_schema())


def test_phase159_media_window_contract_accepts_sync_playback_state():
    payload = _base_payload()
    payload["action"] = "sync_playback_state"
    payload["payload"] = {
        "session_state": {
            "schema_version": "artifact_media_session_state_v1",
            "path": "/Users/danilagulin/work/teletape_temp/berlin/video_gen/clip01.mp4",
            "current_time": 12.4,
            "is_playing": True,
            "volume": 0.85,
            "is_muted": False,
            "quality_scale": "half",
            "playback_rate": 1.0,
        }
    }
    jsonschema.validate(instance=payload, schema=_schema())

