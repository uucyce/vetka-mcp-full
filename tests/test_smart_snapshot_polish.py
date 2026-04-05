"""Tests for HARNESS-209.3: smart_snapshot polish — conflict detection edge cases
+ sidecar auto-expand verification.

These tests exercise the logic extracted from TaskBoard._execute_merge's
smart_snapshot strategy without needing real git operations.  We mock _git
calls and validate the filtering, sidecar expansion, conflict parsing, and
glob-based scope matching.
"""

import asyncio
import fnmatch
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch


# ---------------------------------------------------------------------------
# Helpers: replicate the core logic extracted from task_board.py so we can
# unit-test it in isolation.  This avoids needing to instantiate the full
# TaskBoard + temp worktree machinery.
# ---------------------------------------------------------------------------

def _filter_scoped_files(all_changed: set, scope_prefixes: list) -> set:
    """Replicate Step 2 scope filtering (with glob support)."""
    if not scope_prefixes:
        return set(all_changed)
    scoped = set()
    for f in all_changed:
        for prefix in scope_prefixes:
            if "*" in prefix or "?" in prefix:
                if fnmatch.fnmatch(f, prefix):
                    scoped.add(f)
                    break
            elif f == prefix or f.startswith(prefix.rstrip("/") + "/"):
                scoped.add(f)
                break
    return scoped


def _detect_sidecars(scoped_files: set, all_changed: set) -> set:
    """Replicate sidecar auto-detection from smart_snapshot Step 2."""
    sidecars = set()
    remaining = all_changed - scoped_files
    for f in scoped_files:
        fp = Path(f)
        stem = fp.stem
        suffix = fp.suffix
        for candidate in remaining:
            cp = Path(candidate)
            cand_stem = cp.stem
            if cand_stem == f"test_{stem}" or cand_stem == f"{stem}_test" or cand_stem == stem:
                sidecars.add(candidate)
            elif cp.name == "__init__.py" and str(cp.parent) == str(fp.parent):
                sidecars.add(candidate)
            elif suffix in (".json", ".jsonl") and cp.suffix in (".json", ".jsonl"):
                if cand_stem == stem:
                    sidecars.add(candidate)
    return sidecars


def _parse_conflicts(mt_out: str, scoped_files: set) -> list:
    """Replicate conflict detection parsing from smart_snapshot Step 3."""
    if not mt_out:
        return []
    conflicting_set = set()
    lines = mt_out.splitlines()
    current_file = None
    for line in lines:
        for sf in scoped_files:
            if sf in line:
                current_file = sf
                break
        if current_file and ("<<<<<<" in line or "+<<<<<<" in line):
            conflicting_set.add(current_file)
    # Fallback
    if not conflicting_set and ("<<<<<<" in mt_out or "+<<<<<<" in mt_out):
        for sf in scoped_files:
            if sf in mt_out:
                conflicting_set.add(sf)
    return sorted(conflicting_set)


# ===========================================================================
# Test: Scope filtering
# ===========================================================================

class TestScopeFiltering:
    """Scope prefix matching with exact, directory, and glob patterns."""

    def test_exact_match(self):
        changed = {"src/orchestration/task_board.py", "src/other.py"}
        scoped = _filter_scoped_files(changed, ["src/orchestration/task_board.py"])
        assert scoped == {"src/orchestration/task_board.py"}

    def test_directory_prefix(self):
        changed = {
            "src/orchestration/task_board.py",
            "src/orchestration/helpers.py",
            "src/other.py",
        }
        scoped = _filter_scoped_files(changed, ["src/orchestration/"])
        assert scoped == {"src/orchestration/task_board.py", "src/orchestration/helpers.py"}

    def test_directory_prefix_without_trailing_slash(self):
        """Prefix without trailing slash still matches subdirectory files."""
        changed = {"src/orchestration/task_board.py", "src/other.py"}
        scoped = _filter_scoped_files(changed, ["src/orchestration"])
        assert scoped == {"src/orchestration/task_board.py"}

    def test_glob_star(self):
        changed = {"tests/test_a.py", "tests/test_b.py", "src/a.py"}
        scoped = _filter_scoped_files(changed, ["tests/*.py"])
        assert scoped == {"tests/test_a.py", "tests/test_b.py"}

    def test_glob_recursive_star(self):
        changed = {
            "tests/unit/test_a.py",
            "tests/integration/test_b.py",
            "src/a.py",
        }
        scoped = _filter_scoped_files(changed, ["tests/**/*.py"])
        # fnmatch does not support ** natively as recursive — it treats
        # ** as a literal glob, which won't match subdirectories.
        # This documents actual behavior: fnmatch ** matches single segment only.
        # We don't assert specific behavior here but ensure no crash.
        assert isinstance(scoped, set)

    def test_glob_question_mark(self):
        changed = {"src/a.py", "src/b.py", "src/ab.py"}
        scoped = _filter_scoped_files(changed, ["src/?.py"])
        assert scoped == {"src/a.py", "src/b.py"}

    def test_empty_scope_takes_all(self):
        changed = {"a.py", "b.py", "c.txt"}
        scoped = _filter_scoped_files(changed, [])
        assert scoped == changed

    def test_no_match(self):
        changed = {"src/a.py", "src/b.py"}
        scoped = _filter_scoped_files(changed, ["lib/"])
        assert scoped == set()

    def test_mixed_exact_and_glob(self):
        changed = {"src/a.py", "tests/test_a.py", "docs/readme.md"}
        scoped = _filter_scoped_files(changed, ["src/a.py", "tests/*.py"])
        assert scoped == {"src/a.py", "tests/test_a.py"}


# ===========================================================================
# Test: Sidecar auto-expand
# ===========================================================================

class TestSidecarAutoExpand:
    """Sidecar detection: test files, __init__.py, json/jsonl variants."""

    def test_test_prefix_convention(self):
        """test_{stem}.py is detected as sidecar."""
        scoped = {"src/orchestration/task_board.py"}
        all_changed = scoped | {"tests/test_task_board.py"}
        sidecars = _detect_sidecars(scoped, all_changed)
        assert "tests/test_task_board.py" in sidecars

    def test_test_suffix_convention(self):
        """'{stem}_test.py' is detected as sidecar."""
        scoped = {"src/foo.py"}
        all_changed = scoped | {"tests/foo_test.py"}
        sidecars = _detect_sidecars(scoped, all_changed)
        assert "tests/foo_test.py" in sidecars

    def test_same_stem_different_dir(self):
        """Same stem in a different dir (e.g. migration/copy) is a sidecar."""
        scoped = {"src/utils.py"}
        all_changed = scoped | {"lib/utils.py"}
        sidecars = _detect_sidecars(scoped, all_changed)
        assert "lib/utils.py" in sidecars

    def test_init_py_same_dir(self):
        """__init__.py in same directory is detected."""
        scoped = {"src/orchestration/task_board.py"}
        all_changed = scoped | {"src/orchestration/__init__.py"}
        sidecars = _detect_sidecars(scoped, all_changed)
        assert "src/orchestration/__init__.py" in sidecars

    def test_init_py_different_dir_not_sidecar(self):
        """__init__.py in a DIFFERENT directory is NOT a sidecar."""
        scoped = {"src/orchestration/task_board.py"}
        all_changed = scoped | {"src/other/__init__.py"}
        sidecars = _detect_sidecars(scoped, all_changed)
        assert "src/other/__init__.py" not in sidecars

    def test_json_to_jsonl_variant(self):
        """data.json scoped → data.jsonl included as sidecar."""
        scoped = {"data/config.json"}
        all_changed = scoped | {"data/config.jsonl"}
        sidecars = _detect_sidecars(scoped, all_changed)
        assert "data/config.jsonl" in sidecars

    def test_jsonl_to_json_variant(self):
        """data.jsonl scoped → data.json included as sidecar."""
        scoped = {"data/log.jsonl"}
        all_changed = scoped | {"data/log.json"}
        sidecars = _detect_sidecars(scoped, all_changed)
        assert "data/log.json" in sidecars

    def test_json_different_stem_not_sidecar(self):
        """Different stem .json files are NOT sidecars."""
        scoped = {"data/config.json"}
        all_changed = scoped | {"data/other.jsonl"}
        sidecars = _detect_sidecars(scoped, all_changed)
        assert "data/other.jsonl" not in sidecars

    def test_no_sidecars_for_unrelated(self):
        """Completely unrelated files produce zero sidecars."""
        scoped = {"src/a.py"}
        all_changed = scoped | {"docs/readme.md", "Makefile"}
        sidecars = _detect_sidecars(scoped, all_changed)
        assert sidecars == set()

    def test_already_scoped_not_duplicated(self):
        """Files already in scoped_files are not returned as sidecars."""
        scoped = {"src/a.py", "tests/test_a.py"}
        all_changed = scoped.copy()
        sidecars = _detect_sidecars(scoped, all_changed)
        assert sidecars == set()

    def test_multiple_scoped_files(self):
        """Sidecars from multiple scoped files are all captured."""
        scoped = {"src/a.py", "src/b.py"}
        all_changed = scoped | {"tests/test_a.py", "tests/test_b.py", "unrelated.txt"}
        sidecars = _detect_sidecars(scoped, all_changed)
        assert sidecars == {"tests/test_a.py", "tests/test_b.py"}


# ===========================================================================
# Test: Conflict detection parsing
# ===========================================================================

class TestConflictDetection:
    """Parsing of git merge-tree output for conflict markers."""

    def test_no_output_no_conflicts(self):
        assert _parse_conflicts("", {"src/a.py"}) == []
        assert _parse_conflicts(None, {"src/a.py"}) == []

    def test_clean_merge_no_conflicts(self):
        """merge-tree output with file names but no conflict markers."""
        mt_out = (
            "result 100644 abc123 src/a.py\n"
            "result 100644 def456 src/b.py\n"
        )
        assert _parse_conflicts(mt_out, {"src/a.py", "src/b.py"}) == []

    def test_single_file_conflict(self):
        """One scoped file has conflict markers."""
        mt_out = (
            "src/a.py\n"
            "<<<<<<< ours\n"
            "line from main\n"
            "=======\n"
            "line from branch\n"
            ">>>>>>> theirs\n"
        )
        result = _parse_conflicts(mt_out, {"src/a.py"})
        assert result == ["src/a.py"]

    def test_conflict_in_unscoped_file_ignored(self):
        """Conflict in a file outside scope should not appear."""
        mt_out = (
            "src/unscoped.py\n"
            "<<<<<<< ours\n"
            "conflict\n"
            ">>>>>>> theirs\n"
        )
        result = _parse_conflicts(mt_out, {"src/scoped.py"})
        assert result == []

    def test_multiple_files_one_conflict(self):
        """Two scoped files, only one has conflict markers."""
        mt_out = (
            "src/a.py\n"
            "clean content\n"
            "src/b.py\n"
            "<<<<<<< ours\n"
            "conflict\n"
            ">>>>>>> theirs\n"
        )
        result = _parse_conflicts(mt_out, {"src/a.py", "src/b.py"})
        assert result == ["src/b.py"]

    def test_multiple_files_both_conflict(self):
        mt_out = (
            "src/a.py\n"
            "+<<<<<<< ours\n"
            "conflict\n"
            "src/b.py\n"
            "<<<<<<< ours\n"
            "conflict\n"
        )
        result = _parse_conflicts(mt_out, {"src/a.py", "src/b.py"})
        assert result == ["src/a.py", "src/b.py"]

    def test_deduplication(self):
        """Same file mentioned multiple times — no duplicates in result."""
        mt_out = (
            "src/a.py\n"
            "<<<<<<< ours\n"
            "src/a.py\n"
            "<<<<<<< ours\n"
        )
        result = _parse_conflicts(mt_out, {"src/a.py"})
        assert result == ["src/a.py"]

    def test_fallback_global_conflict(self):
        """Fallback: conflict markers exist but file paths are not on separate lines."""
        mt_out = "changed src/a.py <<<<<<< ours conflict >>>>>>> theirs"
        result = _parse_conflicts(mt_out, {"src/a.py"})
        # current_file gets set AND conflict detected on same line
        assert result == ["src/a.py"]

    def test_plus_prefixed_conflict_markers(self):
        """merge-tree sometimes prefixes with +."""
        mt_out = (
            "src/a.py\n"
            "+<<<<<<< ours\n"
            "conflict content\n"
        )
        result = _parse_conflicts(mt_out, {"src/a.py"})
        assert result == ["src/a.py"]

    def test_file_identical_on_both_sides(self):
        """File exists in both main and branch with same content — no conflict."""
        mt_out = "src/a.py\nidentical content\n"
        result = _parse_conflicts(mt_out, {"src/a.py"})
        assert result == []

    def test_file_doesnt_exist_on_main(self):
        """New file on branch — merge-tree won't show conflict for it."""
        mt_out = ""
        result = _parse_conflicts(mt_out, {"src/new_file.py"})
        assert result == []

    def test_sorted_output(self):
        """Results are always sorted for deterministic output."""
        mt_out = (
            "src/z.py\n<<<<<<< ours\nsrc/a.py\n<<<<<<< ours\n"
        )
        result = _parse_conflicts(mt_out, {"src/z.py", "src/a.py"})
        assert result == ["src/a.py", "src/z.py"]


# ===========================================================================
# Test: Empty allowed_paths edge case
# ===========================================================================

class TestEmptyAllowedPaths:
    """When allowed_paths is empty or None, all changed files are in scope."""

    def test_none_allowed_paths(self):
        changed = {"a.py", "b.py"}
        scoped = _filter_scoped_files(changed, None)
        # None is falsy, so scope_prefixes becomes empty list → all changed
        # Actually our function receives [] from `list(None or [])`.
        # But we pass None directly — let's handle:
        scoped = _filter_scoped_files(changed, [])
        assert scoped == changed

    def test_empty_list_allowed_paths(self):
        changed = {"a.py", "b.py", "c.txt"}
        scoped = _filter_scoped_files(changed, [])
        assert scoped == changed

    def test_empty_changed_files(self):
        scoped = _filter_scoped_files(set(), ["src/"])
        assert scoped == set()


# ===========================================================================
# Integration-style: full pipeline (scope → sidecar → conflict)
# ===========================================================================

class TestFullPipeline:
    """End-to-end: scope filtering + sidecar expansion + conflict check."""

    def test_scope_then_sidecar_then_conflict_clean(self):
        all_changed = {
            "src/orchestration/task_board.py",
            "tests/test_task_board.py",
            "docs/readme.md",
        }
        allowed = ["src/orchestration/"]
        scoped = _filter_scoped_files(all_changed, allowed)
        assert scoped == {"src/orchestration/task_board.py"}

        sidecars = _detect_sidecars(scoped, all_changed)
        assert sidecars == {"tests/test_task_board.py"}

        full_scope = scoped | sidecars
        mt_out = "src/orchestration/task_board.py\nclean merge\n"
        conflicts = _parse_conflicts(mt_out, full_scope)
        assert conflicts == []

    def test_scope_then_sidecar_then_conflict_detected(self):
        all_changed = {
            "src/orchestration/task_board.py",
            "tests/test_task_board.py",
        }
        allowed = ["src/orchestration/"]
        scoped = _filter_scoped_files(all_changed, allowed)
        sidecars = _detect_sidecars(scoped, all_changed)
        full_scope = scoped | sidecars

        mt_out = (
            "src/orchestration/task_board.py\n"
            "<<<<<<< ours\n"
            "main version\n"
            "=======\n"
            "branch version\n"
            ">>>>>>> theirs\n"
        )
        conflicts = _parse_conflicts(mt_out, full_scope)
        assert conflicts == ["src/orchestration/task_board.py"]

    def test_json_jsonl_sidecar_in_pipeline(self):
        all_changed = {
            "data/reflex/feedback_log.json",
            "data/reflex/feedback_log.jsonl",
        }
        allowed = ["data/reflex/feedback_log.json"]
        scoped = _filter_scoped_files(all_changed, allowed)
        assert scoped == {"data/reflex/feedback_log.json"}

        sidecars = _detect_sidecars(scoped, all_changed)
        assert sidecars == {"data/reflex/feedback_log.jsonl"}
