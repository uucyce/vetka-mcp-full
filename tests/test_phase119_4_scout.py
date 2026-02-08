"""Phase 119.4: Scout Role Tests

Tests for the 5th pipeline role — Scout scans codebase before Architect.

MARKER_119.4
"""

import json
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock


# ═══════════════════════════════════════════════════════════════════════
# 1. Scout Prompt Configuration
# ═══════════════════════════════════════════════════════════════════════

class TestScoutPromptConfig:
    """Test scout prompt exists in pipeline_prompts.json."""

    def test_scout_in_pipeline_prompts(self):
        """Scout key exists in pipeline_prompts.json."""
        prompts_path = Path(__file__).parent.parent / "data" / "templates" / "pipeline_prompts.json"
        data = json.loads(prompts_path.read_text())
        assert "scout" in data, "pipeline_prompts.json must have 'scout' key"

    def test_scout_prompt_fields(self):
        """Scout prompt has system, temperature, model, model_fallback."""
        prompts_path = Path(__file__).parent.parent / "data" / "templates" / "pipeline_prompts.json"
        data = json.loads(prompts_path.read_text())
        scout = data["scout"]
        assert "system" in scout
        assert scout["temperature"] == 0.1
        assert "model" in scout
        assert "model_fallback" in scout

    def test_scout_system_prompt_requires_json(self):
        """Scout system prompt instructs JSON output."""
        prompts_path = Path(__file__).parent.parent / "data" / "templates" / "pipeline_prompts.json"
        data = json.loads(prompts_path.read_text())
        system = data["scout"]["system"]
        assert "JSON" in system
        assert "context_summary" in system
        assert "relevant_files" in system
        assert "patterns_found" in system


# ═══════════════════════════════════════════════════════════════════════
# 2. Scout in All Presets
# ═══════════════════════════════════════════════════════════════════════

class TestScoutInPresets:
    """Test scout model is defined in all presets."""

    def _load_presets(self):
        presets_path = Path(__file__).parent.parent / "data" / "templates" / "model_presets.json"
        return json.loads(presets_path.read_text())

    def test_scout_in_all_dragon_presets(self):
        """All dragon presets have scout role."""
        data = self._load_presets()
        dragon_presets = [k for k in data["presets"] if k.startswith("dragon_")]
        assert len(dragon_presets) >= 3, "Should have at least 3 dragon presets"
        for name in dragon_presets:
            roles = data["presets"][name]["roles"]
            assert "scout" in roles, f"{name} missing scout role"

    def test_scout_in_all_titan_presets(self):
        """All titan presets have scout role."""
        data = self._load_presets()
        titan_presets = [k for k in data["presets"] if k.startswith("titan_")]
        assert len(titan_presets) >= 3, "Should have at least 3 titan presets"
        for name in titan_presets:
            roles = data["presets"][name]["roles"]
            assert "scout" in roles, f"{name} missing scout role"

    def test_scout_in_all_presets(self):
        """Every single preset has scout role."""
        data = self._load_presets()
        for name, preset in data["presets"].items():
            roles = preset.get("roles", {})
            assert "scout" in roles, f"Preset '{name}' missing scout role"


# ═══════════════════════════════════════════════════════════════════════
# 3. Scout Scan Method
# ═══════════════════════════════════════════════════════════════════════

class TestScoutScan:
    """Test _scout_scan() method on AgentPipeline."""

    def _make_pipeline(self, **kwargs):
        """Create pipeline with mocked prompts to avoid file I/O."""
        from src.orchestration.agent_pipeline import AgentPipeline
        with patch.object(AgentPipeline, '_load_prompts'), \
             patch.object(AgentPipeline, '_apply_preset'):
            pipe = AgentPipeline(**kwargs)
            pipe.prompts = json.loads(
                (Path(__file__).parent.parent / "data" / "templates" / "pipeline_prompts.json").read_text()
            )
            pipe.preset_models = None
            pipe.provider_override = None
            pipe.elision_compressor = MagicMock()
            pipe._last_used_model = ""
        return pipe

    @pytest.mark.asyncio
    async def test_scout_scan_returns_data(self):
        """_scout_scan returns structured dict on success."""
        pipe = self._make_pipeline()

        mock_tool = MagicMock()
        mock_tool.execute.return_value = {
            "success": True,
            "result": {
                "content": json.dumps({
                    "context_summary": "Found relevant files",
                    "relevant_files": ["src/foo.py"],
                    "patterns_found": ["singleton pattern"],
                    "risks": [],
                    "recommendations": ["follow existing pattern"]
                }),
                "model": "test-model"
            }
        }
        pipe.llm_tool = mock_tool

        result = await pipe._scout_scan("implement feature X", "build")
        assert result is not None
        assert "context_summary" in result
        assert len(result["relevant_files"]) == 1
        assert result["patterns_found"] == ["singleton pattern"]

    @pytest.mark.asyncio
    async def test_scout_scan_graceful_failure(self):
        """_scout_scan returns None on LLM failure (non-fatal)."""
        pipe = self._make_pipeline()

        mock_tool = MagicMock()
        mock_tool.execute.return_value = {
            "success": False,
            "error": "Model unavailable"
        }
        pipe.llm_tool = mock_tool

        result = await pipe._scout_scan("fix bug Y", "fix")
        assert result is None

    @pytest.mark.asyncio
    async def test_scout_scan_skip_when_no_prompt(self):
        """_scout_scan returns None if 'scout' not in self.prompts."""
        pipe = self._make_pipeline()
        del pipe.prompts["scout"]  # Remove scout prompt

        result = await pipe._scout_scan("task Z", "research")
        assert result is None


# ═══════════════════════════════════════════════════════════════════════
# 4. Scout Integration with Architect
# ═══════════════════════════════════════════════════════════════════════

class TestScoutIntegration:
    """Test scout context injection into architect."""

    def _make_pipeline(self):
        from src.orchestration.agent_pipeline import AgentPipeline
        with patch.object(AgentPipeline, '_load_prompts'), \
             patch.object(AgentPipeline, '_apply_preset'):
            pipe = AgentPipeline()
            pipe.prompts = json.loads(
                (Path(__file__).parent.parent / "data" / "templates" / "pipeline_prompts.json").read_text()
            )
            pipe.preset_models = None
            pipe.provider_override = None
            pipe.elision_compressor = MagicMock()
            pipe._last_used_model = ""
        return pipe

    @pytest.mark.asyncio
    async def test_architect_receives_scout_context(self):
        """_architect_plan injects scout report into user message."""
        pipe = self._make_pipeline()

        captured_args = {}

        mock_tool = MagicMock()
        def capture_execute(args):
            captured_args.update(args)
            return {
                "success": True,
                "result": {
                    "content": json.dumps({
                        "subtasks": [{"description": "do X", "needs_research": False, "marker": "MARKER_119.1"}],
                        "execution_order": "sequential",
                        "estimated_complexity": "low"
                    }),
                    "model": "test-architect"
                }
            }
        mock_tool.execute.side_effect = capture_execute
        pipe.llm_tool = mock_tool

        scout_data = {
            "context_summary": "Found auth module",
            "relevant_files": ["src/auth.py"],
            "patterns_found": ["JWT pattern"],
            "risks": [],
            "recommendations": ["Use existing auth"]
        }

        plan = await pipe._architect_plan("add login", "build", scout_context=scout_data)

        assert plan is not None
        # Check that user message contains scout report
        user_msg = captured_args["messages"][1]["content"]
        assert "[Scout Report]" in user_msg
        assert "Found auth module" in user_msg

    @pytest.mark.asyncio
    async def test_architect_works_without_scout(self):
        """_architect_plan works normally when scout_context is None."""
        pipe = self._make_pipeline()

        mock_tool = MagicMock()
        mock_tool.execute.return_value = {
            "success": True,
            "result": {
                "content": json.dumps({
                    "subtasks": [{"description": "task 1", "needs_research": False, "marker": "MARKER_1"}],
                    "execution_order": "sequential",
                    "estimated_complexity": "medium"
                }),
                "model": "test"
            }
        }
        pipe.llm_tool = mock_tool

        plan = await pipe._architect_plan("simple task", "research", scout_context=None)
        assert "subtasks" in plan
        # No scout report in user message
        user_msg = mock_tool.execute.call_args[0][0]["messages"][1]["content"]
        assert "[Scout Report]" not in user_msg
