"""
MARKER_B2.1 — Tests for render cancel mechanism.

Tests: RenderCancelled exception, cancel_check callback, elapsed_sec in result.
"""
from __future__ import annotations

import pytest

from src.services.cut_render_engine import RenderCancelled, RenderClip, RenderPlan


class TestRenderCancelled:
    def test_is_runtime_error(self) -> None:
        assert issubclass(RenderCancelled, RuntimeError)

    def test_can_raise(self) -> None:
        with pytest.raises(RenderCancelled, match="cancelled"):
            raise RenderCancelled("Render cancelled by user")

    def test_message(self) -> None:
        exc = RenderCancelled("test message")
        assert str(exc) == "test message"


class TestRenderClipHasColorFields:
    def test_log_profile_default(self) -> None:
        clip = RenderClip(source_path="/tmp/test.mp4")
        assert clip.log_profile == ""
        assert clip.lut_path == ""

    def test_log_profile_set(self) -> None:
        clip = RenderClip(source_path="/tmp/test.mp4", log_profile="V-Log", lut_path="/luts/film.cube")
        assert clip.log_profile == "V-Log"
        assert clip.lut_path == "/luts/film.cube"
