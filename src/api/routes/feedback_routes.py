# MARKER_134.FEEDBACK_API: Pipeline feedback and self-improvement endpoints
"""
Feedback API — reports, patterns, improvements from pipeline runs.

Endpoints:
  GET  /api/feedback/reports       — List recent pipeline reports
  GET  /api/feedback/reports/{id}  — Get single report
  GET  /api/feedback/patterns      — Recurring issues across runs
  GET  /api/feedback/improvements  — Opus-generated improvement suggestions
  POST /api/feedback/improvements  — Add improvement (from Opus review)
"""

from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Body, Query

router = APIRouter(prefix="/api/feedback", tags=["feedback"])


@router.get("/reports")
async def list_reports(limit: int = Query(20, ge=1, le=100)):
    """List recent pipeline reports, newest first."""
    from src.services.feedback_service import list_reports
    reports = list_reports(limit=limit)
    return {"success": True, "reports": reports, "count": len(reports)}


@router.get("/reports/{run_id}")
async def get_report(run_id: str):
    """Get a single pipeline report by run_id."""
    from src.services.feedback_service import get_report
    report = get_report(run_id)
    if report is None:
        return {"success": False, "error": f"Report {run_id} not found"}
    return {"success": True, "report": report}


@router.get("/patterns")
async def get_patterns(min_occurrences: int = Query(2, ge=1)):
    """Detect recurring issues across all pipeline reports."""
    from src.services.feedback_service import detect_patterns
    patterns = detect_patterns(min_occurrences=min_occurrences)
    return {"success": True, "patterns": patterns}


@router.get("/improvements")
async def get_improvements():
    """Get accumulated improvement suggestions."""
    from src.services.feedback_service import get_improvements
    improvements = get_improvements()
    return {"success": True, "improvements": improvements, "count": len(improvements)}


@router.post("/improvements")
async def add_improvement(body: Dict[str, Any] = Body(...)):
    """
    Add an improvement suggestion (from Opus review).
    Body: {"category": "prompts", "description": "...", "source_reports": ["run_xxx"], "priority": "high"}
    """
    from src.services.feedback_service import add_improvement
    add_improvement(
        category=body.get("category", "general"),
        description=body.get("description", ""),
        source_reports=body.get("source_reports", []),
        priority=body.get("priority", "medium"),
    )
    return {"success": True}
