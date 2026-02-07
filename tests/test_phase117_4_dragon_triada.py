"""
Phase 117.4: Dragon Триада (Bronze→Silver→Gold) + Auto-Tier Routing

MARKER_117.4D: Tests for preset renaming, auto-default loading,
auto-tier selection, and Grok Fast 4.1 as "The Last Samurai" researcher.
"""

import json
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

# Paths
PRESETS_FILE = Path(__file__).parent.parent / "data" / "templates" / "model_presets.json"


# ============================================================================
# MARKER_117.4D_PRESETS: Preset JSON structure tests
# ============================================================================

class TestPresetTriada:
    """Test preset renaming to bronze/silver/gold triada."""

    @pytest.fixture(autouse=True)
    def load_presets(self):
        """Load presets JSON once."""
        assert PRESETS_FILE.exists(), f"Presets file not found: {PRESETS_FILE}"
        self.data = json.loads(PRESETS_FILE.read_text())
        self.presets = self.data.get("presets", {})

    def test_preset_renamed_bronze_silver_gold(self):
        """MARKER_117.4D: All three dragon tiers exist."""
        assert "dragon_bronze" in self.presets, "dragon_bronze missing"
        assert "dragon_silver" in self.presets, "dragon_silver missing"
        assert "dragon_gold" in self.presets, "dragon_gold missing"

    def test_old_preset_names_removed(self):
        """MARKER_117.4D: Old names (dragon, dragon_budget, dragon_quality) are gone."""
        assert "dragon" not in self.presets, "Old 'dragon' preset should be renamed to dragon_silver"
        assert "dragon_budget" not in self.presets, "Old 'dragon_budget' should be renamed to dragon_bronze"
        assert "dragon_quality" not in self.presets, "Old 'dragon_quality' should be renamed to dragon_gold"

    def test_default_preset_is_dragon_silver(self):
        """MARKER_117.4D: Default preset is dragon_silver."""
        assert self.data.get("default_preset") == "dragon_silver"

    def test_tier_map_in_presets(self):
        """MARKER_117.4D: _tier_map field exists and maps low/medium/high."""
        tier_map = self.data.get("_tier_map")
        assert tier_map is not None, "_tier_map missing from presets JSON"
        assert tier_map.get("low") == "dragon_bronze"
        assert tier_map.get("medium") == "dragon_silver"
        assert tier_map.get("high") == "dragon_gold"

    def test_grok_fast_in_all_dragon_tiers(self):
        """MARKER_117.4D: Grok Fast 4.1 ('The Last Samurai') is researcher in all 3 tiers."""
        for tier in ("dragon_bronze", "dragon_silver", "dragon_gold"):
            preset = self.presets[tier]
            researcher = preset["roles"]["researcher"]
            assert "grok-4.1-fast" in researcher, (
                f"{tier}: researcher should be grok-4.1-fast, got {researcher}"
            )

    def test_no_claude_in_dragon_presets(self):
        """MARKER_117.4D: No Claude/Anthropic models in any dragon_* preset."""
        for name, preset in self.presets.items():
            if not name.startswith("dragon_"):
                continue
            for role, model in preset.get("roles", {}).items():
                assert "claude" not in model.lower(), (
                    f"{name}.{role} uses Claude model: {model}"
                )
                assert "anthropic" not in model.lower(), (
                    f"{name}.{role} uses Anthropic model: {model}"
                )

    def test_all_dragon_tiers_use_polza(self):
        """MARKER_117.4D: All dragon tiers route through Polza provider."""
        for tier in ("dragon_bronze", "dragon_silver", "dragon_gold"):
            assert self.presets[tier]["provider"] == "polza", (
                f"{tier} should use polza provider"
            )

    def test_dragon_silver_has_kimi_architect(self):
        """MARKER_117.4D: Silver and Gold use Kimi K2.5 as architect."""
        for tier in ("dragon_silver", "dragon_gold"):
            architect = self.presets[tier]["roles"]["architect"]
            assert "kimi" in architect.lower(), (
                f"{tier}: architect should be Kimi, got {architect}"
            )


# ============================================================================
# MARKER_117.4D_AUTOTIER: Auto-tier and preset auto-loading tests
# ============================================================================

class TestAutoTier:
    """Test auto-tier selection and default preset loading."""

    def test_apply_preset_auto_loads_default(self):
        """MARKER_117.4D: AgentPipeline(preset=None) should auto-load default preset."""
        from src.orchestration.agent_pipeline import AgentPipeline

        # Create pipeline without specifying preset
        pipeline = AgentPipeline(preset=None)

        # Should have auto-loaded "dragon_silver" from JSON
        assert pipeline.preset_name == "dragon_silver", (
            f"Expected auto-loaded 'dragon_silver', got '{pipeline.preset_name}'"
        )
        # Verify models were actually applied
        assert pipeline.preset_models is not None, "preset_models should be set"
        assert "architect" in pipeline.preset_models
        assert "kimi" in pipeline.preset_models["architect"].lower()

    def test_explicit_preset_overrides_default(self):
        """MARKER_117.4D: Explicit preset should override default."""
        from src.orchestration.agent_pipeline import AgentPipeline

        pipeline = AgentPipeline(preset="dragon_bronze")
        assert pipeline.preset_name == "dragon_bronze"
        assert pipeline.preset_models is not None
        # Bronze architect is Qwen, not Kimi
        assert "qwen" in pipeline.preset_models["architect"].lower()

    def test_resolve_tier_low_medium_high(self):
        """MARKER_117.4D: _resolve_tier maps complexity to correct preset."""
        from src.orchestration.agent_pipeline import AgentPipeline

        pipeline = AgentPipeline()
        assert pipeline._resolve_tier("low") == "dragon_bronze"
        assert pipeline._resolve_tier("medium") == "dragon_silver"
        assert pipeline._resolve_tier("high") == "dragon_gold"

    def test_resolve_tier_unknown_returns_none(self):
        """MARKER_117.4D: Unknown complexity returns None."""
        from src.orchestration.agent_pipeline import AgentPipeline

        pipeline = AgentPipeline()
        assert pipeline._resolve_tier("extreme") is None
        assert pipeline._resolve_tier("") is None

    def test_fallback_models_not_used_with_default(self):
        """MARKER_117.4D: With default preset, architect should NOT be claude-sonnet-4."""
        from src.orchestration.agent_pipeline import AgentPipeline

        pipeline = AgentPipeline()  # No preset specified
        architect_model = pipeline.prompts.get("architect", {}).get("model", "")
        assert "claude" not in architect_model.lower(), (
            f"Architect should not fallback to Claude, got: {architect_model}"
        )

    def test_provider_override_from_preset(self):
        """MARKER_117.4D: Provider should be auto-set from preset."""
        from src.orchestration.agent_pipeline import AgentPipeline

        pipeline = AgentPipeline()
        assert pipeline.provider_override == "polza", (
            f"Expected provider 'polza' from dragon_silver, got '{pipeline.provider_override}'"
        )


# ============================================================================
# MARKER_117.4D_PROMPT: Architect prompt tests
# ============================================================================

class TestArchitectPrompt:
    """Test architect system prompt has complexity guide."""

    def test_architect_prompt_has_complexity_guide(self):
        """MARKER_117.4D: Architect prompt should mention complexity tiers."""
        from src.orchestration.agent_pipeline import AgentPipeline

        pipeline = AgentPipeline()
        architect_prompt = pipeline.prompts.get("architect", {}).get("system", "")
        assert "estimated_complexity" in architect_prompt or "complexity" in architect_prompt.lower(), (
            "Architect prompt should mention complexity"
        )
        # Should mention all three tiers
        assert "bronze" in architect_prompt.lower() or "low" in architect_prompt.lower()
        assert "gold" in architect_prompt.lower() or "high" in architect_prompt.lower()

    def test_architect_prompt_mentions_markers(self):
        """MARKER_117.4D: Architect prompt should instruct to use MARKERs."""
        from src.orchestration.agent_pipeline import AgentPipeline

        pipeline = AgentPipeline()
        architect_prompt = pipeline.prompts.get("architect", {}).get("system", "")
        assert "MARKER" in architect_prompt, "Architect should mention MARKER convention"
