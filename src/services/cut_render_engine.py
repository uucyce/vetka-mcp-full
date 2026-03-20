"""
MARKER_B5 — CUT Render Engine with filter_complex support.

Extracted from cut_routes.py _run_master_render_job. Adds:
- filter_complex graph builder for transitions (crossfade, dip-to-black)
- Speed changes via setpts/atempo
- Per-clip trim (source in/out)
- Composable filter chain: inputs → trim → speed → xfade → scale → encode

Architecture:
  RenderPlan → list[RenderClip] → FilterGraphBuilder → FFmpeg command
  The plan is built from timeline state, then compiled into a single
  FFmpeg invocation with -filter_complex.

@status: active
@phase: B5
@task: tb_1773981833_10
@depends: cut_codec_probe, cut_mcp_job_store, cut_project_store
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal


# ---------------------------------------------------------------------------
# Codec / Resolution maps (shared with cut_routes.py)
# ---------------------------------------------------------------------------

CODEC_MAP: dict[str, dict[str, str]] = {
    "prores_422": {"vcodec": "prores_ks", "profile": "2", "ext": ".mov", "pix_fmt": "yuv422p10le"},
    "prores_4444": {"vcodec": "prores_ks", "profile": "4", "ext": ".mov", "pix_fmt": "yuva444p10le"},
    "h264": {"vcodec": "libx264", "profile": "", "ext": ".mp4", "pix_fmt": "yuv420p"},
    "h265": {"vcodec": "libx265", "profile": "", "ext": ".mp4", "pix_fmt": "yuv420p"},
    "dnxhd": {"vcodec": "dnxhd", "profile": "", "ext": ".mxf", "pix_fmt": "yuv422p"},
}

RESOLUTION_MAP: dict[str, tuple[int, int] | None] = {
    "8k": (7680, 4320),
    "4k": (3840, 2160),
    "1080p": (1920, 1080),
    "720p": (1280, 720),
    "source": None,
}

# Social presets → override codec/resolution/bitrate
SOCIAL_PRESETS: dict[str, dict[str, Any]] = {
    "youtube": {"codec": "h264", "resolution": "1080p", "fps": 30, "quality": 85},
    "instagram_reels": {"codec": "h264", "resolution": "1080p", "fps": 30, "quality": 80, "aspect": "9:16"},
    "tiktok": {"codec": "h264", "resolution": "1080p", "fps": 30, "quality": 80, "aspect": "9:16"},
    "telegram": {"codec": "h264", "resolution": "720p", "fps": 30, "quality": 70},
}


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------

@dataclass
class RenderClip:
    """A single clip in the render timeline."""
    source_path: str
    start_sec: float = 0.0          # position on timeline
    duration_sec: float = 0.0       # duration on timeline (after speed)
    source_in: float = 0.0          # trim: source start
    source_out: float = 0.0         # trim: source end (0 = full)
    speed: float = 1.0              # playback speed (0.25-4.0)
    lane_id: str = ""
    clip_id: str = ""


@dataclass
class Transition:
    """Transition between two adjacent clips."""
    type: Literal["crossfade", "dip_to_black", "wipe", "dissolve"] = "crossfade"
    duration_sec: float = 1.0       # overlap duration
    between: tuple[int, int] = (0, 1)  # indices into clip list


@dataclass
class RenderPlan:
    """Complete render specification built from timeline state."""
    clips: list[RenderClip] = field(default_factory=list)
    transitions: list[Transition] = field(default_factory=list)
    codec: str = "h264"
    resolution: str = "1080p"
    width: int = 1920
    height: int = 1080
    fps: int = 25
    quality: int = 80
    range_in: float | None = None
    range_out: float | None = None
    audio_stems: bool = False
    output_path: str = ""
    preset: str = ""                # social preset name


# ---------------------------------------------------------------------------
# Timeline → RenderPlan
# ---------------------------------------------------------------------------

def build_render_plan(
    timeline: dict[str, Any],
    *,
    codec: str = "h264",
    resolution: str = "1080p",
    fps: int = 25,
    quality: int = 80,
    range_in: float | None = None,
    range_out: float | None = None,
    audio_stems: bool = False,
    output_dir: str = "",
    project_id: str = "project",
    timeline_id: str = "main",
    preset: str = "",
) -> RenderPlan:
    """Build a RenderPlan from timeline state dict."""
    # Apply social preset overrides
    if preset and preset in SOCIAL_PRESETS:
        sp = SOCIAL_PRESETS[preset]
        codec = sp.get("codec", codec)
        resolution = sp.get("resolution", resolution)
        fps = sp.get("fps", fps)
        quality = sp.get("quality", quality)

    codec_cfg = CODEC_MAP.get(codec, CODEC_MAP["h264"])
    ext = codec_cfg["ext"]

    res = RESOLUTION_MAP.get(resolution)
    width, height = res if res else (1920, 1080)

    if not output_dir:
        output_dir = "/tmp/cut_renders"
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, f"{project_id}_{timeline_id}_master{ext}")

    # Collect video clips from lanes
    clips: list[RenderClip] = []
    lanes = timeline.get("lanes", [])
    for lane in lanes:
        lt = lane.get("lane_type", "")
        if not (lt.startswith("video") or lt.startswith("take_alt")):
            continue
        for clip in lane.get("clips", []):
            sp = clip.get("source_path", "")
            if not sp or not os.path.isfile(sp):
                continue
            clips.append(RenderClip(
                source_path=sp,
                start_sec=float(clip.get("start_sec", 0)),
                duration_sec=float(clip.get("duration_sec", 0)),
                source_in=float(clip.get("source_in", 0)),
                source_out=float(clip.get("source_out", 0)),
                speed=float(clip.get("speed", 1.0)),
                lane_id=lane.get("lane_id", ""),
                clip_id=clip.get("clip_id", ""),
            ))

    clips.sort(key=lambda c: c.start_sec)

    # Detect transitions from clip overlaps
    transitions: list[Transition] = []
    for i in range(len(clips) - 1):
        a, b = clips[i], clips[i + 1]
        a_end = a.start_sec + a.duration_sec
        overlap = a_end - b.start_sec
        if overlap > 0.01:  # >10ms overlap = transition
            transitions.append(Transition(
                type="crossfade",
                duration_sec=min(overlap, 5.0),  # cap at 5s
                between=(i, i + 1),
            ))

    return RenderPlan(
        clips=clips,
        transitions=transitions,
        codec=codec,
        resolution=resolution,
        width=width,
        height=height,
        fps=fps,
        quality=quality,
        range_in=range_in,
        range_out=range_out,
        audio_stems=audio_stems,
        output_path=output_path,
        preset=preset,
    )


# ---------------------------------------------------------------------------
# filter_complex graph builder
# ---------------------------------------------------------------------------

class FilterGraphBuilder:
    """
    Builds an FFmpeg -filter_complex string from a RenderPlan.

    Strategy:
    - Each clip input [0:v], [1:v], ... gets trim + setpts + scale
    - Adjacent clips with transitions get xfade between them
    - Clips without transitions get concat
    - Audio mirrors video: acrossfade for transitions, concat otherwise

    For N clips with M transitions, the graph chains xfade filters:
      [v0][v1]xfade=transition=fade:duration=D:offset=O[vx01]
      [vx01][v2]xfade=...[vx012]
      ...
    """

    def __init__(self, plan: RenderPlan):
        self.plan = plan
        self._video_filters: list[str] = []
        self._audio_filters: list[str] = []
        self._inputs: list[str] = []
        self._transition_map: dict[int, Transition] = {}

        for t in plan.transitions:
            self._transition_map[t.between[0]] = t

    def build(self) -> tuple[list[str], str, str]:
        """
        Returns:
            (input_args, filter_complex_string, output_video_label, output_audio_label)
            → actually returns (input_args, filter_complex_string, final_video_pad, final_audio_pad)
              packed as (input_args, filter_graph)
              where filter_graph includes [outv] and [outa] final labels.

        Returns:
            Tuple of (ffmpeg_input_args, filter_complex_string).
        """
        clips = self.plan.clips
        if not clips:
            return [], ""

        input_args: list[str] = []
        filters: list[str] = []

        # Build inputs and per-clip filters
        for i, clip in enumerate(clips):
            input_args += ["-i", clip.source_path]
            vfilter = self._clip_video_filter(i, clip)
            afilter = self._clip_audio_filter(i, clip)
            filters.append(vfilter)
            filters.append(afilter)

        # Chain video with xfade transitions
        v_chain = self._build_xfade_chain(clips, is_audio=False)
        a_chain = self._build_xfade_chain(clips, is_audio=True)
        filters.extend(v_chain)
        filters.extend(a_chain)

        # Scale final output
        n = len(clips)
        final_v = f"[vout{n - 1}]" if self._transition_map else f"[v{n - 1}]" if n == 1 else f"[vout{n - 1}]"
        final_a = f"[aout{n - 1}]" if self._transition_map else f"[a{n - 1}]" if n == 1 else f"[aout{n - 1}]"

        w, h = self.plan.width, self.plan.height
        filters.append(
            f"{final_v}scale={w}:{h}:force_original_aspect_ratio=decrease,"
            f"pad={w}:{h}:-1:-1:color=black,fps={self.plan.fps}[outv]"
        )
        filters.append(f"{final_a}anull[outa]")

        filter_str = ";\n".join(f for f in filters if f)
        return input_args, filter_str

    def _clip_video_filter(self, idx: int, clip: RenderClip) -> str:
        """Per-clip video: trim + speed + label."""
        parts: list[str] = []

        # Trim
        if clip.source_in > 0 or clip.source_out > 0:
            trim = f"trim=start={clip.source_in}"
            if clip.source_out > clip.source_in:
                trim += f":end={clip.source_out}"
            parts.append(trim)
            parts.append("setpts=PTS-STARTPTS")

        # Speed
        if clip.speed != 1.0 and clip.speed > 0:
            pts_factor = 1.0 / clip.speed
            parts.append(f"setpts={pts_factor:.4f}*PTS")

        if not parts:
            parts.append("null")

        return f"[{idx}:v]{','.join(parts)}[v{idx}]"

    def _clip_audio_filter(self, idx: int, clip: RenderClip) -> str:
        """Per-clip audio: atrim + speed."""
        parts: list[str] = []

        if clip.source_in > 0 or clip.source_out > 0:
            trim = f"atrim=start={clip.source_in}"
            if clip.source_out > clip.source_in:
                trim += f":end={clip.source_out}"
            parts.append(trim)
            parts.append("asetpts=PTS-STARTPTS")

        if clip.speed != 1.0 and clip.speed > 0:
            # atempo only supports 0.5-2.0, chain for wider range
            speed = clip.speed
            tempo_chain = _build_atempo_chain(speed)
            parts.extend(tempo_chain)

        if not parts:
            parts.append("anull")

        return f"[{idx}:a]{','.join(parts)}[a{idx}]"

    def _build_xfade_chain(self, clips: list[RenderClip], *, is_audio: bool) -> list[str]:
        """Chain clips with xfade/acrossfade or concat."""
        n = len(clips)
        if n < 2:
            return []

        filters: list[str] = []
        prefix = "a" if is_audio else "v"
        out_prefix = "a" if is_audio else "v"

        # Track current accumulated label
        current = f"[{prefix}0]"
        running_offset = clips[0].duration_sec

        for i in range(1, n):
            next_label = f"[{prefix}{i}]"
            out_label = f"[{out_prefix}out{i}]"

            t = self._transition_map.get(i - 1)

            if t and not is_audio:
                # Video xfade
                xfade_type = _map_transition_type(t.type)
                offset = max(0, running_offset - t.duration_sec)
                filters.append(
                    f"{current}{next_label}xfade=transition={xfade_type}"
                    f":duration={t.duration_sec:.3f}:offset={offset:.3f}{out_label}"
                )
                running_offset = offset + clips[i].duration_sec

            elif t and is_audio:
                # Audio crossfade
                filters.append(
                    f"{current}{next_label}acrossfade=d={t.duration_sec:.3f}"
                    f":c1=tri:c2=tri{out_label}"
                )
                running_offset = running_offset - t.duration_sec + clips[i].duration_sec

            else:
                # No transition — concat
                filters.append(
                    f"{current}{next_label}concat=n=2:v={'1' if not is_audio else '0'}"
                    f":a={'0' if not is_audio else '1'}{out_label}"
                )
                running_offset += clips[i].duration_sec

            current = out_label

        return filters


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _map_transition_type(t: str) -> str:
    """Map our transition type to FFmpeg xfade transition name."""
    mapping = {
        "crossfade": "fade",
        "dissolve": "dissolve",
        "dip_to_black": "fadeblack",
        "wipe": "wipeleft",
    }
    return mapping.get(t, "fade")


def _build_atempo_chain(speed: float) -> list[str]:
    """
    Build atempo filter chain for arbitrary speed.
    atempo supports 0.5-100.0 per instance; chain for values outside range.
    """
    if speed <= 0:
        return ["anull"]

    parts: list[str] = []
    remaining = speed

    # Handle speeds < 0.5 by chaining
    while remaining < 0.5:
        parts.append("atempo=0.5")
        remaining /= 0.5

    # Handle speeds > 100.0 by chaining
    while remaining > 100.0:
        parts.append("atempo=100.0")
        remaining /= 100.0

    parts.append(f"atempo={remaining:.4f}")
    return parts


# ---------------------------------------------------------------------------
# FFmpeg command builder
# ---------------------------------------------------------------------------

def build_ffmpeg_command(
    plan: RenderPlan,
    ffmpeg_path: str = "ffmpeg",
) -> list[str]:
    """
    Build complete FFmpeg command from RenderPlan.

    For simple timelines (no transitions, no speed changes), uses concat demuxer.
    For complex timelines, uses -filter_complex.
    """
    has_transitions = bool(plan.transitions)
    has_speed_changes = any(c.speed != 1.0 for c in plan.clips)
    has_trims = any(c.source_in > 0 or c.source_out > 0 for c in plan.clips)
    use_filter_complex = has_transitions or has_speed_changes or has_trims

    if use_filter_complex:
        return _build_filter_complex_cmd(plan, ffmpeg_path)
    else:
        return _build_concat_cmd(plan, ffmpeg_path)


def _build_filter_complex_cmd(plan: RenderPlan, ffmpeg_path: str) -> list[str]:
    """Build FFmpeg command with -filter_complex."""
    builder = FilterGraphBuilder(plan)
    input_args, filter_graph = builder.build()

    codec_cfg = CODEC_MAP.get(plan.codec, CODEC_MAP["h264"])
    cmd = [ffmpeg_path, "-y"]
    cmd += input_args
    cmd += ["-filter_complex", filter_graph]
    cmd += ["-map", "[outv]", "-map", "[outa]"]

    # Video codec
    cmd += ["-c:v", codec_cfg["vcodec"]]
    if codec_cfg["profile"]:
        cmd += ["-profile:v", codec_cfg["profile"]]
    cmd += ["-pix_fmt", codec_cfg["pix_fmt"]]

    # Quality
    if plan.codec in ("h264", "h265"):
        crf = max(0, min(51, int(51 - (plan.quality / 100) * 51)))
        cmd += ["-crf", str(crf)]

    # Audio
    cmd += ["-c:a", "aac", "-b:a", "320k"]

    # Range (applied as output trim)
    if plan.range_in is not None and plan.range_out is not None and plan.range_out > plan.range_in:
        cmd += ["-ss", str(plan.range_in), "-t", str(plan.range_out - plan.range_in)]

    cmd += [plan.output_path]
    return cmd


def _build_concat_cmd(plan: RenderPlan, ffmpeg_path: str) -> list[str]:
    """Build FFmpeg command with concat demuxer (simple case, no filters)."""
    codec_cfg = CODEC_MAP.get(plan.codec, CODEC_MAP["h264"])

    # Write concat file
    concat_dir = os.path.dirname(plan.output_path)
    concat_path = os.path.join(concat_dir, f"_concat_{os.getpid()}.txt")
    with open(concat_path, "w") as f:
        for clip in plan.clips:
            escaped = clip.source_path.replace("'", "'\\''")
            f.write(f"file '{escaped}'\n")
            if clip.duration_sec:
                f.write(f"duration {clip.duration_sec}\n")

    cmd = [ffmpeg_path, "-y", "-f", "concat", "-safe", "0", "-i", concat_path]
    cmd += ["-c:v", codec_cfg["vcodec"]]
    if codec_cfg["profile"]:
        cmd += ["-profile:v", codec_cfg["profile"]]
    cmd += ["-pix_fmt", codec_cfg["pix_fmt"]]

    # Resolution
    res = RESOLUTION_MAP.get(plan.resolution)
    if res:
        cmd += ["-vf", f"scale={res[0]}:{res[1]}:force_original_aspect_ratio=decrease,pad={res[0]}:{res[1]}:-1:-1:color=black"]

    # Quality
    if plan.codec in ("h264", "h265"):
        crf = max(0, min(51, int(51 - (plan.quality / 100) * 51)))
        cmd += ["-crf", str(crf)]

    # Range
    if plan.range_in is not None and plan.range_out is not None and plan.range_out > plan.range_in:
        cmd += ["-ss", str(plan.range_in), "-t", str(plan.range_out - plan.range_in)]

    cmd += ["-r", str(plan.fps)]
    cmd += ["-c:a", "aac", "-b:a", "320k"]
    cmd += [plan.output_path]

    # Store concat path for cleanup
    plan._concat_path = concat_path  # type: ignore[attr-defined]
    return cmd


# ---------------------------------------------------------------------------
# Audio stems export
# ---------------------------------------------------------------------------

def export_audio_stems(
    timeline: dict[str, Any],
    output_dir: str,
    ffmpeg_path: str = "ffmpeg",
    *,
    range_in: float | None = None,
    range_out: float | None = None,
) -> list[str]:
    """Export per-track WAV stems from timeline audio lanes."""
    os.makedirs(output_dir, exist_ok=True)
    stem_paths: list[str] = []

    for lane in timeline.get("lanes", []):
        if not lane.get("lane_type", "").startswith("audio"):
            continue
        lane_id = lane.get("lane_id", "unknown")
        for clip in lane.get("clips", []):
            sp = clip.get("source_path", "")
            if not sp or not os.path.isfile(sp):
                continue
            stem_name = f"{lane_id}_{os.path.basename(sp).rsplit('.', 1)[0]}.wav"
            stem_path = os.path.join(output_dir, stem_name)
            cmd = [ffmpeg_path, "-y", "-i", sp, "-vn", "-c:a", "pcm_s24le", "-ar", "48000"]
            if range_in is not None and range_out is not None:
                cmd += ["-ss", str(range_in), "-t", str(range_out - range_in)]
            cmd += [stem_path]
            try:
                subprocess.run(cmd, capture_output=True, timeout=120)
                if os.path.exists(stem_path):
                    stem_paths.append(stem_path)
            except Exception:
                pass  # best-effort stems

    return stem_paths


# ---------------------------------------------------------------------------
# High-level render runner (for job system integration)
# ---------------------------------------------------------------------------

def render_timeline(
    timeline: dict[str, Any],
    *,
    codec: str = "h264",
    resolution: str = "1080p",
    fps: int = 25,
    quality: int = 80,
    range_in: float | None = None,
    range_out: float | None = None,
    audio_stems: bool = False,
    output_dir: str = "",
    project_id: str = "project",
    timeline_id: str = "main",
    preset: str = "",
    ffmpeg_path: str | None = None,
    timeout: int = 600,
    on_progress: Any = None,
) -> dict[str, Any]:
    """
    Render a timeline to a video file.

    Args:
        timeline: Timeline state dict with lanes/clips.
        on_progress: Optional callback(progress: float, message: str).
        Other args: render settings.

    Returns:
        Dict with output_path, file_size_bytes, stem_paths, codec, resolution.

    Raises:
        RuntimeError: If ffmpeg not found or render fails.
    """
    if ffmpeg_path is None:
        ffmpeg_path = shutil.which("ffmpeg")
    if not ffmpeg_path:
        raise RuntimeError("FFmpeg not found on system")

    def _progress(p: float, msg: str = "") -> None:
        if on_progress:
            on_progress(p, msg)

    _progress(0.05, "Building render plan")

    plan = build_render_plan(
        timeline,
        codec=codec,
        resolution=resolution,
        fps=fps,
        quality=quality,
        range_in=range_in,
        range_out=range_out,
        audio_stems=audio_stems,
        output_dir=output_dir,
        project_id=project_id,
        timeline_id=timeline_id,
        preset=preset,
    )

    if not plan.clips:
        raise RuntimeError("No video clips found in timeline")

    _progress(0.1, f"Rendering {len(plan.clips)} clips, {len(plan.transitions)} transitions")

    cmd = build_ffmpeg_command(plan, ffmpeg_path)

    _progress(0.3, "Running FFmpeg")

    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        raise RuntimeError(f"FFmpeg timed out after {timeout}s")

    # Cleanup concat file if used
    concat_path = getattr(plan, "_concat_path", None)
    if concat_path:
        try:
            os.remove(concat_path)
        except OSError:
            pass

    if proc.returncode != 0:
        stderr = (proc.stderr or "")[-500:]
        raise RuntimeError(f"FFmpeg failed (exit {proc.returncode}): {stderr}")

    result: dict[str, Any] = {
        "output_path": plan.output_path,
        "codec": plan.codec,
        "resolution": plan.resolution,
        "file_size_bytes": os.path.getsize(plan.output_path) if os.path.exists(plan.output_path) else 0,
        "clips_count": len(plan.clips),
        "transitions_count": len(plan.transitions),
        "used_filter_complex": bool(plan.transitions) or any(c.speed != 1.0 for c in plan.clips),
        "stem_paths": [],
        "stem_count": 0,
    }

    # Audio stems
    if audio_stems:
        _progress(0.85, "Exporting audio stems")
        stems_dir = os.path.join(os.path.dirname(plan.output_path), "stems")
        stem_paths = export_audio_stems(
            timeline, stems_dir, ffmpeg_path,
            range_in=range_in, range_out=range_out,
        )
        result["stem_paths"] = stem_paths
        result["stem_count"] = len(stem_paths)

    _progress(1.0, "Render complete")
    return result
