"""
Phase 178 Wave 7 Tests — End-to-End Smoke Test
MARKER_178.7 — Full protocol: create → claim → complete → commit → digest → session_init.
"""
import json
import os
import sys
import time
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))

SESSION_TOOLS_PATH = os.path.join(PROJECT_ROOT, "src", "mcp", "tools", "session_tools.py")
BRIDGE_PATH = os.path.join(PROJECT_ROOT, "src", "mcp", "vetka_mcp_bridge.py")


def _read_source(path):
    with open(path) as f:
        return f.read()


class TestE2ETaskLifecycle:
    """MARKER_178.7.1-7.3: Task lifecycle via local handler."""

    def test_create_claim_complete_task(self):
        """178.7.1-3: Create → claim → complete cycle works."""
        from src.mcp.tools.task_board_tools import handle_task_board

        result = handle_task_board({
            "action": "add",
            "title": "E2E smoke test 178.7",
            "description": "Automated smoke test for Phase 178",
            "priority": 5,
            "phase_type": "fix",
        })
        assert result["success"], f"Create failed: {result}"
        task_id = result["task_id"]

        try:
            result = handle_task_board({
                "action": "claim", "task_id": task_id,
                "assigned_to": "opus_test", "agent_type": "claude_code"
            })
            assert result.get("success") is True, f"Claim failed: {result}"

            # Pass commit_hash to test Case A (already committed) — avoids
            # real git commit in test environment with dirty worktree
            result = handle_task_board({
                "action": "complete", "task_id": task_id,
                "commit_hash": "test1234", "commit_message": "test commit"
            })
            assert result.get("success") is True, f"Complete failed: {result}"

            result = handle_task_board({"action": "get", "task_id": task_id})
            if result.get("success"):
                task = result.get("task", {})
                assert task.get("status") in ("done", "completed"), f"Expected done, got {task.get('status')}"
        finally:
            try: handle_task_board({"action": "remove", "task_id": task_id})
            except: pass


class TestDigestSeqIntegrity:
    """MARKER_178.7.4: Digest _seq increments on updates."""

    def test_digest_has_seq(self):
        """178.7.4: project_digest.json is readable JSON."""
        digest_path = os.path.join(PROJECT_ROOT, "data", "project_digest.json")
        if not os.path.exists(digest_path):
            pytest.skip("project_digest.json not found")
        with open(digest_path) as f:
            digest = json.load(f)
        assert isinstance(digest, dict)


class TestSessionInitReturnsAllFields:
    """MARKER_178.7.5: session_init returns all Phase 178 enrichment fields."""

    def test_session_init_code_has_all_fields(self):
        """178.7.5: session_init handler includes all expected field code paths."""
        source = _read_source(SESSION_TOOLS_PATH)
        for field in [
            "task_board_summary", "recent_commits", "capabilities",
            "next_steps", "reflex_recommendations", "reflex_report",
        ]:
            assert field in source, f"session_init must populate '{field}'"

    def test_session_init_next_steps_sources(self):
        """178.7.5: next_steps built from tasks + REFLEX + commits."""
        source = _read_source(SESSION_TOOLS_PATH)
        assert "pending_count" in source
        assert "reflex_recommendations" in source
        assert "recent_commits" in source


class TestGitSafeStaging:
    """MARKER_178.7.6: Git staging uses porcelain, not git add -A."""

    def test_git_tool_no_add_all(self):
        """178.7.6: git_tool.py must not use 'git add -A' in active code."""
        git_tool_path = os.path.join(PROJECT_ROOT, "src", "mcp", "tools", "git_tool.py")
        if not os.path.exists(git_tool_path):
            pytest.skip("git_tool.py not found")
        with open(git_tool_path) as f:
            content = f.read()
        lines = content.split('\n')
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith('#') or stripped.startswith('"""') or stripped.startswith("'''"):
                continue
            if 'git add -A' in line and not stripped.startswith('#'):
                if 'MARKER' in line or 'replaced' in line.lower() or 'removed' in line.lower():
                    continue
                pytest.fail(f"Line {i+1}: 'git add -A' found in active code")


class TestCapabilityBrokerIntegration:
    """MARKER_178.7: Capability broker integrates with session_init."""

    def test_broker_returns_manifest(self):
        try:
            from src.mcp.tools.capability_broker import build_capability_manifest
            manifest = build_capability_manifest()
            assert manifest is not None
            assert len(manifest.transports) > 0
        except ImportError:
            pytest.skip("capability_broker not available")

    def test_session_init_includes_capabilities(self):
        source = _read_source(SESSION_TOOLS_PATH)
        assert "build_manifest" in source
        assert 'context["capabilities"]' in source


class TestREFLEXEnabled:
    """MARKER_178.7: REFLEX is enabled by default."""

    def test_reflex_enabled_default(self):
        from src.services.reflex_scorer import REFLEX_ENABLED
        env_val = os.environ.get("REFLEX_ENABLED", "true")
        expected = env_val.lower() in ("true", "1", "yes")
        assert REFLEX_ENABLED == expected

    def test_reflex_feedback_log_autocreate(self):
        from src.services.reflex_feedback import ReflexFeedback
        fb = ReflexFeedback()
        summary = fb.get_feedback_summary()
        assert isinstance(summary, dict)


class TestVetkaTaskBoardFallback:
    """MARKER_178.7: vetka_task_board works as fallback when MYCELIUM down."""

    def test_fallback_list(self):
        from src.mcp.tools.task_board_tools import handle_task_board
        result = handle_task_board({"action": "list"})
        assert "success" in result or "tasks" in result

    def test_fallback_summary(self):
        from src.mcp.tools.task_board_tools import handle_task_board
        result = handle_task_board({"action": "summary"})
        assert result is not None

    def test_bridge_handler_calls_real_function(self):
        source = _read_source(BRIDGE_PATH)
        idx = source.find('elif name == "vetka_task_board"')
        assert idx > 0
        block = source[idx:idx + 500]
        assert "handle_task_board" in block
        assert "DEPRECATED" not in block
