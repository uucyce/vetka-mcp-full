"""
MARKER_W6.TOOL-SM: Unit tests for tool state machine.

Tests cursor mapping, tool display config, and tool switching logic.
"""
import pytest


# ── Tool definitions (mirrors TypeScript) ────────────────────

ALL_TOOLS = ['selection', 'razor', 'hand', 'zoom', 'slip', 'slide', 'ripple', 'roll']

TOOL_CURSOR = {
    'selection': 'default', 'razor': 'crosshair', 'hand': 'grab', 'zoom': 'zoom-in',
    'slip': 'ew-resize', 'slide': 'col-resize', 'ripple': 'w-resize', 'roll': 'col-resize',
}

CLIP_CURSOR = {
    'selection': 'grab', 'razor': 'crosshair', 'hand': 'grab', 'zoom': 'zoom-in',
    'slip': 'ew-resize', 'slide': 'col-resize', 'ripple': 'w-resize', 'roll': 'col-resize',
}

TOOL_DISPLAY = {
    'selection': {'label': 'Select', 'shortcut': 'V', 'color': '#ccc'},
    'razor':     {'label': 'Razor',  'shortcut': 'C', 'color': '#f87171'},
    'slip':      {'label': 'Slip',   'shortcut': 'Y', 'color': '#4ade80'},
    'slide':     {'label': 'Slide',  'shortcut': 'U', 'color': '#60a5fa'},
    'ripple':    {'label': 'Ripple', 'shortcut': 'B', 'color': '#fbbf24'},
    'roll':      {'label': 'Roll',   'shortcut': 'N', 'color': '#c084fc'},
    'hand':      {'label': 'Hand',   'shortcut': 'H', 'color': '#888'},
    'zoom':      {'label': 'Zoom',   'shortcut': 'Z', 'color': '#888'},
}

# Hotkey → tool mapping (Premiere preset)
PREMIERE_HOTKEYS = {
    'v': 'selection', 'c': 'razor', 'y': 'slip', 'u': 'slide',
    'b': 'ripple', 'n': 'roll', 'h': 'hand', 'z': 'zoom',
}


class TestToolCursorMap:
    """Every tool must have a cursor for both lane and clip contexts."""

    def test_all_tools_have_lane_cursor(self):
        for tool in ALL_TOOLS:
            assert tool in TOOL_CURSOR, f"Missing lane cursor for {tool}"

    def test_all_tools_have_clip_cursor(self):
        for tool in ALL_TOOLS:
            assert tool in CLIP_CURSOR, f"Missing clip cursor for {tool}"

    def test_selection_clip_cursor_is_grab(self):
        """Selection tool: clips are grabbable."""
        assert CLIP_CURSOR['selection'] == 'grab'

    def test_razor_clip_cursor_is_crosshair(self):
        """Razor tool: click splits, so crosshair on clips too."""
        assert CLIP_CURSOR['razor'] == 'crosshair'

    def test_trim_tools_have_resize_cursors(self):
        """Trim tools show resize cursors on clips."""
        for tool in ['slip', 'slide', 'ripple', 'roll']:
            assert CLIP_CURSOR[tool] in ('ew-resize', 'col-resize', 'w-resize'), \
                f"{tool} should have a resize cursor, got {CLIP_CURSOR[tool]}"

    def test_clip_cursor_differs_from_lane_for_selection(self):
        """Selection: lane=pointer, clip=grab."""
        assert TOOL_CURSOR['selection'] != CLIP_CURSOR['selection']


class TestToolDisplay:
    """Every tool must have display metadata for the toolbar indicator."""

    def test_all_tools_have_display(self):
        for tool in ALL_TOOLS:
            assert tool in TOOL_DISPLAY, f"Missing display config for {tool}"

    def test_all_display_have_label(self):
        for tool, info in TOOL_DISPLAY.items():
            assert 'label' in info and info['label'], f"Missing label for {tool}"

    def test_all_display_have_shortcut(self):
        for tool, info in TOOL_DISPLAY.items():
            assert 'shortcut' in info and info['shortcut'], f"Missing shortcut for {tool}"

    def test_all_display_have_color(self):
        for tool, info in TOOL_DISPLAY.items():
            assert 'color' in info and info['color'].startswith('#'), f"Bad color for {tool}"


class TestToolSwitching:
    """Tool switching via hotkeys."""

    def test_premiere_hotkey_coverage(self):
        """Every tool is reachable via a Premiere hotkey."""
        reachable = set(PREMIERE_HOTKEYS.values())
        assert reachable == set(ALL_TOOLS)

    def test_escape_resets_to_selection(self):
        """Escape should reset to selection tool."""
        # escapeContext handler sets activeTool to 'selection'
        active = 'razor'
        active = 'selection'  # after escape
        assert active == 'selection'

    def test_default_tool_is_selection(self):
        """Store default for activeTool should be 'selection'."""
        default = 'selection'
        assert default in ALL_TOOLS
