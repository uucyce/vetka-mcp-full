"""
Phase 119.6: Digest Harmony — auto-sync phase from git + integrity tests.

Tests:
- TestAutoSyncFromGit: phase extraction, headline generation, achievement insertion, pending cleanup
- TestDigestIntegrity: no dead doc links, current_phase matches reality, pending_items sanity
"""

import json
import copy
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.update_project_digest import auto_sync_from_git


# --- Fixtures ---

@pytest.fixture
def base_digest():
    """A minimal digest for testing auto_sync_from_git."""
    return {
        "current_phase": {
            "number": 118,
            "subphase": "10",
            "name": "Old Phase",
            "status": "COMPLETED"
        },
        "summary": {
            "headline": "Phase 118.10 DONE! Old stuff",
            "key_achievements": [
                "[aaaa1111] Phase 118.10: something old"
            ],
            "pending_items": [
                "Phase 119.1: MGC Deduplication (P0)",
                "Phase 119.2: STM Unification (P0)",
                "Phase 119.3: Heartbeat Live Test",
                "Phase 120.1: Future task",
                "TEST: Verify MGC cascade works"
            ]
        }
    }


def _mock_git_log(commit_msg: str, commit_hash: str = "abcd1234" * 5):
    """Create a mock for subprocess.run that returns a git log result."""
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = f"{commit_hash} {commit_msg}\n"
    return mock_result


# --- TestAutoSyncFromGit ---

class TestAutoSyncFromGit:
    """Test auto_sync_from_git() function."""

    @patch("scripts.update_project_digest.subprocess.run")
    def test_extracts_phase_from_commit(self, mock_run, base_digest):
        """Phase number and subphase extracted from commit message."""
        mock_run.return_value = _mock_git_log(
            "Phase 119.5: Scout role + CAM rename",
            "abcdef1234567890abcdef1234567890abcdef12"
        )

        result = auto_sync_from_git(copy.deepcopy(base_digest))

        assert result["current_phase"]["number"] == 119
        assert result["current_phase"]["subphase"] == "5"
        assert result["current_phase"]["status"] == "COMPLETED"

    @patch("scripts.update_project_digest.subprocess.run")
    def test_generates_headline(self, mock_run, base_digest):
        """Headline auto-generated from phase info."""
        mock_run.return_value = _mock_git_log(
            "Phase 119.5: Scout role + CAM rename"
        )

        result = auto_sync_from_git(copy.deepcopy(base_digest))

        assert "Phase 119.5 DONE!" in result["summary"]["headline"]
        assert "Scout role" in result["summary"]["headline"]

    @patch("scripts.update_project_digest.subprocess.run")
    def test_inserts_achievement(self, mock_run, base_digest):
        """New achievement prepended to list."""
        mock_run.return_value = _mock_git_log(
            "Phase 119.5: Scout role + CAM rename",
            "ff001122334455667788990011223344ff001122"
        )

        result = auto_sync_from_git(copy.deepcopy(base_digest))
        achievements = result["summary"]["key_achievements"]

        # New achievement at index 0
        assert "ff001122" in achievements[0]
        assert "Phase 119.5" in achievements[0]
        # Old achievement still present
        assert any("aaaa1111" in a for a in achievements)
        # Max 10
        assert len(achievements) <= 10

    @patch("scripts.update_project_digest.subprocess.run")
    def test_cleans_pending_items(self, mock_run, base_digest):
        """Completed phases removed from pending_items."""
        mock_run.return_value = _mock_git_log(
            "Phase 119.3: Heartbeat Live Test"
        )

        result = auto_sync_from_git(copy.deepcopy(base_digest))
        pending = result["summary"]["pending_items"]

        # 119.1, 119.2, 119.3 should be cleaned (all <= 119.3)
        assert not any("119.1" in p for p in pending)
        assert not any("119.2" in p for p in pending)
        assert not any("119.3" in p for p in pending)
        # 120.1 should remain (future)
        assert any("120.1" in p for p in pending)
        # Non-phase items should remain
        assert any("TEST:" in p for p in pending)

    @patch("scripts.update_project_digest.subprocess.run")
    def test_no_phase_in_commit_noop(self, mock_run, base_digest):
        """Non-phase commits leave digest unchanged."""
        mock_run.return_value = _mock_git_log(
            "Fix typo in README"
        )

        original = copy.deepcopy(base_digest)
        result = auto_sync_from_git(copy.deepcopy(base_digest))

        assert result["current_phase"]["number"] == original["current_phase"]["number"]
        assert result["summary"]["headline"] == original["summary"]["headline"]

    @patch("scripts.update_project_digest.subprocess.run")
    def test_no_duplicate_achievement(self, mock_run, base_digest):
        """Same commit hash doesn't create duplicate achievements."""
        mock_run.return_value = _mock_git_log(
            "Phase 119.5: Scout role",
            "abcdef1234567890abcdef1234567890abcdef12"
        )

        # First call
        result = auto_sync_from_git(copy.deepcopy(base_digest))
        count_after_first = len(result["summary"]["key_achievements"])

        # Second call with same hash
        result = auto_sync_from_git(result)
        count_after_second = len(result["summary"]["key_achievements"])

        assert count_after_first == count_after_second

    @patch("scripts.update_project_digest.subprocess.run")
    def test_git_failure_noop(self, mock_run, base_digest):
        """Git command failure leaves digest unchanged."""
        mock_result = MagicMock()
        mock_result.returncode = 128
        mock_result.stdout = ""
        mock_run.return_value = mock_result

        original = copy.deepcopy(base_digest)
        result = auto_sync_from_git(copy.deepcopy(base_digest))

        assert result["current_phase"] == original["current_phase"]


# --- TestDigestIntegrity ---

class TestDigestIntegrity:
    """Test the actual project_digest.json for integrity."""

    @pytest.fixture
    def digest(self):
        digest_path = PROJECT_ROOT / "data" / "project_digest.json"
        with open(digest_path) as f:
            return json.load(f)

    def test_no_dead_documentation_links(self, digest):
        """No documentation section with dead file links."""
        if "documentation" in digest:
            for key, path in digest["documentation"].items():
                full_path = PROJECT_ROOT / path
                assert full_path.exists(), f"Dead doc link: {key} -> {path}"

    def test_no_stale_phase_108_plan(self, digest):
        """Dead phase_108_7_plan artifact should be removed."""
        assert "phase_108_7_plan" not in digest, "Stale phase_108_7_plan should be removed"

    def test_pending_items_not_completed(self, digest):
        """Pending items should not reference phases that are already completed."""
        import re
        current = digest.get("current_phase", {})
        current_num = current.get("number", 0)
        current_sub = int(current.get("subphase", "0"))

        pending = digest.get("summary", {}).get("pending_items", [])
        for item in pending:
            match = re.search(r'Phase\s+(\d+)\.(\d+)', item)
            if match:
                item_phase = int(match.group(1))
                item_sub = int(match.group(2))
                is_completed = (item_phase < current_num or
                                (item_phase == current_num and item_sub <= current_sub))
                assert not is_completed, f"Pending item references completed phase: {item}"
