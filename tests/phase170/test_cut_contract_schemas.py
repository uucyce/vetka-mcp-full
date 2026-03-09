import json
from pathlib import Path


def test_cut_contract_schemas_parse_as_json():
    paths = [
        Path('/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/docs/contracts/cut_bootstrap_state_v1.schema.json'),
        Path('/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/docs/contracts/cut_bootstrap_v1.schema.json'),
        Path('/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/docs/contracts/cut_project_state_v1.schema.json'),
        Path('/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/docs/contracts/cut_project_v1.schema.json'),
        Path('/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/docs/contracts/cut_time_marker_apply_v1.schema.json'),
        Path('/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/docs/contracts/cut_time_marker_bundle_v1.schema.json'),
        Path('/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/docs/contracts/cut_time_marker_v1.schema.json'),
        Path('/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/docs/contracts/cut_timeline_apply_v1.schema.json'),
        Path('/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/docs/contracts/cut_timeline_state_v1.schema.json'),
        Path('/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/docs/contracts/cut_scene_graph_apply_v1.schema.json'),
        Path('/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/docs/contracts/cut_scene_graph_v1.schema.json'),
        Path('/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/docs/contracts/cut_mcp_job_v1.schema.json'),
        Path('/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/docs/contracts/cut_thumbnail_bundle_v1.schema.json'),
        Path('/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/docs/contracts/cut_transcript_bundle_v1.schema.json'),
        Path('/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/docs/contracts/cut_waveform_bundle_v1.schema.json'),
        Path('/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/docs/contracts/cut_worker_task_v1.schema.json'),
    ]
    for path in paths:
        payload = json.loads(path.read_text(encoding='utf-8'))
        assert isinstance(payload, dict)
        assert '$schema' in payload
