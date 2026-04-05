"""
Tests for Phase 146.5: Playground Ops — Review, Promote, Reject lifecycle.

MARKER_146.5_TESTS

@status: active
@phase: 146.5
@depends: src/orchestration/playground_manager.py
"""

import asyncio
import json
import os
import shutil
import subprocess
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock

PROJECT_ROOT = Path(__file__).parent.parent


# ============================================================
# Test 1: Review
# ============================================================
class TestPlaygroundReview(unittest.TestCase):
    """Test playground review — diff + file listing."""

    def setUp(self):
        self.test_base = PROJECT_ROOT / ".playgrounds_test_ops"
        self.test_base.mkdir(parents=True, exist_ok=True)

        result = subprocess.run(
            ["git", "rev-parse", "--is-inside-work-tree"],
            capture_output=True, text=True, cwd=str(PROJECT_ROOT)
        )
        if result.returncode != 0:
            self.skipTest("Not in a git repository")

    def tearDown(self):
        self._cleanup_worktrees()

    def _cleanup_worktrees(self):
        result = subprocess.run(
            ["git", "worktree", "list", "--porcelain"],
            capture_output=True, text=True, cwd=str(PROJECT_ROOT)
        )
        for line in result.stdout.split("\n"):
            if line.startswith("worktree ") and ".playgrounds_test_ops" in line:
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

    def test_review_empty_playground(self):
        """Fresh playground has no changes."""
        from src.orchestration.playground_manager import PlaygroundManager

        manager = PlaygroundManager(base_dir=self.test_base)
        config = asyncio.run(manager.create(task_description="Review empty test"))
        review = asyncio.run(manager.review(config.playground_id))

        self.assertIsNotNone(review)
        self.assertEqual(review["playground_id"], config.playground_id)
        self.assertEqual(review["total_changes"], 0)
        self.assertIsInstance(review["changed_files"], list)

        asyncio.run(manager.destroy(config.playground_id))

    def test_review_with_new_file(self):
        """Review detects new untracked files."""
        from src.orchestration.playground_manager import PlaygroundManager

        manager = PlaygroundManager(base_dir=self.test_base)
        config = asyncio.run(manager.create(task_description="Review new file test"))
        wt_path = Path(config.worktree_path)

        # Create a new file in playground
        new_file = wt_path / "src" / "test_new_feature.py"
        new_file.parent.mkdir(parents=True, exist_ok=True)
        new_file.write_text("# New feature\ndef hello():\n    return 'world'\n")

        review = asyncio.run(manager.review(config.playground_id))

        self.assertIsNotNone(review)
        self.assertGreater(review["total_changes"], 0)

        # Find our file in changes
        paths = [f["path"] for f in review["changed_files"]]
        self.assertIn("src/test_new_feature.py", paths)

        # Check it has diff content
        for f in review["changed_files"]:
            if f["path"] == "src/test_new_feature.py":
                self.assertEqual(f["status"], "new")
                self.assertIn("diff", f)
                self.assertIn("hello", f["diff"])

        asyncio.run(manager.destroy(config.playground_id))

    def test_review_with_modified_file(self):
        """Review detects modifications to existing tracked files."""
        from src.orchestration.playground_manager import PlaygroundManager

        manager = PlaygroundManager(base_dir=self.test_base)
        config = asyncio.run(manager.create(task_description="Review modify test"))
        wt_path = Path(config.worktree_path)

        # Modify an existing file
        gitignore = wt_path / ".gitignore"
        if gitignore.exists():
            original = gitignore.read_text()
            gitignore.write_text(original + "\n# test line\n")

            review = asyncio.run(manager.review(config.playground_id))
            self.assertIsNotNone(review)
            self.assertGreater(review["total_changes"], 0)

            # Restore
            gitignore.write_text(original)

        asyncio.run(manager.destroy(config.playground_id))

    def test_review_nonexistent_playground(self):
        """Review of nonexistent playground returns None/error."""
        from src.orchestration.playground_manager import PlaygroundManager

        manager = PlaygroundManager(base_dir=self.test_base)
        review = asyncio.run(manager.review("pg_nonexistent"))
        self.assertIsNone(review)

    def test_review_includes_metadata(self):
        """Review includes playground metadata (task, preset, age)."""
        from src.orchestration.playground_manager import PlaygroundManager

        manager = PlaygroundManager(base_dir=self.test_base)
        config = asyncio.run(manager.create(
            task_description="Metadata test",
            preset="dragon_gold",
        ))

        review = asyncio.run(manager.review(config.playground_id))

        self.assertIn("task", review)
        self.assertIn("preset", review)
        self.assertIn("branch", review)
        self.assertIn("age_minutes", review)
        self.assertIn("pipeline_runs", review)
        self.assertEqual(review["preset"], "dragon_gold")
        self.assertEqual(review["task"], "Metadata test")

        asyncio.run(manager.destroy(config.playground_id))


# ============================================================
# Test 2: Promote (Copy Strategy)
# ============================================================
class TestPlaygroundPromote(unittest.TestCase):
    """Test promoting playground files to main codebase."""

    def setUp(self):
        self.test_base = PROJECT_ROOT / ".playgrounds_test_ops"
        self.test_base.mkdir(parents=True, exist_ok=True)

        result = subprocess.run(
            ["git", "rev-parse", "--is-inside-work-tree"],
            capture_output=True, text=True, cwd=str(PROJECT_ROOT)
        )
        if result.returncode != 0:
            self.skipTest("Not in a git repository")

    def tearDown(self):
        # Clean up any promoted files
        cleanup_files = [
            PROJECT_ROOT / "src" / "promoted_test_file.py",
            PROJECT_ROOT / "tests" / "promoted_test_file.py",
        ]
        for f in cleanup_files:
            if f.exists():
                f.unlink()

        self._cleanup_worktrees()

    def _cleanup_worktrees(self):
        result = subprocess.run(
            ["git", "worktree", "list", "--porcelain"],
            capture_output=True, text=True, cwd=str(PROJECT_ROOT)
        )
        for line in result.stdout.split("\n"):
            if line.startswith("worktree ") and ".playgrounds_test_ops" in line:
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

    def test_promote_copy_specific_files(self):
        """Promote specific files from playground to main via copy strategy."""
        from src.orchestration.playground_manager import PlaygroundManager

        manager = PlaygroundManager(base_dir=self.test_base)
        config = asyncio.run(manager.create(task_description="Promote test"))
        wt_path = Path(config.worktree_path)

        # Create a file in playground
        src_file = wt_path / "src" / "promoted_test_file.py"
        src_file.parent.mkdir(parents=True, exist_ok=True)
        src_file.write_text("# Promoted from playground\ndef promoted():\n    return True\n")

        # Promote just this file
        result = asyncio.run(manager.promote(
            playground_id=config.playground_id,
            files=["src/promoted_test_file.py"],
            strategy="copy",
            destroy_after=False,  # Keep for inspection
        ))

        self.assertTrue(result["success"])
        self.assertIn("src/promoted_test_file.py", result["promoted_files"])
        self.assertEqual(result["strategy"], "copy")
        self.assertEqual(len(result["errors"]), 0)

        # Verify file now exists in main
        main_file = PROJECT_ROOT / "src" / "promoted_test_file.py"
        self.assertTrue(main_file.exists(), "Promoted file should exist in main")
        self.assertIn("promoted", main_file.read_text())

        # Cleanup
        main_file.unlink()
        asyncio.run(manager.destroy(config.playground_id))

    def test_promote_nonexistent_file(self):
        """Promoting a file that doesn't exist in playground reports error."""
        from src.orchestration.playground_manager import PlaygroundManager

        manager = PlaygroundManager(base_dir=self.test_base)
        config = asyncio.run(manager.create(task_description="Promote missing"))

        result = asyncio.run(manager.promote(
            playground_id=config.playground_id,
            files=["src/this_does_not_exist.py"],
            strategy="copy",
            destroy_after=False,
        ))

        self.assertFalse(result["success"])
        self.assertGreater(len(result["errors"]), 0)

        asyncio.run(manager.destroy(config.playground_id))

    def test_promote_with_destroy_after(self):
        """Promote with destroy_after=True removes playground."""
        from src.orchestration.playground_manager import PlaygroundManager

        manager = PlaygroundManager(base_dir=self.test_base)
        config = asyncio.run(manager.create(task_description="Destroy after test"))
        wt_path = Path(config.worktree_path)

        # Create file
        src_file = wt_path / "src" / "promoted_test_file.py"
        src_file.parent.mkdir(parents=True, exist_ok=True)
        src_file.write_text("# auto-destroy\n")

        result = asyncio.run(manager.promote(
            playground_id=config.playground_id,
            files=["src/promoted_test_file.py"],
            strategy="copy",
            destroy_after=True,
        ))

        self.assertTrue(result["success"])
        self.assertTrue(result["destroyed"])

        # Playground should be gone
        active = manager.list_playgrounds(include_inactive=False)
        ids = [p.playground_id for p in active]
        self.assertNotIn(config.playground_id, ids)

        # Clean up promoted file
        promoted = PROJECT_ROOT / "src" / "promoted_test_file.py"
        if promoted.exists():
            promoted.unlink()

    def test_promote_blocks_path_traversal(self):
        """Promote won't copy files outside project root."""
        from src.orchestration.playground_manager import PlaygroundManager

        manager = PlaygroundManager(base_dir=self.test_base)
        config = asyncio.run(manager.create(task_description="Security test"))

        result = asyncio.run(manager.promote(
            playground_id=config.playground_id,
            files=["../../../etc/passwd"],
            strategy="copy",
            destroy_after=False,
        ))

        # Should fail — source doesn't exist in playground
        self.assertFalse(result["success"])

        asyncio.run(manager.destroy(config.playground_id))

    def test_promote_nonexistent_playground(self):
        """Promoting from non-existent playground returns error."""
        from src.orchestration.playground_manager import PlaygroundManager

        manager = PlaygroundManager(base_dir=self.test_base)
        result = asyncio.run(manager.promote(
            playground_id="pg_fake_123",
            files=["anything.py"],
        ))

        self.assertFalse(result["success"])
        self.assertIn("error", result)

    def test_promote_unknown_strategy(self):
        """Unknown promote strategy returns error."""
        from src.orchestration.playground_manager import PlaygroundManager

        manager = PlaygroundManager(base_dir=self.test_base)
        config = asyncio.run(manager.create(task_description="Bad strategy"))

        result = asyncio.run(manager.promote(
            playground_id=config.playground_id,
            strategy="teleport",
        ))

        self.assertFalse(result["success"])
        self.assertIn("Unknown strategy", result["error"])

        asyncio.run(manager.destroy(config.playground_id))


# ============================================================
# Test 3: Reject
# ============================================================
class TestPlaygroundReject(unittest.TestCase):
    """Test rejecting playground results."""

    def setUp(self):
        self.test_base = PROJECT_ROOT / ".playgrounds_test_ops"
        self.test_base.mkdir(parents=True, exist_ok=True)

        result = subprocess.run(
            ["git", "rev-parse", "--is-inside-work-tree"],
            capture_output=True, text=True, cwd=str(PROJECT_ROOT)
        )
        if result.returncode != 0:
            self.skipTest("Not in a git repository")

    def tearDown(self):
        self._cleanup_worktrees()

    def _cleanup_worktrees(self):
        result = subprocess.run(
            ["git", "worktree", "list", "--porcelain"],
            capture_output=True, text=True, cwd=str(PROJECT_ROOT)
        )
        for line in result.stdout.split("\n"):
            if line.startswith("worktree ") and ".playgrounds_test_ops" in line:
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

    def test_reject_sets_failed_status(self):
        """Rejecting marks playground as failed."""
        from src.orchestration.playground_manager import PlaygroundManager

        manager = PlaygroundManager(base_dir=self.test_base)
        config = asyncio.run(manager.create(task_description="Reject test"))

        result = asyncio.run(manager.reject(
            config.playground_id,
            reason="Code quality too low",
        ))

        self.assertTrue(result["success"])
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["reason"], "Code quality too low")
        self.assertFalse(result["destroyed"])

        # Status should be failed
        updated = manager._playgrounds[config.playground_id]
        self.assertEqual(updated.status, "failed")

        asyncio.run(manager.destroy(config.playground_id))

    def test_reject_with_destroy(self):
        """Rejecting with destroy=True removes playground."""
        from src.orchestration.playground_manager import PlaygroundManager

        manager = PlaygroundManager(base_dir=self.test_base)
        config = asyncio.run(manager.create(task_description="Reject destroy test"))

        result = asyncio.run(manager.reject(
            config.playground_id,
            reason="Bad code",
            destroy=True,
        ))

        self.assertTrue(result["success"])
        self.assertTrue(result["destroyed"])

    def test_reject_nonexistent(self):
        """Rejecting non-existent playground returns error."""
        from src.orchestration.playground_manager import PlaygroundManager

        manager = PlaygroundManager(base_dir=self.test_base)
        result = asyncio.run(manager.reject("pg_fake_456"))
        self.assertFalse(result["success"])


# ============================================================
# Test 4: Settings
# ============================================================
class TestPlaygroundSettings(unittest.TestCase):
    """Test playground settings persistence."""

    def setUp(self):
        self.settings_file = PROJECT_ROOT / "data" / "playground_settings.json"
        # Backup existing settings
        self._backup = None
        if self.settings_file.exists():
            self._backup = self.settings_file.read_text()

    def tearDown(self):
        # Restore settings
        if self._backup:
            self.settings_file.write_text(self._backup)
        elif self.settings_file.exists():
            self.settings_file.unlink()

    def test_load_defaults(self):
        """Load settings returns defaults when no file exists."""
        from src.orchestration.playground_manager import PlaygroundManager

        # Remove settings file if exists
        if self.settings_file.exists():
            self.settings_file.unlink()

        settings = PlaygroundManager.load_settings()
        self.assertIn("base_dir", settings)
        self.assertIn("max_concurrent", settings)
        self.assertIn("ttl_hours", settings)
        self.assertIn("auto_cleanup", settings)
        self.assertEqual(settings["max_concurrent"], 5)

    def test_save_and_load(self):
        """Save settings to disk and reload."""
        from src.orchestration.playground_manager import PlaygroundManager

        custom = {
            "base_dir": "/tmp/my_playgrounds",
            "max_concurrent": 3,
            "ttl_hours": 2.0,
            "auto_cleanup": False,
        }
        PlaygroundManager.save_settings(custom)

        loaded = PlaygroundManager.load_settings()
        self.assertEqual(loaded["base_dir"], "/tmp/my_playgrounds")
        self.assertEqual(loaded["max_concurrent"], 3)
        self.assertEqual(loaded["ttl_hours"], 2.0)
        self.assertFalse(loaded["auto_cleanup"])


# ============================================================
# Test 5: REST API Endpoints (existence check)
# ============================================================
class TestPlaygroundRestEndpoints(unittest.TestCase):
    """Verify REST endpoints are registered."""

    def test_endpoints_exist_in_debug_routes(self):
        """All playground REST endpoints are defined."""
        from src.api.routes.debug_routes import router

        # Get all route paths
        routes = []
        for route in router.routes:
            if hasattr(route, "path"):
                routes.append(route.path)

        # Check playground endpoints exist (router prefix is /api/debug)
        expected_paths = [
            "/api/debug/playground",
            "/api/debug/playground/create",
            "/api/debug/playground/{pg_id}/review",
            "/api/debug/playground/{pg_id}/promote",
            "/api/debug/playground/{pg_id}/reject",
            "/api/debug/playground/{pg_id}",
            "/api/debug/playground/settings",
        ]
        for path in expected_paths:
            self.assertIn(
                path, routes,
                f"Endpoint {path} not found in routes. Available: {sorted(routes)}"
            )


# ============================================================
# Test 6: Convenience Functions
# ============================================================
class TestConvenienceFunctions(unittest.TestCase):
    """Test module-level convenience functions."""

    def test_review_playground_function(self):
        """review_playground convenience function works."""
        from src.orchestration.playground_manager import review_playground
        result = asyncio.run(review_playground("pg_nonexistent_999"))
        self.assertIn("error", result)

    def test_promote_playground_function(self):
        """promote_playground convenience function works."""
        from src.orchestration.playground_manager import promote_playground
        result = asyncio.run(promote_playground("pg_nonexistent_999"))
        self.assertFalse(result["success"])

    def test_reject_playground_function(self):
        """reject_playground convenience function works."""
        from src.orchestration.playground_manager import reject_playground
        result = asyncio.run(reject_playground("pg_nonexistent_999"))
        self.assertFalse(result["success"])


# ============================================================
# Test 7: Full Lifecycle (create → write → review → promote → verify)
# ============================================================
class TestFullLifecycle(unittest.TestCase):
    """Integration test: full create → write → review → promote → verify."""

    def setUp(self):
        self.test_base = PROJECT_ROOT / ".playgrounds_test_ops"
        self.test_base.mkdir(parents=True, exist_ok=True)

        result = subprocess.run(
            ["git", "rev-parse", "--is-inside-work-tree"],
            capture_output=True, text=True, cwd=str(PROJECT_ROOT)
        )
        if result.returncode != 0:
            self.skipTest("Not in a git repository")

    def tearDown(self):
        # Clean up promoted file
        promoted = PROJECT_ROOT / "src" / "lifecycle_test_output.py"
        if promoted.exists():
            promoted.unlink()

        self._cleanup_worktrees()

    def _cleanup_worktrees(self):
        result = subprocess.run(
            ["git", "worktree", "list", "--porcelain"],
            capture_output=True, text=True, cwd=str(PROJECT_ROOT)
        )
        for line in result.stdout.split("\n"):
            if line.startswith("worktree ") and ".playgrounds_test_ops" in line:
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

    def test_full_create_write_review_promote(self):
        """Full lifecycle: create → write file → review → promote → verify in main."""
        from src.orchestration.playground_manager import PlaygroundManager

        manager = PlaygroundManager(base_dir=self.test_base)

        # Step 1: Create
        config = asyncio.run(manager.create(
            task_description="Full lifecycle test",
            preset="dragon_silver",
        ))
        self.assertEqual(config.status, "active")
        wt_path = Path(config.worktree_path)

        # Step 2: Write (simulating pipeline output)
        out_file = wt_path / "src" / "lifecycle_test_output.py"
        out_file.parent.mkdir(parents=True, exist_ok=True)
        out_file.write_text(
            '"""Generated by lifecycle test."""\n\n'
            'def lifecycle_function():\n'
            '    return "promoted successfully"\n'
        )

        # Step 3: Review
        review = asyncio.run(manager.review(config.playground_id))
        self.assertIsNotNone(review)
        self.assertGreater(review["total_changes"], 0)
        paths = [f["path"] for f in review["changed_files"]]
        self.assertIn("src/lifecycle_test_output.py", paths)

        # Step 4: Promote
        result = asyncio.run(manager.promote(
            playground_id=config.playground_id,
            files=["src/lifecycle_test_output.py"],
            strategy="copy",
            destroy_after=True,
        ))
        self.assertTrue(result["success"])
        self.assertTrue(result["destroyed"])

        # Step 5: Verify in main
        promoted_file = PROJECT_ROOT / "src" / "lifecycle_test_output.py"
        self.assertTrue(promoted_file.exists(), "File should be in main after promote")
        content = promoted_file.read_text()
        self.assertIn("lifecycle_function", content)
        self.assertIn("promoted successfully", content)


if __name__ == "__main__":
    unittest.main()
