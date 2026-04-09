"""
MARKER_189.2 — AudioScanner: media analysis for audio tracks.
Wraps existing waveform extraction and Whisper STT.
Returns ScanResult with waveform bins, transcript segments, and SignalEdge[].

@status: active
@phase: 189
@depends: cut_ffmpeg_waveform, stt_engine, scan_types
@used_by: cut_routes (scan-matrix-async)
"""
from __future__ import annotations

import logging
import os
import time
from pathlib import Path
from typing import Any

from src.scanners.scan_types import (
    MediaMetadata,
    ScanResult,
    SignalEdge,
    TranscriptSegment,
)
from src.services.cut_ffmpeg_waveform import (
    HAS_FFMPEG,
    build_waveform_with_fallback,
)

logger = logging.getLogger(__name__)

AUDIO_EXTENSIONS = {
    ".mp3", ".wav", ".aiff", ".aif", ".m4a", ".aac",
    ".flac", ".ogg", ".wma", ".opus",
}

# Also scan audio tracks from video files
VIDEO_EXTENSIONS_WITH_AUDIO = {
    ".mp4", ".mov", ".m4v", ".avi", ".mkv", ".webm",
    ".mxf", ".mts", ".m2ts",
}

# Lazy import — mlx_whisper may not be installed
_whisper_stt = None
_whisper_available: bool | None = None


def _get_whisper() -> Any | None:
    """Lazy-load WhisperSTT. Returns None if unavailable."""
    global _whisper_stt, _whisper_available
    if _whisper_available is False:
        return None
    if _whisper_stt is not None:
        return _whisper_stt
    try:
        from src.voice.stt_engine import WhisperSTT
        _whisper_stt = WhisperSTT(model_name="base")
        _whisper_available = True
        return _whisper_stt
    except Exception as exc:
        logger.info("Whisper STT not available: %s", exc)
        _whisper_available = False
        return None


def _transcribe_file(
    media_path: str,
    *,
    max_duration_sec: float = 600.0,
) -> list[TranscriptSegment]:
    """Run Whisper STT on a media file. Returns segments or empty list."""
    whisper = _get_whisper()
    if whisper is None:
        return []
    try:
        result = whisper.transcribe(media_path)
        segments: list[TranscriptSegment] = []
        for seg in result.get("segments", []):
            segments.append(TranscriptSegment(
                start_sec=round(float(seg.get("start", 0)), 3),
                end_sec=round(float(seg.get("end", 0)), 3),
                text=str(seg.get("text", "")).strip(),
                confidence=round(float(seg.get("avg_logprob", 0) + 1.0), 3),
                language=result.get("language", ""),
            ))
        return segments
    except Exception as exc:
        logger.warning("Whisper transcription failed for %s: %s", media_path, exc)
        return []


def _build_audio_edges(
    source_path: str,
    transcript: list[TranscriptSegment],
) -> list[SignalEdge]:
    """Build SignalEdge[] from transcript — semantic edges between utterances."""
    edges: list[SignalEdge] = []
    basename = Path(source_path).stem
    for i in range(len(transcript) - 1):
        a = transcript[i]
        b = transcript[i + 1]
        if not a.text or not b.text:
            continue
        gap = round(b.start_sec - a.end_sec, 3)
        edges.append(SignalEdge(
            source=f"{basename}:utt_{i}",
            target=f"{basename}:utt_{i + 1}",
            channel="temporal",
            evidence=[f"sequential utterances, gap={gap}s"],
            confidence=min(a.confidence, b.confidence),
            weight=0.7,
            source_type="audio",
            target_type="audio",
        ))
    return edges


def scan_audio(
    media_path: str,
    *,
    waveform_bins: int = 120,
    run_stt: bool = True,
    max_stt_duration_sec: float = 600.0,
    metadata: MediaMetadata | None = None,
) -> ScanResult:
    """Run full AudioScanner pipeline on a media file.

    Steps:
    1. Waveform extraction (FFmpeg → RMS bins)
    2. Speech-to-text (Whisper, if available)
    3. SignalEdge generation from transcript

    Args:
        media_path: Path to audio or video file.
        waveform_bins: Number of waveform bins for display.
        run_stt: Whether to run Whisper STT.
        max_stt_duration_sec: Max duration for STT processing.
        metadata: Pre-existing metadata from VideoScanner (avoids re-probe).

    Returns ScanResult with waveform, transcript, and edges.
    """
    t0 = time.monotonic()
    result = ScanResult(scanner_type="audio", source_path=media_path)

    if not os.path.isfile(media_path):
        result.extraction_status = "error"
        result.extraction_error = "file_not_found"
        result.elapsed_sec = time.monotonic() - t0
        return result

    ext = Path(media_path).suffix.lower()
    if ext not in AUDIO_EXTENSIONS and ext not in VIDEO_EXTENSIONS_WITH_AUDIO:
        result.extraction_status = "error"
        result.extraction_error = f"unsupported_extension:{ext}"
        result.elapsed_sec = time.monotonic() - t0
        return result

    result.extraction_status = "running"

    # Use pre-existing metadata if provided (from VideoScanner)
    if metadata:
        result.metadata = metadata
    else:
        result.metadata = MediaMetadata(
            path=media_path,
            media_type="audio" if ext in AUDIO_EXTENSIONS else "video",
            file_size_bytes=os.path.getsize(media_path),
        )

    # Step 1: Waveform
    try:
        bins, degraded, reason = build_waveform_with_fallback(
            media_path, bins=waveform_bins,
        )
        result.waveform_bins = bins
        result.waveform_degraded = degraded
        if degraded and reason:
            logger.info("Waveform degraded for %s: %s", media_path, reason)
    except Exception as exc:
        logger.warning("Waveform extraction failed for %s: %s", media_path, exc)
        result.waveform_bins = [0.0] * waveform_bins
        result.waveform_degraded = True

    # Step 2: STT
    if run_stt:
        try:
            result.transcript = _transcribe_file(
                media_path, max_duration_sec=max_stt_duration_sec,
            )
        except Exception as exc:
            logger.warning("STT failed for %s: %s", media_path, exc)

    # Step 3: Edges
    if result.transcript:
        result.edges = _build_audio_edges(media_path, result.transcript)

    result.extraction_status = "complete"
    result.elapsed_sec = time.monotonic() - t0
    logger.info(
        "AudioScanner complete: %s — %d waveform bins, %d transcript segs, %.1fs",
        Path(media_path).name, len(result.waveform_bins),
        len(result.transcript), result.elapsed_sec,
    )
    return result
