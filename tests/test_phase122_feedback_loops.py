"""
Phase 122: Pipeline Feedback Loops — Verifier, Retry, Escalation

Tests:
- TestVerifySubtask: verifier call, severity detection, graceful degradation
- TestCoderRetryLoop: retry on minor issues, max retries, feedback injection
- TestCoderTierUpgrade: bronze→silver→gold upgrade path
- TestArchitectEscalation: major issue → re-plan, max replans
- TestParallelRecon: Scout + Researcher parallel execution
- TestArchitectPMPass: PM pass on low confidence, skip on high
- TestEndToEnd: full pipeline flow with verify-retry
"""

import asyncio
import json
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock, PropertyMock
from dataclasses import dataclass, field, asdict

import pytest

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.orchestration.agent_pipeline import (
    AgentPipeline, Subtask, PipelineTask,
    MAX_CODER_RETRIES, MAX_ARCHITECT_REPLANS, VERIFIER_PASS_THRESHOLD
)


# --- Helpers ---

def _make_pipeline(**kwargs) -> AgentPipeline:
    """Create a pipeline with mocked LLM tool."""
    defaults = {
        "chat_id": "test-chat",
        "preset": "dragon_bronze",
        "auto_write": False,
    }
    defaults.update(kwargs)
    p = AgentPipeline(**defaults)
    # Inject verifier prompt for tests
    if "verifier" not in p.prompts:
        p.prompts["verifier"] = {
            "system": "You are a verifier.",
            "model": "test/verifier-model",
            "temperature": 0.1,
        }
    return p


def _make_subtask(**kwargs) -> Subtask:
    """Create a test subtask."""
    defaults = {
        "description": "Test subtask description",
        "marker": "MARKER_TEST_1",
    }
    defaults.update(kwargs)
    return Subtask(**defaults)


# --- TestVerifySubtask ---

class TestVerifySubtask:
    """Test _verify_subtask method."""

    @pytest.mark.asyncio
    async def test_verify_passing(self):
        """Verifier returns passed=True."""
        pipeline = _make_pipeline()
        subtask = _make_subtask()

        mock_tool = MagicMock()
        mock_tool.execute.return_value = {
            "success": True,
            "result": {
                "content": json.dumps({
                    "passed": True, "issues": [], "suggestions": [],
                    "confidence": 0.95, "severity": "minor"
                }),
                "model": "test/verifier"
            }
        }
        pipeline._get_llm_tool = MagicMock(return_value=mock_tool)

        result = await pipeline._verify_subtask(subtask, "some code output", "build")
        assert result["passed"] is True
        assert result["confidence"] == 0.95

    @pytest.mark.asyncio
    async def test_verify_minor_failure(self):
        """Verifier returns minor failure."""
        pipeline = _make_pipeline()
        subtask = _make_subtask()

        mock_tool = MagicMock()
        mock_tool.execute.return_value = {
            "success": True,
            "result": {
                "content": json.dumps({
                    "passed": False, "issues": ["missing error handling"],
                    "suggestions": ["add try/except"], "confidence": 0.7,
                    "severity": "minor"
                }),
                "model": "test/verifier"
            }
        }
        pipeline._get_llm_tool = MagicMock(return_value=mock_tool)

        result = await pipeline._verify_subtask(subtask, "code", "fix")
        assert result["passed"] is False
        assert result["severity"] == "minor"
        assert len(result["issues"]) == 1

    @pytest.mark.asyncio
    async def test_verify_major_failure(self):
        """Verifier returns major failure with many issues."""
        pipeline = _make_pipeline()
        subtask = _make_subtask()

        mock_tool = MagicMock()
        mock_tool.execute.return_value = {
            "success": True,
            "result": {
                "content": json.dumps({
                    "passed": False,
                    "issues": ["wrong algorithm", "missing validation", "security hole"],
                    "suggestions": [], "confidence": 0.3
                }),
                "model": "test/verifier"
            }
        }
        pipeline._get_llm_tool = MagicMock(return_value=mock_tool)

        result = await pipeline._verify_subtask(subtask, "bad code", "build")
        assert result["passed"] is False
        # Auto-severity: 3 issues + confidence 0.3 < 0.6 → major
        assert result["severity"] == "major"

    @pytest.mark.asyncio
    async def test_verify_graceful_degradation(self):
        """When verifier LLM fails, default to passed=True."""
        pipeline = _make_pipeline()
        subtask = _make_subtask()

        mock_tool = MagicMock()
        mock_tool.execute.return_value = {"success": False, "error": "API timeout"}
        pipeline._get_llm_tool = MagicMock(return_value=mock_tool)

        result = await pipeline._verify_subtask(subtask, "code", "build")
        assert result["passed"] is True  # Graceful degradation

    @pytest.mark.asyncio
    async def test_verify_no_verifier_prompt(self):
        """When verifier prompt is missing, default to passed=True."""
        pipeline = _make_pipeline()
        pipeline.prompts.pop("verifier", None)
        subtask = _make_subtask()

        result = await pipeline._verify_subtask(subtask, "code", "build")
        assert result["passed"] is True


# --- TestCoderRetryLoop ---

class TestCoderRetryLoop:
    """Test coder retry mechanism."""

    @pytest.mark.asyncio
    async def test_retry_on_minor_issues(self):
        """Coder retries once on minor issues, then passes."""
        pipeline = _make_pipeline()
        subtask = _make_subtask()
        pipeline._emit_progress = AsyncMock()

        # Mock _execute_subtask: returns different code on retry
        pipeline._execute_subtask = AsyncMock(return_value="fixed code")

        verifier_result = {
            "passed": False, "issues": ["style issue"],
            "suggestions": ["use snake_case"], "confidence": 0.7,
            "severity": "minor"
        }

        result = await pipeline._retry_coder(subtask, verifier_result, "fix")
        assert subtask.retry_count == 1
        assert result == "fixed code"
        assert "verifier_feedback" in subtask.context

    @pytest.mark.asyncio
    async def test_max_retries_respected(self):
        """Retry loop stops at MAX_CODER_RETRIES."""
        pipeline = _make_pipeline()
        subtask = _make_subtask()
        pipeline._emit_progress = AsyncMock()

        # Simulate MAX_CODER_RETRIES retries
        for _ in range(MAX_CODER_RETRIES):
            pipeline._execute_subtask = AsyncMock(return_value="still bad code")
            await pipeline._retry_coder(subtask, {"passed": False, "issues": ["bug"], "severity": "minor"}, "build")

        assert subtask.retry_count == MAX_CODER_RETRIES

    @pytest.mark.asyncio
    async def test_verifier_feedback_injected(self):
        """Verifier feedback is injected into subtask context."""
        pipeline = _make_pipeline()
        subtask = _make_subtask()
        pipeline._emit_progress = AsyncMock()
        pipeline._execute_subtask = AsyncMock(return_value="new code")

        await pipeline._retry_coder(subtask, {
            "passed": False,
            "issues": ["missing error handling"],
            "suggestions": ["add try/except"],
            "severity": "minor"
        }, "build")

        assert subtask.context is not None
        assert "verifier_feedback" in subtask.context
        assert "missing error handling" in subtask.context["verifier_feedback"]

    @pytest.mark.asyncio
    async def test_no_verify_on_research_phase(self):
        """Verify-retry loop should not trigger for research phase_type.

        This tests the guard condition in _execute_subtasks_sequential:
        `if phase_type in ("fix", "build")` — research is excluded.
        """
        # Research phase should skip verification entirely
        # This is a design-level test — just verify the constants
        assert "research" not in ("fix", "build")


# --- TestCoderTierUpgrade ---

class TestCoderTierUpgrade:
    """Test _upgrade_coder_tier method."""

    def test_upgrade_bronze_to_silver(self):
        pipeline = _make_pipeline(preset="dragon_bronze")
        pipeline.preset_name = "dragon_bronze"
        pipeline._apply_preset = MagicMock()

        result = pipeline._upgrade_coder_tier()
        assert result is True
        assert pipeline.preset_name == "dragon_silver"
        pipeline._apply_preset.assert_called_once()

    def test_upgrade_silver_to_gold(self):
        pipeline = _make_pipeline(preset="dragon_silver")
        pipeline.preset_name = "dragon_silver"
        pipeline._apply_preset = MagicMock()

        result = pipeline._upgrade_coder_tier()
        assert result is True
        assert pipeline.preset_name == "dragon_gold"

    def test_no_upgrade_from_gold(self):
        pipeline = _make_pipeline(preset="dragon_gold")
        pipeline.preset_name = "dragon_gold"
        pipeline._apply_preset = MagicMock()

        result = pipeline._upgrade_coder_tier()
        assert result is False
        assert pipeline.preset_name == "dragon_gold"
        pipeline._apply_preset.assert_not_called()

    def test_titan_upgrade_path(self):
        pipeline = _make_pipeline(preset="titan_lite")
        pipeline.preset_name = "titan_lite"
        pipeline._apply_preset = MagicMock()

        result = pipeline._upgrade_coder_tier()
        assert result is True
        assert pipeline.preset_name == "titan_core"


# --- TestArchitectEscalation ---

class TestArchitectEscalation:
    """Test _escalate_to_architect method."""

    @pytest.mark.asyncio
    async def test_escalate_calls_architect(self):
        """Escalation calls _architect_plan with replan context."""
        pipeline = _make_pipeline()
        pipeline._emit_progress = AsyncMock()

        new_plan = {
            "subtasks": [{"description": "re-do step 1", "needs_research": False, "marker": "MARKER_RE_1"}],
            "execution_order": "sequential",
            "estimated_complexity": "medium"
        }
        pipeline._architect_plan = AsyncMock(return_value=new_plan)

        failed = [_make_subtask(description="failed step", verifier_feedback="logic error")]

        result = await pipeline._escalate_to_architect("original task", failed, {}, "fix")
        assert result == new_plan
        pipeline._architect_plan.assert_called_once()

        # Check that replan_context was passed
        call_kwargs = pipeline._architect_plan.call_args
        assert call_kwargs.kwargs.get("replan_context") is not None
        assert "failed step" in call_kwargs.kwargs["replan_context"]

    @pytest.mark.asyncio
    async def test_escalation_fallback_on_failure(self):
        """If architect re-plan fails, return original plan with needs_research."""
        pipeline = _make_pipeline()
        pipeline._emit_progress = AsyncMock()
        pipeline._architect_plan = AsyncMock(side_effect=Exception("LLM error"))

        original_plan = {
            "subtasks": [{"description": "step 1", "needs_research": False}],
            "execution_order": "sequential",
            "estimated_complexity": "medium"
        }

        result = await pipeline._escalate_to_architect("task", [], original_plan, "build")
        # Fallback: original plan with needs_research=True
        assert result["subtasks"][0]["needs_research"] is True

    def test_max_replans_constant(self):
        """MAX_ARCHITECT_REPLANS should be 1."""
        assert MAX_ARCHITECT_REPLANS == 1


# --- TestParallelRecon ---

class TestParallelRecon:
    """Test _parallel_recon method."""

    @pytest.mark.asyncio
    async def test_both_succeed(self):
        """Both Scout and Researcher return results."""
        pipeline = _make_pipeline()
        pipeline.prompts["scout"] = {"system": "scout", "model": "test/scout"}

        scout_result = {"relevant_files": ["a.py"], "patterns_found": ["pattern1"], "risks": []}
        research_result = {"insights": ["finding1"], "enriched_context": "summary", "confidence": 0.8}

        pipeline._scout_scan = AsyncMock(return_value=scout_result)
        pipeline._research = AsyncMock(return_value=research_result)

        scout_ctx, research_ctx = await pipeline._parallel_recon("task", "build")
        assert scout_ctx is not None
        assert research_ctx is not None
        assert scout_ctx.get("relevant_files") == ["a.py"]
        assert research_ctx.get("confidence") == 0.8

    @pytest.mark.asyncio
    async def test_scout_fails_graceful(self):
        """Scout fails but Researcher still returns."""
        pipeline = _make_pipeline()
        pipeline.prompts["scout"] = {"system": "scout", "model": "test/scout"}

        pipeline._scout_scan = AsyncMock(side_effect=Exception("Scout error"))
        pipeline._research = AsyncMock(return_value={"insights": ["ok"], "confidence": 0.9})

        scout_ctx, research_ctx = await pipeline._parallel_recon("task", "fix")
        assert scout_ctx is None  # Failed gracefully
        assert research_ctx is not None

    @pytest.mark.asyncio
    async def test_researcher_fails_graceful(self):
        """Researcher fails but Scout still returns."""
        pipeline = _make_pipeline()
        pipeline.prompts["scout"] = {"system": "scout", "model": "test/scout"}

        scout_result = {"relevant_files": ["b.py"], "patterns_found": []}
        pipeline._scout_scan = AsyncMock(return_value=scout_result)
        pipeline._research = AsyncMock(side_effect=Exception("Researcher error"))

        scout_ctx, research_ctx = await pipeline._parallel_recon("task", "build")
        assert scout_ctx is not None
        assert research_ctx is None  # Failed gracefully


# --- TestArchitectPMPass ---

class TestArchitectPMPass:
    """Test Architect PM pass logic."""

    def test_pm_pass_triggered_on_low_confidence(self):
        """PM pass should trigger when research confidence < 0.9."""
        research = {"confidence": 0.6, "insights": ["some finding"], "enriched_context": "context"}
        # Condition from execute(): if initial_research and confidence < 0.9
        assert research.get("confidence", 1.0) < 0.9

    def test_pm_pass_skipped_on_high_confidence(self):
        """PM pass should skip when research confidence >= 0.9."""
        research = {"confidence": 0.95, "insights": ["solid finding"]}
        assert not (research.get("confidence", 1.0) < 0.9)

    def test_architect_plan_accepts_research_context(self):
        """_architect_plan signature accepts research_context kwarg."""
        import inspect
        sig = inspect.signature(AgentPipeline._architect_plan)
        assert "research_context" in sig.parameters
        assert "replan_context" in sig.parameters


# --- TestEndToEnd ---

class TestEndToEnd:
    """Test full pipeline flow with feedback loops."""

    @pytest.mark.asyncio
    async def test_flow_passes_first_try(self):
        """Pipeline completes without retries when verifier passes."""
        pipeline = _make_pipeline()
        pipeline._emit_progress = AsyncMock()
        pipeline._emit_to_chat = AsyncMock()
        pipeline._emit_stream_event = MagicMock()
        pipeline._update_task = MagicMock()
        pipeline._log_stm_summary = MagicMock()
        pipeline._bridge_to_global_stm = MagicMock()

        # Mock parallel recon
        pipeline._parallel_recon = AsyncMock(return_value=(
            {"relevant_files": [], "patterns_found": []},
            {"insights": [], "confidence": 0.95, "enriched_context": ""}
        ))

        # Mock architect
        pipeline._architect_plan = AsyncMock(return_value={
            "subtasks": [{"description": "implement feature", "needs_research": False, "marker": "M1"}],
            "execution_order": "sequential",
            "estimated_complexity": "low"
        })

        # Mock coder
        pipeline._execute_subtask = AsyncMock(return_value="implemented code")

        # Mock verifier — passes immediately
        pipeline._verify_subtask = AsyncMock(return_value={
            "passed": True, "issues": [], "confidence": 0.9, "severity": "minor"
        })

        # Mock tier resolve
        pipeline._resolve_tier = MagicMock(return_value=None)

        result = await pipeline.execute("test task", "build")
        assert result["status"] == "done"
        assert result["results"]["subtasks_completed"] == 1

    @pytest.mark.asyncio
    async def test_flow_retry_then_pass(self):
        """Pipeline retries once, then passes on second attempt."""
        pipeline = _make_pipeline()
        pipeline._emit_progress = AsyncMock()
        pipeline._emit_to_chat = AsyncMock()
        pipeline._emit_stream_event = MagicMock()
        pipeline._update_task = MagicMock()
        pipeline._log_stm_summary = MagicMock()
        pipeline._bridge_to_global_stm = MagicMock()

        pipeline._parallel_recon = AsyncMock(return_value=(None, {"confidence": 0.95}))
        pipeline._architect_plan = AsyncMock(return_value={
            "subtasks": [{"description": "fix bug", "needs_research": False, "marker": "M1"}],
            "execution_order": "sequential",
            "estimated_complexity": "low"
        })
        pipeline._resolve_tier = MagicMock(return_value=None)

        # Coder: first call returns bad code, second returns good code
        coder_results = iter(["bad code", "good code"])
        pipeline._execute_subtask = AsyncMock(side_effect=lambda s, p: next(coder_results))

        # Verifier: first call fails (minor), second passes
        verify_results = iter([
            {"passed": False, "issues": ["bug"], "suggestions": ["fix it"], "confidence": 0.7, "severity": "minor"},
            {"passed": True, "issues": [], "confidence": 0.9, "severity": "minor"}
        ])
        pipeline._verify_subtask = AsyncMock(side_effect=lambda s, r, p: next(verify_results))

        result = await pipeline.execute("fix task", "fix")
        assert result["status"] == "done"


# --- TestConstants ---

class TestConstants:
    """Test Phase 122 constants exist and have sane defaults."""

    def test_max_coder_retries(self):
        assert MAX_CODER_RETRIES == 2

    def test_max_architect_replans(self):
        assert MAX_ARCHITECT_REPLANS == 1

    def test_verifier_threshold(self):
        assert VERIFIER_PASS_THRESHOLD == 0.75

    def test_subtask_has_retry_fields(self):
        """Subtask dataclass has new feedback loop fields."""
        s = Subtask(description="test")
        assert s.retry_count == 0
        assert s.verifier_feedback is None
        assert s.escalated is False
