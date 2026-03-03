import json
from pathlib import Path

import jsonschema


SCHEMA_PATH = Path("/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/docs/contracts/vetka_montage_sheet_v1.schema.json")


def _load_schema() -> dict:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def test_phase158_montage_sheet_schema_accepts_valid_payload():
    schema = _load_schema()
    payload = {
        "schema_version": "vetka_montage_sheet_v1",
        "project": {
            "project_id": "berlin_ironwall",
            "project_name": "Berlin Ironwall",
            "fps": 24.0,
            "timezone": "Europe/Berlin",
        },
        "records": [
            {
                "record_id": "rec_001",
                "scene_id": "scene_01",
                "take_id": "take_A",
                "shot_id": "shot_010",
                "camera_id": "cam_A",
                "source_file": "/data/scene_01_take_A.mp4",
                "start_tc": "00:00:10:12",
                "end_tc": "00:00:18:20",
                "duration_sec": 8.333,
                "intra_motion_score": 0.62,
                "cut_rhythm_hint": 0.71,
                "hero_entities": ["hero_main"],
                "location_entities": ["roof"],
                "action_tags": ["run", "turn"],
                "quality_flags": ["sharp", "stable"],
                "notes": "usable take",
            }
        ],
    }
    jsonschema.validate(instance=payload, schema=schema)


def test_phase158_montage_sheet_schema_rejects_missing_required_fields():
    schema = _load_schema()
    invalid = {
        "schema_version": "vetka_montage_sheet_v1",
        "project": {"project_id": "p1", "project_name": "P"},
        "records": [
            {
                "record_id": "rec_001",
                "scene_id": "scene_01",
                "take_id": "take_A",
                "source_file": "/data/x.mp4",
                "start_tc": "00:00:00:00",
                "end_tc": "00:00:01:00"
            }
        ],
    }
    try:
        jsonschema.validate(instance=invalid, schema=schema)
        raise AssertionError("Expected validation error for missing duration_sec")
    except jsonschema.ValidationError:
        pass
