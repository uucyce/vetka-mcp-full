#!/usr/bin/env python3
"""
CUT QA Pyramid — 3-tier merge gate.

Tier 1: Static (0.1s)  — monochrome, imports, contract patterns
Tier 2: Build  (6s)    — vite build, missing exports
Tier 3: E2E    (8s+)   — Playwright smoke suite (requires live server)

Usage:
    python scripts/cut_qa_pyramid.py                 # run tier 1+2 (default gate)
    python scripts/cut_qa_pyramid.py --tier 1        # static only
    python scripts/cut_qa_pyramid.py --tier 2        # build only
    python scripts/cut_qa_pyramid.py --tier 3        # playwright smoke
    python scripts/cut_qa_pyramid.py --tier 1 2 3    # full pyramid
    python scripts/cut_qa_pyramid.py --branch claude/cut-engine  # gate a specific branch
    python scripts/cut_qa_pyramid.py --json          # machine-readable output

Exit codes:
    0 = all tiers PASS
    1 = at least one tier FAIL
    2 = infrastructure error

Designed for REFLEX integration:
    tool_id: cut_qa_pyramid
    triggers: action=merge_request, action=verify
    returns: { tiers: [...], verdict: "PASS"|"FAIL", duration_ms: N }
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional


# ---------------------------------------------------------------------------
# Config — adapt per project
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CLIENT_DIR = PROJECT_ROOT / "client"
PYTEST_BIN = os.environ.get("PYTEST_BIN", "python -m pytest")

# Tier 1: static test files (fast, no server needed)
TIER1_TESTS = [
    "tests/test_monochrome_static.py",
    "tests/test_cut_new_components.py",
]

# Tier 2: build tests (vite build, ~6s)
TIER2_TESTS = [
    "tests/test_cut_build_smoke.py",
]

# Tier 3: Playwright smoke (needs vite dev + FastAPI)
TIER3_CMD = (
    "node node_modules/@playwright/test/cli.js test "
    "--config=client/playwright.config.ts "
    "--workers=1 --grep=smoke --reporter=json"
)

# Monochrome grey-only regex (hex colors where R=G=B or standard greys)
_GREY_HEX = re.compile(
    r"#([0-9a-fA-F])\1\1"           # #aaa
    r"|#([0-9a-fA-F]{2})\2\2"       # #aaaaaa
    r"|#0[0-9a-fA-F]0[0-9a-fA-F]0[0-9a-fA-F]"  # near-black
)
_ANY_HEX = re.compile(r"#[0-9a-fA-F]{3,8}")

# Line-level exempt patterns (markers, color correction data)
MONOCHROME_EXEMPT_LINES = {"MARKER_COLORS", "color correction", "markers exempt"}

# File-level exemptions: color correction, data visualization, scopes
# These components legitimately use color (FCP7 monochrome rule: "except color correction and markers")
MONOCHROME_EXEMPT_FILES = {
    "ColorWheel.tsx", "ColorCorrectionPanel.tsx", "ColorCurves.tsx",
    "VideoScopes.tsx", "WaveformCanvas.tsx", "StereoWaveformCanvas.tsx",
    "BPMTrack.tsx", "CamelotWheel.tsx", "PulseInspector.tsx",
    "StorySpace3D.tsx", "DAGProjectPanel.tsx",  # Camelot viz data
    "AudioLevelMeter.tsx", "AudioMixer.tsx",  # VU metering (green/yellow/red standard)
    "TranscriptOverlay.tsx",  # Speaker color-coding (data viz)
}

# CUT component directories to scan
CUT_COMPONENT_DIRS = [
    CLIENT_DIR / "src" / "components" / "cut",
]


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class TierResult:
    tier: int
    name: str
    passed: bool
    duration_ms: int
    tests_run: int = 0
    tests_passed: int = 0
    tests_failed: int = 0
    failures: list[str] = field(default_factory=list)
    error: Optional[str] = None


@dataclass
class PyramidResult:
    verdict: str  # PASS | FAIL | ERROR
    tiers: list[TierResult] = field(default_factory=list)
    total_duration_ms: int = 0
    branch: Optional[str] = None


# ---------------------------------------------------------------------------
# Tier 1: Static analysis (monochrome + import validation)
# ---------------------------------------------------------------------------

def _scan_monochrome_violations(dirs: list[Path]) -> list[str]:
    """Scan .tsx/.css files for non-grey hex colors."""
    violations = []
    for d in dirs:
        if not d.exists():
            continue
        for ext in ("*.tsx", "*.css", "*.ts"):
            for f in d.rglob(ext):
                # Skip exempt files (color correction, data viz)
                if f.name in MONOCHROME_EXEMPT_FILES:
                    continue
                try:
                    lines = f.read_text(encoding="utf-8").splitlines()
                except (OSError, UnicodeDecodeError):
                    continue
                for i, line in enumerate(lines, 1):
                    # Skip exempt lines
                    if any(ex in line for ex in MONOCHROME_EXEMPT_LINES):
                        continue
                    for match in _ANY_HEX.finditer(line):
                        hex_val = match.group().lower()
                        if not _is_grey(hex_val):
                            rel = f.relative_to(PROJECT_ROOT)
                            violations.append(f"{rel}:{i}: {hex_val}")
    return violations


def _is_grey(hex_color: str) -> bool:
    """Check if a hex color is grey (R=G=B or near-equal channels)."""
    h = hex_color.lstrip("#")
    if len(h) == 3:
        return h[0] == h[1] == h[2]
    if len(h) == 6:
        r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
        # Allow near-grey (delta <= 2 per channel for antialiasing)
        return max(r, g, b) - min(r, g, b) <= 2
    if len(h) == 8:  # with alpha
        r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
        return max(r, g, b) - min(r, g, b) <= 2
    return True  # unknown format, don't flag


def run_tier1() -> TierResult:
    """Tier 1: Static checks — monochrome + pytest static tests."""
    t0 = time.monotonic()
    failures = []
    tests_run = 0
    tests_passed = 0

    # 1a. Monochrome scan (in-process, fast)
    violations = _scan_monochrome_violations(CUT_COMPONENT_DIRS)
    tests_run += 1
    if violations:
        failures.append(f"monochrome: {len(violations)} violations")
        for v in violations[:10]:
            failures.append(f"  {v}")
    else:
        tests_passed += 1

    # 1b. Run pytest static tests
    for test_file in TIER1_TESTS:
        test_path = PROJECT_ROOT / test_file
        if not test_path.exists():
            continue
        tests_run += 1
        result = subprocess.run(
            f"{PYTEST_BIN} {test_path} -q --tb=line",
            shell=True, capture_output=True, text=True,
            timeout=30, cwd=PROJECT_ROOT,
        )
        if result.returncode == 0:
            tests_passed += 1
        else:
            # Extract failure summary
            for line in result.stdout.splitlines()[-5:]:
                if "FAILED" in line or "failed" in line:
                    failures.append(line.strip())

    duration_ms = int((time.monotonic() - t0) * 1000)
    return TierResult(
        tier=1, name="static",
        passed=len(failures) == 0,
        duration_ms=duration_ms,
        tests_run=tests_run,
        tests_passed=tests_passed,
        tests_failed=tests_run - tests_passed,
        failures=failures,
    )


# ---------------------------------------------------------------------------
# Tier 2: Vite build
# ---------------------------------------------------------------------------

def run_tier2() -> TierResult:
    """Tier 2: Vite build smoke test."""
    t0 = time.monotonic()
    failures = []
    tests_run = 0
    tests_passed = 0

    for test_file in TIER2_TESTS:
        test_path = PROJECT_ROOT / test_file
        if not test_path.exists():
            failures.append(f"missing: {test_file}")
            continue
        tests_run += 1
        result = subprocess.run(
            f"{PYTEST_BIN} {test_path} -q --tb=short",
            shell=True, capture_output=True, text=True,
            timeout=60, cwd=PROJECT_ROOT,
        )
        if result.returncode == 0:
            tests_passed += 1
        else:
            for line in result.stdout.splitlines()[-10:]:
                if "FAILED" in line or "Missing export" in line or "Error" in line:
                    failures.append(line.strip())

    duration_ms = int((time.monotonic() - t0) * 1000)
    return TierResult(
        tier=2, name="build",
        passed=len(failures) == 0,
        duration_ms=duration_ms,
        tests_run=tests_run,
        tests_passed=tests_passed,
        tests_failed=tests_run - tests_passed,
        failures=failures,
    )


# ---------------------------------------------------------------------------
# Tier 3: Playwright E2E
# ---------------------------------------------------------------------------

def run_tier3() -> TierResult:
    """Tier 3: Playwright smoke suite (requires live server)."""
    t0 = time.monotonic()

    # Check if playwright is available
    pw_cli = PROJECT_ROOT / "node_modules" / "@playwright" / "test" / "cli.js"
    if not pw_cli.exists():
        # Try worktree paths
        for wt in (PROJECT_ROOT.parent / "cut-engine", PROJECT_ROOT.parent / "cut-ux"):
            candidate = wt / "client" / "node_modules" / "@playwright" / "test" / "cli.js"
            if candidate.exists():
                pw_cli = candidate
                break

    if not pw_cli.exists():
        return TierResult(
            tier=3, name="e2e",
            passed=False,
            duration_ms=int((time.monotonic() - t0) * 1000),
            error="playwright not found — install with: npm i -D @playwright/test",
        )

    result = subprocess.run(
        f"node {pw_cli} test --config=client/playwright.config.ts "
        f"--workers=1 --grep=smoke --reporter=json",
        shell=True, capture_output=True, text=True,
        timeout=120, cwd=PROJECT_ROOT,
    )

    tests_run = 0
    tests_passed = 0
    tests_failed = 0
    failures = []

    try:
        report = json.loads(result.stdout)
        for suite in report.get("suites", []):
            for spec in suite.get("specs", []):
                tests_run += 1
                ok = spec.get("ok", False)
                if ok:
                    tests_passed += 1
                else:
                    tests_failed += 1
                    failures.append(spec.get("title", "unknown"))
    except (json.JSONDecodeError, KeyError):
        # Fallback: parse text output
        for line in result.stderr.splitlines() + result.stdout.splitlines():
            if "failed" in line.lower() and "test" in line.lower():
                failures.append(line.strip())
        if result.returncode != 0 and not failures:
            failures.append(f"playwright exited {result.returncode}")

    duration_ms = int((time.monotonic() - t0) * 1000)
    return TierResult(
        tier=3, name="e2e",
        passed=tests_failed == 0 and tests_run > 0,
        duration_ms=duration_ms,
        tests_run=tests_run,
        tests_passed=tests_passed,
        tests_failed=tests_failed,
        failures=failures[:10],
    )


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

TIER_RUNNERS = {1: run_tier1, 2: run_tier2, 3: run_tier3}


def run_pyramid(
    tiers: list[int] | None = None,
    branch: str | None = None,
    fail_fast: bool = True,
) -> PyramidResult:
    """Run the QA pyramid. Default: tier 1+2 (merge gate)."""
    if tiers is None:
        tiers = [1, 2]

    result = PyramidResult(verdict="PASS", branch=branch)
    t0 = time.monotonic()

    for tier_num in sorted(tiers):
        runner = TIER_RUNNERS.get(tier_num)
        if not runner:
            continue
        tier_result = runner()
        result.tiers.append(tier_result)
        if not tier_result.passed:
            result.verdict = "FAIL"
            if fail_fast and tier_num < max(tiers):
                # Skip higher tiers on failure
                break

    result.total_duration_ms = int((time.monotonic() - t0) * 1000)
    return result


def print_human(result: PyramidResult) -> None:
    """Pretty-print pyramid results."""
    print(f"\n{'=' * 60}")
    print(f"  CUT QA PYRAMID — {result.verdict}")
    if result.branch:
        print(f"  Branch: {result.branch}")
    print(f"  Duration: {result.total_duration_ms}ms")
    print(f"{'=' * 60}\n")

    for t in result.tiers:
        icon = "PASS" if t.passed else "FAIL"
        print(f"  Tier {t.tier} ({t.name}): {icon}  "
              f"[{t.tests_passed}/{t.tests_run} tests, {t.duration_ms}ms]")
        if t.error:
            print(f"    Error: {t.error}")
        for f in t.failures[:5]:
            print(f"    - {f}")
        if len(t.failures) > 5:
            print(f"    ... and {len(t.failures) - 5} more")

    print(f"\n  Verdict: {result.verdict}\n")


# ---------------------------------------------------------------------------
# REFLEX integration hook
# ---------------------------------------------------------------------------

def reflex_gate(branch: str | None = None) -> dict:
    """
    Entry point for REFLEX tool registration.

    Register as:
        tool_id: cut_qa_pyramid
        trigger: action=merge_request | action=verify
        input: { branch?: string, tiers?: [1,2,3] }
        output: { verdict, tiers, duration_ms }
    """
    result = run_pyramid(tiers=[1, 2], branch=branch)
    return asdict(result)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(description="CUT QA Pyramid — merge gate")
    parser.add_argument(
        "--tier", nargs="+", type=int, default=None,
        help="Tiers to run (default: 1 2)",
    )
    parser.add_argument(
        "--branch", type=str, default=None,
        help="Branch being gated (informational)",
    )
    parser.add_argument(
        "--json", action="store_true",
        help="Output JSON (for REFLEX/pipeline)",
    )
    parser.add_argument(
        "--no-fail-fast", action="store_true",
        help="Run all tiers even if earlier ones fail",
    )
    args = parser.parse_args()

    tiers = args.tier or [1, 2]
    result = run_pyramid(
        tiers=tiers,
        branch=args.branch,
        fail_fast=not args.no_fail_fast,
    )

    if args.json:
        print(json.dumps(asdict(result), indent=2))
    else:
        print_human(result)

    return 0 if result.verdict == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
