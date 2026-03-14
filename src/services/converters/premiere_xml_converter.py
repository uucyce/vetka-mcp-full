"""
Premiere XML converter (XMEML v5) for media timeline interchange.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional
from xml.dom import minidom
from xml.etree import ElementTree as ET


def _to_frames(sec: float, fps: float) -> int:
    return max(0, int(round(float(sec) * float(fps))))


def _safe_text(value: Any) -> str:
    return str(value or "").strip()


def build_premiere_xml(payload: Dict[str, Any]) -> str:
    project_name = _safe_text(payload.get("project_name")) or "VETKA_Project"
    sequence_name = _safe_text(payload.get("sequence_name")) or "VETKA_Sequence"
    source_path = str(payload.get("source_path") or "")
    fps = float(payload.get("fps", 30.0) or 30.0)
    duration_sec = float(payload.get("duration_sec", 0.0) or 0.0)
    duration_frames = _to_frames(duration_sec, fps)
    clips = list(payload.get("clips") or [])
    markers = list(payload.get("markers") or [])

    root = ET.Element("xmeml", {"version": "5"})
    project = ET.SubElement(root, "project")
    ET.SubElement(project, "n").text = project_name

    file_elem = ET.SubElement(project, "file", {"id": "file-1"})
    ET.SubElement(file_elem, "pathurl").text = f"file://{source_path}"
    ET.SubElement(file_elem, "name").text = Path(source_path).name if source_path else "source"

    sequence = ET.SubElement(project, "sequence")
    ET.SubElement(sequence, "n").text = sequence_name
    ET.SubElement(sequence, "duration").text = str(duration_frames)
    ET.SubElement(sequence, "rate")
    media = ET.SubElement(sequence, "media")
    video = ET.SubElement(media, "video")
    track = ET.SubElement(video, "track")

    if not clips:
        clips = [{"start_sec": 0.0, "end_sec": duration_sec, "name": "primary"}]

    clipitems: List[ET.Element] = []
    for idx, clip in enumerate(clips, start=1):
        start_sec = float(clip.get("start_sec", 0.0) or 0.0)
        end_sec = max(start_sec, float(clip.get("end_sec", start_sec) or start_sec))
        clipitem = ET.SubElement(track, "clipitem", {"id": f"clipitem-{idx}"})
        clipitems.append(clipitem)
        ET.SubElement(clipitem, "n").text = _safe_text(clip.get("name")) or f"clip_{idx}"
        ET.SubElement(clipitem, "start").text = str(_to_frames(start_sec, fps))
        ET.SubElement(clipitem, "end").text = str(_to_frames(end_sec, fps))
        ET.SubElement(clipitem, "in").text = "0"
        ET.SubElement(clipitem, "out").text = str(_to_frames(end_sec - start_sec, fps))
        ET.SubElement(clipitem, "duration").text = str(_to_frames(end_sec - start_sec, fps))
        clip_file = ET.SubElement(clipitem, "file", {"id": "file-1"})
        ET.SubElement(clip_file, "pathurl").text = f"file://{source_path}"

    if markers:
        # Keep sequence-level markers
        marker_box = ET.SubElement(sequence, "markers")
        for m in markers[:512]:
            marker = ET.SubElement(marker_box, "marker")
            time_sec = float(m.get("time_sec", 0.0) or 0.0)
            ET.SubElement(marker, "in").text = str(_to_frames(time_sec, fps))
            ET.SubElement(marker, "out").text = str(_to_frames(time_sec, fps))
            ET.SubElement(marker, "comment").text = _safe_text(m.get("comment"))
        # Baseline compatibility lane: duplicate speech markers under first clipitem
        if clipitems:
            clip_markers = ET.SubElement(clipitems[0], "markers")
            for m in markers[:512]:
                marker = ET.SubElement(clip_markers, "marker")
                time_sec = float(m.get("time_sec", 0.0) or 0.0)
                ET.SubElement(marker, "in").text = str(_to_frames(time_sec, fps))
                ET.SubElement(marker, "duration").text = str(max(1, int(round(fps))))
                ET.SubElement(marker, "comment").text = _safe_text(m.get("comment"))

    rough = ET.tostring(root, encoding="utf-8")
    return minidom.parseString(rough).toprettyxml(indent="  ")


def build_premiere_xml_from_transcript(
    *,
    source_path: str,
    transcript_normalized_json: Dict[str, Any],
    sequence_name: str = "VETKA_Sequence",
    fps: float = 30.0,
) -> str:
    duration_sec = float(transcript_normalized_json.get("duration_sec", 0.0) or 0.0)
    segments = list(transcript_normalized_json.get("segments") or [])

    clips: List[Dict[str, Any]] = []
    markers: List[Dict[str, Any]] = []
    for idx, seg in enumerate(segments[:1024], start=1):
        start = float(seg.get("start_sec", 0.0) or 0.0)
        end = max(start, float(seg.get("end_sec", start) or start))
        text = _safe_text(seg.get("text"))
        clips.append({"start_sec": start, "end_sec": end, "name": f"seg_{idx:04d}"})
        if text:
            markers.append({"time_sec": start, "comment": text[:220]})

    return build_premiere_xml(
        {
            "project_name": "VETKA_Premiere_Export",
            "sequence_name": sequence_name,
            "source_path": source_path,
            "fps": fps,
            "duration_sec": duration_sec,
            "clips": clips,
            "markers": markers,
        }
    )
