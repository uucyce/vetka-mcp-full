"""
MARKER_172.5.EXPORT_TESTS
Tests for CUT export endpoints: Premiere XML, FCPXML.
Verifies timeline → XML conversion, marker inclusion, contract shape.
"""
import json
import time
from pathlib import Path
from xml.etree import ElementTree as ET

from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.routes.cut_routes import router
from src.services.cut_project_store import CutProjectStore


def _make_client() -> TestClient:
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


def _bootstrap_project(tmp_path: Path) -> tuple[TestClient, str, str]:
    """Bootstrap a CUT project with 2 clips and return (client, sandbox, project_id)."""
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    (source_dir / "cam_a.mp4").write_bytes(b"\x00" * 20)
    (source_dir / "cam_b.mp4").write_bytes(b"\x00" * 20)

    sandbox = tmp_path / "sandbox"
    for d in ("config", "cut_runtime", "cut_storage", "core_mirror"):
        (sandbox / d).mkdir(parents=True)
    (sandbox / "config" / "cut_core_mirror_manifest.json").write_text("{}\n")

    client = _make_client()
    resp = client.post(
        "/api/cut/bootstrap",
        json={
            "source_path": str(source_dir),
            "sandbox_root": str(sandbox),
            "project_name": "Export Test",
        },
    )
    assert resp.status_code == 200, resp.text
    project_id = resp.json()["project"]["project_id"]

    # Run scene assembly to populate timeline
    job = client.post(
        "/api/cut/scene-assembly-async",
        json={"sandbox_root": str(sandbox), "project_id": project_id},
    )
    for _ in range(30):
        r = client.get(f"/api/cut/job/{job.json()['job_id']}")
        if r.json()["job"]["state"] in {"done", "error"}:
            break
        time.sleep(0.05)

    return client, str(sandbox), project_id


# ─── Premiere XML export ───


def test_premiere_xml_export_success(tmp_path: Path):
    client, sandbox, project_id = _bootstrap_project(tmp_path)

    resp = client.post(
        "/api/cut/export/premiere-xml",
        json={
            "sandbox_root": sandbox,
            "project_id": project_id,
            "sequence_name": "Test_Seq",
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["schema_version"] == "cut_export_result_v1"
    assert body["format"] == "premiere_xml"
    assert body["project_id"] == project_id
    assert body["clip_count"] >= 1
    assert "generated_at" in body
    assert "xml_content" in body

    # Verify XML parses
    xml = body["xml_content"]
    assert "xmeml" in xml
    root = ET.fromstring(xml)
    assert root.tag == "xmeml"


def test_premiere_xml_has_clips(tmp_path: Path):
    client, sandbox, project_id = _bootstrap_project(tmp_path)

    resp = client.post(
        "/api/cut/export/premiere-xml",
        json={"sandbox_root": sandbox, "project_id": project_id},
    )
    body = resp.json()
    root = ET.fromstring(body["xml_content"])

    # Find clipitems
    clipitems = root.findall(".//clipitem")
    assert len(clipitems) >= 1
    assert body["clip_count"] == len(clipitems)


def test_premiere_xml_no_timeline_returns_404(tmp_path: Path):
    sandbox = tmp_path / "sandbox"
    for d in ("config", "cut_runtime", "cut_storage", "core_mirror"):
        (sandbox / d).mkdir(parents=True)
    (sandbox / "config" / "cut_core_mirror_manifest.json").write_text("{}\n")

    client = _make_client()
    resp = client.post(
        "/api/cut/export/premiere-xml",
        json={"sandbox_root": str(sandbox), "project_id": "nonexistent"},
    )
    assert resp.status_code == 404


def test_premiere_xml_missing_params():
    client = _make_client()
    resp = client.post(
        "/api/cut/export/premiere-xml",
        json={"sandbox_root": "", "project_id": ""},
    )
    assert resp.status_code == 400


# ─── FCPXML export ───


def test_fcpxml_export_success(tmp_path: Path):
    client, sandbox, project_id = _bootstrap_project(tmp_path)

    resp = client.post(
        "/api/cut/export/fcpxml",
        json={
            "sandbox_root": sandbox,
            "project_id": project_id,
            "sequence_name": "FCP_Seq",
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["schema_version"] == "cut_export_result_v1"
    assert body["format"] == "fcpxml"
    assert body["clip_count"] >= 1

    root = ET.fromstring(body["xml_content"])
    assert root.tag == "fcpxml"
    assert root.attrib.get("version") == "1.10"


def test_fcpxml_has_asset_clips(tmp_path: Path):
    client, sandbox, project_id = _bootstrap_project(tmp_path)

    resp = client.post(
        "/api/cut/export/fcpxml",
        json={"sandbox_root": sandbox, "project_id": project_id},
    )
    body = resp.json()
    root = ET.fromstring(body["xml_content"])

    asset_clips = root.findall(".//asset-clip")
    assert len(asset_clips) >= 1
    assert body["clip_count"] == len(asset_clips)


def test_fcpxml_no_timeline_returns_404(tmp_path: Path):
    sandbox = tmp_path / "sandbox"
    for d in ("config", "cut_runtime", "cut_storage", "core_mirror"):
        (sandbox / d).mkdir(parents=True)
    (sandbox / "config" / "cut_core_mirror_manifest.json").write_text("{}\n")

    client = _make_client()
    resp = client.post(
        "/api/cut/export/fcpxml",
        json={"sandbox_root": str(sandbox), "project_id": "nonexistent"},
    )
    assert resp.status_code == 404


# ─── Export with markers ───


def test_export_includes_markers(tmp_path: Path):
    client, sandbox, project_id = _bootstrap_project(tmp_path)

    # Add markers via time-markers/apply
    source_dir = tmp_path / "source"
    media_path = str(source_dir / "cam_a.mp4")
    client.post(
        "/api/cut/time-markers/apply",
        json={
            "sandbox_root": sandbox,
            "project_id": project_id,
            "op": "create",
            "start_sec": 1.0,
            "end_sec": 1.5,
            "kind": "favorite",
            "label": "Beat marker",
            "media_path": media_path,
        },
    )
    client.post(
        "/api/cut/time-markers/apply",
        json={
            "sandbox_root": sandbox,
            "project_id": project_id,
            "op": "create",
            "start_sec": 5.0,
            "end_sec": 5.5,
            "kind": "insight",
            "label": "Important moment",
            "media_path": media_path,
        },
    )

    resp = client.post(
        "/api/cut/export/premiere-xml",
        json={"sandbox_root": sandbox, "project_id": project_id},
    )
    body = resp.json()
    assert body["marker_count"] == 2

    root = ET.fromstring(body["xml_content"])
    markers = root.findall(".//marker")
    assert len(markers) >= 2


# ─── Contract shape ───


def test_export_result_contract_shape(tmp_path: Path):
    client, sandbox, project_id = _bootstrap_project(tmp_path)

    resp = client.post(
        "/api/cut/export/premiere-xml",
        json={"sandbox_root": sandbox, "project_id": project_id},
    )
    body = resp.json()
    required_fields = [
        "schema_version", "format", "project_id",
        "clip_count", "marker_count", "xml_content", "generated_at",
    ]
    for field in required_fields:
        assert field in body, f"Missing field: {field}"


def test_both_formats_produce_different_output(tmp_path: Path):
    client, sandbox, project_id = _bootstrap_project(tmp_path)

    premiere = client.post(
        "/api/cut/export/premiere-xml",
        json={"sandbox_root": sandbox, "project_id": project_id},
    ).json()
    fcpxml = client.post(
        "/api/cut/export/fcpxml",
        json={"sandbox_root": sandbox, "project_id": project_id},
    ).json()

    assert premiere["format"] != fcpxml["format"]
    assert premiere["xml_content"] != fcpxml["xml_content"]
    assert premiere["clip_count"] == fcpxml["clip_count"]
