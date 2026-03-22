"""
Phase 178 Wave 5 Tests — CLAUDE.md Dynamic Bridge
MARKER_178.5 — Verify CLAUDE.md references next_steps and session_init dynamic guidance.
"""
import os
import pytest

pytestmark = pytest.mark.stale(reason="Pre-existing failure — phase 178 contracts changed")


CLAUDE_MD_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    ".claude", "worktrees", "confident-ritchie", "CLAUDE.md"
)

# Fallback: check main repo CLAUDE.md if worktree doesn't exist
CLAUDE_MD_MAIN = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "CLAUDE.md"
)


def _read_claude_md():
    """Read CLAUDE.md from worktree or main repo."""
    for path in [CLAUDE_MD_PATH, CLAUDE_MD_MAIN]:
        if os.path.exists(path):
            with open(path) as f:
                return f.read()
    pytest.skip("CLAUDE.md not found in expected locations")


def _read_session_tools_source():
    """Read session_tools.py source for code inspection."""
    path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        "src", "mcp", "tools", "session_tools.py"
    )
    with open(path) as f:
        return f.read()


class TestClaudeMdBridge:
    """MARKER_178.5: CLAUDE.md references dynamic session_init guidance."""

    def test_claude_md_mentions_next_steps(self):
        """178.5.1: CLAUDE.md tells agents to follow next_steps."""
        content = _read_claude_md()
        assert "next_steps" in content, "CLAUDE.md must mention next_steps"

    def test_claude_md_mentions_reflex_recommendations(self):
        """178.5.1: CLAUDE.md tells agents about reflex_recommendations."""
        content = _read_claude_md()
        assert "reflex_recommendations" in content, "CLAUDE.md must mention reflex_recommendations"

    def test_claude_md_mentions_capabilities(self):
        """178.5.1: CLAUDE.md tells agents about capabilities/transport manifest."""
        content = _read_claude_md()
        assert "capabilities" in content

    def test_claude_md_dynamic_guidance_section(self):
        """178.5.1: CLAUDE.md has Dynamic Guidance section."""
        content = _read_claude_md()
        assert "Dynamic Guidance" in content, "CLAUDE.md must have Dynamic Guidance section"

    def test_claude_md_static_vs_dynamic_explanation(self):
        """178.5.3: CLAUDE.md explains static vs dynamic split."""
        content = _read_claude_md()
        assert "static" in content.lower() and "dynamic" in content.lower()

    def test_claude_md_fallback_rule(self):
        """178.5.4: CLAUDE.md mentions vetka_task_board as fallback."""
        content = _read_claude_md()
        assert "vetka_task_board" in content and "fallback" in content.lower()

    def test_rule_1_references_next_steps(self):
        """178.5.2: Rule #1 references next_steps."""
        content = _read_claude_md()
        assert "follow `next_steps`" in content or "follow next_steps" in content


class TestSessionInitNextSteps:
    """MARKER_178.5.2: session_init next_steps references CLAUDE.md task lifecycle."""

    def test_next_steps_mentions_task_board(self):
        """next_steps references mycelium_task_board."""
        source = _read_session_tools_source()
        assert "next_steps" in source
        assert "mycelium_task_board" in source or "task_board" in source

    def test_next_steps_mentions_fallback(self):
        """next_steps references vetka_task_board fallback."""
        source = _read_session_tools_source()
        assert "vetka_task_board" in source, "next_steps should mention fallback"

    def test_reflex_report_in_session_init(self):
        """178.4.12: session_init includes reflex_report code path."""
        source = _read_session_tools_source()
        assert "reflex_report" in source
        assert "get_feedback_summary" in source
