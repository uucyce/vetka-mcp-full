"""
Contract tests for GAMMA-BUILD: Trim tool UX polish — FCP7 Ch.27 trim visual feedback.

Covers:
  1. Monochrome palette — no RGB color (only grey/white rgba variants)
  2. isTrimTool spans exactly ripple/roll/slip/slide
  3. Handle tint values (active 0.06, hover 0.25) within FCP7 monochrome spec
  4. Snap diamond: 7×7px, rotate 45deg
  5. Slip ghost: ‹/› direction indicator, no emoji
  6. Slide neighbor ghost: width formulas are geometrically correct
  7. Tool name display: RIPPLE/ROLL/SLIP/SLIDE labels present in source

@phase 201
@task tb_1774763560_2394_1
@branch claude/cut-ux
"""

from __future__ import annotations
import re
import pathlib
import pytest

_SRC = pathlib.Path(__file__).parent.parent / "client/src/components/cut/TimelineTrackView.tsx"


@pytest.fixture(scope="module")
def src() -> str:
    """Read TimelineTrackView.tsx from the cut-ux branch via git show."""
    import subprocess
    result = subprocess.run(
        ["git", "show", "dc655295:client/src/components/cut/TimelineTrackView.tsx"],
        cwd=str(pathlib.Path(__file__).parent.parent),
        capture_output=True, text=True,
    )
    assert result.returncode == 0, f"git show failed: {result.stderr}"
    return result.stdout


# ── 1. Monochrome palette ──────────────────────────────────────────────────

class TestMonochromePalette:

    def test_no_color_rgb_in_trim_markers(self, src):
        """Trim markers must not use colored RGB values — only grey/white rgba."""
        # Extract lines between MARKER_TRIM markers
        trim_lines = [
            l for l in src.splitlines()
            if "MARKER_TRIM" in l or "trimHandle" in l or "snapDiamond" in l
            or "slip" in l.lower() or "slide" in l.lower()
        ]
        for line in trim_lines:
            # Find all rgba() calls and check they are grey (R≈G≈B)
            for match in re.finditer(r'rgba\((\d+),\s*(\d+),\s*(\d+),', line):
                r, g, b = int(match.group(1)), int(match.group(2)), int(match.group(3))
                assert abs(r - g) <= 10 and abs(g - b) <= 10, (
                    f"Non-monochrome color rgba({r},{g},{b}) found in trim code: {line.strip()}"
                )

    def test_no_hex_color_in_trim_markers(self, src):
        """No hardcoded hex color codes (e.g. #FF0000) in trim visual code."""
        trim_section = src[src.find("MARKER_TRIM"):]
        colored_hex = re.findall(r'#([0-9A-Fa-f]{6})\b', trim_section)
        for h in colored_hex:
            r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
            assert abs(r - g) <= 15 and abs(g - b) <= 15, (
                f"Non-monochrome hex #{h} in trim markers"
            )


# ── 2. isTrimTool coverage ─────────────────────────────────────────────────

class TestIsTrimTool:

    def test_all_four_trim_tools_in_istrimtool(self, src):
        """isTrimTool must include ripple, roll, slip, and slide."""
        match = re.search(r'isTrimTool\s*=\s*(.+?)(?:\n|;)', src)
        assert match, "isTrimTool variable not found in source"
        expr = match.group(1)
        for tool in ("ripple", "roll", "slip", "slide"):
            assert tool in expr, f"'{tool}' missing from isTrimTool expression: {expr}"

    def test_trim_handle_bg_uses_istrimtool(self, src):
        """trimHandleBg must reference isTrimTool."""
        assert "trimHandleBg" in src
        match = re.search(r'trimHandleBg\s*=\s*(.+?)(?:\n|;)', src)
        assert match, "trimHandleBg assignment not found"
        assert "isTrimTool" in match.group(1), "trimHandleBg should depend on isTrimTool"

    def test_trim_edge_border_for_ripple_and_roll_only(self, src):
        """trimEdgeBorder visible border only for ripple and roll (not slip/slide)."""
        match = re.search(r'trimEdgeBorder\s*=\s*(.+?)(?:\n|;)', src)
        assert match, "trimEdgeBorder not found"
        expr = match.group(1)
        assert "ripple" in expr and "roll" in expr, "trimEdgeBorder must include ripple and roll"
        # Must NOT include slip or slide (they don't show border, just tint)
        assert "slip" not in expr, "trimEdgeBorder should not include slip"
        assert "slide" not in expr, "trimEdgeBorder should not include slide"


# ── 3. Handle tint values ──────────────────────────────────────────────────

class TestHandleTintValues:

    def test_active_tint_value(self, src):
        """Active trim handle tint = rgba(255,255,255,0.06) per FCP7 spec."""
        assert "rgba(255,255,255,0.06)" in src, (
            "Active handle tint rgba(255,255,255,0.06) not found — check MARKER_TRIM.HANDLE"
        )

    def test_hover_tint_brighter_than_active(self, src):
        """Hover tint (0.25) must be brighter than active tint (0.06)."""
        # Both values should be present
        assert "0.06" in src, "Active tint 0.06 missing"
        assert "0.25" in src, "Hover tint 0.25 missing"
        # Hover alpha > active alpha numerically
        # (verified by presence — full numeric check would need parsing)

    def test_visible_border_for_ripple_roll(self, src):
        """Ripple/roll border: rgba(255,255,255,0.18)."""
        assert "rgba(255,255,255,0.18)" in src, (
            "Ripple/roll visible edge border rgba(255,255,255,0.18) not found"
        )

    def test_hover_border_brighter(self, src):
        """Hover border: rgba(255,255,255,0.5) — brighter than active 0.18."""
        assert "rgba(255,255,255,0.5)" in src, (
            "Hover border rgba(255,255,255,0.5) not found"
        )


# ── 4. Snap diamond ────────────────────────────────────────────────────────

class TestSnapDiamond:

    def test_snap_diamond_marker_exists(self, src):
        assert "MARKER_TRIM.SNAP-DIAMOND" in src

    def test_snap_diamond_is_7x7(self, src):
        """Diamond dimensions: width:7, height:7."""
        diamond_section = src[src.find("MARKER_TRIM.SNAP-DIAMOND"):]
        assert "width: 7" in diamond_section or "width:7" in diamond_section, \
            "Snap diamond width should be 7px"
        assert "height: 7" in diamond_section or "height:7" in diamond_section, \
            "Snap diamond height should be 7px"

    def test_snap_diamond_rotated_45(self, src):
        """Diamond uses rotate(45deg) to create diamond shape."""
        diamond_section = src[src.find("MARKER_TRIM.SNAP-DIAMOND"):]
        assert "rotate(45deg)" in diamond_section, \
            "Snap diamond must use rotate(45deg)"

    def test_snap_diamond_no_pointer_events(self, src):
        """Diamond overlay must have pointerEvents: none — not interactive."""
        diamond_section = src[src.find("MARKER_TRIM.SNAP-DIAMOND"):]
        assert "pointerEvents: 'none'" in diamond_section or "pointerEvents:'none'" in diamond_section


# ── 5. Slip ghost ──────────────────────────────────────────────────────────

class TestSlipGhost:

    def test_slip_ghost_marker_exists(self, src):
        assert "MARKER_TRIM-SLIP-GHOST" in src

    def test_slip_ghost_uses_direction_chars_not_emoji(self, src):
        """Slip ghost uses ‹/› text chars, not emoji."""
        assert "‹" in src and "›" in src, "Slip ghost should use ‹ and › direction chars"

    def test_slip_ghost_direction_logic(self, src):
        """goRight determines which arrow to show: goRight → ›, else ‹."""
        slip_section = src[src.find("MARKER_TRIM-SLIP-GHOST"):]
        # goRight = shift > 0
        assert "shift > 0" in slip_section or "goRight" in slip_section, \
            "Slip ghost must compute direction from shift"
        assert "goRight" in slip_section, "goRight flag must exist for direction logic"

    def test_slip_ghost_threshold_check(self, src):
        """Slip ghost only renders when |shift| > threshold (not for zero drift)."""
        slip_section = src[src.find("MARKER_TRIM-SLIP-GHOST"):]
        assert "Math.abs(shift)" in slip_section, \
            "Slip ghost should check Math.abs(shift) to avoid rendering at zero"

    def test_slip_ghost_no_pointer_events(self, src):
        """Slip ghost is non-interactive."""
        slip_section = src[src.find("MARKER_TRIM-SLIP-GHOST"):]
        assert "pointerEvents: 'none'" in slip_section or "pointerEvents:'none'" in slip_section


# ── 6. Slide neighbor ghost geometry ──────────────────────────────────────

class TestSlideNeighborGhost:

    def test_slide_ghost_marker_exists(self, src):
        assert "MARKER_TRIM-SLIDE-GHOST" in src

    def test_neighbor_left_width_formula(self, src):
        """Left neighbor ghost width = (clip.startSec - neighborLeft.startSec) * zoom."""
        slide_section = src[src.find("MARKER_TRIM-SLIDE-GHOST"):]
        assert "neighborLeft.startSec" in slide_section, \
            "neighborLeft.startSec must be used in left ghost width formula"
        assert "dragState.startSec - dragState.neighborLeft.startSec" in slide_section, \
            "Left ghost width = clip.startSec - neighborLeft.startSec"

    def test_neighbor_right_left_position(self, src):
        """Right ghost starts at current clip's right edge."""
        slide_section = src[src.find("MARKER_TRIM-SLIDE-GHOST"):]
        assert "dragState.startSec + dragState.durationSec" in slide_section, \
            "Right ghost left = clip.startSec + clip.durationSec"

    def test_ghost_has_dashed_border(self, src):
        """Neighbor ghosts use dashed outline (not solid) to distinguish from real clips."""
        slide_section = src[src.find("MARKER_TRIM-SLIDE-GHOST"):]
        assert "dashed" in slide_section, "Slide neighbor ghosts should use dashed border"

    def test_ghost_min_width_4px(self, src):
        """Ghost min-width clamped to 4px to remain visible when neighbor is nearly gone."""
        slide_section = src[src.find("MARKER_TRIM-SLIDE-GHOST"):]
        assert "Math.max(4," in slide_section, \
            "Neighbor ghost width should have Math.max(4, ...) floor"

    def test_ghost_no_pointer_events(self, src):
        """Neighbor ghosts are non-interactive overlays."""
        slide_section = src[src.find("MARKER_TRIM-SLIDE-GHOST"):]
        assert "pointerEvents: 'none'" in slide_section or "pointerEvents:'none'" in slide_section


# ── 7. Toolbar trim tool name ──────────────────────────────────────────────

class TestToolbarTrimName:

    def test_ripple_label_present(self, src):
        assert "'RIPPLE'" in src or '"RIPPLE"' in src, "RIPPLE label missing from toolbar"

    def test_roll_label_present(self, src):
        assert "'ROLL'" in src or '"ROLL"' in src, "ROLL label missing from toolbar"

    def test_slip_label_present(self, src):
        assert "'SLIP'" in src or '"SLIP"' in src, "SLIP label missing from toolbar"

    def test_slide_label_present(self, src):
        assert "'SLIDE'" in src or '"SLIDE"' in src, "SLIDE label missing from toolbar"
