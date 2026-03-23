"""
MARKER_B48 — Multicam Sync Engine (FCP7 Ch.46-47).

Core PluralEyes replacement: sync multiple camera angles by audio waveform,
timecode, or manual markers. Returns frame-accurate offsets for multicam clip.

Architecture:
  source_paths[] → extract audio/timecode → pairwise sync → compute offsets
  → MulticamClip { angles[], offsets[], reference }

Uses existing infrastructure:
  - sync_two_files_ffmpeg() for audio cross-correlation (two-pass: coarse→fine)
  - extract_pcm_mono_16bit() for PCM extraction
  - probe_file() for timecode/duration metadata

@status: active
@phase: B48
@task: tb_1774250711_7
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4


@dataclass
class MulticamAngle:
    """A single camera angle in a multicam clip."""
    angle_index: int
    source_path: str
    label: str = ""
    offset_sec: float = 0.0      # offset relative to reference (0 = reference)
    duration_sec: float = 0.0
    sync_confidence: float = 0.0  # 0-1 from cross-correlation
    is_reference: bool = False


@dataclass
class MulticamClip:
    """A multicam clip composed of synced camera angles."""
    multicam_id: str = ""
    angles: list[MulticamAngle] = field(default_factory=list)
    sync_method: str = "waveform"  # waveform | timecode | marker
    reference_index: int = 0
    total_duration_sec: float = 0.0
    created_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "multicam_id": self.multicam_id,
            "angles": [
                {
                    "angle_index": a.angle_index,
                    "source_path": a.source_path,
                    "label": a.label,
                    "offset_sec": round(a.offset_sec, 4),
                    "duration_sec": round(a.duration_sec, 4),
                    "sync_confidence": round(a.sync_confidence, 4),
                    "is_reference": a.is_reference,
                }
                for a in self.angles
            ],
            "sync_method": self.sync_method,
            "reference_index": self.reference_index,
            "total_duration_sec": round(self.total_duration_sec, 4),
            "created_at": self.created_at,
        }


# ---------------------------------------------------------------------------
# Timecode extraction
# ---------------------------------------------------------------------------


def _extract_timecode_from_file(source_path: str) -> str | None:
    """Extract embedded timecode from video file via ffprobe."""
    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        return None
    try:
        cmd = [
            ffprobe, "-v", "error",
            "-select_streams", "v:0",
            "-show_entries", "format_tags=timecode:stream_tags=timecode",
            "-of", "default=noprint_wrappers=1:nokey=1",
            source_path,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
        tc = result.stdout.strip()
        if tc and re.match(r"\d{2}:\d{2}:\d{2}[;:]\d{2}", tc):
            return tc
    except Exception:
        pass
    return None


def _timecode_to_seconds(tc: str, fps: float = 25.0) -> float:
    """Convert SMPTE timecode (HH:MM:SS:FF or HH:MM:SS;FF) to seconds."""
    parts = re.split(r"[:;]", tc)
    if len(parts) != 4:
        return 0.0
    hh, mm, ss, ff = int(parts[0]), int(parts[1]), int(parts[2]), int(parts[3])
    return hh * 3600 + mm * 60 + ss + ff / fps


def _probe_duration(source_path: str) -> float:
    """Get media duration in seconds via ffprobe."""
    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        return 0.0
    try:
        cmd = [
            ffprobe, "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            source_path,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
        return float(result.stdout.strip()) if result.stdout.strip() else 0.0
    except Exception:
        return 0.0


# ---------------------------------------------------------------------------
# Sync methods
# ---------------------------------------------------------------------------


def sync_by_waveform(
    source_paths: list[str],
    *,
    reference_index: int = 0,
    max_lag_sec: float = 30.0,
    max_duration_sec: float = 120.0,
) -> MulticamClip:
    """Sync multiple angles by audio waveform cross-correlation.

    Uses existing sync_two_files_ffmpeg() (two-pass: coarse at 2kHz → fine at 16kHz).
    Reference angle has offset=0, others are relative.

    Args:
        source_paths: List of media file paths (one per angle).
        reference_index: Which angle is the reference (default: first).
        max_lag_sec: Maximum offset to search (default: 30s).
        max_duration_sec: Max audio to analyze per file.

    Returns:
        MulticamClip with angles and offsets.
    """
    from src.services.cut_ffmpeg_audio_sync import sync_two_files_ffmpeg

    if not source_paths:
        return MulticamClip(multicam_id=str(uuid4()))

    reference_index = max(0, min(reference_index, len(source_paths) - 1))
    ref_path = source_paths[reference_index]

    angles: list[MulticamAngle] = []
    for i, sp in enumerate(source_paths):
        label = os.path.splitext(os.path.basename(sp))[0]
        duration = _probe_duration(sp)

        if i == reference_index:
            angles.append(MulticamAngle(
                angle_index=i, source_path=sp, label=label,
                offset_sec=0.0, duration_sec=duration,
                sync_confidence=1.0, is_reference=True,
            ))
            continue

        # Cross-correlate against reference
        sync_result = sync_two_files_ffmpeg(
            ref_path, sp,
            max_lag_sec=max_lag_sec,
            max_duration_sec=max_duration_sec,
        )

        angles.append(MulticamAngle(
            angle_index=i, source_path=sp, label=label,
            offset_sec=sync_result.detected_offset_sec,
            duration_sec=duration,
            sync_confidence=sync_result.confidence,
            is_reference=False,
        ))

    # Total duration = max(offset + duration) across all angles
    total = max((a.offset_sec + a.duration_sec) for a in angles) if angles else 0.0

    return MulticamClip(
        multicam_id=str(uuid4()),
        angles=angles,
        sync_method="waveform",
        reference_index=reference_index,
        total_duration_sec=total,
    )


def sync_by_timecode(
    source_paths: list[str],
    *,
    fps: float = 25.0,
) -> MulticamClip:
    """Sync multiple angles by embedded timecode.

    Extracts SMPTE timecode from each file, computes offsets relative to
    the earliest timecode (which becomes reference).

    Args:
        source_paths: List of media file paths.
        fps: Framerate for timecode→seconds conversion.

    Returns:
        MulticamClip with angles and timecode-based offsets.
    """
    if not source_paths:
        return MulticamClip(multicam_id=str(uuid4()))

    # Extract timecodes
    tc_data: list[tuple[int, str, str | None, float]] = []  # (index, path, tc, duration)
    for i, sp in enumerate(source_paths):
        tc = _extract_timecode_from_file(sp)
        duration = _probe_duration(sp)
        tc_data.append((i, sp, tc, duration))

    # Find earliest timecode as reference
    valid_tcs = [(i, sp, tc, dur, _timecode_to_seconds(tc, fps))
                 for i, sp, tc, dur in tc_data if tc is not None]

    if not valid_tcs:
        # No timecodes found — fall back to zero offsets
        angles = [
            MulticamAngle(
                angle_index=i, source_path=sp,
                label=os.path.splitext(os.path.basename(sp))[0],
                offset_sec=0.0, duration_sec=dur,
                sync_confidence=0.0, is_reference=(i == 0),
            )
            for i, sp, tc, dur in tc_data
        ]
        return MulticamClip(
            multicam_id=str(uuid4()), angles=angles,
            sync_method="timecode", reference_index=0,
            total_duration_sec=max((a.duration_sec for a in angles), default=0.0),
        )

    # Reference = earliest timecode
    valid_tcs.sort(key=lambda x: x[4])
    ref_tc_sec = valid_tcs[0][4]
    ref_index = valid_tcs[0][0]

    angles = []
    for i, sp, tc, dur in tc_data:
        label = os.path.splitext(os.path.basename(sp))[0]
        if tc is not None:
            tc_sec = _timecode_to_seconds(tc, fps)
            offset = tc_sec - ref_tc_sec
            confidence = 1.0
        else:
            offset = 0.0
            confidence = 0.0

        angles.append(MulticamAngle(
            angle_index=i, source_path=sp, label=label,
            offset_sec=round(offset, 4), duration_sec=dur,
            sync_confidence=confidence, is_reference=(i == ref_index),
        ))

    total = max((a.offset_sec + a.duration_sec) for a in angles) if angles else 0.0

    return MulticamClip(
        multicam_id=str(uuid4()), angles=angles,
        sync_method="timecode", reference_index=ref_index,
        total_duration_sec=total,
    )


def sync_by_markers(
    source_paths: list[str],
    marker_times: list[float],
) -> MulticamClip:
    """Sync multiple angles by manual marker positions.

    Each source has a marker at a known point in real-world time.
    Offsets = marker_time[reference] - marker_time[i].

    Args:
        source_paths: List of media file paths.
        marker_times: Corresponding marker time (seconds) in each source.
                      Must be same length as source_paths.

    Returns:
        MulticamClip with marker-based offsets.
    """
    if not source_paths or len(marker_times) != len(source_paths):
        return MulticamClip(multicam_id=str(uuid4()))

    # Reference = first source
    ref_marker = marker_times[0]

    angles = []
    for i, (sp, mt) in enumerate(zip(source_paths, marker_times)):
        label = os.path.splitext(os.path.basename(sp))[0]
        duration = _probe_duration(sp)
        offset = mt - ref_marker  # positive = this angle starts later
        angles.append(MulticamAngle(
            angle_index=i, source_path=sp, label=label,
            offset_sec=round(offset, 4), duration_sec=duration,
            sync_confidence=1.0, is_reference=(i == 0),
        ))

    total = max((a.offset_sec + a.duration_sec) for a in angles) if angles else 0.0

    return MulticamClip(
        multicam_id=str(uuid4()), angles=angles,
        sync_method="marker", reference_index=0,
        total_duration_sec=total,
    )


# ---------------------------------------------------------------------------
# Multicam switch — insert angle cut on timeline
# ---------------------------------------------------------------------------


def build_multicam_switch_clip(
    multicam: MulticamClip,
    angle_index: int,
    switch_time_sec: float,
    duration_sec: float,
) -> dict[str, Any]:
    """Build a timeline clip dict for a multicam angle switch.

    Args:
        multicam: The multicam clip with synced angles.
        angle_index: Which angle to switch to.
        switch_time_sec: Timeline time of the switch point.
        duration_sec: Duration of this angle segment.

    Returns:
        Timeline clip dict ready for insertion.
    """
    if angle_index < 0 or angle_index >= len(multicam.angles):
        raise ValueError(f"Invalid angle_index {angle_index}, multicam has {len(multicam.angles)} angles")

    angle = multicam.angles[angle_index]

    # source_in = switch_time on timeline - angle's offset (where in the source file)
    source_in = max(0.0, switch_time_sec - angle.offset_sec)

    return {
        "clip_id": f"mc_{multicam.multicam_id[:8]}_{angle_index}_{int(switch_time_sec * 1000)}",
        "source_path": angle.source_path,
        "start_sec": switch_time_sec,
        "duration_sec": duration_sec,
        "source_in": round(source_in, 4),
        "source_out": round(source_in + duration_sec, 4),
        "multicam_id": multicam.multicam_id,
        "angle_index": angle_index,
        "angle_label": angle.label,
    }
