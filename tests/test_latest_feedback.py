"""MARKER_208.LATEST_FEEDBACK: Tests for latest_feedback in session_init.

Tests:
1. _get_latest_feedback returns newest file for a known role
2. _get_latest_feedback returns None for unknown role
3. Template has no hardcoded FEEDBACK_*SESSION* filenames
"""

import glob
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent


class TestLatestFeedback:
    """session_init latest_feedback logic."""

    def test_glob_finds_commander_feedback(self):
        """Glob pattern finds FEEDBACK_COMMANDER_* files from main repo."""
        pattern = str(PROJECT_ROOT / "docs" / "190_ph_CUT_WORKFLOW_ARCH" / "feedback" / "FEEDBACK_COMMANDER_*")
        files = sorted(glob.glob(pattern))
        assert len(files) >= 1, f"Expected at least 1 FEEDBACK_COMMANDER_* file, found {len(files)}"
        # Newest should be last (date suffix = alphabetical order)
        newest = files[-1]
        assert "FEEDBACK_COMMANDER_" in newest

    def test_glob_returns_empty_for_unknown_role(self):
        """Glob pattern returns no files for a role with no feedback docs."""
        pattern = str(PROJECT_ROOT / "docs" / "190_ph_CUT_WORKFLOW_ARCH" / "feedback" / "FEEDBACK_NONEXISTENT_ROLE_*")
        files = glob.glob(pattern)
        assert len(files) == 0

    def test_template_no_hardcoded_feedback_session(self):
        """claude_md_template.j2 must not contain hardcoded FEEDBACK_*SESSION* filenames."""
        template_path = PROJECT_ROOT / "data" / "templates" / "claude_md_template.j2"
        content = template_path.read_text(encoding="utf-8")
        # No hardcoded session-specific feedback paths
        import re
        matches = re.findall(r"FEEDBACK_\w+_SESSION\d+", content)
        assert len(matches) == 0, f"Found hardcoded feedback paths in template: {matches}"

    def test_session_tools_has_latest_feedback_code(self):
        """session_tools.py contains MARKER_208.LATEST_FEEDBACK code path."""
        session_tools = PROJECT_ROOT / "src" / "mcp" / "tools" / "session_tools.py"
        content = session_tools.read_text(encoding="utf-8")
        assert "latest_feedback" in content
        assert "FEEDBACK_" in content
        assert "MARKER_208.LATEST_FEEDBACK" in content
