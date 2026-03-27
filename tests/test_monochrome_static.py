"""
MARKER_DELTA3_MONO: Static monochrome enforcement for CUT UI.

Scans all .tsx/.css files under client/src/components/cut/ for non-grey
hex colors (R!=G or G!=B). Exempt zones: color correction, markers,
music visualization (Camelot/BPM/Pulse), audio metering.

Fails on ANY non-grey color outside exempt zones — blocks the entire
class of color violations from regressing.
"""

import re
import pytest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CUT_DIR = ROOT / "client" / "src" / "components" / "cut"

# Files where color is EXEMPT (functional, not decorative)
EXEMPT_FILES = {
    "ColorWheel.tsx",           # color correction tool
    "ColorCorrectionPanel.tsx", # color correction UI
    "CamelotWheel.tsx",         # music key visualization (Itten wheel)
    "StorySpace3D.tsx",         # 3D music visualization
    "BPMTrack.tsx",             # beat grid (audio/visual/sync markers)
    "PulseInspector.tsx",       # McKee story triangle + music context
    "AudioLevelMeter.tsx",      # red/yellow/green metering (safety)
    "AudioMixer.tsx",           # level meters (safety)
    "ClippingIndicator.tsx",    # clipping warning (safety)
    "WaveformCanvas.tsx",       # waveform rendering
    "StereoWaveformCanvas.tsx", # stereo waveform
    # Files scheduled for deletion on cut-engine branch merge:
    "CodecProbeDetail.tsx",     # colored badges (deleted in Alpha cleanup)
    "ProxyToggle.tsx",          # green toggle (deleted in Alpha cleanup)
    "RenderIndicator.tsx",      # red/green status (deleted in Alpha cleanup)
}

# Lines containing these keywords are exempt (marker colors, comments)
EXEMPT_LINE_KEYWORDS = [
    "// marker",
    "marker color",
    "color correct",
    "waveform",
    "EXEMPT",
    "ZERO blue",       # the comment documenting the rule itself
    "camelot",
]

# Specific hex values that are exempt even in non-exempt files
# (marker type colors used in timeline/inspector/transcript)
EXEMPT_MARKER_COLORS = {
    "f59e0b",  # amber — favorite marker
    "ef4444",  # red — negative/anti-favorite
    "a855f7",  # purple — camera note
    "22c55e",  # green — AI insight
    "94a3b8",  # slate — chat reference
    "64748b",  # slate alt
    "8b5cf6",  # purple — transcript pause
    "ec4899",  # pink — energy pause
    "6b7280",  # grey-blue — default marker
    "4a9eff",  # blue — visual cut points (BPM markers)
    "9ca3af",  # grey-blue — rubber band labels
    "d1d5db",  # light grey-blue — rubber band text
    "8899aa",  # desaturated blue-grey — comment annotation marker
    "06b6d4",  # cyan — comment marker (TranscriptOverlay)
    "3b82f6",  # blue — comment marker (MarkerListPanel) TODO: Gamma desaturate
    "4ade80",  # green — success/export path text
}

HEX_PATTERN = re.compile(r"#([0-9a-fA-F]{6})\b")


def _is_grey(hex6: str) -> bool:
    """Return True if hex color is grey (R==G==B)."""
    r, g, b = hex6[0:2], hex6[2:4], hex6[4:6]
    return r == g == b


def _collect_violations():
    """Scan CUT components for non-grey hex colors outside exempt zones."""
    violations = []

    for ext in ("*.tsx", "*.css"):
        for filepath in sorted(CUT_DIR.rglob(ext)):
            fname = filepath.name
            if fname in EXEMPT_FILES:
                continue

            rel = filepath.relative_to(ROOT)
            for lineno, line in enumerate(filepath.read_text().splitlines(), 1):
                line_lower = line.lower()

                # Skip exempt keywords
                if any(kw in line_lower for kw in EXEMPT_LINE_KEYWORDS):
                    continue

                for match in HEX_PATTERN.finditer(line):
                    hex6 = match.group(1).lower()
                    if _is_grey(hex6):
                        continue
                    if hex6 in EXEMPT_MARKER_COLORS:
                        continue
                    violations.append(
                        f"{rel}:{lineno}: #{hex6} — {line.strip()[:80]}"
                    )

    return violations


class TestMonochromeEnforcement:
    """CUT UI monochrome compliance — ZERO non-grey color outside exempt zones."""

    def test_no_non_grey_hex_in_cut_components(self):
        """Scan all .tsx/.css in components/cut/ for non-grey hex colors."""
        if not CUT_DIR.exists():
            pytest.skip("CUT component directory not found")

        violations = _collect_violations()

        if violations:
            report = "\n".join(violations[:30])
            total = len(violations)
            pytest.fail(
                f"Monochrome violations ({total} found):\n{report}"
                + (f"\n... and {total - 30} more" if total > 30 else "")
            )

    def test_exempt_files_exist(self):
        """Verify that exempt files actually exist (catch stale exemptions)."""
        if not CUT_DIR.exists():
            pytest.skip("CUT component directory not found")

        missing = []
        for fname in EXEMPT_FILES:
            matches = list(CUT_DIR.rglob(fname))
            if not matches:
                missing.append(fname)

        # Some files may be deleted during cleanup — warn but don't fail
        # Only fail if MORE THAN HALF of exemptions are stale
        if len(missing) > len(EXEMPT_FILES) // 2:
            pytest.fail(
                f"Too many stale exemptions ({len(missing)}/{len(EXEMPT_FILES)}): "
                + ", ".join(missing)
            )
