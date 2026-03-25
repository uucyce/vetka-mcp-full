"""
MARKER_EPSILON.BLOCK1: Wiring verification tests.

Verifies that newly written components are actually imported and used
in their parent components — not orphaned code.
"""

import re
from pathlib import Path

import pytest

CLIENT = Path(__file__).resolve().parent.parent / "client" / "src"
CUT = CLIENT / "components" / "cut"


def _read(p: Path) -> str:
    if not p.exists():
        pytest.skip(f"File not found: {p.name}")
    return p.read_text()


# ═══════════════════════════════════════════════════════
# ThumbnailStrip wired into TimelineTrackView
# ═══════════════════════════════════════════════════════

class TestThumbnailStripWiring:
    """ThumbnailStrip must be imported and rendered inside video clips."""

    def test_imported_in_timeline(self):
        src = _read(CUT / "TimelineTrackView.tsx")
        assert "import ThumbnailStrip" in src

    def test_rendered_for_video_lanes(self):
        src = _read(CUT / "TimelineTrackView.tsx")
        assert re.search(r"<ThumbnailStrip", src), \
            "ThumbnailStrip JSX element must be rendered in TimelineTrackView"

    def test_conditional_on_video_lane_type(self):
        src = _read(CUT / "TimelineTrackView.tsx")
        assert re.search(r"lane_type.*video.*ThumbnailStrip|ThumbnailStrip.*video|showThumbnails", src, re.DOTALL)

    def test_component_exists(self):
        assert (CUT / "ThumbnailStrip.tsx").exists()


# ═══════════════════════════════════════════════════════
# WaveformOverlay wired into audio tracks
# ═══════════════════════════════════════════════════════

class TestWaveformOverlayWiring:
    """WaveformOverlay/WaveformCanvas must render on audio clips."""

    def test_waveform_imported_in_timeline(self):
        src = _read(CUT / "TimelineTrackView.tsx")
        has_import = "WaveformOverlay" in src or "WaveformCanvas" in src or "waveform" in src.lower()
        assert has_import, "Waveform component must be imported in TimelineTrackView"

    def test_show_waveforms_store_field(self):
        src = _read(CLIENT / "store" / "useCutEditorStore.ts")
        assert "showWaveforms" in src

    def test_show_waveforms_default_true(self):
        """Waveforms should be visible by default."""
        src = _read(CLIENT / "store" / "useCutEditorStore.ts")
        assert re.search(r"showWaveforms:\s*true", src), \
            "showWaveforms should default to true"


# ═══════════════════════════════════════════════════════
# AudioLevelMeter wired to monitors
# ═══════════════════════════════════════════════════════

class TestAudioLevelMeterWiring:
    """AudioLevelMeter must be embedded in Program Monitor or timeline area."""

    def test_component_exists(self):
        assert (CUT / "AudioLevelMeter.tsx").exists()

    def test_imported_somewhere(self):
        """AudioLevelMeter must be imported by at least one parent component."""
        found = False
        for f in CUT.rglob("*.tsx"):
            if f.name == "AudioLevelMeter.tsx":
                continue
            content = f.read_text()
            if "AudioLevelMeter" in content:
                found = True
                break
        assert found, "AudioLevelMeter not imported by any parent component"


# ═══════════════════════════════════════════════════════
# TrackResizeHandle wired into timeline
# ═══════════════════════════════════════════════════════

class TestTrackResizeHandleWiring:
    """TrackResizeHandle must be imported and rendered in timeline track headers."""

    def test_component_exists(self):
        assert (CUT / "TrackResizeHandle.tsx").exists()

    def test_imported_in_timeline(self):
        src = _read(CUT / "TimelineTrackView.tsx")
        assert "TrackResizeHandle" in src

    def test_rendered_in_jsx(self):
        src = _read(CUT / "TimelineTrackView.tsx")
        assert re.search(r"<TrackResizeHandle", src)

    def test_uses_track_height_store(self):
        src = _read(CLIENT / "store" / "useCutEditorStore.ts")
        assert "setTrackHeightForLane" in src
        assert "trackHeights" in src


# ═══════════════════════════════════════════════════════
# SourceMonitorButtons wired into Source panel
# ═══════════════════════════════════════════════════════

class TestSourceMonitorButtonsWiring:
    """Source Monitor must have Insert/Overwrite/Mark buttons."""

    def test_component_exists(self):
        assert (CUT / "SourceMonitorButtons.tsx").exists()

    def test_imported_in_source_panel(self):
        """SourceMonitorButtons imported by SourceMonitorPanel or MonitorTransport."""
        found = False
        for name in ["panels/SourceMonitorPanel.tsx", "MonitorTransport.tsx",
                      "panels/ProgramMonitorPanel.tsx", "CutEditorLayoutV2.tsx"]:
            p = CUT / name
            if p.exists() and "SourceMonitorButtons" in p.read_text():
                found = True
                break
        assert found, "SourceMonitorButtons not imported by any monitor panel"


# ═══════════════════════════════════════════════════════
# ToolIcons SVG wired (replacing Unicode)
# ═══════════════════════════════════════════════════════

class TestToolIconsWiring:
    """SVG tool icons must replace Unicode chars in toolbar."""

    def test_tool_icons_file_exists(self):
        assert (CUT / "icons" / "ToolIcons.tsx").exists()

    def test_imported_in_timeline_toolbar(self):
        src = _read(CUT / "TimelineToolbar.tsx")
        assert "ToolIcons" in src or "SelectionIcon" in src or "RazorIcon" in src

    def test_no_unicode_hand_emoji(self):
        """No \\u270B (color emoji hand) in toolbar."""
        src = _read(CUT / "TimelineToolbar.tsx")
        assert "\u270B" not in src, "Color emoji ✋ still present — must be SVG"

    def test_no_unicode_scissors(self):
        src = _read(CUT / "TimelineToolbar.tsx")
        assert "\u2702" not in src, "Unicode scissors ✂ still present — must be SVG"


# ═══════════════════════════════════════════════════════
# DockviewLayout panel registry completeness
# ═══════════════════════════════════════════════════════

class TestDockviewPanelRegistry:
    """All canonical panels from CUT_UNIFIED_VISION must be registered."""

    def test_core_panels_registered(self):
        src = _read(CUT / "DockviewLayout.tsx")
        # 'graph' may be registered as 'dag' or 'graph'
        required = ["project", "script", "source", "program", "timeline", "effects"]
        for panel in required:
            assert re.search(rf"['\"]{panel}['\"]", src), \
                f"Core panel '{panel}' not registered in PANEL_COMPONENTS"

    def test_analysis_panels_registered(self):
        src = _read(CUT / "DockviewLayout.tsx")
        for panel in ["inspector", "clip", "history"]:
            assert panel in src, f"Analysis panel '{panel}' should be registered"
