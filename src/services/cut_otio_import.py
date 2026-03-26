"""
MARKER_BOTIO — OTIO Import Service.

Parses Premiere XML (XMEML v5), FCPXML (v1.x), OTIO JSON, and EDL files
into CUT project structures (timeline lanes + clips + markers).

No opentimelineio library dependency — uses stdlib XML + JSON parsers only.
This is intentional: VETKA CUT's OTIO export is a hand-rolled JSON subset,
and we support the same formats directly to avoid the heavy OTIO dependency.

Supported input adapters:
  - .otio / .otio.json  — VETKA OTIO JSON (Timeline.1 schema)
  - .xml                — Premiere XMEML v5 (<xmeml version="5">)
  - .fcpxml             — FCPXML v1.x (<fcpxml version="1.x">)
  - .edl                — CMX 3600 EDL (V/A event lines)

Output: CutImportResult — a structured dict ready for timeline store hydration.

@status: active
@phase: BOTIO
@task: tb_1774423967_1
@depends: cut_project_store (CutProjectStore)
"""
from __future__ import annotations

import json
import logging
import re
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET

logger = logging.getLogger("cut.otio_import")


# ---------------------------------------------------------------------------
# Data model — what we return to the caller / route layer
# ---------------------------------------------------------------------------


@dataclass
class ImportedClip:
    clip_id: str
    name: str
    source_path: str
    start_sec: float           # position on timeline
    duration_sec: float        # clip duration
    source_in_sec: float = 0.0 # in-point in source file
    lane_id: str = "V1"
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "clip_id": self.clip_id,
            "name": self.name,
            "source_path": self.source_path,
            "start_sec": self.start_sec,
            "end_sec": self.start_sec + self.duration_sec,
            "duration_sec": self.duration_sec,
            "source_in_sec": self.source_in_sec,
            "lane_id": self.lane_id,
            "metadata": self.metadata,
        }


@dataclass
class ImportedLane:
    lane_id: str
    kind: str = "video"        # "video" | "audio"
    name: str = ""
    clips: list[ImportedClip] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "lane_id": self.lane_id,
            "kind": self.kind,
            "name": self.name or self.lane_id,
            "clips": [c.to_dict() for c in self.clips],
        }


@dataclass
class ImportedMarker:
    marker_id: str
    time_sec: float
    start_sec: float
    end_sec: float
    kind: str = "comment"
    comment: str = ""
    media_path: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "marker_id": self.marker_id,
            "time_sec": self.time_sec,
            "start_sec": self.start_sec,
            "end_sec": self.end_sec,
            "kind": self.kind,
            "comment": self.comment,
            "media_path": self.media_path,
            "metadata": self.metadata,
        }


@dataclass
class CutImportResult:
    """Structured result from any import adapter.

    timeline_state: dict ready to be saved via CutProjectStore.save_timeline_state()
    markers: list of marker dicts ready for time_marker_bundle
    warnings: non-fatal issues encountered during parse
    source_format: detected input format
    """
    timeline_state: dict[str, Any]
    markers: list[dict[str, Any]]
    warnings: list[str]
    source_format: str
    project_name: str
    sequence_name: str
    fps: float
    duration_sec: float
    clip_count: int
    lane_count: int


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _new_id(prefix: str = "clip") -> str:
    return f"{prefix}_{uuid.uuid4().hex[:8]}"


def _frames_to_sec(frames: int | float, fps: float) -> float:
    return float(frames) / max(1.0, float(fps))


def _rational_to_sec(rational_str: str) -> float:
    """Parse FCPXML rational time strings like '120/30s' → 4.0 seconds."""
    s = str(rational_str or "").strip().rstrip("s")
    if "/" in s:
        parts = s.split("/", 1)
        try:
            return float(parts[0]) / max(1.0, float(parts[1]))
        except (ValueError, ZeroDivisionError):
            return 0.0
    try:
        return float(s)
    except ValueError:
        return 0.0


def _normalize_path(raw: str) -> str:
    """Strip file:// prefix and normalize path string."""
    p = str(raw or "").strip()
    if p.startswith("file://"):
        p = p[7:]
    return p


def _build_timeline_state(
    *,
    project_id: str,
    timeline_id: str,
    fps: float,
    lanes: list[ImportedLane],
) -> dict[str, Any]:
    """Build a cut_timeline_state_v1 dict from imported lanes."""
    from datetime import datetime, timezone
    return {
        "schema_version": "cut_timeline_state_v1",
        "project_id": project_id,
        "timeline_id": timeline_id,
        "revision": 1,
        "fps": fps,
        "lanes": [lane.to_dict() for lane in lanes],
        "selection": {"clip_ids": [], "marker_ids": []},
        "view": {"scroll_x": 0.0, "zoom": 1.0},
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }


# ---------------------------------------------------------------------------
# Adapter: VETKA OTIO JSON (.otio / .otio.json)
# ---------------------------------------------------------------------------


def _parse_otio_json(data: dict[str, Any], project_id: str) -> CutImportResult:
    """Parse VETKA hand-rolled OTIO JSON (Timeline.1 schema) into CUT structures."""
    warnings: list[str] = []

    schema = str(data.get("OTIO_SCHEMA") or "")
    if not schema.startswith("Timeline"):
        warnings.append(f"Root OTIO_SCHEMA is '{schema}', expected 'Timeline.*'. Trying anyway.")

    sequence_name = str(data.get("name") or "Imported_Timeline")
    metadata = data.get("metadata") or {}
    project_name = str(metadata.get("project_name") or sequence_name)

    tracks_block = data.get("tracks") or {}
    track_list = tracks_block.get("children") or []

    fps = 25.0
    lanes: list[ImportedLane] = []
    all_duration = 0.0

    for track_data in track_list:
        track_schema = str(track_data.get("OTIO_SCHEMA") or "")
        if not track_schema.startswith("Track"):
            warnings.append(f"Skipping non-Track child: {track_schema}")
            continue

        track_kind = str(track_data.get("kind") or "Video").lower()
        track_name = str(track_data.get("name") or "")
        lane_id = track_name or ("V1" if track_kind == "video" else "A1")
        lane = ImportedLane(lane_id=lane_id, kind=track_kind, name=track_name)

        children = track_data.get("children") or []
        for child in children:
            child_schema = str(child.get("OTIO_SCHEMA") or "")
            if not child_schema.startswith("Clip"):
                # Transitions / gaps — skip for now
                if child_schema.startswith("Transition"):
                    warnings.append(f"Transition '{child.get('name', '')}' skipped (not yet supported).")
                continue

            clip_name = str(child.get("name") or "clip")
            src_range = child.get("source_range") or {}
            duration_rt = src_range.get("duration") or {}
            start_rt = src_range.get("start_time") or {}

            clip_fps = float(duration_rt.get("rate") or start_rt.get("rate") or fps)
            fps = clip_fps  # propagate last seen fps

            dur_frames = float(duration_rt.get("value") or 0)
            src_in_frames = float(start_rt.get("value") or 0)
            dur_sec = _frames_to_sec(dur_frames, clip_fps)
            src_in_sec = _frames_to_sec(src_in_frames, clip_fps)

            child_meta = child.get("metadata") or {}
            vetka_meta = child_meta.get("vetka") or {}
            source_path = _normalize_path(str(vetka_meta.get("source_path") or ""))
            # timeline_start_sec is stored in vetka metadata on export
            start_sec = float(vetka_meta.get("timeline_start_sec") or 0.0)

            all_duration = max(all_duration, start_sec + dur_sec)

            clip = ImportedClip(
                clip_id=_new_id("clip"),
                name=clip_name,
                source_path=source_path,
                start_sec=start_sec,
                duration_sec=dur_sec,
                source_in_sec=src_in_sec,
                lane_id=lane_id,
                metadata=child_meta,
            )
            lane.clips.append(clip)

        lanes.append(lane)

    if not lanes:
        warnings.append("No tracks found in OTIO file. Creating empty timeline.")
        lanes = [ImportedLane(lane_id="V1", kind="video", name="V1")]

    timeline_id = f"import_{uuid.uuid4().hex[:6]}"
    timeline_state = _build_timeline_state(
        project_id=project_id,
        timeline_id=timeline_id,
        fps=fps,
        lanes=lanes,
    )

    clip_count = sum(len(lane.clips) for lane in lanes)
    return CutImportResult(
        timeline_state=timeline_state,
        markers=[],
        warnings=warnings,
        source_format="otio_json",
        project_name=project_name,
        sequence_name=sequence_name,
        fps=fps,
        duration_sec=all_duration,
        clip_count=clip_count,
        lane_count=len(lanes),
    )


# ---------------------------------------------------------------------------
# Adapter: Premiere XML (XMEML v5)
# ---------------------------------------------------------------------------


def _parse_premiere_xml(root: ET.Element, project_id: str) -> CutImportResult:
    """Parse Premiere XMEML v5 <xmeml> tree into CUT structures."""
    warnings: list[str] = []

    # Discover FPS from rate element
    fps = 25.0
    rate_el = root.find(".//rate")
    if rate_el is not None:
        tb = rate_el.findtext("timebase")
        if tb:
            try:
                fps = float(tb)
            except ValueError:
                pass
        ntsc = (rate_el.findtext("ntsc") or "").lower()
        if ntsc == "true":
            fps = round(fps * 1000.0 / 1001.0, 3)

    # Project and sequence metadata
    project_name = root.findtext(".//project/name") or root.findtext(".//project/n") or "Imported_Project"
    sequence_el = root.find(".//sequence")
    sequence_name = ""
    if sequence_el is not None:
        sequence_name = sequence_el.findtext("name") or sequence_el.findtext("n") or ""
    if not sequence_name:
        sequence_name = project_name

    # Build file-path index from <file id="..."> elements
    file_index: dict[str, str] = {}
    for file_el in root.iter("file"):
        fid = file_el.get("id") or ""
        pathurl = file_el.findtext("pathurl") or ""
        if fid and pathurl:
            file_index[fid] = _normalize_path(pathurl)

    # Parse video tracks
    lanes: list[ImportedLane] = []
    all_duration = 0.0
    markers: list[ImportedMarker] = []

    # Sequence-level markers
    for marker_el in (sequence_el or root).findall("markers/marker"):
        in_frames = int(marker_el.findtext("in") or 0)
        comment = marker_el.findtext("comment") or ""
        time_sec = _frames_to_sec(in_frames, fps)
        markers.append(ImportedMarker(
            marker_id=_new_id("mk"),
            time_sec=time_sec,
            start_sec=time_sec,
            end_sec=time_sec + 1.0,
            kind="comment",
            comment=comment,
        ))

    # Video tracks
    media_el = (sequence_el or root).find("media") or root.find(".//media")
    video_el = (media_el.find("video") if media_el is not None else None) or root.find(".//video")
    track_idx = 0
    for track_el in (video_el.findall("track") if video_el is not None else []):
        track_idx += 1
        lane_id = f"V{track_idx}"
        lane = ImportedLane(lane_id=lane_id, kind="video", name=lane_id)

        for clipitem_el in track_el.findall("clipitem"):
            name = clipitem_el.findtext("name") or clipitem_el.findtext("n") or "clip"
            start_f = int(clipitem_el.findtext("start") or 0)
            end_f = int(clipitem_el.findtext("end") or 0)
            in_f = int(clipitem_el.findtext("in") or 0)

            # Source file reference
            file_ref = clipitem_el.find("file")
            source_path = ""
            if file_ref is not None:
                ref_id = file_ref.get("id") or ""
                source_path = file_index.get(ref_id, "")
                if not source_path:
                    source_path = _normalize_path(file_ref.findtext("pathurl") or "")

            start_sec = _frames_to_sec(start_f, fps)
            end_sec = _frames_to_sec(end_f, fps)
            in_sec = _frames_to_sec(in_f, fps)
            dur_sec = max(0.0, end_sec - start_sec)
            all_duration = max(all_duration, end_sec)

            clip = ImportedClip(
                clip_id=_new_id("clip"),
                name=name,
                source_path=source_path,
                start_sec=start_sec,
                duration_sec=dur_sec,
                source_in_sec=in_sec,
                lane_id=lane_id,
            )
            lane.clips.append(clip)

            # Clip-level markers
            for mk_el in clipitem_el.findall("markers/marker"):
                mk_in_f = int(mk_el.findtext("in") or 0)
                mk_comment = mk_el.findtext("comment") or ""
                mk_time = start_sec + _frames_to_sec(mk_in_f, fps)
                markers.append(ImportedMarker(
                    marker_id=_new_id("mk"),
                    time_sec=mk_time,
                    start_sec=mk_time,
                    end_sec=mk_time + 1.0,
                    kind="comment",
                    comment=mk_comment,
                    media_path=source_path,
                ))

        if lane.clips:
            lanes.append(lane)

    # Audio tracks
    audio_el = (media_el.find("audio") if media_el is not None else None) or root.find(".//audio")
    atrack_idx = 0
    for track_el in (audio_el.findall("track") if audio_el is not None else []):
        atrack_idx += 1
        lane_id = f"A{atrack_idx}"
        lane = ImportedLane(lane_id=lane_id, kind="audio", name=lane_id)

        for clipitem_el in track_el.findall("clipitem"):
            name = clipitem_el.findtext("name") or clipitem_el.findtext("n") or "audio_clip"
            start_f = int(clipitem_el.findtext("start") or 0)
            end_f = int(clipitem_el.findtext("end") or 0)
            in_f = int(clipitem_el.findtext("in") or 0)

            file_ref = clipitem_el.find("file")
            source_path = ""
            if file_ref is not None:
                ref_id = file_ref.get("id") or ""
                source_path = file_index.get(ref_id, "")
                if not source_path:
                    source_path = _normalize_path(file_ref.findtext("pathurl") or "")

            start_sec = _frames_to_sec(start_f, fps)
            end_sec = _frames_to_sec(end_f, fps)
            in_sec = _frames_to_sec(in_f, fps)
            dur_sec = max(0.0, end_sec - start_sec)
            all_duration = max(all_duration, end_sec)

            clip = ImportedClip(
                clip_id=_new_id("clip"),
                name=name,
                source_path=source_path,
                start_sec=start_sec,
                duration_sec=dur_sec,
                source_in_sec=in_sec,
                lane_id=lane_id,
            )
            lane.clips.append(clip)

        if lane.clips:
            lanes.append(lane)

    if not lanes:
        warnings.append("No clips found in Premiere XML. Creating empty timeline.")
        lanes = [ImportedLane(lane_id="V1", kind="video", name="V1")]

    timeline_id = f"import_{uuid.uuid4().hex[:6]}"
    timeline_state = _build_timeline_state(
        project_id=project_id,
        timeline_id=timeline_id,
        fps=fps,
        lanes=lanes,
    )

    clip_count = sum(len(lane.clips) for lane in lanes)
    return CutImportResult(
        timeline_state=timeline_state,
        markers=[m.to_dict() for m in markers],
        warnings=warnings,
        source_format="premiere_xml",
        project_name=project_name,
        sequence_name=sequence_name,
        fps=fps,
        duration_sec=all_duration,
        clip_count=clip_count,
        lane_count=len(lanes),
    )


# ---------------------------------------------------------------------------
# Adapter: FCPXML (Final Cut Pro XML v1.x)
# ---------------------------------------------------------------------------


def _parse_fcpxml(root: ET.Element, project_id: str) -> CutImportResult:
    """Parse FCPXML v1.x <fcpxml> tree into CUT structures."""
    warnings: list[str] = []

    # Discover FPS from format element
    fps = 25.0
    format_el = root.find(".//resources/format")
    if format_el is not None:
        frame_dur = format_el.get("frameDuration") or ""
        if frame_dur:
            frame_sec = _rational_to_sec(frame_dur)
            if frame_sec > 0:
                fps = round(1.0 / frame_sec, 3)

    # Build asset index: id → src path
    asset_index: dict[str, str] = {}
    for asset_el in root.findall(".//resources/asset"):
        aid = asset_el.get("id") or ""
        src = _normalize_path(asset_el.get("src") or "")
        if aid and src:
            asset_index[aid] = src

    # Project and sequence metadata
    project_name = ""
    project_el = root.find(".//library/event/project")
    if project_el is not None:
        project_name = project_el.get("name") or ""
    if not project_name:
        project_name = "Imported_Project"

    event_el = root.find(".//library/event")
    event_name = (event_el.get("name") if event_el is not None else None) or ""
    sequence_name = event_name or project_name

    lanes: list[ImportedLane] = []
    markers: list[ImportedMarker] = []
    all_duration = 0.0

    sequence_el = root.find(".//sequence") or root.find(".//spine/..")
    spine_el = (sequence_el.find("spine") if sequence_el is not None else None) or root.find(".//spine")

    # Primary lane V1 from spine clips
    if spine_el is not None:
        lane = ImportedLane(lane_id="V1", kind="video", name="V1")
        for clip_el in spine_el:
            tag = clip_el.tag
            if tag not in ("asset-clip", "clip", "ref-clip", "mc-clip"):
                continue

            name = clip_el.get("name") or "clip"
            ref = clip_el.get("ref") or ""
            source_path = asset_index.get(ref, "")

            offset_str = clip_el.get("offset") or "0s"
            start_str = clip_el.get("start") or "0s"
            dur_str = clip_el.get("duration") or "0s"

            start_sec = _rational_to_sec(offset_str)
            src_in_sec = _rational_to_sec(start_str)
            dur_sec = _rational_to_sec(dur_str)
            all_duration = max(all_duration, start_sec + dur_sec)

            clip = ImportedClip(
                clip_id=_new_id("clip"),
                name=name,
                source_path=source_path,
                start_sec=start_sec,
                duration_sec=dur_sec,
                source_in_sec=src_in_sec,
                lane_id="V1",
            )
            lane.clips.append(clip)

            # Markers on clip
            for mk_el in clip_el.findall("marker"):
                mk_offset = _rational_to_sec(mk_el.get("start") or "0s")
                mk_time = start_sec + mk_offset
                mk_comment = mk_el.get("value") or mk_el.get("note") or ""
                markers.append(ImportedMarker(
                    marker_id=_new_id("mk"),
                    time_sec=mk_time,
                    start_sec=mk_time,
                    end_sec=mk_time + 1.0,
                    kind="comment",
                    comment=mk_comment,
                    media_path=source_path,
                ))

        if lane.clips:
            lanes.append(lane)

    # Secondary lanes (connected clips / audio roles)
    atrack_idx = 0
    for ref_el in (spine_el or root).iter("asset-clip"):
        lane_role = ref_el.get("lane") or ""
        if not lane_role:
            continue
        # Connected clips in FCPXML use lane attribute for secondary tracks
        atrack_idx += 1
        lane_id = f"A{atrack_idx}"
        warnings.append(f"Connected clip '{ref_el.get('name', '')}' lane={lane_role} mapped to {lane_id}.")

    if not lanes:
        warnings.append("No clips found in FCPXML. Creating empty timeline.")
        lanes = [ImportedLane(lane_id="V1", kind="video", name="V1")]

    timeline_id = f"import_{uuid.uuid4().hex[:6]}"
    timeline_state = _build_timeline_state(
        project_id=project_id,
        timeline_id=timeline_id,
        fps=fps,
        lanes=lanes,
    )

    clip_count = sum(len(lane.clips) for lane in lanes)
    return CutImportResult(
        timeline_state=timeline_state,
        markers=[m.to_dict() for m in markers],
        warnings=warnings,
        source_format="fcpxml",
        project_name=project_name,
        sequence_name=sequence_name,
        fps=fps,
        duration_sec=all_duration,
        clip_count=clip_count,
        lane_count=len(lanes),
    )


# ---------------------------------------------------------------------------
# Adapter: EDL (CMX 3600)
# ---------------------------------------------------------------------------

_EDL_EVENT_RE = re.compile(
    r"^(\d{3,})\s+(\S+)\s+(\S+)\s+(\S+)\s+"
    r"(\d{2}:\d{2}:\d{2}[;:]\d{2})\s+"
    r"(\d{2}:\d{2}:\d{2}[;:]\d{2})\s+"
    r"(\d{2}:\d{2}:\d{2}[;:]\d{2})\s+"
    r"(\d{2}:\d{2}:\d{2}[;:]\d{2})"
)
_EDL_FC_RE = re.compile(r"^FCM:\s*(.+)$", re.IGNORECASE)
_EDL_TITLE_RE = re.compile(r"^TITLE:\s*(.+)$", re.IGNORECASE)
_EDL_CLIP_NAME_RE = re.compile(r"^\*\s*FROM CLIP NAME:\s*(.+)$", re.IGNORECASE)


def _tc_to_sec(tc: str, fps: float) -> float:
    """Convert HH:MM:SS:FF or HH:MM:SS;FF timecode to seconds."""
    tc = tc.replace(";", ":").strip()
    parts = tc.split(":")
    if len(parts) != 4:
        return 0.0
    try:
        hh, mm, ss, ff = int(parts[0]), int(parts[1]), int(parts[2]), int(parts[3])
        return hh * 3600.0 + mm * 60.0 + ss + ff / max(1.0, fps)
    except ValueError:
        return 0.0


def _parse_edl(text: str, project_id: str) -> CutImportResult:
    """Parse CMX 3600 EDL text into CUT structures."""
    warnings: list[str] = []
    lines = text.splitlines()

    fps = 25.0
    sequence_name = "Imported_EDL"
    project_name = sequence_name

    lane = ImportedLane(lane_id="V1", kind="video", name="V1")
    all_duration = 0.0

    pending_clip_name: str | None = None

    for line in lines:
        line = line.rstrip()
        if not line:
            continue

        # Title
        m = _EDL_TITLE_RE.match(line)
        if m:
            sequence_name = m.group(1).strip()
            project_name = sequence_name
            continue

        # FCM — detect drop/non-drop
        m = _EDL_FC_RE.match(line)
        if m:
            if "30" in m.group(1):
                fps = 29.97 if "drop" in m.group(1).lower() else 30.0
            elif "25" in m.group(1):
                fps = 25.0
            elif "24" in m.group(1):
                fps = 24.0
            continue

        # Clip name comment
        m = _EDL_CLIP_NAME_RE.match(line)
        if m:
            pending_clip_name = m.group(1).strip()
            continue

        # Event line
        m = _EDL_EVENT_RE.match(line)
        if m:
            # groups: event reel track cut src_in src_out rec_in rec_out
            reel = m.group(2)
            track = m.group(3).upper()
            src_in_tc = m.group(5)
            src_out_tc = m.group(6)
            rec_in_tc = m.group(7)
            rec_out_tc = m.group(8)

            src_in_sec = _tc_to_sec(src_in_tc, fps)
            src_out_sec = _tc_to_sec(src_out_tc, fps)
            rec_in_sec = _tc_to_sec(rec_in_tc, fps)
            rec_out_sec = _tc_to_sec(rec_out_tc, fps)

            dur_sec = max(0.0, rec_out_sec - rec_in_sec)
            src_dur = max(0.0, src_out_sec - src_in_sec)
            if dur_sec == 0.0 and src_dur > 0.0:
                dur_sec = src_dur

            name = pending_clip_name or reel or "clip"
            pending_clip_name = None

            # Only primary video (V) track — audio skipped for now
            if track.startswith("V") or track == "AA" or track == "A":
                all_duration = max(all_duration, rec_out_sec)
                clip = ImportedClip(
                    clip_id=_new_id("clip"),
                    name=name,
                    source_path="",  # EDL doesn't embed full paths
                    start_sec=rec_in_sec,
                    duration_sec=dur_sec,
                    source_in_sec=src_in_sec,
                    lane_id="V1",
                    metadata={"edl_reel": reel},
                )
                lane.clips.append(clip)

    if lane.clips:
        lanes = [lane]
    else:
        warnings.append("No events found in EDL. Creating empty timeline.")
        lanes = [ImportedLane(lane_id="V1", kind="video", name="V1")]

    if not lane.clips and fps == 25.0:
        warnings.append("EDL parsed without valid event lines. FPS defaulted to 25.")

    if lane.clips:
        warnings.append(
            "EDL media paths are empty — EDL only stores reel names, not file paths. "
            "Use the media relink tool after import to resolve source files."
        )

    timeline_id = f"import_{uuid.uuid4().hex[:6]}"
    timeline_state = _build_timeline_state(
        project_id=project_id,
        timeline_id=timeline_id,
        fps=fps,
        lanes=lanes,
    )

    clip_count = sum(len(l.clips) for l in lanes)
    return CutImportResult(
        timeline_state=timeline_state,
        markers=[],
        warnings=warnings,
        source_format="edl",
        project_name=project_name,
        sequence_name=sequence_name,
        fps=fps,
        duration_sec=all_duration,
        clip_count=clip_count,
        lane_count=len(lanes),
    )


# ---------------------------------------------------------------------------
# Dispatcher: detect format and route to correct adapter
# ---------------------------------------------------------------------------


def _detect_format(file_path: str, content: bytes) -> str:
    """Detect file format from extension and content sniffing."""
    ext = Path(file_path).suffix.lower()
    if ext in (".json",):
        # Could be .otio.json or generic JSON
        try:
            obj = json.loads(content[:512])
            if isinstance(obj, dict) and "OTIO_SCHEMA" in obj:
                return "otio_json"
        except Exception:
            pass
        return "unknown"
    if ext == ".otio":
        return "otio_json"
    if ext == ".xml":
        head = content[:512].decode("utf-8", errors="replace")
        if "<xmeml" in head:
            return "premiere_xml"
        if "<fcpxml" in head:
            return "fcpxml"
        return "premiere_xml"  # default to Premiere for .xml
    if ext == ".fcpxml":
        return "fcpxml"
    if ext == ".edl":
        return "edl"
    # Sniff content
    head_text = content[:256].decode("utf-8", errors="replace")
    if "OTIO_SCHEMA" in head_text:
        return "otio_json"
    if "<xmeml" in head_text:
        return "premiere_xml"
    if "<fcpxml" in head_text:
        return "fcpxml"
    if "TITLE:" in head_text or re.search(r"^\d{3}\s+", head_text, re.MULTILINE):
        return "edl"
    return "unknown"


def parse_otio_file(
    file_path: str,
    content: bytes | None = None,
    project_id: str = "",
) -> CutImportResult:
    """
    Main entry point: parse any supported NLE timeline file into CUT structures.

    Args:
        file_path: Path to the file (used for extension detection and error messages).
        content: Raw file bytes. If None, the file is read from disk.
        project_id: CUT project ID to embed in timeline_state. Defaults to a generated UUID.

    Returns:
        CutImportResult with timeline_state, markers, warnings, and metadata.

    Raises:
        ValueError: If the file format is unrecognized or the file cannot be parsed.
        FileNotFoundError: If file_path is given without content and the file does not exist.
    """
    if not project_id:
        project_id = f"imported_{uuid.uuid4().hex[:8]}"

    if content is None:
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Import file not found: {file_path}")
        content = path.read_bytes()

    fmt = _detect_format(file_path, content)
    logger.info("cut_otio_import: detected format=%s for file=%s", fmt, file_path)

    if fmt == "otio_json":
        try:
            data = json.loads(content.decode("utf-8", errors="replace"))
        except json.JSONDecodeError as exc:
            raise ValueError(f"Failed to parse OTIO JSON: {exc}") from exc
        return _parse_otio_json(data, project_id)

    if fmt == "premiere_xml":
        try:
            root = ET.fromstring(content.decode("utf-8", errors="replace"))
        except ET.ParseError as exc:
            raise ValueError(f"Failed to parse Premiere XML: {exc}") from exc
        return _parse_premiere_xml(root, project_id)

    if fmt == "fcpxml":
        try:
            root = ET.fromstring(content.decode("utf-8", errors="replace"))
        except ET.ParseError as exc:
            raise ValueError(f"Failed to parse FCPXML: {exc}") from exc
        return _parse_fcpxml(root, project_id)

    if fmt == "edl":
        text = content.decode("utf-8", errors="replace")
        return _parse_edl(text, project_id)

    raise ValueError(
        f"Unrecognized file format for '{Path(file_path).name}'. "
        "Supported: .otio, .otio.json, .xml (Premiere XMEML), .fcpxml, .edl"
    )
