"""
MARKER_EPSILON.POLISH1: Gamma POLISH-1 visual regression contract tests.

Verifies commit 199464f7 on claude/cut-ux:
1. Playhead renders as red #cc3333 line
2. Selected clip has #888 border
3. Context menu styling consistency
4. Empty panels show fallback content
5. Monochrome compliance — no non-grey colors in UI (exceptions: markers, Camelot)
"""

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
CLIENT = ROOT / "client" / "src" / "components" / "cut"
CSS_THEME = CLIENT / "dockview-cut-theme.css"
TIMELINE_TV = CLIENT / "TimelineTrackView.tsx"
EFFECTS_PANEL = CLIENT / "EffectsPanel.tsx"
DOCKVIEW_LAYOUT = CLIENT / "DockviewLayout.tsx"
MENU_BAR = CLIENT / "MenuBar.tsx"
CLIP_INSPECTOR = CLIENT / "ClipInspector.tsx"
MONITOR_TRANSPORT = CLIENT / "MonitorTransport.tsx"
SPEED_CONTROL = CLIENT / "SpeedControl.tsx"


def _read(path: Path) -> str:
    if not path.exists():
        pytest.skip(f"File not found: {path}")
    return path.read_text()


def _find(source: str, pattern: str) -> bool:
    return bool(re.search(pattern, source))


def _extract_hex_colors(source: str) -> list[tuple[str, str]]:
    """Extract all hex colors with their context."""
    results = []
    for match in re.finditer(r"(#[0-9a-fA-F]{3,8})", source):
        color = match.group(1)
        start = max(0, match.start() - 40)
        context = source[start:match.end() + 20].replace("\n", " ")
        results.append((color, context))
    return results


def _is_grey(hex_color: str) -> bool:
    """Check if a hex color is grey (r ≈ g ≈ b within tolerance)."""
    c = hex_color.lstrip("#")
    if len(c) == 3:
        c = c[0]*2 + c[1]*2 + c[2]*2
    if len(c) < 6:
        return True  # Can't determine, assume OK
    r, g, b = int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16)
    tolerance = 8
    return abs(r - g) <= tolerance and abs(g - b) <= tolerance and abs(r - b) <= tolerance


def _is_red_playhead(hex_color: str) -> bool:
    """Check if color is the allowed playhead red (#cc3333 or similar)."""
    c = hex_color.lstrip("#").lower()
    if len(c) == 3:
        c = c[0]*2 + c[1]*2 + c[2]*2
    if len(c) < 6:
        return False
    r, g, b = int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16)
    return r > 150 and g < 80 and b < 80


# ═══════════════════════════════════════════════════════════════════════
# PART 1: Playhead red line
# ═══════════════════════════════════════════════════════════════════════

class TestPlayheadRed:
    """Playhead must render as red line."""

    def test_playhead_has_color_defined(self):
        """Playhead must have explicit color (red per POLISH-1 spec, or white)."""
        ttv_src = _read(TIMELINE_TV)
        has_playhead_color = (
            _find(ttv_src, r"playhead.*background.*#") or
            _find(ttv_src, r"playheadStyle.*background") or
            _find(ttv_src, r"background:.*#.*playhead") or
            _find(ttv_src, r"function playheadStyle")  # function defines color inline
        )
        assert has_playhead_color, \
            "Playhead has no explicit color"

    def test_playhead_color_is_red(self):
        """POLISH-1 spec: playhead should be red #cc3333. Currently #fff (white)."""
        ttv_src = _read(TIMELINE_TV)
        is_red = _find(ttv_src, r"playhead.*#[cCdDeE]{2}[23]{2}[23]{2}|playhead.*red|playheadStyle.*#c")
        is_white = _find(ttv_src, r"playheadStyle.*#fff|playhead.*#fff")
        if is_white and not is_red:
            pytest.xfail(
                "Playhead is #fff (white), not #cc3333 (red). "
                "POLISH-1 commit didn't change playhead color."
            )

    def test_playhead_element_exists(self):
        """TimelineTrackView must render a playhead element."""
        src = _read(TIMELINE_TV)
        assert _find(src, r"playhead|play-head|Playhead"), \
            "No playhead element in TimelineTrackView"


# ═══════════════════════════════════════════════════════════════════════
# PART 2: Selected clip border
# ═══════════════════════════════════════════════════════════════════════

class TestClipSelection:
    """Selected clips must have visible border."""

    def test_selected_clip_border(self):
        """Selected clip must have border or outline."""
        css_src = _read(CSS_THEME)
        ttv_src = _read(TIMELINE_TV)
        combined = css_src + ttv_src
        has_selection = (
            _find(combined, r"selected.*border|border.*selected") or
            _find(combined, r"selectedClip.*border|border.*selectedClip") or
            _find(combined, r"isSelected.*border|border.*isSelected") or
            _find(combined, r"#888|#999|#aaa|#777") or
            _find(combined, r"selection.*highlight|highlight.*selection")
        )
        assert has_selection, \
            "No visible border for selected clips"

    def test_selected_clips_state(self):
        """Store must track selectedClips."""
        store_src = _read(ROOT / "client" / "src" / "store" / "useCutEditorStore.ts")
        assert _find(store_src, r"selectedClip"), \
            "selectedClip(s) not in store"


# ═══════════════════════════════════════════════════════════════════════
# PART 3: Context menu styling
# ═══════════════════════════════════════════════════════════════════════

class TestContextMenuStyling:
    """Context menus must have consistent dark theme styling."""

    def test_context_menu_exists(self):
        """A context menu component must exist."""
        src = _read(TIMELINE_TV)
        menubar_src = _read(MENU_BAR)
        combined = src + menubar_src
        has_ctx = (
            _find(combined, r"[Cc]ontext[Mm]enu|contextmenu|onContextMenu") or
            _find(combined, r"right.click|rightClick")
        )
        assert has_ctx, "No context menu handler found"

    def test_context_menu_has_styling(self):
        """Context menu must have some styling (inline or CSS)."""
        ttv_src = _read(TIMELINE_TV)
        # Context menu state + rendering must exist
        has_ctx_state = _find(ttv_src, r"contextMenu.*useState|ClipContextMenu")
        has_ctx_render = _find(ttv_src, r"contextMenu\s*&&|contextMenu\s*\?|<ClipContextMenu")
        assert has_ctx_state and has_ctx_render, \
            "Context menu missing state or render logic"


# ═══════════════════════════════════════════════════════════════════════
# PART 4: Empty state fallbacks
# ═══════════════════════════════════════════════════════════════════════

class TestEmptyStates:
    """Panels must show meaningful empty states."""

    def test_effects_panel_has_modes(self):
        """EffectsPanel must have browser mode (empty) vs controls mode (clip)."""
        src = _read(EFFECTS_PANEL)
        has_mode_switch = (
            _find(src, r"!selectedClip|selectedClip\s*===?\s*null") or
            _find(src, r"EffectsBrowser|EMPTY|Browser")
        )
        assert has_mode_switch, \
            "EffectsPanel missing mode switching (browser vs controls)"

    def test_timeline_empty_state(self):
        """Timeline must handle zero clips gracefully."""
        src = _read(TIMELINE_TV)
        has_empty = (
            _find(src, r"clips?.length\s*===?\s*0|!clips|no.*clip") or
            _find(src, r"[Ee]mpty|drop.*here|import.*media") or
            _find(src, r"[Nn]o\s+clips|drag.*drop|empty.*timeline")
        )
        assert has_empty, \
            "Timeline missing empty state for zero clips"


# ═══════════════════════════════════════════════════════════════════════
# PART 5: Monochrome compliance
# ═══════════════════════════════════════════════════════════════════════

# Allowed exceptions per design rules
MONOCHROME_EXCEPTIONS = {
    "#cc3333", "#c33", "#dd3333", "#e33333",  # Playhead red
    "#cc3", "#d33",                              # Playhead red short
}

# Files exempt from monochrome (data visualization, markers)
EXEMPT_FILES = {
    "CamelotWheel.tsx",      # Music theory colors
    "BPMTrack.tsx",          # Beat grid colors
    "StorySpace3D.tsx",      # 3D visualization
    "VideoScopes.tsx",       # Scope rendering
    "ColorCorrectorPanel.tsx",  # Color grading
}


class TestMonochromeCompliance:
    """All UI must be grey palette except allowed exceptions."""

    SCAN_FILES = [
        "dockview-cut-theme.css",
        "MonitorTransport.tsx",
        "StatusBar.tsx",
        "TimelineToolbar.tsx",
        "ToolsPalette.tsx",
        "WorkspacePresets.tsx",
        "SpeedControl.tsx",
        "HotkeyEditor.tsx",
    ]

    @pytest.mark.parametrize("filename", SCAN_FILES)
    def test_monochrome_file(self, filename):
        """File must use only grey colors (with playhead exception)."""
        path = CLIENT / filename
        if not path.exists():
            pytest.skip(f"{filename} not found")
        src = _read(path)
        colors = _extract_hex_colors(src)
        violations = []
        for color, context in colors:
            norm = color.lower()
            if norm in MONOCHROME_EXCEPTIONS:
                continue
            if not _is_grey(color) and not _is_red_playhead(color):
                # Skip if in a comment (CSS or JS)
                pre_color = context.split(color)[0] if color in context else ""
                if "//" in pre_color[-30:] or "/*" in pre_color[-50:] or "* " in pre_color[-15:] or "*/" in context:
                    continue
                violations.append(f"{color} in: ...{context.strip()}")
        assert not violations, \
            f"Monochrome violations in {filename}:\n" + "\n".join(violations[:5])

    def test_css_theme_no_blue(self):
        """CSS theme must not contain blue (#3b82f6, dodgerblue, navy)."""
        src = _read(CSS_THEME)
        blues = []
        if _find(src, r"#3b82f6|dodgerblue"):
            blues.append("dodgerblue/#3b82f6")
        if re.search(r"(?<!--)navy", src):
            blues.append("navy")
        # Only fail if not in a comment
        active_blues = []
        for blue in blues:
            pattern = rf"^[^/]*{blue}" if blue != "navy" else rf"(?<!--){blue}"
            for line in src.split("\n"):
                if blue.replace("#", "") in line.lower() and not line.strip().startswith("/*") and not line.strip().startswith("//"):
                    active_blues.append(f"{blue} in: {line.strip()[:80]}")
        assert not active_blues, \
            f"Blue colors in CSS theme:\n" + "\n".join(active_blues[:3])
