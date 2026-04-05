import pytest
import json
from pathlib import Path

pytestmark = pytest.mark.stale(reason="CUT API refactored — bootstrap/project_state contracts changed")

from src.services.cut_scene_graph_taxonomy import SCENE_GRAPH_EDGE_TYPES, SCENE_GRAPH_NODE_TYPES


def test_cut_contract_schemas_parse_as_json():
    paths = [
        Path('/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/docs/contracts/cut_bootstrap_state_v1.schema.json'),
        Path('/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/docs/contracts/cut_bootstrap_v1.schema.json'),
        Path('/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/docs/contracts/cut_audio_sync_result_v1.schema.json'),
        Path('/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/docs/contracts/cut_montage_state_v1.schema.json'),
        Path('/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/docs/contracts/cut_music_sync_result_v1.schema.json'),
        Path('/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/docs/contracts/cut_meta_sync_result_v1.schema.json'),
        Path('/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/docs/contracts/cut_project_state_v1.schema.json'),
        Path('/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/docs/contracts/cut_project_v1.schema.json'),
        Path('/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/docs/contracts/cut_rhythm_surface_v1.schema.json'),
        Path('/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/docs/contracts/cut_slice_bundle_v1.schema.json'),
        Path('/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/docs/contracts/cut_sync_surface_v1.schema.json'),
        Path('/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/docs/contracts/cut_timecode_sync_result_v1.schema.json'),
        Path('/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/docs/contracts/cut_time_marker_apply_v1.schema.json'),
        Path('/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/docs/contracts/cut_time_marker_bundle_v1.schema.json'),
        Path('/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/docs/contracts/cut_time_marker_v1.schema.json'),
        Path('/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/docs/contracts/cut_timeline_apply_v1.schema.json'),
        Path('/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/docs/contracts/cut_timeline_state_v1.schema.json'),
        Path('/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/docs/contracts/cut_scene_graph_apply_v1.schema.json'),
        Path('/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/docs/contracts/cut_scene_graph_v1.schema.json'),
        Path('/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/docs/contracts/cut_scene_graph_view_v1.schema.json'),
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


def test_cut_scene_graph_taxonomy_constants_match_contract_schema():
    schema_path = Path('/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/docs/contracts/cut_scene_graph_v1.schema.json')
    payload = json.loads(schema_path.read_text(encoding='utf-8'))

    node_enum = payload["properties"]["nodes"]["items"]["properties"]["node_type"]["enum"]
    edge_enum = payload["properties"]["edges"]["items"]["properties"]["edge_type"]["enum"]

    assert tuple(node_enum) == SCENE_GRAPH_NODE_TYPES
    assert tuple(edge_enum) == SCENE_GRAPH_EDGE_TYPES


def test_cut_scene_graph_view_schema_exposes_focus_and_layout_hints():
    schema_path = Path('/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/docs/contracts/cut_scene_graph_view_v1.schema.json')
    payload = json.loads(schema_path.read_text(encoding='utf-8'))

    assert "focus" in payload["required"]
    assert "layout_hints" in payload["required"]
    assert payload["properties"]["focus"]["required"] == [
        "selected_clip_ids",
        "selected_scene_ids",
        "focused_node_ids",
        "anchor_node_id",
    ]
    assert payload["properties"]["layout_hints"]["required"] == [
        "structural_edge_types",
        "intelligence_edge_types",
        "primary_rank_edge_types",
    ]
    assert "crosslinks" in payload["required"]
    assert payload["properties"]["crosslinks"]["required"] == [
        "by_clip_id",
        "by_scene_id",
        "by_source_path",
    ]
    assert "structural_subgraph" in payload["required"]
    assert "overlay_edges" in payload["required"]
    assert "dag_projection" in payload["required"]
    assert "inspector" in payload["required"]


def test_cut_project_state_schema_exposes_montage_state():
    schema_path = Path('/Users/danilagulin/Documents/VETKA_Project/vetka_live_03/docs/contracts/cut_project_state_v1.schema.json')
    payload = json.loads(schema_path.read_text(encoding='utf-8'))

    assert "montage_state" in payload["properties"]
    assert "montage_ready" in payload["properties"]
    assert "rhythm_surface" in payload["properties"]
    assert "rhythm_surface_ready" in payload["properties"]
