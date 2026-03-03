"""
FCPXML converter (Final Cut XML lane) for media timeline interchange.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List
from xml.dom import minidom
from xml.etree import ElementTree as ET


def _safe_text(value: Any) -> str:
    return str(value or "").strip()


def _to_fcpx_time(sec: float, fps: float) -> str:
    # FCPXML friendly rational seconds string
    scale = max(1, int(round(float(fps))))
    ticks = max(0, int(round(float(sec) * scale)))
    return f"{ticks}/{scale}s"


def build_fcpxml(payload: Dict[str, Any]) -> str:
    project_name = _safe_text(payload.get("project_name")) or "VETKA_Project"
    sequence_name = _safe_text(payload.get("sequence_name")) or "VETKA_Sequence"
    source_path = str(payload.get("source_path") or "")
    fps = float(payload.get("fps", 30.0) or 30.0)
    duration_sec = float(payload.get("duration_sec", 0.0) or 0.0)
    clips = list(payload.get("clips") or [])

    root = ET.Element("fcpxml", {"version": "1.10"})
    resources = ET.SubElement(root, "resources")
    ET.SubElement(resources, "format", {"id": "r1", "name": "FFVideoFormat", "frameDuration": _to_fcpx_time(1.0, fps)})
    ET.SubElement(
        resources,
        "asset",
        {
            "id": "r2",
            "name": Path(source_path).name if source_path else "source",
            "src": f"file://{source_path}",
            "duration": _to_fcpx_time(duration_sec, fps),
            "hasVideo": "1",
            "hasAudio": "1",
            "format": "r1",
        },
    )

    library = ET.SubElement(root, "library")
    event = ET.SubElement(library, "event", {"name": "VETKA_Event"})
    project = ET.SubElement(event, "project", {"name": project_name})
    sequence = ET.SubElement(
        project,
        "sequence",
        {
            "format": "r1",
            "duration": _to_fcpx_time(duration_sec, fps),
            "tcStart": "0s",
            "tcFormat": "NDF",
            "audioLayout": "stereo",
            "audioRate": "48k",
        },
    )
    spine = ET.SubElement(sequence, "spine")

    if not clips:
        clips = [{"start_sec": 0.0, "end_sec": duration_sec, "name": "primary"}]

    for idx, clip in enumerate(clips, start=1):
        start_sec = float(clip.get("start_sec", 0.0) or 0.0)
        end_sec = max(start_sec, float(clip.get("end_sec", start_sec) or start_sec))
        ET.SubElement(
            spine,
            "asset-clip",
            {
                "name": _safe_text(clip.get("name")) or f"seg_{idx:04d}",
                "ref": "r2",
                "offset": _to_fcpx_time(start_sec, fps),
                "start": _to_fcpx_time(start_sec, fps),
                "duration": _to_fcpx_time(end_sec - start_sec, fps),
            },
        )

    rough = ET.tostring(root, encoding="utf-8")
    return minidom.parseString(rough).toprettyxml(indent="  ")


def build_fcpxml_from_transcript(
    *,
    source_path: str,
    transcript_normalized_json: Dict[str, Any],
    sequence_name: str = "VETKA_Sequence",
    fps: float = 30.0,
) -> str:
    duration_sec = float(transcript_normalized_json.get("duration_sec", 0.0) or 0.0)
    segments = list(transcript_normalized_json.get("segments") or [])
    clips: List[Dict[str, Any]] = []
    for idx, seg in enumerate(segments[:1024], start=1):
        start = float(seg.get("start_sec", 0.0) or 0.0)
        end = max(start, float(seg.get("end_sec", start) or start))
        clips.append({"start_sec": start, "end_sec": end, "name": f"seg_{idx:04d}"})

    return build_fcpxml(
        {
            "project_name": "VETKA_FCPXML_Export",
            "sequence_name": sequence_name,
            "source_path": source_path,
            "fps": fps,
            "duration_sec": duration_sec,
            "clips": clips,
        }
    )
