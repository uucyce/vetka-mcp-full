"""
MARKER_ZETA.D2: Experience Report Store.

Stores and retrieves structured experience reports from agent sessions.
Reports are JSON files in data/experience_reports/<session_id>.json.

Used by:
- vetka_submit_experience_report MCP tool (writes)
- CLAUDE.md Generator D3 (reads latest per-role)
- session_init (checks pending reports from previous sessions)
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_REPORTS_DIR = _PROJECT_ROOT / "data" / "experience_reports"


@dataclass
class ExperienceReport:
    """Structured experience report from an agent session."""

    session_id: str
    agent_callsign: str        # "Alpha", "Beta", "Gamma", "Delta", "Commander"
    domain: str                # "engine", "media", "ux", "qa", "architect"
    branch: str                # "claude/cut-engine"
    timestamp: str             # ISO 8601

    # Work summary
    tasks_completed: list[str] = field(default_factory=list)   # task IDs
    files_touched: list[str] = field(default_factory=list)

    # Learnings
    lessons_learned: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)   # for successor
    bugs_found: list[dict] = field(default_factory=list)       # [{file, description}]

    # Metrics
    commits: int = 0
    tests_added: int = 0
    tests_passing: int = 0

    # REFLEX snapshot (optional, auto-populated)
    reflex_summary: Optional[dict] = None


class ExperienceReportStore:
    """Read/write experience reports as JSON files."""

    def __init__(self, reports_dir: Optional[Path] = None):
        self._dir = reports_dir or _REPORTS_DIR
        self._dir.mkdir(parents=True, exist_ok=True)

    def submit(self, report: ExperienceReport) -> Path:
        """Save report to disk. Returns the file path."""
        path = self._dir / f"{report.session_id}.json"
        data = asdict(report)
        data["_saved_at"] = time.time()
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        logger.info(
            "[ExperienceReport] Saved report for %s (%s) → %s",
            report.agent_callsign,
            report.domain,
            path.name,
        )

        # MARKER_ZETA.F2: Smart Debrief — auto-create tasks + route to memory
        try:
            if report.lessons_learned or report.recommendations:
                from src.services.smart_debrief import process_smart_debrief
                process_smart_debrief(report)
        except Exception as e:
            logger.debug("[ExperienceReport] Smart debrief processing failed (non-fatal): %s", e)

        return path

    def get(self, session_id: str) -> Optional[ExperienceReport]:
        """Load report by session_id."""
        path = self._dir / f"{session_id}.json"
        if not path.exists():
            return None
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        data.pop("_saved_at", None)
        return ExperienceReport(**data)

    def list_reports(self, callsign: Optional[str] = None, limit: int = 10) -> list[dict]:
        """List recent reports, optionally filtered by callsign."""
        reports = []
        for path in sorted(self._dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if callsign and data.get("agent_callsign", "").lower() != callsign.lower():
                    continue
                reports.append({
                    "session_id": data.get("session_id", path.stem),
                    "agent_callsign": data.get("agent_callsign", ""),
                    "domain": data.get("domain", ""),
                    "timestamp": data.get("timestamp", ""),
                    "tasks_completed": len(data.get("tasks_completed", [])),
                    "lessons_count": len(data.get("lessons_learned", [])),
                })
                if len(reports) >= limit:
                    break
            except Exception:
                logger.debug("Skipping malformed report: %s", path.name)
        return reports

    def get_latest_for_role(self, callsign: str) -> Optional[ExperienceReport]:
        """Get the most recent report for a given callsign."""
        for path in sorted(self._dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if data.get("agent_callsign", "").lower() == callsign.lower():
                    data.pop("_saved_at", None)
                    return ExperienceReport(**data)
            except Exception:
                continue
        return None


# Singleton
_store_instance: Optional[ExperienceReportStore] = None


def get_experience_store(reports_dir: Optional[Path] = None) -> ExperienceReportStore:
    global _store_instance
    if _store_instance is None or reports_dir is not None:
        _store_instance = ExperienceReportStore(reports_dir)
    return _store_instance


def reset_experience_store() -> None:
    global _store_instance
    _store_instance = None
