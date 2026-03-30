"""Tests for MARKER_200.FEEDBACK_BRIDGE — Claude Code feedback memory ingestion into ENGRAM L1.

Verifies:
1. Feedback files are parsed and ingested as ENGRAM danger entries
2. Idempotent — re-running doesn't duplicate entries
3. Role filter works on ingested entries
4. Malformed files are skipped gracefully
"""

from pathlib import Path

import pytest

from src.memory.engram_cache import (
    EngramCache,
    ingest_feedback_memories,
    _parse_feedback_frontmatter,
)


@pytest.fixture
def cache(tmp_path):
    """Create an isolated EngramCache with temp storage."""
    return EngramCache(cache_path=tmp_path / "engram_test.json")


@pytest.fixture
def memory_dir(tmp_path):
    """Create a mock Claude Code memory directory with feedback files."""
    mem = tmp_path / "memory"
    mem.mkdir()

    # Valid feedback file
    (mem / "feedback_task_closure.md").write_text(
        "---\n"
        "name: Task closure protocol\n"
        "description: Always close tasks via task_board action=complete\n"
        "type: feedback\n"
        "---\n\n"
        "Detailed explanation here.\n"
    )

    # Another valid feedback file
    (mem / "feedback_no_preview.md").write_text(
        "---\n"
        "name: no_preview_for_cut\n"
        "description: Never use Preview for CUT — viewport too narrow\n"
        "type: feedback\n"
        "---\n\n"
        "Use Control Chrome MCP instead.\n"
    )

    # Malformed file (no closing ---)
    (mem / "feedback_broken.md").write_text(
        "---\n"
        "name: broken\n"
        "description: This file has no closing frontmatter\n"
    )

    # Non-feedback file (should be ignored by glob)
    (mem / "project_opus_role.md").write_text(
        "---\n"
        "name: Opus role\n"
        "description: Opus is commander\n"
        "type: project\n"
        "---\n"
    )

    return mem


class TestParseFrontmatter:
    def test_valid_file(self, memory_dir):
        name, desc = _parse_feedback_frontmatter(memory_dir / "feedback_task_closure.md")
        assert name == "Task closure protocol"
        assert desc == "Always close tasks via task_board action=complete"

    def test_malformed_file(self, memory_dir):
        name, desc = _parse_feedback_frontmatter(memory_dir / "feedback_broken.md")
        assert name == ""
        assert desc == ""

    def test_no_frontmatter(self, tmp_path):
        f = tmp_path / "feedback_plain.md"
        f.write_text("Just plain text, no frontmatter.")
        name, desc = _parse_feedback_frontmatter(f)
        assert name == ""
        assert desc == ""


class TestIngestFeedbackMemories:
    def test_ingests_valid_files(self, memory_dir, cache, monkeypatch):
        import src.memory.engram_cache as mod
        monkeypatch.setattr(mod, "_instance", cache)
        monkeypatch.setattr(mod, "CACHE_PATH", cache._path)

        count = ingest_feedback_memories(memory_dir)
        assert count == 2  # task_closure + no_preview (broken is skipped)

        dangers = cache.get_danger_entries()
        keys = {e.key for e in dangers}
        assert "feedback::Task closure protocol::rule" in keys
        assert "feedback::no_preview_for_cut::rule" in keys

    def test_idempotent(self, memory_dir, cache, monkeypatch):
        import src.memory.engram_cache as mod
        monkeypatch.setattr(mod, "_instance", cache)
        monkeypatch.setattr(mod, "CACHE_PATH", cache._path)

        count1 = ingest_feedback_memories(memory_dir)
        assert count1 == 2
        count2 = ingest_feedback_memories(memory_dir)
        assert count2 == 0  # No new entries

        dangers = cache.get_danger_entries()
        assert len(dangers) == 2  # Still only 2

    def test_category_is_danger(self, memory_dir, cache, monkeypatch):
        import src.memory.engram_cache as mod
        monkeypatch.setattr(mod, "_instance", cache)

        ingest_feedback_memories(memory_dir)
        for entry in cache.get_danger_entries():
            assert entry.category == "danger"

    def test_source_learning_id(self, memory_dir, cache, monkeypatch):
        import src.memory.engram_cache as mod
        monkeypatch.setattr(mod, "_instance", cache)

        ingest_feedback_memories(memory_dir)
        for entry in cache.get_danger_entries():
            assert entry.source_learning_id.startswith("feedback_bridge:")

    def test_empty_dir(self, tmp_path):
        empty = tmp_path / "empty_memory"
        empty.mkdir()
        count = ingest_feedback_memories(empty)
        assert count == 0

    def test_nonexistent_dir(self):
        count = ingest_feedback_memories(Path("/nonexistent/path"))
        assert count == 0


class TestRoleFilter:
    def test_feedback_entries_match_all_roles(self, memory_dir, cache, monkeypatch):
        """Feedback entries (prefix 'feedback::') are universal — match all roles."""
        import src.memory.engram_cache as mod
        monkeypatch.setattr(mod, "_instance", cache)

        ingest_feedback_memories(memory_dir)

        # Add role-specific entries
        cache.put("Zeta::session_tools::fix::harness", "Zeta-specific", category="danger")
        cache.put("Alpha::engine::fix::engine", "Alpha-specific", category="danger")

        zeta_dangers = cache.get_danger_entries(role="Zeta")
        alpha_dangers = cache.get_danger_entries(role="Alpha")

        zeta_keys = {e.key for e in zeta_dangers}
        alpha_keys = {e.key for e in alpha_dangers}

        # Both see feedback entries (universal)
        assert "feedback::Task closure protocol::rule" in zeta_keys
        assert "feedback::Task closure protocol::rule" in alpha_keys

        # Only own role-specific entries
        assert "Zeta::session_tools::fix::harness" in zeta_keys
        assert "Zeta::session_tools::fix::harness" not in alpha_keys
        assert "Alpha::engine::fix::engine" in alpha_keys
        assert "Alpha::engine::fix::engine" not in zeta_keys

    def test_no_role_filter_returns_all(self, cache):
        """Without role filter, all entries are returned."""
        cache.put("feedback::test::rule", "feedback entry", category="danger")
        cache.put("Zeta::test::fix::harness", "zeta entry", category="danger")
        cache.put("Alpha::test::fix::engine", "alpha entry", category="danger")

        all_dangers = cache.get_danger_entries()
        assert len(all_dangers) == 3

    def test_wildcard_entries_match_all_roles(self, cache):
        """Entries with '*' prefix match all roles."""
        cache.put("*::test::fix::all", "universal warning", category="danger")

        assert len(cache.get_danger_entries(role="Zeta")) == 1
        assert len(cache.get_danger_entries(role="Alpha")) == 1

    def test_pair_entries_match_all_roles(self, cache):
        """Entries with 'pair::' prefix match all roles."""
        cache.put("pair::file1::file2::action", "pair warning", category="danger")

        assert len(cache.get_danger_entries(role="Zeta")) == 1
        assert len(cache.get_danger_entries(role="Delta")) == 1

    def test_category_filter_with_role(self, cache):
        """get_all_by_category also supports role filter."""
        cache.put("Zeta::test::arch", "zeta arch", category="architecture")
        cache.put("Alpha::test::arch", "alpha arch", category="architecture")
        cache.put("*::shared::arch", "shared arch", category="architecture")

        zeta_arch = cache.get_all_by_category("architecture", role="Zeta")
        assert len(zeta_arch) == 2  # Zeta + shared
        alpha_arch = cache.get_all_by_category("architecture", role="Alpha")
        assert len(alpha_arch) == 2  # Alpha + shared
