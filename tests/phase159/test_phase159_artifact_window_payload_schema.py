from pathlib import Path

import json
import jsonschema
import pytest


SCHEMA_PATH = Path("/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/docs/contracts/artifact_window_payload_v1.schema.json")


def _schema() -> dict:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def _base_payload() -> dict:
    return {
        "schema_version": "artifact_window_payload_v1",
        "path": "/Users/danilagulin/work/teletape_temp/berlin/video_gen/clip01.mp4",
        "name": "clip01.mp4",
        "extension": "mp4",
        "artifact_id": "artifact_159_clip01",
        "initial_seek_sec": 1.25,
        "content_mode": "file",
    }


def test_phase159_artifact_window_payload_schema_accepts_valid_payload():
    jsonschema.validate(instance=_base_payload(), schema=_schema())


def test_phase159_artifact_window_payload_schema_rejects_missing_required_fields():
    payload = _base_payload()
    payload.pop("path")
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(instance=payload, schema=_schema())


def test_phase159_artifact_window_payload_schema_rejects_invalid_content_mode():
    payload = _base_payload()
    payload["content_mode"] = "media"
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(instance=payload, schema=_schema())
