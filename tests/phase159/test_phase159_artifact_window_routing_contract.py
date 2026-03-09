from pathlib import Path

import json
import jsonschema
import pytest


ROOT = Path("/Users/danilagulin/Documents/VETKA_Project/vetka_live_03")
SCHEMA_PATH = ROOT / "docs/contracts/artifact_window_routing_v1.schema.json"


def _schema() -> dict:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def _artifact_payload() -> dict:
    return {
        "schema_version": "artifact_window_payload_v1",
        "path": "/Users/danilagulin/work/teletape_temp/berlin/video_gen/clip01.mp4",
        "name": "clip01.mp4",
        "extension": "mp4",
        "artifact_id": "artifact_159_clip01",
        "initial_seek_sec": 2.5,
        "content_mode": "file",
    }


def _base_routing(action: str) -> dict:
    payload = {
        "schema_version": "artifact_window_routing_v1",
        "request_id": "99f1a9d7-28a4-4df0-a77f-a269992fc6aa",
        "action": action,
        "payload": {},
        "timestamp_ms": 1762302000123,
    }
    if action == "open_artifact_window":
        payload["payload"] = {
            "window_label": "artifact-media",
            "artifact_payload": _artifact_payload(),
        }
    elif action in ("close_artifact_window", "focus_artifact_window"):
        payload["payload"] = {"window_label": "artifact-main"}
    elif action == "set_artifact_fullscreen":
        payload["payload"] = {
            "window_label": "artifact-media",
            "fullscreen_enabled": True,
        }
    return payload


def test_phase159_artifact_window_routing_contract_accepts_all_actions():
    schema = _schema()
    for action in (
        "open_artifact_window",
        "close_artifact_window",
        "focus_artifact_window",
        "set_artifact_fullscreen",
    ):
        jsonschema.validate(instance=_base_routing(action), schema=schema)


def test_phase159_artifact_window_routing_contract_rejects_missing_open_payload():
    payload = _base_routing("open_artifact_window")
    payload["payload"] = {"window_label": "artifact-media"}
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(instance=payload, schema=_schema())


def test_phase159_artifact_window_routing_contract_rejects_invalid_label():
    payload = _base_routing("close_artifact_window")
    payload["payload"]["window_label"] = "main"
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(instance=payload, schema=_schema())


def test_phase159_artifact_window_routing_contract_rejects_unknown_action():
    payload = _base_routing("close_artifact_window")
    payload["action"] = "open_media_window"
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(instance=payload, schema=_schema())
