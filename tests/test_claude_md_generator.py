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

import json
import time

import pytest
from pathlib import Path

from src.services.agent_registry import AgentRegistry
from src.tools.generate_claude_md import (
    generate_claude_md,
    generate_all,
    write_claude_md,
    _load_template,
    _extract_predecessor_advice_from_json,
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
    def test_has_role_header(self, registry, template):
        content = generate_claude_md("Alpha", registry=registry, template=template)
        assert "**Role:**" in content
        assert "**Callsign:** Alpha" in content

    def test_has_first_task_section(self, registry, template):
        content = generate_claude_md("Alpha", registry=registry, template=template)
        assert "Your First Task in 3 Steps" in content
        assert "mcp__vetka__vetka_session_init" in content

    def test_has_identity_section(self, registry, template):
        content = generate_claude_md("Alpha", registry=registry, template=template)
        assert "## Identity" in content

    def test_has_owned_files_section(self, registry, template):
        content = generate_claude_md("Alpha", registry=registry, template=template)
        assert "Owned Files" in content
        assert "useTimelineInstanceStore" in content

    def test_has_do_not_touch_section(self, registry, template):
        content = generate_claude_md("Alpha", registry=registry, template=template)
        assert "DO NOT Touch" in content
        assert "MenuBar" in content

    def test_has_cardinal_rules(self, registry, template):
        content = generate_claude_md("Alpha", registry=registry, template=template)
        assert "NEVER commit to main" in content
        assert "branch=claude/cut-engine" in content

    def test_has_key_docs(self, registry, template):
        content = generate_claude_md("Alpha", registry=registry, template=template)
        assert "Key Docs" in content

    def test_has_session_end_section(self, registry, template):
        content = generate_claude_md("Alpha", registry=registry, template=template)
        assert "Before Session End" in content
        assert "experience report" in content.lower()

    def test_has_auto_generated_header(self, registry, template):
        content = generate_claude_md("Alpha", registry=registry, template=template)
        assert "AUTO-GENERATED" in content


# ── Predecessor Advice Tests ────────────────────────────────


class TestPredecessorAdvice:
    def test_advice_from_json_reports(self, tmp_path, registry, template):
        """Create a fake JSON experience report and verify it's picked up."""
        reports_dir = tmp_path / "reports"
        reports_dir.mkdir()
        report = {
            "session_id": "test-001",
            "agent_callsign": "Alpha",
            "domain": "engine",
            "branch": "claude/cut-engine",
            "timestamp": "2026-03-22T00:00:00Z",
            "lessons_learned": ["Always test the JKL shuttle at 4x speed"],
            "recommendations": ["Read chapter 5 of the FCP7 manual"],
        }
        (reports_dir / "test-001.json").write_text(json.dumps(report))

        # Monkey-patch the reports dir
        import src.tools.generate_claude_md as gen_mod
        original_dir = gen_mod._EXPERIENCE_REPORTS_DIR
        gen_mod._EXPERIENCE_REPORTS_DIR = reports_dir
        try:
            content = generate_claude_md("Alpha", registry=registry, template=template)
            assert "Always test the JKL shuttle at 4x speed" in content
            assert "Read chapter 5 of the FCP7 manual" in content
        finally:
            gen_mod._EXPERIENCE_REPORTS_DIR = original_dir

    def test_no_advice_still_renders(self, registry, template, tmp_path):
        """Even with no experience reports, CLAUDE.md should render."""
        import src.tools.generate_claude_md as gen_mod
        original_dir = gen_mod._EXPERIENCE_REPORTS_DIR
        gen_mod._EXPERIENCE_REPORTS_DIR = tmp_path / "empty_reports"
        original_fb = gen_mod._FEEDBACK_DOCS_DIR
        gen_mod._FEEDBACK_DOCS_DIR = tmp_path / "empty_feedback"
        try:
            content = generate_claude_md("Alpha", registry=registry, template=template)
            assert content is not None
            assert "Agent Alpha" in content
        finally:
            gen_mod._EXPERIENCE_REPORTS_DIR = original_dir
            gen_mod._FEEDBACK_DOCS_DIR = original_fb


# ── Pending Tasks Tests ─────────────────────────────────────


class TestPendingTasks:
    def test_pending_tasks_rendered(self, registry, template):
        tasks = [
            {"id": "tb_001", "title": "Fix timeline playback", "priority": 2},
            {"id": "tb_002", "title": "Add JKL shuttle", "priority": 1},
        ]
        content = generate_claude_md("Alpha", registry=registry, template=template, pending_tasks=tasks)
        assert "tb_001" in content
        assert "Fix timeline playback" in content
        assert "P2" in content
        assert "tb_002" in content

    def test_no_pending_tasks_section_when_empty(self, registry, template):
        content = generate_claude_md("Alpha", registry=registry, template=template, pending_tasks=[])
        # Should not have the pending tasks header
        assert "Current Pending Tasks" not in content


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
