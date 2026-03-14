import json
from pathlib import Path

import jsonschema
import pytest


SCHEMA_PATH = Path("/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/docs/contracts/media_mcp_job_v1.schema.json")


def _schema() -> dict:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def _base_payload() -> dict:
    return {
        "schema_version": "media_mcp_job_v1",
        "job_id": "2cc4f2f1-050f-4c67-b8f2-43f981cabfe1",
        "idempotency_key": "ingest:5a7a8f11",
        "job_type": "ingest",
        "queue_lane": "interactive",
        "priority": "normal",
        "state": "queued",
        "progress": 0.0,
        "retry_count": 0,
        "max_retries": 3,
        "input": {
            "media_path": "/tmp/clip.mp4",
            "metadata": {"duration_sec": 10.0, "format": "mp4"},
        },
        "timestamps": {
            "queued_at_ms": 1735689600000,
            "updated_at_ms": 1735689600000,
        },
    }


def test_phase159_media_mcp_job_schema_accepts_valid_done_payload():
    payload = _base_payload()
    payload["state"] = "done"
    payload["progress"] = 1.0
    payload["result"] = {
        "artifact_refs": ["artifact://1"],
        "summary": "ok",
    }
    payload["timestamps"]["finished_at_ms"] = 1735689601000
    jsonschema.validate(instance=payload, schema=_schema())


def test_phase159_media_mcp_job_schema_rejects_invalid_state():
    payload = _base_payload()
    payload["state"] = "paused"
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(instance=payload, schema=_schema())


def test_phase159_media_mcp_job_schema_requires_error_for_error_state():
    payload = _base_payload()
    payload["state"] = "error"
    payload["progress"] = 0.4
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(instance=payload, schema=_schema())


def test_phase159_media_mcp_job_schema_rejects_partial_with_progress_one():
    payload = _base_payload()
    payload["state"] = "partial"
    payload["progress"] = 1.0
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(instance=payload, schema=_schema())
