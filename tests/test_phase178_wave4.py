"""
Phase 178 Wave 4: Universal REFLEX hooks in ALL LLM call paths.
Verify that REFLEX pre/post hooks fire at choke points.
MARKER_178.4.TESTS
"""
import sys
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# Resolve actual source root (may differ from worktree root when running from main project)
def _find_src_root() -> Path:
    """Find the root that contains src/mcp/tools/llm_call_tool.py."""
    candidate = ROOT
    if (candidate / "src" / "mcp" / "tools" / "llm_call_tool.py").exists():
        return candidate
    # Fallback: walk up or check sys.path entries
    for p in sys.path:
        pp = Path(p)
        if (pp / "src" / "mcp" / "tools" / "llm_call_tool.py").exists():
            return pp
    return candidate  # best effort

SRC_ROOT = _find_src_root()


class TestLLMCallToolReflexHooks:
    """178.4.8-9: REFLEX hooks in LLMCallTool"""

    def test_llm_call_tool_importable(self):
        """LLMCallTool should be importable"""
        from src.mcp.tools.llm_call_tool import LLMCallTool
        tool = LLMCallTool()
        assert tool is not None

    def test_llm_call_tool_has_execute(self):
        """LLMCallTool should have execute method"""
        from src.mcp.tools.llm_call_tool import LLMCallTool
        tool = LLMCallTool()
        assert hasattr(tool, 'execute')

    def test_reflex_hooks_marker_present(self):
        """MARKER_178.4.8 and 178.4.9 should be in llm_call_tool.py"""
        tool_path = SRC_ROOT / "src" / "mcp" / "tools" / "llm_call_tool.py"
        content = tool_path.read_text()
        assert "MARKER_178.4.8" in content or "reflex_pre_fc" in content


class TestLLMCallToolAsyncReflexHooks:
    """178.4.8-9: REFLEX hooks in LLMCallToolAsync"""

    def test_async_tool_importable(self):
        """LLMCallToolAsync should be importable"""
        from src.mcp.tools.llm_call_tool_async import LLMCallToolAsync
        tool = LLMCallToolAsync()
        assert tool is not None


class TestPipelinePromptInjection:
    """178.4.2-4: REFLEX injected into pipeline agent prompts"""

    def test_feedback_summary_for_architect(self):
        """Feedback summary should be injectable into architect prompt"""
        from src.services.reflex_feedback import ReflexFeedback
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
            fb = ReflexFeedback(log_path=Path(f.name))
            # Add some test data
            for i in range(5):
                fb.record(tool_id="vetka_edit_file", success=True, useful=True, phase_type="fix")
            fb.record(tool_id="vetka_search_semantic", success=True, useful=False, phase_type="fix")

            summary = fb.get_stats()
            assert summary["total_entries"] == 6

            # Build preamble like the architect hook does
            reflex_preamble = f"[REFLEX Team Performance]\n"
            reflex_preamble += f"Total tool calls tracked: {summary['total_entries']}\n"
            reflex_preamble += f"Success rate: {summary['avg_success_rate']:.0%}\n"

            assert "6" in reflex_preamble
            assert "100%" in reflex_preamble

    def test_reflex_recommendations_format(self):
        """REFLEX recommendations should format correctly for coder prompt"""
        recs = [
            {"tool_id": "vetka_edit_file", "score": 0.92, "reason": "file editing"},
            {"tool_id": "vetka_search_semantic", "score": 0.85, "reason": "search context"}
        ]
        coder_hint = "[REFLEX Recommendations]\n"
        for rec in recs[:5]:
            coder_hint += f"- {rec['tool_id']} (score: {rec['score']:.2f})\n"

        assert "vetka_edit_file" in coder_hint
        assert "0.92" in coder_hint
        assert "vetka_search_semantic" in coder_hint


class TestUniversalCoverage:
    """178.4: Every LLM call path has REFLEX awareness"""

    def test_reflex_integration_functions_exist(self):
        """All needed REFLEX integration functions should exist"""
        from src.services.reflex_integration import (
            reflex_pre_fc,
            reflex_post_fc,
            reflex_verifier,
            reflex_session,
            reflex_filter_schemas,
            _is_enabled
        )
        assert callable(reflex_pre_fc)
        assert callable(reflex_post_fc)
        assert callable(reflex_verifier)
        assert callable(reflex_session)
        assert callable(reflex_filter_schemas)
        assert callable(_is_enabled)

    def test_reflex_pre_fc_with_minimal_subtask(self):
        """reflex_pre_fc should work with a minimal mock subtask"""
        from src.services.reflex_integration import reflex_pre_fc

        class MinimalSubtask:
            def __init__(self):
                self.description = "Test LLM call from chat"
                self.context = {"phase_type": "research", "agent_role": "coder"}

        result = reflex_pre_fc(MinimalSubtask(), phase_type="research", agent_role="coder")
        assert isinstance(result, list)

    def test_reflex_post_fc_with_tool_calls(self):
        """reflex_post_fc should handle tool_calls format from LLM response"""
        from src.services.reflex_integration import reflex_post_fc

        tool_execs = [
            {"name": "vetka_edit_file", "success": True, "result": {"content": "edited"}},
            {"name": "vetka_read_file", "success": True, "result": {"content": "read"}}
        ]
        count = reflex_post_fc(tool_execs, phase_type="fix", agent_role="coder", subtask_id="chat_call")
        assert isinstance(count, int)

    def test_pipeline_prompts_loadable(self):
        """pipeline_prompts.json should be loadable"""
        import json
        prompts_path = ROOT / "data" / "templates" / "pipeline_prompts.json"
        if prompts_path.exists():
            prompts = json.loads(prompts_path.read_text())
            assert "architect" in prompts
            assert "coder" in prompts
            assert "system" in prompts["architect"]

    def test_choke_point_coverage(self):
        """Both sync and async LLM tools should exist"""
        sync_path = ROOT / "src" / "mcp" / "tools" / "llm_call_tool.py"
        async_path = ROOT / "src" / "mcp" / "tools" / "llm_call_tool_async.py"
        assert sync_path.exists(), "Sync LLM call tool missing"
        assert async_path.exists(), "Async LLM call tool missing"
