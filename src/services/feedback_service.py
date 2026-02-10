# MARKER_134.FEEDBACK: Pipeline feedback and self-improvement service
"""
Feedback Service — collects pipeline reports, detects patterns, suggests improvements.

Flow:
  1. Verifier scores subtask → if < 0.8, structured feedback saved
  2. After pipeline completes → Architect generates final report
  3. Reports accumulate in data/feedback/reports/
  4. Pattern detection finds recurring issues
  5. Opus reviews and creates improvement tasks
"""

import json
import time
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
from collections import Counter

logger = logging.getLogger("VETKA_FEEDBACK")

# MARKER_134.FIX_CWD: Use absolute path from __file__ to avoid CWD issues in MCP context
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
FEEDBACK_DIR = _PROJECT_ROOT / "data" / "feedback"
REPORTS_DIR = FEEDBACK_DIR / "reports"
PATTERNS_FILE = FEEDBACK_DIR / "patterns.json"
IMPROVEMENTS_FILE = FEEDBACK_DIR / "improvements.json"


def _ensure_dirs():
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)


def save_report(report: Dict[str, Any]) -> str:
    """Save a pipeline final report to disk."""
    _ensure_dirs()
    run_id = report.get("run_id", f"run_{int(time.time())}")
    report["run_id"] = run_id
    report["saved_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    path = REPORTS_DIR / f"{run_id}.json"
    path.write_text(json.dumps(report, indent=2, default=str))
    logger.info(f"[Feedback] Saved report: {run_id}")
    return run_id


def get_report(run_id: str) -> Optional[Dict[str, Any]]:
    """Load a single report."""
    path = REPORTS_DIR / f"{run_id}.json"
    if path.exists():
        return json.loads(path.read_text())
    return None


def list_reports(limit: int = 20) -> List[Dict[str, Any]]:
    """List recent reports, newest first."""
    _ensure_dirs()
    files = sorted(REPORTS_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    reports = []
    for f in files[:limit]:
        try:
            data = json.loads(f.read_text())
            # Return summary, not full content
            reports.append({
                "run_id": data.get("run_id"),
                "task": data.get("task", "")[:100],
                "quality_score": data.get("quality_score"),
                "issues_count": len(data.get("issues_found", [])),
                "improvements_count": len(data.get("improvements_for_next_run", [])),
                "preset": data.get("preset"),
                "status": data.get("status"),
                "duration_s": data.get("duration_s"),
                "saved_at": data.get("saved_at"),
            })
        except Exception:
            continue
    return reports


def save_verifier_feedback(
    task_id: str,
    subtask_marker: str,
    score: float,
    issues: List[str],
    suggestion: str,
    severity: str = "medium",
):
    """Save structured verifier feedback for a subtask."""
    _ensure_dirs()
    feedback = {
        "task_id": task_id,
        "subtask_marker": subtask_marker,
        "score": score,
        "issues": issues,
        "suggestion": suggestion,
        "severity": severity,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }

    # Append to task-specific feedback file
    feedback_file = FEEDBACK_DIR / f"verifier_{task_id}.json"
    existing = []
    if feedback_file.exists():
        try:
            existing = json.loads(feedback_file.read_text())
        except Exception:
            pass
    existing.append(feedback)
    feedback_file.write_text(json.dumps(existing, indent=2, default=str))
    return feedback


def detect_patterns(min_occurrences: int = 3) -> List[Dict[str, Any]]:
    """Detect recurring issues across all reports."""
    _ensure_dirs()
    all_issues: List[str] = []

    for f in REPORTS_DIR.glob("*.json"):
        try:
            data = json.loads(f.read_text())
            for issue in data.get("issues_found", []):
                if isinstance(issue, dict):
                    all_issues.append(issue.get("type", "unknown"))
                elif isinstance(issue, str):
                    all_issues.append(issue)
        except Exception:
            continue

    # Count occurrences
    counter = Counter(all_issues)
    patterns = [
        {"issue_type": issue, "count": count, "is_recurring": count >= min_occurrences}
        for issue, count in counter.most_common(20)
        if count >= 2  # Show anything with 2+ occurrences
    ]

    # Save patterns
    PATTERNS_FILE.parent.mkdir(parents=True, exist_ok=True)
    PATTERNS_FILE.write_text(json.dumps({
        "patterns": patterns,
        "total_reports_analyzed": len(list(REPORTS_DIR.glob("*.json"))),
        "analyzed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }, indent=2))

    return patterns


def get_improvements() -> List[Dict[str, Any]]:
    """Get accumulated improvement suggestions."""
    if IMPROVEMENTS_FILE.exists():
        try:
            data = json.loads(IMPROVEMENTS_FILE.read_text())
            return data.get("improvements", [])
        except Exception:
            pass
    return []


def add_improvement(
    category: str,
    description: str,
    source_reports: List[str],
    priority: str = "medium",
):
    """Add an improvement suggestion (from Opus review)."""
    improvements = get_improvements()
    improvements.append({
        "id": f"imp_{int(time.time())}",
        "category": category,
        "description": description,
        "source_reports": source_reports,
        "priority": priority,
        "status": "pending",
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    })
    IMPROVEMENTS_FILE.parent.mkdir(parents=True, exist_ok=True)
    IMPROVEMENTS_FILE.write_text(json.dumps({"improvements": improvements}, indent=2))
