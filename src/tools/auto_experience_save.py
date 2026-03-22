"""
MARKER_ZETA.E1: Auto-Experience Save — session end hook.

Runs automatically on Claude Code Stop event (configured via hooks in settings.json).
Collects passive signals from session tracker + CORTEX feedback and saves
an ExperienceReport without any agent interaction.

Usage:
    # As Claude Code hook (automatic)
    # settings.json: {"hooks": {"Stop": [{"type": "command", "command": ".venv/bin/python -m src.tools.auto_experience_save"}]}}

    # Manual (for testing)
    .venv/bin/python -m src.tools.auto_experience_save
    .venv/bin/python -m src.tools.auto_experience_save --dry-run
"""

from __future__ import annotations

import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_FEEDBACK_LOG = _PROJECT_ROOT / "data" / "reflex" / "feedback_log.jsonl"


def _detect_branch() -> str:
    """Detect current git branch."""
    try:
        result = subprocess.run(
            ["git", "branch", "--show-current"],
            capture_output=True, text=True, timeout=5,
            cwd=str(_PROJECT_ROOT),
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except Exception:
        pass
    return "main"


def _get_role(branch: str):
    """Get AgentRole from registry, returns None if not found."""
    try:
        from src.services.agent_registry import get_agent_registry
        registry = get_agent_registry()
        return registry.get_by_branch(branch)
    except Exception:
        return None


def _get_session_state() -> dict:
    """Read session tracker state. Returns dict with metrics."""
    try:
        from src.services.session_tracker import get_session_tracker
        tracker = get_session_tracker()

        # Find the most active session (most actions)
        best_session = None
        best_score = -1
        for sid, session in tracker._sessions.items():
            score = session.tasks_completed + session.edit_count + session.search_count
            if score > best_score:
                best_score = score
                best_session = session

        if best_session is None:
            return {"empty": True}

        return {
            "empty": False,
            "session_id": best_session.session_id,
            "tasks_completed": best_session.tasks_completed,
            "claimed_task_id": best_session.claimed_task_id,
            "files_read": list(best_session.files_read),
            "files_edited": list(best_session.files_edited),
            "read_count": best_session.read_count,
            "edit_count": best_session.edit_count,
            "search_count": best_session.search_count,
            "task_board_calls": best_session.task_board_calls,
            "experience_report_submitted": best_session.experience_report_submitted,
            "created_at": best_session.created_at,
        }
    except Exception:
        return {"empty": True}


def _get_cortex_summary(since_timestamp: Optional[float] = None) -> dict:
    """Read CORTEX feedback_log.jsonl and compute summary."""
    if not _FEEDBACK_LOG.exists():
        return {"total_calls": 0}

    entries = []
    try:
        with open(_FEEDBACK_LOG, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                    # Filter by timestamp if provided
                    if since_timestamp:
                        ts = entry.get("timestamp", 0)
                        if isinstance(ts, str):
                            continue  # skip non-numeric timestamps
                        if ts < since_timestamp:
                            continue
                    entries.append(entry)
                except json.JSONDecodeError:
                    continue
    except Exception:
        return {"total_calls": 0}

    if not entries:
        return {"total_calls": 0}

    # Aggregate by tool_id
    tool_stats: dict[str, dict] = {}
    for e in entries:
        tid = e.get("tool_id", "unknown")
        if tid not in tool_stats:
            tool_stats[tid] = {"calls": 0, "successes": 0}
        tool_stats[tid]["calls"] += 1
        if e.get("success"):
            tool_stats[tid]["successes"] += 1

    total = len(entries)
    total_success = sum(1 for e in entries if e.get("success"))

    # Top tools (by call count, descending)
    sorted_tools = sorted(tool_stats.items(), key=lambda x: x[1]["calls"], reverse=True)
    top_tools = [
        {
            "tool": tid,
            "calls": stats["calls"],
            "success_rate": round(stats["successes"] / stats["calls"], 2) if stats["calls"] > 0 else 0,
        }
        for tid, stats in sorted_tools[:5]
    ]

    # Failed tools (success_rate < 0.5 and at least 2 calls)
    failed_tools = [
        {
            "tool": tid,
            "calls": stats["calls"],
            "success_rate": round(stats["successes"] / stats["calls"], 2) if stats["calls"] > 0 else 0,
        }
        for tid, stats in sorted_tools
        if stats["calls"] >= 2 and (stats["successes"] / stats["calls"]) < 0.5
    ]

    return {
        "total_calls": total,
        "success_rate": round(total_success / total, 3) if total > 0 else 0,
        "top_tools": top_tools,
        "failed_tools": failed_tools,
    }


def _has_meaningful_work(session_state: dict) -> bool:
    """Check if session had meaningful work worth saving."""
    if session_state.get("empty"):
        return False
    tasks = session_state.get("tasks_completed", 0)
    edits = session_state.get("edit_count", 0)
    searches = session_state.get("search_count", 0)
    return (tasks > 0) or (edits > 0) or (searches > 0)


def auto_save(dry_run: bool = False) -> Optional[Path]:
    """
    Main entry point. Collects session data and saves ExperienceReport.

    Returns path to saved report, or None if skipped.
    """
    from src.services.experience_report import ExperienceReport, get_experience_store

    # 1. Detect role
    branch = _detect_branch()
    role = _get_role(branch)
    callsign = role.callsign if role else ""
    domain = role.domain if role else ""

    # 2. Read session state
    session_state = _get_session_state()

    # 3. Check if meaningful work happened
    if not _has_meaningful_work(session_state):
        print("[auto-experience] No meaningful work detected — skipping.", file=sys.stderr)
        return None

    # 4. Read CORTEX feedback
    since = session_state.get("created_at")
    cortex = _get_cortex_summary(since_timestamp=since)

    # 5. Build report
    now = datetime.now(timezone.utc)
    session_id = f"auto-{now.strftime('%Y%m%d-%H%M%S')}-{role.worktree if role else 'main'}"

    duration = int(time.time() - session_state.get("created_at", time.time()))

    report = ExperienceReport(
        session_id=session_id,
        agent_callsign=callsign,
        domain=domain,
        branch=branch,
        timestamp=now.isoformat(),
        tasks_completed=[session_state.get("claimed_task_id", "")] if session_state.get("claimed_task_id") else [],
        files_touched=list(session_state.get("files_edited", [])),
        lessons_learned=[],      # auto-mode: passive only
        recommendations=[],      # filled by D5 debrief if triggered
        bugs_found=[],
        commits=0,               # could be enriched from git log
        tests_added=0,
        tests_passing=0,
        reflex_summary=cortex,
    )

    # 6. Save
    if dry_run:
        import dataclasses
        print(json.dumps(dataclasses.asdict(report), indent=2, default=str))
        return None

    store = get_experience_store()
    path = store.submit(report)

    # 7. Print summary
    print(
        f"[auto-experience] Saved: {callsign or 'unknown'} ({domain or 'cross-cutting'}) "
        f"| tasks={session_state.get('tasks_completed', 0)} "
        f"| edits={session_state.get('edit_count', 0)} "
        f"| duration={duration}s "
        f"→ {path.name}",
        file=sys.stderr,
    )

    return path


def main():
    """Entry point — always exits 0."""
    try:
        dry_run = "--dry-run" in sys.argv
        auto_save(dry_run=dry_run)
    except Exception as e:
        print(f"[auto-experience] Error (non-fatal): {e}", file=sys.stderr)
    sys.exit(0)


if __name__ == "__main__":
    main()
