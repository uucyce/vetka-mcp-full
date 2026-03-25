"""
MARKER_EPSILON.H1: FCP7 hotkey mapping compliance tests.

Verifies that FCP7_PRESET and PREMIERE_PRESET in useCutHotkeys.ts
match the official FCP7 User Manual (Ch.18-19, Ch.44, App.A)
and Premiere Pro defaults.

These tests parse the TypeScript source directly to avoid drift
between test expectations and actual code.

Context:
- FCP7 manual: R=Ripple, RR=Roll (double-tap not supported in web, Shift+R used)
- FCP7 manual: A=Selection, B=Razor, Y=Slip, U=Slide
- Premiere: V=Selection, C=Razor, B=Ripple, N=Roll
- Coverage matrix: docs/190_ph_CUT_WORKFLOW_ARCH/CUT_FCP7_COVERAGE_MATRIX.md
"""

import re
from pathlib import Path

import pytest

# Path to hotkey source file
HOTKEYS_FILE = Path(__file__).resolve().parent.parent / "client" / "src" / "hooks" / "useCutHotkeys.ts"


def _parse_preset(source: str, preset_name: str) -> dict[str, str]:
    """Extract key bindings from a named preset in the TS source."""
    # Find the preset object
    pattern = rf"export const {preset_name}:\s*HotkeyMap\s*=\s*\{{(.*?)\}};"
    match = re.search(pattern, source, re.DOTALL)
    if not match:
        pytest.fail(f"Could not find {preset_name} in source")
    block = match.group(1)

    # Parse key: 'value' pairs (handles single-quote value like extractClip: "'")
    bindings = {}
    for line in block.split("\n"):
        line = line.strip()
        if not line or line.startswith("//") or line.startswith("/*"):
            continue
        # Match action: 'binding' or action: "binding"
        m = re.match(r"""(\w+):\s*(?:'([^']*)'|"([^"]*)")""", line)
        if m:
            bindings[m.group(1)] = m.group(2) if m.group(2) is not None else m.group(3)
    return bindings


@pytest.fixture(scope="module")
def source():
    """Read hotkey source file."""
    if not HOTKEYS_FILE.exists():
        pytest.skip(f"Hotkey file not found: {HOTKEYS_FILE}")
    return HOTKEYS_FILE.read_text()


@pytest.fixture(scope="module")
def fcp7(source):
    return _parse_preset(source, "FCP7_PRESET")


@pytest.fixture(scope="module")
def premiere(source):
    return _parse_preset(source, "PREMIERE_PRESET")


class TestFCP7TrimToolMapping:
    """FCP7 Ch.44: Trim tool key assignments."""

    def test_r_maps_to_ripple(self, fcp7):
        """FCP7 manual: R = Ripple Edit tool."""
        assert fcp7["rippleTool"] == "r", \
            f"FCP7 R should be Ripple, got {fcp7.get('rippleTool')}"

    def test_roll_accessible(self, fcp7):
        """FCP7 manual: RR = Roll (double-tap not in web, Shift+R substitute)."""
        assert "rollTool" in fcp7, "rollTool must exist in FCP7 preset"
        # Shift+r is acceptable web substitute for double-tap RR
        assert fcp7["rollTool"] in ("Shift+r", "rr"), \
            f"Roll should be Shift+r or rr, got {fcp7['rollTool']}"

    def test_slip_tool_exists(self, fcp7):
        """FCP7 uses SS for slip. Web substitute: Y."""
        assert "slipTool" in fcp7
        assert fcp7["slipTool"] == "y"

    def test_slide_tool_exists(self, fcp7):
        """FCP7 uses SSS for slide. Web substitute: U."""
        assert "slideTool" in fcp7
        assert fcp7["slideTool"] == "u"


class TestFCP7CoreTools:
    """FCP7 App.A: Core tool bindings."""

    def test_selection_tool(self, fcp7):
        """FCP7: A = Selection (Arrow) tool."""
        assert fcp7["selectTool"] == "a"

    def test_razor_tool(self, fcp7):
        """FCP7: B = Blade (Razor) tool."""
        assert fcp7["razorTool"] == "b"


class TestFCP7Playback:
    """FCP7 App.A: JKL shuttle."""

    def test_jkl_shuttle(self, fcp7):
        assert fcp7["shuttleBack"] == "j"
        assert fcp7["stop"] == "k"
        assert fcp7["shuttleForward"] == "l"
        assert fcp7["playPause"] == "Space"

    def test_frame_step(self, fcp7):
        assert fcp7["frameStepBack"] == "ArrowLeft"
        assert fcp7["frameStepForward"] == "ArrowRight"


class TestFCP7Marking:
    """FCP7 App.A: Mark In/Out/Clip."""

    def test_mark_in_out(self, fcp7):
        assert fcp7["markIn"] == "i"
        assert fcp7["markOut"] == "o"

    def test_mark_clip(self, fcp7):
        assert fcp7["markClip"] == "x"

    def test_go_to_in_out(self, fcp7):
        assert fcp7["goToIn"] == "Shift+i"
        assert fcp7["goToOut"] == "Shift+o"

    def test_clear_in_out(self, fcp7):
        assert fcp7["clearInOut"] == "Alt+x"


class TestFCP7Editing:
    """FCP7 App.A: Core editing operations."""

    def test_split_at_playhead(self, fcp7):
        """FCP7: Ctrl+V = Add Edit (split at playhead)."""
        assert fcp7["splitClip"] == "Ctrl+v"

    def test_insert_overwrite(self, fcp7):
        assert fcp7["insertEdit"] == ","
        assert fcp7["overwriteEdit"] == "."

    def test_lift_extract(self, fcp7):
        assert fcp7["liftClip"] == ";"
        assert fcp7["extractClip"] == "'"

    def test_match_frame(self, fcp7):
        """FCP7: F = Match Frame."""
        assert fcp7["matchFrame"] == "f"

    def test_toggle_source_program(self, fcp7):
        """FCP7: Q = toggle Source/Program viewer."""
        assert fcp7["toggleSourceProgram"] == "q"


class TestFCP7Navigation:
    """FCP7 App.A: Navigation keys."""

    def test_edit_points(self, fcp7):
        assert fcp7["prevEditPoint"] == "ArrowUp"
        assert fcp7["nextEditPoint"] == "ArrowDown"

    def test_start_end(self, fcp7):
        assert fcp7["goToStart"] == "Home"
        assert fcp7["goToEnd"] == "End"


class TestPremierePreset:
    """Premiere Pro defaults for comparison."""

    def test_selection_tool(self, premiere):
        assert premiere["selectTool"] == "v"

    def test_razor_tool(self, premiere):
        assert premiere["razorTool"] == "c"

    def test_ripple_roll(self, premiere):
        """Premiere: B=Ripple, Shift+N=Roll (N reserved for toggleSnap)."""
        assert premiere["rippleTool"] == "b"
        assert premiere["rollTool"] == "Shift+n"

    def test_split(self, premiere):
        """Premiere: Cmd+K = Add Edit."""
        assert premiere["splitClip"] == "Cmd+k"


class TestNoCollisions:
    """Verify no two actions share the same key binding within a preset."""

    def test_fcp7_no_collisions(self, fcp7):
        seen: dict[str, str] = {}
        collisions = []
        for action, key in fcp7.items():
            if key in seen:
                collisions.append(f"{key}: {seen[key]} vs {action}")
            seen[key] = action
        assert not collisions, f"FCP7 key collisions: {collisions}"

    def test_premiere_no_collisions(self, premiere):
        seen: dict[str, str] = {}
        collisions = []
        for action, key in premiere.items():
            if key in seen:
                collisions.append(f"{key}: {seen[key]} vs {action}")
            seen[key] = action
        assert not collisions, f"Premiere key collisions: {collisions}"
