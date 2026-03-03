import importlib.util
from pathlib import Path
from xml.etree import ElementTree as ET

import pytest

from src.services.converters.premiere_xml_converter import build_premiere_xml_from_transcript


BASELINE_FILE = Path("/Users/danilagulin/Documents/CinemaFactory/core/premiere_xml_generator_adobe.py")


@pytest.mark.integration
def test_premiere_baseline_cinemafactory_structural_compat():
    if not BASELINE_FILE.exists():
        pytest.skip(f"Missing baseline file: {BASELINE_FILE}")

    spec = importlib.util.spec_from_file_location("cinema_factory_premiere_xml", BASELINE_FILE)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)

    baseline_gen = module.PremiereXMLGenerator()
    baseline_xml = baseline_gen.generate_premiere_xml(
        video_path="/tmp/baseline_source.mp4",
        whisper_transcription={
            "segments": [
                {"start": 0.5, "end": 1.2, "text": "hello"},
                {"start": 2.0, "end": 2.9, "text": "world"},
            ]
        },
    )
    ours_xml = build_premiere_xml_from_transcript(
        source_path="/tmp/baseline_source.mp4",
        transcript_normalized_json={
            "duration_sec": 10.0,
            "segments": [
                {"start_sec": 0.5, "end_sec": 1.2, "text": "hello"},
                {"start_sec": 2.0, "end_sec": 2.9, "text": "world"},
            ],
        },
        sequence_name="Baseline_Compare",
        fps=30.0,
    )

    b = ET.fromstring(baseline_xml)
    o = ET.fromstring(ours_xml)

    # Shared must-have Premiere XML invariants
    assert b.tag == "xmeml"
    assert o.tag == "xmeml"
    assert b.attrib.get("version") == "5"
    assert o.attrib.get("version") == "5"
    assert b.find("./project") is not None
    assert o.find("./project") is not None
    assert b.find(".//sequence") is not None
    assert o.find(".//sequence") is not None
    assert b.find(".//clipitem") is not None
    assert o.find(".//clipitem") is not None

    # Baseline has clipitem markers; keep compatibility in our export
    assert b.find(".//clipitem/markers/marker") is not None
    assert o.find(".//clipitem/markers/marker") is not None
