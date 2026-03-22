"""
MARKER_B2 — Tests for auto_select_proxy_spec (ProbeResult → proxy decision).

Tests the decision matrix:
  transcode_required → 480p
  proxy_recommended + 4K → 480p
  proxy_recommended + 1080p → 720p
  proxy_recommended + SD → skip
  native + 4K → 720p
  native + 1080p → skip
  audio_only → skip
  unsupported → 480p
  probe_failed → skip
"""
from __future__ import annotations

from types import SimpleNamespace

import pytest

from src.services.cut_proxy_worker import (
    PROXY_480P,
    PROXY_720P,
    AutoProxyDecision,
    auto_select_proxy_spec,
)


def _mock_probe(
    *,
    ok: bool = True,
    playback_class: str = "native",
    height: int = 1080,
    codec_family: str = "delivery",
    resolution_label: str = "1080p",
    file_size_bytes: int = 100_000_000,
    video_codec: str = "h264",
) -> SimpleNamespace:
    """Create a minimal mock ProbeResult."""
    return SimpleNamespace(
        ok=ok,
        playback_class=playback_class,
        height=height,
        codec_family=codec_family,
        resolution_label=resolution_label,
        file_size_bytes=file_size_bytes,
        video_codec=video_codec,
    )


# ── transcode_required → always 480p ──


class TestTranscodeRequired:
    def test_raw_4k(self) -> None:
        probe = _mock_probe(playback_class="transcode_required", height=2160, codec_family="camera_raw", resolution_label="4K")
        d = auto_select_proxy_spec(probe)
        assert d.needs_proxy is True
        assert d.spec is PROXY_480P
        assert "transcode_required" in d.reason

    def test_raw_1080p(self) -> None:
        probe = _mock_probe(playback_class="transcode_required", height=1080, codec_family="camera_raw", resolution_label="1080p")
        d = auto_select_proxy_spec(probe)
        assert d.needs_proxy is True
        assert d.spec is PROXY_480P

    def test_raw_720p(self) -> None:
        probe = _mock_probe(playback_class="transcode_required", height=720, codec_family="camera_raw", resolution_label="720p")
        d = auto_select_proxy_spec(probe)
        assert d.needs_proxy is True
        assert d.spec is PROXY_480P


# ── proxy_recommended ──


class TestProxyRecommended:
    def test_4k_prores(self) -> None:
        probe = _mock_probe(playback_class="proxy_recommended", height=2160, codec_family="production", resolution_label="4K")
        d = auto_select_proxy_spec(probe)
        assert d.needs_proxy is True
        assert d.spec is PROXY_480P
        assert "4K" in d.reason

    def test_6k_prores(self) -> None:
        probe = _mock_probe(playback_class="proxy_recommended", height=2880, codec_family="production", resolution_label="6K")
        d = auto_select_proxy_spec(probe)
        assert d.needs_proxy is True
        assert d.spec is PROXY_480P

    def test_1080p_hevc_10bit(self) -> None:
        probe = _mock_probe(playback_class="proxy_recommended", height=1080, resolution_label="1080p")
        d = auto_select_proxy_spec(probe)
        assert d.needs_proxy is True
        assert d.spec is PROXY_720P

    def test_720p_heavy_skip(self) -> None:
        probe = _mock_probe(playback_class="proxy_recommended", height=720, resolution_label="720p")
        d = auto_select_proxy_spec(probe)
        assert d.needs_proxy is False
        assert d.spec is None

    def test_sd_heavy_skip(self) -> None:
        probe = _mock_probe(playback_class="proxy_recommended", height=480, resolution_label="SD")
        d = auto_select_proxy_spec(probe)
        assert d.needs_proxy is False


# ── native ──


class TestNative:
    def test_4k_h264_needs_proxy(self) -> None:
        probe = _mock_probe(playback_class="native", height=2160, resolution_label="4K")
        d = auto_select_proxy_spec(probe)
        assert d.needs_proxy is True
        assert d.spec is PROXY_720P

    def test_1080p_h264_skip(self) -> None:
        probe = _mock_probe(playback_class="native", height=1080, resolution_label="1080p")
        d = auto_select_proxy_spec(probe)
        assert d.needs_proxy is False

    def test_720p_h264_skip(self) -> None:
        probe = _mock_probe(playback_class="native", height=720, resolution_label="720p")
        d = auto_select_proxy_spec(probe)
        assert d.needs_proxy is False


# ── Edge cases ──


class TestEdgeCases:
    def test_audio_only(self) -> None:
        probe = _mock_probe(codec_family="audio_only", playback_class="native", height=0, resolution_label="")
        d = auto_select_proxy_spec(probe)
        assert d.needs_proxy is False
        assert "audio_only" in d.reason

    def test_unsupported(self) -> None:
        probe = _mock_probe(playback_class="unsupported", height=1080)
        d = auto_select_proxy_spec(probe)
        assert d.needs_proxy is True
        assert d.spec is PROXY_480P

    def test_probe_failed(self) -> None:
        probe = _mock_probe(ok=False)
        d = auto_select_proxy_spec(probe)
        assert d.needs_proxy is False
        assert "probe_failed" in d.reason

    def test_unknown_playback_class(self) -> None:
        probe = _mock_probe(playback_class="something_new", height=1080)
        d = auto_select_proxy_spec(probe)
        assert d.needs_proxy is False

    def test_returns_auto_proxy_decision(self) -> None:
        probe = _mock_probe()
        d = auto_select_proxy_spec(probe)
        assert isinstance(d, AutoProxyDecision)
        assert d.playback_class == "native"
        assert d.source_resolution == "1080p"
