"""
MARKER_ZETA.D3: Tests for CLAUDE.md Generator.

Tests:
1. Template rendering — all 5 roles produce valid CLAUDE.md
2. Structure — output matches expected sections
3. Predecessor advice — extracted from JSON experience reports
4. Predecessor advice — fallback to MD files
5. Dry-run mode — no file writes
6. Write mode — files created on disk
7. Pending tasks — injected into output
"""

import time

import pytest
from pathlib import Path

from src.services.agent_registry import AgentRegistry
from src.tools.generate_claude_md import (
    generate_claude_md,
    generate_all,
    write_claude_md,
    _load_template,
)


REGISTRY_PATH = Path(__file__).resolve().parent.parent / "data" / "templates" / "agent_registry.yaml"
TEMPLATE_PATH = Path(__file__).resolve().parent.parent / "data" / "templates" / "claude_md_template.j2"


@pytest.fixture
def registry():
    return AgentRegistry(REGISTRY_PATH)


@pytest.fixture
def template():
    return _load_template(TEMPLATE_PATH)


# ── Rendering Tests ─────────────────────────────────────────


class TestRendering:
    def test_alpha_renders(self, registry, template):
        content = generate_claude_md("Alpha", registry=registry, template=template)
        assert content is not None
        assert "Agent Alpha" in content
        assert "Engine" in content

    def test_beta_renders(self, registry, template):
        content = generate_claude_md("Beta", registry=registry, template=template)
        assert content is not None
        assert "Agent Beta" in content
        assert "Media" in content

    def test_gamma_renders(self, registry, template):
        content = generate_claude_md("Gamma", registry=registry, template=template)
        assert content is not None
        assert "Agent Gamma" in content

    def test_delta_renders(self, registry, template):
        content = generate_claude_md("Delta", registry=registry, template=template)
        assert content is not None
        assert "Agent Delta" in content
        assert "QA" in content or "Qa" in content

    def test_commander_renders(self, registry, template):
        content = generate_claude_md("Commander", registry=registry, template=template)
        assert content is not None
        assert "Commander" in content

    def test_unknown_callsign_returns_none(self, registry, template):
        content = generate_claude_md("Omega", registry=registry, template=template)
        assert content is None

    def test_all_five_roles_render(self, registry, template):
        for callsign in ["Alpha", "Beta", "Gamma", "Delta", "Commander"]:
            content = generate_claude_md(callsign, registry=registry, template=template)
            assert content is not None, f"{callsign} failed to render"
            assert len(content) > 100, f"{callsign} output too short"


# ── Structure Tests ─────────────────────────────────────────


class TestStructure:
    """MARKER_197.SLIM: CLAUDE.md is now a thin bootstrap stub.
    All dynamic context comes from session_init."""

    def test_has_role_header(self, registry, template):
        content = generate_claude_md("Alpha", registry=registry, template=template)
        assert "**Role:**" in content

    def test_has_init_section(self, registry, template):
        content = generate_claude_md("Alpha", registry=registry, template=template)
        assert "## Init" in content
        assert "mcp__vetka__vetka_session_init" in content

    def test_has_cardinal_rules(self, registry, template):
        content = generate_claude_md("Alpha", registry=registry, template=template)
        assert "NEVER commit to main" in content
        assert "claude/cut-engine" in content

    def test_has_required_reading(self, registry, template):
        content = generate_claude_md("Alpha", registry=registry, template=template)
        assert "Required Reading" in content

    def test_has_auto_generated_header(self, registry, template):
        content = generate_claude_md("Alpha", registry=registry, template=template)
        assert "Auto-generated" in content


# ── Predecessor Advice Tests ────────────────────────────────
# MARKER_197.SLIM: Predecessor advice now comes from session_init,
# not from _EXPERIENCE_REPORTS_DIR. No internal APIs to test.


# ── Pending Tasks Tests ─────────────────────────────────────
# MARKER_197.SLIM: pending_tasks param is deprecated (ignored).
# Tasks come from session_init. Verify param is accepted but harmless.


class TestPendingTasks:
    def test_pending_tasks_param_accepted(self, registry, template):
        """pending_tasks param is deprecated but must not crash."""
        tasks = [
            {"id": "tb_001", "title": "Fix timeline playback", "priority": 2},
        ]
        content = generate_claude_md("Alpha", registry=registry, template=template, pending_tasks=tasks)
        assert content is not None
        assert "Agent Alpha" in content


# ── File Write Tests ────────────────────────────────────────


class TestFileWrites:
    def test_dry_run_generates_all(self, registry):
        """generate_all with dry_run=True returns content for all roles."""
        results = generate_all(dry_run=True)
        assert len(results) == 7  # Alpha, Beta, Gamma, Delta, Epsilon, Zeta, Commander
        assert "Alpha" in results
        assert "Beta" in results
        assert "Commander" in results

    def test_write_creates_file(self, tmp_path, registry, template):
        out_dir = tmp_path / "test-worktree"
        path = write_claude_md("Alpha", output_dir=out_dir, registry=registry, template=template)
        assert path is not None
        assert path.exists()
        assert path.name == "CLAUDE.md"
        content = path.read_text()
        assert "Agent Alpha" in content

    def test_generate_all_writes_files(self, tmp_path):
        results = generate_all(dry_run=False, output_base=tmp_path)
        assert len(results) == 7  # All 7 roles
        # Verify files on disk
        for role_name in ["cut-engine", "cut-media", "cut-ux", "cut-qa", "pedantic-bell"]:
            path = tmp_path / role_name / "CLAUDE.md"
            assert path.exists(), f"Missing: {path}"
            content = path.read_text()
            assert len(content) > 100
