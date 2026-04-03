"""
MARKER_203.ROLE_MEMORY: Role Memory Writer — write side for per-role MEMORY.md.

Auto-populates memory/roles/{callsign}/MEMORY.md from task debrief answers (Q1/Q2/Q3).
Called by smart_debrief.process_smart_debrief() after each task completion.

Pattern: same as Sherpa feedback_log.jsonl — auto-collect → structured store → inject.
Read side: session_tools.py injects load_recent() result as role_memory field.

@file src/memory/role_memory_writer.py
@phase 203
@depends pathlib, logging, datetime
@used_by src/services/smart_debrief.py, src/mcp/tools/session_tools.py
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# MARKER_198.DEBRIEF worktree-safe root resolution (same pattern as experience_report.py)
def _resolve_project_root() -> Path:
    """Return main repo root, bypassing git worktree indirection."""
    candidate = Path(__file__).resolve().parent.parent.parent
    parts = candidate.parts
    try:
        wt_idx = parts.index(".claude")
        main_root = Path(*parts[:wt_idx])
        if main_root.exists():
            return main_root
    except ValueError:
        pass
    return candidate


_PROJECT_ROOT = _resolve_project_root()

# MARKER_203.ROLE_MEMORY_PATH: Store in ~/.claude/projects/.../memory/roles/
# Same location as feedback_*.md — outside repo, no merge conflicts across worktrees.
# All worktrees share one write target. Encoding: replace / and _ with - in project path.
def _get_roles_memory_dir() -> Path:
    """Return ~/.claude/projects/<key>/memory/roles/ for this project."""
    key = "-" + str(_PROJECT_ROOT).lstrip("/").replace("/", "-").replace("_", "-")
    claude_path = Path.home() / ".claude" / "projects" / key / "memory" / "roles"
    if claude_path.parent.parent.exists():  # ~/.claude/projects/<key>/ must exist
        return claude_path
    # Fallback: repo-relative (worktrees still share main repo memory/)
    return _PROJECT_ROOT / "memory" / "roles"


_ROLES_MEMORY_DIR = _get_roles_memory_dir()

MAX_ENTRIES_PER_ROLE = 50  # rotate: drop oldest beyond this limit

_HEADER_MARKER = "[auto-entries below — do not edit manually]"


def _rotate_if_needed(memory_path: Path, callsign: str) -> None:
    """Drop oldest auto-entries if count exceeds MAX_ENTRIES_PER_ROLE.

    Preserves manual preamble (everything before the header marker).
    Non-blocking: silently returns on any error.
    """
    try:
        text = memory_path.read_text(encoding="utf-8")
        # Find split point: manual preamble vs auto-entries
        marker_line = f"<!-- {_HEADER_MARKER} -->"
        if marker_line in text:
            preamble, _, auto_part = text.partition(marker_line)
        else:
            preamble, auto_part = "", text

        raw_entries = auto_part.split("\n## [")
        auto_entries = raw_entries[1:]  # first element is empty or pre-header text

        if len(auto_entries) <= MAX_ENTRIES_PER_ROLE:
            return  # nothing to rotate

        kept = auto_entries[-MAX_ENTRIES_PER_ROLE:]
        new_auto = "\n## [".join([""] + kept)
        new_text = preamble + marker_line + new_auto
        memory_path.write_text(new_text, encoding="utf-8")
        dropped = len(auto_entries) - MAX_ENTRIES_PER_ROLE
        logger.info("[RoleMemory] Rotated %s: dropped %d oldest entries", callsign, dropped)
    except Exception as exc:
        logger.debug("[RoleMemory] Rotation skipped for %s: %s", callsign, exc)


def append_entry(
    callsign: str,
    task_id: str,
    task_title: str,
    q1: Optional[str] = None,
    q2: Optional[str] = None,
    q3: Optional[str] = None,
    domain: str = "",
    hot_files: Optional[list] = None,
) -> bool:
    """Append one task completion entry to memory/roles/{callsign}/MEMORY.md.

    Non-blocking: never raises, always returns bool success.
    Called from smart_debrief.process_smart_debrief() — must not delay completion.
    """
    try:
        role_dir = _ROLES_MEMORY_DIR / callsign
        role_dir.mkdir(parents=True, exist_ok=True)
        memory_path = role_dir / "MEMORY.md"

        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        files_block = (
            "\n".join(f"  - {f}" for f in (hot_files or [])[:5])
            or "  (none recorded)"
        )

        entry = (
            f"\n## [{task_id}] {task_title}\n"
            f"**Date:** {date_str} | **Domain:** {domain or 'general'}\n"
            f"\n### What I Learned (Q1)\n"
            f"{q1.strip() if q1 else '(not recorded)'}\n"
            f"\n### What Worked (Q2)\n"
            f"{q2.strip() if q2 else '(not recorded)'}\n"
            f"\n### What I'd Do Next (Q3)\n"
            f"{q3.strip() if q3 else '(not recorded)'}\n"
            f"\n### Hot Files\n"
            f"{files_block}\n"
            f"\n---\n"
        )

        is_new = not memory_path.exists() or memory_path.stat().st_size == 0
        with open(memory_path, "a", encoding="utf-8") as f:
            if is_new:
                f.write(
                    f"# Role Memory — {callsign}\n"
                    f"# Auto-generated by role_memory_writer.py\n"
                    f"# Entries append at task_complete. Add narrative preamble above the marker.\n\n"
                    f"---\n"
                    f"<!-- {_HEADER_MARKER} -->\n"
                )
            f.write(entry)

        _rotate_if_needed(memory_path, callsign)
        logger.info("[RoleMemory] Appended entry for %s task=%s", callsign, task_id)
        return True

    except Exception as exc:
        logger.debug("[RoleMemory] Non-fatal write error for %s: %s", callsign, exc)
        return False


def load_recent(callsign: str, last_n: int = 3) -> list[dict]:
    """Load last N task entries from memory/roles/{callsign}/MEMORY.md.

    Returns list of dicts: [{task_id, title, raw}]
    Returns [] on any error or missing file.
    """
    try:
        memory_path = _ROLES_MEMORY_DIR / callsign / "MEMORY.md"
        if not memory_path.exists():
            return []

        text = memory_path.read_text(encoding="utf-8")

        # Split on "## [" which marks each auto-entry header
        raw_entries = text.split("\n## [")
        entries = []
        for raw in raw_entries[1:]:  # skip file header
            lines = raw.strip().split("\n")
            header = lines[0] if lines else ""
            bracket_end = header.find("]")
            if bracket_end < 0:
                continue
            task_id = header[:bracket_end].strip()
            title = header[bracket_end + 1:].strip()
            entries.append({
                "task_id": task_id,
                "title": title,
                "raw": ("## [" + raw)[:800],  # cap at 800 chars for token budget
            })

        return entries[-last_n:]  # most recent N

    except Exception as exc:
        logger.debug("[RoleMemory] Non-fatal read error for %s: %s", callsign, exc)
        return []
