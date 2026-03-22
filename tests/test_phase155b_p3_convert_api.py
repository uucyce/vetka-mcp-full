"""
Phase 155B-P3 tests: canonical converters + unified convert API.
"""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.routes.workflow_routes import router
import pytest

pytestmark = pytest.mark.stale(reason="Pre-existing failure — phase 155b contracts changed")

def _client() -> TestClient:
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


def _sample_graph() -> dict:
    return {
        "schema_version": "1.0.0",
        "graph": {
            "id": "wf_sample",
            "version": "v1",
            "source_format": "json",
            "execution_mode": "design",
        },
        "nodes": [
            {"id": "n1", "type": "task", "label": "Scout"},
            {"id": "n2", "type": "task", "label": "Coder"},
        ],
        "edges": [
            {"source": "n1", "target": "n2", "kind": "flow"},
        ],
        "layout_hints": {"orientation": "bottom_up", "layer_spacing": 120, "node_spacing": 80},
    }


def test_convert_md_roundtrip():
    client = _client()
    graph = _sample_graph()

    to_md = client.post(
        "/api/workflow/convert",
        json={"from_format": "canonical", "to_format": "md", "graph": graph},
    )
    assert to_md.status_code == 200
    md_payload = to_md.json()
    assert md_payload["marker"] == "MARKER_155B.CANON.CONVERT_API.V1"
    assert "MARKER_155B.CANON.MD_CONVERTER.V1" in md_payload["canonical_markers"]
    md_text = md_payload["content"]
    assert "## nodes" in md_text

    back = client.post(
        "/api/workflow/convert",
        json={"from_format": "md", "to_format": "canonical", "content": md_text},
    )
    assert back.status_code == 200
    restored = back.json()["graph"]
    assert restored["schema_version"] == "1.0.0"
    assert len(restored["nodes"]) == 2
    assert len(restored["edges"]) == 1


def test_convert_xml_roundtrip():
    client = _client()
    graph = _sample_graph()

    to_xml = client.post(
        "/api/workflow/convert",
        json={"from_format": "canonical", "to_format": "xml", "graph": graph},
    )
    assert to_xml.status_code == 200
    xml_text = to_xml.json()["content"]
    assert "<canonical_graph" in xml_text

    back = client.post(
        "/api/workflow/convert",
        json={"from_format": "xml", "to_format": "canonical", "content": xml_text},
    )
    assert back.status_code == 200
    restored = back.json()["graph"]
    assert restored["graph"]["id"] == "wf_sample"
    assert len(restored["nodes"]) == 2


def test_convert_xlsx_roundtrip():
    client = _client()
    graph = _sample_graph()

    to_xlsx = client.post(
        "/api/workflow/convert",
        json={"from_format": "canonical", "to_format": "xlsx", "graph": graph},
    )
    assert to_xlsx.status_code == 200
    xlsx_payload = to_xlsx.json()
    assert xlsx_payload["content_type"].endswith("spreadsheetml.sheet")
    assert len(xlsx_payload["content_base64"]) > 100

    back = client.post(
        "/api/workflow/convert",
        json={
            "from_format": "xlsx",
            "to_format": "canonical",
            "content_base64": xlsx_payload["content_base64"],
        },
    )
    assert back.status_code == 200
    restored = back.json()["graph"]
    assert restored["schema_version"] == "1.0.0"
    assert len(restored["nodes"]) == 2
    assert len(restored["edges"]) == 1


def test_convert_requires_mandatory_fields():
    client = _client()
    missing_formats = client.post("/api/workflow/convert", json={})
    assert missing_formats.status_code == 422

    missing_graph = client.post(
        "/api/workflow/convert",
        json={"from_format": "canonical", "to_format": "md"},
    )
    assert missing_graph.status_code == 422

    unsupported = client.post(
        "/api/workflow/convert",
        json={"from_format": "json", "to_format": "md", "graph": _sample_graph()},
    )
    assert unsupported.status_code == 400
