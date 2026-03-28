"""
Tests for scripts/qa_fleet.py — QA Fleet Orchestrator.
MARKER_200.QA_FLEET — unit tests for audit checks.
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from scripts.qa_fleet import (
    check_scope,
    check_monochrome_in_diff,
    check_commit_exists,
    check_task_has_deliverable,
    check_title_matches_commit,
    _is_grey,
)


class TestIsGrey:
    def test_short_grey(self):
        assert _is_grey("#aaa") is True
        assert _is_grey("#fff") is True

    def test_short_not_grey(self):
        assert _is_grey("#abc") is False

    def test_long_grey(self):
        assert _is_grey("#222222") is True
        assert _is_grey("#cccccc") is True

    def test_long_not_grey(self):
        assert _is_grey("#5DCAA5") is False
        assert _is_grey("#1f1f2a") is False

    def test_with_alpha_grey(self):
        assert _is_grey("#22222280") is True

    def test_with_alpha_not_grey(self):
        assert _is_grey("#5DCAA580") is False


class TestCheckScope:
    def test_all_in_scope(self):
        result = check_scope(
            ["tests/test_foo.py", "tests/test_bar.py"],
            ["tests/"],
        )
        assert result.passed is True

    def test_out_of_scope(self):
        result = check_scope(
            ["tests/test_foo.py", "src/main.py"],
            ["tests/"],
        )
        assert result.passed is False
        assert "src/main.py" in result.details

    def test_no_restrictions(self):
        result = check_scope(["anything.py"], [])
        assert result.passed is True

    def test_exact_file_match(self):
        result = check_scope(
            ["scripts/qa_fleet.py"],
            ["scripts/qa_fleet.py"],
        )
        assert result.passed is True

    def test_glob_prefix(self):
        result = check_scope(
            ["client/e2e/test_smoke.spec.cjs"],
            ["client/e2e/"],
        )
        assert result.passed is True


class TestCheckMonochrome:
    def test_no_violations(self):
        patch = "+  color: #333;\n+  background: #ffffff;"
        result = check_monochrome_in_diff(patch)
        assert result.passed is True

    def test_color_violation(self):
        patch = "+  color: #5DCAA5;"
        result = check_monochrome_in_diff(patch)
        assert result.passed is False
        assert "5dcaa5" in result.details.lower()

    def test_exempt_line(self):
        patch = "+  // MARKER_COLORS: #ff0000 is ok here"
        result = check_monochrome_in_diff(patch)
        assert result.passed is True

    def test_context_lines_ignored(self):
        patch = "   color: #ff0000;\n-  old: #00ff00;"
        result = check_monochrome_in_diff(patch)
        assert result.passed is True


class TestCheckDeliverable:
    def test_has_files(self):
        result = check_task_has_deliverable(["file.py"], "commit msg")
        assert result.passed is True

    def test_no_files_no_msg(self):
        result = check_task_has_deliverable([], "")
        assert result.passed is False

    def test_msg_but_no_files(self):
        result = check_task_has_deliverable([], "some message")
        assert result.passed is False


class TestTitleMatch:
    def test_good_overlap(self):
        result = check_title_matches_commit(
            "ALPHA-FIX: Restore run_favorites_assembly stubs",
            "fix: restore run_favorites_assembly stubs in pulse_auto_montage.py",
        )
        assert result.passed is True

    def test_no_overlap(self):
        result = check_title_matches_commit(
            "Build audio mixer panel",
            "fix: remove unused CSS variables from timeline",
        )
        assert result.passed is False

    def test_no_commit_message(self):
        result = check_title_matches_commit("Some task", "")
        assert result.passed is False
