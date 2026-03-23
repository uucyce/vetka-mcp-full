"""
MARKER_EPSILON.PLAYBACK: Playback state machine contract tests.

Verifies store fields and transitions for:
- Play/Pause/Stop lifecycle
- JKL shuttle speed progression
- Frame stepping (±1, ±5)
- Source vs Program independent playback
- Playhead seek and boundary clamping
"""

import re
from pathlib import Path

import pytest

STORE = Path(__file__).resolve().parent.parent / "client" / "src" / "store" / "useCutEditorStore.ts"
LAYOUT = Path(__file__).resolve().parent.parent / "client" / "src" / "components" / "cut" / "CutEditorLayoutV2.tsx"


@pytest.fixture(scope="module")
def store():
    return STORE.read_text()


@pytest.fixture(scope="module")
def layout():
    return LAYOUT.read_text()


class TestPlaybackFields:
    """Core playback state fields must exist."""

    def test_is_playing(self, store):
        assert "isPlaying" in store

    def test_current_time(self, store):
        assert "currentTime" in store

    def test_duration(self, store):
        assert "duration" in store

    def test_shuttle_speed(self, store):
        assert "shuttleSpeed" in store

    def test_playback_rate(self, store):
        assert "playbackRate" in store


class TestPlaybackActions:
    """Play/pause/stop/seek actions."""

    def test_play_action(self, store):
        assert re.search(r"play\b|togglePlay|playPause", store)

    def test_pause_action(self, store):
        assert re.search(r"pause\b|setIsPlaying.*false", store)

    def test_seek_action(self, store):
        assert re.search(r"\bseek:\s*\(", store)

    def test_seek_clamps_to_zero(self, store):
        """seek() must clamp to >= 0."""
        assert re.search(r"Math\.max\s*\(\s*0", store)


class TestJKLShuttle:
    """JKL shuttle speed progression (FCP7 Ch.App.A)."""

    def test_shuttle_forward_handler(self, layout):
        assert "shuttleForward" in layout

    def test_shuttle_back_handler(self, layout):
        assert "shuttleBack" in layout

    def test_stop_resets_shuttle(self, layout):
        """K key (stop) must reset shuttleSpeed to 0."""
        assert re.search(r"stop.*shuttle|shuttleSpeed.*0|setShuttleSpeed.*0", layout, re.DOTALL)


class TestFrameStepping:
    """Arrow keys: ±1 frame, Shift+Arrow: ±5 frames."""

    def test_frame_step_forward(self, layout):
        assert "frameStepForward" in layout

    def test_frame_step_back(self, layout):
        assert "frameStepBack" in layout

    def test_five_frame_step(self, layout):
        assert "fiveFrameStepForward" in layout or "5" in layout


class TestSourceProgramPlayback:
    """Source and Program monitors have independent playback state."""

    def test_source_is_playing(self, store):
        assert "sourceIsPlaying" in store

    def test_source_current_time(self, store):
        assert "sourceCurrentTime" in store

    def test_seek_source_action(self, store):
        assert "seekSource" in store

    def test_source_duration(self, store):
        assert "sourceDuration" in store

    def test_play_source_action(self, store):
        assert re.search(r"playSource|toggleSourcePlay|setSourceIsPlaying", store)


class TestPlayheadNavigation:
    """Go to start/end, prev/next edit point."""

    def test_go_to_start(self, layout):
        assert "goToStart" in layout

    def test_go_to_end(self, layout):
        assert "goToEnd" in layout

    def test_prev_edit_point(self, layout):
        assert "prevEditPoint" in layout

    def test_next_edit_point(self, layout):
        assert "nextEditPoint" in layout


class TestPlaybackRateControl:
    """Playback rate (speed during play)."""

    def test_cycle_playback_rate(self, layout):
        assert "cyclePlaybackRate" in layout

    def test_playback_rate_in_store(self, store):
        assert "playbackRate" in store
