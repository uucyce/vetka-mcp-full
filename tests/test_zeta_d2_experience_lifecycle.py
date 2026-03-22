"""
MARKER_ZETA.D2: Tests for Experience Lifecycle Guards.

Tests:
1. SessionActions — tasks_completed + experience_report_submitted tracking
2. ProtocolGuard — experience_report_after_task rule
3. ExperienceReportStore — submit, get, list, get_latest_for_role
4. Integration — session tracker records experience report tool call
"""

import json
import time

import pytest

from src.services.session_tracker import SessionActions, SessionActionTracker, reset_session_tracker
from src.services.protocol_guard import ProtocolGuard, ProtocolViolation, reset_protocol_guard
from src.services.experience_report import (
    ExperienceReport,
    ExperienceReportStore,
    reset_experience_store,
)


# ── Fixtures ────────────────────────────────────────────────


@pytest.fixture
def tracker():
    reset_session_tracker()
    return SessionActionTracker()


@pytest.fixture
def guard():
    reset_protocol_guard()
    return ProtocolGuard()


@pytest.fixture
def store(tmp_path):
    reset_experience_store()
    return ExperienceReportStore(reports_dir=tmp_path / "reports")


@pytest.fixture
def sample_report():
    return ExperienceReport(
        session_id="test-session-001",
        agent_callsign="Alpha",
        domain="engine",
        branch="claude/cut-engine",
        timestamp="2026-03-22T06:00:00Z",
        tasks_completed=["tb_001", "tb_002"],
        files_touched=["useTimelineInstanceStore.ts"],
        lessons_learned=["Three-Point Edit is THE NLE litmus test"],
        recommendations=["Read FCP7 PDF before coding"],
        bugs_found=[{"file": "DockviewLayout.tsx", "description": "Panel re-registration"}],
        commits=3,
        tests_added=5,
        tests_passing=40,
    )


# ── SessionActions Extension Tests ──────────────────────────


class TestSessionActionsExperience:
    def test_cold_session_has_zero_completed(self, tracker):
        session = tracker.get_session("s1")
        assert session.tasks_completed == 0
        assert session.experience_report_submitted is False
        assert session.experience_report_path is None

    def test_task_complete_increments_counter(self, tracker):
        tracker.record_action("s1", "vetka_task_board", {"action": "complete", "task_id": "tb_1"})
        session = tracker.get_session("s1")
        assert session.tasks_completed == 1

    def test_multiple_completes_accumulate(self, tracker):
        tracker.record_action("s1", "vetka_task_board", {"action": "complete", "task_id": "tb_1"})
        tracker.record_action("s1", "vetka_task_board", {"action": "complete", "task_id": "tb_2"})
        session = tracker.get_session("s1")
        assert session.tasks_completed == 2

    def test_experience_report_submission_recorded(self, tracker):
        tracker.record_action("s1", "vetka_submit_experience_report", {"report_path": "/tmp/r.json"})
        session = tracker.get_session("s1")
        assert session.experience_report_submitted is True
        assert session.experience_report_path == "/tmp/r.json"

    def test_claim_does_not_count_as_complete(self, tracker):
        tracker.record_action("s1", "vetka_task_board", {"action": "claim", "task_id": "tb_1"})
        session = tracker.get_session("s1")
        assert session.tasks_completed == 0
        assert session.task_claimed is True


# ── ProtocolGuard Experience Rule Tests ─────────────────────


class TestExperienceReportGuardRule:
    def _make_session(self, tasks_completed=0, report_submitted=False):
        s = SessionActions(session_id="test")
        s.session_init_called = True
        s.task_board_checked = True
        s.task_claimed = True
        s.roadmap_exists = True
        s.tasks_completed = tasks_completed
        s.experience_report_submitted = report_submitted
        return s

    def test_no_violation_when_no_tasks_completed(self, guard):
        session = self._make_session(tasks_completed=0)
        violations = guard.check_all_pending(session)
        rule_ids = [v.rule_id for v in violations]
        assert "experience_report_after_task" not in rule_ids

    def test_violation_when_tasks_completed_without_report(self, guard):
        session = self._make_session(tasks_completed=2)
        violations = guard.check_all_pending(session)
        rule_ids = [v.rule_id for v in violations]
        assert "experience_report_after_task" in rule_ids

    def test_violation_message_includes_count(self, guard):
        session = self._make_session(tasks_completed=3)
        violations = guard.check_all_pending(session)
        exp_v = [v for v in violations if v.rule_id == "experience_report_after_task"][0]
        assert "3 task(s)" in exp_v.message

    def test_no_violation_when_report_submitted(self, guard):
        session = self._make_session(tasks_completed=2, report_submitted=True)
        violations = guard.check_all_pending(session)
        rule_ids = [v.rule_id for v in violations]
        assert "experience_report_after_task" not in rule_ids

    def test_check_method_also_fires(self, guard):
        session = self._make_session(tasks_completed=1)
        violations = guard.check(session, "Edit", {"file_path": "src/foo.py"})
        rule_ids = [v.rule_id for v in violations]
        assert "experience_report_after_task" in rule_ids

    def test_severity_is_warn_by_default(self, guard):
        session = self._make_session(tasks_completed=1)
        violations = guard.check_all_pending(session)
        exp_v = [v for v in violations if v.rule_id == "experience_report_after_task"][0]
        assert exp_v.severity == "warn"


# ── ExperienceReportStore Tests ─────────────────────────────


class TestExperienceReportStore:
    def test_submit_creates_file(self, store, sample_report, tmp_path):
        path = store.submit(sample_report)
        assert path.exists()
        assert path.suffix == ".json"

    def test_submit_and_get_roundtrip(self, store, sample_report):
        store.submit(sample_report)
        loaded = store.get(sample_report.session_id)
        assert loaded is not None
        assert loaded.agent_callsign == "Alpha"
        assert loaded.domain == "engine"
        assert loaded.tasks_completed == ["tb_001", "tb_002"]
        assert loaded.lessons_learned == ["Three-Point Edit is THE NLE litmus test"]
        assert loaded.commits == 3

    def test_get_nonexistent_returns_none(self, store):
        assert store.get("nonexistent") is None

    def test_list_reports(self, store, sample_report):
        store.submit(sample_report)

        report2 = ExperienceReport(
            session_id="test-session-002",
            agent_callsign="Beta",
            domain="media",
            branch="claude/cut-media",
            timestamp="2026-03-22T07:00:00Z",
        )
        store.submit(report2)

        reports = store.list_reports()
        assert len(reports) == 2

    def test_list_reports_filter_by_callsign(self, store, sample_report):
        store.submit(sample_report)

        report2 = ExperienceReport(
            session_id="test-session-002",
            agent_callsign="Beta",
            domain="media",
            branch="claude/cut-media",
            timestamp="2026-03-22T07:00:00Z",
        )
        store.submit(report2)

        alpha_reports = store.list_reports(callsign="Alpha")
        assert len(alpha_reports) == 1
        assert alpha_reports[0]["agent_callsign"] == "Alpha"

    def test_list_reports_limit(self, store):
        for i in range(5):
            store.submit(ExperienceReport(
                session_id=f"session-{i}",
                agent_callsign="Alpha",
                domain="engine",
                branch="claude/cut-engine",
                timestamp=f"2026-03-22T0{i}:00:00Z",
            ))
        reports = store.list_reports(limit=3)
        assert len(reports) == 3

    def test_get_latest_for_role(self, store):
        store.submit(ExperienceReport(
            session_id="old",
            agent_callsign="Alpha",
            domain="engine",
            branch="claude/cut-engine",
            timestamp="2026-03-21T00:00:00Z",
        ))
        time.sleep(0.05)  # ensure mtime differs
        store.submit(ExperienceReport(
            session_id="new",
            agent_callsign="Alpha",
            domain="engine",
            branch="claude/cut-engine",
            timestamp="2026-03-22T00:00:00Z",
            lessons_learned=["latest lesson"],
        ))

        latest = store.get_latest_for_role("Alpha")
        assert latest is not None
        assert latest.session_id == "new"
        assert latest.lessons_learned == ["latest lesson"]

    def test_get_latest_for_role_none(self, store):
        assert store.get_latest_for_role("Omega") is None

    def test_report_json_structure(self, store, sample_report, tmp_path):
        path = store.submit(sample_report)
        with open(path) as f:
            data = json.load(f)
        assert data["session_id"] == "test-session-001"
        assert data["agent_callsign"] == "Alpha"
        assert "_saved_at" in data  # metadata field
        assert isinstance(data["bugs_found"], list)
        assert data["bugs_found"][0]["file"] == "DockviewLayout.tsx"


# ── Integration Tests ───────────────────────────────────────


class TestExperienceLifecycleIntegration:
    """Full lifecycle: claim → complete → guard fires → submit report → guard clears."""

    def test_full_lifecycle(self, tracker, guard, store, sample_report):
        sid = "lifecycle-test"

        # 1. Session init
        tracker.record_action(sid, "vetka_session_init", {})
        # 2. Check board
        tracker.record_action(sid, "vetka_task_board", {"action": "list"})
        # 3. Claim task
        tracker.record_action(sid, "vetka_task_board", {"action": "claim", "task_id": "tb_1"})
        # 4. Complete task
        tracker.record_action(sid, "vetka_task_board", {"action": "complete", "task_id": "tb_1"})

        session = tracker.get_session(sid)
        session.roadmap_exists = True

        # Guard should fire — task completed, no report
        violations = guard.check_all_pending(session)
        rule_ids = [v.rule_id for v in violations]
        assert "experience_report_after_task" in rule_ids

        # 5. Submit experience report
        tracker.record_action(sid, "vetka_submit_experience_report", {"report_path": "/tmp/r.json"})

        session = tracker.get_session(sid)
        # Guard should clear
        violations = guard.check_all_pending(session)
        rule_ids = [v.rule_id for v in violations]
        assert "experience_report_after_task" not in rule_ids
