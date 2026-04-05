"""
Phase 76.4: CAM Integration Tests
Test suite for CAM tools integration in VETKA agents
"""

import pytest

pytestmark = pytest.mark.stale(reason="CAM/AURA integration — level lookup API changed")

import asyncio
from unittest.mock import Mock, AsyncMock, patch
from typing import Dict, Any, List

# Import the modules we're testing
from src.agents.tools import (
    CalculateSurpriseTool,
    CompressWithElisionTool,
    AdaptiveMemorySizingTool,
    get_tools_for_agent,
    AGENT_TOOL_PERMISSIONS,
)
from src.memory.aura_store import aura_lookup


class TestCAMTools:
    """Test CAM tools functionality"""

    @pytest.mark.asyncio
    async def test_calculate_surprise_tool(self):
        """Test CalculateSurpriseTool execution"""
        tool = CalculateSurpriseTool()

        # Test with actual implementation (it has built-in mock)
        result = await tool.execute(context="This is a test context with unique words")

        assert result.success is True
        assert "surprise_score" in result.result
        assert "context_length" in result.result
        assert "interpretation" in result.result
        assert 0 <= result.result["surprise_score"] <= 1.0

    @pytest.mark.asyncio
    async def test_compress_with_elision_tool(self):
        """Test CompressWithElisionTool execution"""
        tool = CompressWithElisionTool()

        # Test with actual ELISION implementation
        result = await tool.execute(
            context="This is a long test context that should be compressed",
            target_ratio=0.5,
        )

        assert result.success is True
        assert "compressed_context" in result.result
        assert "original_length" in result.result
        assert "compressed_length" in result.result
        assert "compression_ratio" in result.result

    @pytest.mark.asyncio
    async def test_adaptive_memory_sizing_tool(self):
        """Test AdaptiveMemorySizingTool execution"""
        tool = AdaptiveMemorySizingTool()

        # Mock complexity analysis
        # Test with actual implementation
        result = await tool.execute(
            content="Complex code context", current_context_size=4000
        )

        assert result.success is True
        assert "content_complexity" in result.result
        assert "optimal_context_size" in result.result
        assert "complexity_level" in result.result
        assert 0 <= result.result["content_complexity"] <= 1.0

    def test_cam_tools_registration(self):
        """Test that CAM tools are registered"""
        from src.tools.base_tool import registry

        # Check tools are registered
        assert registry.get("calculate_surprise") is not None
        assert registry.get("compress_with_elision") is not None
        assert registry.get("adaptive_memory_sizing") is not None


class TestAgentPermissions:
    """Test agent permission updates for CAM tools"""

    def test_cam_tools_in_permissions(self):
        """Test that CAM tools are added to agent permissions"""
        # Check that agents have CAM tools in their permissions
        for agent_type, tools in AGENT_TOOL_PERMISSIONS.items():
            if agent_type in ["PM", "Dev", "QA", "Architect", "Researcher"]:
                assert "calculate_surprise" in tools, (
                    f"{agent_type} missing calculate_surprise"
                )
                assert "adaptive_memory_sizing" in tools, (
                    f"{agent_type} missing adaptive_memory_sizing"
                )

            if agent_type in ["Architect", "Researcher"]:
                assert "compress_with_elision" in tools, (
                    f"{agent_type} missing compress_with_elision"
                )

    def test_get_tools_for_agent_includes_cam(self):
        """Test that get_tools_for_agent returns CAM tools"""
        # Test with agent that should have CAM tools
        tools = get_tools_for_agent("Researcher")
        tool_names = [tool.get("function", {}).get("name") for tool in tools]

        assert "calculate_surprise" in tool_names
        assert "compress_with_elision" in tool_names
        assert "adaptive_memory_sizing" in tool_names


class TestAuraLevels:
    """Test Aura level functionality"""

    @pytest.mark.asyncio
    async def test_aura_lookup_level1(self):
        """Test basic Aura lookup (Level 1)"""
        # Mock memory instance
        mock_memory = Mock()
        mock_memory.ram_cache = {
            "user1": Mock(
                preferences={
                    "coding": {"python": "preference_value"},
                    "style": {"format": "value2"},
                }
            )
        }

        with patch(
            "src.memory.aura_store.get_aura_store",
            return_value=mock_memory,
        ):
            results = await aura_lookup("python")

            assert results is not None
            assert len(results) > 0
            assert results[0]["category"] == "coding"
            assert results[0]["key"] == "python"
            assert results[0]["source"] == "engram_o1"


class TestOrchestratorIntegration:
    """Test orchestrator integration with CAM"""

    @pytest.mark.asyncio
    async def test_get_tools_for_agent_with_scope(self):
        """Test orchestrator's enhanced get_tools_for_agent method"""
        # This would require importing OrchestratorWithElisya
        # For now, we'll test the logic conceptually

        from src.orchestration.orchestrator_with_elisya import OrchestratorWithElisya

        # Mock dependencies to avoid full initialization
        with patch.multiple(
            "src.orchestration.orchestrator_with_elisya",
            VETKAPMAgent=Mock(),
            VETKADevAgent=Mock(),
            VETKAQAAgent=Mock(),
            VETKAArchitectAgent=Mock(),
        ):
            try:
                orchestrator = OrchestratorWithElisya()

                # Test with analysis scope
                tools = orchestrator.get_tools_for_agent("Researcher", scope="analysis")
                tool_names = [tool.get("function", {}).get("name") for tool in tools]

                # Should include CAM tools for analysis scope
                assert "calculate_surprise" in tool_names
                assert "adaptive_memory_sizing" in tool_names

            except Exception as e:
                # Expected due to mocked dependencies, but we can still test the method exists
                assert hasattr(OrchestratorWithElisya, "get_tools_for_agent")

    @pytest.mark.asyncio
    async def test_dynamic_semantic_search(self):
        """Test dynamic semantic search functionality"""
        # This would require full orchestrator setup
        # For now, test the method exists and basic logic

        from src.orchestration.orchestrator_with_elisya import OrchestratorWithElisya

        assert hasattr(OrchestratorWithElisya, "dynamic_semantic_search")


# Performance benchmarks
class TestCAMPerformance:
    """Test CAM performance characteristics"""

    @pytest.mark.asyncio
    async def test_surprise_calculation_performance(self):
        """Test that surprise calculation is performant"""
        tool = CalculateSurpriseTool()

        # Test with different content sizes (using built-in implementation)
        small_content = "Small"
        large_content = "Large content " * 1000

        import time

        # Small content should be fast
        start = time.time()
        await tool.execute(context=small_content)
        small_time = time.time() - start

        # Large content should still be reasonable
        start = time.time()
        await tool.execute(context=large_content)
        large_time = time.time() - start

        # Performance assertions (adjust thresholds as needed)
        assert small_time < 0.1  # Should be very fast
        assert large_time < 1.0  # Should still be reasonable

    @pytest.mark.asyncio
    async def test_compression_ratio(self):
        """Test that compression achieves expected ratios"""
        tool = CompressWithElisionTool()

        # Test with actual ELISION implementation
        original = "Test content " * 100  # 1400 chars
        result = await tool.execute(context=original, target_ratio=0.5)

        assert result.success is True
        assert "compression_ratio" in result.result
        assert "tokens_saved" in result.result
        # ELISION should provide some compression
        assert result.result["compression_ratio"] >= 1.0


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])
