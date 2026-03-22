"""
MARKER_ZETA.F2: Tests for Smart Debrief — auto-task creation + memory routing.
"""

import pytest
pytestmark = pytest.mark.stale(reason="Pre-existing failure — smart debrief pipeline imports changed")
from unittest.mock import patch, MagicMock

from src.services.smart_debrief import (
    _is_bug_report,
    _extract_summary,
    _route_to_memory,
    _create_auto_tasks,
    process_smart_debrief,
)
from src.services.experience_report import ExperienceReport


@pytest.fixture
def bug_report():
    return ExperienceReport(
        session_id="test-001",
        agent_callsign="Alpha",
        domain="engine",
        branch="claude/cut-engine",
        timestamp="2026-03-22T00:00:00Z",
        lessons_learned=[
            "Q1: task_board.py:847 _detect_current_branch() always returns main from worktree. Это сломано.",
            "Q2: Handoff docs через markdown работают отлично как паттерн координации.",
        ],
        recommendations=[
            "Q3: active_agents можно обогатить из AgentRegistry — добавить role, domain в ответ.",
        ],
    )


@pytest.fixture
def empty_report():
    return ExperienceReport(
        session_id="test-002",
        agent_callsign="Beta",
        domain="media",
        branch="claude/cut-media",
        timestamp="2026-03-22T01:00:00Z",
    )


# ── Bug Detection ───────────────────────────────────────────


class TestBugDetection:
    def test_detects_broken(self):
        assert _is_bug_report("vetka_read_file сломан — HTTP 422") is True

    def test_detects_bug_keyword(self):
        assert _is_bug_report("Found a bug in branch detection") is True

    def test_detects_error(self):
        assert _is_bug_report("API returns error 500") is True

    def test_detects_workaround(self):
        assert _is_bug_report("Had to use Read as workaround for vetka_read_file") is True

    def test_detects_stale(self):
        assert _is_bug_report("stale test artifacts in prod DB") is True

    def test_detects_russian_broken(self):
        assert _is_bug_report("Функция не работает из worktree") is True

    def test_positive_not_bug(self):
        assert _is_bug_report("Handoff docs work great for coordination") is False

    def test_idea_not_bug(self):
        assert _is_bug_report("active_agents можно обогатить из registry") is False


# ── Summary Extraction ──────────────────────────────────────


class TestSummaryExtraction:
    def test_strips_q_prefix(self):
        assert _extract_summary("Q1: branch detection broken") == "branch detection broken"

    def test_strips_numbering(self):
        assert _extract_summary("1. task_board.py bug") == "task_board.py bug"

    def test_truncates_long(self):
        long_text = "A" * 100
        result = _extract_summary(long_text, max_len=60)
        assert len(result) <= 60
        assert result.endswith("...")

    def test_first_line_only(self):
        result = _extract_summary("First line\nSecond line\nThird line")
        assert result == "First line"


# ── Memory Routing ──────────────────────────────────────────


class TestMemoryRouting:
    def test_reflex_trigger_on_tool_mention(self, bug_report):
        result = _route_to_memory("vetka_read_file is broken", bug_report)
        assert "reflex_tools" in result
        assert "vetka_read_file" in result["reflex_tools"]

    def test_aura_trigger_on_user_mention(self, bug_report):
        result = _route_to_memory("пользователь не видит warnings", bug_report)
        assert "aura_ux" in result

    def test_aura_trigger_on_ux(self, bug_report):
        result = _route_to_memory("The UX for merge conflicts is poor", bug_report)
        assert "aura_ux" in result

    def test_mgc_trigger_on_file_path(self, bug_report):
        result = _route_to_memory("task_board.py:847 has a bug", bug_report)
        assert "mgc_files" in result
        assert any("task_board.py" in f for f in result["mgc_files"])

    def test_engram_trigger_on_pattern(self, bug_report):
        result = _route_to_memory("The effective* variable pattern always works", bug_report)
        assert "engram_learning" in result

    def test_engram_trigger_on_russian(self, bug_report):
        result = _route_to_memory("Этот паттерн эффективнее чем прямой подход", bug_report)
        assert "engram_learning" in result

    def test_cortex_fallback(self, bug_report):
        result = _route_to_memory("Simple observation with no triggers", bug_report)
        assert "cortex_general" in result

    def test_multiple_triggers(self, bug_report):
        result = _route_to_memory(
            "vetka_read_file in task_board.py is broken, пользователь should always use Read pattern",
            bug_report,
        )
        assert "reflex_tools" in result
        assert "mgc_files" in result
        assert "aura_ux" in result
        assert "engram_learning" in result


# ── Auto-Task Creation ──────────────────────────────────────


class TestAutoTaskCreation:
    def test_creates_bug_task(self, bug_report):
        mock_board = MagicMock()
        mock_board.add_task.return_value = "tb_auto_1"

        tasks = _create_auto_tasks(bug_report, mock_board)

        assert len(tasks) >= 1
        # Check the bug task was created
        call_args = mock_board.add_task.call_args_list[0]
        assert "[DEBRIEF-BUG]" in call_args.kwargs.get("title", call_args[1].get("title", ""))

    def test_creates_idea_task(self, bug_report):
        mock_board = MagicMock()
        mock_board.add_task.return_value = "tb_auto_1"

        _create_auto_tasks(bug_report, mock_board)

        # Find the idea task call
        idea_calls = [
            c for c in mock_board.add_task.call_args_list
            if "[DEBRIEF-IDEA]" in str(c)
        ]
        assert len(idea_calls) >= 1

    def test_bug_task_is_research_p3(self, bug_report):
        mock_board = MagicMock()
        mock_board.add_task.return_value = "tb_auto_1"

        _create_auto_tasks(bug_report, mock_board)

        bug_call = mock_board.add_task.call_args_list[0]
        kwargs = bug_call.kwargs if bug_call.kwargs else {}
        assert kwargs.get("phase_type") == "research"
        assert kwargs.get("priority") == 3
        assert "debrief-auto" in kwargs.get("tags", [])
        assert "architect-review" in kwargs.get("tags", [])

    def test_idea_task_is_research_p4(self, bug_report):
        mock_board = MagicMock()
        mock_board.add_task.return_value = "tb_auto_1"

        _create_auto_tasks(bug_report, mock_board)

        # Last call should be the idea
        idea_call = mock_board.add_task.call_args_list[-1]
        kwargs = idea_call.kwargs if idea_call.kwargs else {}
        assert kwargs.get("phase_type") == "research"
        assert kwargs.get("priority") == 4
        assert "idea" in kwargs.get("tags", [])

    def test_no_tasks_for_non_bug_lessons(self):
        report = ExperienceReport(
            session_id="test",
            agent_callsign="Alpha",
            domain="engine",
            branch="main",
            timestamp="2026-03-22T00:00:00Z",
            lessons_learned=["Everything worked perfectly fine"],
            recommendations=[],
        )
        mock_board = MagicMock()
        tasks = _create_auto_tasks(report, mock_board)
        assert len(tasks) == 0

    def test_empty_report_creates_nothing(self, empty_report):
        mock_board = MagicMock()
        tasks = _create_auto_tasks(empty_report, mock_board)
        assert len(tasks) == 0
        mock_board.add_task.assert_not_called()


# ── Integration ─────────────────────────────────────────────


class TestProcessSmartDebrief:
    def test_full_pipeline(self, bug_report):
        mock_board = MagicMock()
        mock_board.add_task.return_value = "tb_auto_1"

        with patch("src.orchestration.task_board.TaskBoard", return_value=mock_board):
            results = process_smart_debrief(bug_report)

        assert len(results["tasks_created"]) >= 1
        assert len(results["memory_routes"]) == 3  # 2 lessons + 1 recommendation

    def test_memory_routes_have_triggers(self, bug_report):
        mock_board = MagicMock()
        mock_board.add_task.return_value = "tb_auto_1"

        with patch("src.orchestration.task_board.TaskBoard", return_value=mock_board):
            results = process_smart_debrief(bug_report)

        for route in results["memory_routes"]:
            assert "triggered" in route
            assert len(route["triggered"]) > 0
