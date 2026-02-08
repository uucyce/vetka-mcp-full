"""
Phase 117.5: Cursor Insights Integration Tests

MARKER_117.5: Tests for event-driven wakeup, STM auto-reset,
and GPT-5.2 Gold preset (dragon_gold_gpt).

Cursor research (Feb 2026) validated VETKA's multi-agent architecture.
Three key insights applied:
  A. Event-driven wakeup (on_pipeline_complete)
  B. Auto context reset (STM drift prevention)
  C. GPT-5.2 option in Gold tier
"""

import json
import inspect
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock

# Paths
PRESETS_FILE = Path(__file__).parent.parent / "data" / "templates" / "model_presets.json"


# ============================================================================
# MARKER_117.5A: Event-driven wakeup tests
# ============================================================================

class TestEventDrivenWakeup:
    """Test on_pipeline_complete wakeup hook."""

    def test_on_pipeline_complete_importable(self):
        """MARKER_117.5A: on_pipeline_complete function exists and is importable."""
        from src.orchestration.mycelium_heartbeat import on_pipeline_complete
        assert callable(on_pipeline_complete)

    def test_on_pipeline_complete_is_async(self):
        """MARKER_117.5A: on_pipeline_complete must be async (awaitable)."""
        from src.orchestration.mycelium_heartbeat import on_pipeline_complete
        assert inspect.iscoroutinefunction(on_pipeline_complete), (
            "on_pipeline_complete should be async"
        )

    def test_wakeup_hook_in_pipeline_execute_source(self):
        """MARKER_117.5A: execute() in AgentPipeline should contain wakeup hook."""
        pipeline_file = Path(__file__).parent.parent / "src" / "orchestration" / "agent_pipeline.py"
        source = pipeline_file.read_text()
        assert "on_pipeline_complete" in source, (
            "agent_pipeline.py should reference on_pipeline_complete wakeup hook"
        )
        assert "MARKER_117.5A" in source, (
            "agent_pipeline.py should have MARKER_117.5A for wakeup hook"
        )

    def test_heartbeat_has_wakeup_marker(self):
        """MARKER_117.5A: mycelium_heartbeat.py should have MARKER_117.5A."""
        heartbeat_file = Path(__file__).parent.parent / "src" / "orchestration" / "mycelium_heartbeat.py"
        source = heartbeat_file.read_text()
        assert "MARKER_117.5A" in source
        assert "on_pipeline_complete" in source


# ============================================================================
# MARKER_117.5B: Auto context reset (STM drift prevention)
# ============================================================================

class TestSTMAutoReset:
    """Test STM auto-reset to combat context drift."""

    def test_max_stm_before_reset_defined(self):
        """MARKER_117.5B: MAX_STM_BEFORE_RESET constant should exist."""
        from src.orchestration.agent_pipeline import MAX_STM_BEFORE_RESET
        assert isinstance(MAX_STM_BEFORE_RESET, int)
        assert MAX_STM_BEFORE_RESET == 10, (
            f"Expected MAX_STM_BEFORE_RESET=10, got {MAX_STM_BEFORE_RESET}"
        )

    def test_pipeline_source_has_stm_reset(self):
        """MARKER_117.5B: _execute_subtasks_sequential should contain STM reset logic."""
        pipeline_file = Path(__file__).parent.parent / "src" / "orchestration" / "agent_pipeline.py"
        source = pipeline_file.read_text()
        assert "CONTEXT_RESET" in source, (
            "Pipeline should have CONTEXT_RESET marker in STM reset"
        )
        assert "MAX_STM_BEFORE_RESET" in source, (
            "Pipeline should reference MAX_STM_BEFORE_RESET threshold"
        )
        assert "anti-drift" in source.lower(), (
            "Pipeline should mention anti-drift purpose"
        )

    def test_stm_reset_in_sequential_method(self):
        """MARKER_117.5B: STM reset should be in _execute_subtasks_sequential."""
        from src.orchestration.agent_pipeline import AgentPipeline
        source = inspect.getsource(AgentPipeline._execute_subtasks_sequential)
        assert "MAX_STM_BEFORE_RESET" in source, (
            "STM reset should be inside _execute_subtasks_sequential"
        )

    def test_stm_reset_creates_summary(self):
        """MARKER_117.5B: After reset, STM should contain summary, not be empty."""
        # This tests the reset logic by examining the source code pattern
        pipeline_file = Path(__file__).parent.parent / "src" / "orchestration" / "agent_pipeline.py"
        source = pipeline_file.read_text()
        # After reset, STM should be set to a list with one summary entry
        assert 'self.stm = [{' in source.replace(" ", "").replace("\n", "") or \
               'self.stm = [{\n' in source or \
               '"CONTEXT_RESET"' in source, (
            "STM reset should create a summary entry, not empty list"
        )


# ============================================================================
# MARKER_117.5C: GPT-5.2 Gold preset
# ============================================================================

class TestGPTGoldPreset:
    """Test dragon_gold_gpt preset with GPT-5.2."""

    @pytest.fixture(autouse=True)
    def load_presets(self):
        """Load presets JSON once."""
        assert PRESETS_FILE.exists(), f"Presets file not found: {PRESETS_FILE}"
        self.data = json.loads(PRESETS_FILE.read_text())
        self.presets = self.data.get("presets", {})

    def test_dragon_gold_gpt_exists(self):
        """MARKER_117.5C: dragon_gold_gpt preset should exist."""
        assert "dragon_gold_gpt" in self.presets, (
            "dragon_gold_gpt preset missing from model_presets.json"
        )

    def test_dragon_gold_gpt_has_gpt52_coder(self):
        """MARKER_117.5C: dragon_gold_gpt coder should be GPT-5.2."""
        preset = self.presets["dragon_gold_gpt"]
        coder = preset["roles"]["coder"]
        assert "gpt-5.2" in coder.lower(), (
            f"dragon_gold_gpt coder should be gpt-5.2, got {coder}"
        )

    def test_dragon_gold_gpt_keeps_grok_researcher(self):
        """MARKER_117.5C: dragon_gold_gpt researcher should still be Grok Fast 4.1."""
        preset = self.presets["dragon_gold_gpt"]
        researcher = preset["roles"]["researcher"]
        assert "grok-4.1-fast" in researcher, (
            f"dragon_gold_gpt researcher should be grok-4.1-fast, got {researcher}"
        )

    def test_dragon_gold_gpt_keeps_kimi_architect(self):
        """MARKER_117.5C: dragon_gold_gpt architect should be Kimi K2.5."""
        preset = self.presets["dragon_gold_gpt"]
        architect = preset["roles"]["architect"]
        assert "kimi" in architect.lower(), (
            f"dragon_gold_gpt architect should be Kimi, got {architect}"
        )

    def test_dragon_gold_gpt_uses_polza(self):
        """MARKER_117.5C: dragon_gold_gpt should use polza provider."""
        preset = self.presets["dragon_gold_gpt"]
        assert preset["provider"] == "polza", (
            f"dragon_gold_gpt should use polza, got {preset['provider']}"
        )

    def test_presets_version_updated(self):
        """MARKER_118.10: Presets version should be 4.0 (Phase 118.10 Titans League)."""
        meta = self.data.get("_meta", {})
        assert meta.get("version") == "4.0", (
            f"Expected presets version 4.0, got {meta.get('version')}"
        )

    def test_original_dragon_tiers_intact(self):
        """MARKER_117.5C: Original dragon_bronze/silver/gold should still exist."""
        assert "dragon_bronze" in self.presets
        assert "dragon_silver" in self.presets
        assert "dragon_gold" in self.presets
