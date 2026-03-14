from xml.etree import ElementTree as ET

import pytest
import threading
import time

from src.services.premiere_adapter import (
    MCPLiveBridgePremiereAdapter,
    PremiereExportRequest,
    get_premiere_adapter,
)


def _sample_transcript() -> dict:
    return {
        "duration_sec": 6.0,
        "segments": [
            {"start_sec": 0.2, "end_sec": 1.0, "text": "line one"},
            {"start_sec": 2.1, "end_sec": 2.8, "text": "line two"},
        ],
    }


def test_phase158_premiere_adapter_exports_premiere_xml_lane():
    adapter = get_premiere_adapter("xml_interchange")
    artifact = adapter.export_from_transcript(
        PremiereExportRequest(
            source_path="/tmp/sample.mp4",
            transcript_normalized_json=_sample_transcript(),
            sequence_name="SeqA",
            fps=24.0,
            lane="premiere_xml",
        )
    )
    assert artifact.lane == "premiere_xml"
    assert artifact.file_ext == ".xml"
    root = ET.fromstring(artifact.xml_text)
    assert root.tag == "xmeml"


def test_phase158_premiere_adapter_exports_fcpxml_lane():
    adapter = get_premiere_adapter("xml_interchange")
    artifact = adapter.export_from_transcript(
        PremiereExportRequest(
            source_path="/tmp/sample.mp4",
            transcript_normalized_json=_sample_transcript(),
            sequence_name="SeqB",
            fps=25.0,
            lane="fcpxml",
        )
    )
    assert artifact.lane == "fcpxml"
    assert artifact.file_ext == ".fcpxml"
    root = ET.fromstring(artifact.xml_text)
    assert root.tag == "fcpxml"


def test_phase158_premiere_adapter_rejects_unknown_lane():
    adapter = get_premiere_adapter("xml_interchange")
    with pytest.raises(ValueError):
        adapter.export_from_transcript(
            PremiereExportRequest(
                source_path="/tmp/sample.mp4",
                transcript_normalized_json=_sample_transcript(),
                lane="unknown_lane",
            )
        )


def test_phase158_mcp_live_bridge_adapter_fallback_when_unavailable(tmp_path):
    bridge_dir = tmp_path / "missing_bridge_dir"
    adapter = MCPLiveBridgePremiereAdapter(bridge_dir=str(bridge_dir), timeout_sec=0.2, poll_interval_sec=0.02)
    artifact = adapter.export_from_transcript(
        PremiereExportRequest(
            source_path="/tmp/sample.mp4",
            transcript_normalized_json=_sample_transcript(),
            lane="premiere_xml",
        )
    )
    assert artifact.bridge_mode == "mcp_live_bridge"
    assert artifact.degraded_mode is True
    assert artifact.degraded_reason == "bridge_unavailable_or_timeout"
    root = ET.fromstring(artifact.xml_text)
    assert root.tag == "xmeml"


def test_phase158_mcp_live_bridge_adapter_reads_result_file(tmp_path):
    bridge_dir = tmp_path / "bridge"
    commands = bridge_dir / "commands"
    results = bridge_dir / "results"
    commands.mkdir(parents=True, exist_ok=True)
    results.mkdir(parents=True, exist_ok=True)

    def _worker():
        deadline = time.time() + 2.0
        while time.time() < deadline:
            files = sorted(commands.glob("*.json"))
            if not files:
                time.sleep(0.01)
                continue
            req_file = files[0]
            req_data = req_file.read_text(encoding="utf-8")
            import json

            req = json.loads(req_data)
            out = {
                "request_id": req["request_id"],
                "lane": req.get("lane", "premiere_xml"),
                "xml_text": "<?xml version=\"1.0\" ?><xmeml version=\"5\"></xmeml>",
            }
            (results / f"{req['request_id']}.json").write_text(json.dumps(out), encoding="utf-8")
            return

    t = threading.Thread(target=_worker, daemon=True)
    t.start()

    adapter = MCPLiveBridgePremiereAdapter(bridge_dir=str(bridge_dir), timeout_sec=1.0, poll_interval_sec=0.02)
    artifact = adapter.export_from_transcript(
        PremiereExportRequest(
            source_path="/tmp/sample.mp4",
            transcript_normalized_json=_sample_transcript(),
            lane="premiere_xml",
        )
    )
    assert artifact.bridge_mode == "mcp_live_bridge"
    assert artifact.degraded_mode is False
    root = ET.fromstring(artifact.xml_text)
    assert root.tag == "xmeml"
