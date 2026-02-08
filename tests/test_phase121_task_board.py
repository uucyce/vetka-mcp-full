"""
Phase 121: Task Board — Multi-Agent Task Queue

Tests:
- TestTaskBoardCRUD: add, get, update, remove tasks
- TestTaskBoardQueue: priority ordering, dependency resolution, next task
- TestTaskBoardImport: import from todo file, phase detection
- TestTaskBoardSummary: board summary counts
- TestMCPToolHandlers: MCP tool handler functions
- TestHeartbeatBoard: @board trigger pattern, phase type map
"""

import json
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock

import pytest

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.orchestration.task_board import TaskBoard, get_task_board, PRIORITY_HIGH, PRIORITY_MEDIUM, PRIORITY_LOW


# --- TestTaskBoardCRUD ---

class TestTaskBoardCRUD:
    """Test basic CRUD operations."""

    def setup_method(self):
        """Create fresh TaskBoard with temp file."""
        self.tmp = tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w")
        self.tmp.write('{"tasks": {}, "settings": {"max_concurrent": 2, "auto_dispatch": false, "default_preset": "dragon_silver"}}')
        self.tmp.close()
        self.board = TaskBoard(board_file=Path(self.tmp.name))

    def teardown_method(self):
        """Clean up temp file."""
        Path(self.tmp.name).unlink(missing_ok=True)

    def test_add_task(self):
        task_id = self.board.add_task("Fix bug", "Fix positioning", priority=2)
        assert task_id.startswith("tb_")
        assert task_id in self.board.tasks

    def test_add_task_defaults(self):
        task_id = self.board.add_task("Simple task")
        task = self.board.get_task(task_id)
        assert task["priority"] == PRIORITY_MEDIUM
        assert task["phase_type"] == "build"
        assert task["complexity"] == "medium"
        assert task["status"] == "pending"

    def test_get_task(self):
        task_id = self.board.add_task("Test task", description="Details")
        task = self.board.get_task(task_id)
        assert task is not None
        assert task["title"] == "Test task"
        assert task["description"] == "Details"

    def test_get_task_not_found(self):
        assert self.board.get_task("nonexistent") is None

    def test_update_task(self):
        task_id = self.board.add_task("Original title")
        ok = self.board.update_task(task_id, title="Updated title", priority=1)
        assert ok is True
        task = self.board.get_task(task_id)
        assert task["title"] == "Updated title"
        assert task["priority"] == 1

    def test_update_task_status(self):
        task_id = self.board.add_task("Task")
        ok = self.board.update_task(task_id, status="running")
        assert ok is True
        assert self.board.get_task(task_id)["status"] == "running"

    def test_update_task_invalid_status(self):
        task_id = self.board.add_task("Task")
        ok = self.board.update_task(task_id, status="invalid_status")
        assert ok is False

    def test_update_nonexistent(self):
        ok = self.board.update_task("fake_id", title="X")
        assert ok is False

    def test_remove_task(self):
        task_id = self.board.add_task("To remove")
        assert self.board.remove_task(task_id) is True
        assert self.board.get_task(task_id) is None

    def test_remove_nonexistent(self):
        assert self.board.remove_task("fake_id") is False

    def test_priority_clamped(self):
        task_id1 = self.board.add_task("Low", priority=0)
        task_id2 = self.board.add_task("High", priority=10)
        assert self.board.get_task(task_id1)["priority"] == 1
        assert self.board.get_task(task_id2)["priority"] == 5

    def test_persistence(self):
        """Tasks survive reload from disk."""
        task_id = self.board.add_task("Persistent task")
        board2 = TaskBoard(board_file=Path(self.tmp.name))
        assert board2.get_task(task_id) is not None
        assert board2.get_task(task_id)["title"] == "Persistent task"


# --- TestTaskBoardQueue ---

class TestTaskBoardQueue:
    """Test queue/priority operations."""

    def setup_method(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w")
        self.tmp.write('{"tasks": {}, "settings": {}}')
        self.tmp.close()
        self.board = TaskBoard(board_file=Path(self.tmp.name))

    def teardown_method(self):
        Path(self.tmp.name).unlink(missing_ok=True)

    def test_get_next_empty(self):
        assert self.board.get_next_task() is None

    def test_priority_ordering(self):
        """Higher priority (lower number) tasks come first."""
        self.board.add_task("Low priority", priority=4)
        self.board.add_task("Critical", priority=1)
        self.board.add_task("Medium", priority=3)

        next_task = self.board.get_next_task()
        assert next_task["title"] == "Critical"
        assert next_task["priority"] == 1

    def test_get_queue_filtered(self):
        id1 = self.board.add_task("Pending 1")
        id2 = self.board.add_task("Pending 2")
        self.board.update_task(id2, status="running")

        pending = self.board.get_queue(status="pending")
        assert len(pending) == 1
        assert pending[0]["id"] == id1

    def test_get_queue_all(self):
        self.board.add_task("Task 1")
        self.board.add_task("Task 2")
        all_tasks = self.board.get_queue()
        assert len(all_tasks) == 2

    def test_dependency_resolution(self):
        """Tasks with unsatisfied dependencies are skipped."""
        id1 = self.board.add_task("Dependency", priority=3)
        id2 = self.board.add_task("Dependent", priority=1, dependencies=[id1])
        id3 = self.board.add_task("Independent", priority=2)

        # Dependent task (P1) has unmet dependency, so Independent (P2) comes first
        next_task = self.board.get_next_task()
        assert next_task["id"] == id3

    def test_dependency_satisfied(self):
        """Once dependency is done, dependent task becomes available."""
        id1 = self.board.add_task("Dependency", priority=3)
        id2 = self.board.add_task("Dependent", priority=1, dependencies=[id1])

        # Mark dependency as done
        self.board.update_task(id1, status="done")

        next_task = self.board.get_next_task()
        assert next_task["id"] == id2

    def test_only_pending_dispatched(self):
        """Running tasks are not returned by get_next_task."""
        id1 = self.board.add_task("Running", priority=1)
        id2 = self.board.add_task("Pending", priority=2)
        self.board.update_task(id1, status="running")

        next_task = self.board.get_next_task()
        assert next_task["id"] == id2


# --- TestTaskBoardImport ---

class TestTaskBoardImport:
    """Test todo file import."""

    def setup_method(self):
        self.tmp_board = tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w")
        self.tmp_board.write('{"tasks": {}, "settings": {}}')
        self.tmp_board.close()
        self.board = TaskBoard(board_file=Path(self.tmp_board.name))

    def teardown_method(self):
        Path(self.tmp_board.name).unlink(missing_ok=True)

    def test_import_basic(self):
        """Import tasks from a simple todo file."""
        tmp_todo = tempfile.NamedTemporaryFile(suffix=".txt", delete=False, mode="w")
        tmp_todo.write("Fix: broken file import for single files\n")
        tmp_todo.write("Add star/favorite toggle to chat items\n")
        tmp_todo.write("Research how to categorize embedding models\n")
        tmp_todo.close()

        count = self.board.import_from_todo(tmp_todo.name, "test")
        assert count == 3
        assert len(self.board.tasks) == 3
        Path(tmp_todo.name).unlink()

    def test_import_fix_detection(self):
        """Lines with 'fix'/'broken' detected as phase_type=fix."""
        tmp_todo = tempfile.NamedTemporaryFile(suffix=".txt", delete=False, mode="w")
        tmp_todo.write("Fix broken file import for single files\n")
        tmp_todo.close()

        self.board.import_from_todo(tmp_todo.name, "test")
        tasks = list(self.board.tasks.values())
        assert len(tasks) == 1
        assert tasks[0]["phase_type"] == "fix"
        assert tasks[0]["priority"] == PRIORITY_HIGH
        Path(tmp_todo.name).unlink()

    def test_import_research_detection(self):
        """Lines with 'research'/'выяснить' detected as phase_type=research."""
        tmp_todo = tempfile.NamedTemporaryFile(suffix=".txt", delete=False, mode="w")
        tmp_todo.write("выяснить как использовать модели для поиска вроде tavily\n")
        tmp_todo.close()

        self.board.import_from_todo(tmp_todo.name, "test")
        tasks = list(self.board.tasks.values())
        assert len(tasks) == 1
        assert tasks[0]["phase_type"] == "research"
        Path(tmp_todo.name).unlink()

    def test_import_skips_short_lines(self):
        """Lines under 10 chars are skipped."""
        tmp_todo = tempfile.NamedTemporaryFile(suffix=".txt", delete=False, mode="w")
        tmp_todo.write("short\n")
        tmp_todo.write("\n")
        tmp_todo.write("This is a valid task description for import\n")
        tmp_todo.close()

        count = self.board.import_from_todo(tmp_todo.name, "test")
        assert count == 1
        Path(tmp_todo.name).unlink()

    def test_import_nonexistent_file(self):
        count = self.board.import_from_todo("/nonexistent/file.txt", "test")
        assert count == 0

    def test_import_source_tag(self):
        """Source tag is stored on imported tasks."""
        tmp_todo = tempfile.NamedTemporaryFile(suffix=".txt", delete=False, mode="w")
        tmp_todo.write("Add new feature to the system\n")
        tmp_todo.close()

        self.board.import_from_todo(tmp_todo.name, "dragon_todo")
        tasks = list(self.board.tasks.values())
        assert tasks[0]["source"] == "dragon_todo"
        Path(tmp_todo.name).unlink()


# --- TestTaskBoardSummary ---

class TestTaskBoardSummary:
    """Test board summary."""

    def setup_method(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w")
        self.tmp.write('{"tasks": {}, "settings": {}}')
        self.tmp.close()
        self.board = TaskBoard(board_file=Path(self.tmp.name))

    def teardown_method(self):
        Path(self.tmp.name).unlink(missing_ok=True)

    def test_empty_summary(self):
        summary = self.board.get_board_summary()
        assert summary["total"] == 0
        assert summary["next_task"] is None

    def test_summary_counts(self):
        id1 = self.board.add_task("Task 1")
        id2 = self.board.add_task("Task 2")
        id3 = self.board.add_task("Task 3")
        self.board.update_task(id2, status="done")
        self.board.update_task(id3, status="failed")

        summary = self.board.get_board_summary()
        assert summary["total"] == 3
        assert summary["by_status"]["pending"] == 1
        assert summary["by_status"]["done"] == 1
        assert summary["by_status"]["failed"] == 1

    def test_summary_next_task(self):
        self.board.add_task("Next task", priority=1)
        summary = self.board.get_board_summary()
        assert summary["next_task"] is not None
        assert summary["next_task"]["title"] == "Next task"


# --- TestMCPToolHandlers ---

class TestMCPToolHandlers:
    """Test MCP tool handler functions."""

    def setup_method(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w")
        self.tmp.write('{"tasks": {}, "settings": {}}')
        self.tmp.close()

    def teardown_method(self):
        Path(self.tmp.name).unlink(missing_ok=True)

    @patch("src.orchestration.task_board.get_task_board")
    def test_handle_add(self, mock_get_board):
        from src.mcp.tools.task_board_tools import handle_task_board
        board = TaskBoard(board_file=Path(self.tmp.name))
        mock_get_board.return_value = board

        result = handle_task_board({"action": "add", "title": "New task", "priority": 2})
        assert result["success"] is True
        assert "task_id" in result

    @patch("src.orchestration.task_board.get_task_board")
    def test_handle_add_no_title(self, mock_get_board):
        from src.mcp.tools.task_board_tools import handle_task_board
        board = TaskBoard(board_file=Path(self.tmp.name))
        mock_get_board.return_value = board

        result = handle_task_board({"action": "add"})
        assert result["success"] is False
        assert "title" in result["error"]

    @patch("src.orchestration.task_board.get_task_board")
    def test_handle_summary(self, mock_get_board):
        from src.mcp.tools.task_board_tools import handle_task_board
        board = TaskBoard(board_file=Path(self.tmp.name))
        board.add_task("Task 1")
        mock_get_board.return_value = board

        result = handle_task_board({"action": "summary"})
        assert result["success"] is True
        assert result["total"] == 1

    @patch("src.orchestration.task_board.get_task_board")
    def test_handle_list(self, mock_get_board):
        from src.mcp.tools.task_board_tools import handle_task_board
        board = TaskBoard(board_file=Path(self.tmp.name))
        board.add_task("Task 1")
        board.add_task("Task 2")
        mock_get_board.return_value = board

        result = handle_task_board({"action": "list"})
        assert result["success"] is True
        assert result["count"] == 2

    @patch("src.orchestration.task_board.get_task_board")
    def test_handle_unknown_action(self, mock_get_board):
        from src.mcp.tools.task_board_tools import handle_task_board
        board = TaskBoard(board_file=Path(self.tmp.name))
        mock_get_board.return_value = board

        result = handle_task_board({"action": "explode"})
        assert result["success"] is False

    def test_handle_no_action(self):
        from src.mcp.tools.task_board_tools import handle_task_board
        result = handle_task_board({})
        assert result["success"] is False

    @patch("src.orchestration.task_board.get_task_board")
    def test_handle_import(self, mock_get_board):
        from src.mcp.tools.task_board_tools import handle_task_import
        board = TaskBoard(board_file=Path(self.tmp.name))
        mock_get_board.return_value = board

        tmp_todo = tempfile.NamedTemporaryFile(suffix=".txt", delete=False, mode="w")
        tmp_todo.write("Fix broken import feature for files\n")
        tmp_todo.close()

        result = handle_task_import({"file_path": tmp_todo.name, "source_tag": "test"})
        assert result["success"] is True
        assert result["imported_count"] == 1
        Path(tmp_todo.name).unlink()


# --- TestHeartbeatBoard ---

class TestHeartbeatBoard:
    """Test @board trigger integration in heartbeat."""

    def test_board_pattern_exists(self):
        """@board pattern is registered in TASK_PATTERNS."""
        from src.orchestration.mycelium_heartbeat import TASK_PATTERNS
        patterns_str = [p.pattern for p in TASK_PATTERNS]
        assert any("board" in p.lower() for p in patterns_str)

    def test_board_phase_type(self):
        """@board maps to 'board' phase type."""
        from src.orchestration.mycelium_heartbeat import PHASE_TYPE_MAP
        assert PHASE_TYPE_MAP.get("board") == "board"

    def test_board_pattern_matches(self):
        """@board dispatch should match the pattern."""
        from src.orchestration.mycelium_heartbeat import TASK_PATTERNS
        board_pattern = [p for p in TASK_PATTERNS if "board" in p.pattern.lower()][0]
        match = board_pattern.search("@board dispatch")
        assert match is not None
        assert match.group(1).strip() == "dispatch"

    def test_board_list_command(self):
        """@board list should match the pattern."""
        from src.orchestration.mycelium_heartbeat import TASK_PATTERNS
        board_pattern = [p for p in TASK_PATTERNS if "board" in p.pattern.lower()][0]
        match = board_pattern.search("@board list")
        assert match is not None
        assert match.group(1).strip() == "list"
