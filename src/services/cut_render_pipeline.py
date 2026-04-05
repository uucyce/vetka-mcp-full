"""
MARKER_B5 — CUT Render Pipeline (split from cut_render_engine.py).

Contains the render pipeline code: data types, plan builder, filter graph,
FFmpeg command builders, audio stem export, thumbnail generation, and the
high-level render_timeline() runner.

Codec/format definitions live in the split modules:
  - cut_codecs.py   — CODEC_MAP, _LOG_DECODE_FILTERS, compile_log_decode_filter
  - cut_formats.py  — RESOLUTION_MAP, EXPORT_PRESETS, SOCIAL_PRESETS

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
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

from src.services.cut_codecs import CODEC_MAP, _LOG_DECODE_FILTERS, compile_log_decode_filter, _compile_log_decode_filter
from src.services.cut_formats import RESOLUTION_MAP, EXPORT_PRESETS, SOCIAL_PRESETS


# ---------------------------------------------------------------------------
# MARKER_B2.1: Render cancellation exception
# ---------------------------------------------------------------------------

class RenderCancelled(RuntimeError):
    """Raised when render is cancelled by user."""
    pass


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
    # MARKER_B9: Per-clip effects
    video_effects: list[Any] = field(default_factory=list)  # list[EffectParam]
    audio_effects: list[Any] = field(default_factory=list)  # list[EffectParam]
    # MARKER_B11: Speed control extensions
    reverse: bool = False           # reverse playback
    frame_blend: bool = False       # smooth slow-mo via minterpolate
    maintain_pitch: bool = True     # preserve audio pitch during speed change
    # MARKER_B16: Color pipeline for render
    log_profile: str = ""           # camera log profile: "V-Log", "S-Log3", "LogC3", etc.
    lut_path: str = ""              # path to .cube LUT file
    # MARKER_B44: Per-clip keyframes for animated parameters
    keyframes: dict[str, list[dict]] = field(default_factory=dict)  # property → [{time_sec, value, easing}]
    # MARKER_B53: Motion controls (position/scale/rotation/opacity/crop)
    motion: dict[str, Any] = field(default_factory=dict)  # {x, y, scaleX, scaleY, rotation, opacity, cropL/R/T/B}


@dataclass
class Transition:
    """Transition between two adjacent clips."""
    type: Literal["crossfade", "dip_to_black", "wipe", "dissolve"] = "crossfade"
    duration_sec: float = 1.0       # overlap duration
    between: tuple[int, int] = (0, 1)  # indices into clip list
    # MARKER_B14: Audio crossfade curve type (FCP7 Ch.47)
    audio_curve: Literal["equal_power", "linear"] = "equal_power"
    # equal_power = +3dB at midpoint (default, sounds smooth)
    # linear = 0dB at midpoint (straight fade, sounds dip)


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
    # MARKER_B6.2: Audio codec selection
    audio_codec: str = "aac"        # aac, pcm_s24le, libmp3lame, flac
    # MARKER_B6.3: Bitrate mode
    bitrate_mode: str = "crf"       # crf, cbr, vbr
    target_bitrate: str = ""        # e.g. "12M", "8M", "50M" (for cbr/vbr)
    max_bitrate: str = ""           # e.g. "15M" (for vbr only)


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
    audio_codec: str = "aac",
    bitrate_mode: str = "crf",
    target_bitrate: str = "",
    max_bitrate: str = "",
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
            # MARKER_B9: Extract effects from clip metadata
            effects_data = clip.get("effects") or {}
            clips.append(RenderClip(
                source_path=sp,
                start_sec=float(clip.get("start_sec", 0)),
                duration_sec=float(clip.get("duration_sec", 0)),
                source_in=float(clip.get("source_in", 0)),
                source_out=float(clip.get("source_out", 0)),
                speed=float(clip.get("speed", 1.0)),
                lane_id=lane.get("lane_id", ""),
                clip_id=clip.get("clip_id", ""),
                video_effects=effects_data.get("video_effects", []),
                audio_effects=effects_data.get("audio_effects", []),
                # MARKER_B11: Speed extensions
                reverse=bool(clip.get("reverse", False)),
                frame_blend=bool(clip.get("frame_blend", False)),
                maintain_pitch=bool(clip.get("maintain_pitch", True)),
                # MARKER_B16: Color pipeline
                log_profile=str(clip.get("log_profile") or ""),
                lut_path=str(clip.get("lut_path") or ""),
                # MARKER_B44: Keyframes for animated parameters
                keyframes=dict(clip.get("keyframes") or {}),
                # MARKER_B53: Motion controls
                motion=dict(clip.get("motion") or {}),
            ))

    clips.sort(key=lambda c: c.start_sec)

    # MARKER_B10: Detect transitions from clip metadata or overlaps
    # Collect raw timeline clips to read transition metadata
    _raw_clips_sorted: list[dict] = []
    for lane in lanes:
        lt = lane.get("lane_type", "")
        if not (lt.startswith("video") or lt.startswith("take_alt")):
            continue
        for clip in lane.get("clips", []):
            sp = clip.get("source_path", "")
            if sp and os.path.isfile(sp):
                _raw_clips_sorted.append(clip)
    _raw_clips_sorted.sort(key=lambda c: c.get("start_sec", 0))

    transitions: list[Transition] = []
    for i in range(len(clips) - 1):
        a, b = clips[i], clips[i + 1]
        a_end = a.start_sec + a.duration_sec
        overlap = a_end - b.start_sec

        # Explicit transition metadata (from TransitionsPanel UI) takes priority
        raw_b = _raw_clips_sorted[i + 1] if i + 1 < len(_raw_clips_sorted) else {}
        tr_meta = raw_b.get("transition")
        if tr_meta and isinstance(tr_meta, dict):
            transitions.append(Transition(
                type=tr_meta.get("type", "crossfade"),
                duration_sec=float(tr_meta.get("duration_sec", 1.0)),
                between=(i, i + 1),
                # MARKER_B14: Audio crossfade curve from metadata
                audio_curve=tr_meta.get("audio_curve", "equal_power"),
            ))
        elif overlap > 0.01:  # >10ms overlap = auto crossfade
            transitions.append(Transition(
                type="crossfade",
                duration_sec=min(overlap, 5.0),
                between=(i, i + 1),
                audio_curve="equal_power",  # MARKER_B14: default +3dB
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
        audio_codec=audio_codec,
        bitrate_mode=bitrate_mode,
        target_bitrate=target_bitrate,
        max_bitrate=max_bitrate,
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

    @staticmethod
    def _has_animated_keyframes_static(clip: RenderClip) -> bool:
        """Check if clip has keyframes with 2+ points on sendcmd-animatable params."""
        ANIMATABLE = {"brightness.value", "contrast.value", "saturation.value",
                      "gamma.value", "blur.sigma", "hue.degrees"}
        for key, kfs in clip.keyframes.items():
            if key in ANIMATABLE and len(kfs) >= 2:
                return True
        return False

    def _clip_video_filter(self, idx: int, clip: RenderClip) -> str:
        """Per-clip video: trim + effects + speed + reverse + frame_blend + label."""
        parts: list[str] = []

        # Trim
        if clip.source_in > 0 or clip.source_out > 0:
            trim = f"trim=start={clip.source_in}"
            if clip.source_out > clip.source_in:
                trim += f":end={clip.source_out}"
            parts.append(trim)
            parts.append("setpts=PTS-STARTPTS")

        # MARKER_B16: Color pipeline — log decode BEFORE effects (decode to linear first)
        if clip.log_profile:
            log_filter = _compile_log_decode_filter(clip.log_profile)
            if log_filter:
                parts.append(log_filter)

        # MARKER_B16: LUT application — after log decode, before user effects
        if clip.lut_path and os.path.isfile(clip.lut_path):
            # Escape path for FFmpeg filter (single quotes, escape internal quotes)
            escaped = clip.lut_path.replace("'", "'\\''")
            parts.append(f"lut3d='{escaped}'")

        # MARKER_B9 + B44 + B45: Insert video effects (with keyframe resolution)
        if clip.video_effects:
            from src.services.cut_effects_engine import (
                compile_video_filters,
                resolve_effect_params_at_time,
                compile_keyframed_sendcmd,
            )
            has_animated_kfs = self._has_animated_keyframes_static(clip)
            if clip.keyframes and has_animated_kfs:
                # MARKER_B45: V2 — animated keyframes via sendcmd temp file
                sendcmd_text = compile_keyframed_sendcmd(
                    clip.video_effects, clip.keyframes, clip.duration_sec,
                )
                if sendcmd_text:
                    import tempfile
                    sendcmd_fd, sendcmd_path = tempfile.mkstemp(
                        prefix=f"cut_sendcmd_{idx}_", suffix=".txt",
                    )
                    os.write(sendcmd_fd, sendcmd_text.encode("utf-8"))
                    os.close(sendcmd_fd)
                    # Track for cleanup
                    if not hasattr(self.plan, "_sendcmd_paths"):
                        self.plan._sendcmd_paths = []  # type: ignore[attr-defined]
                    self.plan._sendcmd_paths.append(sendcmd_path)  # type: ignore[attr-defined]
                    # Add sendcmd before effect filters, then static-resolved effects
                    escaped = sendcmd_path.replace("'", "'\\''")
                    parts.append(f"sendcmd=f='{escaped}'")
                # Still add static filters (sendcmd modifies them dynamically)
                mid_time = clip.duration_sec / 2.0
                resolved_effects = [
                    resolve_effect_params_at_time(e, clip.keyframes, mid_time)
                    for e in clip.video_effects
                ]
                effect_filters = compile_video_filters(resolved_effects)
            elif clip.keyframes:
                # B44 V1 fallback: resolve at midpoint (non-animatable keyframes)
                mid_time = clip.duration_sec / 2.0
                resolved_effects = [
                    resolve_effect_params_at_time(e, clip.keyframes, mid_time)
                    for e in clip.video_effects
                ]
                effect_filters = compile_video_filters(resolved_effects)
            else:
                effect_filters = compile_video_filters(clip.video_effects)
            parts.extend(effect_filters)

        # MARKER_B53: Motion controls → FFmpeg filters
        if clip.motion:
            m = clip.motion
            # Crop (percentage → pixels, applied first)
            cl = float(m.get("cropLeft", 0))
            cr = float(m.get("cropRight", 0))
            ct = float(m.get("cropTop", 0))
            cb = float(m.get("cropBottom", 0))
            if cl > 0 or cr > 0 or ct > 0 or cb > 0:
                # crop=out_w:out_h:x:y — expressed as expressions using iw/ih
                parts.append(
                    f"crop=iw*(1-{(cl+cr)/100:.4f}):ih*(1-{(ct+cb)/100:.4f})"
                    f":iw*{cl/100:.4f}:ih*{ct/100:.4f}"
                )
            # Scale
            sx = float(m.get("scaleX", 1))
            sy = float(m.get("scaleY", sx))  # default uniform
            if sx != 1.0 or sy != 1.0:
                parts.append(f"scale=iw*{sx:.4f}:ih*{sy:.4f}")
            # Rotation (degrees → radians for FFmpeg rotate filter)
            rot = float(m.get("rotation", 0))
            if rot != 0:
                import math
                rad = rot * math.pi / 180
                parts.append(f"rotate={rad:.6f}:ow=rotw({rad:.6f}):oh=roth({rad:.6f}):fillcolor=black")
            # Position (x/y offset via pad + crop trick)
            px = float(m.get("x", 0))
            py = float(m.get("y", 0))
            if px != 0 or py != 0:
                # Pad canvas larger, then crop back to original size at offset
                parts.append(f"pad=iw+abs({px:.0f})*2:ih+abs({py:.0f})*2:{max(0,px):.0f}:{max(0,py):.0f}:black")
            # Opacity (via colorchannelmixer alpha)
            opacity = float(m.get("opacity", 1))
            if opacity < 1.0:
                parts.append(f"colorchannelmixer=aa={opacity:.4f}")

        # Speed
        if clip.speed != 1.0 and clip.speed > 0:
            pts_factor = 1.0 / clip.speed
            parts.append(f"setpts={pts_factor:.4f}*PTS")

        # MARKER_B11: Reverse playback — must come after speed
        if clip.reverse:
            parts.append("reverse")
            parts.append("setpts=PTS-STARTPTS")

        # MARKER_B11: Frame blending for smooth slow-mo (FCP7 Ch.73)
        # minterpolate generates intermediate frames via motion estimation
        if clip.frame_blend and clip.speed < 1.0 and clip.speed > 0:
            target_fps = self.plan.fps
            parts.append(f"minterpolate=fps={target_fps}:mi_mode=mci:mc_mode=aobmc:me_mode=bidir:vsbmc=1")

        if not parts:
            parts.append("null")

        return f"[{idx}:v]{','.join(parts)}[v{idx}]"

    def _clip_audio_filter(self, idx: int, clip: RenderClip) -> str:
        """Per-clip audio: atrim + effects + speed + reverse."""
        parts: list[str] = []

        if clip.source_in > 0 or clip.source_out > 0:
            trim = f"atrim=start={clip.source_in}"
            if clip.source_out > clip.source_in:
                trim += f":end={clip.source_out}"
            parts.append(trim)
            parts.append("asetpts=PTS-STARTPTS")

        # MARKER_B9: Insert audio effects between trim and speed
        if clip.audio_effects:
            from src.services.cut_effects_engine import compile_audio_filters
            effect_filters = compile_audio_filters(clip.audio_effects)
            parts.extend(effect_filters)

        # MARKER_B11: Speed change with pitch control
        if clip.speed != 1.0 and clip.speed > 0:
            if clip.maintain_pitch:
                # atempo preserves pitch (default, FCP7 behavior)
                tempo_chain = _build_atempo_chain(clip.speed)
                parts.extend(tempo_chain)
            else:
                # asetrate shifts pitch with speed (chipmunk/slow effect)
                parts.append(f"asetrate=r={clip.speed:.4f}*44100")
                parts.append("aresample=44100")

        # MARKER_B11: Reverse audio — must come after speed
        if clip.reverse:
            parts.append("areverse")
            parts.append("asetpts=PTS-STARTPTS")

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
                # MARKER_B14: Audio crossfade with curve selection
                # equal_power (+3dB) = qsin (quarter sine), sounds smooth
                # linear (0dB) = tri (triangle), sounds dip at midpoint
                curve = getattr(t, "audio_curve", "equal_power")
                if curve == "linear":
                    c1, c2 = "tri", "tri"
                else:
                    c1, c2 = "qsin", "qsin"  # equal_power (default, FCP7 +3dB)
                filters.append(
                    f"{current}{next_label}acrossfade=d={t.duration_sec:.3f}"
                    f":c1={c1}:c2={c2}{out_label}"
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
        "dip_to_white": "fadewhite",
        "wipe": "wipeleft",
        "wipe_left": "wipeleft",
        "wipe_right": "wiperight",
        "wipe_up": "wipeup",
        "wipe_down": "wipedown",
        "slide_left": "slideleft",
        "slide_right": "slideright",
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
    has_effects = any(c.video_effects or c.audio_effects for c in plan.clips)
    # MARKER_B11: reverse and frame_blend require filter_complex
    has_reverse = any(c.reverse for c in plan.clips)
    has_frame_blend = any(c.frame_blend and c.speed < 1.0 for c in plan.clips)
    # MARKER_B16: color pipeline requires filter_complex
    has_color = any(c.log_profile or c.lut_path for c in plan.clips)
    use_filter_complex = (has_transitions or has_speed_changes or has_trims
                          or has_effects or has_reverse or has_frame_blend
                          or has_color)

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

    # Quality / Bitrate (MARKER_B6.3: CBR/VBR/CRF modes)
    if plan.codec in ("h264", "h265"):
        mode = plan.bitrate_mode or "crf"
        if mode == "cbr" and plan.target_bitrate:
            cmd += ["-b:v", plan.target_bitrate, "-maxrate", plan.target_bitrate, "-bufsize", plan.target_bitrate]
        elif mode == "vbr" and plan.target_bitrate:
            cmd += ["-b:v", plan.target_bitrate]
            if plan.max_bitrate:
                cmd += ["-maxrate", plan.max_bitrate, "-bufsize", plan.max_bitrate]
        else:
            # CRF (default)
            crf = max(0, min(51, int(51 - (plan.quality / 100) * 51)))
            cmd += ["-crf", str(crf)]

    # Audio (MARKER_B6.2: configurable audio codec)
    a_codec = plan.audio_codec or "aac"
    cmd += ["-c:a", a_codec]
    if a_codec == "aac":
        cmd += ["-b:a", "320k"]
    elif a_codec == "libmp3lame":
        cmd += ["-b:a", "320k"]
    # PCM and FLAC don't need bitrate

    # Range (applied as output trim)
    if plan.range_in is not None and plan.range_out is not None and plan.range_out > plan.range_in:
        cmd += ["-ss", str(plan.range_in), "-t", str(plan.range_out - plan.range_in)]

    # MARKER_B43: Real-time progress via -progress pipe
    cmd += ["-progress", "pipe:1"]
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

    # Quality / Bitrate (MARKER_B6.3)
    if plan.codec in ("h264", "h265"):
        mode = plan.bitrate_mode or "crf"
        if mode == "cbr" and plan.target_bitrate:
            cmd += ["-b:v", plan.target_bitrate, "-maxrate", plan.target_bitrate, "-bufsize", plan.target_bitrate]
        elif mode == "vbr" and plan.target_bitrate:
            cmd += ["-b:v", plan.target_bitrate]
            if plan.max_bitrate:
                cmd += ["-maxrate", plan.max_bitrate, "-bufsize", plan.max_bitrate]
        else:
            crf = max(0, min(51, int(51 - (plan.quality / 100) * 51)))
            cmd += ["-crf", str(crf)]

    # Range
    if plan.range_in is not None and plan.range_out is not None and plan.range_out > plan.range_in:
        cmd += ["-ss", str(plan.range_in), "-t", str(plan.range_out - plan.range_in)]

    cmd += ["-r", str(plan.fps)]
    # MARKER_B6.2: configurable audio codec
    a_codec = plan.audio_codec or "aac"
    cmd += ["-c:a", a_codec]
    if a_codec in ("aac", "libmp3lame"):
        cmd += ["-b:a", "320k"]
    # MARKER_B43: Real-time progress via -progress pipe
    cmd += ["-progress", "pipe:1"]
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
# MARKER_B2.5: Thumbnail generation
# ---------------------------------------------------------------------------

def generate_thumbnail(
    video_path: str,
    *,
    output_path: str = "",
    seek_sec: float | None = None,
    width: int = 1280,
    height: int = 720,
    ffmpeg_path: str | None = None,
    timeout: int = 30,
) -> str:
    """
    Extract a thumbnail JPEG from a video file.

    Args:
        video_path: Path to source video.
        output_path: Where to save thumbnail. Default: {video}_thumb.jpg
        seek_sec: Timestamp to extract. Default: middle of video.
        width/height: Thumbnail dimensions (maintains aspect ratio).

    Returns:
        Path to generated thumbnail, or "" on failure.
    """
    if not os.path.isfile(video_path):
        return ""

    if ffmpeg_path is None:
        ffmpeg_path = shutil.which("ffmpeg")
    if not ffmpeg_path:
        return ""

    if not output_path:
        base, _ = os.path.splitext(video_path)
        output_path = f"{base}_thumb.jpg"

    # Determine seek position
    if seek_sec is None:
        # Probe duration, seek to middle
        ffprobe = shutil.which("ffprobe")
        if ffprobe:
            try:
                proc = subprocess.run(
                    [ffprobe, "-v", "error", "-show_entries", "format=duration",
                     "-of", "csv=p=0", video_path],
                    capture_output=True, text=True, timeout=10,
                )
                dur = float(proc.stdout.strip() or "0")
                seek_sec = dur / 2.0
            except Exception:
                seek_sec = 1.0
        else:
            seek_sec = 1.0

    cmd = [
        ffmpeg_path, "-y",
        "-ss", str(seek_sec),
        "-i", video_path,
        "-frames:v", "1",
        "-vf", f"scale={width}:{height}:force_original_aspect_ratio=decrease,"
               f"pad={width}:{height}:-1:-1:color=black",
        "-q:v", "3",  # JPEG quality (2-5 is good, lower=better)
        output_path,
    ]

    try:
        subprocess.run(cmd, capture_output=True, timeout=timeout)
        if os.path.isfile(output_path):
            return output_path
    except Exception:
        pass

    return ""


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
    mixer: dict[str, Any] | None = None,  # MARKER_B13: mixer state
    cancel_check: Any = None,  # MARKER_B2.1: callable() → bool, True = cancel requested
    audio_codec: str = "aac",  # MARKER_B6.2: aac, pcm_s24le, libmp3lame, flac
    bitrate_mode: str = "crf",  # MARKER_B6.3: crf, cbr, vbr
    target_bitrate: str = "",   # e.g. "12M"
    max_bitrate: str = "",      # e.g. "15M" (vbr only)
) -> dict[str, Any]:
    """
    Render a timeline to a video file.

    Args:
        timeline: Timeline state dict with lanes/clips.
        on_progress: Optional callback(progress: float, message: str).
        cancel_check: Optional callable returning True if cancel requested.
        Other args: render settings.

    Returns:
        Dict with output_path, file_size_bytes, stem_paths, codec, resolution.

    Raises:
        RuntimeError: If ffmpeg not found or render fails.
        RenderCancelled: If cancel_check returns True during render.
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
        audio_codec=audio_codec,
        bitrate_mode=bitrate_mode,
        target_bitrate=target_bitrate,
        max_bitrate=max_bitrate,
    )

    # MARKER_B13: Apply mixer state (volume/mute/solo/pan) to render plan
    if mixer:
        from src.services.cut_audio_engine import MixerState, apply_mixer_to_plan
        mixer_state = MixerState.from_dict(mixer)
        apply_mixer_to_plan(plan, mixer_state)

    if not plan.clips:
        raise RuntimeError("No video clips found in timeline")

    _progress(0.1, f"Rendering {len(plan.clips)} clips, {len(plan.transitions)} transitions")

    cmd = build_ffmpeg_command(plan, ffmpeg_path)

    _progress(0.3, "Running FFmpeg")

    # MARKER_B43: Compute total duration for real progress %
    total_duration_sec = 0.0
    for c in plan.clips:
        total_duration_sec += c.duration_sec / c.speed if c.speed > 0 else c.duration_sec
    if plan.range_in is not None and plan.range_out is not None:
        total_duration_sec = min(total_duration_sec, plan.range_out - plan.range_in)
    total_duration_us = max(1, total_duration_sec * 1_000_000)

    # MARKER_B2.1 + B43: Use Popen with -progress pipe:1 for real progress
    t_start = time.monotonic()
    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
    except OSError as exc:
        raise RuntimeError(f"FFmpeg launch failed: {exc}")

    # MARKER_B43 + B45: Parse -progress pipe output for real % and speed
    cancelled = False
    _last_speed_x = 0.0  # MARKER_B45: track encoding speed for ETA
    try:
        import selectors
        sel = selectors.DefaultSelector()
        sel.register(proc.stdout, selectors.EVENT_READ)  # type: ignore[arg-type]

        while proc.poll() is None:
            elapsed = time.monotonic() - t_start

            # Check cancel
            if cancel_check and cancel_check():
                proc.kill()
                proc.wait(timeout=5)
                cancelled = True
                break

            # Check timeout
            if elapsed > timeout:
                proc.kill()
                proc.wait(timeout=5)
                raise RuntimeError(f"FFmpeg timed out after {timeout}s")

            # Read available lines from -progress pipe (non-blocking via selector)
            ready = sel.select(timeout=0.3)
            if ready:
                line = proc.stdout.readline()  # type: ignore[union-attr]
                if line:
                    line = line.strip()
                    if line.startswith("out_time_us="):
                        try:
                            out_us = int(line.split("=", 1)[1])
                            frac = min(out_us / total_duration_us, 1.0)
                            # MARKER_B45: Include speed and ETA in progress message
                            remaining_sec = 0.0
                            if _last_speed_x > 0 and frac < 1.0:
                                rendered_sec = out_us / 1_000_000
                                remaining_media_sec = total_duration_sec - rendered_sec
                                remaining_sec = remaining_media_sec / _last_speed_x
                            msg = "Encoding..."
                            if _last_speed_x > 0:
                                msg = f"Encoding at {_last_speed_x:.1f}x"
                                if remaining_sec > 0:
                                    msg += f", ETA: {int(remaining_sec)}s"
                            _progress(0.3 + frac * 0.55, msg)
                        except (ValueError, ZeroDivisionError):
                            pass
                    elif line.startswith("speed="):
                        # MARKER_B45: Parse encoding speed (e.g. "speed=2.34x")
                        try:
                            speed_str = line.split("=", 1)[1].strip().rstrip("x")
                            _last_speed_x = float(speed_str) if speed_str != "N/A" else 0.0
                        except (ValueError, IndexError):
                            pass
            else:
                # No data ready — just loop (selector handles timing)
                pass

        sel.close()

        # Drain remaining stdout
        if proc.stdout:
            proc.stdout.read()

    except Exception:
        # Ensure process is killed on any error
        if proc.poll() is None:
            proc.kill()
            proc.wait(timeout=5)
        raise

    # Cleanup concat file if used
    concat_path = getattr(plan, "_concat_path", None)
    if concat_path:
        try:
            os.remove(concat_path)
        except OSError:
            pass

    # MARKER_B45: Cleanup sendcmd temp files
    sendcmd_paths = getattr(plan, "_sendcmd_paths", [])
    for sp in sendcmd_paths:
        try:
            os.remove(sp)
        except OSError:
            pass

    # Handle cancellation
    if cancelled:
        # Cleanup partial output
        if os.path.exists(plan.output_path):
            try:
                os.remove(plan.output_path)
            except OSError:
                pass
        raise RenderCancelled("Render cancelled by user")

    if proc.returncode != 0:
        stderr = ""
        if proc.stderr:
            try:
                stderr = proc.stderr.read()[-500:]
            except Exception:
                pass
        raise RuntimeError(f"FFmpeg failed (exit {proc.returncode}): {stderr}")

    elapsed_sec = round(time.monotonic() - t_start, 2)

    result: dict[str, Any] = {
        "output_path": plan.output_path,
        "codec": plan.codec,
        "resolution": plan.resolution,
        "elapsed_sec": elapsed_sec,  # MARKER_B2.1
        "file_size_bytes": os.path.getsize(plan.output_path) if os.path.exists(plan.output_path) else 0,
        "clips_count": len(plan.clips),
        "transitions_count": len(plan.transitions),
        "used_filter_complex": bool(plan.transitions) or any(c.speed != 1.0 for c in plan.clips),
        # MARKER_B11: Speed/reverse stats
        "speed_clips": sum(1 for c in plan.clips if c.speed != 1.0),
        "reversed_clips": sum(1 for c in plan.clips if c.reverse),
        "frame_blend_clips": sum(1 for c in plan.clips if c.frame_blend and c.speed < 1.0),
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

    # MARKER_B2.5: Generate thumbnail
    _progress(0.95, "Generating thumbnail")
    thumb_path = generate_thumbnail(plan.output_path, ffmpeg_path=ffmpeg_path)
    result["thumbnail_path"] = thumb_path

    _progress(1.0, "Render complete")
    return result
