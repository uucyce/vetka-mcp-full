"""
MARKER_197.SLIM: Tests for CLAUDE.md Generator — slim routing stub version.

Tests:
1. Template rendering — all 7 roles produce valid CLAUDE.md
2. Structure — output has init section, branch, role title
3. Commander — gets orchestration section
4. Slim contract — no owned_paths, no predecessor, no L1/L2 tables
5. Dry-run mode — no file writes
6. Write mode — files created on disk
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

    def test_all_roles_render(self, registry, template):
        for callsign in ["Alpha", "Beta", "Gamma", "Delta", "Epsilon", "Zeta", "Commander"]:
            content = generate_claude_md(callsign, registry=registry, template=template)
            assert content is not None, f"{callsign} failed to render"
            assert len(content) > 50, f"{callsign} output too short"


# ── Structure Tests — Slim Template ─────────────────────────


class TestStructure:
    def test_has_role_header(self, registry, template):
        content = generate_claude_md("Alpha", registry=registry, template=template)
        assert "**Role:**" in content
        assert "Engine Architect" in content

    def test_has_init_section(self, registry, template):
        content = generate_claude_md("Alpha", registry=registry, template=template)
        assert "## Init" in content
        assert "mcp__vetka__vetka_session_init" in content

    def test_has_branch(self, registry, template):
        content = generate_claude_md("Alpha", registry=registry, template=template)
        assert "branch=claude/cut-engine" in content

    def test_has_cardinal_rules(self, registry, template):
        content = generate_claude_md("Alpha", registry=registry, template=template)
        assert "NEVER commit to main" in content
        assert "NEVER" in content

    def test_has_auto_generated_header(self, registry, template):
        content = generate_claude_md("Alpha", registry=registry, template=template)
        assert "Auto-generated" in content

    def test_session_init_returns_role_context(self, registry, template):
        """Slim CLAUDE.md tells agent that session_init provides role_context."""
        content = generate_claude_md("Alpha", registry=registry, template=template)
        assert "role_context" in content


# ── Slim Contract — Removed Sections ─────────────────────────


class TestSlimContract:
    """Verify that bloated sections are NOT in slim template."""

    def test_no_owned_files_section(self, registry, template):
        content = generate_claude_md("Alpha", registry=registry, template=template)
        assert "Owned Files" not in content
        assert "useTimelineInstanceStore" not in content

    def test_no_predecessor_advice(self, registry, template):
        content = generate_claude_md("Alpha", registry=registry, template=template)
        assert "Predecessor Advice" not in content

    def test_no_memory_context_tables(self, registry, template):
        content = generate_claude_md("Alpha", registry=registry, template=template)
        assert "L1 — Hot Context" not in content
        assert "L2 — Warm Context" not in content

    def test_no_key_docs_section(self, registry, template):
        content = generate_claude_md("Alpha", registry=registry, template=template)
        assert "Key Docs" not in content

    def test_no_session_end_section(self, registry, template):
        content = generate_claude_md("Alpha", registry=registry, template=template)
        assert "Before Session End" not in content

    def test_no_commit_flow_details(self, registry, template):
        content = generate_claude_md("Alpha", registry=registry, template=template)
        assert "Commit Flow" not in content
        assert "Anti-pattern" not in content

    def test_slim_size_under_1000_chars(self, registry, template):
        """Non-Commander roles should be under 1000 chars."""
        content = generate_claude_md("Alpha", registry=registry, template=template)
        assert len(content) < 1000, f"Alpha CLAUDE.md is {len(content)} chars, should be < 1000"


# ── Commander Orchestration ─────────────────────────────────


class TestCommander:
    def test_has_orchestration_section(self, registry, template):
        content = generate_claude_md("Commander", registry=registry, template=template)
        assert "Orchestration" in content
        assert "Fleet" in content

    def test_non_commander_no_orchestration(self, registry, template):
        content = generate_claude_md("Alpha", registry=registry, template=template)
        assert "Orchestration" not in content


# ── File Write Tests ────────────────────────────────────────


class TestFileWrites:
    def test_dry_run_generates_all(self, registry):
        """generate_all with dry_run=True returns content for all 7 roles."""
        results = generate_all(dry_run=True)
        assert len(results) == 7
        assert "Alpha" in results
        assert "Beta" in results
        assert "Commander" in results
        assert "Zeta" in results

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
        assert len(results) == 7
        # Verify files on disk for all worktrees
        for role_name in ["cut-engine", "cut-media", "cut-ux", "cut-qa", "cut-qa-2", "harness", "pedantic-bell"]:
            path = tmp_path / role_name / "CLAUDE.md"
            assert path.exists(), f"Missing: {path}"
            content = path.read_text()
            assert len(content) > 50
