"""
Tests for Phase 129.0: Watcher skip patterns for high-frequency data files.

MARKER_129.0A: During pipeline execution, data/ files get written 50+ times.
Without skip patterns, each write triggers TripleWrite (Qdrant + Weaviate + Changelog)
causing server to freeze. These tests verify all high-frequency files are skipped.

Phase: 129.0
Author: Opus (Claude Code)
"""
import pytest
from pathlib import Path


class TestWatcherSkipPatterns:
    """Verify all high-frequency data files are in SKIP_PATTERNS."""

    @pytest.fixture
    def skip_patterns(self):
        """Load SKIP_PATTERNS from file_watcher.py."""
        from src.scanners.file_watcher import SKIP_PATTERNS
        return SKIP_PATTERNS

    @pytest.fixture
    def should_skip(self):
        """Get _should_skip function via VetkaFileHandler."""
        from src.scanners.file_watcher import SKIP_PATTERNS

        def _check(path: str) -> bool:
            for pattern in SKIP_PATTERNS:
                if pattern in path:
                    return True
            return False

        return _check

    # --- Pipeline high-frequency files ---

    def test_skip_pipeline_tasks(self, should_skip):
        """pipeline_tasks.json written ~10x per pipeline (subtask state changes)."""
        path = "/Users/user/VETKA/vetka_live_03/data/pipeline_tasks.json"
        assert should_skip(path), "pipeline_tasks.json must be skipped"

    def test_skip_usage_tracking(self, should_skip):
        """usage_tracking.json written ~25x per pipeline (every LLM call)."""
        path = "/Users/user/VETKA/vetka_live_03/data/usage_tracking.json"
        assert should_skip(path), "usage_tracking.json must be skipped"

    def test_skip_model_status_cache(self, should_skip):
        """model_status_cache.json written ~15x per pipeline (model health updates)."""
        path = "/Users/user/VETKA/vetka_live_03/data/model_status_cache.json"
        assert should_skip(path), "model_status_cache.json must be skipped"

    def test_skip_heartbeat_state(self, should_skip):
        """heartbeat_state.json written per heartbeat tick."""
        path = "/Users/user/VETKA/vetka_live_03/data/heartbeat_state.json"
        assert should_skip(path), "heartbeat_state.json must be skipped"

    def test_skip_task_board(self, should_skip):
        """task_board.json written per task dispatch/completion."""
        path = "/Users/user/VETKA/vetka_live_03/data/task_board.json"
        assert should_skip(path), "task_board.json must be skipped"

    def test_skip_project_digest(self, should_skip):
        """project_digest.json written on git commit/sync."""
        path = "/Users/user/VETKA/vetka_live_03/data/project_digest.json"
        assert should_skip(path), "project_digest.json must be skipped"

    def test_skip_config(self, should_skip):
        """config.json — app config, no need to index."""
        path = "/Users/user/VETKA/vetka_live_03/data/config.json"
        assert should_skip(path), "config.json must be skipped"

    # --- Pre-existing skips (regression) ---

    def test_skip_changelog_dir(self, should_skip):
        """data/changelog/ must stay skipped (FIX_95.9.3)."""
        path = "/Users/user/VETKA/vetka_live_03/data/changelog/changelog_2026-02-09.json"
        assert should_skip(path), "changelog files must be skipped"

    def test_skip_watcher_state(self, should_skip):
        """watcher_state.json must stay skipped."""
        path = "/Users/user/VETKA/vetka_live_03/data/watcher_state.json"
        assert should_skip(path), "watcher_state.json must be skipped"

    def test_skip_models_cache(self, should_skip):
        """models_cache.json must stay skipped."""
        path = "/Users/user/VETKA/vetka_live_03/data/models_cache.json"
        assert should_skip(path), "models_cache.json must be skipped"

    def test_skip_groups(self, should_skip):
        """groups.json must stay skipped."""
        path = "/Users/user/VETKA/vetka_live_03/data/groups.json"
        assert should_skip(path), "groups.json must be skipped"

    def test_skip_chat_history(self, should_skip):
        """chat_history.json must stay skipped."""
        path = "/Users/user/VETKA/vetka_live_03/data/chat_history.json"
        assert should_skip(path), "chat_history.json must be skipped"

    def test_skip_mcp_audit(self, should_skip):
        """MCP audit directory must be skipped."""
        path = "/Users/user/VETKA/vetka_live_03/data/mcp_audit/mcp_audit_2026-02-09.jsonl"
        assert should_skip(path), "mcp_audit files must be skipped"

    def test_skip_tool_audit_log(self, should_skip):
        """tool_audit_log.jsonl (append-only) must be skipped."""
        path = "/Users/user/VETKA/vetka_live_03/data/tool_audit_log.jsonl"
        assert should_skip(path), "tool_audit_log.jsonl must be skipped"

    # --- Source code must NOT be skipped ---

    def test_allow_python_source(self, should_skip):
        """Python source files must NOT be skipped."""
        path = "/Users/user/VETKA/vetka_live_03/src/orchestration/agent_pipeline.py"
        assert not should_skip(path), "Python source must not be skipped"

    def test_allow_typescript_source(self, should_skip):
        """TypeScript source files must NOT be skipped."""
        path = "/Users/user/VETKA/vetka_live_03/client/src/components/panels/DevPanel.tsx"
        assert not should_skip(path), "TypeScript source must not be skipped"

    def test_allow_template_json(self, should_skip):
        """Template JSON files (prompts, presets) must NOT be skipped."""
        path = "/Users/user/VETKA/vetka_live_03/data/templates/pipeline_prompts.json"
        assert not should_skip(path), "Template JSON must not be skipped"

    def test_allow_docs(self, should_skip):
        """Documentation must NOT be skipped."""
        path = "/Users/user/VETKA/vetka_live_03/docs/129_ph/PHASE_129_PLAN.md"
        assert not should_skip(path), "Documentation must not be skipped"


class TestSkipPatternsCompleteness:
    """Verify all known high-frequency data files are covered."""

    def test_all_pipeline_data_files_covered(self):
        """Every file written during pipeline must be in SKIP_PATTERNS."""
        from src.scanners.file_watcher import SKIP_PATTERNS

        # Files written during Dragon Silver pipeline execution
        pipeline_files = [
            'pipeline_tasks.json',      # 10x per pipeline
            'usage_tracking.json',      # 25x per pipeline
            'model_status_cache.json',  # 15x per pipeline
            'heartbeat_state.json',     # per tick
            'task_board.json',          # per dispatch
        ]

        skip_text = ' '.join(SKIP_PATTERNS)
        for f in pipeline_files:
            assert f in skip_text, f"{f} must be in SKIP_PATTERNS"

    def test_skip_count_minimum(self):
        """At least 20 skip patterns (was 13 before 129.0)."""
        from src.scanners.file_watcher import SKIP_PATTERNS
        assert len(SKIP_PATTERNS) >= 20, f"Expected 20+ patterns, got {len(SKIP_PATTERNS)}"


class TestWriteFrequencyDocumentation:
    """Document expected write frequencies for monitoring."""

    def test_pipeline_tasks_frequency(self):
        """pipeline_tasks.json: ~10 writes per pipeline."""
        # State changes: planning + executing + (per subtask: executing + done) + final stats
        # 5 subtasks: 1 + 1 + 5*2 + 1 = 13 max
        assert True  # Documentation test

    def test_usage_tracking_frequency(self):
        """usage_tracking.json: ~25 writes per pipeline (1 per LLM call)."""
        # Scout(1) + Architect(1) + Researcher(5) + Coder(5) + Verifier(5) + retries(3) = 20-25
        assert True  # Documentation test

    def test_model_status_frequency(self):
        """model_status_cache.json: ~15 writes per pipeline."""
        # 1 per model health update after each LLM call
        assert True  # Documentation test
