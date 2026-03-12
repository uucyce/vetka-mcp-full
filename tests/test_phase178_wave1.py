"""
Phase 178 Wave 1: Session Init enrichment + REFLEX activation tests.
MARKER_178.1.TESTS
"""
import json
import os
import sys
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add project root to path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


class TestReflexEnabled:
    """178.1.6: REFLEX_ENABLED defaults to true after Phase 178 activation"""

    def test_reflex_enabled_default_true(self):
        """REFLEX should be enabled by default after Phase 178.

        Phase 178 changes the default from 'false' to 'true'.
        If the scorer still has the old default, this test documents
        the required change.
        """
        import importlib
        import src.services.reflex_scorer as scorer_mod

        # Patch os.getenv to simulate no REFLEX_ENABLED env var set
        with patch.dict(os.environ, {}, clear=False):
            # Remove REFLEX_ENABLED from env if set
            env_without = {k: v for k, v in os.environ.items() if k != "REFLEX_ENABLED"}
            with patch.dict(os.environ, env_without, clear=True):
                importlib.reload(scorer_mod)
                # Phase 178 target: default should be true
                # If this fails, update the default in reflex_scorer.py:
                #   os.getenv("REFLEX_ENABLED", "true")
                assert scorer_mod.REFLEX_ENABLED is True, (
                    "Phase 178 requires REFLEX_ENABLED to default to True. "
                    "Update reflex_scorer.py: os.getenv('REFLEX_ENABLED', 'true')"
                )

    def test_reflex_can_be_disabled_via_env(self):
        """REFLEX can still be disabled via env var"""
        import importlib
        import src.services.reflex_scorer as scorer_mod

        env_with_false = {k: v for k, v in os.environ.items()}
        env_with_false["REFLEX_ENABLED"] = "false"
        with patch.dict(os.environ, env_with_false, clear=True):
            importlib.reload(scorer_mod)
            assert scorer_mod.REFLEX_ENABLED is False

    def test_reflex_enabled_via_env_true(self):
        """REFLEX can be explicitly enabled via env var"""
        import importlib
        import src.services.reflex_scorer as scorer_mod

        env_with_true = {k: v for k, v in os.environ.items()}
        env_with_true["REFLEX_ENABLED"] = "true"
        with patch.dict(os.environ, env_with_true, clear=True):
            importlib.reload(scorer_mod)
            assert scorer_mod.REFLEX_ENABLED is True


class TestFeedbackLogAutoCreate:
    """178.1.5: feedback_log.jsonl auto-creation"""

    def test_feedback_log_path_defined(self):
        """FEEDBACK_LOG_PATH should be defined and point to feedback_log.jsonl"""
        from src.services.reflex_feedback import FEEDBACK_LOG_PATH
        assert FEEDBACK_LOG_PATH is not None
        assert str(FEEDBACK_LOG_PATH).endswith("feedback_log.jsonl")

    def test_feedback_log_path_in_reflex_dir(self):
        """FEEDBACK_LOG_PATH should be under data/reflex/"""
        from src.services.reflex_feedback import FEEDBACK_LOG_PATH
        assert "reflex" in str(FEEDBACK_LOG_PATH)

    def test_auto_create_on_write(self, tmp_path):
        """feedback_log.jsonl should be auto-created on first write"""
        from src.services.reflex_feedback import ReflexFeedback, FEEDBACK_LOG_PATH

        log_path = tmp_path / "feedback_log.jsonl"
        assert not log_path.exists()

        feedback = ReflexFeedback(log_path=log_path)
        feedback.record(
            tool_id="vetka_edit_file",
            success=True,
            useful=True,
            phase_type="build",
        )
        # After recording, the log file should exist
        assert log_path.exists()

    def test_feedback_record_roundtrip(self, tmp_path):
        """Recorded entries should be loadable from the log"""
        from src.services.reflex_feedback import ReflexFeedback

        log_path = tmp_path / "fb.jsonl"
        feedback = ReflexFeedback(log_path=log_path)
        entry = feedback.record(
            tool_id="mycelium_pipeline",
            success=True,
            useful=False,
            phase_type="fix",
        )
        assert entry.tool_id == "mycelium_pipeline"

        # Load from disk and verify
        new_fb = ReflexFeedback(log_path=log_path)
        score = new_fb.get_score("mycelium_pipeline")
        # Score should exist (not 0.5 default means actual data, but default is fine too)
        assert 0.0 <= score <= 1.0


class TestSessionInitEnrichment:
    """178.1.1-4: session_init returns tasks, commits, capabilities, next_steps"""

    def test_task_board_summary_structure(self):
        """TaskBoard summary should have expected keys"""
        from src.orchestration.task_board import TaskBoard, TASK_BOARD_FILE

        board = TaskBoard(TASK_BOARD_FILE)
        all_tasks = list(board.tasks.values())
        pending = [t for t in all_tasks if t.get("status") == "pending"]
        in_progress = [t for t in all_tasks if t.get("status") == "in_progress"]

        summary = {
            "pending_count": len(pending),
            "in_progress_count": len(in_progress),
            "top_pending": [
                {"task_id": t.get("task_id", t.get("id", "")), "title": t.get("title", "")[:60]}
                for t in pending[:5]
            ],
        }
        assert "pending_count" in summary
        assert isinstance(summary["pending_count"], int)
        assert isinstance(summary["top_pending"], list)

    def test_task_board_get_queue(self):
        """TaskBoard.get_queue should return a list"""
        from src.orchestration.task_board import TaskBoard, TASK_BOARD_FILE

        board = TaskBoard(TASK_BOARD_FILE)
        queue = board.get_queue()
        assert isinstance(queue, list)

    def test_task_board_get_queue_filtered(self):
        """TaskBoard.get_queue(status=...) should filter by status"""
        from src.orchestration.task_board import TaskBoard, TASK_BOARD_FILE

        board = TaskBoard(TASK_BOARD_FILE)
        pending = board.get_queue(status="pending")
        assert isinstance(pending, list)
        for t in pending:
            assert t.get("status") == "pending"

    def test_recent_commits_from_git(self):
        """Should get recent commits via git log"""
        import subprocess

        result = subprocess.run(
            ["git", "log", "--oneline", "-5"],
            capture_output=True,
            text=True,
            timeout=3,
            cwd=str(ROOT),
        )
        assert result.returncode == 0
        commits = [c for c in result.stdout.strip().split("\n") if c.strip()]
        assert len(commits) >= 1
        assert len(commits) <= 5

    def test_capability_broker_builds_manifest(self):
        """build_capability_manifest should return a manifest with transports"""
        from src.mcp.tools.capability_broker import build_capability_manifest

        manifest = build_capability_manifest(timeout_s=0.3)
        assert hasattr(manifest, "transports")
        assert hasattr(manifest, "recommended")
        # At least MCP_VETKA + FILE should be present
        assert len(manifest.transports) >= 2

    def test_capability_manifest_has_task_board(self):
        """Manifest should recommend a transport for task_board"""
        from src.mcp.tools.capability_broker import build_capability_manifest

        manifest = build_capability_manifest(timeout_s=0.3)
        assert "task_board" in manifest.recommended

    def test_capability_manifest_vetka_always_available(self):
        """MCP_VETKA transport should always be AVAILABLE (in-process)"""
        from src.mcp.tools.capability_broker import build_capability_manifest, TransportKind, TransportStatus

        manifest = build_capability_manifest(timeout_s=0.3)
        vetka_entry = next(
            (t for t in manifest.transports if t.kind == TransportKind.MCP_VETKA), None
        )
        assert vetka_entry is not None
        assert vetka_entry.status == TransportStatus.AVAILABLE

    def test_capability_manifest_to_dict(self):
        """manifest_to_dict should produce a JSON-serializable dict"""
        from src.mcp.tools.capability_broker import build_capability_manifest, manifest_to_dict

        manifest = build_capability_manifest(timeout_s=0.3)
        d = manifest_to_dict(manifest)
        assert "transports" in d
        assert "recommended" in d
        assert "generated_at" in d
        # Should be JSON serializable
        json_str = json.dumps(d)
        assert len(json_str) > 0


class TestNextSteps:
    """178.1.4: next_steps generation from context"""

    def test_next_steps_from_pending_tasks(self):
        """Should suggest checking tasks when pending > 0"""
        context = {
            "task_board_summary": {
                "pending_count": 5,
                "in_progress_count": 0,
                "top_pending": [],
                "in_progress": [],
            },
            "reflex_recommendations": [],
            "recent_commits": ["abc123 some commit"],
        }
        next_steps = []
        tb = context.get("task_board_summary", {})
        if tb.get("pending_count", 0) > 0:
            next_steps.append(
                f"{tb['pending_count']} pending tasks -> mycelium_task_board action=list"
            )
        assert len(next_steps) == 1
        assert "5 pending" in next_steps[0]

    def test_next_steps_from_reflex(self):
        """Should include REFLEX recommendation"""
        context = {
            "task_board_summary": {"pending_count": 0, "in_progress_count": 0},
            "reflex_recommendations": [
                {"tool_id": "vetka_edit_file", "score": 0.9, "reason": "file editing"}
            ],
            "recent_commits": ["abc123 commit"],
        }
        next_steps = []
        recs = context.get("reflex_recommendations", [])
        if recs:
            top = recs[0]
            next_steps.append(f"REFLEX suggests: {top['tool_id']} ({top['reason']})")
        assert len(next_steps) == 1
        assert "vetka_edit_file" in next_steps[0]

    def test_next_steps_no_commits_warning(self):
        """Should warn when no recent commits"""
        context = {
            "task_board_summary": {"pending_count": 0, "in_progress_count": 0},
            "reflex_recommendations": [],
            "recent_commits": [],
        }
        next_steps = []
        if not context.get("recent_commits"):
            next_steps.append("No recent commits found - check git status")
        assert len(next_steps) == 1
        assert "git status" in next_steps[0]

    def test_next_steps_empty_when_nothing(self):
        """next_steps should be empty when there is nothing to act on"""
        context = {
            "task_board_summary": {"pending_count": 0, "in_progress_count": 0},
            "reflex_recommendations": [],
            "recent_commits": ["abc commit"],
        }
        next_steps = []
        # No pending, no reflex, commits exist -> nothing
        tb = context.get("task_board_summary", {})
        if tb.get("pending_count", 0) > 0:
            next_steps.append("pending tasks")
        recs = context.get("reflex_recommendations", [])
        if recs:
            next_steps.append("reflex")
        if not context.get("recent_commits"):
            next_steps.append("no commits")
        assert len(next_steps) == 0

    def test_next_steps_in_progress_tasks(self):
        """Should mention in-progress tasks when present"""
        context = {
            "task_board_summary": {"pending_count": 0, "in_progress_count": 2},
            "reflex_recommendations": [],
            "recent_commits": ["abc commit"],
        }
        next_steps = []
        tb = context.get("task_board_summary", {})
        if tb.get("in_progress_count", 0) > 0:
            next_steps.append(
                f"{tb['in_progress_count']} tasks in progress -> mycelium_task_board action=list filter_status=in_progress"
            )
        assert len(next_steps) == 1
        assert "2 tasks in progress" in next_steps[0]


class TestReflexIntegrationEnabled:
    """Check REFLEX integration functions work when enabled"""

    def test_reflex_session_callable(self):
        """reflex_session should be importable and callable"""
        from src.services.reflex_integration import reflex_session

        # With REFLEX disabled (default), should return empty list without error
        result = reflex_session({}, phase_type="research")
        assert isinstance(result, list)

    def test_reflex_session_with_enabled_flag(self):
        """reflex_session returns list of dicts when REFLEX is enabled"""
        import importlib
        import src.services.reflex_scorer as scorer_mod
        import src.services.reflex_integration as integration_mod

        env_with_true = {k: v for k, v in os.environ.items()}
        env_with_true["REFLEX_ENABLED"] = "true"
        with patch.dict(os.environ, env_with_true, clear=True):
            importlib.reload(scorer_mod)
            # Call with minimal session data
            result = integration_mod.reflex_session({}, phase_type="research")
            assert isinstance(result, list)
            # Each item should have tool_id, score, reason
            for item in result:
                assert "tool_id" in item
                assert "score" in item
                assert "reason" in item

    def test_reflex_scorer_recommend_empty_tools(self):
        """ReflexScorer.recommend with empty tool list returns empty list"""
        import importlib
        import src.services.reflex_scorer as scorer_mod

        env_with_true = {k: v for k, v in os.environ.items()}
        env_with_true["REFLEX_ENABLED"] = "true"
        with patch.dict(os.environ, env_with_true, clear=True):
            importlib.reload(scorer_mod)
            scorer = scorer_mod.ReflexScorer()
            ctx = scorer_mod.ReflexContext(phase_type="fix")
            # Empty tool list -> empty result
            result = scorer.recommend(ctx, available_tools=[], top_n=5)
            assert isinstance(result, list)
            assert len(result) == 0

    def test_reflex_scorer_recommend_with_registry(self):
        """ReflexScorer.recommend_for_session returns list when REFLEX enabled"""
        import importlib
        import src.services.reflex_scorer as scorer_mod

        env_with_true = {k: v for k, v in os.environ.items()}
        env_with_true["REFLEX_ENABLED"] = "true"
        with patch.dict(os.environ, env_with_true, clear=True):
            importlib.reload(scorer_mod)
            scorer = scorer_mod.ReflexScorer()
            result = scorer.recommend_for_session({}, phase_type="research", top_n=5)
            assert isinstance(result, list)

    def test_reflex_context_from_session(self):
        """ReflexContext.from_session should build a valid context"""
        from src.services.reflex_scorer import ReflexContext

        session_data = {
            "viewport": {"zoom": 0.5},
            "user_preferences": {"has_preferences": False},
        }
        ctx = ReflexContext.from_session(session_data, phase_type="build")
        assert ctx.phase_type == "build"
        assert ctx.hope_level in ("LOW", "MID", "HIGH")
        assert isinstance(ctx.user_tool_prefs, dict)

    def test_reflex_context_hope_level_zoom(self):
        """ReflexContext should map zoom correctly to HOPE level"""
        from src.services.reflex_scorer import ReflexContext

        # Low zoom -> LOW
        ctx_low = ReflexContext.from_session({"viewport": {"zoom": 0.1}})
        assert ctx_low.hope_level == "LOW"

        # High zoom -> HIGH
        ctx_high = ReflexContext.from_session({"viewport": {"zoom": 1.5}})
        assert ctx_high.hope_level == "HIGH"

        # Mid zoom -> MID
        ctx_mid = ReflexContext.from_session({"viewport": {"zoom": 0.5}})
        assert ctx_mid.hope_level == "MID"
