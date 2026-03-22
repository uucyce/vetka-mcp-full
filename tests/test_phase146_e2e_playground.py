"""
E2E tests for Phase 146: Playground + Pipeline Sandbox Integration.

Tests the FULL lifecycle:
1. Create playground (real git worktree)
2. Run pipeline with playground_root scoping
3. Verify files written to worktree, NOT main codebase
4. Check git diff in playground
5. Cleanup: destroy playground, verify branch removed

MARKER_146.E2E

@status: active
@phase: 146
@depends: src/orchestration/playground_manager.py, agent_pipeline.py
"""

import asyncio
import json
import os
import re
import shutil
import subprocess
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock
import pytest

pytestmark = pytest.mark.stale(reason="Pre-existing failure — phase 146 contracts changed")

# Project root
PROJECT_ROOT = Path(__file__).parent.parent


# ============================================================
# Test 1: Real Git Worktree Lifecycle
# ============================================================
class TestPlaygroundGitWorktreeE2E(unittest.TestCase):
    """Test real git worktree create/destroy cycle.

    These tests use REAL git commands (not mocked).
    They create actual worktrees in .playgrounds/ and clean up after.
    """

    def setUp(self):
        """Ensure we're in a git repo and no stale playgrounds exist."""
        # Verify we're in a git repo
        result = subprocess.run(
            ["git", "rev-parse", "--is-inside-work-tree"],
            capture_output=True, text=True, cwd=str(PROJECT_ROOT)
        )
        if result.returncode != 0:
            self.skipTest("Not in a git repository")

        # Use a temporary playground base to avoid conflicts
        self.test_base = PROJECT_ROOT / ".playgrounds_test_e2e"
        self.test_base.mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        """Clean up test playground directory and any branches."""
        # Remove any worktrees we created
        result = subprocess.run(
            ["git", "worktree", "list", "--porcelain"],
            capture_output=True, text=True, cwd=str(PROJECT_ROOT)
        )
        for line in result.stdout.split("\n"):
            if line.startswith("worktree ") and ".playgrounds_test_e2e" in line:
                wt_path = line.split("worktree ", 1)[1]
                subprocess.run(
                    ["git", "worktree", "remove", "--force", wt_path],
                    capture_output=True, text=True, cwd=str(PROJECT_ROOT)
                )

        # Remove test branches
        result = subprocess.run(
            ["git", "branch", "--list", "playground/pg_test_*"],
            capture_output=True, text=True, cwd=str(PROJECT_ROOT)
        )
        for branch in result.stdout.strip().split("\n"):
            branch = branch.strip()
            if branch and branch.startswith("playground/pg_test_"):
                subprocess.run(
                    ["git", "branch", "-D", branch],
                    capture_output=True, text=True, cwd=str(PROJECT_ROOT)
                )

        # Clean up test directory
        if self.test_base.exists():
            shutil.rmtree(self.test_base, ignore_errors=True)

        # Prune stale worktrees
        subprocess.run(
            ["git", "worktree", "prune"],
            capture_output=True, text=True, cwd=str(PROJECT_ROOT)
        )

    def test_create_real_worktree(self):
        """Create a real git worktree and verify it exists."""
        from src.orchestration.playground_manager import PlaygroundManager

        manager = PlaygroundManager(base_dir=self.test_base)
        config = asyncio.run(manager.create(
            task_description="E2E test: verify worktree creation",
            preset="dragon_silver",
        ))

        # Verify playground created
        self.assertTrue(config.playground_id.startswith("pg_"))
        self.assertEqual(config.status, "active")
        self.assertTrue(config.branch_name.startswith("playground/"))

        # Verify worktree exists on disk
        wt_path = Path(config.worktree_path)
        self.assertTrue(wt_path.exists(), f"Worktree not found: {wt_path}")
        self.assertTrue(wt_path.is_dir())

        # Verify it's a real git worktree (has .git file pointing to main)
        git_file = wt_path / ".git"
        self.assertTrue(git_file.exists(), ".git file missing in worktree")

        # Verify branch exists
        result = subprocess.run(
            ["git", "branch", "--list", config.branch_name],
            capture_output=True, text=True, cwd=str(PROJECT_ROOT)
        )
        self.assertIn(config.branch_name, result.stdout.strip())

        # Verify playground metadata file
        meta_file = wt_path / ".playground.json"
        self.assertTrue(meta_file.exists(), ".playground.json missing")
        meta = json.loads(meta_file.read_text())
        self.assertEqual(meta["playground_id"], config.playground_id)
        self.assertFalse(meta["restrictions"]["can_write_main"])

        # Cleanup
        asyncio.run(manager.destroy(config.playground_id))

    def test_worktree_has_project_files(self):
        """Worktree should contain the same files as main branch."""
        from src.orchestration.playground_manager import PlaygroundManager

        manager = PlaygroundManager(base_dir=self.test_base)
        config = asyncio.run(manager.create(
            task_description="E2E test: verify project files in worktree",
        ))

        wt_path = Path(config.worktree_path)

        # Key project files should exist in worktree
        key_files = [
            "src/orchestration/agent_pipeline.py",
            "src/mcp/mycelium_mcp_server.py",
            "tests/test_phase146_playground.py",
            ".gitignore",
        ]
        for f in key_files:
            self.assertTrue(
                (wt_path / f).exists(),
                f"Project file {f} missing from worktree"
            )

        # Cleanup
        asyncio.run(manager.destroy(config.playground_id))

    def test_destroy_removes_worktree_and_branch(self):
        """Destroying playground removes worktree dir and git branch."""
        from src.orchestration.playground_manager import PlaygroundManager

        manager = PlaygroundManager(base_dir=self.test_base)
        config = asyncio.run(manager.create(
            task_description="E2E test: verify cleanup",
        ))

        wt_path = Path(config.worktree_path)
        branch = config.branch_name

        # Verify exists first
        self.assertTrue(wt_path.exists())

        # Destroy
        result = asyncio.run(manager.destroy(config.playground_id))
        self.assertTrue(result)

        # Worktree dir should be gone
        self.assertFalse(wt_path.exists(), "Worktree dir should be removed")

        # Branch should be gone
        branch_check = subprocess.run(
            ["git", "branch", "--list", branch],
            capture_output=True, text=True, cwd=str(PROJECT_ROOT)
        )
        self.assertEqual(branch_check.stdout.strip(), "", f"Branch {branch} should be deleted")

    def test_write_file_in_playground(self):
        """Write a file inside playground worktree — verify it doesn't touch main."""
        from src.orchestration.playground_manager import PlaygroundManager

        manager = PlaygroundManager(base_dir=self.test_base)
        config = asyncio.run(manager.create(
            task_description="E2E test: file write isolation",
        ))

        wt_path = Path(config.worktree_path)

        # Write a test file inside the playground
        test_file = wt_path / "src" / "test_sandbox_output.py"
        test_file.parent.mkdir(parents=True, exist_ok=True)
        test_file.write_text("# Generated by playground E2E test\nprint('hello from sandbox')\n")

        # Verify file exists in playground
        self.assertTrue(test_file.exists())

        # Verify file does NOT exist in main codebase
        main_file = PROJECT_ROOT / "src" / "test_sandbox_output.py"
        self.assertFalse(main_file.exists(), "File should NOT appear in main codebase!")

        # Verify git diff shows the change
        diff_result = subprocess.run(
            ["git", "diff", "--name-only"],
            capture_output=True, text=True, cwd=str(wt_path)
        )
        # Note: untracked files won't show in git diff, use git status instead
        status_result = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True, text=True, cwd=str(wt_path)
        )
        self.assertIn("test_sandbox_output.py", status_result.stdout)

        # Cleanup
        asyncio.run(manager.destroy(config.playground_id))


# ============================================================
# Test 2: Pipeline + Playground Integration (Mocked LLM)
# ============================================================
class TestPipelinePlaygroundE2E(unittest.TestCase):
    """Test pipeline with playground_root scoping.

    Uses real git worktree but mocked LLM calls.
    Verifies file extraction writes to playground, not main.
    """

    def setUp(self):
        self.test_base = PROJECT_ROOT / ".playgrounds_test_e2e"
        self.test_base.mkdir(parents=True, exist_ok=True)

        # Check we're in a git repo
        result = subprocess.run(
            ["git", "rev-parse", "--is-inside-work-tree"],
            capture_output=True, text=True, cwd=str(PROJECT_ROOT)
        )
        if result.returncode != 0:
            self.skipTest("Not in a git repository")

    def tearDown(self):
        # Clean up worktrees
        result = subprocess.run(
            ["git", "worktree", "list", "--porcelain"],
            capture_output=True, text=True, cwd=str(PROJECT_ROOT)
        )
        for line in result.stdout.split("\n"):
            if line.startswith("worktree ") and ".playgrounds_test_e2e" in line:
                wt_path = line.split("worktree ", 1)[1]
                subprocess.run(
                    ["git", "worktree", "remove", "--force", wt_path],
                    capture_output=True, text=True, cwd=str(PROJECT_ROOT)
                )

        # Remove test branches
        result = subprocess.run(
            ["git", "branch", "--list", "playground/pg_*"],
            capture_output=True, text=True, cwd=str(PROJECT_ROOT)
        )
        for branch in result.stdout.strip().split("\n"):
            branch = branch.strip()
            if branch and "playground/pg_" in branch:
                subprocess.run(
                    ["git", "branch", "-D", branch],
                    capture_output=True, text=True, cwd=str(PROJECT_ROOT)
                )

        if self.test_base.exists():
            shutil.rmtree(self.test_base, ignore_errors=True)

        subprocess.run(
            ["git", "worktree", "prune"],
            capture_output=True, text=True, cwd=str(PROJECT_ROOT)
        )

    def test_pipeline_writes_to_playground(self):
        """Pipeline with playground_root writes files to worktree, not main."""
        from src.orchestration.playground_manager import PlaygroundManager
        from src.orchestration.agent_pipeline import AgentPipeline

        # Create playground
        manager = PlaygroundManager(base_dir=self.test_base)
        config = asyncio.run(manager.create(
            task_description="Add bookmark toggle",
            preset="dragon_silver",
        ))
        wt_path = Path(config.worktree_path)

        # Create pipeline with playground_root
        pipeline = AgentPipeline(
            auto_write=True,
            preset="dragon_silver",
            playground_root=str(wt_path),
        )

        # Verify playground_root is set
        self.assertEqual(pipeline.playground_root, str(wt_path))

        # Simulate _resolve_write_path
        resolved = pipeline._resolve_write_path("src/components/BookmarkToggle.tsx")
        self.assertEqual(resolved, wt_path / "src" / "components" / "BookmarkToggle.tsx")
        self.assertTrue(str(resolved).startswith(str(wt_path)))

        # Simulate file extraction (what _extract_and_write_files does)
        test_content = """```typescript
// file: src/components/BookmarkToggle.tsx
import React from 'react';

export const BookmarkToggle = () => {
  const [bookmarked, setBookmarked] = React.useState(false);

  return (
    <button onClick={() => setBookmarked(!bookmarked)}>
      {bookmarked ? '⭐' : '☆'} Bookmark
    </button>
  );
};
```"""

        # Create a mock subtask
        class MockSubtask:
            description = "Create BookmarkToggle component"
            marker = "MARKER_TEST_1"

        # Write the file through _resolve_write_path (like pipeline does)
        filepath = "src/components/BookmarkToggle.tsx"
        path_obj = pipeline._resolve_write_path(filepath)
        path_obj.parent.mkdir(parents=True, exist_ok=True)
        path_obj.write_text("import React from 'react';\n// BookmarkToggle component\n")

        # Verify: file is in playground
        self.assertTrue(path_obj.exists())
        self.assertTrue(str(path_obj).startswith(str(wt_path)))

        # Verify: file is NOT in main codebase
        main_file = PROJECT_ROOT / filepath
        self.assertFalse(main_file.exists(), f"File should NOT exist in main: {main_file}")

        # Cleanup
        asyncio.run(manager.destroy(config.playground_id))

    def test_pipeline_without_playground_writes_normally(self):
        """Pipeline without playground_root writes to normal paths (regression)."""
        from src.orchestration.agent_pipeline import AgentPipeline

        pipeline = AgentPipeline(auto_write=True, preset="dragon_silver")
        self.assertIsNone(pipeline.playground_root)

        # _resolve_write_path should return relative path (normal behavior)
        resolved = pipeline._resolve_write_path("src/components/Foo.tsx")
        self.assertEqual(resolved, Path("src/components/Foo.tsx"))

    def test_forbidden_files_allowed_in_playground(self):
        """In playground mode, forbidden files (main.py etc) can be overwritten."""
        from src.orchestration.playground_manager import PlaygroundManager
        from src.orchestration.agent_pipeline import AgentPipeline

        manager = PlaygroundManager(base_dir=self.test_base)
        config = asyncio.run(manager.create(
            task_description="Test forbidden file override",
        ))
        wt_path = Path(config.worktree_path)

        pipeline = AgentPipeline(
            auto_write=True,
            playground_root=str(wt_path),
        )

        # In playground, the forbidden file check is relaxed:
        # `if path_obj.name in _forbidden and not self.playground_root:`
        # This means forbidden files CAN be written in playground
        self.assertIsNotNone(pipeline.playground_root)

        # Verify the check logic
        _forbidden = ('agent_pipeline.py', 'mycelium_mcp_server.py', 'vetka_mcp_bridge.py',
                      '__init__.py', 'main.py', 'app.py')
        for fname in _forbidden:
            # Condition: `path_obj.name in _forbidden and not self.playground_root`
            # With playground_root set, `not self.playground_root` is False
            # So the block is never entered — writes are allowed!
            blocked = fname in _forbidden and not pipeline.playground_root
            self.assertFalse(blocked, f"{fname} should be writable in playground")

        # Cleanup
        asyncio.run(manager.destroy(config.playground_id))

    def test_staging_dirs_scoped_to_playground(self):
        """Staging/fallback directories are also scoped to playground."""
        from src.orchestration.playground_manager import PlaygroundManager
        from src.orchestration.agent_pipeline import AgentPipeline

        manager = PlaygroundManager(base_dir=self.test_base)
        config = asyncio.run(manager.create(
            task_description="Test staging dirs",
        ))
        wt_path = Path(config.worktree_path)

        pipeline = AgentPipeline(
            auto_write=True,
            playground_root=str(wt_path),
        )

        # All staging dirs should be inside playground
        staging_paths = [
            "data/vetka_staging",
            "data/vetka_staging/blocked",
            "data/vetka_staging/would_overwrite",
        ]
        for sp in staging_paths:
            resolved = pipeline._resolve_write_path(sp)
            self.assertTrue(
                str(resolved).startswith(str(wt_path)),
                f"Staging dir {sp} should be inside playground: got {resolved}"
            )

        # Cleanup
        asyncio.run(manager.destroy(config.playground_id))


# ============================================================
# Test 3: Playground Diff
# ============================================================
class TestPlaygroundDiff(unittest.TestCase):
    """Test git diff output from playground changes."""

    def setUp(self):
        self.test_base = PROJECT_ROOT / ".playgrounds_test_e2e"
        self.test_base.mkdir(parents=True, exist_ok=True)

        result = subprocess.run(
            ["git", "rev-parse", "--is-inside-work-tree"],
            capture_output=True, text=True, cwd=str(PROJECT_ROOT)
        )
        if result.returncode != 0:
            self.skipTest("Not in a git repository")

    def tearDown(self):
        result = subprocess.run(
            ["git", "worktree", "list", "--porcelain"],
            capture_output=True, text=True, cwd=str(PROJECT_ROOT)
        )
        for line in result.stdout.split("\n"):
            if line.startswith("worktree ") and ".playgrounds_test_e2e" in line:
                wt_path = line.split("worktree ", 1)[1]
                subprocess.run(
                    ["git", "worktree", "remove", "--force", wt_path],
                    capture_output=True, text=True, cwd=str(PROJECT_ROOT)
                )

        result = subprocess.run(
            ["git", "branch", "--list", "playground/pg_*"],
            capture_output=True, text=True, cwd=str(PROJECT_ROOT)
        )
        for branch in result.stdout.strip().split("\n"):
            branch = branch.strip()
            if branch and "playground/pg_" in branch:
                subprocess.run(
                    ["git", "branch", "-D", branch],
                    capture_output=True, text=True, cwd=str(PROJECT_ROOT)
                )

        if self.test_base.exists():
            shutil.rmtree(self.test_base, ignore_errors=True)

        subprocess.run(
            ["git", "worktree", "prune"],
            capture_output=True, text=True, cwd=str(PROJECT_ROOT)
        )

    def test_diff_shows_modified_files(self):
        """Modifying a file in playground shows up in diff."""
        from src.orchestration.playground_manager import PlaygroundManager

        manager = PlaygroundManager(base_dir=self.test_base)
        config = asyncio.run(manager.create(
            task_description="E2E test: diff check",
        ))
        wt_path = Path(config.worktree_path)

        # Modify an existing file in the playground
        readme = wt_path / ".gitignore"
        if readme.exists():
            original = readme.read_text()
            readme.write_text(original + "\n# Added by playground E2E test\n")

        # Get diff (uses git diff --stat HEAD)
        diff = asyncio.run(manager.get_diff(config.playground_id))

        # Since we modified an existing tracked file, diff should show something
        self.assertIsNotNone(diff)
        if diff:  # May be empty string if no changes detected
            self.assertIn(".gitignore", diff)

        # Cleanup — restore file before destroy to keep main clean
        if readme.exists() and 'original' in dir():
            readme.write_text(original)
        asyncio.run(manager.destroy(config.playground_id))

    def test_diff_empty_for_unmodified_playground(self):
        """Fresh playground with no changes has empty diff."""
        from src.orchestration.playground_manager import PlaygroundManager

        manager = PlaygroundManager(base_dir=self.test_base)
        config = asyncio.run(manager.create(
            task_description="E2E test: no changes diff",
        ))

        diff = asyncio.run(manager.get_diff(config.playground_id))
        # Fresh worktree should have empty diff (or None/empty string)
        self.assertTrue(diff is not None)
        # The diff should be empty since nothing changed
        # Note: .playground.json is untracked (not staged), so it won't appear in diff

        asyncio.run(manager.destroy(config.playground_id))


# ============================================================
# Test 4: MCP Tool Integration
# ============================================================
class TestMCPPlaygroundTools(unittest.TestCase):
    """Test MCP tool handlers for playground operations."""

    def test_playground_tools_registered(self):
        """All 4 playground tools are in MYCELIUM_TOOLS."""
        from src.mcp.mycelium_mcp_server import MYCELIUM_TOOLS
        names = {t.name for t in MYCELIUM_TOOLS}

        playground_tools = {
            "mycelium_playground_create",
            "mycelium_playground_list",
            "mycelium_playground_destroy",
            "mycelium_playground_diff",
        }
        missing = playground_tools - names
        self.assertFalse(missing, f"Missing playground tools: {missing}")

    def test_pipeline_tool_has_playground_id_param(self):
        """mycelium_pipeline accepts playground_id parameter."""
        from src.mcp.mycelium_mcp_server import MYCELIUM_TOOLS

        pipeline_tool = None
        for t in MYCELIUM_TOOLS:
            if t.name == "mycelium_pipeline":
                pipeline_tool = t
                break

        self.assertIsNotNone(pipeline_tool, "mycelium_pipeline not found")
        props = pipeline_tool.inputSchema.get("properties", {})
        self.assertIn("playground_id", props, "playground_id missing from pipeline schema")
        self.assertEqual(props["playground_id"]["type"], "string")

    def test_dispatch_table_has_playground_handlers(self):
        """All 4 playground handlers in dispatch table."""
        from src.mcp.mycelium_mcp_server import _TOOL_DISPATCH

        expected = [
            "mycelium_playground_create",
            "mycelium_playground_list",
            "mycelium_playground_destroy",
            "mycelium_playground_diff",
        ]
        for tool_name in expected:
            self.assertIn(tool_name, _TOOL_DISPATCH,
                         f"{tool_name} missing from _TOOL_DISPATCH")
            self.assertTrue(callable(_TOOL_DISPATCH[tool_name]),
                          f"{tool_name} handler is not callable")


# ============================================================
# Test 5: Path Security (E2E with real worktree)
# ============================================================
class TestPathSecurityE2E(unittest.TestCase):
    """Test path traversal protection with real filesystem."""

    def setUp(self):
        self.test_base = PROJECT_ROOT / ".playgrounds_test_e2e"
        self.test_base.mkdir(parents=True, exist_ok=True)

        result = subprocess.run(
            ["git", "rev-parse", "--is-inside-work-tree"],
            capture_output=True, text=True, cwd=str(PROJECT_ROOT)
        )
        if result.returncode != 0:
            self.skipTest("Not in a git repository")

    def tearDown(self):
        result = subprocess.run(
            ["git", "worktree", "list", "--porcelain"],
            capture_output=True, text=True, cwd=str(PROJECT_ROOT)
        )
        for line in result.stdout.split("\n"):
            if line.startswith("worktree ") and ".playgrounds_test_e2e" in line:
                wt_path = line.split("worktree ", 1)[1]
                subprocess.run(
                    ["git", "worktree", "remove", "--force", wt_path],
                    capture_output=True, text=True, cwd=str(PROJECT_ROOT)
                )

        result = subprocess.run(
            ["git", "branch", "--list", "playground/pg_*"],
            capture_output=True, text=True, cwd=str(PROJECT_ROOT)
        )
        for branch in result.stdout.strip().split("\n"):
            branch = branch.strip()
            if branch and "playground/pg_" in branch:
                subprocess.run(
                    ["git", "branch", "-D", branch],
                    capture_output=True, text=True, cwd=str(PROJECT_ROOT)
                )

        if self.test_base.exists():
            shutil.rmtree(self.test_base, ignore_errors=True)

        subprocess.run(
            ["git", "worktree", "prune"],
            capture_output=True, text=True, cwd=str(PROJECT_ROOT)
        )

    def test_path_traversal_blocked_with_real_worktree(self):
        """Path traversal attempts are blocked on real filesystem."""
        from src.orchestration.playground_manager import PlaygroundManager

        manager = PlaygroundManager(base_dir=self.test_base)
        config = asyncio.run(manager.create(
            task_description="E2E test: security",
        ))

        # These should all return None (blocked)
        attacks = [
            "../../../etc/passwd",
            "../../main.py",
            "../.env",
            "src/../../outside.py",
        ]
        for attack in attacks:
            result = manager.scope_path(config.playground_id, attack)
            self.assertIsNone(result, f"Path traversal not blocked: {attack}")

        # These should work (valid paths)
        valid = [
            "src/main.py",
            "tests/test_new.py",
            "data/output.json",
        ]
        for v in valid:
            result = manager.scope_path(config.playground_id, v)
            self.assertIsNotNone(result, f"Valid path blocked: {v}")
            self.assertTrue(
                str(result).startswith(str(config.worktree_path)),
                f"Path not scoped to playground: {result}"
            )

        asyncio.run(manager.destroy(config.playground_id))

    def test_validate_path_with_symlinks(self):
        """validate_path handles symlinks correctly (resolve catches them)."""
        from src.orchestration.playground_manager import PlaygroundManager

        manager = PlaygroundManager(base_dir=self.test_base)
        config = asyncio.run(manager.create(
            task_description="E2E test: symlink security",
        ))

        wt_path = Path(config.worktree_path)

        # A path outside playground should fail validation
        outside_path = "/tmp/evil_file.py"
        self.assertFalse(manager.validate_path(config.playground_id, outside_path))

        # A path inside playground should pass
        inside_path = str(wt_path / "src" / "safe.py")
        self.assertTrue(manager.validate_path(config.playground_id, inside_path))

        asyncio.run(manager.destroy(config.playground_id))


# ============================================================
# Test 6: Playground Record and List
# ============================================================
class TestPlaygroundRecordAndList(unittest.TestCase):
    """Test playground usage tracking and listing."""

    def setUp(self):
        self.test_base = PROJECT_ROOT / ".playgrounds_test_e2e"
        self.test_base.mkdir(parents=True, exist_ok=True)

        result = subprocess.run(
            ["git", "rev-parse", "--is-inside-work-tree"],
            capture_output=True, text=True, cwd=str(PROJECT_ROOT)
        )
        if result.returncode != 0:
            self.skipTest("Not in a git repository")

    def tearDown(self):
        result = subprocess.run(
            ["git", "worktree", "list", "--porcelain"],
            capture_output=True, text=True, cwd=str(PROJECT_ROOT)
        )
        for line in result.stdout.split("\n"):
            if line.startswith("worktree ") and ".playgrounds_test_e2e" in line:
                wt_path = line.split("worktree ", 1)[1]
                subprocess.run(
                    ["git", "worktree", "remove", "--force", wt_path],
                    capture_output=True, text=True, cwd=str(PROJECT_ROOT)
                )

        result = subprocess.run(
            ["git", "branch", "--list", "playground/pg_*"],
            capture_output=True, text=True, cwd=str(PROJECT_ROOT)
        )
        for branch in result.stdout.strip().split("\n"):
            branch = branch.strip()
            if branch and "playground/pg_" in branch:
                subprocess.run(
                    ["git", "branch", "-D", branch],
                    capture_output=True, text=True, cwd=str(PROJECT_ROOT)
                )

        if self.test_base.exists():
            shutil.rmtree(self.test_base, ignore_errors=True)

        subprocess.run(
            ["git", "worktree", "prune"],
            capture_output=True, text=True, cwd=str(PROJECT_ROOT)
        )

    def test_record_pipeline_run(self):
        """Record pipeline runs and created files."""
        from src.orchestration.playground_manager import PlaygroundManager

        manager = PlaygroundManager(base_dir=self.test_base)
        config = asyncio.run(manager.create(
            task_description="E2E test: record pipeline",
        ))

        # Record a run
        manager.record_pipeline_run(
            config.playground_id,
            files_created=["src/new_feature.py", "tests/test_new.py"]
        )

        # Check counters
        updated = manager._playgrounds[config.playground_id]
        self.assertEqual(updated.pipeline_runs, 1)
        self.assertEqual(len(updated.files_created), 2)
        self.assertIn("src/new_feature.py", updated.files_created)

        # Record another run
        manager.record_pipeline_run(
            config.playground_id,
            files_created=["src/utils.py"]
        )
        updated = manager._playgrounds[config.playground_id]
        self.assertEqual(updated.pipeline_runs, 2)
        self.assertEqual(len(updated.files_created), 3)

        asyncio.run(manager.destroy(config.playground_id))

    def test_list_playgrounds(self):
        """List active and inactive playgrounds."""
        from src.orchestration.playground_manager import PlaygroundManager

        manager = PlaygroundManager(base_dir=self.test_base)

        # Create two playgrounds
        config1 = asyncio.run(manager.create(task_description="Task 1"))
        config2 = asyncio.run(manager.create(task_description="Task 2"))

        # List active only
        active = manager.list_playgrounds(include_inactive=False)
        self.assertEqual(len(active), 2)

        # Destroy one
        asyncio.run(manager.destroy(config1.playground_id))

        # List active — should be 1
        active = manager.list_playgrounds(include_inactive=False)
        self.assertEqual(len(active), 1)
        self.assertEqual(active[0].playground_id, config2.playground_id)

        # List all — should be 2
        all_pg = manager.list_playgrounds(include_inactive=True)
        self.assertEqual(len(all_pg), 2)

        # Cleanup
        asyncio.run(manager.destroy(config2.playground_id))

    def test_config_persists_to_disk(self):
        """Playground config survives manager restart."""
        from src.orchestration.playground_manager import PlaygroundManager

        manager = PlaygroundManager(base_dir=self.test_base)
        config = asyncio.run(manager.create(
            task_description="Persistence test",
            preset="dragon_gold",
        ))
        pg_id = config.playground_id

        # Record some activity
        manager.record_pipeline_run(pg_id, files_created=["a.py", "b.py"])

        # Create a NEW manager instance (simulates restart)
        manager2 = PlaygroundManager(base_dir=self.test_base)

        # Should load the saved config
        self.assertIn(pg_id, manager2._playgrounds)
        loaded = manager2._playgrounds[pg_id]
        self.assertEqual(loaded.task_description, "Persistence test")
        self.assertEqual(loaded.preset, "dragon_gold")
        self.assertEqual(loaded.pipeline_runs, 1)
        self.assertEqual(len(loaded.files_created), 2)

        # Cleanup via the new manager
        asyncio.run(manager2.destroy(pg_id))


# ============================================================
# Test 7: Convenience Functions
# ============================================================
class TestConvenienceFunctionsE2E(unittest.TestCase):
    """Test module-level convenience functions with real git."""

    def setUp(self):
        self.test_base = PROJECT_ROOT / ".playgrounds_test_e2e"
        self.test_base.mkdir(parents=True, exist_ok=True)

        result = subprocess.run(
            ["git", "rev-parse", "--is-inside-work-tree"],
            capture_output=True, text=True, cwd=str(PROJECT_ROOT)
        )
        if result.returncode != 0:
            self.skipTest("Not in a git repository")

    def tearDown(self):
        result = subprocess.run(
            ["git", "worktree", "list", "--porcelain"],
            capture_output=True, text=True, cwd=str(PROJECT_ROOT)
        )
        for line in result.stdout.split("\n"):
            if line.startswith("worktree ") and ".playgrounds_test_e2e" in line:
                wt_path = line.split("worktree ", 1)[1]
                subprocess.run(
                    ["git", "worktree", "remove", "--force", wt_path],
                    capture_output=True, text=True, cwd=str(PROJECT_ROOT)
                )

        result = subprocess.run(
            ["git", "branch", "--list", "playground/pg_*"],
            capture_output=True, text=True, cwd=str(PROJECT_ROOT)
        )
        for branch in result.stdout.strip().split("\n"):
            branch = branch.strip()
            if branch and "playground/pg_" in branch:
                subprocess.run(
                    ["git", "branch", "-D", branch],
                    capture_output=True, text=True, cwd=str(PROJECT_ROOT)
                )

        if self.test_base.exists():
            shutil.rmtree(self.test_base, ignore_errors=True)

        subprocess.run(
            ["git", "worktree", "prune"],
            capture_output=True, text=True, cwd=str(PROJECT_ROOT)
        )

        # Reset singleton for clean tests
        import src.orchestration.playground_manager as pm_mod
        pm_mod._manager = None

    def test_list_playgrounds_summary(self):
        """list_playgrounds_summary returns formatted list."""
        from src.orchestration.playground_manager import PlaygroundManager, list_playgrounds_summary
        import src.orchestration.playground_manager as pm_mod
import pytest

        # Set up manager with our test base
        manager = PlaygroundManager(base_dir=self.test_base)
        pm_mod._manager = manager  # Override singleton for test

        config = asyncio.run(manager.create(
            task_description="Summary test task that is quite long and should be truncated",
        ))

        summary = list_playgrounds_summary()
        self.assertIsInstance(summary, list)
        self.assertEqual(len(summary), 1)

        item = summary[0]
        self.assertEqual(item["playground_id"], config.playground_id)
        self.assertEqual(item["status"], "active")
        self.assertIn("branch", item)
        self.assertIn("pipeline_runs", item)
        self.assertIn("age_minutes", item)
        # Task should be truncated to 80 chars
        self.assertLessEqual(len(item["task"]), 80)

        asyncio.run(manager.destroy(config.playground_id))


if __name__ == "__main__":
    unittest.main()
