"""
Tier markers contract test — audits marker coverage across the test suite.

Rules:
- PASSES even if some files lack markers (documents gaps, does not fail).
- Reports unmarked files as warnings via pytest.warns / print output.
- Counts tests per tier and exposes them as pytest output.

Tiers defined in pytest.ini:
    unit        — fast, no browser, no backend
    integration — store-level tests (needs __CUT_STORE__ or backend)
    e2e         — full browser E2E (needs Playwright + dev server)
    smoke       — quick sanity checks
    tdd_red     — intentionally failing (acceptance criteria)
"""
from __future__ import annotations

import ast
import importlib.util
import re
import sys
from pathlib import Path
from typing import Dict, List, Set

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).parent.parent
TESTS_DIR = REPO_ROOT / "tests"

KNOWN_TIERS: Set[str] = {"unit", "integration", "e2e", "smoke", "tdd_red"}

# Markers that indicate a file is intentionally not tier-classified
EXEMPT_MARKERS: Set[str] = {"stale"}

# Pattern to detect pytest.mark.<name> usage in source text
_MARK_PATTERN = re.compile(r"pytest\.mark\.(\w+)")


def _collect_markers_from_source(path: Path) -> Set[str]:
    """Return all pytest marker names referenced in *path* via static text scan."""
    try:
        source = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return set()
    return set(_MARK_PATTERN.findall(source))


def _collect_markers_from_ast(path: Path) -> Set[str]:
    """Return markers applied at class/function level via AST (decorator scan)."""
    found: Set[str] = set()
    try:
        tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"))
    except SyntaxError:
        return found

    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            continue
        for deco in node.decorator_list:
            # @pytest.mark.xxx  →  Attribute node
            if (
                isinstance(deco, ast.Attribute)
                and isinstance(deco.value, ast.Attribute)
                and isinstance(deco.value.value, ast.Name)
                and deco.value.value.id == "pytest"
                and deco.value.attr == "mark"
            ):
                found.add(deco.attr)
            # @pytest.mark.xxx(...)  →  Call node
            elif isinstance(deco, ast.Call):
                func = deco.func
                if (
                    isinstance(func, ast.Attribute)
                    and isinstance(func.value, ast.Attribute)
                    and isinstance(func.value.value, ast.Name)
                    and func.value.value.id == "pytest"
                    and func.value.attr == "mark"
                ):
                    found.add(func.attr)
    return found


def _scan_all_test_files() -> Dict[Path, Set[str]]:
    """Return {file: set_of_marker_names} for every test_*.py in TESTS_DIR."""
    result: Dict[Path, Set[str]] = {}
    for path in sorted(TESTS_DIR.glob("test_*.py")):
        if path.name == Path(__file__).name:
            continue  # skip self
        # Combine AST + regex for robustness (parametrize strings etc.)
        markers = _collect_markers_from_ast(path) | _collect_markers_from_source(path)
        result[path] = markers
    return result


# ---------------------------------------------------------------------------
# Contract tests
# ---------------------------------------------------------------------------


class TestTierMarkersContract:
    """Audit tier marker coverage — document gaps, do not block the suite."""

    def test_pytest_ini_declares_all_tiers(self):
        """pytest.ini must declare all KNOWN_TIERS as registered markers."""
        ini_path = REPO_ROOT / "pytest.ini"
        assert ini_path.exists(), "pytest.ini not found at repo root"
        content = ini_path.read_text(encoding="utf-8")
        missing = [t for t in sorted(KNOWN_TIERS) if t not in content]
        assert not missing, (
            f"pytest.ini is missing marker declarations for: {missing}\n"
            f"Add them under the [markers] section."
        )

    def test_tier_counts_are_reportable(self, capsys):
        """Scan all test files and print tier coverage — always passes."""
        file_markers = _scan_all_test_files()

        tier_counts: Dict[str, int] = {t: 0 for t in KNOWN_TIERS}
        unmarked_files: List[str] = []

        for path, markers in file_markers.items():
            tier_hits = markers & KNOWN_TIERS
            exempt_hits = markers & EXEMPT_MARKERS

            if tier_hits:
                for t in tier_hits:
                    if t in tier_counts:
                        tier_counts[t] += 1
            elif not exempt_hits:
                unmarked_files.append(path.name)

        # Report
        with capsys.disabled():
            print("\n" + "=" * 60)
            print("TIER MARKER COVERAGE REPORT")
            print("=" * 60)
            for tier, count in sorted(tier_counts.items()):
                bar = "#" * min(count, 40)
                print(f"  {tier:<12} {count:>4} files  {bar}")
            print("-" * 60)
            total = len(file_markers)
            covered = total - len(unmarked_files)
            pct = (covered / total * 100) if total else 0
            print(f"  Coverage: {covered}/{total} files ({pct:.0f}%)")
            if unmarked_files:
                print(f"\n  UNMARKED FILES ({len(unmarked_files)}):")
                for name in sorted(unmarked_files):
                    print(f"    - {name}")
            print("=" * 60)

        # The test always passes — gaps are documented, not enforced
        assert True

    def test_unmarked_file_count_is_tracked(self, record_property):
        """Record the number of unmarked files as a JUnit property for CI tracking."""
        file_markers = _scan_all_test_files()
        unmarked = [
            p.name
            for p, markers in file_markers.items()
            if not (markers & KNOWN_TIERS) and not (markers & EXEMPT_MARKERS)
        ]
        record_property("unmarked_test_files", len(unmarked))
        record_property("total_test_files", len(file_markers))
        # Always passes — just records the metric
        assert True

    def test_known_tier_markers_are_valid_identifiers(self):
        """All tier names must be valid Python identifiers (sanity check)."""
        for tier in KNOWN_TIERS:
            assert tier.isidentifier(), f"Tier name {tier!r} is not a valid identifier"

    def test_cut_specific_files_have_markers_or_are_documented(self, capsys):
        """CUT-domain test files without markers are surfaced as a named list."""
        cut_prefixes = ("test_cut_", "test_jkl_", "test_hotkey_", "test_match_",
                        "test_import_media_", "test_dockview_")
        file_markers = _scan_all_test_files()

        unmarked_cut: List[str] = []
        for path, markers in file_markers.items():
            if any(path.name.startswith(p) for p in cut_prefixes):
                if not (markers & KNOWN_TIERS) and not (markers & EXEMPT_MARKERS):
                    unmarked_cut.append(path.name)

        with capsys.disabled():
            if unmarked_cut:
                print(f"\n  CUT files lacking tier markers ({len(unmarked_cut)}):")
                for name in sorted(unmarked_cut):
                    print(f"    [WARN] {name}")
            else:
                print("\n  All CUT domain files have tier markers.")

        # Document only — does not fail the suite
        assert True
