"""
MARKER_B41 — Media & Color sub-router.
Extracted from cut_routes.py to reduce merge conflicts and improve modularity.

Routes: scopes, probes, color pipeline, LUT management, preview decoder,
waveform peaks, codec detection, thumbnail, audio clip-segment.

@status: active
@phase: B41
@task: tb_1774243018_2
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Any

import numpy as np
from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel

from src.services.cut_codec_probe import probe_file
from src.services.cut_project_store import CutProjectStore

media_router = APIRouter(tags=["CUT-Media"])


# ---------------------------------------------------------------------------
# Request Models
# ---------------------------------------------------------------------------


class CutColorApplyRequest(BaseModel):
    source_path: str
    time: float = 0.0
    log_profile: str | None = None
    lut_path: str | None = None
    max_width: int = 540


class CutLutImportRequest(BaseModel):
    sandbox_root: str
    project_id: str
    source_path: str


class CutLutDeleteRequest(BaseModel):
    sandbox_root: str
    project_id: str
    lut_filename: str


class CutLutPreviewRequest(BaseModel):
    source_path: str
    lut_path: str
    time: float = 0.0
    proxy_height: int = 270


class CutPreviewRequest(BaseModel):
    source_path: str
    time: float = 0.0
    proxy_height: int = 540
    log_profile: str | None = None
    lut_path: str | None = None
    jpeg_quality: int = 80
    effects: list[dict[str, Any]] | None = None


# ---------------------------------------------------------------------------
# Routes: Scopes
# ---------------------------------------------------------------------------


@media_router.get("/scopes/analyze")
async def cut_scopes_analyze(
    source_path: str,
    time: float = 0.0,
    scopes: str = "histogram,waveform,vectorscope",
    size: int = 256,
    log_profile: str | None = None,
    lut_path: str | None = None,
) -> dict[str, Any]:
    """
    MARKER_B19 — Video scope analysis: waveform, parade, vectorscope, histogram.
    MARKER_B25 — With optional color pipeline grading.
    """
    from src.services.cut_scope_renderer import analyze_frame_scopes

    size = max(64, min(512, size))
    scope_list = [s.strip() for s in scopes.split(",") if s.strip()]
    valid = {"histogram", "waveform", "vectorscope", "parade", "broadcast_safe"}
    scope_list = [s for s in scope_list if s in valid] or ["histogram", "waveform", "vectorscope"]

    return analyze_frame_scopes(
        source_path=source_path, time_sec=time, scopes=scope_list, scope_size=size,
        log_profile=log_profile, lut_path=lut_path,
    )


# ---------------------------------------------------------------------------
# Routes: Color Pipeline & LUT
# ---------------------------------------------------------------------------


@media_router.post("/color/apply")
async def cut_color_apply(body: CutColorApplyRequest) -> dict[str, Any]:
    """MARKER_B18 — Apply color pipeline (log decode + LUT) to a single frame."""
    from src.services.cut_scope_renderer import extract_frame_rgb
    from src.services.cut_color_pipeline import apply_color_pipeline

    frame = extract_frame_rgb(body.source_path, body.time, max_width=body.max_width)
    if frame is None:
        return {"success": False, "error": "frame_extraction_failed"}

    graded = apply_color_pipeline(frame, log_profile=body.log_profile, lut_path=body.lut_path)
    h, w, _ = graded.shape

    try:
        cmd = [
            "ffmpeg", "-v", "error",
            "-f", "rawvideo", "-pix_fmt", "rgb24",
            "-s", f"{w}x{h}", "-i", "pipe:0",
            "-vframes", "1", "-f", "image2", "-vcodec", "mjpeg", "-q:v", "4", "pipe:1",
        ]
        proc = subprocess.run(cmd, input=graded.tobytes(), capture_output=True, timeout=5)
        if proc.returncode != 0:
            return {"success": False, "error": "jpeg_encode_failed"}
        jpeg_b64 = base64.b64encode(proc.stdout).decode("ascii")
    except Exception as e:
        return {"success": False, "error": str(e)}

    return {
        "success": True, "width": w, "height": h, "format": "jpeg",
        "data": jpeg_b64, "log_profile": body.log_profile, "lut_path": body.lut_path,
    }


@media_router.get("/probe/log-detect")
async def cut_probe_log_detect(source_path: str) -> dict[str, Any]:
    """MARKER_B24 — Auto-detect camera log profile from metadata."""
    from src.services.cut_codec_probe import probe_and_detect_log
    return probe_and_detect_log(source_path)


@media_router.post("/color/lut/import")
async def cut_lut_import(body: CutLutImportRequest) -> dict[str, Any]:
    """MARKER_B23 — Import a .cube LUT file into project storage."""
    from src.services.cut_color_pipeline import import_lut
    store = CutProjectStore(body.sandbox_root)
    project = store.load_project()
    if project is None or str(project.get("project_id") or "") != str(body.project_id):
        return {"success": False, "error": "project_not_found"}
    return import_lut(body.sandbox_root, body.source_path)


@media_router.get("/color/lut/list")
async def cut_lut_list(sandbox_root: str, project_id: str) -> dict[str, Any]:
    """MARKER_B23 — List LUT files in project storage."""
    from src.services.cut_color_pipeline import list_project_luts
    store = CutProjectStore(sandbox_root)
    project = store.load_project()
    if project is None or str(project.get("project_id") or "") != str(project_id):
        return {"success": False, "error": "project_not_found"}
    luts = list_project_luts(sandbox_root)
    return {"success": True, "luts": luts, "count": len(luts)}


@media_router.post("/color/lut/delete")
async def cut_lut_delete(body: CutLutDeleteRequest) -> dict[str, Any]:
    """MARKER_B23 — Delete a LUT from project storage."""
    from src.services.cut_color_pipeline import get_lut_storage_dir
    store = CutProjectStore(body.sandbox_root)
    project = store.load_project()
    if project is None or str(project.get("project_id") or "") != str(body.project_id):
        return {"success": False, "error": "project_not_found"}
    lut_dir = get_lut_storage_dir(body.sandbox_root)
    safe_name = os.path.basename(body.lut_filename)
    path = os.path.join(lut_dir, safe_name)
    if os.path.exists(path):
        os.remove(path)
        return {"success": True, "deleted": safe_name}
    return {"success": False, "error": "lut_not_found"}


@media_router.post("/color/lut/preview")
async def cut_lut_preview(body: CutLutPreviewRequest) -> dict[str, Any]:
    """MARKER_B23 — Preview a LUT on current frame. Returns before/after base64 JPEGs."""
    from src.services.cut_scope_renderer import extract_frame_rgb
    from src.services.cut_color_pipeline import apply_color_pipeline

    frame = extract_frame_rgb(body.source_path, body.time, max_width=body.proxy_height * 16 // 9)
    if frame is None:
        return {"success": False, "error": "frame_extraction_failed"}

    graded = apply_color_pipeline(frame, lut_path=body.lut_path)
    h, w, _ = graded.shape

    def encode_jpeg(f: "np.ndarray") -> str | None:
        try:
            cmd = ["ffmpeg", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
                   "-s", f"{w}x{h}", "-i", "pipe:0", "-vframes", "1",
                   "-f", "image2", "-vcodec", "mjpeg", "-q:v", "6", "pipe:1"]
            proc = subprocess.run(cmd, input=f.tobytes(), capture_output=True, timeout=5)
            if proc.returncode == 0 and proc.stdout:
                return base64.b64encode(proc.stdout).decode("ascii")
        except Exception:
            pass
        return None

    return {
        "success": True, "width": w, "height": h,
        "before": encode_jpeg(frame), "after": encode_jpeg(graded), "lut_path": body.lut_path,
    }


@media_router.get("/color/profiles")
async def cut_color_profiles() -> dict[str, Any]:
    """MARKER_B18 — List available camera log profiles."""
    from src.services.cut_color_pipeline import list_log_profiles
    return {"success": True, "profiles": list_log_profiles()}


# ---------------------------------------------------------------------------
# Routes: Preview Decoder
# ---------------------------------------------------------------------------


@media_router.post("/preview/frame")
async def cut_preview_frame(body: CutPreviewRequest) -> dict[str, Any]:
    """MARKER_B20 — Decode preview frame with full color pipeline."""
    from src.services.cut_preview_decoder import decode_preview_frame, encode_preview_jpeg, apply_numpy_effects
    import time as time_mod

    t0 = time_mod.monotonic()
    frame = decode_preview_frame(body.source_path, body.time, body.proxy_height, body.log_profile, body.lut_path)
    if frame is None:
        return {"success": False, "error": "decode_failed"}

    if body.effects:
        frame_f = frame.astype(np.float32) / 255.0
        frame_f = apply_numpy_effects(frame_f, body.effects)
        frame = (np.clip(frame_f, 0, 1) * 255).astype(np.uint8)

    jpeg = encode_preview_jpeg(frame, body.jpeg_quality)
    if jpeg is None:
        return {"success": False, "error": "encode_failed"}

    elapsed_ms = (time_mod.monotonic() - t0) * 1000
    return {
        "success": True, "width": frame.shape[1], "height": frame.shape[0],
        "format": "jpeg", "data": base64.b64encode(jpeg).decode("ascii"),
        "timing_ms": round(elapsed_ms, 1), "time_sec": body.time,
        "log_profile": body.log_profile, "lut_applied": body.lut_path is not None,
        "effects_applied": len(body.effects or []),
    }


@media_router.get("/preview/info")
async def cut_preview_info() -> dict[str, Any]:
    """MARKER_B20 — Preview decoder capabilities."""
    from src.services.cut_preview_decoder import HAS_PYAV
    return {
        "success": True, "pyav_available": HAS_PYAV,
        "decoder": "pyav" if HAS_PYAV else "ffmpeg",
        "proxy_heights": [360, 540, 720, 1080], "default_proxy_height": 540,
    }


# ---------------------------------------------------------------------------
# Routes: Waveform, Probes, Codecs, Audio Segment, Thumbnail
# ---------------------------------------------------------------------------


@media_router.get("/waveform-peaks")
async def cut_waveform_peaks(source_path: str, bins: int = 128, stereo: bool = False) -> dict[str, Any]:
    """MARKER_B15/B29 — Per-clip waveform peaks (stereo support)."""
    from src.services.cut_ffmpeg_waveform import build_waveform_with_fallback, build_stereo_waveform

    bins = max(16, min(512, bins))
    p = Path(source_path)
    if not p.exists():
        return {"success": False, "error": "file_not_found", "peaks": []}

    if stereo:
        left, right, degraded, reason = build_stereo_waveform(str(p), bins)
        return {
            "success": True, "source_path": str(p), "bins": bins, "stereo": True,
            "peaks_left": left, "peaks_right": right, "peaks": left,
            "degraded": degraded, "degraded_reason": reason,
        }

    peak_bins, degraded, reason = build_waveform_with_fallback(str(p), bins)
    return {
        "success": True, "source_path": str(p), "bins": bins, "stereo": False,
        "peaks": peak_bins, "degraded": degraded, "degraded_reason": reason,
    }


@media_router.get("/codecs/available")
async def cut_codecs_available() -> dict[str, Any]:
    """MARKER_B38 — Detect which codecs are available in the system FFmpeg build."""
    import shutil

    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        return {"success": False, "error": "ffmpeg_not_found"}

    try:
        result = subprocess.run([ffmpeg, "-codecs"], capture_output=True, text=True, timeout=10)
        codec_output = result.stdout or ""
    except Exception:
        return {"success": False, "error": "ffmpeg_codecs_failed"}

    codecs: dict[str, dict[str, Any]] = {}
    our_codecs = {
        "h264": "H.264 / AVC", "hevc": "H.265 / HEVC",
        "prores": "Apple ProRes", "dnxhd": "DNxHD/DNxHR",
        "dvvideo": "DV Video", "av1": "AV1",
        "vp9": "VP9", "aac": "AAC",
        "mp3": "MP3", "flac": "FLAC",
        "pcm_s16le": "PCM 16-bit", "pcm_s24le": "PCM 24-bit",
    }

    for name, label in our_codecs.items():
        can_decode = False
        can_encode = False
        for line in codec_output.split("\n"):
            parts = line.strip().split()
            if len(parts) >= 2 and parts[1] == name:
                flags = parts[0]
                can_decode = "D" in flags
                can_encode = "E" in flags
                break
        codecs[name] = {"label": label, "decode": can_decode, "encode": can_encode}

    version = ""
    try:
        ver_result = subprocess.run([ffmpeg, "-version"], capture_output=True, text=True, timeout=5)
        first_line = (ver_result.stdout or "").split("\n")[0]
        version = first_line.strip()
    except Exception:
        pass

    return {
        "success": True, "ffmpeg_version": version, "codecs": codecs,
        "summary": {
            "total": len(codecs),
            "can_encode": sum(1 for c in codecs.values() if c["encode"]),
            "can_decode": sum(1 for c in codecs.values() if c["decode"]),
        },
    }


@media_router.get("/probe/streams")
async def cut_probe_streams(source_path: str) -> dict[str, Any]:
    """MARKER_B6.5 — Probe all streams in a media file."""
    p = Path(source_path)
    if not p.exists():
        return {"success": False, "error": "file_not_found"}

    result = probe_file(str(p))
    if not result.ok:
        return {"success": False, "error": result.error or "probe_failed"}

    video_streams = [
        {
            "index": vs.index, "type": "video", "codec": vs.codec, "profile": vs.profile,
            "width": vs.width, "height": vs.height, "fps": round(vs.fps, 3),
            "pix_fmt": vs.pix_fmt, "bit_depth": vs.bit_depth,
            "color_primaries": vs.color_primaries, "color_transfer": vs.color_transfer,
        }
        for vs in result.video_streams
    ]
    audio_streams = [
        {
            "index": a_s.index, "type": "audio", "codec": a_s.codec,
            "channels": a_s.channels, "sample_rate": a_s.sample_rate, "bit_depth": a_s.bit_depth,
        }
        for a_s in result.audio_streams
    ]

    return {
        "success": True, "source_path": str(p), "container": result.container,
        "duration_sec": result.duration_sec, "file_size_bytes": result.file_size_bytes,
        "streams": video_streams + audio_streams,
        "video_count": len(video_streams), "audio_count": len(audio_streams),
    }


@media_router.get("/audio/clip-segment")
async def cut_audio_clip_segment(
    source_path: str, start_sec: float = 0.0, duration_sec: float = 10.0,
    sample_rate: int = 44100, channels: int = 2,
) -> Any:
    """MARKER_B5.1 — Extract audio segment as WAV for Web Audio API playback."""
    from src.services.cut_ffmpeg_waveform import extract_audio_wav_segment

    p = Path(source_path)
    if not p.exists():
        return {"success": False, "error": "file_not_found"}

    wav_bytes = extract_audio_wav_segment(
        str(p),
        start_sec=max(0, start_sec),
        duration_sec=min(30.0, max(0.01, duration_sec)),
        sample_rate=max(8000, min(48000, sample_rate)),
        channels=max(1, min(2, channels)),
    )
    if wav_bytes is None:
        return {"success": False, "error": "extraction_failed"}

    return Response(
        content=wav_bytes, media_type="audio/wav",
        headers={"Content-Disposition": 'inline; filename="clip_audio.wav"', "Cache-Control": "public, max-age=3600"},
    )


# ---------------------------------------------------------------------------
# MARKER_B42: Batch audio segment extraction for timeline playback
# ---------------------------------------------------------------------------


class CutAudioBatchSegment(BaseModel):
    clip_id: str = ""
    source_path: str
    start_sec: float = 0.0
    duration_sec: float = 10.0


class CutAudioBatchRequest(BaseModel):
    segments: list[CutAudioBatchSegment]
    sample_rate: int = 44100
    channels: int = 2


@media_router.post("/audio/clip-segments-batch")
async def cut_audio_clip_segments_batch(body: CutAudioBatchRequest) -> dict[str, Any]:
    """
    MARKER_B42 — Batch audio segment extraction for timeline playback.
    Accepts up to 8 segments, extracts in parallel via ThreadPoolExecutor.
    Returns per-clip WAV as base64 JSON (avoids N sequential HTTP requests).
    """
    import asyncio
    from src.services.cut_ffmpeg_waveform import extract_audio_wav_segments_batch

    if not body.segments:
        return {"success": True, "segments": [], "count": 0}

    if len(body.segments) > 8:
        return {"success": False, "error": "max_8_segments_per_batch"}

    seg_dicts = [
        {"clip_id": s.clip_id, "source_path": s.source_path,
         "start_sec": s.start_sec, "duration_sec": s.duration_sec}
        for s in body.segments
    ]

    # Run in thread pool to not block event loop (FFmpeg subprocess calls)
    loop = asyncio.get_running_loop()
    results = await loop.run_in_executor(
        None,
        lambda: extract_audio_wav_segments_batch(
            seg_dicts,
            sample_rate=max(8000, min(48000, body.sample_rate)),
            channels=max(1, min(2, body.channels)),
        ),
    )

    # Encode WAV bytes to base64 for JSON transport
    response_segments = []
    for r in results:
        entry: dict[str, Any] = {"clip_id": r["clip_id"], "success": r["success"]}
        if r["success"] and r.get("wav_bytes"):
            entry["wav_base64"] = base64.b64encode(r["wav_bytes"]).decode("ascii")
            entry["size_bytes"] = len(r["wav_bytes"])
        else:
            entry["wav_base64"] = None
            entry["error"] = r.get("error", "unknown")
        response_segments.append(entry)

    return {
        "success": True,
        "segments": response_segments,
        "count": len(response_segments),
        "success_count": sum(1 for s in response_segments if s["success"]),
    }


@media_router.get("/thumbnail")
async def cut_thumbnail(
    source_path: str, time_sec: float = 1.0, width: int = 320, height: int = 180,
) -> Any:
    """MARKER_B7.3 — Extract single-frame JPEG thumbnail from video."""
    from src.services.cut_render_engine import generate_thumbnail

    p = Path(source_path)
    if not p.exists():
        return {"success": False, "error": "file_not_found"}

    cache_key = hashlib.md5(f"{source_path}|{time_sec}|{width}x{height}".encode()).hexdigest()
    cache_dir = os.path.join(tempfile.gettempdir(), "cut_thumb_cache")
    os.makedirs(cache_dir, exist_ok=True)
    cache_path = os.path.join(cache_dir, f"{cache_key}.jpg")

    if os.path.isfile(cache_path):
        with open(cache_path, "rb") as f:
            return Response(content=f.read(), media_type="image/jpeg",
                          headers={"Cache-Control": "public, max-age=86400"})

    result_path = generate_thumbnail(
        str(p), output_path=cache_path,
        seek_sec=max(0, time_sec), width=max(64, min(1920, width)), height=max(36, min(1080, height)),
    )

    if result_path and os.path.isfile(result_path):
        with open(result_path, "rb") as f:
            return Response(content=f.read(), media_type="image/jpeg",
                          headers={"Cache-Control": "public, max-age=86400"})

    return {"success": False, "error": "thumbnail_generation_failed"}


# ---------------------------------------------------------------------------
# Routes: Audio Loudness
# ---------------------------------------------------------------------------


@media_router.get("/audio/loudness")
async def cut_audio_loudness(source_path: str, standard: str = "ebu_r128") -> dict[str, Any]:
    """MARKER_B17 — Analyze audio loudness (EBU R128 / ATSC A/85 / YouTube / etc)."""
    from src.services.cut_audio_engine import analyze_loudness, LOUDNESS_STANDARDS
    result = analyze_loudness(source_path, standard=standard)
    return {**result.to_dict(), "standards_available": list(LOUDNESS_STANDARDS.keys())}


@media_router.get("/audio/loudness-standards")
async def cut_loudness_standards() -> dict[str, Any]:
    """MARKER_B17 — List available loudness standards with targets."""
    from src.services.cut_audio_engine import LOUDNESS_STANDARDS
    return {"success": True, "standards": LOUDNESS_STANDARDS}


# ---------------------------------------------------------------------------
# MARKER_B46: Audio normalization — LUFS-targeted loudnorm filter for export
# ---------------------------------------------------------------------------


class CutAudioNormalizeRequest(BaseModel):
    source_path: str
    standard: str = "youtube"  # youtube, ebu_r128, atsc_a85, netflix, podcast
    target_lufs: float | None = None  # override standard target


@media_router.post("/audio/normalize")
async def cut_audio_normalize(body: CutAudioNormalizeRequest) -> dict[str, Any]:
    """
    MARKER_B46 — Compute loudnorm filter parameters for LUFS-targeted normalization.

    Analyzes source audio, returns FFmpeg loudnorm filter string ready for
    insertion into render pipeline. Two-pass approach: measure first, then
    return linear normalization params.
    """
    from src.services.cut_audio_engine import analyze_loudness, LOUDNESS_STANDARDS

    p = Path(body.source_path)
    if not p.exists():
        return {"success": False, "error": "file_not_found"}

    # Resolve target LUFS
    std_config = LOUDNESS_STANDARDS.get(body.standard)
    if body.target_lufs is not None:
        target = body.target_lufs
    elif std_config:
        target = std_config["target_lufs"]
    else:
        return {"success": False, "error": f"unknown_standard: {body.standard}",
                "available": list(LOUDNESS_STANDARDS.keys())}

    max_tp = std_config["max_true_peak"] if std_config else -1.0

    # Measure current loudness
    measurement = analyze_loudness(str(p), standard=body.standard)
    if not measurement.success:
        return {"success": False, "error": "analysis_failed",
                "detail": measurement.error}

    # Build loudnorm filter string (FFmpeg two-pass)
    # measured_I, measured_TP, measured_LRA, measured_thresh from first pass
    loudnorm_filter = (
        f"loudnorm=I={target:.1f}"
        f":TP={max_tp:.1f}"
        f":LRA=11"
        f":measured_I={measurement.integrated_lufs:.1f}"
        f":measured_TP={measurement.true_peak_dbfs:.1f}"
        f":measured_LRA={measurement.lra:.1f}"
        f":measured_thresh={measurement.integrated_lufs - 10:.1f}"
        f":linear=true"
    )

    # Compute gain adjustment
    gain_db = target - measurement.integrated_lufs

    return {
        "success": True,
        "source_path": str(p),
        "standard": body.standard,
        "target_lufs": target,
        "max_true_peak": max_tp,
        "current_lufs": measurement.integrated_lufs,
        "current_true_peak": measurement.true_peak_dbfs,
        "current_lra": measurement.lra,
        "gain_db": round(gain_db, 1),
        "loudnorm_filter": loudnorm_filter,
        "compliant": measurement.compliant,
    }


# ---------------------------------------------------------------------------
# MARKER_B47: Media cache management
# ---------------------------------------------------------------------------


@media_router.get("/cache/status")
async def cut_cache_status(sandbox_root: str) -> dict[str, Any]:
    """
    MARKER_B47 — Media cache disk usage: proxies, thumbnails, render artifacts.
    """
    proxy_dir = os.path.join(sandbox_root, "cut_runtime", "proxies")
    render_dir = os.path.join(sandbox_root, "cut_runtime", "renders")
    thumb_dir = os.path.join(tempfile.gettempdir(), "cut_thumb_cache")

    def _dir_stats(d: str) -> dict[str, Any]:
        if not os.path.isdir(d):
            return {"path": d, "exists": False, "file_count": 0, "size_bytes": 0}
        total = 0
        count = 0
        for entry in os.scandir(d):
            if entry.is_file():
                count += 1
                total += entry.stat().st_size
        return {"path": d, "exists": True, "file_count": count, "size_bytes": total}

    proxy_stats = _dir_stats(proxy_dir)
    render_stats = _dir_stats(render_dir)
    thumb_stats = _dir_stats(thumb_dir)
    total_bytes = proxy_stats["size_bytes"] + render_stats["size_bytes"] + thumb_stats["size_bytes"]

    return {
        "success": True,
        "proxies": proxy_stats,
        "renders": render_stats,
        "thumbnails": thumb_stats,
        "total_size_bytes": total_bytes,
        "total_size_mb": round(total_bytes / (1024 * 1024), 1),
    }


class CutCacheCleanupRequest(BaseModel):
    sandbox_root: str
    project_id: str = ""
    clean_proxies: bool = True
    clean_thumbnails: bool = True
    clean_renders: bool = False  # dangerous — default off


@media_router.post("/cache/cleanup")
async def cut_cache_cleanup(body: CutCacheCleanupRequest) -> dict[str, Any]:
    """
    MARKER_B47 — Clean stale cache: orphaned proxies, thumbnails, old renders.
    Uses ProxyWorker.cleanup_stale() for proxy cleanup.
    """
    freed_bytes = 0
    removed_files = 0

    # Proxy cleanup — remove proxies for sources no longer in timeline
    if body.clean_proxies:
        from src.services.cut_proxy_worker import ProxyWorker
        from src.services.cut_project_store import CutProjectStore as _CPS

        store = _CPS(body.sandbox_root)
        timeline = store.load_timeline_state() or {}
        # Collect valid source paths from timeline
        valid_sources: set[str] = set()
        for lane in timeline.get("lanes", []):
            for clip in lane.get("clips", []):
                sp = clip.get("source_path", "")
                if sp:
                    valid_sources.add(sp)

        worker = ProxyWorker(body.sandbox_root)
        proxy_dir = os.path.join(body.sandbox_root, "cut_runtime", "proxies")
        if os.path.isdir(proxy_dir):
            before = sum(e.stat().st_size for e in os.scandir(proxy_dir) if e.is_file())
            worker.cleanup_stale(valid_sources)
            after = sum(e.stat().st_size for e in os.scandir(proxy_dir) if e.is_file())
            freed_bytes += max(0, before - after)

    # Thumbnail cleanup — wipe entire cache (regenerates on demand)
    if body.clean_thumbnails:
        thumb_dir = os.path.join(tempfile.gettempdir(), "cut_thumb_cache")
        if os.path.isdir(thumb_dir):
            for entry in os.scandir(thumb_dir):
                if entry.is_file():
                    try:
                        freed_bytes += entry.stat().st_size
                        os.remove(entry.path)
                        removed_files += 1
                    except OSError:
                        pass

    # Render cleanup — optional, removes all renders
    if body.clean_renders:
        render_dir = os.path.join(body.sandbox_root, "cut_runtime", "renders")
        if os.path.isdir(render_dir):
            for entry in os.scandir(render_dir):
                if entry.is_file():
                    try:
                        freed_bytes += entry.stat().st_size
                        os.remove(entry.path)
                        removed_files += 1
                    except OSError:
                        pass

    return {
        "success": True,
        "freed_bytes": freed_bytes,
        "freed_mb": round(freed_bytes / (1024 * 1024), 1),
        "removed_files": removed_files,
        "cleaned": {
            "proxies": body.clean_proxies,
            "thumbnails": body.clean_thumbnails,
            "renders": body.clean_renders,
        },
    }


# ---------------------------------------------------------------------------
# MARKER_B47: Conform / Relink (FCP7 Ch.44)
# ---------------------------------------------------------------------------


class CutConformCheckRequest(BaseModel):
    sandbox_root: str
    project_id: str = ""
    search_roots: list[str] = []
    auto_relink_threshold: float = 0.0  # MARKER_B49: auto-relink above this score


@media_router.post("/conform/check")
async def cut_conform_check(body: CutConformCheckRequest) -> dict[str, Any]:
    """
    MARKER_B47 + B49 — Check source files, auto-relink above threshold.
    """
    from src.services.cut_conform import check_project_media, relink_media
    store = CutProjectStore(body.sandbox_root)
    timeline = store.load_timeline_state() or {}

    results, auto_remap = check_project_media(
        timeline,
        search_roots=body.search_roots or [],
        auto_relink_threshold=body.auto_relink_threshold,
    )

    # MARKER_B49: Apply auto-relinks if threshold produced remap
    auto_relinked = 0
    if auto_remap:
        relink_result = relink_media(timeline, auto_remap)
        auto_relinked = relink_result["remapped_count"]
        if auto_relinked > 0:
            store.save_timeline_state(timeline)

    online = sum(1 for r in results if r.status == "online")
    offline = sum(1 for r in results if r.status == "offline")
    moved = sum(1 for r in results if r.status == "moved")

    return {
        "success": True,
        "media": [
            {
                "source_path": r.source_path,
                "status": r.status,
                "clip_ids": r.clip_ids,
                "file_size": r.file_size,
                "suggestions": r.suggestions,
            }
            for r in results
        ],
        "summary": {
            "total": len(results),
            "online": online,
            "offline": offline,
            "moved": moved,
            "auto_relinked": auto_relinked,
        },
        "auto_remap": auto_remap,
    }


class CutConformRelinkRequest(BaseModel):
    sandbox_root: str
    project_id: str = ""
    remap: dict[str, str]  # {old_path: new_path}


@media_router.post("/conform/relink")
async def cut_conform_relink(body: CutConformRelinkRequest) -> dict[str, Any]:
    """
    MARKER_B47 — Apply source path remapping across all timeline clips.
    Persists updated timeline to project store.
    """
    from src.services.cut_conform import relink_media
    store = CutProjectStore(body.sandbox_root)
    timeline = store.load_timeline_state()
    if timeline is None:
        return {"success": False, "error": "timeline_not_found"}

    result = relink_media(timeline, body.remap)

    # Persist updated timeline
    if result["remapped_count"] > 0:
        store.save_timeline_state(timeline)

    return {
        "success": True,
        **result,
    }


# ---------------------------------------------------------------------------
# MARKER_B50: Effect defaults + listing API
# ---------------------------------------------------------------------------


@media_router.get("/effects/list")
async def cut_effects_list() -> dict[str, Any]:
    """MARKER_B50 — List all available effect types with params schema."""
    from src.services.cut_effects_engine import list_effect_types
    return {"success": True, "effects": list_effect_types()}


@media_router.get("/effects/defaults/{effect_type}")
async def cut_effects_defaults(effect_type: str) -> dict[str, Any]:
    """MARKER_B50 — Get default params for an effect type."""
    from src.services.cut_effects_engine import get_effect_defaults, EFFECT_DEFS
    if effect_type not in EFFECT_DEFS:
        return {"success": False, "error": f"unknown_effect: {effect_type}"}
    return {"success": True, "effect_type": effect_type, "defaults": get_effect_defaults(effect_type)}


# ---------------------------------------------------------------------------
# MARKER_B52: Mixer state persistence
# ---------------------------------------------------------------------------


class CutMixerStateRequest(BaseModel):
    sandbox_root: str
    project_id: str = ""
    lane_volumes: dict[str, float] = {}
    lane_pans: dict[str, float] = {}
    muted_lanes: list[str] = []
    soloed_lanes: list[str] = []
    master_volume: float = 1.0
    master_pan: float = 0.0


@media_router.post("/mixer/state")
async def cut_mixer_state_save(body: CutMixerStateRequest) -> dict[str, Any]:
    """MARKER_B52 — Persist audio mixer state to project store."""
    store = CutProjectStore(body.sandbox_root)
    timeline = store.load_timeline_state()
    if not timeline:
        return {"success": False, "error": "timeline_not_found"}

    timeline["mixer_state"] = {
        "lane_volumes": body.lane_volumes,
        "lane_pans": body.lane_pans,
        "muted_lanes": body.muted_lanes,
        "soloed_lanes": body.soloed_lanes,
        "master_volume": body.master_volume,
        "master_pan": body.master_pan,
    }
    store.save_timeline_state(timeline)
    return {"success": True, "mixer_state": timeline["mixer_state"]}


@media_router.get("/mixer/state")
async def cut_mixer_state_load(sandbox_root: str) -> dict[str, Any]:
    """MARKER_B52 — Load persisted mixer state."""
    store = CutProjectStore(sandbox_root)
    timeline = store.load_timeline_state()
    if not timeline:
        return {"success": False, "error": "timeline_not_found"}

    mixer = timeline.get("mixer_state", {})
    return {"success": True, "mixer_state": mixer}


# ---------------------------------------------------------------------------
# MARKER_B51: Effect CRUD — apply/remove/reorder/clear per clip
# ---------------------------------------------------------------------------


class CutEffectApplyRequest(BaseModel):
    sandbox_root: str
    clip_id: str
    effect_type: str
    params: dict[str, Any] = {}
    effect_id: str = ""  # auto-generated if empty


class CutEffectRemoveRequest(BaseModel):
    sandbox_root: str
    clip_id: str
    effect_id: str


class CutEffectReorderRequest(BaseModel):
    sandbox_root: str
    clip_id: str
    effect_ids: list[str]  # ordered list of effect IDs


class CutEffectClearRequest(BaseModel):
    sandbox_root: str
    clip_id: str


def _find_clip_in_timeline(timeline: dict[str, Any], clip_id: str) -> tuple[dict | None, dict | None]:
    """Find clip dict + its lane in timeline. Returns (clip, lane) or (None, None)."""
    for lane in timeline.get("lanes", []):
        for clip in lane.get("clips", []):
            if clip.get("clip_id") == clip_id:
                return clip, lane
    return None, None


@media_router.post("/effects/apply")
async def cut_effects_apply(body: CutEffectApplyRequest) -> dict[str, Any]:
    """MARKER_B51 — Add effect to clip. Persists to project store."""
    from src.services.cut_effects_engine import EFFECT_DEFS, get_effect_defaults
    from uuid import uuid4

    if body.effect_type not in EFFECT_DEFS:
        return {"success": False, "error": f"unknown_effect: {body.effect_type}"}

    store = CutProjectStore(body.sandbox_root)
    timeline = store.load_timeline_state()
    if not timeline:
        return {"success": False, "error": "timeline_not_found"}

    clip, lane = _find_clip_in_timeline(timeline, body.clip_id)
    if not clip:
        return {"success": False, "error": "clip_not_found"}

    # Build effect entry
    defaults = get_effect_defaults(body.effect_type)
    merged_params = {**defaults, **body.params}
    effect_id = body.effect_id or f"fx_{uuid4().hex[:8]}"

    effect_entry = {
        "effect_id": effect_id,
        "type": body.effect_type,
        "enabled": True,
        "params": merged_params,
    }

    # Ensure effects structure
    effects = clip.setdefault("effects", {})
    video_effects = effects.setdefault("video_effects", [])
    video_effects.append(effect_entry)

    store.save_timeline_state(timeline)
    return {"success": True, "effect_id": effect_id, "clip_id": body.clip_id, "effect": effect_entry}


@media_router.post("/effects/remove")
async def cut_effects_remove(body: CutEffectRemoveRequest) -> dict[str, Any]:
    """MARKER_B51 — Remove specific effect from clip by effect_id."""
    store = CutProjectStore(body.sandbox_root)
    timeline = store.load_timeline_state()
    if not timeline:
        return {"success": False, "error": "timeline_not_found"}

    clip, _ = _find_clip_in_timeline(timeline, body.clip_id)
    if not clip:
        return {"success": False, "error": "clip_not_found"}

    effects = clip.get("effects", {})
    video_effects = effects.get("video_effects", [])
    before_count = len(video_effects)
    effects["video_effects"] = [e for e in video_effects if e.get("effect_id") != body.effect_id]
    removed = before_count - len(effects["video_effects"])

    if removed > 0:
        store.save_timeline_state(timeline)
    return {"success": True, "removed": removed, "clip_id": body.clip_id}


@media_router.post("/effects/reorder")
async def cut_effects_reorder(body: CutEffectReorderRequest) -> dict[str, Any]:
    """MARKER_B51 — Reorder effects on clip. Effect order matters for render."""
    store = CutProjectStore(body.sandbox_root)
    timeline = store.load_timeline_state()
    if not timeline:
        return {"success": False, "error": "timeline_not_found"}

    clip, _ = _find_clip_in_timeline(timeline, body.clip_id)
    if not clip:
        return {"success": False, "error": "clip_not_found"}

    effects = clip.get("effects", {})
    video_effects = effects.get("video_effects", [])

    # Build index by effect_id
    by_id = {e["effect_id"]: e for e in video_effects if "effect_id" in e}
    reordered = [by_id[eid] for eid in body.effect_ids if eid in by_id]
    # Append any effects not in the order list at the end
    remaining = [e for e in video_effects if e.get("effect_id") not in set(body.effect_ids)]
    effects["video_effects"] = reordered + remaining

    store.save_timeline_state(timeline)
    return {"success": True, "clip_id": body.clip_id, "order": [e["effect_id"] for e in effects["video_effects"]]}


@media_router.post("/effects/clear")
async def cut_effects_clear(body: CutEffectClearRequest) -> dict[str, Any]:
    """MARKER_B51 — Clear all effects from clip."""
    store = CutProjectStore(body.sandbox_root)
    timeline = store.load_timeline_state()
    if not timeline:
        return {"success": False, "error": "timeline_not_found"}

    clip, _ = _find_clip_in_timeline(timeline, body.clip_id)
    if not clip:
        return {"success": False, "error": "clip_not_found"}

    clip["effects"] = {"video_effects": [], "audio_effects": []}
    store.save_timeline_state(timeline)
    return {"success": True, "clip_id": body.clip_id}


# ---------------------------------------------------------------------------
# MARKER_B48: Multicam Sync Engine (FCP7 Ch.46-47)
# ---------------------------------------------------------------------------

# In-memory store for multicam clips (persisted per-session)
_multicam_clips: dict[str, dict[str, Any]] = {}


class CutMulticamCreateRequest(BaseModel):
    source_paths: list[str]
    sync_method: str = "waveform"  # waveform | timecode | marker
    reference_index: int = 0
    marker_times: list[float] = []  # for sync_method=marker
    fps: float = 25.0              # for timecode sync
    max_lag_sec: float = 30.0      # for waveform sync


@media_router.post("/multicam/create")
async def cut_multicam_create(body: CutMulticamCreateRequest) -> dict[str, Any]:
    """
    MARKER_B48 — Create multicam clip from multiple camera angles.
    Syncs by waveform (cross-correlation), timecode, or markers.
    Returns multicam_clip_id with aligned offsets per angle.
    """
    import asyncio
    from src.services.cut_multicam_sync import (
        sync_by_waveform,
        sync_by_timecode,
        sync_by_markers,
    )
    from datetime import datetime, timezone

    if len(body.source_paths) < 2:
        return {"success": False, "error": "need_at_least_2_sources"}

    # Validate files exist
    missing = [p for p in body.source_paths if not os.path.isfile(p)]
    if missing:
        return {"success": False, "error": "files_not_found", "missing": missing}

    loop = asyncio.get_running_loop()

    if body.sync_method == "waveform":
        multicam = await loop.run_in_executor(None, lambda: sync_by_waveform(
            body.source_paths,
            reference_index=body.reference_index,
            max_lag_sec=body.max_lag_sec,
        ))
    elif body.sync_method == "timecode":
        multicam = await loop.run_in_executor(None, lambda: sync_by_timecode(
            body.source_paths, fps=body.fps,
        ))
    elif body.sync_method == "marker":
        if len(body.marker_times) != len(body.source_paths):
            return {"success": False, "error": "marker_times_count_mismatch"}
        multicam = sync_by_markers(body.source_paths, body.marker_times)
    else:
        return {"success": False, "error": f"unknown_sync_method: {body.sync_method}"}

    multicam.created_at = datetime.now(timezone.utc).isoformat()

    # Store in memory
    mc_dict = multicam.to_dict()
    _multicam_clips[multicam.multicam_id] = mc_dict

    return {"success": True, **mc_dict}


@media_router.get("/multicam/{multicam_id}")
async def cut_multicam_get(multicam_id: str) -> dict[str, Any]:
    """MARKER_B48 — Get multicam clip state."""
    mc = _multicam_clips.get(multicam_id)
    if not mc:
        return {"success": False, "error": "multicam_not_found"}
    return {"success": True, **mc}


class CutMulticamSwitchRequest(BaseModel):
    multicam_id: str
    angle_index: int
    switch_time_sec: float
    duration_sec: float = 5.0


@media_router.post("/multicam/switch")
async def cut_multicam_switch(body: CutMulticamSwitchRequest) -> dict[str, Any]:
    """
    MARKER_B48 — Generate a timeline clip for switching to a specific angle.
    Returns clip dict ready for timeline insertion (FCP7 Ch.47).
    """
    from src.services.cut_multicam_sync import MulticamClip, MulticamAngle, build_multicam_switch_clip

    mc_dict = _multicam_clips.get(body.multicam_id)
    if not mc_dict:
        return {"success": False, "error": "multicam_not_found"}

    # Reconstruct MulticamClip from dict
    multicam = MulticamClip(
        multicam_id=mc_dict["multicam_id"],
        angles=[MulticamAngle(**a) for a in mc_dict["angles"]],
        sync_method=mc_dict["sync_method"],
        reference_index=mc_dict["reference_index"],
        total_duration_sec=mc_dict["total_duration_sec"],
    )

    try:
        clip = build_multicam_switch_clip(
            multicam, body.angle_index, body.switch_time_sec, body.duration_sec,
        )
    except ValueError as e:
        return {"success": False, "error": str(e)}

    return {"success": True, "clip": clip}
