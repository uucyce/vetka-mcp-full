#!/usr/bin/env python3
"""
QA Fleet Orchestrator — auto-audit done_worktree tasks.

Fetches done_worktree tasks from TaskBoard, gathers git diffs and context,
runs automated static checks, and generates structured audit prompts
for parallel Sonnet agent verification.

Usage:
    python scripts/qa_fleet.py                          # audit all done_worktree
    python scripts/qa_fleet.py --project CUT            # filter by project
    python scripts/qa_fleet.py --task-id tb_123_1       # audit single task
    python scripts/qa_fleet.py --auto-verify            # auto-PASS trivial tasks
    python scripts/qa_fleet.py --json                   # machine-readable output

Designed for Delta QA agent — run this, then feed prompts to Sonnet agents.

Exit codes:
    0 = all audits generated / all auto-verified PASS
    1 = at least one FAIL or needs manual review
    2 = infrastructure error
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
from typing import Any, Optional


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent
API_BASE = os.environ.get("VETKA_API_BASE", "http://127.0.0.1:5001")
CLIENT_DIR = PROJECT_ROOT / "client"

# Monochrome check (reused from cut_qa_pyramid.py)
_GREY_HEX = re.compile(
    r"#([0-9a-fA-F])\1\1"
    r"|#([0-9a-fA-F]{2})\2\2"
)
_ANY_HEX = re.compile(r"#[0-9a-fA-F]{3,8}")

MONOCHROME_EXEMPT_FILES = {
    "ColorWheel.tsx", "ColorCorrectionPanel.tsx", "ColorCurves.tsx",
    "VideoScopes.tsx", "WaveformCanvas.tsx", "StereoWaveformCanvas.tsx",
    "BPMTrack.tsx", "CamelotWheel.tsx", "PulseInspector.tsx",
    "DAGProjectPanel.tsx",  # has known violation, separate task
}

MONOCHROME_EXEMPT_LINES = {"MARKER_COLORS", "color correction", "markers exempt"}


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class AuditCheck:
    name: str
    passed: bool
    details: str = ""


@dataclass
class TaskAudit:
    task_id: str
    title: str
    branch: str
    commit_hash: str
    checks: list[AuditCheck] = field(default_factory=list)
    verdict: str = "PENDING"  # PASS, FAIL, NEEDS_REVIEW
    diff_summary: str = ""
    allowed_paths: list[str] = field(default_factory=list)
    changed_files: list[str] = field(default_factory=list)
    sonnet_prompt: str = ""

    @property
    def auto_passable(self) -> bool:
        """Can be auto-verified without Sonnet review."""
        return all(c.passed for c in self.checks) and len(self.checks) >= 3


# ---------------------------------------------------------------------------
# TaskBoard client (REST API)
# ---------------------------------------------------------------------------

def _fetch_json(url: str) -> dict:
    """Fetch JSON from REST API using curl (no requests dependency)."""
    try:
        result = subprocess.run(
            ["curl", "-s", "-f", url],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode != 0:
            return {"success": False, "error": f"curl failed: {result.stderr.strip()}"}
        return json.loads(result.stdout)
    except Exception as e:
        return {"success": False, "error": str(e)}


def fetch_done_worktree_tasks(project_id: str = "") -> list[dict]:
    """Fetch all done_worktree tasks from TaskBoard."""
    url = f"{API_BASE}/api/debug/task-board"
    if project_id:
        url += f"?project_id={project_id}"
    data = _fetch_json(url)
    if not data.get("success"):
        print(f"[ERROR] Cannot fetch tasks: {data.get('error', 'unknown')}", file=sys.stderr)
        return []
    tasks = data.get("tasks", [])
    # Filter for done_worktree, skip synthetic test tasks and empty commits
    SYNTHETIC_COMMITS = {"test_only", "stress_test_only", "lifecycle_test", ""}
    result = []
    for t in tasks:
        if t.get("status") != "done_worktree":
            continue
        commit = t.get("commit_hash", "") or ""
        if commit in SYNTHETIC_COMMITS:
            continue
        # Skip tasks with tags indicating test/synthetic origin
        tags = t.get("tags") or []
        if "stress-test" in tags or "lifecycle-test" in tags:
            continue
        result.append(t)
    return result


def fetch_task_detail(task_id: str) -> dict | None:
    """Fetch single task details."""
    url = f"{API_BASE}/api/debug/task-board"
    data = _fetch_json(url)
    if not data.get("success"):
        return None
    for t in data.get("tasks", []):
        if t.get("id") == task_id:
            return t
    return None


# ---------------------------------------------------------------------------
# Git helpers
# ---------------------------------------------------------------------------

def git_diff_for_commit(commit_hash: str) -> str:
    """Get the diff for a specific commit."""
    if not commit_hash:
        return ""
    try:
        result = subprocess.run(
            ["git", "diff", f"{commit_hash}^..{commit_hash}", "--stat"],
            capture_output=True, text=True, timeout=10,
            cwd=str(PROJECT_ROOT),
        )
        return result.stdout.strip() if result.returncode == 0 else ""
    except Exception:
        return ""


def git_diff_files_for_commit(commit_hash: str) -> list[str]:
    """Get list of changed files for a commit."""
    if not commit_hash:
        return []
    try:
        result = subprocess.run(
            ["git", "diff", f"{commit_hash}^..{commit_hash}", "--name-only"],
            capture_output=True, text=True, timeout=10,
            cwd=str(PROJECT_ROOT),
        )
        if result.returncode == 0:
            return [f for f in result.stdout.strip().split("\n") if f]
        return []
    except Exception:
        return []


def git_show_commit_message(commit_hash: str) -> str:
    """Get commit message."""
    if not commit_hash:
        return ""
    try:
        result = subprocess.run(
            ["git", "log", "--format=%B", "-1", commit_hash],
            capture_output=True, text=True, timeout=10,
            cwd=str(PROJECT_ROOT),
        )
        return result.stdout.strip() if result.returncode == 0 else ""
    except Exception:
        return ""


def git_diff_patch_for_commit(commit_hash: str, max_lines: int = 200) -> str:
    """Get actual patch content (truncated)."""
    if not commit_hash:
        return ""
    try:
        result = subprocess.run(
            ["git", "diff", f"{commit_hash}^..{commit_hash}"],
            capture_output=True, text=True, timeout=10,
            cwd=str(PROJECT_ROOT),
        )
        if result.returncode == 0:
            lines = result.stdout.split("\n")
            if len(lines) > max_lines:
                return "\n".join(lines[:max_lines]) + f"\n... ({len(lines) - max_lines} more lines)"
            return result.stdout.strip()
        return ""
    except Exception:
        return ""


# ---------------------------------------------------------------------------
# Audit checks
# ---------------------------------------------------------------------------

def check_scope(changed_files: list[str], allowed_paths: list[str]) -> AuditCheck:
    """Verify all changed files are within allowed_paths."""
    if not allowed_paths:
        return AuditCheck("scope", True, "No path restrictions defined")

    violations = []
    for f in changed_files:
        in_scope = False
        for allowed in allowed_paths:
            # Handle both directory patterns (ending with /) and file patterns
            if allowed.endswith("/"):
                if f.startswith(allowed) or f.startswith(allowed.rstrip("/")):
                    in_scope = True
                    break
            else:
                # Exact file match or glob-style prefix
                if f == allowed or f.startswith(allowed.rstrip("*")):
                    in_scope = True
                    break
        if not in_scope:
            violations.append(f)

    if violations:
        return AuditCheck("scope", False, f"Out-of-scope files: {', '.join(violations)}")
    return AuditCheck("scope", True, f"All {len(changed_files)} files within scope")


def check_monochrome_in_diff(patch: str) -> AuditCheck:
    """Check for non-grey hex colors in added lines."""
    violations = []
    for line in patch.split("\n"):
        if not line.startswith("+"):
            continue
        if any(ex in line for ex in MONOCHROME_EXEMPT_LINES):
            continue
        for match in _ANY_HEX.finditer(line):
            hex_val = match.group().lower()
            if not _is_grey(hex_val):
                violations.append(f"{hex_val} in: {line.strip()[:80]}")

    if violations:
        return AuditCheck("monochrome", False, f"{len(violations)} color violations: {'; '.join(violations[:5])}")
    return AuditCheck("monochrome", True, "No color violations in diff")


def _is_grey(hex_color: str) -> bool:
    """Check if a hex color is grey (R=G=B)."""
    h = hex_color.lstrip("#")
    if len(h) == 3:
        return h[0] == h[1] == h[2]
    if len(h) == 6:
        return h[0:2] == h[2:4] == h[4:6]
    if len(h) == 8:  # with alpha
        return h[0:2] == h[2:4] == h[4:6]
    return True  # unknown format, don't flag


def check_commit_exists(commit_hash: str) -> AuditCheck:
    """Verify the commit hash actually exists in git."""
    if not commit_hash:
        return AuditCheck("commit_exists", False, "No commit hash recorded")
    try:
        result = subprocess.run(
            ["git", "cat-file", "-t", commit_hash],
            capture_output=True, text=True, timeout=5,
            cwd=str(PROJECT_ROOT),
        )
        if result.returncode == 0 and "commit" in result.stdout:
            return AuditCheck("commit_exists", True, f"Commit {commit_hash[:8]} exists")
        return AuditCheck("commit_exists", False, f"Commit {commit_hash} not found in repo")
    except Exception as e:
        return AuditCheck("commit_exists", False, f"Git error: {e}")


def check_task_has_deliverable(changed_files: list[str], commit_msg: str) -> AuditCheck:
    """Verify the task actually produced something (not empty completion)."""
    if not changed_files and not commit_msg:
        return AuditCheck("deliverable", False, "No files changed and no commit message — empty task")
    if not changed_files:
        return AuditCheck("deliverable", False, f"Commit message exists but no files changed")
    return AuditCheck("deliverable", True, f"{len(changed_files)} files changed")


def check_title_matches_commit(title: str, commit_msg: str) -> AuditCheck:
    """Basic sanity: does the commit message relate to the task title."""
    if not commit_msg:
        return AuditCheck("title_match", False, "No commit message to check")

    # Extract key words from title (skip common prefixes)
    title_words = set(
        w.lower() for w in re.findall(r'\w+', title)
        if len(w) > 3 and w.upper() not in {"DELTA", "ALPHA", "BETA", "GAMMA", "EPSILON", "ZETA", "BUILD", "TEST", "MISSION"}
    )
    commit_words = set(w.lower() for w in re.findall(r'\w+', commit_msg))
    overlap = title_words & commit_words

    if len(overlap) >= 2 or (title_words and len(overlap) / max(len(title_words), 1) > 0.3):
        return AuditCheck("title_match", True, f"Title/commit overlap: {', '.join(sorted(overlap)[:5])}")
    return AuditCheck("title_match", False, f"Low overlap between title and commit. Title words: {', '.join(sorted(title_words)[:5])}")


# ---------------------------------------------------------------------------
# Sonnet prompt generation
# ---------------------------------------------------------------------------

def generate_sonnet_prompt(task: dict, audit: TaskAudit, patch: str) -> str:
    """Generate a structured audit prompt for a Sonnet agent."""
    return f"""You are a QA auditor for VETKA CUT NLE project. Audit this completed task.

## Task
- **ID:** {audit.task_id}
- **Title:** {audit.title}
- **Description:** {task.get('description', 'N/A')[:500]}
- **Allowed paths:** {', '.join(audit.allowed_paths) or 'unrestricted'}
- **Completion contract:** {json.dumps(task.get('completion_contract', []))}

## Commit
- **Hash:** {audit.commit_hash}
- **Message:** {git_show_commit_message(audit.commit_hash)}

## Changed files
{chr(10).join(f'- {f}' for f in audit.changed_files) or 'None'}

## Diff (stat)
{audit.diff_summary}

## Patch (truncated)
```
{patch[:3000]}
```

## Automated check results
{chr(10).join(f'- {c.name}: {"PASS" if c.passed else "FAIL"} — {c.details}' for c in audit.checks)}

## Your task
1. Does the diff actually implement what the task title/description claims?
2. Are there any obvious bugs, security issues, or anti-patterns in the patch?
3. Does the code follow project conventions (monochrome UI, data-testid, no hardcoded URLs)?
4. Is the scope appropriate (no unexpected file changes)?

## Output format
Reply with EXACTLY this JSON (no extra text):
```json
{{
  "verdict": "PASS" or "FAIL",
  "confidence": 0.0-1.0,
  "findings": ["finding 1", "finding 2"],
  "summary": "one-line summary"
}}
```"""


# ---------------------------------------------------------------------------
# Main audit pipeline
# ---------------------------------------------------------------------------

def audit_task(task: dict) -> TaskAudit:
    """Run full audit pipeline on a single task."""
    task_id = task.get("id", "unknown")
    title = task.get("title", "untitled")
    commit_hash = task.get("commit_hash", "")
    branch = task.get("branch_name", "")
    allowed_paths = task.get("allowed_paths", [])

    audit = TaskAudit(
        task_id=task_id,
        title=title,
        branch=branch,
        commit_hash=commit_hash,
        allowed_paths=allowed_paths,
    )

    # Gather git data
    audit.diff_summary = git_diff_for_commit(commit_hash)
    audit.changed_files = git_diff_files_for_commit(commit_hash)
    commit_msg = git_show_commit_message(commit_hash)
    patch = git_diff_patch_for_commit(commit_hash)

    # Run automated checks
    audit.checks.append(check_commit_exists(commit_hash))
    audit.checks.append(check_task_has_deliverable(audit.changed_files, commit_msg))
    audit.checks.append(check_scope(audit.changed_files, allowed_paths))
    audit.checks.append(check_title_matches_commit(title, commit_msg))

    # Monochrome check only for frontend files
    has_frontend = any(f.endswith((".tsx", ".css", ".ts")) and "client/" in f for f in audit.changed_files)
    if has_frontend:
        audit.checks.append(check_monochrome_in_diff(patch))

    # Generate Sonnet prompt
    audit.sonnet_prompt = generate_sonnet_prompt(task, audit, patch)

    # Determine verdict
    if not audit.checks:
        audit.verdict = "NEEDS_REVIEW"
    elif all(c.passed for c in audit.checks):
        audit.verdict = "AUTO_PASS" if audit.auto_passable else "NEEDS_REVIEW"
    else:
        failed = [c for c in audit.checks if not c.passed]
        critical_fails = [c for c in failed if c.name in ("commit_exists", "deliverable")]
        if critical_fails:
            audit.verdict = "AUTO_FAIL"
        else:
            audit.verdict = "NEEDS_REVIEW"

    return audit


def print_audit_report(audits: list[TaskAudit], as_json: bool = False) -> None:
    """Print human-readable or JSON audit report."""
    if as_json:
        print(json.dumps([{
            "task_id": a.task_id,
            "title": a.title,
            "verdict": a.verdict,
            "checks": [asdict(c) for c in a.checks],
            "changed_files": a.changed_files,
            "diff_summary": a.diff_summary,
        } for a in audits], indent=2))
        return

    print(f"\n{'='*70}")
    print(f"QA FLEET AUDIT REPORT — {len(audits)} tasks")
    print(f"{'='*70}\n")

    auto_pass = [a for a in audits if a.verdict == "AUTO_PASS"]
    auto_fail = [a for a in audits if a.verdict == "AUTO_FAIL"]
    needs_review = [a for a in audits if a.verdict == "NEEDS_REVIEW"]

    if auto_pass:
        print(f"AUTO-PASS ({len(auto_pass)}):")
        for a in auto_pass:
            print(f"  [PASS] {a.task_id}: {a.title[:60]}")
        print()

    if auto_fail:
        print(f"AUTO-FAIL ({len(auto_fail)}):")
        for a in auto_fail:
            failed = [c for c in a.checks if not c.passed]
            print(f"  [FAIL] {a.task_id}: {a.title[:60]}")
            for c in failed:
                print(f"         - {c.name}: {c.details}")
        print()

    if needs_review:
        print(f"NEEDS SONNET REVIEW ({len(needs_review)}):")
        for a in needs_review:
            check_str = " ".join(f"{'✓' if c.passed else '✗'}{c.name}" for c in a.checks)
            print(f"  [REVIEW] {a.task_id}: {a.title[:50]}  [{check_str}]")
        print()

    print(f"Summary: {len(auto_pass)} auto-pass, {len(auto_fail)} auto-fail, {len(needs_review)} need review")

    if needs_review:
        print(f"\n{'='*70}")
        print("SONNET PROMPTS (copy-paste to Agent tool with model=sonnet):")
        print(f"{'='*70}")
        for a in needs_review:
            print(f"\n--- PROMPT FOR {a.task_id} ---")
            print(a.sonnet_prompt)
            print(f"--- END PROMPT ---\n")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="QA Fleet Orchestrator")
    parser.add_argument("--project", default="", help="Filter by project ID (e.g., CUT)")
    parser.add_argument("--task-id", default="", help="Audit single task by ID")
    parser.add_argument("--auto-verify", action="store_true", help="Auto-verify AUTO_PASS tasks via REST API")
    parser.add_argument("--json", action="store_true", help="Machine-readable JSON output")
    parser.add_argument("--prompts-only", action="store_true", help="Only output Sonnet prompts for NEEDS_REVIEW")
    args = parser.parse_args()

    t0 = time.monotonic()

    # Fetch tasks
    if args.task_id:
        task = fetch_task_detail(args.task_id)
        if not task:
            print(f"[ERROR] Task {args.task_id} not found", file=sys.stderr)
            sys.exit(2)
        if task.get("status") != "done_worktree":
            print(f"[WARN] Task {args.task_id} status is '{task.get('status')}', not done_worktree", file=sys.stderr)
        tasks = [task]
    else:
        tasks = fetch_done_worktree_tasks(args.project)
        if not tasks:
            print("No done_worktree tasks found.")
            sys.exit(0)

    print(f"Auditing {len(tasks)} done_worktree tasks...", file=sys.stderr)

    # Run audits
    audits = []
    for task in tasks:
        audit = audit_task(task)
        audits.append(audit)

    # Output
    if args.prompts_only:
        needs_review = [a for a in audits if a.verdict == "NEEDS_REVIEW"]
        for a in needs_review:
            print(a.sonnet_prompt)
            print("\n---\n")
    elif args.json:
        print_audit_report(audits, as_json=True)
    else:
        print_audit_report(audits)

    elapsed = time.monotonic() - t0
    print(f"\nCompleted in {elapsed:.1f}s", file=sys.stderr)

    # Exit code
    auto_fail = [a for a in audits if a.verdict == "AUTO_FAIL"]
    if auto_fail:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
