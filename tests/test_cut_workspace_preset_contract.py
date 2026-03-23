"""
MARKER_EPSILON.T5: Workspace preset switch contract tests.

Verifies WorkspacePresets.tsx (MARKER_C5 + GAMMA-WS1):
1. Four presets defined: editing, color, audio, custom
2. Each has SVG icon, label, shortcut hint
3. Active preset tracked in useDockviewStore
4. Switching calls loadLayout
5. Custom preset supports double-click to save
6. Presets use monochrome palette

Source: client/src/components/cut/WorkspacePresets.tsx
Store: client/src/store/useDockviewStore.ts
"""

import re
from pathlib import Path

import pytest

PRESETS_FILE = Path(__file__).resolve().parent.parent / "client" / "src" / "components" / "cut" / "WorkspacePresets.tsx"
DOCKVIEW_STORE = Path(__file__).resolve().parent.parent / "client" / "src" / "store" / "useDockviewStore.ts"


@pytest.fixture(scope="module")
def source():
    if not PRESETS_FILE.exists():
        pytest.skip(f"WorkspacePresets not found: {PRESETS_FILE}")
    return PRESETS_FILE.read_text()


@pytest.fixture(scope="module")
def dockview_source():
    if not DOCKVIEW_STORE.exists():
        pytest.skip(f"useDockviewStore not found: {DOCKVIEW_STORE}")
    return DOCKVIEW_STORE.read_text()


class TestPresetDefinitions:
    """Four workspace presets with metadata."""

    def test_editing_preset(self, source):
        assert "'editing'" in source

    def test_color_preset(self, source):
        assert "'color'" in source

    def test_audio_preset(self, source):
        assert "'audio'" in source

    def test_custom_preset(self, source):
        assert "'custom'" in source

    def test_exactly_four_presets(self, source):
        """PRESETS array should have exactly 4 entries."""
        # Count name: 'xxx' patterns in PRESETS array
        names = re.findall(r"name:\s*'(\w+)'", source)
        assert len(names) == 4, f"Expected 4 presets, found {len(names)}: {names}"

    def test_each_has_label(self, source):
        """Each preset must have a label."""
        labels = re.findall(r"label:\s*'(\w+)'", source)
        assert len(labels) == 4

    def test_each_has_shortcut(self, source):
        """Each preset must have a shortcut hint."""
        shortcuts = re.findall(r"shortcut:\s*'([^']+)'", source)
        assert len(shortcuts) == 4

    def test_each_has_svg_icon(self, source):
        """Each preset must have an SVG path icon."""
        icons = re.findall(r"icon:\s*'([^']+)'", source)
        assert len(icons) == 4
        for icon in icons:
            assert icon.startswith("M"), f"SVG path should start with M: {icon[:20]}"


class TestPresetSwitching:
    """Verify preset switching mechanics."""

    def test_uses_dockview_store(self, source):
        """Must import from useDockviewStore."""
        assert "useDockviewStore" in source

    def test_reads_active_preset(self, source):
        """Must read activePreset from store."""
        assert "activePreset" in source

    def test_calls_set_active_preset(self, source):
        """Clicking preset must call setActivePreset."""
        assert "setActivePreset" in source

    def test_calls_load_layout(self, source):
        """Switching must call loadLayout to reconfigure panels."""
        assert "loadLayout" in source

    def test_calls_save_layout(self, source):
        """Must save current layout before switching."""
        assert "saveLayout" in source


class TestCustomPresetSave:
    """Custom preset: double-click to save current layout."""

    def test_double_click_handler(self, source):
        """Custom preset must support double-click to save."""
        assert re.search(r"onDoubleClick|dblclick|doubleClick", source, re.IGNORECASE)


class TestMonochromeCompliance:
    """All colors must be monochrome (grey palette)."""

    def test_no_color_hex(self, source):
        """No non-grey hex colors allowed."""
        # Extract all hex colors
        colors = re.findall(r"#([0-9a-fA-F]{3,8})", source)
        for c in colors:
            # Normalize to 6-char
            if len(c) == 3:
                c = c[0]*2 + c[1]*2 + c[2]*2
            if len(c) >= 6:
                r, g, b = int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16)
                # Grey: r ≈ g ≈ b (tolerance ±5)
                is_grey = (abs(r - g) <= 5 and abs(g - b) <= 5 and abs(r - b) <= 5)
                assert is_grey, f"Non-grey color #{c} found in WorkspacePresets"


class TestDockviewStoreContract:
    """Verify useDockviewStore provides required fields."""

    def test_active_preset_field(self, dockview_source):
        assert "activePreset" in dockview_source

    def test_set_active_preset_action(self, dockview_source):
        assert "setActivePreset" in dockview_source

    def test_load_layout_action(self, dockview_source):
        assert "loadLayout" in dockview_source

    def test_save_layout_action(self, dockview_source):
        assert "saveLayout" in dockview_source

    def test_workspace_preset_name_type(self, dockview_source):
        """WorkspacePresetName type must be exported."""
        assert "WorkspacePresetName" in dockview_source
