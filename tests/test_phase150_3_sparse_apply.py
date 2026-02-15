"""
Tests for Phase 150.3: Sparse Apply (PatchApplier).

Tests:
- Marker insert: INSERT_AFTER, INSERT_BEFORE, REPLACE
- Marker insert: line number fallback, marker:line format
- Unified diff: single hunk, multiple hunks
- Mode detection: auto-detect from coder output
- Extract patches from coder output
- Error handling: missing file, missing marker

@phase 150.3
"""
import os
import pytest
import tempfile
from pathlib import Path

from src.tools.patch_applier import PatchApplier, PatchResult


# ── Fixtures ──

@pytest.fixture
def tmp_dir():
    """Create a temp directory for test files."""
    with tempfile.TemporaryDirectory() as d:
        yield d


@pytest.fixture
def applier(tmp_dir):
    """PatchApplier with temp directory as base."""
    return PatchApplier(base_path=tmp_dir)


def _write_file(tmp_dir, rel_path, content):
    """Write a file in the temp directory."""
    abs_path = Path(tmp_dir) / rel_path
    abs_path.parent.mkdir(parents=True, exist_ok=True)
    abs_path.write_text(content)
    return abs_path


# ── Test: Marker Insert ──

class TestMarkerInsert:
    """Test marker insert mode."""

    def test_insert_after_marker(self, tmp_dir, applier):
        """Code should be inserted after the marker line."""
        _write_file(tmp_dir, "store.ts", (
            "import { create } from 'zustand';\n"
            "// MARKER_SCOUT_1\n"
            "export const useStore = create(() => ({}));\n"
        ))

        result = applier.apply_marker_insert(
            "store.ts", "MARKER_SCOUT_1",
            "export const toggleBookmark = (id: string) => {\n  // toggle logic\n};\n",
            action="INSERT_AFTER"
        )

        assert result.success
        assert result.mode == "marker_insert"
        assert result.lines_added == 3

        content = (Path(tmp_dir) / "store.ts").read_text()
        lines = content.splitlines()
        # Marker should be on line 2 (0-indexed: 1)
        assert "MARKER_SCOUT_1" in lines[1]
        # Inserted code should be on lines 2-4
        assert "toggleBookmark" in lines[2]
        # Original code still present after inserted code
        assert "useStore" in lines[5]

    def test_insert_before_marker(self, tmp_dir, applier):
        """Code should be inserted before the marker line."""
        _write_file(tmp_dir, "store.ts", (
            "const a = 1;\n"
            "// MARKER_SCOUT_2\n"
            "const b = 2;\n"
        ))

        result = applier.apply_marker_insert(
            "store.ts", "MARKER_SCOUT_2",
            "const inserted = true;\n",
            action="INSERT_BEFORE"
        )

        assert result.success
        content = (Path(tmp_dir) / "store.ts").read_text()
        lines = content.splitlines()
        assert "inserted" in lines[1]
        assert "MARKER_SCOUT_2" in lines[2]

    def test_replace_marker_line(self, tmp_dir, applier):
        """Marker line should be replaced with code."""
        _write_file(tmp_dir, "store.ts", (
            "const a = 1;\n"
            "// MARKER_TO_REPLACE\n"
            "const b = 2;\n"
        ))

        result = applier.apply_marker_insert(
            "store.ts", "MARKER_TO_REPLACE",
            "const replaced = true;\n",
            action="REPLACE"
        )

        assert result.success
        assert result.lines_removed == 1
        content = (Path(tmp_dir) / "store.ts").read_text()
        assert "MARKER_TO_REPLACE" not in content
        assert "replaced" in content

    def test_marker_with_line_number(self, tmp_dir, applier):
        """MARKER_SCOUT_1:42 format should use line 42 as fallback."""
        content_lines = [f"line {i}\n" for i in range(1, 51)]
        _write_file(tmp_dir, "file.ts", "".join(content_lines))

        result = applier.apply_marker_insert(
            "file.ts", "MARKER_SCOUT_1:42",
            "inserted code\n",
            action="INSERT_AFTER"
        )

        assert result.success
        content = (Path(tmp_dir) / "file.ts").read_text()
        lines = content.splitlines()
        # Line 42 (0-indexed: 41) is "line 42", inserted after it
        assert lines[41] == "line 42"
        assert lines[42] == "inserted code"

    def test_forced_line_number(self, tmp_dir, applier):
        """Explicit line_number parameter should override marker search."""
        _write_file(tmp_dir, "file.ts", "line 1\nline 2\nline 3\n")

        result = applier.apply_marker_insert(
            "file.ts", "nonexistent_marker",
            "inserted\n",
            action="INSERT_AFTER",
            line_number=2  # Insert after line 2
        )

        assert result.success
        lines = (Path(tmp_dir) / "file.ts").read_text().splitlines()
        assert lines[0] == "line 1"
        assert lines[1] == "line 2"
        assert lines[2] == "inserted"
        assert lines[3] == "line 3"

    def test_missing_marker_fails(self, tmp_dir, applier):
        """Should fail if marker not found and no line number."""
        _write_file(tmp_dir, "file.ts", "line 1\nline 2\n")

        result = applier.apply_marker_insert(
            "file.ts", "NONEXISTENT_MARKER",
            "code\n",
        )

        assert not result.success
        assert "not found" in result.error

    def test_missing_file_fails(self, tmp_dir, applier):
        """Should fail if file doesn't exist."""
        result = applier.apply_marker_insert(
            "nonexistent.ts", "MARKER",
            "code\n",
        )

        assert not result.success
        assert "not found" in result.error

    def test_backup_created(self, tmp_dir, applier):
        """Backup .bak file should be created."""
        _write_file(tmp_dir, "store.ts", "// MARKER\noriginal\n")

        result = applier.apply_marker_insert(
            "store.ts", "MARKER", "new code\n"
        )

        assert result.success
        assert result.backup_path
        assert Path(result.backup_path).exists()
        # Backup should have original content
        backup_content = Path(result.backup_path).read_text()
        assert "original" in backup_content


# ── Test: Unified Diff ──

class TestUnifiedDiff:
    """Test unified diff application."""

    def test_single_hunk_add(self, tmp_dir, applier):
        """Single hunk adding lines should work."""
        _write_file(tmp_dir, "store.ts", (
            "import { create } from 'zustand';\n"
            "\n"
            "export const useStore = create(() => ({\n"
            "  count: 0,\n"
            "}));\n"
        ))

        diff = (
            "--- a/store.ts\n"
            "+++ b/store.ts\n"
            "@@ -3,3 +3,5 @@\n"
            " export const useStore = create(() => ({\n"
            "   count: 0,\n"
            "+  bookmarks: [],\n"
            "+  toggleBookmark: (id) => {},\n"
            " }));\n"
        )

        result = applier.apply_unified_diff("store.ts", diff)

        assert result.success
        assert result.lines_added == 2
        content = (Path(tmp_dir) / "store.ts").read_text()
        assert "bookmarks" in content
        assert "toggleBookmark" in content

    def test_single_hunk_remove(self, tmp_dir, applier):
        """Hunk removing lines should work."""
        _write_file(tmp_dir, "file.ts", (
            "line 1\n"
            "line 2\n"
            "DELETE ME\n"
            "line 4\n"
        ))

        diff = (
            "--- a/file.ts\n"
            "+++ b/file.ts\n"
            "@@ -1,4 +1,3 @@\n"
            " line 1\n"
            " line 2\n"
            "-DELETE ME\n"
            " line 4\n"
        )

        result = applier.apply_unified_diff("file.ts", diff)

        assert result.success
        assert result.lines_removed == 1
        content = (Path(tmp_dir) / "file.ts").read_text()
        assert "DELETE ME" not in content

    def test_empty_diff_fails(self, tmp_dir, applier):
        """Empty diff with no hunks should fail."""
        _write_file(tmp_dir, "file.ts", "content\n")

        result = applier.apply_unified_diff("file.ts", "no hunks here")
        assert not result.success
        assert "No valid hunks" in result.error

    def test_diff_backup_created(self, tmp_dir, applier):
        """Backup should be created before diff application."""
        _write_file(tmp_dir, "file.ts", "original\nline 2\n")

        diff = (
            "--- a/file.ts\n"
            "+++ b/file.ts\n"
            "@@ -1,2 +1,3 @@\n"
            " original\n"
            "+added\n"
            " line 2\n"
        )

        result = applier.apply_unified_diff("file.ts", diff)
        assert result.success
        assert result.backup_path


# ── Test: Create File ──

class TestCreateFile:
    """Test file creation mode."""

    def test_create_new_file(self, tmp_dir, applier):
        """Should create a new file with given content."""
        result = applier.create_file(
            "components/NewComponent.tsx",
            "export const NewComponent = () => <div>Hello</div>;\n"
        )

        assert result.success
        assert result.mode == "create"
        assert (Path(tmp_dir) / "components/NewComponent.tsx").exists()

    def test_create_with_subdirectories(self, tmp_dir, applier):
        """Should create parent directories if needed."""
        result = applier.create_file(
            "deep/nested/path/file.ts",
            "export const x = 1;\n"
        )

        assert result.success
        assert (Path(tmp_dir) / "deep/nested/path/file.ts").exists()


# ── Test: Mode Detection ──

class TestModeDetection:
    """Test auto-detection of output mode."""

    def test_detect_unified_diff(self, tmp_dir, applier):
        """Should detect unified diff format."""
        output = "--- a/file.ts\n+++ b/file.ts\n@@ -1,3 +1,4 @@\n code\n+new\n"
        assert applier.detect_mode(output) == "unified_diff"

    def test_detect_marker_insert(self, tmp_dir, applier):
        """Should detect marker insert JSON format."""
        output = '{"marker": "MARKER_1", "action": "INSERT_AFTER", "code": "new code"}'
        assert applier.detect_mode(output) == "marker_insert"

    def test_detect_create_for_new_file(self, tmp_dir, applier):
        """Should detect create mode when target file doesn't exist."""
        assert applier.detect_mode("function x() {}", target_file="new_file.ts") == "create"

    def test_detect_full_file_default(self, tmp_dir, applier):
        """Should default to full_file when no pattern matches."""
        assert applier.detect_mode("just some code") == "full_file"


# ── Test: Extract Patches ──

class TestExtractPatches:
    """Test patch extraction from coder output."""

    def test_extract_unified_diff(self, tmp_dir, applier):
        """Should extract unified diff from coder output."""
        output = (
            "Here's the change:\n"
            "--- a/store.ts\n"
            "+++ b/store.ts\n"
            "@@ -1,3 +1,4 @@\n"
            " import x\n"
            "+import y\n"
            " export\n"
            "\nDone!"
        )

        patches = applier.extract_patches(output)
        assert len(patches) >= 1
        assert patches[0]["mode"] == "unified_diff"
        assert patches[0]["file_path"] == "store.ts"

    def test_extract_marker_insert_json(self, tmp_dir, applier):
        """Should extract marker insert JSON from coder output."""
        output = (
            'I will insert the code:\n'
            '{"marker": "MARKER_SCOUT_1", "action": "INSERT_AFTER", '
            '"code": "const x = 1;", "file": "store.ts"}\n'
            'That should work.'
        )

        patches = applier.extract_patches(output)
        assert len(patches) >= 1
        assert patches[0]["mode"] == "marker_insert"
        assert patches[0]["marker_id"] == "MARKER_SCOUT_1"


# ── Test: Diff Parser ──

class TestDiffParser:
    """Test unified diff parsing."""

    def test_parse_single_hunk(self, tmp_dir, applier):
        """Should parse a single hunk correctly."""
        diff = (
            "--- a/file.ts\n"
            "+++ b/file.ts\n"
            "@@ -1,3 +1,4 @@\n"
            " line 1\n"
            "+added\n"
            " line 2\n"
            " line 3\n"
        )

        hunks = applier._parse_unified_diff(diff)
        assert len(hunks) == 1
        assert hunks[0]["old_start"] == 1
        assert hunks[0]["old_count"] == 3
        assert hunks[0]["new_count"] == 4

        # Check changes
        changes = hunks[0]["changes"]
        ops = [op for op, _ in changes]
        assert "+" in ops
        assert " " in ops

    def test_parse_multiple_hunks(self, tmp_dir, applier):
        """Should parse multiple hunks."""
        diff = (
            "--- a/file.ts\n"
            "+++ b/file.ts\n"
            "@@ -1,2 +1,3 @@\n"
            " line 1\n"
            "+added 1\n"
            " line 2\n"
            "@@ -10,2 +11,3 @@\n"
            " line 10\n"
            "+added 2\n"
            " line 11\n"
        )

        hunks = applier._parse_unified_diff(diff)
        assert len(hunks) == 2
        assert hunks[0]["old_start"] == 1
        assert hunks[1]["old_start"] == 10
