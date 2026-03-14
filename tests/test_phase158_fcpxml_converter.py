from xml.etree import ElementTree as ET

from src.services.converters.fcpxml_converter import (
    build_fcpxml,
    build_fcpxml_from_transcript,
)


def test_build_fcpxml_minimal_structure():
    xml_text = build_fcpxml(
        {
            "project_name": "VETKA_Test",
            "sequence_name": "Scene_01",
            "source_path": "/tmp/source.mp4",
            "fps": 25.0,
            "duration_sec": 8.0,
            "clips": [
                {"start_sec": 0.0, "end_sec": 2.0, "name": "clip_a"},
                {"start_sec": 2.0, "end_sec": 4.5, "name": "clip_b"},
            ],
        }
    )
    root = ET.fromstring(xml_text)
    assert root.tag == "fcpxml"
    assert root.attrib.get("version")
    assert root.find("./resources") is not None
    assert root.find(".//project") is not None
    assert root.find(".//sequence") is not None
    assert root.find(".//asset-clip") is not None
    assert "source.mp4" in xml_text


def test_build_fcpxml_from_transcript_maps_segments_to_asset_clips():
    xml_text = build_fcpxml_from_transcript(
        source_path="/tmp/voice.m4a",
        transcript_normalized_json={
            "duration_sec": 10.0,
            "segments": [
                {"start_sec": 0.5, "end_sec": 1.1, "text": "hello"},
                {"start_sec": 2.0, "end_sec": 2.8, "text": "world"},
            ],
        },
        sequence_name="AudioSeq",
        fps=30.0,
    )
    root = ET.fromstring(xml_text)
    clips = root.findall(".//asset-clip")
    assert len(clips) >= 2
    names = [c.attrib.get("name", "") for c in clips]
    assert any("seg_0001" in n for n in names)
