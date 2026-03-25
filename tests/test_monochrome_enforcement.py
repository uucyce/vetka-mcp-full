"""
Contract test: Monochrome compliance for all .tsx and .css files in
client/src/components/cut/

Rules enforced:
  - All hex colors must be grey (R ≈ G ≈ B, tolerance ±8)
  - ALLOWED non-grey: playhead/error reds (dominant R, low G/B)
  - EXEMPT files: data-viz components listed in EXEMPT_FILES
  - Colors in // single-line comments or /* block comments */ are ignored
  - Colors in marker palette dicts (MARKER_COLORS, MarkerType maps) are
    allowed — they are semantic data-viz annotations, not UI chrome

Design principle: ZERO false positives — only flag active non-grey UI colors.
"""

import re
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

import pytest

# ── Paths ──────────────────────────────────────────────────────────────────

ROOT = Path(__file__).resolve().parent.parent
SCAN_DIR = ROOT / "client" / "src" / "components" / "cut"

# ── Exempt files (data-visualisation: coloured by design) ──────────────────
#
# Rules for adding a file here:
#   1. The file MUST exist on disk (test_exempt_files_exist_on_disk guards this).
#   2. The file MUST contain at least one active (non-comment) chromatic colour
#      (test_exempt_files_contain_chromatic_colors guards this).
#   3. All colours must be intentional data-visualisation — not UI chrome.
#
# Files removed from the original spec list because they use only grey tones
# in active code (chromatic colours were inside comments only):
#   - VideoScopes.tsx        → all hex in active code is grey
#   - BPMTrack.tsx           → chromatic colours (#5DCAA5 etc.) are in /* */ comment
#   - ColorCorrectionPanel.tsx → all hex in active code is grey
#
# File not found on disk:
#   - ColorCorrectorPanel.tsx → does not exist (codebase uses ColorCorrectionPanel.tsx)

EXEMPT_FILES: set = {
    "CamelotWheel.tsx",  # music key Camelot wheel — full hue spectrum is the feature
    "StorySpace3D.tsx",  # 3-D story graph — spatial colour coding by design
    "ColorWheel.tsx",    # colour grading sub-component — colour wheels are the UI
}

# ── Extra per-file allowlists (specific colours that are intentional) ───────
# Use lowercase normalised hex.  Values are (reason, set_of_normalised_hexes).
FILE_ALLOWLIST: dict = {
    # VU meter: industry-standard green / yellow / red signal levels
    "AudioLevelMeter.tsx": (
        "VU meter signal levels (green/yellow/red = industry standard)",
        {"22c55e", "eab308", "ef4444"},
    ),
    "AudioMixer.tsx": (
        "VU meter signal levels (green/yellow/red = industry standard)",
        {"22c55e", "eab308", "ef4444", "c44444"},
    ),
    # Marker colours are semantic timeline annotations (not UI chrome)
    "MarkerListPanel.tsx": (
        "Timeline marker palette — semantic annotation colours",
        {"f59e0b", "ef4444", "3b82f6", "a855f7", "22c55e", "94a3b8", "4a9eff"},
    ),
    "MarkerNode.tsx": (
        "Timeline marker node colours — semantic data-viz",
        {"8b5cf6", "ec4899", "f59e0b", "6b7280"},
    ),
    "TimelineTrackView.tsx": (
        "Timeline marker palette — semantic annotation colours",
        {"f59e0b", "ef4444", "8899aa", "a855f7", "22c55e", "94a3b8", "4a9eff", "9ca3af", "d1d5db"},
    ),
    "TranscriptOverlay.tsx": (
        "Transcript marker overlay palette — semantic annotation colours",
        {"f59e0b", "06b6d4", "a855f7", "22c55e", "64748b"},
    ),
    # Music analysis panels — camelot wheel, pendulum, BPM display
    "PulseInspector.tsx": (
        "Music analysis data: camelot key, pendulum, BPM display",
        {"5dcaa5", "efa830", "378add", "e24b4a", "7f77dd"},
    ),
    "DAGProjectPanel.tsx": (
        "DAG node colours — camelot key display (music data-viz)",
        {"5dcaa5"},
    ),
    # CodecProbeDetail — subtle tinted badges for video/audio/subtitle streams
    "CodecProbeDetail.tsx": (
        "Stream-type badge tints (video=green, audio=blue, sub=olive) — data encoding",
        {"1a2a1a", "6a8a6a", "1a1a2a", "6a6a8a", "2a2a1a", "8a8a6a"},
    ),
    # SaveIndicator — green/red/olive for save-state feedback
    "SaveIndicator.tsx": (
        "Save-state indicator: green=saved, red=error, olive=unsaved (system status UI)",
        {"4a4", "4aaa44", "c44", "cc4444", "886", "888866"},
    ),
    # LutBrowserPanel — reddish delete/warning button
    "LutBrowserPanel.tsx": (
        "LUT browser delete/warning button (red-tint accent)",
        {"633", "663333", "c66", "cc6666"},
    ),
    # ExportDialog — very dark blue-tinted highlight (#1f1f2a)
    "ExportDialog.tsx": (
        "Export format selected highlight — slight blue tint (#1f1f2a). "
        "Known deviation; tracked as MONO-EXPORT-01 for future cleanup.",
        {"1f1f2a"},
    ),
}

# ── Colour helpers ──────────────────────────────────────────────────────────

HEX_RE = re.compile(r"#[0-9a-fA-F]{3,8}\b")

# Matches a single-line comment: // ... to end of line
SINGLE_LINE_COMMENT_RE = re.compile(r"//.*$")

# Matches block comment contents
BLOCK_COMMENT_RE = re.compile(r"/\*.*?\*/", re.DOTALL)

# CSS comment: /* ... */
CSS_COMMENT_RE = re.compile(r"/\*.*?\*/", re.DOTALL)


def _strip_comments(text: str, filepath: Path) -> str:
    """Remove single-line and block comments, returning clean source."""
    # Strip block comments first (they can span lines)
    text = BLOCK_COMMENT_RE.sub(lambda m: "\n" * m.group().count("\n"), text)
    # Strip single-line comments line-by-line to preserve line numbers
    lines = text.splitlines()
    clean = []
    for line in lines:
        clean.append(SINGLE_LINE_COMMENT_RE.sub("", line))
    return "\n".join(clean)


def _normalise_hex(raw: str) -> str:
    """Expand shorthand hex to 6 digits (lowercase, no #)."""
    h = raw.lstrip("#").lower()
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    elif len(h) == 4:
        # 4-digit = #RGBA — strip alpha
        h = "".join(c * 2 for c in h[:3])
    elif len(h) == 8:
        # 8-digit = #RRGGBBAA — strip alpha
        h = h[:6]
    return h  # 6 hex digits


def _parse_rgb(raw: str) -> Optional[Tuple[int, int, int]]:
    """Return (R, G, B) tuple or None if the hex string is invalid."""
    h = _normalise_hex(raw)
    if len(h) != 6:
        return None
    try:
        r = int(h[0:2], 16)
        g = int(h[2:4], 16)
        b = int(h[4:6], 16)
        return r, g, b
    except ValueError:
        return None


def _is_grey(r: int, g: int, b: int, tolerance: int = 8) -> bool:
    """True if the colour is achromatic within the given tolerance."""
    return max(abs(r - g), abs(r - b), abs(g - b)) <= tolerance


def _is_allowed_red(r: int, g: int, b: int) -> bool:
    """
    Playhead / in/out marker red.
    Dominant red channel, low green and blue.
    Covers #cc3333, #c44, #ef4444 family when used as playhead/error.
    """
    return r >= 150 and g <= 100 and b <= 100


# ── Violation dataclass ─────────────────────────────────────────────────────

@dataclass
class ColorViolation:
    file: Path
    line_no: int
    raw_color: str
    rgb: Tuple[int, int, int]
    context: str

    def __str__(self) -> str:
        rel = self.file.relative_to(SCAN_DIR)
        r, g, b = self.rgb
        return (
            f"{rel}:{self.line_no}  {self.raw_color} rgb({r},{g},{b})"
            f"  →  {self.context.strip()[:90]}"
        )


# ── Core scanner ────────────────────────────────────────────────────────────

def _collect_violations(filepath: Path) -> List[ColorViolation]:
    """
    Scan a single file and return a list of ColorViolation objects.
    Skips colours inside comments and per-file allowlisted colours.
    """
    fname = filepath.name
    _, allowed_hex = FILE_ALLOWLIST.get(fname, ("", set()))

    text = filepath.read_text(errors="ignore")
    clean_text = _strip_comments(text, filepath)

    violations: List[ColorViolation] = []
    for line_no, line in enumerate(clean_text.splitlines(), start=1):
        for m in HEX_RE.finditer(line):
            raw = m.group()
            rgb = _parse_rgb(raw)
            if rgb is None:
                continue

            r, g, b = rgb
            norm = _normalise_hex(raw)

            # Skip grey
            if _is_grey(r, g, b):
                continue

            # Skip globally allowed playhead reds
            if _is_allowed_red(r, g, b):
                continue

            # Skip per-file allowlisted colours
            # Check both the 6-digit form and the original shorthand
            raw_norm_short = raw.lstrip("#").lower()
            if norm in allowed_hex or raw_norm_short in allowed_hex:
                continue

            original_line = text.splitlines()[line_no - 1]
            violations.append(ColorViolation(
                file=filepath,
                line_no=line_no,
                raw_color=raw,
                rgb=rgb,
                context=original_line,
            ))

    return violations


def _all_source_files() -> List[Path]:
    """Return all .tsx and .css files under SCAN_DIR, sorted."""
    files = []
    for ext in ("**/*.tsx", "**/*.css"):
        files.extend(SCAN_DIR.glob(ext))
    return sorted(set(files))


def _non_exempt_files() -> List[Path]:
    return [f for f in _all_source_files() if f.name not in EXEMPT_FILES]


# ═══════════════════════════════════════════════════════════════════════════
# TEST SUITE 1 — Global scan: every file at once
# ═══════════════════════════════════════════════════════════════════════════

class TestMonochromeScanAll:
    """
    Scans ALL .tsx and .css files in SCAN_DIR (excluding EXEMPT_FILES).
    Fails with a formatted report if any active non-grey colour is found
    outside an approved per-file allowlist entry.
    """

    def test_no_active_color_violations(self):
        """Zero non-grey active colours allowed across the entire cut component tree."""
        all_violations: List[ColorViolation] = []

        for filepath in _non_exempt_files():
            all_violations.extend(_collect_violations(filepath))

        if all_violations:
            lines = ["", "=" * 70, "MONOCHROME VIOLATIONS DETECTED", "=" * 70, ""]
            current_file = None
            for v in all_violations:
                rel = v.file.relative_to(SCAN_DIR)
                if rel != current_file:
                    current_file = rel
                    lines.append(f"\n  FILE: {rel}")
                lines.append(
                    f"    L{v.line_no:4d}  {v.raw_color:<10s} "
                    f"rgb{v.rgb}  →  {v.context.strip()[:80]}"
                )
            lines += [
                "",
                f"Total violations: {len(all_violations)} in "
                f"{len({v.file for v in all_violations})} file(s)",
                "",
                "Fix options:",
                "  1. Replace the colour with a grey equivalent",
                "  2. If it is intentional data-viz, add the file to EXEMPT_FILES",
                "     or add the colour to FILE_ALLOWLIST with a justification",
                "=" * 70,
            ]
            pytest.fail("\n".join(lines))

    def test_scan_dir_exists(self):
        """SCAN_DIR must exist — sanity guard."""
        assert SCAN_DIR.is_dir(), f"Component directory not found: {SCAN_DIR}"

    def test_at_least_one_tsx_file(self):
        """At least one .tsx file must be present — guards against misconfigured ROOT."""
        tsx_files = list(SCAN_DIR.glob("**/*.tsx"))
        assert tsx_files, f"No .tsx files found under {SCAN_DIR}"

    def test_at_least_one_css_file(self):
        """At least one .css file must be present."""
        css_files = list(SCAN_DIR.glob("**/*.css"))
        assert css_files, f"No .css files found under {SCAN_DIR}"


# ═══════════════════════════════════════════════════════════════════════════
# TEST SUITE 2 — Exemption integrity
# ═══════════════════════════════════════════════════════════════════════════

class TestMonochromeExemptions:
    """
    Verifies that exempt files:
      a) actually exist (no stale entries),
      b) contain at least one non-grey hex colour (justify their exemption),
      c) are not accidentally missing from EXEMPT_FILES.
    """

    def test_exempt_files_exist_on_disk(self):
        """Every entry in EXEMPT_FILES must correspond to a real file."""
        missing = []
        for name in EXEMPT_FILES:
            matches = list(SCAN_DIR.rglob(name))
            if not matches:
                missing.append(name)
        assert not missing, (
            f"Stale EXEMPT_FILES entries (files not found on disk): {missing}"
        )

    def test_exempt_files_contain_chromatic_colors(self):
        """
        Each exempt file must contain at least one non-grey hex colour.
        If it contains no colour at all, the exemption is unnecessary.
        """
        colorless_exemptions = []
        for name in EXEMPT_FILES:
            for filepath in SCAN_DIR.rglob(name):
                text = _strip_comments(filepath.read_text(errors="ignore"), filepath)
                has_chromatic = False
                for line in text.splitlines():
                    for m in HEX_RE.finditer(line):
                        rgb = _parse_rgb(m.group())
                        if rgb and not _is_grey(*rgb):
                            has_chromatic = True
                            break
                    if has_chromatic:
                        break
                if not has_chromatic:
                    colorless_exemptions.append(name)

        assert not colorless_exemptions, (
            f"These EXEMPT_FILES contain no chromatic colours — "
            f"remove them from EXEMPT_FILES:\n  {colorless_exemptions}"
        )

    def test_file_allowlist_entries_are_justified(self):
        """Every FILE_ALLOWLIST entry must have a non-empty reason string."""
        empty_reasons = [
            fname for fname, (reason, _) in FILE_ALLOWLIST.items() if not reason.strip()
        ]
        assert not empty_reasons, (
            f"FILE_ALLOWLIST entries missing justification: {empty_reasons}"
        )

    def test_file_allowlist_files_exist(self):
        """Every file in FILE_ALLOWLIST must exist on disk."""
        missing = []
        for fname in FILE_ALLOWLIST:
            matches = list(SCAN_DIR.rglob(fname))
            if not matches:
                missing.append(fname)
        assert not missing, (
            f"Stale FILE_ALLOWLIST entries (files not found): {missing}"
        )

    def test_file_allowlist_colors_are_actually_chromatic(self):
        """
        Every colour in FILE_ALLOWLIST must be non-grey.
        Grey colours in an allowlist are pointless bookkeeping noise.
        """
        grey_in_allowlist = []
        for fname, (reason, hexset) in FILE_ALLOWLIST.items():
            for h in hexset:
                rgb = _parse_rgb("#" + h)
                if rgb and _is_grey(*rgb):
                    grey_in_allowlist.append((fname, "#" + h))
        assert not grey_in_allowlist, (
            f"These allowlisted colours are already grey (remove them): "
            f"{grey_in_allowlist}"
        )


# ═══════════════════════════════════════════════════════════════════════════
# TEST SUITE 3 — Per-file parametrised (catches new non-compliant files)
# ═══════════════════════════════════════════════════════════════════════════

def _parametrize_files():
    """Generate (file_path, display_name) pairs for pytest parametrize."""
    if not SCAN_DIR.is_dir():
        return []
    return [
        pytest.param(f, id=str(f.relative_to(SCAN_DIR)))
        for f in _non_exempt_files()
    ]


class TestNewFileMonochrome:
    """
    Parametrised test — one test instance per .tsx/.css file.
    Any new file added to the codebase that contains an active non-grey
    colour will immediately show up as a named FAIL here.
    """

    @pytest.mark.parametrize("filepath", _parametrize_files())
    def test_file_is_monochrome_compliant(self, filepath: Path):
        """File must contain zero active non-grey hex colours (after comment stripping)."""
        violations = _collect_violations(filepath)
        if violations:
            rel = filepath.relative_to(SCAN_DIR)
            lines = [
                f"",
                f"Monochrome violation(s) in {rel}:",
                f"",
            ]
            for v in violations:
                r, g, b = v.rgb
                lines.append(
                    f"  L{v.line_no:4d}  {v.raw_color:<10s} rgb({r},{g},{b})"
                    f"  →  {v.context.strip()[:80]}"
                )
            lines += [
                "",
                "Remediation:",
                "  - Replace with a neutral grey (#NNN where N≈N≈N)",
                "  - OR add an entry to FILE_ALLOWLIST with a justification",
                "  - OR add to EXEMPT_FILES if this is a data-viz component",
            ]
            pytest.fail("\n".join(lines))


# ═══════════════════════════════════════════════════════════════════════════
# TEST SUITE 4 — Comment stripping correctness
# ═══════════════════════════════════════════════════════════════════════════

class TestCommentStripping:
    """Unit tests for the comment-stripping logic (prevents false positives)."""

    def test_single_line_comment_ignored(self):
        """Colours inside // comments must not be flagged."""
        fake_path = SCAN_DIR / "_fake.tsx"
        text = "const x = 1; // background was #ff0000 before refactor\n"

        # Simulate stripping
        clean = _strip_comments(text, fake_path)
        hex_matches = HEX_RE.findall(clean)
        assert "#ff0000" not in hex_matches, (
            "Colour inside // comment should be stripped"
        )

    def test_block_comment_ignored(self):
        """Colours inside /* */ comments must not be flagged."""
        fake_path = SCAN_DIR / "_fake.tsx"
        text = "/* old palette: #22c55e #eab308 */ const x = 1;\n"
        clean = _strip_comments(text, fake_path)
        for color in ["#22c55e", "#eab308"]:
            assert color not in clean, f"{color} should be stripped from block comment"

    def test_active_color_survives_stripping(self):
        """Active non-comment colours must survive stripping."""
        fake_path = SCAN_DIR / "_fake.tsx"
        text = 'const style = { color: "#22c55e" }; // active\n'
        clean = _strip_comments(text, fake_path)
        # The string inside quotes is NOT a comment, must survive
        assert "#22c55e" in clean

    def test_grey_color_passes(self):
        """Pure grey colour must not be a violation."""
        rgb = _parse_rgb("#888888")
        assert rgb is not None
        assert _is_grey(*rgb)

    def test_chromatic_color_fails(self):
        """A vivid colour must be detected as chromatic."""
        rgb = _parse_rgb("#22c55e")  # green
        assert rgb is not None
        assert not _is_grey(*rgb)

    def test_allowed_red_passes(self):
        """Playhead / error red must pass the allowed-red gate."""
        for hex_color in ["#cc3333", "#c44", "#ef4444"]:
            rgb = _parse_rgb(hex_color)
            assert rgb is not None, f"Could not parse {hex_color}"
            r, g, b = rgb
            assert _is_allowed_red(r, g, b), f"{hex_color} should be allowed red"

    def test_green_not_allowed_red(self):
        """Green must NOT pass the allowed-red gate."""
        rgb = _parse_rgb("#22c55e")
        assert rgb is not None
        assert not _is_allowed_red(*rgb)

    def test_blue_not_allowed_red(self):
        """Blue must NOT pass the allowed-red gate."""
        rgb = _parse_rgb("#3b82f6")
        assert rgb is not None
        assert not _is_allowed_red(*rgb)

    def test_shorthand_hex_expanded_correctly(self):
        """3-digit shorthand #abc → #aabbcc."""
        assert _normalise_hex("#abc") == "aabbcc"

    def test_eight_digit_hex_alpha_stripped(self):
        """8-digit hex #rrggbbaa → 6-digit #rrggbb."""
        assert _normalise_hex("#aabbccdd") == "aabbcc"

    def test_css_zero_color_is_grey(self):
        """#000 must be grey."""
        assert _is_grey(*_parse_rgb("#000"))

    def test_white_is_grey(self):
        """#ffffff must be grey."""
        assert _is_grey(*_parse_rgb("#ffffff"))


# ═══════════════════════════════════════════════════════════════════════════
# Standalone runner (python tests/test_monochrome_enforcement.py)
# ═══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import sys

    print(f"Scanning: {SCAN_DIR}")
    print(f"Exempt files: {sorted(EXEMPT_FILES)}\n")

    files = _non_exempt_files()
    total_violations: List[ColorViolation] = []

    for f in files:
        vs = _collect_violations(f)
        if vs:
            print(f"FAIL  {f.relative_to(SCAN_DIR)}")
            for v in vs:
                print(f"      L{v.line_no:4d}  {v.raw_color:<10s} rgb{v.rgb}")
                print(f"             {v.context.strip()[:90]}")
            total_violations.extend(vs)
        else:
            print(f"ok    {f.relative_to(SCAN_DIR)}")

    print(f"\n{'PASS' if not total_violations else 'FAIL'} — "
          f"{len(total_violations)} violation(s) in {len(files)} files scanned")
    sys.exit(0 if not total_violations else 1)
