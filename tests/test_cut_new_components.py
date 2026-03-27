"""
MARKER_DELTA3_COMPONENTS: Static validation of new Gamma CUT components.

Verifies file structure, exports, testids, monochrome compliance,
and FCP7 conventions for recently added components.
"""

import re
import pytest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CUT_DIR = ROOT / "client" / "src" / "components" / "cut"


class TestWelcomeScreen:
    """GAMMA-APP1: Welcome / New Project screen."""

    @pytest.fixture
    def source(self):
        path = CUT_DIR / "WelcomeScreen.tsx"
        if not path.exists():
            pytest.skip("WelcomeScreen.tsx not found")
        return path.read_text()

    def test_exports_add_recent_project(self, source):
        assert "export function addRecentProject" in source

    def test_has_resolution_presets(self, source):
        assert "1920" in source and "1080" in source, "Missing 1080p resolution"
        assert "3840" in source or "4K" in source, "Missing 4K resolution"

    def test_has_frame_rate_options(self, source):
        assert "23.976" in source, "Missing 23.976 fps (film)"
        assert "24" in source, "Missing 24 fps (cinema)"
        assert "25" in source, "Missing 25 fps (PAL)"

    def test_has_create_and_open_buttons(self, source):
        assert "Create Project" in source or "createProject" in source.lower()
        assert "Open Project" in source or "openProject" in source.lower()

    def test_recent_projects_in_localstorage(self, source):
        assert "cut_recent_projects" in source

    def test_monochrome_background(self, source):
        # Background should be dark grey, not colored
        bgs = re.findall(r"background:\s*'(#[0-9a-fA-F]{6})'", source)
        for bg in bgs:
            hex6 = bg.lstrip("#").lower()
            r, g, b = hex6[0:2], hex6[2:4], hex6[4:6]
            assert r == g == b, f"Non-grey background {bg} in WelcomeScreen"


class TestClipContextMenu:
    """GAMMA-CLIP1: Right-click context menu for timeline clips."""

    @pytest.fixture
    def source(self):
        path = CUT_DIR / "ClipContextMenu.tsx"
        if not path.exists():
            pytest.skip("ClipContextMenu.tsx not found")
        return path.read_text()

    def test_exports_props_interface(self, source):
        assert "ClipContextMenuProps" in source

    def test_has_clip_id_prop(self, source):
        assert "clipId" in source

    def test_has_position_prop(self, source):
        assert "position" in source and "x:" in source and "y:" in source

    def test_has_on_close(self, source):
        assert "onClose" in source

    def test_has_fcp7_actions(self, source):
        """FCP7 context menu should have standard editing actions."""
        lower = source.lower()
        # At least some of: cut, copy, paste, delete, split, speed
        actions_found = sum(1 for a in ["cut", "copy", "delete", "split", "speed"]
                           if a in lower)
        assert actions_found >= 3, f"Only {actions_found}/5 standard actions found"

    def test_monochrome_menu_style(self, source):
        assert "#1a1a1a" in source, "Menu should use dark grey background"

    def test_uses_store(self, source):
        assert "useCutEditorStore" in source, "Should dispatch to store"


class TestSourceMonitorButtons:
    """GAMMA-MON1: FCP7 Source Monitor action buttons."""

    @pytest.fixture
    def source(self):
        path = CUT_DIR / "SourceMonitorButtons.tsx"
        if not path.exists():
            pytest.skip("SourceMonitorButtons.tsx not found")
        return path.read_text()

    def test_has_testid(self, source):
        assert 'data-testid="source-monitor-buttons"' in source

    def test_has_fcp7_buttons(self, source):
        """FCP7 Source viewer: Insert, Overwrite, Mark Clip, Match Frame."""
        assert "Insert" in source or "insertEdit" in source
        assert "Overwrite" in source or "overwriteEdit" in source
        assert "Mark Clip" in source or "markClip" in source
        assert "Match Frame" in source or "matchFrame" in source

    def test_buttons_have_titles(self, source):
        assert "title=" in source, "Buttons should have tooltip titles"

    def test_monochrome_style(self, source):
        bgs = re.findall(r"background:\s*'(#[0-9a-fA-F]{6})'", source)
        for bg in bgs:
            hex6 = bg.lstrip("#").lower()
            r, g, b = hex6[0:2], hex6[2:4], hex6[4:6]
            assert r == g == b, f"Non-grey background {bg} in SourceMonitorButtons"


class TestToolIcons:
    """GAMMA-ICON1: SVG tool icons."""

    @pytest.fixture
    def source(self):
        path = CUT_DIR / "icons" / "ToolIcons.tsx"
        if not path.exists():
            pytest.skip("ToolIcons.tsx not found")
        return path.read_text()

    def test_has_svg_elements(self, source):
        assert "<svg" in source.lower() or "svg" in source

    def test_has_standard_tools(self, source):
        lower = source.lower()
        tools = ["selection", "razor", "ripple", "roll", "hand", "zoom"]
        found = sum(1 for t in tools if t in lower)
        assert found >= 4, f"Only {found}/6 standard tool icons"


class TestTimelineRuler:
    """GAMMA-TIMELINE: Timeline ruler component."""

    def test_file_exists(self):
        path = CUT_DIR / "TimelineRuler.tsx"
        assert path.exists(), "TimelineRuler.tsx should exist"

    def test_exports_default(self):
        path = CUT_DIR / "TimelineRuler.tsx"
        if not path.exists():
            pytest.skip("not found")
        source = path.read_text()
        assert "export default" in source or "export function" in source


class TestTrackResizeHandle:
    """GAMMA-TIMELINE: Track resize handle."""

    def test_file_exists(self):
        path = CUT_DIR / "TrackResizeHandle.tsx"
        assert path.exists(), "TrackResizeHandle.tsx should exist"


class TestSequenceSettingsDialog:
    """BETA-B3: Sequence settings dialog."""

    def test_file_exists(self):
        path = CUT_DIR / "SequenceSettingsDialog.tsx"
        assert path.exists(), "SequenceSettingsDialog.tsx should exist"

    def test_has_fps_and_resolution(self):
        path = CUT_DIR / "SequenceSettingsDialog.tsx"
        if not path.exists():
            pytest.skip("not found")
        source = path.read_text()
        assert "fps" in source.lower() or "frameRate" in source or "frame_rate" in source
        assert "resolution" in source.lower() or "width" in source
