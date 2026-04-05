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

    # MARKER_B1.5: Codec classification
    codec_family: str = ""       # camera_raw, production, delivery, web, audio_only
    playback_class: str = ""     # native, proxy_recommended, transcode_required, unsupported

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
            "codec_family": self.codec_family,
            "playback_class": self.playback_class,
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
    "bt470m": "BT.470M",          # NTSC 1953
    "ebu3213": "EBU 3213",        # EBU Tech 3213
    "jedec-p22": "JEDEC P22",     # Generic phosphors
    "smpte428": "DCI XYZ",        # SMPTE ST 428 (cinema XYZ)
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
    "gbrap10le": (10, "RGB+A"),
    "gbrap12le": (12, "RGB+A"),
    # Panasonic/Sony camera formats
    "yuv422p10": (10, "4:2:2"),
    "p010le": (10, "4:2:0"),       # HEVC 10-bit (GH5, Sony)
    "p010be": (10, "4:2:0"),
    "p016le": (16, "4:2:0"),
    "p210le": (10, "4:2:2"),
    "p216le": (16, "4:2:2"),
    "p410le": (10, "4:4:4"),
    "p416le": (16, "4:4:4"),
    # DPX / EXR / CinemaDNG
    "rgb48be": (16, "RGB"),
    "rgba64le": (16, "RGBA"),
    "gbrpf32le": (32, "RGB"),      # float
    "gbrapf32le": (32, "RGB+A"),   # float
    # XYZ (DCI cinema)
    "xyz12le": (12, "XYZ"),
    "xyz12be": (12, "XYZ"),
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
# MARKER_B1.5: Codec family + playback class classification
# ---------------------------------------------------------------------------

# codec_name (from ffprobe) → family
_CODEC_FAMILY_MAP: dict[str, str] = {
    # === Camera RAW — needs transcode, huge files ===
    "r3d": "camera_raw",                # RED R3D
    "braw": "camera_raw",               # Blackmagic RAW
    "cdng": "camera_raw",               # CinemaDNG
    "dpx": "camera_raw",                # DPX sequence
    "exr": "camera_raw",                # OpenEXR
    "ari": "camera_raw",                # ARRIRAW
    "rawvideo": "camera_raw",

    # === Production — high quality, often needs proxy ===
    "prores": "production",             # Apple ProRes (all profiles)
    "dnxhd": "production",              # Avid DNxHD / DNxHR
    "ffv1": "production",               # FFV1 lossless
    "huffyuv": "production",            # HuffYUV lossless
    "magicyuv": "production",           # MagicYUV
    "cineform": "production",           # GoPro CineForm
    "cfhd": "production",               # CineForm (alt name)
    "v210": "production",               # Uncompressed 10-bit 4:2:2
    "v410": "production",               # Uncompressed 10-bit 4:4:4
    "png": "production",                # PNG sequence
    "tiff": "production",               # TIFF sequence
    "jpeg2000": "production",           # JPEG 2000 (MXF)
    "j2k": "production",                # JPEG 2000 (alt)

    # === Delivery — playback-ready, good balance ===
    "h264": "delivery",                 # H.264 / AVC
    "h265": "delivery",                 # H.265 / HEVC
    "hevc": "delivery",                 # HEVC (alt name)
    "mpeg4": "delivery",                # MPEG-4 Part 2
    "mpeg2video": "delivery",           # MPEG-2 (broadcast, DVD)
    "mpeg1video": "delivery",           # MPEG-1
    "mjpeg": "delivery",               # Motion JPEG
    "theora": "delivery",

    # === Web — optimized for streaming ===
    "vp8": "web",
    "vp9": "web",
    "av1": "web",
    "libaom-av1": "web",
    "libsvtav1": "web",
    "librav1e": "web",
    "webp": "web",                      # Animated WebP

    # === Audio only ===
    "aac": "audio_only",
    "mp3": "audio_only",
    "pcm_s16le": "audio_only",
    "pcm_s16be": "audio_only",
    "pcm_s24le": "audio_only",
    "pcm_s24be": "audio_only",
    "pcm_s32le": "audio_only",
    "pcm_s32be": "audio_only",
    "pcm_f32le": "audio_only",
    "pcm_f32be": "audio_only",
    "pcm_f64le": "audio_only",
    "pcm_f64be": "audio_only",
    "flac": "audio_only",
    "alac": "audio_only",
    "opus": "audio_only",
    "vorbis": "audio_only",
    "ac3": "audio_only",
    "eac3": "audio_only",
    "dts": "audio_only",
    "truehd": "audio_only",
    "mlp": "audio_only",
    "wmav2": "audio_only",
    "adpcm_ima_wav": "audio_only",
    "pcm_alaw": "audio_only",
    "pcm_mulaw": "audio_only",
}

# Containers where browser/Electron can play natively
_NATIVE_CONTAINERS: set[str] = {
    "mp4", "m4v", "webm", "ogg", "mov",
}

# Containers needing proxy or transcode for smooth playback
_PROXY_CONTAINERS: set[str] = {
    "mxf", "avi", "mkv", "mts", "m2ts", "ts", "gxf",
    "flv", "f4v", "3gp", "3g2", "wmv", "asf",
}

# Camera-specific containers that always need transcode
_TRANSCODE_CONTAINERS: set[str] = {
    "r3d", "braw", "ari", "dpx", "exr", "cin", "dng",
}

# Codecs that are heavy regardless of container
_HEAVY_CODECS: set[str] = {
    "prores", "dnxhd", "cineform", "cfhd", "v210", "v410",
    "huffyuv", "ffv1", "magicyuv", "jpeg2000", "j2k",
    "r3d", "braw", "cdng", "ari", "rawvideo",
}

# Codecs that always need transcode (no WebCodecs / Electron support)
_TRANSCODE_CODECS: set[str] = {
    "r3d", "braw", "cdng", "ari", "rawvideo", "dpx", "exr",
    "v210", "v410", "ffv1", "huffyuv", "magicyuv",
    "jpeg2000", "j2k", "cineform", "cfhd",
}


def _infer_codec_family(codec: str) -> str:
    """Classify codec into family: camera_raw, production, delivery, web, audio_only."""
    return _CODEC_FAMILY_MAP.get(codec, "delivery")


def _infer_playback_class(codec: str, container: str, bit_depth: int) -> str:
    """
    Determine playback class based on codec, container, and bit depth.

    Returns: native, proxy_recommended, transcode_required, unsupported
    """
    # Unsupported / raw → always transcode
    if codec in _TRANSCODE_CODECS:
        return "transcode_required"

    # Check container first
    # Normalize container: "mov,mp4,m4a,3gp,3g2,mj2" → check each part
    container_parts = {c.strip() for c in container.lower().split(",")} if container else set()
    ext_from_container = container_parts & _NATIVE_CONTAINERS

    # Camera containers
    if container_parts & _TRANSCODE_CONTAINERS:
        return "transcode_required"

    # Heavy production codecs → proxy recommended
    if codec in _HEAVY_CODECS:
        return "proxy_recommended"

    # HEVC 10-bit (GH5, Sony etc.) — browser can decode but heavy
    if codec in ("hevc", "h265") and bit_depth >= 10:
        return "proxy_recommended"

    # MPEG-2 in MXF (broadcast) — proxy
    if codec == "mpeg2video" and (container_parts & _PROXY_CONTAINERS):
        return "proxy_recommended"

    # Standard H.264/H.265 8-bit in native container → native
    if codec in ("h264", "h265", "hevc") and ext_from_container:
        return "native"

    # VP8/VP9/AV1 in WebM → native
    if codec in ("vp8", "vp9", "av1", "libaom-av1") and ("webm" in container_parts or "mp4" in container_parts):
        return "native"

    # Non-native container but playable codec → proxy recommended
    if container_parts & _PROXY_CONTAINERS:
        return "proxy_recommended"

    # Fallback: if native container, assume native
    if ext_from_container:
        return "native"

    return "proxy_recommended"


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
        # MARKER_B1.5: classify codec
        result.codec_family = _infer_codec_family(v.codec)
        result.playback_class = _infer_playback_class(v.codec, result.container, v.bit_depth)

    if result.audio_streams:
        a = result.audio_streams[0]
        result.audio = a
        result.audio_codec = a.codec
        result.sample_rate = a.sample_rate
        result.channels = a.channels

    # Audio-only files
    if not result.video_streams and result.audio_streams:
        result.codec_family = "audio_only"
        result.playback_class = "native"

    return result


def probe_duration(path: str | Path) -> float:
    """Quick probe — returns duration in seconds, 0.0 on failure."""
    r = probe_file(path, timeout=10.0)
    return r.duration_sec if r.ok else 0.0


# ---------------------------------------------------------------------------
# MARKER_B24: Camera Log Profile Detection
# ---------------------------------------------------------------------------

# color_transfer value → log profile mapping
_LOG_TRANSFER_MAP: dict[str, dict[str, Any]] = {
    # Exact matches from ffprobe color_transfer field
    "arib-std-b67": {"profile": "HLG", "gamut": "Rec.2020", "camera": "HLG broadcast"},
    "smpte2084": {"profile": "PQ", "gamut": "Rec.2020", "camera": "HDR10/Dolby Vision"},
}

# Substring matches in color_transfer (camera-specific strings)
_LOG_TRANSFER_SUBSTR: list[tuple[str, dict[str, Any]]] = [
    ("slog", {"profile": "S-Log3", "gamut": "S-Gamut3.Cine", "camera": "Sony"}),
    ("vlog", {"profile": "V-Log", "gamut": "V-Gamut", "camera": "Panasonic"}),
    ("logc", {"profile": "ARRI LogC3", "gamut": "ARRI Wide Gamut 3", "camera": "ARRI Alexa"}),
    ("clog", {"profile": "Canon Log 3", "gamut": None, "camera": "Canon"}),
    ("log3g10", {"profile": "Log3G10", "gamut": "REDWideGamutRGB", "camera": "RED"}),
    ("dlog", {"profile": "D-Log", "gamut": None, "camera": "DJI"}),
    ("nlog", {"profile": "N-Log", "gamut": None, "camera": "Nikon"}),
    ("flog", {"profile": "F-Log", "gamut": None, "camera": "Fujifilm"}),
    ("bmdfilm", {"profile": "BMDFilm", "gamut": None, "camera": "Blackmagic"}),
]

# Heuristic: camera model keywords in format tags → log profile
_TAG_CAMERA_HINTS: list[tuple[str, dict[str, Any]]] = [
    ("panasonic", {"profile": "V-Log", "gamut": "V-Gamut", "camera": "Panasonic"}),
    ("gh5", {"profile": "V-Log", "gamut": "V-Gamut", "camera": "Panasonic GH5"}),
    ("gh6", {"profile": "V-Log", "gamut": "V-Gamut", "camera": "Panasonic GH6"}),
    ("lumix", {"profile": "V-Log", "gamut": "V-Gamut", "camera": "Panasonic Lumix"}),
    ("sony", {"profile": "S-Log3", "gamut": "S-Gamut3.Cine", "camera": "Sony"}),
    ("fx6", {"profile": "S-Log3", "gamut": "S-Gamut3.Cine", "camera": "Sony FX6"}),
    ("fx3", {"profile": "S-Log3", "gamut": "S-Gamut3.Cine", "camera": "Sony FX3"}),
    ("a7s", {"profile": "S-Log3", "gamut": "S-Gamut3.Cine", "camera": "Sony A7S"}),
    ("arri", {"profile": "ARRI LogC3", "gamut": "ARRI Wide Gamut 3", "camera": "ARRI"}),
    ("alexa", {"profile": "ARRI LogC3", "gamut": "ARRI Wide Gamut 3", "camera": "ARRI Alexa"}),
    ("canon", {"profile": "Canon Log 3", "gamut": None, "camera": "Canon"}),
    ("eos r5", {"profile": "Canon Log 3", "gamut": None, "camera": "Canon EOS R5"}),
    ("c300", {"profile": "Canon Log 3", "gamut": None, "camera": "Canon C300"}),
    ("red", {"profile": "Log3G10", "gamut": "REDWideGamutRGB", "camera": "RED"}),
    ("dji", {"profile": "D-Log", "gamut": None, "camera": "DJI"}),
    ("mavic", {"profile": "D-Log", "gamut": None, "camera": "DJI Mavic"}),
    ("nikon", {"profile": "N-Log", "gamut": None, "camera": "Nikon"}),
    ("fuji", {"profile": "F-Log", "gamut": None, "camera": "Fujifilm"}),
    ("blackmagic", {"profile": "BMDFilm", "gamut": None, "camera": "Blackmagic"}),
    ("bmpcc", {"profile": "BMDFilm", "gamut": None, "camera": "Blackmagic Pocket"}),
]


def detect_log_profile(probe_result: ProbeResult) -> dict[str, Any]:
    """Detect camera log profile from ProbeResult.

    Returns:
        {
            "detected": bool,
            "profile": str | None,
            "gamut": str | None,
            "camera": str | None,
            "confidence": float (0-1),
            "method": "color_transfer" | "tags" | "heuristic" | None,
            "raw_transfer": str,
            "raw_primaries": str,
        }
    """
    if not probe_result.ok or not probe_result.video:
        return {"detected": False, "profile": None, "confidence": 0.0, "method": None,
                "raw_transfer": "", "raw_primaries": ""}

    v = probe_result.video
    trc = (v.color_transfer or "").lower()
    pri = (v.color_primaries or "").lower()

    result: dict[str, Any] = {
        "detected": False, "profile": None, "gamut": None, "camera": None,
        "confidence": 0.0, "method": None,
        "raw_transfer": trc, "raw_primaries": pri,
    }

    # Method 1: Exact color_transfer match
    if trc in _LOG_TRANSFER_MAP:
        entry = _LOG_TRANSFER_MAP[trc]
        result.update({"detected": True, "confidence": 0.95, "method": "color_transfer", **entry})
        return result

    # Method 2: Substring match in color_transfer
    for substr, entry in _LOG_TRANSFER_SUBSTR:
        if substr in trc:
            result.update({"detected": True, "confidence": 0.9, "method": "color_transfer", **entry})
            return result

    # Method 3: bt2020 transfer + 10-bit → likely log (camera footage)
    if "bt2020" in trc and v.bit_depth >= 10:
        # Check format tags for camera hints
        # (probe_file doesn't expose format tags in ProbeResult, use heuristic)
        result.update({
            "detected": True, "profile": "unknown_log",
            "confidence": 0.4, "method": "heuristic",
            "camera": f"Unknown ({v.codec} {v.bit_depth}-bit bt2020)",
        })
        return result

    # Standard Rec.709 — no log
    if trc in ("bt709", "iec61966-2-1", ""):
        result["confidence"] = 0.0

    return result


def probe_and_detect_log(path: str | Path) -> dict[str, Any]:
    """Full probe + log detection in one call."""
    probe = probe_file(path)
    if not probe.ok:
        return {"success": False, "error": probe.error, "source_path": str(path)}

    detection = detect_log_profile(probe)

    return {
        "success": True,
        "source_path": str(path),
        "metadata": probe.to_dict(),
        "log_detection": detection,
    }
