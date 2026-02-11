# MARKER_136.FEEDBACK_INTEGRATION_TEST
import json

import pytest

import src.services.feedback_service as fb


@pytest.fixture
def patched_feedback_paths(monkeypatch, tmp_path):
    feedback_dir = tmp_path / "data" / "feedback"
    reports_dir = feedback_dir / "reports"
    patterns_file = feedback_dir / "patterns.json"
    improvements_file = feedback_dir / "improvements.json"

    monkeypatch.setattr(fb, "FEEDBACK_DIR", feedback_dir)
    monkeypatch.setattr(fb, "REPORTS_DIR", reports_dir)
    monkeypatch.setattr(fb, "PATTERNS_FILE", patterns_file)
    monkeypatch.setattr(fb, "IMPROVEMENTS_FILE", improvements_file)

    return {
        "feedback_dir": feedback_dir,
        "reports_dir": reports_dir,
        "patterns_file": patterns_file,
        "improvements_file": improvements_file,
    }


def test_pipeline_report_then_feedback_context(patched_feedback_paths):
    # Simulate first pipeline run writing structured report.
    run_id = fb.save_report(
        {
            "run_id": "phase136_fb_1",
            "task": "Implement auth endpoint",
            "quality_score": 0.62,
            "issues_found": [
                {"type": "verifier_fail", "issues": ["Missing error handling"]},
                {"type": "tests_missing", "issues": ["No integration test"]},
            ],
            "improvements_for_next_run": ["Add explicit error path tests"],
            "status": "done",
        }
    )
    assert run_id == "phase136_fb_1"

    # Next pipeline run should receive feedback for architect prompt injection.
    context = fb.get_feedback_for_architect(max_reports=5)
    assert context is not None
    assert "[FEEDBACK FROM PAST RUNS]" in context
    assert "Missing error handling" in context
    assert "Add explicit error path tests" in context


def test_feedback_handles_corrupt_report_file(patched_feedback_paths):
    reports_dir = patched_feedback_paths["reports_dir"]
    reports_dir.mkdir(parents=True, exist_ok=True)

    # One invalid JSON report + one valid report.
    (reports_dir / "corrupt.json").write_text("{not-valid-json", encoding="utf-8")
    (reports_dir / "valid.json").write_text(
        json.dumps(
            {
                "run_id": "valid",
                "quality_score": 0.55,
                "issues_found": [{"type": "runtime", "issues": ["Crash in handler"]}],
                "improvements_for_next_run": [],
            }
        ),
        encoding="utf-8",
    )

    context = fb.get_feedback_for_architect(max_reports=10)
    assert context is not None
    assert "Crash in handler" in context


def test_feedback_handles_empty_or_missing_reports_dir(patched_feedback_paths):
    # reports dir is missing initially by fixture design
    context_initial = fb.get_feedback_for_architect()
    assert context_initial is None

    # exists but empty
    patched_feedback_paths["reports_dir"].mkdir(parents=True, exist_ok=True)
    context_empty = fb.get_feedback_for_architect()
    assert context_empty is None

