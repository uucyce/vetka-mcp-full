"""
MARKER_B74 — Optical flow motion intensity analyzer for PULSE scene analysis.

Computes per-frame motion intensity using OpenCV Farneback optical flow.
Output: MotionProfile with motion_intensity samples (0.0=static, 1.0=max motion).

Used by PULSE conductor as VisualBPM.motion_intensity source.

@status: active
@phase: BETA-P2
@task: tb_1774410751_1
"""
from __future__ import annotations

import logging
import math
import os
import subprocess
import tempfile
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger("cut.motion_analyzer")

# Optional OpenCV import — graceful degradation if unavailable
try:
    import cv2
    HAS_CV2 = True
except ImportError:
    cv2 = None  # type: ignore[assignment]
    HAS_CV2 = False
    logger.warning("cv2 (OpenCV) not available — MotionAnalyzer will return stub profiles")

# FFmpeg availability (reuse from existing waveform module)
try:
    from src.services.cut_ffmpeg_waveform import HAS_FFMPEG, FFMPEG
except ImportError:
    HAS_FFMPEG = bool(subprocess.run(
        ["which", "ffmpeg"], capture_output=True
    ).returncode == 0)
    FFMPEG = "ffmpeg" if HAS_FFMPEG else None

# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

_FLOW_RESIZE_W = 320
_FLOW_RESIZE_H = 240


@dataclass
class MotionProfile:
    """
    Full motion characterization of a video clip.

    Fields:
        motion_samples      — per-sample intensity 0.0-1.0
        avg_motion          — mean across all samples
        max_motion          — peak motion
        motion_variance     — how varied the motion is
        cut_density         — estimated cuts per minute (from motion spikes)
        sample_interval_sec — time between samples
        total_duration_sec  — total analyzed duration
        error               — non-empty string if analysis failed
    """
    motion_samples: list[float] = field(default_factory=list)
    avg_motion: float = 0.0
    max_motion: float = 0.0
    motion_variance: float = 0.0
    cut_density: float = 0.0
    sample_interval_sec: float = 0.0
    total_duration_sec: float = 0.0
    error: str = ""

    def to_dict(self) -> dict:
        return {
            "motion_samples": self.motion_samples,
            "avg_motion": round(self.avg_motion, 4),
            "max_motion": round(self.max_motion, 4),
            "motion_variance": round(self.motion_variance, 4),
            "cut_density": round(self.cut_density, 4),
            "sample_interval_sec": round(self.sample_interval_sec, 4),
            "total_duration_sec": round(self.total_duration_sec, 3),
            "error": self.error,
        }


def _empty_profile(error: str = "") -> MotionProfile:
    return MotionProfile(error=error)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _probe_duration(video_path: str) -> Optional[float]:
    """Get video duration via ffprobe."""
    if not FFMPEG:
        return None
    ffprobe = (FFMPEG or "").replace("ffmpeg", "ffprobe")
    if not os.path.isfile(video_path):
        return None
    try:
        result = subprocess.run(
            [
                ffprobe, "-v", "quiet",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                video_path,
            ],
            capture_output=True, text=True, timeout=10.0,
        )
        if result.returncode == 0 and result.stdout.strip():
            return float(result.stdout.strip())
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError, ValueError):
        pass
    return None


def _compute_flow_magnitude(
    prev_gray,  # numpy uint8 gray frame
    curr_gray,  # numpy uint8 gray frame
) -> float:
    """
    Compute mean optical flow magnitude between two grayscale frames.

    Uses Farneback dense optical flow. Returns raw mean magnitude (pixels/frame).
    """
    flow = cv2.calcOpticalFlowFarneback(  # type: ignore[attr-defined]
        prev_gray, curr_gray,
        None,           # flow output
        0.5,            # pyr_scale
        3,              # levels
        15,             # winsize
        3,              # iterations
        5,              # poly_n
        1.2,            # poly_sigma
        0,              # flags
    )
    # flow shape: (H, W, 2) — dx, dy per pixel
    magnitude = (flow[..., 0] ** 2 + flow[..., 1] ** 2) ** 0.5
    return float(magnitude.mean())


def _normalize_samples(samples: list[float], percentile_cap: float = 0.95) -> list[float]:
    """
    Normalize a list of raw flow magnitudes to [0.0, 1.0].

    Uses percentile cap to avoid single outlier frames distorting the scale.
    Returns zeroes if all samples are zero.
    """
    if not samples:
        return []
    max_val = sorted(samples)[int(len(samples) * percentile_cap)]
    if max_val <= 0.0:
        return [0.0] * len(samples)
    return [min(1.0, s / max_val) for s in samples]


def _compute_variance(values: list[float]) -> float:
    if len(values) < 2:
        return 0.0
    mean = sum(values) / len(values)
    return sum((v - mean) ** 2 for v in values) / len(values)


# ---------------------------------------------------------------------------
# Main analyzer class
# ---------------------------------------------------------------------------


class MotionAnalyzer:
    """
    Analyzes optical flow motion intensity in video clips.

    Requires OpenCV (cv2). Falls back to stub profiles when cv2 is unavailable.
    Frames are resized to 320x240 before flow computation for performance.
    """

    def analyze_clip(
        self,
        video_path: str,
        fps: float = 24.0,
        sample_every_n: int = 5,
    ) -> MotionProfile:
        """
        Analyze motion intensity of a video clip using Farneback optical flow.

        Args:
            video_path:     Absolute path to video file.
            fps:            Source FPS (used for timing, not sampling control).
            sample_every_n: Process every Nth frame (default 5 = ~5 samples/sec at 24fps).

        Returns:
            MotionProfile with normalized motion_samples and summary statistics.
            Returns stub profile (all zeros) if cv2 unavailable or file can't be opened.
        """
        if not HAS_CV2:
            logger.warning("cv2 unavailable — returning stub MotionProfile for %s", video_path)
            return _empty_profile(error="cv2_unavailable")

        if not os.path.isfile(video_path):
            logger.error("Video file not found: %s", video_path)
            return _empty_profile(error="file_not_found")

        cap = cv2.VideoCapture(video_path)  # type: ignore[attr-defined]
        if not cap.isOpened():
            logger.error("Cannot open video: %s", video_path)
            return _empty_profile(error="cannot_open_video")

        try:
            return self._run_flow_analysis(cap, video_path, fps, sample_every_n)
        except Exception as exc:
            logger.exception("Motion analysis failed for %s: %s", video_path, exc)
            return _empty_profile(error=f"analysis_error:{exc}")
        finally:
            cap.release()

    def _run_flow_analysis(
        self,
        cap,
        video_path: str,
        fps: float,
        sample_every_n: int,
    ) -> MotionProfile:
        """Core analysis loop — reads sampled frames and computes optical flow."""
        source_fps = cap.get(cv2.CAP_PROP_FPS) or fps  # type: ignore[attr-defined]
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))  # type: ignore[attr-defined]
        total_duration = total_frames / source_fps if source_fps > 0 else 0.0

        if total_frames <= 0:
            # Try ffprobe fallback for duration
            dur = _probe_duration(video_path)
            total_duration = dur or 0.0

        sample_interval_sec = sample_every_n / source_fps if source_fps > 0 else float(sample_every_n) / fps

        raw_magnitudes: list[float] = []
        prev_gray = None
        frame_idx = 0

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            if frame_idx % sample_every_n != 0:
                frame_idx += 1
                continue

            # Resize for performance
            small = cv2.resize(frame, (_FLOW_RESIZE_W, _FLOW_RESIZE_H))  # type: ignore[attr-defined]
            gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)  # type: ignore[attr-defined]

            if prev_gray is not None:
                magnitude = _compute_flow_magnitude(prev_gray, gray)
                raw_magnitudes.append(magnitude)

            prev_gray = gray
            frame_idx += 1

        if not raw_magnitudes:
            return MotionProfile(
                total_duration_sec=round(total_duration, 3),
                sample_interval_sec=round(sample_interval_sec, 4),
                error="no_frames_sampled",
            )

        # Normalize to [0.0, 1.0]
        normalized = _normalize_samples(raw_magnitudes)

        avg_motion = sum(normalized) / len(normalized)
        max_motion = max(normalized)
        variance = _compute_variance(normalized)

        # Estimate cut density from motion spikes
        spike_timestamps = self.detect_motion_spikes(
            MotionProfile(
                motion_samples=normalized,
                sample_interval_sec=sample_interval_sec,
                total_duration_sec=total_duration,
            )
        )
        cut_density = (len(spike_timestamps) / total_duration * 60.0) if total_duration > 0 else 0.0

        return MotionProfile(
            motion_samples=[round(v, 4) for v in normalized],
            avg_motion=round(avg_motion, 4),
            max_motion=round(max_motion, 4),
            motion_variance=round(variance, 4),
            cut_density=round(cut_density, 4),
            sample_interval_sec=round(sample_interval_sec, 4),
            total_duration_sec=round(total_duration, 3),
        )

    def detect_motion_spikes(
        self,
        profile: MotionProfile,
        threshold: float = 0.7,
    ) -> list[float]:
        """
        Return timestamps (seconds) of high-motion moments (potential cut points).

        A spike is any sample where normalized intensity >= threshold.

        Args:
            profile:   MotionProfile from analyze_clip().
            threshold: Spike detection threshold (default 0.7 = top 30%).

        Returns:
            Sorted list of timestamps in seconds.
        """
        if not profile.motion_samples or profile.sample_interval_sec <= 0:
            return []

        timestamps: list[float] = []
        # +1 offset because first sample = diff between frames 0 and N
        for i, intensity in enumerate(profile.motion_samples):
            if intensity >= threshold:
                t = round((i + 1) * profile.sample_interval_sec, 3)
                timestamps.append(t)

        return sorted(timestamps)


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

_analyzer_instance: Optional[MotionAnalyzer] = None


def get_motion_analyzer() -> MotionAnalyzer:
    """Get or create singleton MotionAnalyzer."""
    global _analyzer_instance
    if _analyzer_instance is None:
        _analyzer_instance = MotionAnalyzer()
    return _analyzer_instance
