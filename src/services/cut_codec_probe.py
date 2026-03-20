"""
MARKER_B1 — FFprobe codec detection + metadata extraction.

Structured wrapper around ffprobe for CUT editor media pipeline.
Replaces inline _probe_ffprobe_metadata() in cut_routes.py with
typed ProbeResult dataclass + color space / bit depth inference.

@status: active
@phase: B1
@task: tb_1773981821_8
@depends: ffprobe (system binary)
@used_by: cut_routes (POST /media/support), cut_proxy_worker, cut_render_engine
"""
from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import dataclass, field
from fractions import Fraction
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# ProbeResult — structured output
# ---------------------------------------------------------------------------

@dataclass
class VideoStream:
    """Parsed video stream from ffprobe."""
    codec: str = ""            # e.g. "h264", "prores", "hevc"
    width: int = 0
    height: int = 0
    fps: float = 0.0
    pix_fmt: str = ""          # e.g. "yuv420p", "yuv422p10le"
    color_space: str = ""      # e.g. "Rec.709", "Rec.2020", "DCI-P3"
    color_primaries: str = ""  # raw ffprobe value
    color_transfer: str = ""   # raw ffprobe value
    bit_depth: int = 8
    profile: str = ""          # e.g. "High", "Main 10"
    index: int = 0


@dataclass
class AudioStream:
    """Parsed audio stream from ffprobe."""
    codec: str = ""            # e.g. "aac", "pcm_s24le"
    sample_rate: int = 0
    channels: int = 0
    bit_depth: int = 0         # 16, 24, 32 for PCM; 0 for lossy
    index: int = 0


@dataclass
class ProbeResult:
    """Full structured probe result for a media file."""
    path: str = ""
    exists: bool = False
    available: bool = False     # True if ffprobe binary found

    # Container
    container: str = ""         # e.g. "mov,mp4,m4a,3gp,3g2,mj2"
    duration_sec: float = 0.0
    bitrate_kbps: int = 0
    file_size_bytes: int = 0

    # Streams
    video: VideoStream | None = None
    audio: AudioStream | None = None
    video_streams: list[VideoStream] = field(default_factory=list)
    audio_streams: list[AudioStream] = field(default_factory=list)

    # Convenience accessors (filled from first video/audio stream)
    video_codec: str = ""
    audio_codec: str = ""
    width: int = 0
    height: int = 0
    fps: float = 0.0
    pix_fmt: str = ""
    color_space: str = ""
    bit_depth: int = 8
    sample_rate: int = 0
    channels: int = 0

    # Error state
    error: str = ""

    @property
    def ok(self) -> bool:
        return self.available and self.exists and not self.error

    @property
    def resolution_label(self) -> str:
        """Human-readable resolution: 4K, 1080p, 720p, etc."""
        h = self.height
        if h >= 4320:
            return "8K"
        if h >= 2880:
            return "6K"
        if h >= 2160:
            return "4K"
        if h >= 1440:
            return "2K"
        if h >= 1080:
            return "1080p"
        if h >= 720:
            return "720p"
        if h >= 480:
            return "SD"
        return f"{h}p" if h > 0 else "unknown"

    def to_dict(self) -> dict[str, Any]:
        """Serialize for JSON API response."""
        d: dict[str, Any] = {
            "path": self.path,
            "exists": self.exists,
            "available": self.available,
            "ok": self.ok,
            "container": self.container,
            "duration_sec": self.duration_sec,
            "bitrate_kbps": self.bitrate_kbps,
            "file_size_bytes": self.file_size_bytes,
            "video_codec": self.video_codec,
            "audio_codec": self.audio_codec,
            "width": self.width,
            "height": self.height,
            "fps": self.fps,
            "pix_fmt": self.pix_fmt,
            "color_space": self.color_space,
            "bit_depth": self.bit_depth,
            "resolution_label": self.resolution_label,
            "sample_rate": self.sample_rate,
            "channels": self.channels,
            "error": self.error,
        }
        if self.video:
            d["video_stream"] = {
                "codec": self.video.codec,
                "width": self.video.width,
                "height": self.video.height,
                "fps": self.video.fps,
                "pix_fmt": self.video.pix_fmt,
                "color_space": self.video.color_space,
                "color_primaries": self.video.color_primaries,
                "color_transfer": self.video.color_transfer,
                "bit_depth": self.video.bit_depth,
                "profile": self.video.profile,
                "index": self.video.index,
            }
        if self.audio:
            d["audio_stream"] = {
                "codec": self.audio.codec,
                "sample_rate": self.audio.sample_rate,
                "channels": self.audio.channels,
                "bit_depth": self.audio.bit_depth,
                "index": self.audio.index,
            }
        d["video_stream_count"] = len(self.video_streams)
        d["audio_stream_count"] = len(self.audio_streams)
        return d


# ---------------------------------------------------------------------------
# Color space inference
# ---------------------------------------------------------------------------

# ffprobe color_primaries → human label
_COLOR_PRIMARIES_MAP: dict[str, str] = {
    "bt709": "Rec.709",
    "bt2020": "Rec.2020",
    "smpte432": "DCI-P3",
    "smpte431": "DCI-P3",
    "bt470bg": "Rec.601",
    "smpte170m": "Rec.601",
    "smpte240m": "SMPTE 240M",
    "film": "Film",
}

# pix_fmt → (bit_depth, chroma)
_PIX_FMT_INFO: dict[str, tuple[int, str]] = {
    "yuv420p": (8, "4:2:0"),
    "yuv422p": (8, "4:2:2"),
    "yuv444p": (8, "4:4:4"),
    "yuv420p10le": (10, "4:2:0"),
    "yuv420p10be": (10, "4:2:0"),
    "yuv422p10le": (10, "4:2:2"),
    "yuv422p10be": (10, "4:2:2"),
    "yuv444p10le": (10, "4:4:4"),
    "yuv444p10be": (10, "4:4:4"),
    "yuv420p12le": (12, "4:2:0"),
    "yuv422p12le": (12, "4:2:2"),
    "yuv444p12le": (12, "4:4:4"),
    "yuva444p10le": (10, "4:4:4+A"),
    "rgb24": (8, "RGB"),
    "rgb48le": (16, "RGB"),
    "gbrp10le": (10, "RGB"),
    "gbrp12le": (12, "RGB"),
}


def _infer_color_space(color_primaries: str, pix_fmt: str) -> str:
    """Infer color space from ffprobe color_primaries and pix_fmt."""
    # Explicit primaries first
    if color_primaries and color_primaries != "unknown":
        label = _COLOR_PRIMARIES_MAP.get(color_primaries, "")
        if label:
            return label

    # Heuristic: 10-bit+ with no explicit primaries — likely Rec.709 (camera default)
    # but flag as unknown to avoid wrong assumptions
    bit_depth, _ = _PIX_FMT_INFO.get(pix_fmt, (8, ""))
    if bit_depth >= 10 and not color_primaries:
        return "Rec.709 (assumed)"

    # 8-bit standard → Rec.709
    if pix_fmt.startswith("yuv") and bit_depth == 8:
        return "Rec.709"

    return "unknown"


def _infer_bit_depth(pix_fmt: str) -> int:
    """Infer bit depth from pix_fmt string."""
    info = _PIX_FMT_INFO.get(pix_fmt)
    if info:
        return info[0]
    # Fallback: look for number in pix_fmt name
    if "10" in pix_fmt:
        return 10
    if "12" in pix_fmt:
        return 12
    if "16" in pix_fmt:
        return 16
    return 8


# ---------------------------------------------------------------------------
# Frame rate parsing
# ---------------------------------------------------------------------------

def _parse_fps(rate_str: str) -> float:
    """Parse ffprobe frame rate string like '30000/1001' or '25/1'."""
    if not rate_str or rate_str == "0/0":
        return 0.0
    try:
        if "/" in rate_str:
            frac = Fraction(rate_str)
            return round(float(frac), 3)
        return round(float(rate_str), 3)
    except (ValueError, ZeroDivisionError):
        return 0.0


# ---------------------------------------------------------------------------
# Audio bit depth from codec
# ---------------------------------------------------------------------------

_PCM_BIT_DEPTH: dict[str, int] = {
    "pcm_s16le": 16, "pcm_s16be": 16,
    "pcm_s24le": 24, "pcm_s24be": 24,
    "pcm_s32le": 32, "pcm_s32be": 32,
    "pcm_f32le": 32, "pcm_f32be": 32,
    "pcm_f64le": 64, "pcm_f64be": 64,
}


# ---------------------------------------------------------------------------
# Core probe function
# ---------------------------------------------------------------------------

_FFPROBE_ENTRIES = (
    "stream=index,codec_name,codec_type,codec_tag_string,profile,"
    "width,height,avg_frame_rate,r_frame_rate,pix_fmt,"
    "color_primaries,color_transfer,color_space,"
    "channels,sample_rate,bits_per_raw_sample,bits_per_sample"
    ":format=format_name,duration,bit_rate,size"
)


def probe_file(path: str | Path, *, timeout: float = 15.0) -> ProbeResult:
    """
    Probe a media file with ffprobe and return structured ProbeResult.

    Args:
        path: Path to media file.
        timeout: ffprobe subprocess timeout in seconds.

    Returns:
        ProbeResult with all detected metadata. Check .ok for success.
    """
    path = Path(path)
    result = ProbeResult(path=str(path))

    # Check ffprobe availability
    ffprobe_bin = shutil.which("ffprobe")
    if not ffprobe_bin:
        result.error = "ffprobe_not_found"
        return result
    result.available = True

    # Check file exists
    if not path.exists():
        result.error = "file_not_found"
        return result
    result.exists = True
    result.file_size_bytes = path.stat().st_size

    # Run ffprobe
    try:
        proc = subprocess.run(
            [
                ffprobe_bin,
                "-v", "error",
                "-show_entries", _FFPROBE_ENTRIES,
                "-of", "json",
                str(path),
            ],
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired:
        result.error = "ffprobe_timeout"
        return result
    except OSError as exc:
        result.error = f"ffprobe_os_error: {exc}"
        return result

    if proc.returncode != 0:
        result.error = f"ffprobe_failed: {proc.stderr.strip() or proc.returncode}"
        return result

    try:
        payload = json.loads(proc.stdout or "{}")
    except json.JSONDecodeError as exc:
        result.error = f"ffprobe_json_error: {exc}"
        return result

    # Parse format
    fmt = payload.get("format") or {}
    result.container = fmt.get("format_name", "")
    result.duration_sec = round(float(fmt.get("duration") or 0), 3)
    result.bitrate_kbps = int(float(fmt.get("bit_rate") or 0)) // 1000

    # Parse streams
    for stream in payload.get("streams") or []:
        codec_type = stream.get("codec_type", "")

        if codec_type == "video":
            pix_fmt = stream.get("pix_fmt") or ""
            color_primaries = stream.get("color_primaries") or ""
            vs = VideoStream(
                codec=stream.get("codec_name", ""),
                width=int(stream.get("width") or 0),
                height=int(stream.get("height") or 0),
                fps=_parse_fps(stream.get("r_frame_rate") or stream.get("avg_frame_rate") or ""),
                pix_fmt=pix_fmt,
                color_primaries=color_primaries,
                color_transfer=stream.get("color_transfer") or "",
                color_space=_infer_color_space(color_primaries, pix_fmt),
                bit_depth=_infer_bit_depth(pix_fmt),
                profile=stream.get("profile") or "",
                index=int(stream.get("index") or 0),
            )
            result.video_streams.append(vs)

        elif codec_type == "audio":
            codec_name = stream.get("codec_name", "")
            a_bit_depth = _PCM_BIT_DEPTH.get(codec_name, 0)
            if not a_bit_depth:
                a_bit_depth = int(stream.get("bits_per_raw_sample") or stream.get("bits_per_sample") or 0)
            aus = AudioStream(
                codec=codec_name,
                sample_rate=int(stream.get("sample_rate") or 0),
                channels=int(stream.get("channels") or 0),
                bit_depth=a_bit_depth,
                index=int(stream.get("index") or 0),
            )
            result.audio_streams.append(aus)

    # Fill convenience fields from first streams
    if result.video_streams:
        v = result.video_streams[0]
        result.video = v
        result.video_codec = v.codec
        result.width = v.width
        result.height = v.height
        result.fps = v.fps
        result.pix_fmt = v.pix_fmt
        result.color_space = v.color_space
        result.bit_depth = v.bit_depth

    if result.audio_streams:
        a = result.audio_streams[0]
        result.audio = a
        result.audio_codec = a.codec
        result.sample_rate = a.sample_rate
        result.channels = a.channels

    return result


def probe_duration(path: str | Path) -> float:
    """Quick probe — returns duration in seconds, 0.0 on failure."""
    r = probe_file(path, timeout=10.0)
    return r.duration_sec if r.ok else 0.0
