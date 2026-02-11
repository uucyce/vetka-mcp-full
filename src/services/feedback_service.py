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


# MARKER_135.FB_LOOP: Feedback summary for Architect injection
def get_feedback_for_architect(max_reports: int = 5) -> Optional[str]:
    """
    Build a concise feedback summary from recent pipeline reports.
    Returns a string to inject into Architect's prompt, or None if no feedback available.

    This closes the feedback loop: past verifier issues → architect awareness.
    """
    _ensure_dirs()
    files = sorted(REPORTS_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not files:
        return None

    recent_issues = []
    recent_improvements = []
    quality_scores = []

    for f in files[:max_reports]:
        try:
            data = json.loads(f.read_text())
            q = data.get("quality_score", 0)
            if q:
                quality_scores.append(q)
            for issue in data.get("issues_found", []):
                if isinstance(issue, dict):
                    desc = ", ".join(issue.get("issues", []))[:120]
                    if desc:
                        recent_issues.append(desc)
                elif isinstance(issue, str):
                    recent_issues.append(issue[:120])
            for imp in data.get("improvements_for_next_run", []):
                if isinstance(imp, str) and imp:
                    recent_improvements.append(imp[:120])
                elif isinstance(imp, dict):
                    recent_improvements.append(imp.get("description", "")[:120])
        except Exception:
            continue

    if not recent_issues and not recent_improvements:
        return None

    # Build concise summary
    parts = ["[FEEDBACK FROM PAST RUNS]"]
    if quality_scores:
        avg_q = sum(quality_scores) / len(quality_scores)
        parts.append(f"Average quality: {avg_q:.1%} ({len(quality_scores)} runs)")
    if recent_issues:
        unique_issues = list(dict.fromkeys(recent_issues))[:5]  # dedupe, limit 5
        parts.append("Recurring issues: " + "; ".join(unique_issues))
    if recent_improvements:
        unique_imps = list(dict.fromkeys(recent_improvements))[:3]
        parts.append("Improvements to apply: " + "; ".join(unique_imps))

    # Patterns
    patterns = detect_patterns(min_occurrences=2)
    recurring = [p for p in patterns if p.get("is_recurring")]
    if recurring:
        pattern_str = ", ".join(f"{p['issue_type']}(×{p['count']})" for p in recurring[:3])
        parts.append(f"Known patterns: {pattern_str}")

    return "\n".join(parts)


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
