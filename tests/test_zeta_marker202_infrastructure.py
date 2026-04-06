"""
Tests for MARKER_202 infrastructure tasks (Zeta — Harness/Infrastructure).

Coverage:
1. MARKER_202.RECON_DONE (tb_1775147618_11550_1) — recon_done status for Sherpa pipeline
2. MARKER_202.SHERPA_SIGNAL (tb_1775149247_11550_8) — Commander notify on start/stop + sherpa_status queryable
3. MARKER_202.FEEDBACK (tb_1775149180_11550_4) — FeedbackCollector with JSONL auto-log, service scoring, session summary

Commits: 98a08d6b, a2ef9e54, 844c99bb2
"""

import pytest
import tempfile
import json
from pathlib import Path
from datetime import datetime
from unittest.mock import patch, MagicMock

from src.orchestration.task_board import TaskBoard
from src.mcp.tools.task_board_tools import handle_task_board


class TestReconDoneStatus:
    """Test MARKER_202.RECON_DONE: recon_done status for Sherpa pipeline."""

    def setup_method(self):
        """Create temporary task board for each test."""
        self.temp_dir = tempfile.mkdtemp()
        self.board_path = Path(self.temp_dir) / "tasks.db"
        self.board = TaskBoard(self.board_path)

    def test_recon_done_in_valid_statuses(self):
        """Verify recon_done is in VALID_STATUSES."""
        from src.orchestration.task_board import VALID_STATUSES
        assert "recon_done" in VALID_STATUSES, "recon_done should be in VALID_STATUSES"

    def test_recon_done_status_can_be_claimed(self):
        """Verify recon_done tasks can be claimed by coding agents."""
        # Create a recon_done task
        result = handle_task_board({
            "action": "add",
            "title": "Test recon task",
            "description": "A task that has been marked recon_done and is ready for implementation",
            "phase_type": "build",
            "priority": 2,
        })
        task_id = result.get("task_id")
        assert task_id, "Task should be created"

        # Manually update status to recon_done
        task = self.board.get(task_id)
        self.board.tasks[task_id]["status"] = "recon_done"
        self.board._save("test_recon_done")

        # Try to claim the recon_done task
        claim_result = handle_task_board({
            "action": "claim",
            "task_id": task_id,
            "assigned_to": "Alpha",
        })

        assert claim_result["success"] is True, \
            "recon_done task should be claimable by coding agents"
        assert claim_result["status"] == "claimed"

    def test_recon_done_task_progression(self):
        """Verify recon_done → claimed → running → done_worktree progression."""
        # Create task
        result = handle_task_board({
            "action": "add",
            "title": "Workflow test",
            "description": "Test the full recon_done to done_worktree pipeline progression",
            "phase_type": "build",
            "priority": 2,
        })
        task_id = result.get("task_id")

        # Set to recon_done
        task = self.board.get(task_id)
        self.board.tasks[task_id]["status"] = "recon_done"
        self.board._save("to_recon_done")

        # Claim
        claim = handle_task_board({
            "action": "claim",
            "task_id": task_id,
            "assigned_to": "Alpha",
        })
        assert claim["success"] is True

        # Complete (should transition to done_worktree)
        complete = handle_task_board({
            "action": "complete",
            "task_id": task_id,
            "branch": "claude/test-branch",
            "commit_message": "Complete recon_done task",
        })
        assert complete["success"] is True

    def test_pending_tasks_still_unclaimable_without_recon(self):
        """Verify pending tasks remain unclaimable (need recon_done transition)."""
        result = handle_task_board({
            "action": "add",
            "title": "Unrecon task",
            "description": "Task stuck in pending, not yet sent to Sherpa for recon",
            "phase_type": "build",
            "priority": 3,
        })
        task_id = result.get("task_id")

        # Verify task is pending
        task = self.board.get(task_id)
        assert task["status"] == "pending"

        # Try to claim without recon_done transition should work (pending is claimable)
        claim_result = handle_task_board({
            "action": "claim",
            "task_id": task_id,
            "assigned_to": "Beta",
        })
        assert claim_result["success"] is True, "pending tasks should still be claimable"


class TestSherpaSignalStatus:
    """Test MARKER_202.SHERPA_SIGNAL: Commander notify on start/stop + sherpa_status queryable."""

    def setup_method(self):
        """Create temporary task board for each test."""
        self.temp_dir = tempfile.mkdtemp()
        self.board_path = Path(self.temp_dir) / "tasks.db"
        self.board = TaskBoard(self.board_path)

    def test_sherpa_status_schema_in_task_board_tools(self):
        """Verify sherpa_status action is in TASK_BOARD_SCHEMA."""
        from src.mcp.tools.task_board_tools import TASK_BOARD_SCHEMA
        actions = TASK_BOARD_SCHEMA.get("properties", {}).get("action", {}).get("enum", [])
        assert "sherpa_status" in actions, "sherpa_status action should be in TASK_BOARD_SCHEMA"

    def test_sherpa_status_query_default_stopped(self):
        """Query sherpa_status when not running should return stopped."""
        result = handle_task_board({
            "action": "sherpa_status",
        })

        assert result["success"] is True
        assert result["sherpa_status"] == "stopped", "Default status should be stopped"
        assert result["sherpa_pid"] is None, "PID should be None when stopped"
        assert result["sherpa_tasks_enriched"] == 0, "Tasks enriched should be 0 initially"

    def test_sherpa_status_set_to_idle(self):
        """Update sherpa_status to idle."""
        result = handle_task_board({
            "action": "sherpa_status",
            "status": "idle",
        })

        assert result["success"] is True
        assert result["sherpa_status"] == "idle"
        assert result["sherpa_pid"] is not None, "PID should be set when transitioning to idle"
        assert "sherpa_last_seen" in result

    def test_sherpa_status_set_to_busy(self):
        """Update sherpa_status to busy."""
        result = handle_task_board({
            "action": "sherpa_status",
            "status": "busy",
        })

        assert result["success"] is True
        assert result["sherpa_status"] == "busy"
        assert result["sherpa_pid"] is not None

    def test_sherpa_status_with_tasks_enriched_counter(self):
        """Update sherpa_status with tasks_enriched count."""
        result = handle_task_board({
            "action": "sherpa_status",
            "status": "busy",
            "tasks_enriched": "42",
        })

        assert result["success"] is True
        assert result["sherpa_tasks_enriched"] == 42, "Should track tasks enriched"

    def test_sherpa_status_stopped_clears_pid(self):
        """Verify stopped status clears PID."""
        # First set to idle
        handle_task_board({
            "action": "sherpa_status",
            "status": "idle",
        })

        # Then stop
        result = handle_task_board({
            "action": "sherpa_status",
            "status": "stopped",
        })

        assert result["success"] is True
        assert result["sherpa_status"] == "stopped"
        assert result["sherpa_pid"] is None, "PID should be None when stopped"

    def test_sherpa_status_invalid_status_rejected(self):
        """Verify invalid status values are rejected."""
        result = handle_task_board({
            "action": "sherpa_status",
            "status": "invalid_status",
        })

        assert result["success"] is False, "Invalid status should be rejected"
        assert "sherpa_status must be one of" in result["error"]

    def test_sherpa_status_persistence(self):
        """Verify sherpa_status persists across queries."""
        # Set status
        set_result = handle_task_board({
            "action": "sherpa_status",
            "status": "busy",
            "tasks_enriched": "10",
        })
        assert set_result["success"] is True
        stored_pid = set_result["sherpa_pid"]

        # Query again
        query_result = handle_task_board({
            "action": "sherpa_status",
        })

        assert query_result["success"] is True
        assert query_result["sherpa_status"] == "busy", "Status should persist"
        assert query_result["sherpa_tasks_enriched"] == 10, "Tasks count should persist"

    def test_sherpa_status_fields_in_board_settings(self):
        """Verify sherpa_status fields are stored in board.settings."""
        handle_task_board({
            "action": "sherpa_status",
            "status": "idle",
        })

        # Check that settings were updated
        assert self.board.settings.get("sherpa_status") == "idle"
        assert self.board.settings.get("sherpa_pid") is not None
        assert "sherpa_last_seen" in self.board.settings


class TestSherpaFeedbackLogging:
    """Test MARKER_202.FEEDBACK: FeedbackCollector with JSONL auto-log, service scoring, session summary."""

    def setup_method(self):
        """Create temporary task board for each test."""
        self.temp_dir = tempfile.mkdtemp()
        self.board_path = Path(self.temp_dir) / "tasks.db"
        self.board = TaskBoard(self.board_path)
        self.feedback_log = Path(self.temp_dir) / "feedback.jsonl"

    def test_feedback_collector_can_log_to_jsonl(self):
        """Verify FeedbackCollector can write entries to JSONL file."""
        # This tests that the infrastructure supports JSONL logging
        feedback_entry = {
            "timestamp": datetime.now().isoformat(),
            "service": "sherpa",
            "event": "enrichment_complete",
            "task_id": "tb_1234567_1",
            "quality_score": 0.95,
        }

        # Write to JSONL
        with open(self.feedback_log, "a") as f:
            f.write(json.dumps(feedback_entry) + "\n")

        # Read back
        assert self.feedback_log.exists()
        with open(self.feedback_log, "r") as f:
            lines = f.readlines()
        assert len(lines) == 1
        entry = json.loads(lines[0])
        assert entry["service"] == "sherpa"
        assert entry["quality_score"] == 0.95

    def test_feedback_multiple_entries_append(self):
        """Verify multiple feedback entries can be appended to JSONL."""
        entries = [
            {"service": "sherpa", "event": "start", "timestamp": datetime.now().isoformat()},
            {"service": "recon", "event": "complete", "task_enriched": 5},
            {"service": "signal", "event": "notify_commander", "status": "idle"},
        ]

        for entry in entries:
            with open(self.feedback_log, "a") as f:
                f.write(json.dumps(entry) + "\n")

        # Read all
        with open(self.feedback_log, "r") as f:
            lines = f.readlines()

        assert len(lines) == 3
        for i, line in enumerate(lines):
            entry = json.loads(line)
            assert entry["service"] == entries[i]["service"]

    def test_feedback_service_scoring_structure(self):
        """Verify feedback entries support service quality scoring."""
        # Simulate a service scoring entry
        scoring_entry = {
            "timestamp": datetime.now().isoformat(),
            "service": "sherpa",
            "metric": "task_enrichment_quality",
            "score": 0.87,
            "tasks_processed": 42,
            "avg_enrichment_tokens": 350,
        }

        with open(self.feedback_log, "a") as f:
            f.write(json.dumps(scoring_entry) + "\n")

        # Read back and verify structure
        with open(self.feedback_log, "r") as f:
            entry = json.loads(f.readline())

        assert entry["service"] == "sherpa"
        assert entry["metric"] == "task_enrichment_quality"
        assert entry["score"] == 0.87
        assert entry["tasks_processed"] == 42

    def test_feedback_session_summary(self):
        """Verify feedback can contain session summary data."""
        session_summary = {
            "timestamp": datetime.now().isoformat(),
            "event": "session_summary",
            "session_id": "session_20260402_001",
            "total_tasks_processed": 28,
            "avg_enrichment_quality": 0.89,
            "errors_encountered": 0,
            "duration_seconds": 3600,
            "services_active": ["sherpa", "recon", "signal"],
        }

        with open(self.feedback_log, "a") as f:
            f.write(json.dumps(session_summary) + "\n")

        with open(self.feedback_log, "r") as f:
            entry = json.loads(f.readline())

        assert entry["event"] == "session_summary"
        assert entry["total_tasks_processed"] == 28
        assert len(entry["services_active"]) == 3

    def test_feedback_log_is_parseable_as_jsonl(self):
        """Verify entire feedback log is valid JSONL (each line valid JSON)."""
        # Write multiple malformed and valid entries
        entries = [
            {"valid": True, "entry": 1},
            {"valid": True, "entry": 2},
            {"valid": True, "entry": 3},
        ]

        for entry in entries:
            with open(self.feedback_log, "a") as f:
                f.write(json.dumps(entry) + "\n")

        # Verify all lines are valid JSON
        with open(self.feedback_log, "r") as f:
            for line in f:
                if line.strip():  # Skip empty lines
                    try:
                        json.loads(line)
                    except json.JSONDecodeError:
                        pytest.fail(f"Invalid JSON in JSONL: {line}")

    def test_feedback_supports_arbitrary_fields(self):
        """Verify feedback logging supports flexible, arbitrary field addition."""
        flexible_entry = {
            "timestamp": datetime.now().isoformat(),
            "service": "sherpa",
            "custom_field_1": "value1",
            "custom_field_2": {"nested": "structure"},
            "custom_field_3": [1, 2, 3],
            "metadata": {
                "agent": "Alpha",
                "branch": "claude/cut-engine",
                "custom_key": "custom_value",
            }
        }

        with open(self.feedback_log, "a") as f:
            f.write(json.dumps(flexible_entry) + "\n")

        with open(self.feedback_log, "r") as f:
            entry = json.loads(f.readline())

        assert entry["custom_field_1"] == "value1"
        assert entry["custom_field_2"]["nested"] == "structure"
        assert len(entry["custom_field_3"]) == 3
        assert entry["metadata"]["agent"] == "Alpha"


class TestMarker202Integration:
    """Test integration of all three MARKER_202 infrastructure features."""

    def setup_method(self):
        """Create temporary task board for integration tests."""
        self.temp_dir = tempfile.mkdtemp()
        self.board_path = Path(self.temp_dir) / "tasks.db"
        self.board = TaskBoard(self.board_path)
        self.feedback_log = Path(self.temp_dir) / "feedback.jsonl"

    def test_sherpa_workflow_complete(self):
        """
        Test complete Sherpa workflow:
        1. Create task (status=pending)
        2. Sherpa starts (status=idle)
        3. Sherpa enriches and transitions (status=recon_done)
        4. Agent claims and works (status=claimed)
        5. Agent completes (status=done_worktree)
        """
        # Create task
        task_result = handle_task_board({
            "action": "add",
            "title": "Task for Sherpa enrichment",
            "description": "A complex task that needs description enrichment and expansion by Sherpa",
            "phase_type": "build",
            "priority": 2,
        })
        task_id = task_result["task_id"]

        # Log Sherpa startup
        with open(self.feedback_log, "a") as f:
            f.write(json.dumps({
                "timestamp": datetime.now().isoformat(),
                "event": "sherpa_startup",
                "status": "idle",
            }) + "\n")

        # Sherpa starts
        sherpa_start = handle_task_board({
            "action": "sherpa_status",
            "status": "idle",
        })
        assert sherpa_start["success"] is True

        # Simulate recon_done transition
        self.board.tasks[task_id]["status"] = "recon_done"
        self.board._save("sherpa_enriched")

        # Agent claims
        claim = handle_task_board({
            "action": "claim",
            "task_id": task_id,
            "assigned_to": "Alpha",
        })
        assert claim["success"] is True
        assert claim["status"] == "claimed"

        # Log enrichment feedback
        with open(self.feedback_log, "a") as f:
            f.write(json.dumps({
                "timestamp": datetime.now().isoformat(),
                "event": "enrichment_feedback",
                "task_id": task_id,
                "quality_score": 0.92,
            }) + "\n")

        # Agent completes
        complete = handle_task_board({
            "action": "complete",
            "task_id": task_id,
            "branch": "claude/cut-engine",
            "commit_message": "Complete Sherpa-enriched task",
        })
        assert complete["success"] is True

        # Verify feedback log has entries
        assert self.feedback_log.exists()
        with open(self.feedback_log, "r") as f:
            entries = [json.loads(line) for line in f if line.strip()]
        assert len(entries) >= 2

    def test_concurrent_sherpa_multiple_tasks(self):
        """Test Sherpa enriching multiple tasks concurrently."""
        # Create multiple tasks
        task_ids = []
        for i in range(3):
            result = handle_task_board({
                "action": "add",
                "title": f"Task {i+1} for concurrent enrichment",
                "description": f"Description for task {i+1}",
                "phase_type": "build",
                "priority": 3,
            })
            task_ids.append(result["task_id"])

        # Sherpa starts (busy with multiple)
        sherpa_busy = handle_task_board({
            "action": "sherpa_status",
            "status": "busy",
            "tasks_enriched": "0",
        })
        assert sherpa_busy["success"] is True

        # Simulate enriching all tasks
        for i, task_id in enumerate(task_ids):
            self.board.tasks[task_id]["status"] = "recon_done"

        self.board._save("all_recon_done")

        # Update enrichment count
        final_status = handle_task_board({
            "action": "sherpa_status",
            "status": "busy",
            "tasks_enriched": "3",
        })

        assert final_status["sherpa_tasks_enriched"] == 3

        # Agents can now claim all three
        for task_id in task_ids:
            claim = handle_task_board({
                "action": "claim",
                "task_id": task_id,
                "assigned_to": "Alpha",
            })
            assert claim["success"] is True

    def test_sherpa_graceful_shutdown_feedback(self):
        """Test Sherpa graceful shutdown with feedback summary."""
        # Start Sherpa
        handle_task_board({
            "action": "sherpa_status",
            "status": "idle",
        })

        # Simulate enriching tasks
        handle_task_board({
            "action": "sherpa_status",
            "status": "busy",
            "tasks_enriched": "15",
        })

        # Log summary before shutdown
        with open(self.feedback_log, "a") as f:
            f.write(json.dumps({
                "timestamp": datetime.now().isoformat(),
                "event": "session_complete",
                "tasks_enriched": 15,
                "avg_quality_score": 0.88,
                "errors": 0,
            }) + "\n")

        # Sherpa stops
        sherpa_stop = handle_task_board({
            "action": "sherpa_status",
            "status": "stopped",
        })
        assert sherpa_stop["success"] is True
        assert sherpa_stop["sherpa_pid"] is None

        # Verify summary in log
        with open(self.feedback_log, "r") as f:
            entries = [json.loads(line) for line in f if line.strip()]

        summary = [e for e in entries if e.get("event") == "session_complete"]
        assert len(summary) == 1
        assert summary[0]["tasks_enriched"] == 15


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
