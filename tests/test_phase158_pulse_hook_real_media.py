from pathlib import Path
import math
import struct
import wave

import pytest

from src.scanners.extractor_registry import ExtractionResult, MediaExtractorRegistry


REAL_AUDIO = Path("/Users/danilagulin/work/teletape_temp/albom/250623_vanpticdanyana_berlin_Punch.m4a")
REAL_VIDEO_DIR = Path("/Users/danilagulin/work/teletape_temp/berlin/video_gen")


def _mk_segments(step: float, count: int) -> list[dict]:
    out: list[dict] = []
    t = 0.0
    for i in range(count):
        out.append(
            {
                "start_sec": round(t, 3),
                "end_sec": round(t + step * 0.6, 3),
                "text": f"seg-{i + 1}",
            }
        )
        t += step
    return out


@pytest.mark.skipif(not REAL_AUDIO.exists(), reason="real audio fixture is unavailable")
def test_phase158_pulse_hook_real_audio_smoke(monkeypatch):
    registry = MediaExtractorRegistry()
    monkeypatch.setenv("VETKA_EXTRACTOR_JEPA_ENABLE", "false")
    monkeypatch.setenv("VETKA_EXTRACTOR_PULSE_ENABLE", "true")
    monkeypatch.setenv("VETKA_EXTRACTOR_PULSE_NATIVE_ENABLE", "true")
    monkeypatch.setenv("VETKA_EXTRACTOR_PULSE_NATIVE_MAX_SEC", "25")
    monkeypatch.setenv("VETKA_EXTRACTOR_PULSE_MAX_LATENCY_MS", "8000")

    extraction = ExtractionResult(
        text="real audio smoke",
        media_chunks=_mk_segments(step=0.52, count=8),
        metadata={"extraction_route": "stt"},
        extractor_id="whisper_stt",
    )
    result = registry._apply_optional_enrichments(
        path=REAL_AUDIO,
        rel_path=str(REAL_AUDIO),
        mime_type="audio/mp4",
        modality="audio",
        extraction=extraction,
    )
    enrich = result.metadata.get("optional_enrichments", {})
    assert "pulse" in enrich
    assert enrich["pulse"]["status"] == "ok"
    payload = enrich["pulse"]["payload"]
    assert payload["mode"] in {"native_audio_v1", "segment_cadence_v1"}
    assert payload["estimated_bpm"] > 0.0
    assert isinstance(payload.get("native_used"), bool)


@pytest.mark.skipif(not REAL_VIDEO_DIR.exists(), reason="real video directory is unavailable")
def test_phase158_pulse_hook_real_video_smoke(monkeypatch):
    clips = sorted([p for p in REAL_VIDEO_DIR.glob("*") if p.suffix.lower() in {".mp4", ".mov", ".mkv", ".webm"}])
    if not clips:
        pytest.skip("no real video clips available")
    clip = clips[0]

    registry = MediaExtractorRegistry()
    monkeypatch.setenv("VETKA_EXTRACTOR_JEPA_ENABLE", "false")
    monkeypatch.setenv("VETKA_EXTRACTOR_PULSE_ENABLE", "true")
    monkeypatch.setenv("VETKA_EXTRACTOR_PULSE_NATIVE_ENABLE", "true")
    monkeypatch.setenv("VETKA_EXTRACTOR_PULSE_NATIVE_MAX_SEC", "25")
    monkeypatch.setenv("VETKA_EXTRACTOR_PULSE_MAX_LATENCY_MS", "8000")

    extraction = ExtractionResult(
        text="real video smoke",
        media_chunks=_mk_segments(step=0.41, count=10),
        metadata={"extraction_route": "stt"},
        extractor_id="whisper_stt",
    )
    result = registry._apply_optional_enrichments(
        path=clip,
        rel_path=str(clip),
        mime_type="video/mp4",
        modality="video",
        extraction=extraction,
    )
    enrich = result.metadata.get("optional_enrichments", {})
    assert "pulse" in enrich
    assert enrich["pulse"]["status"] == "ok"
    payload = enrich["pulse"]["payload"]
    assert payload["mode"] in {"native_audio_v1", "segment_cadence_v1", "metadata_proxy_v1"}
    assert payload["estimated_bpm"] > 0.0


def test_phase158_pulse_hook_native_clicktrack_bpm(tmp_path, monkeypatch):
    bpm_ref = 120.0
    sr = 22050
    duration_sec = 12.0
    beat_sec = 60.0 / bpm_ref
    click_len = int(0.03 * sr)
    total = int(duration_sec * sr)
    data = [0.0] * total
    t = 0.0
    while t < duration_sec:
        start = int(t * sr)
        for i in range(click_len):
            idx = start + i
            if idx >= total:
                break
            env = 1.0 - (i / max(1, click_len))
            data[idx] += 0.7 * env * math.sin(2.0 * math.pi * 880.0 * (i / sr))
        t += beat_sec

    wav_path = tmp_path / "click_120.wav"
    with wave.open(str(wav_path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        frames = bytearray()
        for s in data:
            v = max(-1.0, min(1.0, s))
            frames.extend(struct.pack("<h", int(v * 32767)))
        wf.writeframes(bytes(frames))

    registry = MediaExtractorRegistry()
    monkeypatch.setenv("VETKA_EXTRACTOR_JEPA_ENABLE", "false")
    monkeypatch.setenv("VETKA_EXTRACTOR_PULSE_ENABLE", "true")
    monkeypatch.setenv("VETKA_EXTRACTOR_PULSE_NATIVE_ENABLE", "true")
    monkeypatch.setenv("VETKA_EXTRACTOR_PULSE_NATIVE_MAX_SEC", "20")
    monkeypatch.setenv("VETKA_EXTRACTOR_PULSE_MAX_LATENCY_MS", "8000")

    extraction = ExtractionResult(
        text="click track",
        media_chunks=[],
        metadata={"extraction_route": "stt"},
        extractor_id="whisper_stt",
    )
    result = registry._apply_optional_enrichments(
        path=wav_path,
        rel_path=str(wav_path),
        mime_type="audio/wav",
        modality="audio",
        extraction=extraction,
    )
    payload = result.metadata.get("optional_enrichments", {}).get("pulse", {}).get("payload", {})
    assert payload.get("mode") == "native_audio_v1"
    assert payload.get("native_used") is True
    bpm_est = float(payload.get("estimated_bpm") or 0.0)
    assert 112.0 <= bpm_est <= 128.0
