#!/usr/bin/env python3
"""
detect_xpass_drift.py — Stale xfail detector.

Scans all @pytest.mark.xfail tests, runs them, and flags any that now PASS
(XPASS = unexpectedly passing = stale marker). Stale xfails give false
confidence — pytest reports them as "expected failures" but masks passing code.

Usage:
  python scripts/detect_xpass_drift.py [tests_dir] [--create-tasks] [--filter PAT]
                                        [--api-url URL] [--json] [--runxfail]

  tests_dir     Directory to scan for xfail tests (default: tests/)
  --create-tasks  POST an EPSILON-FIX task for each stale xfail found
  --filter PAT  Only check tests whose node ID matches PAT (fnmatch)
  --api-url     Task board REST base URL (default: http://localhost:5001)
  --json        Machine-readable JSON output
  --runxfail    Pass --runxfail to pytest (strict mode: XPASS → FAIL)

Exit codes:
  0  No stale xfails found
  1  One or more stale xfails found
  2  Usage / pytest not found error
"""

import argparse
import fnmatch
import json
import re
import subprocess
import sys
import urllib.request
import urllib.error
from pathlib import Path


# ---------------------------------------------------------------------------
# Collect xfail test IDs from source
# ---------------------------------------------------------------------------

_XFAIL_RE = re.compile(
    r'@pytest\.mark\.xfail',
)
_TESTFUNC_RE = re.compile(
    r'^\s*(?:async\s+)?def\s+(test_\w+)',
)
_TESTCLASS_RE = re.compile(
    r'^class\s+(Test\w+)',
)


def collect_xfail_tests(tests_dir: Path, filter_pat: str | None) -> list[str]:
    """Return list of pytest node IDs for all @pytest.mark.xfail tests."""
    node_ids: list[str] = []

    for path in sorted(tests_dir.rglob("test_*.py")):
        lines = path.read_text(errors="replace").splitlines()
        current_class: str | None = None
        pending_xfail = False

        for line in lines:
            # Track class context
            cls_match = _TESTCLASS_RE.match(line)
            if cls_match:
                current_class = cls_match.group(1)
                pending_xfail = False
                continue

            # Detect xfail decorator
            if _XFAIL_RE.search(line):
                pending_xfail = True
                continue

            # Next def after xfail → record node ID
            if pending_xfail:
                fn_match = _TESTFUNC_RE.match(line)
                if fn_match:
                    fn_name = fn_match.group(1)
                    rel = path.relative_to(tests_dir.parent)
                    if current_class:
                        node_id = f"{rel}::{current_class}::{fn_name}"
                    else:
                        node_id = f"{rel}::{fn_name}"

                    if filter_pat is None or fnmatch.fnmatch(node_id, filter_pat):
                        node_ids.append(node_id)
                    pending_xfail = False
                elif line.strip() and not line.strip().startswith("@"):
                    # Non-decorator, non-def line after xfail: reset
                    pending_xfail = False

    return node_ids


# ---------------------------------------------------------------------------
# Run pytest and parse XPASS output
# ---------------------------------------------------------------------------

def run_xfail_tests(node_ids: list[str], runxfail: bool) -> list[str]:
    """Run pytest on given node IDs, return list of XPASS test IDs."""
    if not node_ids:
        return []

    cmd = [sys.executable, "-m", "pytest", "--no-header", "-q", "--tb=no"]
    if runxfail:
        cmd.append("--runxfail")
    cmd += node_ids

    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
    except FileNotFoundError:
        print("ERROR: pytest not found. Install with: pip install pytest",
              file=sys.stderr)
        sys.exit(2)

    xpass: list[str] = []
    # Patterns: "XPASS tests/foo.py::Bar::test_baz" or "XPASS tests/foo.py::test_baz"
    xpass_re = re.compile(r'^XPASS\s+(tests/\S+)', re.MULTILINE)
    for match in xpass_re.finditer(result.stdout):
        xpass.append(match.group(1))

    # Also catch the short form: "X tests/foo.py::test_baz - reason"
    short_re = re.compile(r'^X\s+(tests/\S+)', re.MULTILINE)
    for match in short_re.finditer(result.stdout):
        candidate = match.group(1).split(" ")[0].rstrip(":")
        if candidate not in xpass:
            xpass.append(candidate)

    return xpass


# ---------------------------------------------------------------------------
# Task creation
# ---------------------------------------------------------------------------

def create_task(test_id: str, api_url: str) -> str | None:
    title = f"EPSILON-FIX: Remove stale xfail from {test_id.split('::')[-1]}"
    description = (
        f"Test `{test_id}` is marked @pytest.mark.xfail but now passes (XPASS).\n\n"
        f"Action: Remove the @pytest.mark.xfail decorator and verify the test "
        f"passes cleanly with `pytest {test_id} -v`."
    )
    payload = json.dumps({
        "title": title,
        "description": description,
        "priority": 2,
        "phase_type": "fix",
        "source": "detect_xpass_drift",
        "tags": ["xfail", "stale-marker", "auto-detected"],
        "allowed_paths": ["tests/"],
        "role": "Epsilon",
        "domain": "qa",
    }).encode()
    url = f"{api_url.rstrip('/')}/api/debug/task-board/add"
    req = urllib.request.Request(
        url, data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            body = json.loads(resp.read())
            return body.get("task_id")
    except (urllib.error.URLError, json.JSONDecodeError) as e:
        print(f"  [warn] task creation failed: {e}", file=sys.stderr)
        return None


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("tests_dir", nargs="?", default="tests",
                        help="Directory to scan (default: tests/)")
    parser.add_argument("--create-tasks", action="store_true",
                        help="Auto-create EPSILON-FIX tasks for each stale xfail")
    parser.add_argument("--filter", dest="filter_pat", default=None,
                        help="fnmatch pattern to filter test node IDs")
    parser.add_argument("--api-url", default="http://localhost:5001",
                        help="Task board REST base URL")
    parser.add_argument("--json", dest="json_out", action="store_true",
                        help="Output machine-readable JSON")
    parser.add_argument("--runxfail", action="store_true",
                        help="Pass --runxfail to pytest (strict: XPASS → FAIL)")
    args = parser.parse_args()

    tests_dir = Path(args.tests_dir)
    if not tests_dir.is_dir():
        print(f"ERROR: tests_dir not found: {tests_dir}", file=sys.stderr)
        return 2

    # Step 1: collect xfail test IDs
    xfail_ids = collect_xfail_tests(tests_dir, args.filter_pat)

    if not args.json_out:
        print(f"\nScanning {tests_dir}/ for @pytest.mark.xfail tests...")
        print(f"  Found {len(xfail_ids)} xfail test(s)")
        if args.filter_pat:
            print(f"  Filter: {args.filter_pat}")

    if not xfail_ids:
        if args.json_out:
            print(json.dumps({"xfail_count": 0, "xpass": [], "stale_found": False}))
        else:
            print("PASS — no xfail tests found.")
        return 0

    # Step 2: run them
    if not args.json_out:
        print(f"  Running {len(xfail_ids)} test(s)...\n")
    xpass_ids = run_xfail_tests(xfail_ids, args.runxfail)

    # Step 3: report
    if args.json_out:
        print(json.dumps({
            "xfail_count": len(xfail_ids),
            "xpass": xpass_ids,
            "stale_found": bool(xpass_ids),
        }, indent=2))
        return 1 if xpass_ids else 0

    if not xpass_ids:
        print(f"PASS — {len(xfail_ids)} xfail test(s) checked, none unexpectedly pass.")
        return 0

    print("=" * 60)
    print("STALE XFAIL DETECTED")
    print("=" * 60)
    for tid in xpass_ids:
        print(f"\n[XPASS] {tid}")
        print(f"  → Test now passes but still has @pytest.mark.xfail marker")
        if args.create_tasks:
            task_id = create_task(tid, args.api_url)
            print(f"  → task created: {task_id}" if task_id else "  → task creation failed")

    print("\n" + "=" * 60)
    print(f"FAIL — {len(xpass_ids)} stale xfail marker(s) found.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
