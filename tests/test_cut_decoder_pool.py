"""
MARKER_DECODER_POOL — Tests for FFmpegDecoderPool.

Tests: dimension caching, LRU eviction, idle reaping, pool lifecycle,
graceful fallback, thread safety.

Uses mock subprocess (no real FFmpeg needed for unit tests).
"""
from __future__ import annotations

import sys
import threading
import time
from types import ModuleType
from unittest.mock import MagicMock, patch

import pytest

# Ensure numpy stub is available for import
if "numpy" not in sys.modules:
    _np_stub = ModuleType("numpy")
    _np_stub.ndarray = type("ndarray", (), {})  # type: ignore[attr-defined]
    _np_stub.uint8 = "uint8"  # type: ignore[attr-defined]
    _np_stub.float32 = "float32"  # type: ignore[attr-defined]
    _np_stub.full = MagicMock()  # type: ignore[attr-defined]
    _np_stub.zeros = MagicMock()  # type: ignore[attr-defined]
    _np_stub.frombuffer = MagicMock()  # type: ignore[attr-defined]
    _np_stub.clip = MagicMock()  # type: ignore[attr-defined]
    sys.modules["numpy"] = _np_stub

from src.services.cut_preview_decoder import (
    FFmpegDecoderPool,
    _DecoderEntry,
    get_decoder_pool,
)


# ── _DecoderEntry ──


class TestDecoderEntry:
    def test_touch_updates_last_used(self) -> None:
        entry = _DecoderEntry("/a.mp4", 1920, 1080)
        old = entry.last_used
        time.sleep(0.01)
        entry.touch()
        assert entry.last_used > old

    def test_stores_dimensions(self) -> None:
        entry = _DecoderEntry("/a.mp4", 3840, 2160)
        assert entry.width == 3840
        assert entry.height == 2160
        assert entry.source_path == "/a.mp4"


# ── FFmpegDecoderPool — cache behavior ──


class TestPoolCaching:
    def setup_method(self) -> None:
        self.pool = FFmpegDecoderPool(max_size=4, idle_timeout_sec=30.0)

    @patch("src.services.cut_preview_decoder._probe_dimensions", return_value=(1920, 1080))
    def test_caches_dimensions_after_first_probe(self, mock_probe: MagicMock) -> None:
        self.pool._get_or_create("/a.mp4")
        self.pool._get_or_create("/a.mp4")
        # Should only probe once
        assert mock_probe.call_count == 1

    @patch("src.services.cut_preview_decoder._probe_dimensions", return_value=(1920, 1080))
    def test_size_reflects_cached_files(self, mock_probe: MagicMock) -> None:
        self.pool._get_or_create("/a.mp4")
        self.pool._get_or_create("/b.mp4")
        assert self.pool.size == 2
        assert set(self.pool.cached_files) == {"/a.mp4", "/b.mp4"}

    @patch("src.services.cut_preview_decoder._probe_dimensions", return_value=None)
    def test_probe_failure_returns_none(self, mock_probe: MagicMock) -> None:
        entry = self.pool._get_or_create("/missing.mp4")
        assert entry is None
        assert self.pool.size == 0


# ── LRU eviction ──


class TestPoolEviction:
    def setup_method(self) -> None:
        self.pool = FFmpegDecoderPool(max_size=2, idle_timeout_sec=60.0)

    @patch("src.services.cut_preview_decoder._probe_dimensions", return_value=(1920, 1080))
    def test_evicts_lru_when_full(self, mock_probe: MagicMock) -> None:
        self.pool._get_or_create("/a.mp4")
        time.sleep(0.01)
        self.pool._get_or_create("/b.mp4")
        time.sleep(0.01)
        # Adding /c.mp4 should evict /a.mp4 (oldest)
        self.pool._get_or_create("/c.mp4")
        assert self.pool.size == 2
        assert "/a.mp4" not in self.pool.cached_files
        assert "/b.mp4" in self.pool.cached_files
        assert "/c.mp4" in self.pool.cached_files

    @patch("src.services.cut_preview_decoder._probe_dimensions", return_value=(1920, 1080))
    def test_touch_prevents_eviction(self, mock_probe: MagicMock) -> None:
        self.pool._get_or_create("/a.mp4")
        time.sleep(0.01)
        self.pool._get_or_create("/b.mp4")
        time.sleep(0.01)
        # Touch /a.mp4 so /b.mp4 is now oldest
        entry_a = self.pool._get_or_create("/a.mp4")
        entry_a.touch()
        time.sleep(0.01)
        # Adding /c.mp4 should evict /b.mp4
        self.pool._get_or_create("/c.mp4")
        assert "/a.mp4" in self.pool.cached_files
        assert "/b.mp4" not in self.pool.cached_files

    @patch("src.services.cut_preview_decoder._probe_dimensions", return_value=(1920, 1080))
    def test_manual_evict(self, mock_probe: MagicMock) -> None:
        self.pool._get_or_create("/a.mp4")
        assert self.pool.evict("/a.mp4") is True
        assert self.pool.evict("/a.mp4") is False
        assert self.pool.size == 0


# ── Idle reaping ──


class TestPoolReaping:
    def setup_method(self) -> None:
        self.pool = FFmpegDecoderPool(max_size=4, idle_timeout_sec=0.05)

    @patch("src.services.cut_preview_decoder._probe_dimensions", return_value=(1920, 1080))
    def test_reaps_expired_entries(self, mock_probe: MagicMock) -> None:
        self.pool._get_or_create("/a.mp4")
        assert self.pool.size == 1
        time.sleep(0.06)  # wait past idle timeout
        # Reaping happens on next _get_or_create
        self.pool._get_or_create("/b.mp4")
        assert "/a.mp4" not in self.pool.cached_files
        assert "/b.mp4" in self.pool.cached_files


# ── Pool decode with mocked subprocess ──


class TestPoolDecode:
    def setup_method(self) -> None:
        self.pool = FFmpegDecoderPool(max_size=4, idle_timeout_sec=30.0)

    @patch("src.services.cut_preview_decoder.subprocess.run")
    @patch("src.services.cut_preview_decoder._probe_dimensions", return_value=(160, 90))
    def test_decode_returns_frame(self, mock_probe: MagicMock, mock_run: MagicMock) -> None:
        # Create raw bytes of correct size (160x90x3)
        raw = b"\x00" * (160 * 90 * 3)
        mock_run.return_value = MagicMock(returncode=0, stdout=raw)

        # Mock np.frombuffer chain
        mock_array = MagicMock()
        mock_array.reshape.return_value.copy.return_value = mock_array
        mock_array.shape = (90, 160, 3)
        with patch("src.services.cut_preview_decoder.np.frombuffer", return_value=mock_array):
            frame = self.pool.decode("/a.mp4", 1.0, proxy_height=540)
            assert frame is not None

    @patch("src.services.cut_preview_decoder.subprocess.run")
    @patch("src.services.cut_preview_decoder._probe_dimensions", return_value=(160, 90))
    def test_decode_caches_across_calls(self, mock_probe: MagicMock, mock_run: MagicMock) -> None:
        import numpy as np
        raw = np.zeros((90, 160, 3), dtype=np.uint8).tobytes()
        mock_run.return_value = MagicMock(returncode=0, stdout=raw)

        self.pool.decode("/a.mp4", 0.0, proxy_height=540)
        self.pool.decode("/a.mp4", 1.0, proxy_height=540)
        # Probe only once, subprocess twice (one per frame)
        assert mock_probe.call_count == 1
        assert mock_run.call_count == 2

    @patch("src.services.cut_preview_decoder._probe_dimensions", return_value=(160, 90))
    def test_decode_subprocess_error_returns_none(self, mock_probe: MagicMock) -> None:
        with patch("src.services.cut_preview_decoder.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=1, stdout=b"")
            frame = self.pool.decode("/a.mp4", 0.0)
            assert frame is None

    @patch("src.services.cut_preview_decoder._probe_dimensions", return_value=None)
    def test_decode_probe_failure_returns_none(self, mock_probe: MagicMock) -> None:
        frame = self.pool.decode("/missing.mp4", 0.0)
        assert frame is None


# ── Pool lifecycle ──


class TestPoolLifecycle:
    @patch("src.services.cut_preview_decoder._probe_dimensions", return_value=(1920, 1080))
    def test_clear_empties_pool(self, mock_probe: MagicMock) -> None:
        pool = FFmpegDecoderPool(max_size=4)
        pool._get_or_create("/a.mp4")
        pool._get_or_create("/b.mp4")
        pool.clear()
        assert pool.size == 0

    @patch("src.services.cut_preview_decoder._probe_dimensions", return_value=(1920, 1080))
    def test_stats_returns_info(self, mock_probe: MagicMock) -> None:
        pool = FFmpegDecoderPool(max_size=4, idle_timeout_sec=30.0)
        pool._get_or_create("/a.mp4")
        s = pool.stats()
        assert s["size"] == 1
        assert s["max_size"] == 4
        assert len(s["entries"]) == 1
        assert s["entries"][0]["dimensions"] == "1920x1080"


# ── Thread safety ──


class TestPoolThreadSafety:
    @patch("src.services.cut_preview_decoder._probe_dimensions", return_value=(1920, 1080))
    def test_concurrent_access_no_crash(self, mock_probe: MagicMock) -> None:
        pool = FFmpegDecoderPool(max_size=4, idle_timeout_sec=30.0)
        errors = []

        def worker(path: str) -> None:
            try:
                pool._get_or_create(path)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker, args=(f"/{i}.mp4",)) for i in range(8)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        assert pool.size <= 4  # max_size respected


# ── Singleton ──


class TestGetDecoderPool:
    def test_returns_same_instance(self) -> None:
        pool1 = get_decoder_pool()
        pool2 = get_decoder_pool()
        assert pool1 is pool2
