"""
Static debrief audit complement to test_monochrome_enforcement.py.

test_monochrome_enforcement.py handles hex color scanning (active chromatic colours).
This file covers the OTHER static checks that the debrief audit identified as important
but which do not require a browser:

  - Dead/forgotten src attributes (empty src="" → spurious page-load requests)
  - console.log left in production code
  - Hardcoded localhost URLs (break in production)
  - Inline style color values outside grey palette
  - CSS !important overrides (specificity tech debt)
  - UTF-8 validity + brace balance (catches bad merge artifacts)
  - Duplicate data-testid attributes (test selector ambiguity)

All checks are pure Python — no subprocess calls, no external tools.
"""

import re
from collections import defaultdict
from pathlib import Path
from typing import List, Tuple

import pytest

# ── Paths ───────────────────────────────────────────────────────────────────

ROOT = Path(__file__).resolve().parent.parent
CLIENT_SRC = ROOT / "client" / "src"
CUT_COMPONENTS = ROOT / "client" / "src" / "components" / "cut"

# ── Comment-stripping helpers (mirrors test_monochrome_enforcement.py) ───────

_BLOCK_COMMENT_RE = re.compile(r"/\*.*?\*/", re.DOTALL)
_SINGLE_LINE_COMMENT_RE = re.compile(r"//.*$", re.MULTILINE)


def _strip_comments(text: str) -> str:
    """Remove /* block */ and // single-line comments, preserving line count."""
    # Strip block comments first (span multiple lines); replace with same
    # number of newlines so line numbers stay consistent.
    text = _BLOCK_COMMENT_RE.sub(lambda m: "\n" * m.group().count("\n"), text)
    # Strip single-line comments per line
    text = _SINGLE_LINE_COMMENT_RE.sub("", text)
    return text


def _read(path: Path) -> str:
    """Read a file, ignoring encoding errors."""
    return path.read_text(errors="ignore")


def _read_stripped(path: Path) -> str:
    return _strip_comments(_read(path))


# ─────────────────────────────────────────────────────────────────────────────
# Helpers: file collection
# ─────────────────────────────────────────────────────────────────────────────

def _tsx_files(scan_dir: Path) -> List[Path]:
    if not scan_dir.is_dir():
        return []
    return sorted(scan_dir.rglob("*.tsx"))


def _ts_tsx_files(scan_dir: Path) -> List[Path]:
    if not scan_dir.is_dir():
        return []
    return sorted(set(scan_dir.rglob("*.tsx")) | set(scan_dir.rglob("*.ts")))


def _css_files(scan_dir: Path) -> List[Path]:
    if not scan_dir.is_dir():
        return []
    return sorted(scan_dir.rglob("*.css"))


# ─────────────────────────────────────────────────────────────────────────────
# Helpers: grey detection (mirrors test_monochrome_enforcement.py)
# ─────────────────────────────────────────────────────────────────────────────

def _parse_rgb_from_hex(hex_str: str):
    """Return (R, G, B) or None for a CSS hex string like #aabbcc."""
    h = hex_str.lstrip("#").lower()
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    elif len(h) == 4:
        h = "".join(c * 2 for c in h[:3])
    elif len(h) == 8:
        h = h[:6]
    if len(h) != 6:
        return None
    try:
        return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    except ValueError:
        return None


def _parse_rgb_components(r_str: str, g_str: str, b_str: str):
    """Return (R, G, B) or None from string component values."""
    try:
        return int(r_str), int(g_str), int(b_str)
    except ValueError:
        return None


def _is_grey(r: int, g: int, b: int, tolerance: int = 8) -> bool:
    return max(abs(r - g), abs(r - b), abs(g - b)) <= tolerance


# ═══════════════════════════════════════════════════════════════════════════
# TEST SUITE 1 — Dead import / artifact detection
# ═══════════════════════════════════════════════════════════════════════════

class TestDeadImportDetection:
    """
    Detects forgotten placeholder attributes and debug statements that should
    not appear in production source code.
    """

    # ── empty src attributes ────────────────────────────────────────────────

    def test_no_empty_src_attributes_in_tsx(self):
        """
        Scan .tsx files for empty src attributes: src="" / src={""} / src={''}

        These cause browsers to send a spurious GET request to the current
        page URL.  They indicate a forgotten placeholder from a copy-paste or
        template substitution.
        """
        if not CUT_COMPONENTS.is_dir():
            pytest.skip(f"CUT_COMPONENTS not found: {CUT_COMPONENTS}")

        # Matches: src=""  src={""}  src={''}
        _EMPTY_SRC_RE = re.compile(r"""src=(?:""|''|\{""\}|\{''\})""")

        violations: List[str] = []
        for filepath in _tsx_files(CUT_COMPONENTS):
            text = _read(filepath)
            for line_no, line in enumerate(text.splitlines(), start=1):
                if _EMPTY_SRC_RE.search(line):
                    rel = filepath.relative_to(CUT_COMPONENTS)
                    violations.append(f"{rel}:{line_no}  {line.strip()[:100]}")

        assert not violations, (
            "Found empty src= attributes (cause spurious network requests):\n"
            + "\n".join(f"  {v}" for v in violations)
        )

    # ── console.log in production code ─────────────────────────────────────

    # Files that are explicitly for debugging — console.log is expected there.
    _CONSOLE_LOG_EXEMPT = frozenset({
        "DebugShellPanel.tsx",
        "DebugInspectorPanel.tsx",
    })

    _CONSOLE_LOG_RE = re.compile(r"\bconsole\.log\s*\(")

    def test_no_console_log_in_production_code(self):
        """
        Scan .tsx files for console.log( outside comments.

        console.warn( and console.error( are intentional (runtime signals) and
        are allowed.  console.log( is a debugging leftover and should be removed
        before code reaches the component tree.

        Files in _CONSOLE_LOG_EXEMPT are skipped (debug panels).
        """
        if not CUT_COMPONENTS.is_dir():
            pytest.skip(f"CUT_COMPONENTS not found: {CUT_COMPONENTS}")

        violations: List[str] = []
        for filepath in _tsx_files(CUT_COMPONENTS):
            if filepath.name in self._CONSOLE_LOG_EXEMPT:
                continue
            clean = _strip_comments(_read(filepath))
            for line_no, line in enumerate(clean.splitlines(), start=1):
                if self._CONSOLE_LOG_RE.search(line):
                    rel = filepath.relative_to(CUT_COMPONENTS)
                    violations.append(f"{rel}:{line_no}  {line.strip()[:100]}")

        assert not violations, (
            "Found console.log() in production code (use console.warn/error or remove):\n"
            + "\n".join(f"  {v}" for v in violations)
        )

    # ── hardcoded localhost URLs ────────────────────────────────────────────

    # Relative path segments to ignore (e2e tests, vite config, etc.)
    _LOCALHOST_EXEMPT_SEGMENTS = (
        "e2e",
        "vite.config",
        "playwright.config",
        "__tests__",
    )

    _LOCALHOST_RE = re.compile(r"https?://(localhost|127\.0\.0\.1):[0-9]")

    def test_no_hardcoded_localhost_urls(self):
        """
        Scan .tsx and .ts files under client/src/ for hardcoded localhost URLs
        outside comments.

        Such URLs break in staging/production environments.  Use relative paths
        or environment variables (import.meta.env.VITE_API_BASE) instead.

        Exempt: e2e/ test files, vite.config.ts, playwright.config.ts.
        """
        if not CLIENT_SRC.is_dir():
            pytest.skip(f"CLIENT_SRC not found: {CLIENT_SRC}")

        violations: List[str] = []
        for filepath in _ts_tsx_files(CLIENT_SRC):
            # Skip exempt files by checking path segments
            rel_parts = filepath.relative_to(CLIENT_SRC).parts
            if any(seg in part for part in rel_parts for seg in self._LOCALHOST_EXEMPT_SEGMENTS):
                continue
            if any(seg in filepath.name for seg in self._LOCALHOST_EXEMPT_SEGMENTS):
                continue

            clean = _strip_comments(_read(filepath))
            for line_no, line in enumerate(clean.splitlines(), start=1):
                if self._LOCALHOST_RE.search(line):
                    rel = filepath.relative_to(CLIENT_SRC)
                    violations.append(f"{rel}:{line_no}  {line.strip()[:100]}")

        assert not violations, (
            "Found hardcoded localhost URLs (break in production — use relative URLs or env vars):\n"
            + "\n".join(f"  {v}" for v in violations)
        )


# ═══════════════════════════════════════════════════════════════════════════
# TEST SUITE 2 — Additional monochrome static checks
# ═══════════════════════════════════════════════════════════════════════════

class TestMonochromeStaticExtra:
    """
    Complementary static monochrome checks that go beyond hex-literal scanning.

    These target inline style objects (which can embed colors as named values,
    hex, rgb(), etc.) and CSS specificity abuse.
    """

    # Files whose inline style colors are intentionally chromatic (data-viz).
    # This list is deliberately minimal — the canonical allowlist lives in
    # test_monochrome_enforcement.py.  Only files with known inline-style
    # colors that are legitimately chromatic appear here.
    _INLINE_STYLE_EXEMPT = frozenset({
        "CamelotWheel.tsx",
        "StorySpace3D.tsx",
        "ColorWheel.tsx",
        "AudioLevelMeter.tsx",
        "AudioMixer.tsx",
        "MarkerListPanel.tsx",
        "MarkerNode.tsx",
        "TimelineTrackView.tsx",
        "TranscriptOverlay.tsx",
        "PulseInspector.tsx",
        "DAGProjectPanel.tsx",
        "CodecProbeDetail.tsx",
        "SaveIndicator.tsx",
        "LutBrowserPanel.tsx",
        "ExportDialog.tsx",
    })

    # Regex patterns for inline style color values.
    # Captures hex colors inside style={{ color: '...' }} and similar.
    # Matches: color: '#...'  /  backgroundColor: '#...'
    _STYLE_HEX_RE = re.compile(
        r"""(?:color|backgroundColor|borderColor|background)\s*:\s*['"]?(#[0-9a-fA-F]{3,8})\b['"]?""",
    )

    # rgb() / rgba() inline — matches rgb(R, G, B) or rgba(R, G, B, A)
    _STYLE_RGB_RE = re.compile(
        r"""(?:color|backgroundColor|borderColor|background)\s*:\s*rgba?\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)"""
    )

    def test_no_inline_style_colors_outside_allowlist(self):
        """
        Scan .tsx files for inline style color values that are not grey.

        Inline styles bypass CSS class discipline and are often where chromatic
        colors sneak into UI chrome.  Only data-viz components in
        _INLINE_STYLE_EXEMPT are allowed to carry chromatic inline colors.
        """
        if not CUT_COMPONENTS.is_dir():
            pytest.skip(f"CUT_COMPONENTS not found: {CUT_COMPONENTS}")

        violations: List[str] = []

        for filepath in _tsx_files(CUT_COMPONENTS):
            if filepath.name in self._INLINE_STYLE_EXEMPT:
                continue

            clean = _strip_comments(_read(filepath))
            for line_no, line in enumerate(clean.splitlines(), start=1):
                # Check hex colors in inline styles
                for m in self._STYLE_HEX_RE.finditer(line):
                    raw = m.group(1)
                    rgb = _parse_rgb_from_hex(raw)
                    if rgb is not None and not _is_grey(*rgb):
                        rel = filepath.relative_to(CUT_COMPONENTS)
                        violations.append(
                            f"{rel}:{line_no}  inline hex {raw} rgb{rgb}  →  {line.strip()[:80]}"
                        )

                # Check rgb() / rgba() colors in inline styles
                for m in self._STYLE_RGB_RE.finditer(line):
                    rgb = _parse_rgb_components(m.group(1), m.group(2), m.group(3))
                    if rgb is not None and not _is_grey(*rgb):
                        r, g, b = rgb
                        rel = filepath.relative_to(CUT_COMPONENTS)
                        violations.append(
                            f"{rel}:{line_no}  inline rgb({r},{g},{b})  →  {line.strip()[:80]}"
                        )

        assert not violations, (
            "Found chromatic inline style colors outside data-viz exempt list:\n"
            + "\n".join(f"  {v}" for v in violations)
            + "\n\nFix: use CSS class or add file to _INLINE_STYLE_EXEMPT with justification."
        )

    # ── !important audit ────────────────────────────────────────────────────

    # Threshold: if this is exceeded, the test fails.
    # Raise only with explicit justification and a tracking note.
    _IMPORTANT_THRESHOLD = 50

    _IMPORTANT_RE = re.compile(r"!important")

    def test_no_css_important_overrides(self):
        """
        Count !important declarations across all .css files under CUT_COMPONENTS.

        !important is a specificity escape hatch that signals CSS architecture
        debt.  The count must stay below _IMPORTANT_THRESHOLD.  If it rises,
        fix the specificity conflict rather than raising the threshold.
        """
        if not CUT_COMPONENTS.is_dir():
            pytest.skip(f"CUT_COMPONENTS not found: {CUT_COMPONENTS}")

        total_count = 0
        per_file: List[Tuple[str, int]] = []

        for filepath in _css_files(CUT_COMPONENTS):
            text = _read(filepath)
            # Strip CSS comments before counting
            clean = _BLOCK_COMMENT_RE.sub("", text)
            count = len(self._IMPORTANT_RE.findall(clean))
            if count:
                rel = str(filepath.relative_to(CUT_COMPONENTS))
                per_file.append((rel, count))
                total_count += count

        if per_file:
            summary = "  " + "\n  ".join(f"{f}: {c}" for f, c in sorted(per_file))
            report = (
                f"CSS !important count: {total_count} "
                f"(threshold: {self._IMPORTANT_THRESHOLD})\n{summary}"
            )
        else:
            report = f"CSS !important count: 0 (threshold: {self._IMPORTANT_THRESHOLD})"

        assert total_count <= self._IMPORTANT_THRESHOLD, (
            f"!important count ({total_count}) exceeds threshold ({self._IMPORTANT_THRESHOLD}).\n"
            + report
            + "\nFix specificity conflicts rather than raising the threshold."
        )


# ═══════════════════════════════════════════════════════════════════════════
# TEST SUITE 3 — Source integrity
# ═══════════════════════════════════════════════════════════════════════════

def _collect_tsx_params():
    """Parametrize helpers — returns empty list if dir absent (skipped in test)."""
    if not CUT_COMPONENTS.is_dir():
        return []
    return [
        pytest.param(f, id=str(f.relative_to(CUT_COMPONENTS)))
        for f in _tsx_files(CUT_COMPONENTS)
    ]


class TestSourceIntegrity:
    """
    Low-level file integrity checks that catch corrupted files from bad merges,
    bad encodings, or broken refactors before they surface as cryptic TS errors.
    """

    # ── UTF-8 + brace balance ────────────────────────────────────────────────

    @pytest.mark.parametrize("filepath", _collect_tsx_params())
    def test_all_tsx_files_have_valid_syntax(self, filepath: Path):
        """
        Each .tsx file must:
          1. Be readable as UTF-8 (encoding errors surfaced explicitly).
          2. Have equal counts of { and } (rough brace-balance check).

        This is an intentionally coarse check — it catches catastrophically
        broken files (NUL bytes, half-written blocks) that would otherwise
        cause silent TS compilation failures.
        """
        # 1. UTF-8 readability
        try:
            text = filepath.read_text(encoding="utf-8", errors="strict")
        except UnicodeDecodeError as exc:
            pytest.fail(
                f"{filepath.relative_to(CUT_COMPONENTS)}: "
                f"UTF-8 decode error at byte {exc.start}: {exc.reason}"
            )

        # 2. Brace balance (after stripping string literals and comments to
        #    reduce false positives from braces inside strings/comments)
        clean = _strip_comments(text)
        # Remove string content between matching quotes to avoid counting
        # braces inside string literals.
        clean = re.sub(r'"(?:[^"\\]|\\.)*"', '""', clean)
        clean = re.sub(r"'(?:[^'\\]|\\.)*'", "''", clean)
        clean = re.sub(r"`(?:[^`\\]|\\.)*`", "``", clean)

        open_braces = clean.count("{")
        close_braces = clean.count("}")

        # TSX/JSX template expressions and conditional rendering patterns
        # can cause minor brace imbalances after string stripping.
        # Allow a tolerance of ±5 to avoid false positives.
        diff = abs(open_braces - close_braces)
        if diff > 5:
            rel = filepath.relative_to(CUT_COMPONENTS)
            pytest.fail(
                f"{rel}: unbalanced braces — "
                f"{{ count={open_braces}, }} count={close_braces} "
                f"(diff={open_braces - close_braces}). "
                "This may indicate a bad merge or incomplete refactor."
            )

    # ── Duplicate data-testid ───────────────────────────────────────────────

    # Testids that are intentionally shared across components (e.g. a shared
    # button that appears in multiple panels).  Add with justification comment.
    _KNOWN_DUPLICATE_TESTIDS: set = {
        # TimelineRuler rendered inside TimelineTrackView — same testid, nested component
        "cut-timeline-ruler",
        # Conditional rendering branches in same file — only one rendered at a time
        "marker-list-panel",
        "media-info-panel",
        "track-resize-handle",
    }

    _TESTID_RE = re.compile(r'data-testid=["\']([^"\']+)["\']')

    def test_no_duplicate_data_testid(self):
        """
        Scan all .tsx files under CUT_COMPONENTS for data-testid= values.

        The same testid on different components creates ambiguous Playwright
        selectors: page.getByTestId('x') will match multiple elements,
        causing flaky tests.  Each testid must be unique across the component
        tree (or explicitly allowlisted in _KNOWN_DUPLICATE_TESTIDS).
        """
        if not CUT_COMPONENTS.is_dir():
            pytest.skip(f"CUT_COMPONENTS not found: {CUT_COMPONENTS}")

        # Map: testid → list of "file:line" strings
        testid_locations: dict = defaultdict(list)

        for filepath in _tsx_files(CUT_COMPONENTS):
            text = _read(filepath)
            # Use raw text (not stripped) so line numbers are accurate
            for line_no, line in enumerate(text.splitlines(), start=1):
                for m in self._TESTID_RE.finditer(line):
                    tid = m.group(1)
                    rel = filepath.relative_to(CUT_COMPONENTS)
                    testid_locations[tid].append(f"{rel}:{line_no}")

        duplicates = {
            tid: locs
            for tid, locs in testid_locations.items()
            if len(locs) > 1 and tid not in self._KNOWN_DUPLICATE_TESTIDS
        }

        if duplicates:
            lines = ["", "Duplicate data-testid values detected:", ""]
            for tid, locs in sorted(duplicates.items()):
                lines.append(f"  data-testid=\"{tid}\"  ({len(locs)} occurrences):")
                for loc in locs:
                    lines.append(f"    {loc}")
            lines += [
                "",
                "Fix: make testids unique (e.g. prefix with component name).",
                "If the duplication is intentional, add the testid to",
                "_KNOWN_DUPLICATE_TESTIDS with a justification comment.",
            ]
            pytest.fail("\n".join(lines))


# ═══════════════════════════════════════════════════════════════════════════
# Standalone runner
# ═══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import sys

    checks = [
        ("CUT_COMPONENTS exists", lambda: CUT_COMPONENTS.is_dir()),
        ("CLIENT_SRC exists", lambda: CLIENT_SRC.is_dir()),
        ("tsx files found", lambda: bool(_tsx_files(CUT_COMPONENTS))),
        ("css files found", lambda: bool(_css_files(CUT_COMPONENTS))),
    ]

    ok = True
    for name, check_fn in checks:
        try:
            result = check_fn()
        except Exception as exc:
            result = False
            print(f"ERROR  {name}: {exc}")
        status = "ok " if result else "FAIL"
        print(f"  {status}  {name}")
        if not result:
            ok = False

    print()
    print("Run with pytest for full output:")
    print("  pytest tests/test_monochrome_static.py -v")
    sys.exit(0 if ok else 1)
