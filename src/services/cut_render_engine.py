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
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal


# ---------------------------------------------------------------------------
# MARKER_B2.1: Render cancellation exception
# ---------------------------------------------------------------------------

class RenderCancelled(RuntimeError):
    """Raised when render is cancelled by user."""
    pass


# ---------------------------------------------------------------------------
# Codec / Resolution maps (shared with cut_routes.py)
# ---------------------------------------------------------------------------

CODEC_MAP: dict[str, dict[str, str]] = {
    # === Apple ProRes family ===
    "prores_proxy": {"vcodec": "prores_ks", "profile": "0", "ext": ".mov", "pix_fmt": "yuv422p10le"},
    "prores_lt":    {"vcodec": "prores_ks", "profile": "1", "ext": ".mov", "pix_fmt": "yuv422p10le"},
    "prores_422":   {"vcodec": "prores_ks", "profile": "2", "ext": ".mov", "pix_fmt": "yuv422p10le"},
    "prores_422hq": {"vcodec": "prores_ks", "profile": "3", "ext": ".mov", "pix_fmt": "yuv422p10le"},
    "prores_4444":  {"vcodec": "prores_ks", "profile": "4", "ext": ".mov", "pix_fmt": "yuva444p10le"},
    "prores_4444xq": {"vcodec": "prores_ks", "profile": "5", "ext": ".mov", "pix_fmt": "yuva444p10le"},
    # === Avid DNxHR family ===
    "dnxhr_lb":  {"vcodec": "dnxhd", "profile": "dnxhr_lb",  "ext": ".mxf", "pix_fmt": "yuv422p"},
    "dnxhr_sq":  {"vcodec": "dnxhd", "profile": "dnxhr_sq",  "ext": ".mxf", "pix_fmt": "yuv422p"},
    "dnxhr_hq":  {"vcodec": "dnxhd", "profile": "dnxhr_hq",  "ext": ".mxf", "pix_fmt": "yuv422p"},
    "dnxhr_hqx": {"vcodec": "dnxhd", "profile": "dnxhr_hqx", "ext": ".mxf", "pix_fmt": "yuv422p10le"},
    "dnxhr_444": {"vcodec": "dnxhd", "profile": "dnxhr_444", "ext": ".mxf", "pix_fmt": "yuv444p10le"},
    "dnxhd":     {"vcodec": "dnxhd", "profile": "",           "ext": ".mxf", "pix_fmt": "yuv422p"},
    # === H.264 / AVC ===
    "h264":        {"vcodec": "libx264",    "profile": "",     "ext": ".mp4", "pix_fmt": "yuv420p"},
    "h264_10bit":  {"vcodec": "libx264",    "profile": "high10", "ext": ".mp4", "pix_fmt": "yuv420p10le"},
    # === H.265 / HEVC ===
    "h265":        {"vcodec": "libx265",    "profile": "",     "ext": ".mp4", "pix_fmt": "yuv420p"},
    "h265_10bit":  {"vcodec": "libx265",    "profile": "main10", "ext": ".mp4", "pix_fmt": "yuv420p10le"},
    # === Web / Modern codecs ===
    "vp9":    {"vcodec": "libvpx-vp9", "profile": "", "ext": ".webm", "pix_fmt": "yuv420p"},
    "av1":    {"vcodec": "libsvtav1",  "profile": "", "ext": ".mp4",  "pix_fmt": "yuv420p10le"},
    "av1_8":  {"vcodec": "libsvtav1",  "profile": "", "ext": ".mp4",  "pix_fmt": "yuv420p"},
    # === Lossless / Intermediate ===
    "ffv1":     {"vcodec": "ffv1",     "profile": "", "ext": ".mkv",  "pix_fmt": "yuv422p10le"},
    "huffyuv":  {"vcodec": "huffyuv",  "profile": "", "ext": ".avi",  "pix_fmt": "yuv422p"},
    "ut_video": {"vcodec": "utvideo",  "profile": "", "ext": ".avi",  "pix_fmt": "yuv422p"},
    # === Legacy / Broadcast ===
    "mpeg2":  {"vcodec": "mpeg2video", "profile": "", "ext": ".mxf", "pix_fmt": "yuv422p"},
    "mjpeg":  {"vcodec": "mjpeg",      "profile": "", "ext": ".avi", "pix_fmt": "yuvj420p"},
    # === Image sequence ===
    "png_seq":  {"vcodec": "png",      "profile": "", "ext": ".png", "pix_fmt": "rgb24"},
    "tiff_seq": {"vcodec": "tiff",     "profile": "", "ext": ".tiff", "pix_fmt": "rgb48le"},
    "dpx_seq":  {"vcodec": "dpx",      "profile": "", "ext": ".dpx", "pix_fmt": "gbrp10le"},
    "exr_seq":  {"vcodec": "exr",      "profile": "", "ext": ".exr", "pix_fmt": "gbrpf32le"},
}

RESOLUTION_MAP: dict[str, tuple[int, int] | None] = {
    "8k": (7680, 4320),
    "4k": (3840, 2160),
    "1080p": (1920, 1080),
    "720p": (1280, 720),
    "source": None,
}

# MARKER_B2.3: Export presets — social + production
EXPORT_PRESETS: dict[str, dict[str, Any]] = {
    # === Social / Delivery ===
    "youtube_1080": {"codec": "h264", "resolution": "1080p", "fps": 30, "quality": 85,
                     "label": "YouTube 1080p"},
    "youtube_4k": {"codec": "h264", "resolution": "4k", "fps": 30, "quality": 90,
                   "label": "YouTube 4K"},
    "instagram_reels": {"codec": "h264", "resolution": "1080p", "fps": 30, "quality": 80,
                        "aspect": "9:16", "label": "Instagram Reels (9:16)"},
    "instagram_story": {"codec": "h264", "resolution": "1080p", "fps": 30, "quality": 75,
                        "aspect": "9:16", "label": "Instagram Story (9:16)"},
    "tiktok": {"codec": "h264", "resolution": "1080p", "fps": 30, "quality": 80,
               "aspect": "9:16", "label": "TikTok (9:16)"},
    "telegram": {"codec": "h264", "resolution": "720p", "fps": 30, "quality": 70,
                 "label": "Telegram (720p)"},
    "twitter": {"codec": "h264", "resolution": "1080p", "fps": 30, "quality": 80,
                "label": "Twitter/X"},
    "vimeo": {"codec": "h264", "resolution": "1080p", "fps": 25, "quality": 90,
              "label": "Vimeo (high quality)"},
    # === Production / Archive ===
    "prores_master": {"codec": "prores_422hq", "resolution": "source", "fps": 25, "quality": 100,
                      "label": "ProRes 422 HQ (Master)"},
    "prores_4444": {"codec": "prores_4444", "resolution": "4k", "fps": 25, "quality": 100,
                    "label": "ProRes 4444 (Archive)"},
    "dnxhr_hq": {"codec": "dnxhr_hq", "resolution": "1080p", "fps": 25, "quality": 100,
                 "label": "DNxHR HQ (Avid)"},
    "review_h264": {"codec": "h264", "resolution": "720p", "fps": 25, "quality": 60,
                    "label": "Review Copy (720p, fast)"},
    # === Web / Modern ===
    "av1_web": {"codec": "av1", "resolution": "1080p", "fps": 30, "quality": 80,
                "label": "AV1 Web (small file)"},
    "vp9_webm": {"codec": "vp9", "resolution": "1080p", "fps": 30, "quality": 80,
                 "label": "VP9 WebM"},
}

# Backward compat aliases (old key names)
EXPORT_PRESETS["youtube"] = EXPORT_PRESETS["youtube_1080"]
SOCIAL_PRESETS = EXPORT_PRESETS


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
            ))
        elif overlap > 0.01:  # >10ms overlap = auto crossfade
            transitions.append(Transition(
                type="crossfade",
                duration_sec=min(overlap, 5.0),
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

        # MARKER_B9: Insert video effects between color pipeline and speed
        if clip.video_effects:
            from src.services.cut_effects_engine import compile_video_filters
            effect_filters = compile_video_filters(clip.video_effects)
            parts.extend(effect_filters)

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
# MARKER_B16: Log decode → FFmpeg filter compilation
# ---------------------------------------------------------------------------

# Camera log profiles → FFmpeg curves/eq approximation.
# These map log-encoded footage to Rec.709 gamma for viewing/grading.
# For best results, use a proper LUT instead (set lut_path on clip).
_LOG_DECODE_FILTERS: dict[str, str] = {
    # V-Log (Panasonic) → approximate Rec.709 via curves
    "V-Log": "curves=master='0/0 0.09/0 0.13/0.05 0.25/0.15 0.42/0.35 0.52/0.50 0.65/0.70 0.78/0.85 0.90/0.95 1/1'",
    # S-Log3 (Sony) → approximate Rec.709
    "S-Log3": "curves=master='0/0 0.10/0 0.15/0.04 0.25/0.12 0.40/0.30 0.50/0.47 0.63/0.68 0.75/0.82 0.88/0.94 1/1'",
    # ARRI LogC3 → approximate Rec.709
    "LogC3": "curves=master='0/0 0.09/0 0.12/0.03 0.22/0.12 0.38/0.32 0.48/0.48 0.60/0.67 0.73/0.82 0.86/0.93 1/1'",
    "ARRI LogC3": "curves=master='0/0 0.09/0 0.12/0.03 0.22/0.12 0.38/0.32 0.48/0.48 0.60/0.67 0.73/0.82 0.86/0.93 1/1'",
    # Canon Log 3
    "Canon Log 3": "curves=master='0/0 0.08/0 0.12/0.04 0.24/0.14 0.40/0.33 0.50/0.48 0.62/0.66 0.74/0.80 0.88/0.94 1/1'",
    # sRGB → no decode needed (already Rec.709 gamma)
    "sRGB": "",
    # HLG (Hybrid Log-Gamma) → FFmpeg has native support
    "HLG": "zscale=transfer=bt709:transferin=arib-std-b67",
    # PQ (Perceptual Quantizer / HDR10) → tone-map to SDR
    "PQ": "zscale=transfer=bt709:transferin=smpte2084:tonemap=hable",
}


def _compile_log_decode_filter(profile: str) -> str:
    """
    Get FFmpeg filter for decoding camera log profile to Rec.709.

    Returns empty string if profile is unknown or no decode needed.
    The curves approximation is serviceable for editing preview;
    for final delivery, use a proper 3D LUT from the camera manufacturer.
    """
    return _LOG_DECODE_FILTERS.get(profile, "")


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

    # MARKER_B2.1: Use Popen for cancel support + ETA tracking
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

    # Poll loop: check cancel + timeout
    cancelled = False
    try:
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

            # Progress estimate: linear interpolation between 0.3 and 0.85
            # (real FFmpeg progress parsing requires -progress pipe, future enhancement)
            if elapsed > 0 and timeout > 0:
                frac = min(elapsed / timeout, 1.0)
                _progress(0.3 + frac * 0.55, "Encoding...")

            time.sleep(0.5)
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
