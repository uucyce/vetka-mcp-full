"""
MARKER_ZETA.F2+F4: Tests for Smart Debrief — auto-task creation + wired memory routing.
"""

import pytest
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


# ── F4: Wired Memory Routing Tests ────────────────────────────


@pytest.fixture
def f4_report():
    return ExperienceReport(
        session_id="test-f4",
        agent_callsign="Zeta",
        domain="engine",
        branch="claude/cut-engine",
        timestamp="2026-03-23T00:00:00Z",
    )


@pytest.fixture
def mock_reflex():
    with patch("src.services.reflex_feedback.get_reflex_feedback") as m:
        fb = MagicMock()
        m.return_value = fb
        yield fb


@pytest.fixture
def mock_mgc():
    with patch("src.memory.mgc_cache.get_mgc_cache") as m:
        mgc = MagicMock()
        m.return_value = mgc
        yield mgc


@pytest.fixture
def mock_engram():
    with patch("src.memory.engram_cache.get_engram_cache") as m:
        cache = MagicMock()
        m.return_value = cache
        yield cache


class TestMemoryRoutingWired:
    """MARKER_195.21/F4: _route_to_memory with real subsystem writes."""

    def test_reflex_negative(self, f4_report, mock_reflex):
        _route_to_memory("vetka_read_file сломан — HTTP 422", f4_report)
        mock_reflex.record.assert_called_once()
        kw = mock_reflex.record.call_args.kwargs
        assert kw["tool_id"] == "vetka_read_file"
        assert kw["success"] is False
        assert kw["agent_role"] == "debrief"

    def test_reflex_positive(self, f4_report, mock_reflex):
        _route_to_memory("Read tool works great for large files", f4_report)
        kw = mock_reflex.record.call_args.kwargs
        assert kw["tool_id"] == "Read"
        assert kw["success"] is True

    def test_reflex_multiple_tools(self, f4_report, mock_reflex):
        _route_to_memory("vetka_read_file and Bash both useful", f4_report)
        assert mock_reflex.record.call_count == 2

    def test_aura_viewport(self, f4_report, mock_engram):
        """MARKER_195.22: UX insights routed to ENGRAM (not AURA) with ux_viewport category."""
        _route_to_memory("пользователь не видит warnings в UI", f4_report)
        kw = mock_engram.put.call_args.kwargs
        assert kw["category"] == "ux_viewport"
        assert len(kw["value"]) <= 500
        assert "ux_insight" in kw["key"]

    def test_aura_communication(self, f4_report, mock_engram):
        """MARKER_195.22: User mentions without UI/UX → ux_communication category in ENGRAM."""
        _route_to_memory("user prefers русский в ответах", f4_report)
        kw = mock_engram.put.call_args.kwargs
        assert kw["category"] == "ux_communication"

    def test_mgc_hot_file(self, f4_report, mock_mgc):
        _route_to_memory("task_board.py:847 has a bug", f4_report)
        kw = mock_mgc.set_sync.call_args.kwargs
        assert kw["key"].startswith("debrief_hot:")
        assert "task_board.py" in kw["key"]
        assert kw["size_bytes"] == 0

    def test_mgc_multiple_files(self, f4_report, mock_mgc):
        _route_to_memory("task_board.py and session_tools.py need fix", f4_report)
        assert mock_mgc.set_sync.call_count == 2

    def test_engram_architecture(self, f4_report, mock_engram):
        _route_to_memory("Принцип: always pass branch= from worktree", f4_report)
        kw = mock_engram.put.call_args.kwargs
        assert kw["category"] == "architecture"
        assert len(kw["value"]) <= 300
        assert kw["match_count"] == 0

    def test_engram_pattern(self, f4_report, mock_engram):
        _route_to_memory("Этот паттерн координации через markdown эффективнее", f4_report)
        kw = mock_engram.put.call_args.kwargs
        assert kw["category"] == "pattern"

    def test_cortex_fallback(self, f4_report, mock_reflex):
        _route_to_memory("Simple observation about the project", f4_report)
        kw = mock_reflex.record.call_args.kwargs
        assert kw["tool_id"] == "__general_debrief__"

    def test_crash_does_not_propagate(self, f4_report):
        with patch("src.services.reflex_feedback.get_reflex_feedback", side_effect=RuntimeError("down")):
            result = _route_to_memory("vetka_read_file broken", f4_report)
        assert "reflex_tools" in result

    def test_text_truncation(self, f4_report, mock_reflex, mock_engram):
        long_text = "vetka_read_file " + "x" * 1000 + " always apply this pattern"
        _route_to_memory(long_text, f4_report)
        assert len(mock_reflex.record.call_args.kwargs["extra"]["text"]) <= 200
        assert len(mock_engram.put.call_args.kwargs["value"]) <= 300

    def test_multiple_subsystems(self, f4_report, mock_reflex, mock_mgc, mock_engram):
        """MARKER_195.22: All subsystems fire on text with multiple triggers."""
        text = "vetka_read_file in task_board.py — пользователь should always use this pattern"
        result = _route_to_memory(text, f4_report)
        assert "reflex_tools" in result
        assert "aura_ux" in result
        assert "mgc_files" in result
        assert "engram_learning" in result
        mock_reflex.record.assert_called()
        # AURA now routes through ENGRAM (MARKER_195.22)
        mock_mgc.set_sync.assert_called()
        mock_engram.put.assert_called()
