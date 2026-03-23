"""
MARKER_EPSILON.TDD-RED: Tests that FAIL now, PASS when feature is complete.

Each test targets a specific FCP7 gap. When the gap is closed,
the test turns GREEN — serving as acceptance criteria.

Priority order matches FCP7 criticality for working NLE.
"""

import re
from pathlib import Path

import pytest

CLIENT_SRC = Path(__file__).resolve().parent.parent / "client" / "src"
STORE_FILE = CLIENT_SRC / "store" / "useCutEditorStore.ts"
TIMELINE_FILE = CLIENT_SRC / "components" / "cut" / "TimelineTrackView.tsx"
HOTKEYS_FILE = CLIENT_SRC / "hooks" / "useCutHotkeys.ts"
VIDEO_PREVIEW = CLIENT_SRC / "components" / "cut" / "VideoPreview.tsx"
DOCKVIEW_STORE = CLIENT_SRC / "store" / "useDockviewStore.ts"


@pytest.fixture(scope="module")
def store():
    return STORE_FILE.read_text()


@pytest.fixture(scope="module")
def timeline():
    return TIMELINE_FILE.read_text()


@pytest.fixture(scope="module")
def hotkeys():
    return HOTKEYS_FILE.read_text()


def _find_impl(source: str, fn_name: str, window: int = 2000) -> str | None:
    """Find function implementation body (not type declaration)."""
    pattern = rf"{fn_name}:\s*\([^)]*\)\s*=>\s*\{{"
    m = re.search(pattern, source)
    if not m:
        # Try arrow without braces: fn: () => set(...)
        pattern2 = rf"{fn_name}:\s*\([^)]*\)\s*=>\s*\n?\s*set"
        m = re.search(pattern2, source)
    if not m:
        return None
    return source[m.start():m.start() + window]


# ═══════════════════════════════════════════════════════
# PRIORITY 1: Ch.15 — Undo Completeness
# 5 actions bypass applyTimelineOps (no undo/redo)
# ═══════════════════════════════════════════════════════

class TestUndoGap_PasteAttributes:
    """pasteAttributes uses direct set() — not undo-able.
    FIX: Route through applyTimelineOps([{op: 'set_effects', ...}])."""

    def test_paste_attributes_routes_through_undo(self, store):
        """FAIL until pasteAttributes uses applyTimelineOps."""
        impl = _find_impl(store, "pasteAttributes")
        assert impl is not None, "pasteAttributes implementation not found"
        assert "applyTimelineOps" in impl, \
            "GAP: pasteAttributes uses direct set() — Cmd+Z won't undo pasted effects"


class TestUndoGap_SplitEditLCut:
    """splitEditLCut uses direct set({lanes}) — not undo-able.
    FIX: Route through applyTimelineOps([{op: 'trim_clip', ...}])."""

    def test_lcut_routes_through_undo(self, store):
        """FAIL until splitEditLCut uses applyTimelineOps."""
        impl = _find_impl(store, "splitEditLCut")
        assert impl is not None, "splitEditLCut implementation not found"
        assert "applyTimelineOps" in impl, \
            "GAP: splitEditLCut uses direct set({lanes}) — Alt+E then Cmd+Z won't undo L-cut"


class TestUndoGap_SplitEditJCut:
    """splitEditJCut uses direct set({lanes}) — not undo-able."""

    def test_jcut_routes_through_undo(self, store):
        """FAIL until splitEditJCut uses applyTimelineOps."""
        impl = _find_impl(store, "splitEditJCut")
        assert impl is not None, "splitEditJCut implementation not found"
        assert "applyTimelineOps" in impl, \
            "GAP: splitEditJCut uses direct set({lanes}) — Alt+Shift+E then Cmd+Z won't undo J-cut"


class TestUndoGap_SetClipEffects:
    """setClipEffects uses direct set(state => ...) — not undo-able.
    FIX: Route through applyTimelineOps([{op: 'set_effects', clipId, effects}])."""

    def test_set_clip_effects_routes_through_undo(self, store):
        """FAIL until setClipEffects uses applyTimelineOps."""
        impl = _find_impl(store, "setClipEffects")
        assert impl is not None, "setClipEffects implementation not found"
        assert "applyTimelineOps" in impl, \
            "GAP: setClipEffects uses direct set() — adjusting brightness then Cmd+Z won't undo"


class TestUndoGap_AddKeyframe:
    """addKeyframe uses direct set(state => ...) — not undo-able."""

    def test_add_keyframe_routes_through_undo(self, store):
        """FAIL until addKeyframe uses applyTimelineOps."""
        impl = _find_impl(store, "addKeyframe")
        assert impl is not None, "addKeyframe implementation not found"
        assert "applyTimelineOps" in impl, \
            "GAP: addKeyframe uses direct set() — placing keyframe then Cmd+Z won't undo"


class TestUndoGap_RemoveKeyframe:
    """removeKeyframe uses direct set(state => ...) — not undo-able."""

    def test_remove_keyframe_routes_through_undo(self, store):
        """FAIL until removeKeyframe uses applyTimelineOps."""
        impl = _find_impl(store, "removeKeyframe")
        assert impl is not None, "removeKeyframe implementation not found"
        assert "applyTimelineOps" in impl, \
            "GAP: removeKeyframe uses direct set() — deleting keyframe then Cmd+Z won't undo"


# ═══════════════════════════════════════════════════════
# PRIORITY 2: Ch.20 — Snap Toggle Hotkey Collision
# Premiere preset: N = rollTool AND toggleSnap (collision)
# ═══════════════════════════════════════════════════════

class TestSnapHotkeyCollision:
    """Premiere preset has N bound to both rollTool and toggleSnap."""

    def test_premiere_n_not_duplicated(self, hotkeys):
        """FAIL until Premiere toggleSnap changed from 'n' to 's' (real Premiere binding)."""
        # Parse Premiere preset
        match = re.search(r"PREMIERE_PRESET:\s*HotkeyMap\s*=\s*\{(.*?)\};", hotkeys, re.DOTALL)
        assert match, "PREMIERE_PRESET not found"
        block = match.group(1)

        # Find all bindings that use 'n' (case-sensitive, standalone)
        n_bindings = re.findall(r"(\w+):\s*'n'", block)
        assert len(n_bindings) <= 1, \
            f"GAP: Premiere key 'n' bound to {len(n_bindings)} actions: {n_bindings}. " \
            f"Should be rollTool='n', toggleSnap='s'"


# ═══════════════════════════════════════════════════════
# PRIORITY 3: Ch.3 — Source Monitor Independent Seek
# Source must play clip independently of timeline
# ═══════════════════════════════════════════════════════

class TestSourceProgramIndependence:
    """Source and Program monitors must have truly independent video playback."""

    def test_source_has_own_play_pause(self, store):
        """Source must have independent play/pause (not just shared isPlaying)."""
        assert "sourceIsPlaying" in store, \
            "GAP: No sourceIsPlaying — source monitor can't play independently"

    def test_source_has_own_duration(self, store):
        """Source must track its own clip duration."""
        assert "sourceDuration" in store, \
            "GAP: No sourceDuration — source monitor can't show correct timecode"

    def test_set_source_media_triggers_load(self, store):
        """setSourceMedia should exist to load a clip into source monitor."""
        assert "setSourceMedia" in store

    def test_source_mark_in_separate_from_sequence(self, store):
        """Source marks (I/O on source clip) must be separate from sequence marks."""
        assert "sourceMarkIn" in store
        assert "sequenceMarkIn" in store
        # Both must exist AND be separate fields
        source_marks = len(re.findall(r"sourceMarkIn", store))
        seq_marks = len(re.findall(r"sequenceMarkIn", store))
        assert source_marks >= 2 and seq_marks >= 2, \
            "Both sourceMarkIn and sequenceMarkIn must be separate store fields"


# ═══════════════════════════════════════════════════════
# PRIORITY 4: Ch.5 — Multi-Sequence Management
# Open N sequences simultaneously, switch via tabs
# ═══════════════════════════════════════════════════════

class TestMultiSequence:
    """Multiple sequences in a single project."""

    def test_create_new_sequence_action(self, store):
        """Store must have createSequence or addSequence action."""
        has_create = re.search(r"createSequence|addSequence|newSequence", store)
        assert has_create, \
            "GAP: No createSequence action — user can't create additional sequences"

    def test_sequence_list_in_store(self, store):
        """Store must track list of available sequences."""
        has_list = re.search(r"sequences:|sequenceList:|availableSequences:", store)
        assert has_list, \
            "GAP: No sequence list — can't enumerate/switch between sequences"

    def test_switch_sequence_action(self, store):
        """Must be able to switch active sequence by ID."""
        has_switch = re.search(r"switchSequence|activateSequence|setActiveSequence", store)
        assert has_switch, \
            "GAP: No switchSequence action — can't change active timeline"

    def test_delete_sequence_action(self, store):
        """Must be able to delete a sequence."""
        has_delete = re.search(r"deleteSequence|removeSequence", store)
        assert has_delete, \
            "GAP: No deleteSequence action — can't remove unwanted sequences"


# ═══════════════════════════════════════════════════════
# PRIORITY 5: Ch.42 — Multicam Angle Switching
# Live angle switching during playback
# ═══════════════════════════════════════════════════════

class TestMulticamAngleSwitching:
    """FCP7 Ch.42: Live angle switching during multicam playback."""

    def test_multicam_viewer_component(self):
        """Must have a multicam/multiclip viewer component."""
        cut_dir = CLIENT_SRC / "components" / "cut"
        panels_dir = cut_dir / "panels"
        multicam_files = (
            list(cut_dir.glob("*ulticam*")) +
            list(cut_dir.glob("*ulticlip*")) +
            list(panels_dir.glob("*ulticam*")) if panels_dir.exists() else []
        )
        assert multicam_files, \
            "GAP: No MulticamViewer component — can't display angle grid"

    def test_switch_angle_action(self, store):
        """Store must have switchAngle or setActiveAngle action."""
        has_switch = re.search(r"switchAngle|setActiveAngle|selectAngle", store)
        assert has_switch, \
            "GAP: No switchAngle action — can't cut between camera angles"

    def test_multicam_clip_type(self, store):
        """Store must define MulticamClip or multiclip type."""
        has_type = re.search(r"MulticamClip|MulticlipState|multicam.*angles", store)
        assert has_type, \
            "GAP: No MulticamClip type in frontend store — backend exists but no UI binding"


# ═══════════════════════════════════════════════════════
# BONUS: Ch.38 — Marker Delete
# ═══════════════════════════════════════════════════════

class TestMarkerDelete:
    """FCP7 Ch.38: Must be able to delete individual markers."""

    def test_delete_marker_action(self, store):
        """Store must have deleteMarker or removeMarker action."""
        impl = _find_impl(store, "deleteMarker") or _find_impl(store, "removeMarker")
        assert impl is not None, \
            "GAP: No deleteMarker action — markers can only be added, not removed"


# ═══════════════════════════════════════════════════════
# BONUS: Ch.39 — Subclips
# ═══════════════════════════════════════════════════════

class TestSubclips:
    """FCP7 Ch.39: Create subclip from In/Out range."""

    def test_create_subclip_action(self, store):
        """Store must have createSubclip action."""
        has_subclip = re.search(r"createSubclip|makeSubclip", store)
        assert has_subclip, \
            "GAP: No createSubclip — can't create subclip from marked region"


# ═══════════════════════════════════════════════════════
# BONUS: Ch.49 — Sequence Nesting
# ═══════════════════════════════════════════════════════

class TestSequenceNesting:
    """FCP7 Ch.49: Nest sequence inside another sequence."""

    def test_nest_sequence_action(self, store):
        """Store must have nestSequence action."""
        has_nest = re.search(r"nestSequence|collapseToSequence|makeNested", store)
        assert has_nest, \
            "GAP: No nestSequence — can't place one sequence inside another"
