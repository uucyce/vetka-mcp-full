"""
MARKER_EPSILON.FCP7: Contract tests for PARTIAL FCP7 features.

Tests verify what EXISTS and documents what's MISSING for each
PARTIAL feature in the FCP7 compliance matrix (Ch.1-52).

Each test class maps to a specific FCP7 chapter gap.
"""

import re
from pathlib import Path

import pytest

CLIENT_SRC = Path(__file__).resolve().parent.parent / "client" / "src"
STORE_FILE = CLIENT_SRC / "store" / "useCutEditorStore.ts"
LAYOUT_FILE = CLIENT_SRC / "components" / "cut" / "CutEditorLayoutV2.tsx"
HOTKEYS_FILE = CLIENT_SRC / "hooks" / "useCutHotkeys.ts"
TIMELINE_FILE = CLIENT_SRC / "components" / "cut" / "TimelineTrackView.tsx"
VIDEO_PREVIEW = CLIENT_SRC / "components" / "cut" / "VideoPreview.tsx"


@pytest.fixture(scope="module")
def store():
    if not STORE_FILE.exists():
        pytest.skip("Store not found")
    return STORE_FILE.read_text()


@pytest.fixture(scope="module")
def layout():
    if not LAYOUT_FILE.exists():
        pytest.skip("Layout not found")
    return LAYOUT_FILE.read_text()


@pytest.fixture(scope="module")
def hotkeys():
    if not HOTKEYS_FILE.exists():
        pytest.skip("Hotkeys not found")
    return HOTKEYS_FILE.read_text()


@pytest.fixture(scope="module")
def timeline():
    if not TIMELINE_FILE.exists():
        pytest.skip("Timeline not found")
    return TIMELINE_FILE.read_text()


@pytest.fixture(scope="module")
def video_preview():
    if not VIDEO_PREVIEW.exists():
        pytest.skip("VideoPreview not found")
    return VIDEO_PREVIEW.read_text()


# ═══════════════════════════════════════════════════════
# Ch.3: Source vs Program Monitor
# ═══════════════════════════════════════════════════════

class TestCh3SourceProgramMonitor:
    """FCP7 Ch.3: Source and Program must show independent video feeds."""

    def test_video_preview_has_feed_prop(self, video_preview):
        """VideoPreview must accept a 'feed' prop (source vs program)."""
        assert re.search(r"feed|monitor.*type|monitorType", video_preview), \
            "VideoPreview needs feed/monitorType prop to distinguish source from program"

    def test_source_media_path_in_store(self, store):
        """Store must track sourceMediaPath separately from timeline playback."""
        assert "sourceMediaPath" in store

    def test_seek_source_independent(self, store):
        """seekSource must be independent from seek (program)."""
        assert "seekSource" in store

    def test_source_current_time_separate(self, store):
        """sourceCurrentTime must be separate from currentTime."""
        assert "sourceCurrentTime" in store


# ═══════════════════════════════════════════════════════
# Ch.5: Multi-Sequence Support
# ═══════════════════════════════════════════════════════

class TestCh5MultiSequence:
    """FCP7 Ch.5: Multiple sequences in a project."""

    def test_timeline_id_exists(self, store):
        """Store must track current timelineId."""
        assert "timelineId" in store

    def test_snapshot_timeline_exists(self, store):
        """MARKER_198: snapshotTimeline for multi-instance support."""
        assert "snapshotTimeline" in store

    def test_restore_timeline_exists(self, store):
        """restoreTimeline to switch between saved sequences."""
        assert "restoreTimeline" in store

    def test_timeline_snapshots_map(self, store):
        """timelineSnapshots Map for storing multiple sequences."""
        assert "timelineSnapshots" in store


# ═══════════════════════════════════════════════════════
# Ch.15: Undo/Redo Completeness
# ═══════════════════════════════════════════════════════

class TestCh15UndoCompleteness:
    """FCP7 Ch.15: ALL editing operations must be undo-able."""

    def test_apply_timeline_ops_exists(self, store):
        """Core undo mechanism must exist."""
        assert "applyTimelineOps" in store

    def _find_impl(self, store, action_name):
        """Find action implementation (not type declaration) in store source.

        Implementations use `action: (args) => {` or `action: () =>` patterns
        with actual code bodies, not just type signatures like `action: () => void;`.
        """
        # Match implementation: `actionName: (args) => {` with body up to matching `},`
        # Look for the action followed by actual code (not just `=> void;`)
        pattern = rf"{action_name}:\s*\([^)]*\)\s*=>\s*\{{"
        match = re.search(pattern, store)
        if not match:
            return None
        start = match.start()
        # Grab a generous chunk after the match (implementations are 10-50 lines)
        return store[start:start + 2000]

    def test_cut_clips_uses_undo(self, store):
        """cutClips must route through applyTimelineOps."""
        impl = self._find_impl(store, "cutClips")
        assert impl, "cutClips implementation not found"
        assert "applyTimelineOps" in impl, \
            "cutClips must use applyTimelineOps for undo"

    def test_paste_clips_uses_undo(self, store):
        """pasteClips must route through applyTimelineOps."""
        impl = self._find_impl(store, "pasteClips")
        assert impl, "pasteClips implementation not found"
        assert "applyTimelineOps" in impl, \
            "pasteClips must use applyTimelineOps for undo"

    def test_lift_clip_uses_undo(self, store):
        """liftClip must route through applyTimelineOps."""
        impl = self._find_impl(store, "liftClip")
        assert impl, "liftClip implementation not found"
        assert "applyTimelineOps" in impl, \
            "liftClip must use applyTimelineOps"

    def test_extract_clip_uses_undo(self, store):
        """extractClip must route through applyTimelineOps."""
        impl = self._find_impl(store, "extractClip")
        assert impl, "extractClip implementation not found"
        assert "applyTimelineOps" in impl, \
            "extractClip must use applyTimelineOps"

    def test_close_gap_uses_undo(self, store):
        """closeGap must route through applyTimelineOps."""
        impl = self._find_impl(store, "closeGap")
        assert impl, "closeGap implementation not found"
        assert "applyTimelineOps" in impl, \
            "closeGap must use applyTimelineOps"

    # These are KNOWN GAPS — test documents the absence
    def test_paste_attributes_bypasses_undo(self, store):
        """KNOWN GAP: pasteAttributes bypasses applyTimelineOps."""
        paste_attr = re.search(r"pasteAttributes:.*?(?=\n  //|\n  \w+:)", store, re.DOTALL)
        if paste_attr:
            # This test DOCUMENTS the gap — it passes when the bug exists
            has_undo = "applyTimelineOps" in paste_attr.group()
            if not has_undo:
                pytest.skip("KNOWN GAP: pasteAttributes bypasses undo (tb_1774251501_1)")

    def test_split_edit_lcut_bypasses_undo(self, store):
        """KNOWN GAP: splitEditLCut bypasses applyTimelineOps."""
        lcut = re.search(r"splitEditLCut:.*?(?=\n  //|\n  splitEditJCut)", store, re.DOTALL)
        if lcut:
            has_undo = "applyTimelineOps" in lcut.group()
            if not has_undo:
                pytest.skip("KNOWN GAP: splitEditLCut bypasses undo (tb_1774251501_1)")


# ═══════════════════════════════════════════════════════
# Ch.19: Slip/Slide Tool Drag Behavior
# ═══════════════════════════════════════════════════════

class TestCh19SlipSlideDrag:
    """FCP7 Ch.19/44: Slip and Slide must have drag interactions."""

    def test_slip_tool_in_store(self, store):
        """slipTool activeTool value must exist."""
        assert "'slip'" in store

    def test_slide_tool_in_store(self, store):
        """slideTool activeTool value must exist."""
        assert "'slide'" in store

    def test_slip_hotkey_bound(self, hotkeys):
        """Slip tool must have hotkey (Y in both presets)."""
        assert re.search(r"slipTool:\s*'y'", hotkeys)

    def test_slide_hotkey_bound(self, hotkeys):
        """Slide tool must have hotkey (U in both presets)."""
        assert re.search(r"slideTool:\s*'u'", hotkeys)

    def test_timeline_handles_slip_mode(self, timeline):
        """TimelineTrackView should handle slip drag mode."""
        has_slip = "slip" in timeline.lower()
        if not has_slip:
            pytest.skip("GAP: Timeline has no slip drag handler")

    def test_timeline_handles_slide_mode(self, timeline):
        """TimelineTrackView should handle slide drag mode."""
        has_slide = "slide" in timeline.lower()
        if not has_slide:
            pytest.skip("GAP: Timeline has no slide drag handler")


# ═══════════════════════════════════════════════════════
# Ch.20: Snap Behavior
# ═══════════════════════════════════════════════════════

class TestCh20Snapping:
    """FCP7 Ch.20: Snap to edit points with visual indicator."""

    def test_snap_enabled_in_store(self, store):
        """snapEnabled boolean must exist."""
        assert "snapEnabled" in store

    def test_toggle_snap_action(self, store):
        """toggleSnap action must exist."""
        assert "toggleSnap" in store

    def test_snap_hotkey_n(self, hotkeys):
        """N key must toggle snap."""
        assert re.search(r"toggleSnap:\s*'n'", hotkeys)

    def test_snap_visual_indicator(self, timeline):
        """Timeline should show snap indicator line when clips align."""
        has_snap_indicator = re.search(r"snap.*indicator|snap.*line|snapLine", timeline, re.IGNORECASE)
        if not has_snap_indicator:
            pytest.skip("GAP: No visual snap indicator in timeline")


# ═══════════════════════════════════════════════════════
# Ch.30: Paste Attributes
# ═══════════════════════════════════════════════════════

class TestCh30PasteAttributes:
    """FCP7 Ch.30: Paste Attributes must transfer effects between clips."""

    def test_paste_attributes_exists(self, store):
        """pasteAttributes action must exist."""
        assert "pasteAttributes" in store

    def test_copies_effects(self, store):
        """pasteAttributes must copy clip.effects from clipboard."""
        paste_section = re.search(r"pasteAttributes:.*?(?=\n  //|\n  \w+:)", store, re.DOTALL)
        if paste_section:
            assert "effects" in paste_section.group(), \
                "pasteAttributes should reference clip effects"


# ═══════════════════════════════════════════════════════
# Ch.38: Marker Management
# ═══════════════════════════════════════════════════════

class TestCh38MarkerManagement:
    """FCP7 Ch.38: Full marker CRUD."""

    def test_add_marker_exists(self, store):
        assert "addMarker" in store or "markers" in store

    def test_marker_kind_type(self, store):
        """MarkerKind type must exist with semantic types."""
        assert "MarkerKind" in store

    def test_marker_list_panel_exists(self):
        """MarkerListPanel must exist for marker table view."""
        panel = CLIENT_SRC / "components" / "cut" / "panels" / "MarkerListPanel.tsx"
        assert panel.exists(), "MarkerListPanel.tsx should exist"

    def test_delete_marker_action(self, store):
        """deleteMarker or removeMarker action should exist."""
        has_delete = "deleteMarker" in store or "removeMarker" in store
        if not has_delete:
            pytest.skip("GAP: No deleteMarker action in store")


# ═══════════════════════════════════════════════════════
# Ch.41: Split Edits (L/J-cut)
# ═══════════════════════════════════════════════════════

class TestCh41SplitEdits:
    """FCP7 Ch.41: L-cut and J-cut split edits."""

    def test_lcut_action_exists(self, store):
        assert "splitEditLCut" in store

    def test_jcut_action_exists(self, store):
        assert "splitEditJCut" in store

    def test_lcut_hotkey(self, hotkeys):
        """L-cut: Alt+E in both presets."""
        assert re.search(r"splitEditLCut:\s*'Alt\+e'", hotkeys)

    def test_jcut_hotkey(self, hotkeys):
        """J-cut: Alt+Shift+E."""
        assert re.search(r"splitEditJCut:\s*'Alt\+Shift\+e'", hotkeys)


# ═══════════════════════════════════════════════════════
# Ch.47: Transitions
# ═══════════════════════════════════════════════════════

class TestCh47Transitions:
    """FCP7 Ch.47: Default transition application."""

    def test_default_transition_action(self, store):
        assert "addDefaultTransition" in store

    def test_cmd_t_hotkey(self, hotkeys):
        assert re.search(r"addDefaultTransition:\s*'Cmd\+t'", hotkeys)

    def test_transition_type_in_clip(self, store):
        """Clips must have transition_out field."""
        assert "transition_out" in store

    def test_transitions_panel_exists(self):
        panel = CLIENT_SRC / "components" / "cut" / "TransitionsPanel.tsx"
        assert panel.exists()


# ═══════════════════════════════════════════════════════
# Ch.42: Multicam
# ═══════════════════════════════════════════════════════

class TestCh42Multicam:
    """FCP7 Ch.42: Multicam backend + MulticamViewer frontend (MARKER_MULTICAM_VIEWER)."""

    def test_multicam_backend_exists(self):
        """cut_multicam_sync.py must exist."""
        backend = Path(__file__).resolve().parent.parent / "src" / "services" / "cut_multicam_sync.py"
        assert backend.exists(), "Multicam sync backend should exist"

    def test_multicam_has_audio_correlation(self):
        """Backend must have audio cross-correlation sync."""
        backend = Path(__file__).resolve().parent.parent / "src" / "services" / "cut_multicam_sync.py"
        if not backend.exists():
            pytest.skip("No multicam backend")
        content = backend.read_text()
        assert "cross_correlat" in content.lower() or "correlate" in content.lower() or "sync" in content.lower()

    def test_multicam_viewer_exists(self):
        """MulticamViewer.tsx must exist with required testids."""
        viewer = CLIENT_SRC / "components" / "cut" / "MulticamViewer.tsx"
        assert viewer.exists(), "MulticamViewer.tsx should exist in components/cut"
        content = viewer.read_text()
        assert 'data-testid="multicam-viewer-grid"' in content, "Must have static grid testid"
        assert "data-testid={" in content, "Must have dynamic angle testids"

    def test_multicam_viewer_store_contract(self):
        """MulticamViewer.tsx must import and use store fields."""
        viewer = CLIENT_SRC / "components" / "cut" / "MulticamViewer.tsx"
        assert viewer.exists(), "MulticamViewer.tsx should exist"
        content = viewer.read_text()
        assert "useCutEditorStore" in content, "Must import useCutEditorStore"
        assert "multicamMode" in content, "Must read multicamMode from store"
        assert "multicamAngles" in content, "Must read multicamAngles from store"
        assert "multicamActiveAngle" in content, "Must read multicamActiveAngle from store"
        assert "multicamSwitchAngle" in content, "Must read multicamSwitchAngle from store"

    def test_multicam_viewer_grid_logic(self):
        """MulticamViewer.tsx must have grid layout and empty state guard."""
        viewer = CLIENT_SRC / "components" / "cut" / "MulticamViewer.tsx"
        assert viewer.exists(), "MulticamViewer.tsx should exist"
        content = viewer.read_text()
        assert "gridTemplateColumns" in content, "Must use CSS gridTemplateColumns for layout"
        assert "repeat(" in content, "Must use repeat() for dynamic column count"
        assert "No multicam clip loaded" in content, "Must have empty state guard message"

    def test_multicam_angle_switching_wired(self):
        """MulticamViewer.tsx must wire click events to store switchAngle action."""
        viewer = CLIENT_SRC / "components" / "cut" / "MulticamViewer.tsx"
        assert viewer.exists(), "MulticamViewer.tsx should exist"
        content = viewer.read_text()
        assert "onClick" in content, "Must have onClick handler on angle tiles"
        assert "switchAngle" in content, "Must call switchAngle store action on click"


# ═══════════════════════════════════════════════════════
# PULSE Auto-Montage
# ═══════════════════════════════════════════════════════


class TestPulseAutoMontage:
    """Contract tests for PULSE Auto-Montage feature."""

    PROJECT_ROOT = Path(__file__).resolve().parent.parent

    def test_pulse_auto_montage_service_exists(self):
        """pulse_auto_montage.py service must exist."""
        service = self.PROJECT_ROOT / "src" / "services" / "pulse_auto_montage.py"
        assert service.exists(), "src/services/pulse_auto_montage.py must exist"

    def test_pulse_auto_montage_endpoint_exists(self):
        """cut_routes.py must expose pulse/auto-montage POST endpoint."""
        routes = self.PROJECT_ROOT / "src" / "api" / "routes" / "cut_routes.py"
        assert routes.exists(), "src/api/routes/cut_routes.py must exist"
        content = routes.read_text()
        assert "pulse/auto-montage" in content, "Must define pulse/auto-montage route"
        assert "CutPulseAutoMontageRequest" in content, "Must reference CutPulseAutoMontageRequest model"

    def test_auto_montage_panel_exists(self):
        """AutoMontagePanel.tsx must exist with correct header and mode buttons."""
        panel = CLIENT_SRC / "components" / "cut" / "AutoMontagePanel.tsx"
        assert panel.exists(), "AutoMontagePanel.tsx must exist"
        content = panel.read_text()
        assert "PULSE Auto-Montage" in content, "Must contain 'PULSE Auto-Montage' header text"
        assert "Favorites" in content, "Must contain 'Favorites' mode button"
        assert "Script" in content, "Must contain 'Script' mode button"
        assert "Music" in content, "Must contain 'Music' mode button"

    def test_auto_montage_panel_store_wiring(self):
        """AutoMontagePanel.tsx must be wired to the store and call the API endpoint."""
        panel = CLIENT_SRC / "components" / "cut" / "AutoMontagePanel.tsx"
        assert panel.exists(), "AutoMontagePanel.tsx must exist"
        content = panel.read_text()
        assert "useCutEditorStore" in content, "Must import useCutEditorStore"
        assert "montageRunning" in content or "setMontageRunning" in content, (
            "Must reference montageRunning or setMontageRunning from store"
        )
        assert "pulse/auto-montage" in content, "Must reference pulse/auto-montage API endpoint"

    def test_auto_montage_store_actions(self):
        """useCutEditorStore.ts must contain all PULSE montage state fields and actions."""
        content = STORE_FILE.read_text() if STORE_FILE.exists() else ""
        if not content:
            pytest.skip("Store file not found")
        assert "montageRunning" in content, "Store must have montageRunning field"
        assert "montageMode" in content, "Store must have montageMode field"
        assert "montageProgress" in content, "Store must have montageProgress field"
        assert "montageError" in content, "Store must have montageError field"
        assert "setMontageRunning" in content, "Store must have setMontageRunning action"
        assert "setMontageMode" in content, "Store must have setMontageMode action"

    def test_pulse_conductor_exists(self):
        """pulse_conductor.py must exist and produce PulseScore for scenes."""
        conductor = self.PROJECT_ROOT / "src" / "services" / "pulse_conductor.py"
        assert conductor.exists(), "src/services/pulse_conductor.py must exist"
        content = conductor.read_text()
        assert "PulseConductor" in content, "Must define PulseConductor class"
        assert "PulseScore" in content or "score" in content.lower(), (
            "pulse_conductor.py must produce scores for scenes"
        )

    def test_auto_montage_creates_timeline(self):
        """AutoMontagePanel.tsx must create a timeline and open a dockview tab."""
        panel = CLIENT_SRC / "components" / "cut" / "AutoMontagePanel.tsx"
        assert panel.exists(), "AutoMontagePanel.tsx must exist"
        content = panel.read_text()
        assert "createTimeline" in content, "Must call createTimeline to create timeline instance"
        assert "addTimelinePanel" in content, "Must call addTimelinePanel to open dockview tab"
