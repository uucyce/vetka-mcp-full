# MARKER_135.TEST_FB: Tests for Phase 135 feedback loop
"""
Tests for feedback_service.py — specifically the feedback loop:
  save_report() → get_feedback_for_architect() → architect injection

Covers:
  - Report saving and retrieval
  - Feedback generation from reports with issues
  - Feedback returns None when all runs are clean
  - Pattern detection across multiple reports
  - Improvement generation from verifier issues
  - Deduplication of issues and improvements
  - Max reports limit
"""

import json
import time
import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch


# ============================================================
# Fixtures
# ============================================================

@pytest.fixture
def temp_feedback_dir(tmp_path):
    """Create a temporary feedback directory structure."""
    reports_dir = tmp_path / "data" / "feedback" / "reports"
    reports_dir.mkdir(parents=True)
    patterns_file = tmp_path / "data" / "feedback" / "patterns.json"
    improvements_file = tmp_path / "data" / "feedback" / "improvements.json"
    return {
        "root": tmp_path,
        "reports_dir": reports_dir,
        "patterns_file": patterns_file,
        "improvements_file": improvements_file,
    }


@pytest.fixture
def patched_feedback(temp_feedback_dir):
    """Patch feedback_service module-level paths to use temp dir."""
    import src.services.feedback_service as fb
    original_reports = fb.REPORTS_DIR
    original_feedback = fb.FEEDBACK_DIR
    original_patterns = fb.PATTERNS_FILE
    original_improvements = fb.IMPROVEMENTS_FILE

    fb.REPORTS_DIR = temp_feedback_dir["reports_dir"]
    fb.FEEDBACK_DIR = temp_feedback_dir["reports_dir"].parent
    fb.PATTERNS_FILE = temp_feedback_dir["patterns_file"]
    fb.IMPROVEMENTS_FILE = temp_feedback_dir["improvements_file"]

    yield fb

    # Restore
    fb.REPORTS_DIR = original_reports
    fb.FEEDBACK_DIR = original_feedback
    fb.PATTERNS_FILE = original_patterns
    fb.IMPROVEMENTS_FILE = original_improvements


def _make_report(
    run_id: str = "test_run",
    quality: float = 0.9,
    issues: list = None,
    improvements: list = None,
    status: str = "done",
    preset: str = "dragon_bronze",
    duration: float = 45.0,
) -> dict:
    """Helper to create a report dict."""
    return {
        "run_id": run_id,
        "task": f"Test task for {run_id}",
        "summary": "Completed 1/1 subtasks",
        "quality_score": quality,
        "issues_found": issues or [],
        "improvements_for_next_run": improvements or [],
        "tokens_used": 5000,
        "duration_s": duration,
        "preset": preset,
        "status": status,
        "subtasks_total": 1,
        "subtasks_completed": 1,
        "retries": 0,
        "tier_upgrades": 0,
    }


# ============================================================
# Test: save_report and get_report
# ============================================================

class TestSaveAndGetReport:
    def test_save_report_creates_file(self, patched_feedback):
        fb = patched_feedback
        report = _make_report(run_id="save_test_001")
        result = fb.save_report(report)
        assert result == "save_test_001"
        assert (fb.REPORTS_DIR / "save_test_001.json").exists()

    def test_save_report_adds_saved_at(self, patched_feedback):
        fb = patched_feedback
        report = _make_report(run_id="save_test_002")
        fb.save_report(report)
        loaded = fb.get_report("save_test_002")
        assert "saved_at" in loaded
        assert loaded["saved_at"].endswith("Z")

    def test_get_report_returns_none_for_missing(self, patched_feedback):
        fb = patched_feedback
        assert fb.get_report("nonexistent") is None

    def test_list_reports_returns_summaries(self, patched_feedback):
        fb = patched_feedback
        fb.save_report(_make_report(run_id="list_001", quality=0.8))
        fb.save_report(_make_report(run_id="list_002", quality=0.95))
        reports = fb.list_reports(limit=10)
        assert len(reports) == 2
        assert all("quality_score" in r for r in reports)

    def test_list_reports_limit(self, patched_feedback):
        fb = patched_feedback
        for i in range(5):
            fb.save_report(_make_report(run_id=f"limit_{i}"))
        reports = fb.list_reports(limit=3)
        assert len(reports) == 3


# ============================================================
# Test: get_feedback_for_architect (the core feedback loop)
# ============================================================

class TestFeedbackForArchitect:
    def test_returns_none_when_no_reports(self, patched_feedback):
        fb = patched_feedback
        result = fb.get_feedback_for_architect()
        assert result is None

    def test_returns_none_when_all_clean(self, patched_feedback):
        """All reports have no issues and no improvements → no feedback needed."""
        fb = patched_feedback
        fb.save_report(_make_report(run_id="clean_001", quality=0.95))
        fb.save_report(_make_report(run_id="clean_002", quality=0.9))
        result = fb.get_feedback_for_architect()
        assert result is None

    def test_returns_feedback_when_issues_exist(self, patched_feedback):
        fb = patched_feedback
        fb.save_report(_make_report(
            run_id="issue_001",
            quality=0.6,
            issues=[
                {"type": "verifier_fail", "marker": "STEP_1",
                 "issues": ["Missing error handling"], "severity": "major"}
            ],
        ))
        result = fb.get_feedback_for_architect()
        assert result is not None
        assert "[FEEDBACK FROM PAST RUNS]" in result
        assert "Missing error handling" in result

    def test_returns_feedback_when_improvements_exist(self, patched_feedback):
        fb = patched_feedback
        fb.save_report(_make_report(
            run_id="imp_001",
            improvements=["Add input validation", "Break complex tasks into subtasks"],
        ))
        result = fb.get_feedback_for_architect()
        assert result is not None
        assert "Add input validation" in result

    def test_includes_average_quality(self, patched_feedback):
        fb = patched_feedback
        fb.save_report(_make_report(run_id="q1", quality=0.6, issues=[{"type": "fail", "issues": ["bug"]}]))
        fb.save_report(_make_report(run_id="q2", quality=0.8, issues=[{"type": "fail", "issues": ["bug2"]}]))
        result = fb.get_feedback_for_architect()
        assert "Average quality:" in result
        # (0.6 + 0.8) / 2 = 0.7 = 70.0%
        assert "70.0%" in result

    def test_deduplicates_issues(self, patched_feedback):
        fb = patched_feedback
        # Same issue appears in multiple reports
        for i in range(3):
            fb.save_report(_make_report(
                run_id=f"dup_{i}",
                issues=[{"type": "verifier_fail", "issues": ["Same issue repeated"]}],
            ))
        result = fb.get_feedback_for_architect()
        # Should only appear once in output
        assert result.count("Same issue repeated") == 1

    def test_limits_issues_to_5(self, patched_feedback):
        fb = patched_feedback
        issues = [
            {"type": "fail", "issues": [f"Issue number {i}"]}
            for i in range(10)
        ]
        fb.save_report(_make_report(run_id="many_issues", issues=issues))
        result = fb.get_feedback_for_architect()
        # Should have at most 5 unique issues
        assert result is not None
        issue_line = [l for l in result.split("\n") if "Recurring issues:" in l]
        assert len(issue_line) == 1
        # Count semicolons (separator between issues)
        assert issue_line[0].count(";") <= 4  # max 5 items = 4 separators

    def test_limits_improvements_to_3(self, patched_feedback):
        fb = patched_feedback
        improvements = [f"Improvement {i}" for i in range(8)]
        fb.save_report(_make_report(run_id="many_imps", improvements=improvements))
        result = fb.get_feedback_for_architect()
        imp_line = [l for l in result.split("\n") if "Improvements to apply:" in l]
        assert len(imp_line) == 1
        assert imp_line[0].count(";") <= 2  # max 3 items = 2 separators

    def test_max_reports_parameter(self, patched_feedback):
        fb = patched_feedback
        # Create 5 reports, only first 2 have issues
        for i in range(5):
            issues = [{"type": "fail", "issues": [f"Old issue {i}"]}] if i < 2 else []
            fb.save_report(_make_report(run_id=f"maxr_{i}", quality=0.5 + i * 0.1, issues=issues))
            time.sleep(0.01)  # Ensure different mtime
        # With max_reports=2, should only see the 2 most recent (which have NO issues)
        result = fb.get_feedback_for_architect(max_reports=2)
        # Most recent 2 are maxr_3, maxr_4 — no issues
        assert result is None

    def test_handles_string_issues(self, patched_feedback):
        """Issues can be strings (not just dicts)."""
        fb = patched_feedback
        fb.save_report(_make_report(
            run_id="str_issue",
            issues=["Simple string issue", "Another string issue"],
        ))
        result = fb.get_feedback_for_architect()
        assert "Simple string issue" in result

    def test_handles_dict_improvements(self, patched_feedback):
        """Improvements can be dicts with 'description' key."""
        fb = patched_feedback
        fb.save_report(_make_report(
            run_id="dict_imp",
            improvements=[{"description": "Use better prompts", "priority": "high"}],
        ))
        result = fb.get_feedback_for_architect()
        assert "Use better prompts" in result


# ============================================================
# Test: detect_patterns
# ============================================================

class TestDetectPatterns:
    def test_empty_reports(self, patched_feedback):
        fb = patched_feedback
        patterns = fb.detect_patterns()
        assert patterns == []

    def test_detects_recurring_pattern(self, patched_feedback):
        fb = patched_feedback
        # Same issue type 3 times → recurring
        for i in range(3):
            fb.save_report(_make_report(
                run_id=f"pat_{i}",
                issues=[{"type": "missing_tests", "issues": [f"No tests run {i}"]}],
            ))
        patterns = fb.detect_patterns(min_occurrences=3)
        assert len(patterns) == 1
        assert patterns[0]["issue_type"] == "missing_tests"
        assert patterns[0]["count"] == 3
        assert patterns[0]["is_recurring"] is True

    def test_non_recurring_still_shown_if_2plus(self, patched_feedback):
        fb = patched_feedback
        for i in range(2):
            fb.save_report(_make_report(
                run_id=f"nr_{i}",
                issues=[{"type": "timeout", "issues": ["Slow"]}],
            ))
        patterns = fb.detect_patterns(min_occurrences=3)
        assert len(patterns) == 1
        assert patterns[0]["is_recurring"] is False  # count=2 < min_occurrences=3

    def test_saves_patterns_file(self, patched_feedback):
        fb = patched_feedback
        fb.save_report(_make_report(run_id="pf_1", issues=[{"type": "bug", "issues": ["x"]}]))
        fb.save_report(_make_report(run_id="pf_2", issues=[{"type": "bug", "issues": ["y"]}]))
        fb.detect_patterns()
        assert fb.PATTERNS_FILE.exists()
        data = json.loads(fb.PATTERNS_FILE.read_text())
        assert "patterns" in data
        assert "total_reports_analyzed" in data

    def test_feedback_includes_patterns(self, patched_feedback):
        """get_feedback_for_architect should include pattern info."""
        fb = patched_feedback
        for i in range(3):
            fb.save_report(_make_report(
                run_id=f"fb_pat_{i}",
                issues=[{"type": "verifier_fail", "issues": ["Bad code"]}],
            ))
        result = fb.get_feedback_for_architect()
        assert "Known patterns:" in result
        assert "verifier_fail" in result


# ============================================================
# Test: verifier feedback persistence
# ============================================================

class TestVerifierFeedback:
    def test_save_verifier_feedback(self, patched_feedback):
        fb = patched_feedback
        result = fb.save_verifier_feedback(
            task_id="vf_001",
            subtask_marker="STEP_1",
            score=0.5,
            issues=["Missing docstring"],
            suggestion="Add docstring to function",
            severity="medium",
        )
        assert result["score"] == 0.5
        feedback_file = fb.FEEDBACK_DIR / "verifier_vf_001.json"
        assert feedback_file.exists()

    def test_verifier_feedback_appends(self, patched_feedback):
        fb = patched_feedback
        fb.save_verifier_feedback("vf_002", "STEP_1", 0.6, ["Issue 1"], "Fix 1")
        fb.save_verifier_feedback("vf_002", "STEP_2", 0.4, ["Issue 2"], "Fix 2")
        feedback_file = fb.FEEDBACK_DIR / "verifier_vf_002.json"
        data = json.loads(feedback_file.read_text())
        assert len(data) == 2


# ============================================================
# Test: add_improvement
# ============================================================

class TestAddImprovement:
    def test_add_improvement(self, patched_feedback):
        fb = patched_feedback
        fb.add_improvement(
            category="prompt_quality",
            description="Be more specific in coder prompts",
            source_reports=["run_001", "run_002"],
            priority="high",
        )
        improvements = fb.get_improvements()
        assert len(improvements) == 1
        assert improvements[0]["category"] == "prompt_quality"
        assert improvements[0]["priority"] == "high"

    def test_improvements_accumulate(self, patched_feedback):
        fb = patched_feedback
        fb.add_improvement("cat1", "desc1", ["r1"])
        fb.add_improvement("cat2", "desc2", ["r2"])
        improvements = fb.get_improvements()
        assert len(improvements) == 2
