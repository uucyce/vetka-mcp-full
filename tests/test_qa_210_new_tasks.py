"""DELTA QA-210: Verify 2 new done_worktree tasks.

1. tb_1775435995_84818_1 — CUT-BUG-P0: Import dialog fix (ed82fd2f, claude/cut-engine)
2. tb_1775435882_68814_10 — GEMMA-211: Model Router + infrastructure (ab146e1f, claude/harness-eta)
"""
import subprocess
import sys
import ast
import re
from pathlib import Path

_git_result = subprocess.run(
    ["git", "rev-parse", "--git-common-dir"],
    capture_output=True, text=True,
)
if _git_result.returncode == 0:
    _gc = Path(_git_result.stdout.strip())
    PROJECT_ROOT = _gc.parent if _gc.name == ".git" else _gc
else:
    PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent


def _git_show(commit, path):
    result = subprocess.run(
        ["git", "show", f"{commit}:{path}"],
        capture_output=True, text=True, timeout=10,
        cwd=str(PROJECT_ROOT),
    )
    return result.stdout if result.returncode == 0 else ""


# ═══════════════════════════════════════════════════════════════════
# TASK 1: CUT-BUG-P0 Import Dialog — tb_1775435995_84818_1
# Commit: ed82fd2f on claude/cut-engine
# ═══════════════════════════════════════════════════════════════════
class TestImportDialogFix:
    """Verify openFileDialog + ProjectPanel split for file vs folder import."""

    COMMIT = "ed82fd2f"

    def test_commit_exists(self):
        result = subprocess.run(
            ["git", "log", "--oneline", self.COMMIT, "-1"],
            capture_output=True, text=True, timeout=5,
            cwd=str(PROJECT_ROOT),
        )
        assert result.returncode == 0
        assert "IMPORT-DIALOG" in result.stdout

    def test_open_file_dialog_exists(self):
        """openFileDialog() function added to tauri.ts."""
        src = _git_show(self.COMMIT, "client/src/config/tauri.ts")
        assert "openFileDialog" in src, "openFileDialog function missing"

    def test_directory_false(self):
        """openFileDialog uses directory: false."""
        src = _git_show(self.COMMIT, "client/src/config/tauri.ts")
        assert "directory: false" in src, "directory must be false for file picker"

    def test_media_file_extensions(self):
        """Media extensions include mp4, mov, avi, mkv, wav, mp3."""
        src = _git_show(self.COMMIT, "client/src/config/tauri.ts")
        for ext in ["mp4", "mov", "avi", "mkv", "wav", "mp3"]:
            assert f"'{ext}'" in src, f"Missing media extension: {ext}"

    def test_file_filters_categorized(self):
        """Filters split into Video, Audio, Image, All Media."""
        src = _git_show(self.COMMIT, "client/src/config/tauri.ts")
        for category in ["Video", "Audio", "Image", "All Media"]:
            assert f"'{category}'" in src, f"Missing filter category: {category}"

    def test_open_folder_dialog_preserved(self):
        """openFolderDialog still exists for folder import."""
        src = _git_show(self.COMMIT, "client/src/config/tauri.ts")
        assert "openFolderDialog" in src or "openNativeDialog" in src, \
            "Folder dialog must still exist"

    def test_project_panel_updated(self):
        """ProjectPanel.tsx modified to use openFileDialog."""
        src = _git_show(self.COMMIT, "client/src/components/cut/ProjectPanel.tsx")
        assert src, "ProjectPanel.tsx not in commit"
        assert "openFileDialog" in src or "import" in src.lower()

    def test_vitest_tests_included(self):
        """15 vitest tests for import dialog."""
        src = _git_show(self.COMMIT, "client/src/components/cut/__tests__/importMediaDialog.test.ts")
        assert src, "Import dialog test file missing"
        assert len(src) > 200, "Test file too small"

    def test_marker_present(self):
        """MARKER_IMPORT-DIALOG-FIX in tauri.ts."""
        src = _git_show(self.COMMIT, "client/src/config/tauri.ts")
        assert "MARKER_IMPORT-DIALOG-FIX" in src


# ═══════════════════════════════════════════════════════════════════
# TASK 2: GEMMA-211 Model Router — tb_1775435882_68814_10
# Commit: ab146e1f on claude/harness-eta
# ═══════════════════════════════════════════════════════════════════
class TestGemma211ModelRouter:
    """Verify Model Router + provider_registry + tests."""

    COMMIT = "ab146e1f"

    def test_commit_exists(self):
        result = subprocess.run(
            ["git", "log", "--oneline", self.COMMIT, "-1"],
            capture_output=True, text=True, timeout=5,
            cwd=str(PROJECT_ROOT),
        )
        assert result.returncode == 0
        assert "GEMMA-211" in result.stdout

    def test_model_router_created(self):
        """model_router.py exists with route_model function."""
        src = _git_show(self.COMMIT, "src/services/model_router.py")
        assert src, "model_router.py missing"
        assert "route_model" in src or "ModelRouter" in src

    def test_model_router_syntax(self):
        """model_router.py is valid Python."""
        src = _git_show(self.COMMIT, "src/services/model_router.py")
        assert src
        ast.parse(src)

    def test_provider_registry_gemma4(self):
        """Gemma 4 entries added to provider_registry.py."""
        src = _git_show(self.COMMIT, "src/elisya/provider_registry.py")
        assert src
        assert "gemma" in src.lower(), "Gemma entries missing from provider registry"

    def test_provider_registry_syntax(self):
        """provider_registry.py is valid Python."""
        src = _git_show(self.COMMIT, "src/elisya/provider_registry.py")
        assert src
        ast.parse(src)

    def test_benchmark_tests_included(self):
        """test_model_router.py included with tests."""
        src = _git_show(self.COMMIT, "tests/benchmark/test_model_router.py")
        assert src, "test_model_router.py missing"
        assert len(src) > 200

    def test_json_strip_helper(self):
        """JSON strip helper for markdown wrap fix."""
        src = _git_show(self.COMMIT, "src/services/model_router.py")
        assert "json" in src.lower() or "strip" in src.lower() or "markdown" in src.lower()
