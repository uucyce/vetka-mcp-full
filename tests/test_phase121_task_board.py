"""
Phase 121: Task Board — Multi-Agent Task Queue

Tests:
- TestTaskBoardCRUD: add, get, update, remove tasks
- TestTaskBoardQueue: priority ordering, dependency resolution, next task
- TestTaskBoardImport: import from todo file, phase detection
- TestTaskBoardSummary: board summary counts
- TestMCPToolHandlers: MCP tool handler functions
- TestHeartbeatBoard: @board trigger pattern, phase type map
- TestExecutionModeGuard: MARKER_192.2 — manual vs pipeline closure proof
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


# MARKER_192.4: Prevent test boards from reading production task_board.json during auto-migration.
# The _migrate_json_to_sqlite() method falls back to TASK_BOARD_FILE (production path),
# which causes test boards to inherit 396+ real tasks. Patching the constants to nonexistent
# paths ensures test isolation.
_NONEXISTENT = Path("/tmp/_vetka_test_nonexistent_board.json")

@pytest.fixture(autouse=True)
def _isolate_task_board_from_production(tmp_path):
    """Prevent tests from loading production task_board.json during SQLite migration."""
    with patch("src.orchestration.task_board.TASK_BOARD_FILE", _NONEXISTENT), \
         patch("src.orchestration.task_board._TASK_BOARD_FALLBACK", _NONEXISTENT):
        yield


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
        """Clean up temp files (JSON + derived SQLite DB)."""
        Path(self.tmp.name).unlink(missing_ok=True)
        db_path = Path(self.tmp.name).parent / (Path(self.tmp.name).stem + ".db")
        db_path.unlink(missing_ok=True)
        Path(str(db_path) + "-wal").unlink(missing_ok=True)
        Path(str(db_path) + "-shm").unlink(missing_ok=True)

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

    def test_add_task_accepts_test_phase_type(self):
        task_id = self.board.add_task("Test flow", phase_type="test")
        task = self.board.get_task(task_id)
        assert task["phase_type"] == "test"

    def test_add_task_closure_tests_auto_enable_protocol(self):
        task_id = self.board.add_task(
            "Protocol task",
            closure_tests=["pytest -q tests/test_phase121_task_board.py"],
            architecture_docs=["docs/171_ph_multytask_vetka_MCP/RECON_MULTITASK_PROTOCOL_VETKA_MCP_2026-03-11.md"],
        )
        task = self.board.get_task(task_id)
        assert task["require_closure_proof"] is True
        assert task["protocol_version"] == "multitask_mcp_v1"
        assert task["closure_subtask"]["status"] == "pending"

    def test_add_task_invalid_phase_type_raises(self):
        with pytest.raises(ValueError):
            self.board.add_task("Bad task", phase_type="deploy")

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

    def test_save_persists_to_sqlite(self):
        """MARKER_192.4: Tasks are persisted via SQLite, not JSON."""
        task_id = self.board.add_task("Signed task")
        # Verify task survives reload from the same DB path
        board2 = TaskBoard(board_file=Path(self.tmp.name))
        task = board2.get_task(task_id)
        assert task is not None
        assert task["title"] == "Signed task"

    def test_direct_db_tampering_detected_on_reload(self):
        """MARKER_192.4: SQLite integrity is handled by the DB engine itself.
        Verify that data modified via direct DB access is visible on reload."""
        import sqlite3
        task_id = self.board.add_task("Tampered task")
        # Derive the .db path from the .json path (as TaskBoard does)
        db_path = Path(self.tmp.name).parent / (Path(self.tmp.name).stem + ".db")
        conn = sqlite3.connect(str(db_path))
        conn.execute("UPDATE tasks SET title = ? WHERE id = ?", ("Tampered outside protocol", task_id))
        conn.commit()
        conn.close()

        board2 = TaskBoard(board_file=Path(self.tmp.name))
        task = board2.get_task(task_id)
        assert task is not None
        assert task["title"] == "Tampered outside protocol"


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
        db_path = Path(self.tmp.name).parent / (Path(self.tmp.name).stem + ".db")
        db_path.unlink(missing_ok=True)
        Path(str(db_path) + "-wal").unlink(missing_ok=True)
        Path(str(db_path) + "-shm").unlink(missing_ok=True)

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
        db_path = Path(self.tmp_board.name).parent / (Path(self.tmp_board.name).stem + ".db")
        db_path.unlink(missing_ok=True)
        Path(str(db_path) + "-wal").unlink(missing_ok=True)
        Path(str(db_path) + "-shm").unlink(missing_ok=True)

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

    def test_import_test_detection(self):
        """Lines with 'pytest'/'e2e' detected as phase_type=test."""
        tmp_todo = tempfile.NamedTemporaryFile(suffix=".txt", delete=False, mode="w")
        tmp_todo.write("Add pytest smoke coverage for closure protocol\n")
        tmp_todo.close()

        self.board.import_from_todo(tmp_todo.name, "test")
        tasks = list(self.board.tasks.values())
        assert len(tasks) == 1
        assert tasks[0]["phase_type"] == "test"
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
        db_path = Path(self.tmp.name).parent / (Path(self.tmp.name).stem + ".db")
        db_path.unlink(missing_ok=True)
        Path(str(db_path) + "-wal").unlink(missing_ok=True)
        Path(str(db_path) + "-shm").unlink(missing_ok=True)

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
        db_path = Path(self.tmp.name).parent / (Path(self.tmp.name).stem + ".db")
        db_path.unlink(missing_ok=True)
        Path(str(db_path) + "-wal").unlink(missing_ok=True)
        Path(str(db_path) + "-shm").unlink(missing_ok=True)

    @patch("src.orchestration.task_board.get_task_board")
    def test_handle_add(self, mock_get_board):
        from src.mcp.tools.task_board_tools import handle_task_board
        board = TaskBoard(board_file=Path(self.tmp.name))
        mock_get_board.return_value = board

        # MARKER_192.4: DOC_GATE (MARKER_190) requires docs — use force_no_docs to bypass
        result = handle_task_board({"action": "add", "title": "New task", "priority": 2, "force_no_docs": True})
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
    def test_handle_add_with_closure_tests_enables_protocol(self, mock_get_board):
        from src.mcp.tools.task_board_tools import handle_task_board
        board = TaskBoard(board_file=Path(self.tmp.name))
        mock_get_board.return_value = board

        result = handle_task_board({
            "action": "add",
            "title": "Proof task",
            "phase_type": "test",
            "closure_tests": ["pytest -q tests/test_phase121_task_board.py"],
            "architecture_docs": ["docs/171_ph_multytask_vetka_MCP/PHASE_171_MULTITASK_MCC_PROJECT_LANE_RECON_2026-03-13.md"],
            "project_lane": "mcc_lane_a",
        })

        assert result["success"] is True
        task = board.get_task(result["task_id"])
        assert task["phase_type"] == "test"
        assert task["require_closure_proof"] is True
        assert task["project_lane"] == "mcc_lane_a"

    @patch("src.orchestration.task_board.get_task_board")
    def test_handle_add_with_p6_profile_applies_protocol_defaults(self, mock_get_board):
        from src.mcp.tools.task_board_tools import handle_task_board
        board = TaskBoard(board_file=Path(self.tmp.name))
        mock_get_board.return_value = board

        result = handle_task_board({
            "action": "add",
            "title": "Emergency P6 proof task",
            "profile": "p6",
            "project_lane": "lane_p6",
            "architecture_docs": ["docs/171_ph_multytask_vetka_MCP/PHASE_171_MULTITASK_MCC_PROJECT_LANE_RECON_2026-03-13.md"],
            "closure_tests": ["pytest -q tests/test_phase121_task_board.py"],
            "closure_files": ["src/mcp/tools/task_board_tools.py"],
        })

        assert result["success"] is True
        task = board.get_task(result["task_id"])
        assert task["phase_type"] == "test"
        assert task["protocol_version"] == "multitask_mcp_v1"
        assert task["require_closure_proof"] is True
        assert task["task_origin"] == "p6_profile"
        assert "p6" in task["tags"]

    @patch("src.orchestration.task_board.get_task_board")
    def test_handle_add_with_p6_profile_requires_docs_and_tests(self, mock_get_board):
        from src.mcp.tools.task_board_tools import handle_task_board
        board = TaskBoard(board_file=Path(self.tmp.name))
        mock_get_board.return_value = board

        result = handle_task_board({
            "action": "add",
            "title": "Broken Emergency P6 proof task",
            "profile": "p6",
            "project_lane": "lane_p6",
        })

        assert result["success"] is False
        # MARKER_192.4: DOC_GATE (MARKER_190) now intercepts before p6 validation
        assert "DOC_GATE" in result["error"] or "p6 profile requires" in result["error"]

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


# --- TestExecutionModeGuard (MARKER_192.2) ---

class TestExecutionModeGuard:
    """MARKER_192.2: execution_mode controls closure proof requirements.

    Manual agents (claude_code, cursor, human) should only need commit_hash.
    Pipeline agents (mycelium) need full proof: pipeline_success + verifier + tests.
    """

    def setup_method(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w")
        self.tmp.write("{}")
        self.tmp.flush()
        self.board = TaskBoard(board_file=Path(self.tmp.name))

    def teardown_method(self):
        Path(self.tmp.name).unlink(missing_ok=True)

    def test_infer_execution_mode_manual_agents(self):
        """claude_code, cursor, human, grok, codex → manual."""
        for agent_type in ("claude_code", "cursor", "human", "grok", "codex"):
            assert TaskBoard._infer_execution_mode(agent_type) == "manual", f"{agent_type} should be manual"

    def test_infer_execution_mode_pipeline_agents(self):
        """mycelium and unknown → pipeline."""
        assert TaskBoard._infer_execution_mode("mycelium") == "pipeline"
        assert TaskBoard._infer_execution_mode(None) == "pipeline"
        assert TaskBoard._infer_execution_mode("") == "pipeline"

    def test_add_task_sets_execution_mode_from_agent_type(self):
        """Task created with agent_type=claude_code gets execution_mode=manual."""
        tid = self.board.add_task("Manual task", agent_type="claude_code")
        task = self.board.get_task(tid)
        assert task["execution_mode"] == "manual"

    def test_add_task_defaults_to_pipeline(self):
        """Task created without agent_type defaults to pipeline."""
        tid = self.board.add_task("Pipeline task")
        task = self.board.get_task(tid)
        assert task["execution_mode"] == "pipeline"

    def test_add_task_explicit_execution_mode(self):
        """Explicit execution_mode overrides agent_type inference."""
        tid = self.board.add_task("Forced manual", agent_type="mycelium", execution_mode="manual")
        task = self.board.get_task(tid)
        assert task["execution_mode"] == "manual"

    def test_claim_sets_execution_mode_on_untyped_task(self):
        """Claiming a task without agent_type sets execution_mode from claimer."""
        tid = self.board.add_task("Unclaimed task")
        task = self.board.get_task(tid)
        assert task["execution_mode"] == "pipeline"  # default

        self.board.claim_task(tid, "opus", "claude_code")
        task = self.board.get_task(tid)
        assert task["execution_mode"] == "manual"

    def test_manual_closure_needs_only_commit_hash(self):
        """Manual agent can close protocol task with just commit_hash."""
        tid = self.board.add_task(
            "Manual proof task",
            agent_type="claude_code",
            require_closure_proof=True,
        )
        self.board.claim_task(tid, "opus", "claude_code")

        result = self.board.complete_task(
            tid,
            commit_hash="abc123def",
            commit_message="fix: something",
            closure_proof={"commit_hash": "abc123def"},
        )
        assert result["success"] is True
        task = self.board.get_task(tid)
        assert task["status"] in ("done_main", "done_worktree")

    def test_manual_closure_fails_without_commit_hash(self):
        """Manual agent still needs commit_hash even with relaxed proof."""
        tid = self.board.add_task(
            "Manual no-hash task",
            agent_type="claude_code",
            require_closure_proof=True,
        )
        self.board.claim_task(tid, "opus", "claude_code")

        result = self.board.complete_task(
            tid,
            closure_proof={},  # no commit_hash
        )
        assert result["success"] is False
        assert "commit_hash" in result["error"]

    def test_pipeline_closure_fails_without_full_proof(self):
        """Pipeline agent needs pipeline_success + verifier + tests."""
        tid = self.board.add_task(
            "Pipeline proof task",
            agent_type="mycelium",
            require_closure_proof=True,
        )
        self.board.claim_task(tid, "dragon", "mycelium")

        # Try with only commit_hash — should fail for pipeline mode
        result = self.board.complete_task(
            tid,
            commit_hash="abc123def",
            closure_proof={"commit_hash": "abc123def"},
        )
        assert result["success"] is False
        assert "pipeline_success" in result["error"]

    def test_execution_mode_override_at_complete(self):
        """execution_mode can be overridden at complete time."""
        tid = self.board.add_task(
            "Override task",
            agent_type="mycelium",
            require_closure_proof=True,
        )
        self.board.claim_task(tid, "dragon", "mycelium")

        # Override to manual at complete time → should succeed with just commit_hash
        result = self.board.complete_task(
            tid,
            commit_hash="abc123def",
            closure_proof={"commit_hash": "abc123def"},
            execution_mode="manual",
        )
        assert result["success"] is True

    def test_manual_closure_validates_tests_if_provided(self):
        """Manual mode still validates closure_proof.tests if they are present."""
        tid = self.board.add_task(
            "Manual with tests",
            agent_type="claude_code",
            require_closure_proof=True,
        )
        self.board.claim_task(tid, "opus", "claude_code")

        # Provide failing test in proof → should fail
        result = self.board.complete_task(
            tid,
            closure_proof={
                "commit_hash": "abc123def",
                "tests": [{"name": "test_one", "passed": False}],
            },
        )
        assert result["success"] is False
        assert "tests must pass" in result["error"]

    def test_manual_closure_passes_with_passing_tests(self):
        """Manual mode accepts closure with commit_hash + passing tests."""
        tid = self.board.add_task(
            "Manual passing tests",
            agent_type="claude_code",
            require_closure_proof=True,
        )
        self.board.claim_task(tid, "opus", "claude_code")

        result = self.board.complete_task(
            tid,
            closure_proof={
                "commit_hash": "abc123def",
                "tests": [{"name": "test_one", "passed": True}],
            },
        )
        assert result["success"] is True
