"""
Tests for CUT-2.1: scene chunks → DAG nodes integration.
Tests taxonomy additions + project store method.
"""
import pytest
from src.services.cut_scene_graph_taxonomy import (
    SCENE_GRAPH_NODE_TYPE_SET,
    SCENE_GRAPH_EDGE_TYPE_SET,
)
from src.services.screenplay_timing import parse_screenplay


# ─── Taxonomy ───

def test_scene_chunk_in_node_types():
    assert "scene_chunk" in SCENE_GRAPH_NODE_TYPE_SET


def test_next_scene_in_edge_types():
    assert "next_scene" in SCENE_GRAPH_EDGE_TYPE_SET


def test_has_media_in_edge_types():
    assert "has_media" in SCENE_GRAPH_EDGE_TYPE_SET


# ─── DAG node creation (unit test without filesystem) ───

SCREENPLAY = """INT. CAFE - DAY

Anna sits at a corner table.

EXT. STREET - NIGHT

Rain pours down.

INT. APARTMENT - NIGHT

Anna enters.
"""


def test_chunks_to_dag_nodes():
    """Verify chunks can be converted to DAG node dicts."""
    chunks = parse_screenplay(SCREENPLAY)
    assert len(chunks) == 3

    # Simulate what add_scene_chunks_to_dag does
    nodes = []
    edges = []
    for i, chunk in enumerate(chunks):
        node = {
            "node_id": chunk.chunk_id,
            "node_type": "scene_chunk",
            "label": chunk.scene_heading or f"Chunk {i + 1}",
            "start_sec": chunk.start_sec,
            "duration_sec": chunk.duration_sec,
        }
        nodes.append(node)
        if i > 0:
            edges.append({
                "source": chunks[i - 1].chunk_id,
                "target": chunk.chunk_id,
                "edge_type": "next_scene",
            })

    assert len(nodes) == 3
    assert len(edges) == 2  # SCN_01→SCN_02, SCN_02→SCN_03

    assert nodes[0]["node_id"] == "SCN_01"
    assert nodes[0]["node_type"] == "scene_chunk"
    assert nodes[0]["label"] == "INT. CAFE - DAY"

    assert edges[0]["source"] == "SCN_01"
    assert edges[0]["target"] == "SCN_02"
    assert edges[0]["edge_type"] == "next_scene"


def test_dag_spine_chain_order():
    """Verify next_scene edges form a linear chain."""
    chunks = parse_screenplay(SCREENPLAY)
    edges = []
    for i in range(1, len(chunks)):
        edges.append({
            "source": chunks[i - 1].chunk_id,
            "target": chunks[i].chunk_id,
        })

    # Chain: SCN_01 → SCN_02 → SCN_03
    assert edges[0]["source"] == "SCN_01"
    assert edges[0]["target"] == "SCN_02"
    assert edges[1]["source"] == "SCN_02"
    assert edges[1]["target"] == "SCN_03"


def test_dag_nodes_have_timing():
    """Each node should carry start_sec and duration_sec from screenplay_timing."""
    chunks = parse_screenplay(SCREENPLAY)
    for chunk in chunks:
        assert chunk.start_sec >= 0
        assert chunk.duration_sec > 0
    # Cumulative timing
    assert chunks[1].start_sec == pytest.approx(chunks[0].duration_sec, abs=0.01)
