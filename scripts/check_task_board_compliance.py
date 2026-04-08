#!/usr/bin/env python3
"""
Pre-commit hook: Check task board compliance before allowing commit.

MARKER_210.TASK_BOARD_GUARDRAIL: Pre-commit hook guard
Verifies that the agent has a claimed task before allowing the commit.

Usage: python scripts/check_task_board_compliance.py <ROLE>
Exit codes:
  0 = Compliance OK (claimed task found)
  1 = Compliance FAILED (no claimed task)
"""

import sys
import os
from pathlib import Path

# Add src to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.orchestration.task_board import check_claimed_task_for_hook


def main():
    if len(sys.argv) < 2:
        print("❌ Usage: check_task_board_compliance.py <ROLE>", file=sys.stderr)
        return 1

    role = sys.argv[1].strip()

    if not role:
        print("❌ Role cannot be empty", file=sys.stderr)
        return 1

    # Check for claimed task
    claimed_task = check_claimed_task_for_hook(role, time_window_hours=4)

    if claimed_task:
        # SUCCESS: Found a claimed task
        print(f"✅ Task Board Compliance: {role} has claimed task [{claimed_task['id']}]")
        return 0

    # FAILURE: No claimed task found
    print("\n❌ Task Board Compliance Check Failed", file=sys.stderr)
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━", file=sys.stderr)
    print(f"No claimed task found for role: {role}", file=sys.stderr)
    print(f"Branch: {os.environ.get('GIT_BRANCH', '(unknown)')}", file=sys.stderr)
    print("", file=sys.stderr)
    print("Your commits MUST be tied to a claimed task.", file=sys.stderr)
    print("", file=sys.stderr)
    print("Options:", file=sys.stderr)
    print("  1. Claim a task:", file=sys.stderr)
    print("     vetka_task_board action=claim task_id=tb_XXXXX", file=sys.stderr)
    print("", file=sys.stderr)
    print("  2. View pending tasks:", file=sys.stderr)
    print("     vetka_task_board action=list filter_status=pending priority=1,2 limit=5", file=sys.stderr)
    print("", file=sys.stderr)
    print("  3. Create a new task:", file=sys.stderr)
    print("     vetka_task_board action=add title=\"YOUR TASK\" phase_type=build", file=sys.stderr)
    print("", file=sys.stderr)
    print("Emergency bypass (⚠️  use sparingly):", file=sys.stderr)
    print("  git commit --no-verify", file=sys.stderr)
    print("", file=sys.stderr)
    print("Docs: https://docs/200_taskboard_forever/TASK_BOARD_COMPLIANCE.md", file=sys.stderr)
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━", file=sys.stderr)

    return 1


if __name__ == "__main__":
    sys.exit(main())
