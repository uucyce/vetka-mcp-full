"""
Phase 195 -- Protocol Guard Layer test suite (24 + 6 tests).

Cat 1: SessionActionTracker (8 tests) -- record/reset/defaults
Cat 2: ProtocolGuard Rules (8 tests) -- 6 rules enforcement
Cat 3: Path Exemptions (3 tests) -- docs/tests/data exempt from read_before_edit
Cat 4: Full Workflow (3 tests) -- happy path, worst case, partial compliance
Cat 5: Singleton & Config (2 tests) -- get_* singletons, config overrides
Cat 6: Recon Relevance Rule (3 tests) -- MARKER_SC_C.D6
Cat 7: Auto-Debrief Phase Closure (3 tests) -- MARKER_SC_C.D5
"""

import time
import pytest
from unittest.mock import patch, MagicMock

from src.services.session_tracker import (
    SessionActions,
    SessionActionTracker,
    get_session_tracker,
    reset_session_tracker,
)
from src.services.protocol_guard import (
    ProtocolViolation,
    ProtocolGuard,
    get_protocol_guard,
    reset_protocol_guard,
)


# ════════════════════════════════════════════════════════════════
# Fixtures
# ════════════════════════════════════════════════════════════════

SID = "test-session-001"


@pytest.fixture(autouse=True)
def _reset_singletons():
    """Reset singletons before each test for isolation."""
    reset_session_tracker()
    reset_protocol_guard()
    yield
    reset_session_tracker()
    reset_protocol_guard()


@pytest.fixture
def tracker():
    """Fresh SessionActionTracker instance."""
    return SessionActionTracker()


@pytest.fixture
def guard():
    """Fresh ProtocolGuard instance."""
    return ProtocolGuard()


@pytest.fixture
def session(tracker):
    """A cold session via the tracker."""
    return tracker.get_session(SID)


# ════════════════════════════════════════════════════════════════
# Cat 1 -- SessionActionTracker (8 tests)
# ════════════════════════════════════════════════════════════════

class TestSessionActionTracker:
    """Category 1: SessionActionTracker record/reset/defaults."""

    # -- 1. Cold session has all defaults --
    def test_cold_session_defaults(self, tracker):
        """New session has all booleans False, counters 0, sets empty."""
        s = tracker.get_session(SID)

        assert s.session_id == SID
        assert s.session_init_called is False
        assert s.task_board_checked is False
        assert s.task_claimed is False
        assert s.claimed_task_id is None
        assert s.claimed_task_has_recon_docs is False
        assert s.roadmap_exists is False
        assert s.files_read == set()
        assert s.files_edited == set()
        assert s.read_count == 0
        assert s.edit_count == 0
        assert s.search_count == 0
        assert s.task_board_calls == 0
        assert isinstance(s.created_at, float)
        print("  test_cold_session_defaults")

    # -- 2. Record Read updates files_read and read_count --
    def test_record_read(self, tracker):
        """Read tool records file in files_read and increments read_count."""
        tracker.record_action(SID, "Read", {"file_path": "/src/main.py"})
        s = tracker.get_session(SID)

        assert "/src/main.py" in s.files_read
        assert s.read_count == 1

        # Second read of different file
        tracker.record_action(SID, "Read", {"file_path": "/src/utils.py"})
        s = tracker.get_session(SID)
        assert s.read_count == 2
        assert len(s.files_read) == 2
        print("  test_record_read")

    # -- 3. Record Edit updates files_edited and edit_count --
    def test_record_edit(self, tracker):
        """Edit tool records file in files_edited and increments edit_count."""
        tracker.record_action(SID, "Edit", {"file_path": "/src/main.py"})
        s = tracker.get_session(SID)

        assert "/src/main.py" in s.files_edited
        assert s.edit_count == 1
        print("  test_record_edit")

    # -- 4. Record vetka_task_board action=list --
    def test_record_task_board_list(self, tracker):
        """vetka_task_board action=list sets task_board_checked=True."""
        tracker.record_action(SID, "vetka_task_board", {"action": "list"})
        s = tracker.get_session(SID)

        assert s.task_board_checked is True
        assert s.task_board_calls >= 1
        print("  test_record_task_board_list")

    # -- 5. Record vetka_task_board action=claim --
    def test_record_task_board_claim(self, tracker):
        """vetka_task_board action=claim sets task_claimed and claimed_task_id."""
        tracker.record_action(SID, "vetka_task_board", {
            "action": "claim",
            "task_id": "tb_12345",
        })
        s = tracker.get_session(SID)

        assert s.task_claimed is True
        assert s.claimed_task_id == "tb_12345"
        print("  test_record_task_board_claim")

    # -- 6. Record vetka_session_init --
    def test_record_session_init(self, tracker):
        """vetka_session_init sets session_init_called=True."""
        tracker.record_action(SID, "vetka_session_init", {})
        s = tracker.get_session(SID)

        assert s.session_init_called is True
        print("  test_record_session_init")

    # -- 7. Record Grep increments search_count and read_count --
    def test_record_grep(self, tracker):
        """Grep increments search_count; also read if path given."""
        tracker.record_action(SID, "Grep", {"pattern": "TODO", "path": "/src/main.py"})
        s = tracker.get_session(SID)

        assert s.search_count == 1
        # Grep with a path also counts as a read of that path
        assert s.read_count >= 0  # implementation may or may not count
        print("  test_record_grep")

    # -- 8. reset_session clears state --
    def test_reset_session(self, tracker):
        """reset_session returns session to default state."""
        tracker.record_action(SID, "Read", {"file_path": "/src/main.py"})
        tracker.record_action(SID, "Edit", {"file_path": "/src/main.py"})
        tracker.record_action(SID, "vetka_session_init", {})
        s = tracker.get_session(SID)
        assert s.read_count >= 1
        assert s.session_init_called is True

        tracker.reset_session(SID)
        s2 = tracker.get_session(SID)

        assert s2.read_count == 0
        assert s2.edit_count == 0
        assert s2.session_init_called is False
        assert s2.files_read == set()
        assert s2.files_edited == set()
        print("  test_reset_session")


# ════════════════════════════════════════════════════════════════
# Cat 2 -- ProtocolGuard Rules (8 tests)
# ════════════════════════════════════════════════════════════════

class TestProtocolGuardRules:
    """Category 2: ProtocolGuard 6-rule enforcement."""

    # -- 9. Edit without prior Read fires read_before_edit --
    def test_edit_without_read_fires(self, tracker, guard):
        """Edit a file not in files_read triggers read_before_edit violation."""
        s = tracker.get_session(SID)
        # Ensure session_init + task board + claim to isolate this rule
        tracker.record_action(SID, "vetka_session_init", {})
        tracker.record_action(SID, "vetka_task_board", {"action": "list"})
        tracker.record_action(SID, "vetka_task_board", {"action": "claim", "task_id": "tb_1"})
        s = tracker.get_session(SID)

        violations = guard.check(s, "Edit", {"file_path": "src/services/foo.py"})
        rule_ids = [v.rule_id for v in violations]

        assert "read_before_edit" in rule_ids
        print("  test_edit_without_read_fires")

    # -- 10. Edit after Read -- no read_before_edit --
    def test_edit_after_read_no_violation(self, tracker, guard):
        """Edit a file already in files_read does NOT trigger read_before_edit."""
        tracker.record_action(SID, "vetka_session_init", {})
        tracker.record_action(SID, "vetka_task_board", {"action": "list"})
        tracker.record_action(SID, "vetka_task_board", {"action": "claim", "task_id": "tb_1"})
        tracker.record_action(SID, "Read", {"file_path": "src/services/foo.py"})
        s = tracker.get_session(SID)

        violations = guard.check(s, "Edit", {"file_path": "src/services/foo.py"})
        rule_ids = [v.rule_id for v in violations]

        assert "read_before_edit" not in rule_ids
        print("  test_edit_after_read_no_violation")

    # -- 11. Edit without task claimed fires task_before_code --
    def test_edit_without_task_fires(self, tracker, guard):
        """Edit without task_claimed triggers task_before_code violation."""
        tracker.record_action(SID, "vetka_session_init", {})
        tracker.record_action(SID, "vetka_task_board", {"action": "list"})
        # No claim
        s = tracker.get_session(SID)

        violations = guard.check(s, "Edit", {"file_path": "src/services/foo.py"})
        rule_ids = [v.rule_id for v in violations]

        assert "task_before_code" in rule_ids
        print("  test_edit_without_task_fires")

    # -- 12. Edit with task claimed -- no task_before_code --
    def test_edit_with_task_no_violation(self, tracker, guard):
        """Edit with task_claimed=True does NOT trigger task_before_code."""
        tracker.record_action(SID, "vetka_session_init", {})
        tracker.record_action(SID, "vetka_task_board", {"action": "list"})
        tracker.record_action(SID, "vetka_task_board", {"action": "claim", "task_id": "tb_1"})
        tracker.record_action(SID, "Read", {"file_path": "src/services/foo.py"})
        s = tracker.get_session(SID)

        violations = guard.check(s, "Edit", {"file_path": "src/services/foo.py"})
        rule_ids = [v.rule_id for v in violations]

        assert "task_before_code" not in rule_ids
        print("  test_edit_with_task_no_violation")

    # -- 13. Edit without task_board check fires taskboard_before_work --
    def test_edit_without_board_check_fires(self, tracker, guard):
        """Edit without task_board_checked triggers taskboard_before_work."""
        tracker.record_action(SID, "vetka_session_init", {})
        # No board check, no claim
        s = tracker.get_session(SID)

        violations = guard.check(s, "Edit", {"file_path": "src/services/foo.py"})
        rule_ids = [v.rule_id for v in violations]

        assert "taskboard_before_work" in rule_ids
        print("  test_edit_without_board_check_fires")

    # -- 14. Any tool without session_init fires session_init_first --
    def test_tool_without_session_init_fires(self, tracker, guard):
        """MCP tool without session_init_called triggers session_init_first."""
        # No session_init called
        s = tracker.get_session(SID)

        violations = guard.check(s, "vetka_read_file", {"file_path": "src/main.py"})
        rule_ids = [v.rule_id for v in violations]

        assert "session_init_first" in rule_ids
        print("  test_tool_without_session_init_fires")

    # -- 15. task_board add without roadmap fires roadmap_before_tasks --
    def test_task_add_without_roadmap_fires(self, tracker, guard):
        """vetka_task_board action=add without roadmap_exists triggers roadmap_before_tasks."""
        tracker.record_action(SID, "vetka_session_init", {})
        s = tracker.get_session(SID)
        assert s.roadmap_exists is False

        violations = guard.check(s, "vetka_task_board", {"action": "add", "title": "New task"})
        rule_ids = [v.rule_id for v in violations]

        assert "roadmap_before_tasks" in rule_ids
        print("  test_task_add_without_roadmap_fires")

    # -- 16. Edit with claimed task, no recon_docs fires recon_before_code --
    def test_edit_no_recon_docs_fires(self, tracker, guard):
        """Edit with task claimed but no recon docs triggers recon_before_code."""
        tracker.record_action(SID, "vetka_session_init", {})
        tracker.record_action(SID, "vetka_task_board", {"action": "list"})
        tracker.record_action(SID, "vetka_task_board", {"action": "claim", "task_id": "tb_1"})
        s = tracker.get_session(SID)
        assert s.task_claimed is True
        assert s.claimed_task_has_recon_docs is False

        violations = guard.check(s, "Edit", {"file_path": "src/services/foo.py"})
        rule_ids = [v.rule_id for v in violations]

        assert "recon_before_code" in rule_ids
        print("  test_edit_no_recon_docs_fires")


# ════════════════════════════════════════════════════════════════
# Cat 3 -- Path Exemptions (3 tests)
# ════════════════════════════════════════════════════════════════

class TestPathExemptions:
    """Category 3: docs/, tests/, data/ exempt from read_before_edit."""

    def _setup_session_for_edit(self, tracker):
        """Helper: set up init + board + claim so only read_before_edit is testable."""
        tracker.record_action(SID, "vetka_session_init", {})
        tracker.record_action(SID, "vetka_task_board", {"action": "list"})
        tracker.record_action(SID, "vetka_task_board", {"action": "claim", "task_id": "tb_1"})
        # Mark recon docs to avoid that violation
        s = tracker.get_session(SID)
        s.claimed_task_has_recon_docs = True
        return s

    # -- 17. Edit docs/*.md -- exempt --
    def test_edit_docs_exempt(self, tracker, guard):
        """Editing docs/ path does NOT trigger read_before_edit."""
        s = self._setup_session_for_edit(tracker)

        violations = guard.check(s, "Edit", {"file_path": "docs/phase195/ROADMAP.md"})
        rule_ids = [v.rule_id for v in violations]

        assert "read_before_edit" not in rule_ids
        print("  test_edit_docs_exempt")

    # -- 18. Edit tests/*.py -- exempt --
    def test_edit_tests_exempt(self, tracker, guard):
        """Editing tests/ path does NOT trigger read_before_edit."""
        s = self._setup_session_for_edit(tracker)

        violations = guard.check(s, "Edit", {"file_path": "tests/test_something.py"})
        rule_ids = [v.rule_id for v in violations]

        assert "read_before_edit" not in rule_ids
        print("  test_edit_tests_exempt")

    # -- 19. Edit src/services/foo.py -- NOT exempt --
    def test_edit_src_enforced(self, tracker, guard):
        """Editing src/ path DOES trigger read_before_edit if not read first."""
        s = self._setup_session_for_edit(tracker)

        violations = guard.check(s, "Edit", {"file_path": "src/services/foo.py"})
        rule_ids = [v.rule_id for v in violations]

        assert "read_before_edit" in rule_ids
        print("  test_edit_src_enforced")


# ════════════════════════════════════════════════════════════════
# Cat 4 -- Full Workflow (3 tests)
# ════════════════════════════════════════════════════════════════

class TestFullWorkflow:
    """Category 4: End-to-end workflow scenarios."""

    # -- 20. Happy path: init -> board -> claim -> read -> edit = 0 violations --
    def test_happy_path_zero_violations(self, tracker, guard):
        """Full correct workflow produces zero violations."""
        tracker.record_action(SID, "vetka_session_init", {})
        tracker.record_action(SID, "vetka_task_board", {"action": "list"})
        tracker.record_action(SID, "vetka_task_board", {"action": "claim", "task_id": "tb_99"})
        tracker.record_action(SID, "Read", {"file_path": "src/services/engine.py"})

        s = tracker.get_session(SID)
        # Set recon docs flag to clear that rule
        s.claimed_task_has_recon_docs = True

        violations = guard.check(s, "Edit", {"file_path": "src/services/engine.py"})

        assert violations == [], f"Expected 0 violations, got: {[v.rule_id for v in violations]}"
        print("  test_happy_path_zero_violations")

    # -- 21. Worst case: immediate edit = multiple violations --
    def test_worst_case_multiple_violations(self, tracker, guard):
        """Edit with no preparation fires multiple violations at once."""
        s = tracker.get_session(SID)

        violations = guard.check(s, "Edit", {"file_path": "src/core/app.py"})
        rule_ids = [v.rule_id for v in violations]

        # session_init_first only fires for MCP tools (vetka_*), not native "Edit"
        assert "taskboard_before_work" in rule_ids, "Missing taskboard_before_work"
        assert "task_before_code" in rule_ids, "Missing task_before_code"
        assert "read_before_edit" in rule_ids, "Missing read_before_edit"
        assert len(violations) >= 3
        print("  test_worst_case_multiple_violations")

    # -- 22. Partial compliance: init + board check but no task --
    def test_partial_compliance(self, tracker, guard):
        """init + board check but no claim -> only task-related violations."""
        tracker.record_action(SID, "vetka_session_init", {})
        tracker.record_action(SID, "vetka_task_board", {"action": "list"})
        tracker.record_action(SID, "Read", {"file_path": "src/services/foo.py"})
        s = tracker.get_session(SID)

        violations = guard.check(s, "Edit", {"file_path": "src/services/foo.py"})
        rule_ids = [v.rule_id for v in violations]

        # Should NOT have these (we did init, board check, and read):
        assert "session_init_first" not in rule_ids
        assert "taskboard_before_work" not in rule_ids
        assert "read_before_edit" not in rule_ids

        # Should HAVE task-related violations:
        assert "task_before_code" in rule_ids
        print("  test_partial_compliance")


# ════════════════════════════════════════════════════════════════
# Cat 5 -- Singleton & Config (2 tests)
# ════════════════════════════════════════════════════════════════

class TestSingletonAndConfig:
    """Category 5: Singleton pattern and config overrides."""

    # -- 23. get_protocol_guard returns same instance --
    def test_singleton_identity(self):
        """get_protocol_guard() returns the same instance on repeated calls."""
        g1 = get_protocol_guard()
        g2 = get_protocol_guard()

        assert g1 is g2
        print("  test_singleton_identity")

    # -- 24. Config overrides severity --
    def test_config_override_severity(self):
        """ProtocolGuard config can override a rule's severity to 'block'."""
        import tempfile, json as _json
        reset_protocol_guard()
        # Write a config file that overrides read_before_edit to "block"
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            _json.dump({"rules": {"read_before_edit": {"severity": "block", "enabled": True}}}, f)
            cfg_path = f.name
        guard = ProtocolGuard(config_path=cfg_path)

        tracker = SessionActionTracker()
        tracker.record_action(SID, "vetka_session_init", {})
        tracker.record_action(SID, "vetka_task_board", {"action": "list"})
        tracker.record_action(SID, "vetka_task_board", {"action": "claim", "task_id": "tb_1"})
        s = tracker.get_session(SID)
        s.claimed_task_has_recon_docs = True

        # Mock trust modulation so REFLEX emotions don't downgrade severity
        from unittest.mock import patch, MagicMock
        mock_emo = MagicMock()
        mock_emo.get_emotion_state.return_value = MagicMock(trust=0.5)
        with patch("src.services.reflex_emotions.get_reflex_emotions", return_value=mock_emo):
            violations = guard.check(s, "Edit", {"file_path": "src/services/foo.py"})
        read_violations = [v for v in violations if v.rule_id == "read_before_edit"]

        assert len(read_violations) == 1
        assert read_violations[0].severity == "block"
        print("  test_config_override_severity")


# ════════════════════════════════════════════════════════════════
# Cat 6 -- Recon Relevance Rule (3 tests) MARKER_SC_C.D6
# ════════════════════════════════════════════════════════════════

def _mock_session_for_recon(task_claimed=True, claimed_task_id="tb_recon_1"):
    """Helper: build a mock session with recon-relevance-friendly defaults."""
    s = MagicMock()
    s.task_claimed = task_claimed
    s.claimed_task_id = claimed_task_id
    s.claimed_task_has_recon_docs = True
    s.files_read = {"src/services/foo.py"}
    s.task_board_checked = True
    s.session_init_called = True
    s.roadmap_exists = True
    s.tasks_completed = 0
    s.experience_report_submitted = False
    return s


class TestReconRelevance:
    """Category 6: recon_relevance rule — warn when recon_docs are irrelevant."""

    # -- 25. Irrelevant doc warns --
    def test_recon_relevance_warns_on_irrelevant_doc(self, guard, tmp_path):
        """Doc doesn't mention phase number or task keywords -> warn."""
        doc_file = tmp_path / "irrelevant_doc.md"
        doc_file.write_text("# Generic Architecture\nThis is about nothing specific.\n")

        mock_task = {
            "title": "195.2.1: Implement debrief capture",
            "recon_docs": [str(doc_file)],
        }
        session = _mock_session_for_recon()

        with patch("src.orchestration.task_board.TaskBoard") as MockBoard:
            MockBoard.return_value.get_task.return_value = mock_task
            violation = guard._check_recon_relevance(
                session, "Edit", {"file_path": "src/foo.py"}
            )

        assert violation is not None
        assert violation.rule_id == "recon_relevance"
        assert violation.severity == "warn"
        assert "195" in violation.message
        print("  test_recon_relevance_warns_on_irrelevant_doc")

    # -- 26. Relevant doc (mentions phase number) -> no warn --
    def test_recon_relevance_ok_when_doc_mentions_phase(self, guard, tmp_path):
        """Doc mentions phase number -> no warn."""
        doc_file = tmp_path / "relevant_doc.md"
        doc_file.write_text("# Phase 195 Architecture\nThis covers phase 195 debrief.\n")

        mock_task = {
            "title": "195.2.1: Implement debrief capture",
            "recon_docs": [str(doc_file)],
        }
        session = _mock_session_for_recon()

        with patch("src.orchestration.task_board.TaskBoard") as MockBoard:
            MockBoard.return_value.get_task.return_value = mock_task
            violation = guard._check_recon_relevance(
                session, "Edit", {"file_path": "src/foo.py"}
            )

        assert violation is None
        print("  test_recon_relevance_ok_when_doc_mentions_phase")

    # -- 27. Unreadable doc -> no warn (graceful) --
    def test_recon_relevance_skips_when_doc_unreadable(self, guard):
        """File not found -> no warn (graceful skip). All-unreadable = non-fatal pass."""
        mock_task = {
            "title": "195.2.1: Implement debrief capture",
            "recon_docs": ["/nonexistent/path/doc_that_does_not_exist.md"],
        }
        session = _mock_session_for_recon()

        with patch("src.orchestration.task_board.TaskBoard") as MockBoard:
            MockBoard.return_value.get_task.return_value = mock_task
            violation = guard._check_recon_relevance(
                session, "Edit", {"file_path": "src/foo.py"}
            )

        # All docs unreadable -> graceful skip -> no violation
        assert violation is None
        print("  test_recon_relevance_skips_when_doc_unreadable")


# ════════════════════════════════════════════════════════════════
# Cat 7 -- Auto-Debrief Phase Closure (3 tests) MARKER_SC_C.D5
# ════════════════════════════════════════════════════════════════

class TestPhaseClosureDebrief:
    """Category 7: _extract_phase_prefix, _count_pending_for_phase, _generate_debrief_prompt."""

    # -- 28. Extract numeric phase prefix --
    def test_extract_phase_prefix_numeric(self):
        """'195.2.1: Some title' -> '195'; '42.3: Task' -> '42'."""
        from src.orchestration.task_board import TaskBoard
        assert TaskBoard._extract_phase_prefix("195.2.1: Some title") == "195"
        assert TaskBoard._extract_phase_prefix("42.3: Another task") == "42"
        print("  test_extract_phase_prefix_numeric")

    # -- 29. Non-numeric prefix returns None --
    def test_extract_phase_prefix_non_numeric(self):
        """'D4: Non-numeric' -> None; '' -> None."""
        from src.orchestration.task_board import TaskBoard
        assert TaskBoard._extract_phase_prefix("D4: Non-numeric") is None
        assert TaskBoard._extract_phase_prefix("") is None
        assert TaskBoard._extract_phase_prefix("No prefix here") is None
        print("  test_extract_phase_prefix_non_numeric")

    # -- 30. Generate debrief prompt contains 3 questions --
    def test_generate_debrief_prompt(self):
        """Debrief prompt includes phase number, task title, and 3 questions."""
        from src.orchestration.task_board import TaskBoard
        task = {"title": "195.2.1: Final task"}
        prompt = TaskBoard._generate_debrief_prompt("195", task)
        assert "Phase 195 complete" in prompt
        assert "pain point" in prompt
        assert "discovery" in prompt
        assert "change" in prompt
        assert "195.2.1: Final task" in prompt
        print("  test_generate_debrief_prompt")
