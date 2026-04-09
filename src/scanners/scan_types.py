"""
MARKER_189.2 — Shared types for CUT Import Matrix scanners.
Phase 155 SignalEdge contract + scanner result types.

@status: active
@phase: 189
@depends: dataclasses
@used_by: video_scanner, audio_scanner, cut_routes
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class MediaMetadata:
    """ffprobe-derived metadata for a media file."""
    path: str
    duration_sec: float = 0.0
    codec: str = ""
    width: int = 0
    height: int = 0
    fps: float = 0.0
    sample_rate: int = 0
    channels: int = 0
    timecode_start: str = ""
    file_size_bytes: int = 0
    media_type: str = ""  # "video", "audio", "image", "document"
    container: str = ""   # "mp4", "mov", "wav", etc.


@dataclass
class SceneSegment:
    """A detected scene segment within a media file."""
    segment_id: str
    start_sec: float
    end_sec: float
    duration_sec: float = 0.0
    diff_score: float = 0.0  # boundary confidence
    thumbnail_path: str = ""  # extracted poster frame path


@dataclass
class TranscriptSegment:
    """A speech-to-text segment."""
    start_sec: float
    end_sec: float
    text: str = ""
    speaker: str = ""
    confidence: float = 0.0
    language: str = ""


@dataclass
class SignalEdge:
    """Phase 155 contract: typed edge between two content nodes.

    Channels: structural, semantic, temporal, reference, contextual.
    """
    source: str
    target: str
    channel: str  # structural|semantic|temporal|reference|contextual
    evidence: list[str] = field(default_factory=list)
    confidence: float = 0.0
    weight: float = 0.0
    source_type: str = ""  # video, audio, document, image
    target_type: str = ""
    time_delta_days: float = 0.0


@dataclass
class ScanResult:
    """Unified output from any scanner.

    Contains metadata, segments, waveform, transcript, edges,
    and extraction status.
    """
    scanner_type: str  # "video", "audio", "document", "image"
    source_path: str
    metadata: MediaMetadata | None = None
    segments: list[SceneSegment] = field(default_factory=list)
    transcript: list[TranscriptSegment] = field(default_factory=list)
    waveform_bins: list[float] = field(default_factory=list)
    waveform_degraded: bool = False
    thumbnail_paths: list[str] = field(default_factory=list)
    edges: list[SignalEdge] = field(default_factory=list)
    extraction_status: str = "pending"  # pending|running|complete|error
    extraction_error: str = ""
    elapsed_sec: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        """Serialize to JSON-safe dict."""
        d: dict[str, Any] = {
            "scanner_type": self.scanner_type,
            "source_path": self.source_path,
            "extraction_status": self.extraction_status,
            "extraction_error": self.extraction_error,
            "elapsed_sec": round(self.elapsed_sec, 3),
        }
        if self.metadata:
            d["metadata"] = {
                "path": self.metadata.path,
                "duration_sec": self.metadata.duration_sec,
                "codec": self.metadata.codec,
                "width": self.metadata.width,
                "height": self.metadata.height,
                "fps": self.metadata.fps,
                "sample_rate": self.metadata.sample_rate,
                "channels": self.metadata.channels,
                "timecode_start": self.metadata.timecode_start,
                "file_size_bytes": self.metadata.file_size_bytes,
                "media_type": self.metadata.media_type,
                "container": self.metadata.container,
            }
        if self.segments:
            d["segments"] = [
                {
                    "segment_id": s.segment_id,
                    "start_sec": s.start_sec,
                    "end_sec": s.end_sec,
                    "duration_sec": s.duration_sec,
                    "diff_score": s.diff_score,
                    "thumbnail_path": s.thumbnail_path,
                }
                for s in self.segments
            ]
        if self.transcript:
            d["transcript"] = [
                {
                    "start_sec": t.start_sec,
                    "end_sec": t.end_sec,
                    "text": t.text,
                    "speaker": t.speaker,
                    "confidence": t.confidence,
                    "language": t.language,
                }
                for t in self.transcript
            ]
        if self.waveform_bins:
            d["waveform_bins"] = self.waveform_bins
            d["waveform_degraded"] = self.waveform_degraded
        if self.thumbnail_paths:
            d["thumbnail_paths"] = self.thumbnail_paths
        if self.edges:
            d["edges"] = [
                {
                    "source": e.source,
                    "target": e.target,
                    "channel": e.channel,
                    "evidence": e.evidence,
                    "confidence": e.confidence,
                    "weight": e.weight,
                    "source_type": e.source_type,
                    "target_type": e.target_type,
                }
                for e in self.edges
            ]
        return d
