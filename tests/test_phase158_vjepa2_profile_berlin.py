import statistics
import time
from pathlib import Path

import pytest

from src.knowledge_graph.jepa_integrator import JepaIntegrator


BERLIN_VIDEO_DIR = Path("/Users/danilagulin/work/teletape_temp/berlin/video_gen")


def _pick_clips(limit: int = 8) -> list[Path]:
    clips = sorted([p for p in BERLIN_VIDEO_DIR.glob("*") if p.suffix.lower() in {".mp4", ".mov", ".mkv", ".webm"}])
    return clips[:limit]


def _p95(values: list[float]) -> float:
    if not values:
        return 0.0
    s = sorted(values)
    idx = int(max(0, len(s) * 0.95 - 1))
    return float(s[idx])


@pytest.mark.skipif(not BERLIN_VIDEO_DIR.exists(), reason="Berlin video dataset unavailable")
def test_phase158_vjepa2_profile_berlin_baseline():
    try:
        import cv2  # type: ignore
    except Exception:
        pytest.skip("OpenCV unavailable")

    clips = _pick_clips(limit=24)
    if not clips:
        pytest.skip("No video clips found in Berlin dataset")

    candidates = [
        {"target_fps": 1.5, "window_sec": 6.0, "stride_sec": 2.0},
        {"target_fps": 2.0, "window_sec": 8.0, "stride_sec": 2.0},  # expected baseline
        {"target_fps": 3.0, "window_sec": 8.0, "stride_sec": 1.5},
    ]
    integrator = JepaIntegrator(max_frames=48, embedding_dim=256)

    # Metadata-driven profile evaluation across the dataset (fast/stable).
    clip_meta: list[tuple[int, float, float]] = []
    for clip in clips:
        cap = cv2.VideoCapture(str(clip))
        if not cap.isOpened():
            continue
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps_actual = float(cap.get(cv2.CAP_PROP_FPS) or 0.0)
        cap.release()
        if frame_count <= 0:
            continue
        if fps_actual <= 0:
            fps_actual = 24.0
        duration_sec = float(frame_count) / max(fps_actual, 1e-6)
        clip_meta.append((frame_count, fps_actual, duration_sec))
    if not clip_meta:
        pytest.skip("No readable video metadata in Berlin dataset")

    metrics: list[dict] = []
    for profile in candidates:
        integrator.override_video_profile(**profile)
        frame_counts: list[int] = [
            len(integrator._collect_frame_indices(fc, fps, dur))
            for (fc, fps, dur) in clip_meta
        ]
        coverage = sum(1 for c in frame_counts if c > 0) / max(1, len(frame_counts))
        m = {
            **profile,
            "coverage": coverage,
            "frames_p50": statistics.median(frame_counts),
            "frames_min": min(frame_counts) if frame_counts else 0,
            "frames_max": max(frame_counts) if frame_counts else 0,
        }
        metrics.append(m)

    baseline = next(m for m in metrics if m["target_fps"] == 2.0 and m["window_sec"] == 8.0 and m["stride_sec"] == 2.0)
    assert baseline["coverage"] >= 0.95, baseline
    assert baseline["frames_p50"] >= 10, baseline
    assert baseline["frames_max"] <= 48, baseline

    # Select best profile by utility: frame coverage then density.
    best = max(
        metrics,
        key=lambda m: (
            m["coverage"],
            m["frames_p50"],
        ),
    )
    assert best["coverage"] >= 0.95, metrics

    # Real extraction smoke on one clip under baseline profile.
    smoke_clip = clips[0]
    integrator.override_video_profile(target_fps=2.0, window_sec=8.0, stride_sec=2.0)
    t0 = time.perf_counter()
    frames = integrator.extract_video_frames(str(smoke_clip))
    latency_ms = max(0.0, (time.perf_counter() - t0) * 1000.0)
    assert len(frames) > 0
    assert latency_ms <= 5000.0
