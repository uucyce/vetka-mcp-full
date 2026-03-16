#!/usr/bin/env python3
"""
MARKER_189.4 — Merge Gate: pre-merge safety check for worktree branches.

Checks two things before allowing a merge:
1. FILE CONFLICTS: Are there files changed in both branches? (warns about potential conflicts)
2. TASK STATUS: Are all tasks for the merging branch done? (warns/blocks on pending tasks)

Modes (set via VETKA_MERGE_GATE env var):
  soft   — warn only, always exit 0 (default)
  medium — block if pending/in_progress tasks exist
  strict — block unless all tasks have merge_approved=true

Usage:
  python3 scripts/check_merge_gate.py <merge_branch> [<base_branch>]

Exit codes:
  0 — merge allowed
  1 — merge blocked (medium/strict mode only)

@status: active
@phase: 189
@depends: task_board
@used_by: .git/hooks/pre-merge-commit
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


def _git(*args: str) -> str:
    """Run a git command and return stdout."""
    result = subprocess.run(
        ["git", *args],
        capture_output=True, text=True, timeout=10,
    )
    return result.stdout.strip()


def _find_repo_root() -> Path:
    """Find the git repository root."""
    root = _git("rev-parse", "--show-toplevel")
    if root:
        return Path(root)
    # Fallback: walk up from script location
    return Path(__file__).resolve().parent.parent


def _get_mode() -> str:
    """Get merge gate mode from env."""
    mode = os.environ.get("VETKA_MERGE_GATE", "soft").lower()
    if mode not in ("soft", "medium", "strict"):
        return "soft"
    return mode


def _detect_file_overlap(merge_branch: str, base_branch: str) -> list[str]:
    """Find files changed in both branches since their common ancestor."""
    merge_base = _git("merge-base", base_branch, merge_branch)
    if not merge_base:
        return []

    # Files changed in the branch being merged
    incoming_files = set(
        _git("diff", "--name-only", merge_base, merge_branch).splitlines()
    )
    # Files changed in our branch since the common ancestor
    our_files = set(
        _git("diff", "--name-only", merge_base, base_branch).splitlines()
    )

    overlap = sorted(incoming_files & our_files)
    return overlap


def _check_task_board(merge_branch: str, repo_root: Path) -> dict:
    """Check task board for tasks associated with the merge branch.

    Returns dict with:
      - pending: list of pending/in_progress task titles
      - done: list of done_worktree tasks
      - unapproved: list of done but not merge_approved tasks
      - total: total tasks found for this branch
    """
    task_board_path = repo_root / "data" / "task_board.json"
    if not task_board_path.is_file():
        return {"pending": [], "done": [], "unapproved": [], "total": 0}

    try:
        with open(task_board_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        return {"pending": [], "done": [], "unapproved": [], "total": 0}

    tasks = data.get("tasks", {})
    if isinstance(tasks, list):
        tasks = {t.get("id", str(i)): t for i, t in enumerate(tasks)}

    # Also check commits on the branch for [task:tb_xxxx] references
    merge_base = _git("merge-base", "main", merge_branch)
    task_ids_from_commits: set[str] = set()
    if merge_base:
        log_output = _git("log", f"{merge_base}..{merge_branch}", "--format=%s %b")
        import re
        for match in re.finditer(r'\[task:(tb_[0-9_]+)\]', log_output):
            task_ids_from_commits.add(match.group(1))

    # Extract branch short name for matching
    branch_short = merge_branch.replace("claude/", "")

    pending = []
    done = []
    unapproved = []

    for task_id, task in tasks.items():
        # Match by: explicit branch field, or task_id in commits, or branch name in tags
        task_branch = task.get("branch", "")
        task_tags = task.get("tags", [])
        is_branch_task = (
            merge_branch in str(task_branch)
            or branch_short in str(task_branch)
            or task_id in task_ids_from_commits
            or merge_branch in task_tags
            or branch_short in task_tags
        )

        if not is_branch_task:
            continue

        status = task.get("status", "")
        title = task.get("title", task_id)

        if status in ("pending", "in_progress", "claimed"):
            pending.append(f"  [{task_id}] {title} (status: {status})")
        elif status in ("done_worktree", "done", "done_main"):
            done.append(title)
            if not task.get("merge_approved", False) and status == "done_worktree":
                unapproved.append(f"  [{task_id}] {title}")

    total = len(pending) + len(done) + len(unapproved)
    return {
        "pending": pending,
        "done": done,
        "unapproved": unapproved,
        "total": total,
    }


def main() -> int:
    if len(sys.argv) < 2:
        print("[merge-gate] Usage: check_merge_gate.py <merge_branch> [<base_branch>]", file=sys.stderr)
        return 0  # Don't block on usage error

    merge_branch = sys.argv[1]
    base_branch = sys.argv[2] if len(sys.argv) > 2 else "main"
    mode = _get_mode()
    repo_root = _find_repo_root()

    problems = []
    warnings = []

    # ── Check 1: File overlap ──
    overlap = _detect_file_overlap(merge_branch, base_branch)
    if overlap:
        msg = f"[merge-gate] {len(overlap)} file(s) changed in BOTH branches:"
        for f in overlap[:10]:
            msg += f"\n  - {f}"
        if len(overlap) > 10:
            msg += f"\n  ... and {len(overlap) - 10} more"
        msg += "\n  Review these files for merge conflicts!"
        warnings.append(msg)

    # ── Check 2: Task status ──
    task_info = _check_task_board(merge_branch, repo_root)

    if task_info["pending"]:
        msg = f"[merge-gate] {len(task_info['pending'])} UNFINISHED task(s) on branch {merge_branch}:"
        for t in task_info["pending"]:
            msg += f"\n{t}"
        if mode == "soft":
            warnings.append(msg)
        else:
            problems.append(msg)

    if task_info["unapproved"] and mode == "strict":
        msg = f"[merge-gate] {len(task_info['unapproved'])} task(s) not yet approved for merge:"
        for t in task_info["unapproved"]:
            msg += f"\n{t}"
        problems.append(msg)

    # ── Output ──
    if not warnings and not problems:
        if task_info["total"] > 0:
            print(f"[merge-gate] OK — {len(task_info['done'])} completed task(s) on {merge_branch}")
        else:
            print(f"[merge-gate] OK — no task board entries found for {merge_branch}")
        return 0

    for w in warnings:
        print(w, file=sys.stderr)

    if problems:
        for p in problems:
            print(p, file=sys.stderr)
        print(f"\n[merge-gate] BLOCKED (mode={mode}). Fix tasks or set VETKA_MERGE_GATE=soft to override.", file=sys.stderr)
        return 1

    # Soft mode: warnings only, allow merge
    print(f"[merge-gate] Warnings above (mode={mode}), merge allowed.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
