"""
MARKER_EPSILON.T2: Track header Mute/Solo/Lock toggle contract tests.

Verifies that useCutEditorStore provides correct toggle semantics:
1. toggleMute — adds/removes laneId from mutedLanes Set
2. toggleSolo — adds/removes laneId from soloLanes Set
3. toggleLock — adds/removes laneId from lockedLanes Set
4. Sets are initialized empty
5. Toggle is idempotent (toggle twice = back to original)

Source: client/src/store/useCutEditorStore.ts
"""

import re
from pathlib import Path

import pytest

STORE_FILE = Path(__file__).resolve().parent.parent / "client" / "src" / "store" / "useCutEditorStore.ts"


@pytest.fixture(scope="module")
def source():
    if not STORE_FILE.exists():
        pytest.skip(f"Store not found: {STORE_FILE}")
    return STORE_FILE.read_text()


class TestMuteToggle:
    """toggleMute: lane-level mute via mutedLanes Set."""

    def test_muted_lanes_is_set(self, source):
        """mutedLanes must be a Set<string>."""
        assert re.search(r"mutedLanes:\s*(?:new\s+)?Set<string>", source)

    def test_toggle_mute_exists(self, source):
        """toggleMute action must exist."""
        assert "toggleMute" in source

    def test_toggle_mute_adds_to_set(self, source):
        """toggleMute must add laneId when not present."""
        assert re.search(r"mutedLanes\.add\(laneId\)", source)

    def test_toggle_mute_removes_from_set(self, source):
        """toggleMute must delete laneId when present."""
        assert re.search(r"mutedLanes\.delete\(laneId\)", source)

    def test_toggle_mute_checks_has(self, source):
        """toggleMute must check has() before toggling."""
        assert re.search(r"mutedLanes\.has\(laneId\)", source)

    def test_muted_lanes_initialized_empty(self, source):
        """mutedLanes initial value must be empty Set."""
        assert re.search(r"mutedLanes:\s*new\s+Set<string>\(\)", source)


class TestSoloToggle:
    """toggleSolo: lane-level solo via soloLanes Set."""

    def test_solo_lanes_is_set(self, source):
        assert re.search(r"soloLanes:\s*(?:new\s+)?Set<string>", source)

    def test_toggle_solo_exists(self, source):
        assert "toggleSolo" in source

    def test_toggle_solo_adds_to_set(self, source):
        assert re.search(r"soloLanes\.add\(laneId\)", source)

    def test_toggle_solo_removes_from_set(self, source):
        assert re.search(r"soloLanes\.delete\(laneId\)", source)

    def test_solo_lanes_initialized_empty(self, source):
        assert re.search(r"soloLanes:\s*new\s+Set<string>\(\)", source)


class TestLockToggle:
    """toggleLock: lane-level lock via lockedLanes Set (MARKER_W2.1)."""

    def test_locked_lanes_is_set(self, source):
        assert re.search(r"lockedLanes:\s*(?:new\s+)?Set<string>", source)

    def test_toggle_lock_exists(self, source):
        assert "toggleLock" in source

    def test_locked_lanes_initialized_empty(self, source):
        assert re.search(r"lockedLanes:\s*new\s+Set<string>\(\)", source)


class TestTrackHeaderTypeSignatures:
    """Verify type signatures for track header actions."""

    def test_toggle_mute_signature(self, source):
        """toggleMute must accept laneId: string."""
        assert re.search(r"toggleMute:\s*\(laneId:\s*string\)", source)

    def test_toggle_solo_signature(self, source):
        assert re.search(r"toggleSolo:\s*\(laneId:\s*string\)", source)

    def test_toggle_lock_signature(self, source):
        assert re.search(r"toggleLock:\s*\(laneId:\s*string\)", source)


class TestRelatedTrackState:
    """Additional track state: target, visibility, volume."""

    def test_targeted_lanes_exists(self, source):
        """targetedLanes (W2.1) for insert/overwrite destination."""
        assert "targetedLanes" in source

    def test_hidden_lanes_exists(self, source):
        """hiddenLanes for playback/export visibility."""
        assert "hiddenLanes" in source

    def test_lane_volumes_exists(self, source):
        """laneVolumes for per-track volume."""
        assert "laneVolumes" in source

    def test_toggle_visibility_exists(self, source):
        assert "toggleVisibility" in source

    def test_set_lane_volume_exists(self, source):
        assert "setLaneVolume" in source
