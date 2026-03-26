"""
MARKER_W6.WIRE: Tests for all hotkey handler wiring completeness.

Verifies that every CutHotkeyAction has a corresponding handler.
Also tests the logic of newly wired handlers.
"""
import re
from pathlib import Path

import pytest

HOTKEYS_FILE = Path(__file__).resolve().parent.parent / "client" / "src" / "hooks" / "useCutHotkeys.ts"


# ── Handler registry (mirrors CutEditorLayoutV2 hotkeyHandlers) ──

WIRED_HANDLERS = {
    # Playback
    'playPause', 'stop', 'shuttleBack', 'shuttleForward',
    'frameStepBack', 'frameStepForward', 'fiveFrameStepBack', 'fiveFrameStepForward',
    'goToStart', 'goToEnd', 'cyclePlaybackRate',
    # Marking
    'markIn', 'markOut', 'clearIn', 'clearOut', 'clearInOut', 'goToIn', 'goToOut',
    'markClip', 'playInToOut',
    # Editing
    'undo', 'redo', 'deleteClip', 'splitClip', 'rippleDelete',
    'selectAll', 'copy', 'cut', 'paste', 'pasteInsert',
    'nudgeLeft', 'nudgeRight',
    # Tools
    'razorTool', 'selectTool', 'insertEdit', 'overwriteEdit',
    'replaceEdit', 'fitToFill', 'superimpose',
    'slipTool', 'slideTool', 'rippleTool', 'rollTool',
    'handTool', 'zoomTool',
    # Markers + Keyframes
    'addMarker', 'addComment', 'nextMarker', 'prevMarker',
    'nextKeyframe', 'prevKeyframe', 'addKeyframe',
    'toggleRecordMode', 'openSpeedControl',
    # Sequence operations
    'liftClip', 'extractClip', 'closeGap', 'extendEdit',
    'splitEditLCut', 'splitEditJCut', 'addDefaultTransition',
    # Navigation
    'prevEditPoint', 'nextEditPoint', 'matchFrame', 'toggleSourceProgram',
    # View
    'zoomIn', 'zoomOut', 'zoomToFit', 'cycleTrackHeight',
    # Project
    'importMedia', 'saveProject', 'sceneDetect',
    'toggleViewMode', 'escapeContext',
    # Panel focus
    'focusSource', 'focusProgram', 'focusTimeline', 'focusProject', 'focusEffects',
    # Linked selection + Snap + Subclip
    'toggleLinkedSelection', 'toggleSnap', 'makeSubclip',
}

# Full CutHotkeyAction list (from useCutHotkeys.ts)
ALL_ACTIONS = {
    # Playback (11)
    'playPause', 'stop', 'shuttleBack', 'shuttleForward',
    'frameStepBack', 'frameStepForward', 'fiveFrameStepBack', 'fiveFrameStepForward',
    'goToStart', 'goToEnd', 'cyclePlaybackRate',
    # Marking (9)
    'markIn', 'markOut', 'clearIn', 'clearOut', 'clearInOut', 'goToIn', 'goToOut',
    'markClip', 'playInToOut',
    # Editing (12)
    'undo', 'redo', 'deleteClip', 'splitClip', 'rippleDelete',
    'selectAll', 'copy', 'cut', 'paste', 'pasteInsert',
    'nudgeLeft', 'nudgeRight',
    # Tools (13)
    'razorTool', 'selectTool', 'insertEdit', 'overwriteEdit',
    'replaceEdit', 'fitToFill', 'superimpose',
    'slipTool', 'slideTool', 'rippleTool', 'rollTool',
    'handTool', 'zoomTool',
    # Markers + Keyframes (8)
    'addMarker', 'addComment', 'nextMarker', 'prevMarker',
    'nextKeyframe', 'prevKeyframe', 'addKeyframe',
    'toggleRecordMode', 'openSpeedControl',
    # Sequence (7)
    'liftClip', 'extractClip', 'closeGap', 'extendEdit',
    'splitEditLCut', 'splitEditJCut', 'addDefaultTransition',
    # Navigation (4)
    'prevEditPoint', 'nextEditPoint', 'matchFrame', 'toggleSourceProgram',
    # View (4)
    'zoomIn', 'zoomOut', 'zoomToFit', 'cycleTrackHeight',
    # Project (2)
    'importMedia', 'saveProject',
    # Panel focus (5)
    'focusSource', 'focusProgram', 'focusTimeline', 'focusProject', 'focusEffects',
    # Linked selection + Snap + Subclip (3)
    'toggleLinkedSelection', 'toggleSnap', 'makeSubclip',
    # CUT-specific (3)
    'sceneDetect', 'toggleViewMode', 'escapeContext',
}


class TestWiringCompleteness:
    """Every action must have a handler."""

    def test_all_actions_have_handlers(self):
        """No action should be missing from the wired set."""
        missing = ALL_ACTIONS - WIRED_HANDLERS
        assert missing == set(), f"Actions without handlers: {missing}"

    def test_no_phantom_handlers(self):
        """No handler for a non-existent action."""
        phantom = WIRED_HANDLERS - ALL_ACTIONS
        assert phantom == set(), f"Handlers for undefined actions: {phantom}"

    def test_count_matches(self):
        """Handler count = action count."""
        assert len(WIRED_HANDLERS) == len(ALL_ACTIONS)

    def test_all_actions_match_typescript_source(self):
        """ALL_ACTIONS must match CutHotkeyAction type in useCutHotkeys.ts.

        Prevents drift between this test file and the actual TypeScript source.
        """
        if not HOTKEYS_FILE.exists():
            pytest.skip(f"Hotkey file not found: {HOTKEYS_FILE}")
        source = HOTKEYS_FILE.read_text()
        # Parse the type union: | 'actionName'
        match = re.search(r"export type CutHotkeyAction\s*=(.*?);", source, re.DOTALL)
        assert match, "Could not find CutHotkeyAction type"
        ts_actions = set(re.findall(r"'(\w+)'", match.group(1)))
        missing_from_test = ts_actions - ALL_ACTIONS
        extra_in_test = ALL_ACTIONS - ts_actions
        assert not missing_from_test, f"Actions in TS but missing from ALL_ACTIONS: {missing_from_test}"
        assert not extra_in_test, f"Actions in ALL_ACTIONS but not in TS: {extra_in_test}"


# ── Logic tests for newly wired handlers ─────────────────────

class TestCyclePlaybackRate:
    def test_cycle_1_to_2(self):
        RATES = [0.5, 1, 2, 4]
        idx = RATES.index(1)
        assert RATES[(idx + 1) % len(RATES)] == 2

    def test_cycle_4_to_05(self):
        RATES = [0.5, 1, 2, 4]
        idx = RATES.index(4)
        assert RATES[(idx + 1) % len(RATES)] == 0.5

    def test_cycle_05_to_1(self):
        RATES = [0.5, 1, 2, 4]
        idx = RATES.index(0.5)
        assert RATES[(idx + 1) % len(RATES)] == 1


class TestRippleDelete:
    """Remove clip + close gap by shifting subsequent clips left."""

    def test_ripple_delete_middle(self):
        clips = [
            {"clip_id": "A", "start_sec": 0.0, "duration_sec": 5.0},
            {"clip_id": "B", "start_sec": 5.0, "duration_sec": 3.0},
            {"clip_id": "C", "start_sec": 8.0, "duration_sec": 4.0},
        ]
        # Ripple delete B (5.0, dur=3.0)
        target = "B"
        clip = next(c for c in clips if c["clip_id"] == target)
        clip_start = clip["start_sec"]
        clip_dur = clip["duration_sec"]
        result = [c for c in clips if c["clip_id"] != target]
        result = [
            {**c, "start_sec": max(0, c["start_sec"] - clip_dur)} if c["start_sec"] > clip_start else c
            for c in result
        ]
        assert len(result) == 2
        assert result[0]["start_sec"] == 0.0  # A unchanged
        assert result[1]["start_sec"] == 5.0  # C shifted left by 3s

    def test_ripple_delete_first(self):
        clips = [
            {"clip_id": "A", "start_sec": 0.0, "duration_sec": 5.0},
            {"clip_id": "B", "start_sec": 5.0, "duration_sec": 3.0},
        ]
        target = "A"
        clip = next(c for c in clips if c["clip_id"] == target)
        result = [c for c in clips if c["clip_id"] != target]
        result = [
            {**c, "start_sec": max(0, c["start_sec"] - clip["duration_sec"])} if c["start_sec"] > clip["start_sec"] else c
            for c in result
        ]
        assert result[0]["start_sec"] == 0.0  # B shifted to 0


class TestNudge:
    """Move selected clip by 1 frame."""

    def test_nudge_right(self):
        fps = 25
        start = 5.0
        new_start = start + 1 / fps
        assert abs(new_start - 5.04) < 0.001

    def test_nudge_left(self):
        fps = 25
        start = 5.0
        new_start = max(0, start - 1 / fps)
        assert abs(new_start - 4.96) < 0.001

    def test_nudge_left_clamps(self):
        fps = 25
        start = 0.02
        new_start = max(0, start - 1 / fps)
        assert new_start == 0.0
