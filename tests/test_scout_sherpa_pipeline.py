"""
E2E tests for Scout→Sherpa pipeline.

MARKER_203.SCOUT_E2E

Verifies:
1. Scout auto-triggers on add_task() when allowed_paths present
2. scout_context stored with correct fields
3. Tasks without allowed_paths stay pending
4. scout_recon tasks visible for Sherpa polling
5. implementation_hints enriched with Scout markers
"""

import pytest
from src.orchestration.task_board import TaskBoard, VALID_STATUSES


@pytest.fixture
def tb():
    """Fresh TaskBoard instance."""
    board = TaskBoard()
    yield board


@pytest.fixture
def cleanup_tasks(tb):
    """Track and cleanup test tasks."""
    created = []
    yield created
    for tid in created:
        try:
            tb.remove_task(tid)
        except Exception:
            pass


class TestScoutReconStatus:
    def test_scout_recon_in_valid_statuses(self):
        assert "scout_recon" in VALID_STATUSES

    def test_recon_done_in_valid_statuses(self):
        assert "recon_done" in VALID_STATUSES


class TestScoutHookTriggersOnAddTask:
    def test_task_with_allowed_paths_gets_scout_recon(self, tb, cleanup_tasks):
        tid = tb.add_task(
            "E2E: Scout triggers on allowed_paths",
            priority=5, phase_type="test",
            allowed_paths=["src/orchestration/task_board.py"],
            tags=["test-scout-e2e"],
        )
        cleanup_tasks.append(tid)
        task = tb.tasks[tid]
        assert task["status"] == "scout_recon"

    def test_scout_context_stored_in_task(self, tb, cleanup_tasks):
        tid = tb.add_task(
            "E2E: Scout context stored",
            priority=5, phase_type="test",
            allowed_paths=["src/orchestration/task_board.py"],
            tags=["test-scout-e2e"],
        )
        cleanup_tasks.append(tid)
        task = tb.tasks[tid]
        assert "scout_context" in task
        assert isinstance(task["scout_context"], list)
        assert len(task["scout_context"]) > 0

    def test_scout_context_has_required_fields(self, tb, cleanup_tasks):
        tid = tb.add_task(
            "E2E: Scout context fields",
            priority=5, phase_type="test",
            allowed_paths=["src/orchestration/task_board.py"],
            tags=["test-scout-e2e"],
        )
        cleanup_tasks.append(tid)
        ctx = tb.tasks[tid]["scout_context"][0]
        for field in ("file", "start_line", "end_line", "symbol", "snippet", "relevance"):
            assert field in ctx, f"Missing field: {field}"

    def test_implementation_hints_enriched(self, tb, cleanup_tasks):
        tid = tb.add_task(
            "E2E: Hints enriched by Scout",
            priority=5, phase_type="test",
            allowed_paths=["src/orchestration/task_board.py"],
            tags=["test-scout-e2e"],
        )
        cleanup_tasks.append(tid)
        hints = tb.tasks[tid].get("implementation_hints", "")
        assert "[Scout] Code locations:" in hints


class TestScoutHookEdgeCases:
    def test_task_without_allowed_paths_stays_pending(self, tb, cleanup_tasks):
        tid = tb.add_task(
            "E2E: No scope stays pending",
            priority=5, phase_type="test",
            tags=["test-scout-e2e"],
        )
        cleanup_tasks.append(tid)
        assert tb.tasks[tid]["status"] == "pending"

    def test_nonexistent_path_scout_still_safe(self, tb, cleanup_tasks):
        """Scout should not crash on nonexistent paths."""
        tid = tb.add_task(
            "E2E: Nonexistent path is safe",
            description="zzzzz_fake_function_name",
            priority=5, phase_type="test",
            allowed_paths=["src/nonexistent/fake_module.py"],
            tags=["test-scout-e2e"],
        )
        cleanup_tasks.append(tid)
        # Should not crash — status may be pending or scout_recon (fallback dirs)
        assert tb.tasks[tid]["status"] in ("pending", "scout_recon")


class TestSherpaIntegration:
    def test_scout_recon_tasks_visible_for_sherpa(self, tb, cleanup_tasks):
        """Sherpa polls scout_recon — these tasks must be findable."""
        tid = tb.add_task(
            "E2E: Visible for Sherpa",
            priority=5, phase_type="test",
            allowed_paths=["src/orchestration/task_board.py"],
            tags=["test-scout-e2e"],
        )
        cleanup_tasks.append(tid)
        scout_tasks = [
            t for t in tb.tasks.values()
            if t["status"] == "scout_recon" and t["id"] == tid
        ]
        assert len(scout_tasks) == 1
        assert "scout_context" in scout_tasks[0]
