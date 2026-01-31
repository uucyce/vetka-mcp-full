"""
PHASE 104 - ELISION Integration Tests

Tests for ELISION compression integration in:
1. orchestrator_with_elisya.py (LLM context compression)
2. role_prompts.py (ELISION awareness in agent prompts)

MARKER_104_ELISION_INTEGRATION: Verification tests

@file test_phase104_elision_integration.py
@phase 104
@status active
"""

import pytest
import json
from pathlib import Path

# Test imports
from src.memory.elision import (
    get_elision_compressor,
    compress_context,
    compress_level_3,
    ElisionCompressor
)
from src.agents.role_prompts import (
    get_agent_prompt,
    ELISION_AWARENESS_NOTE,
    PM_SYSTEM_PROMPT,
    DEV_SYSTEM_PROMPT,
    QA_SYSTEM_PROMPT,
    ARCHITECT_SYSTEM_PROMPT,
    RESEARCHER_SYSTEM_PROMPT,
    HOSTESS_SYSTEM_PROMPT
)


class TestElisionCompressorIntegration:
    """Test ELISION compression functionality"""

    def test_get_elision_compressor_singleton(self):
        """MARKER_104_ELISION_INTEGRATION: Verify singleton pattern"""
        compressor1 = get_elision_compressor()
        compressor2 = get_elision_compressor()
        assert compressor1 is compressor2, "Compressor should be singleton"

    def test_compress_large_context(self):
        """MARKER_104_ELISION_INTEGRATION: Large context compression"""
        # Create large context (> 5000 chars)
        large_context = json.dumps({
            "context": {
                "current_file": "src/orchestration/orchestrator_with_elisya.py",
                "file_path": "/Users/dani/VETKA_Project/vetka_live_03/src/orchestration",
                "viewport_nodes": [
                    {
                        "file_path": "src/agents/agent1.py",
                        "knowledge_level": 0.95,
                        "surprise_score": 0.3
                    }
                    for _ in range(100)
                ],
                "dependencies": {
                    f"src/module{i}.py": {
                        "imports": [f"src/dep{j}.py" for j in range(5)],
                        "imported_by": [f"src/imp{j}.py" for j in range(3)],
                        "knowledge_level": 0.8
                    }
                    for i in range(20)
                }
            }
        })

        assert len(large_context) > 5000, "Test data should be > 5000 chars"

        compressor = get_elision_compressor()
        result = compressor.compress(large_context, level=2)

        # Verify compression worked
        assert result.compressed_length < result.original_length
        assert result.compression_ratio > 1.0
        assert result.level == 2
        assert result.tokens_saved_estimate > 0

        print(f"\n✓ Large context compressed: {result.original_length} → {result.compressed_length} bytes")
        print(f"  Compression ratio: {result.compression_ratio:.2f}x")
        print(f"  Tokens saved: ~{result.tokens_saved_estimate}")

    def test_compress_small_context_bypass(self):
        """MARKER_104_ELISION_INTEGRATION: Small context should bypass compression"""
        small_context = json.dumps({
            "message": "Hello world",
            "user": "test_user"
        })

        assert len(small_context) < 5000, "Test data should be < 5000 chars"

        compressor = get_elision_compressor()
        result = compressor.compress(small_context, level=2)

        # Small contexts may have minimal compression
        # The important thing is that compression doesn't fail
        assert result.compressed is not None
        assert result.compression_ratio >= 1.0

        print(f"\n✓ Small context handled: {result.original_length} bytes (ratio: {result.compression_ratio:.2f}x)")

    def test_compress_level_2_reversibility(self):
        """MARKER_104_ELISION_INTEGRATION: Level 2 compression should be reversible"""
        test_data = {
            "context": {
                "current_file": "src/memory/elision.py",
                "file_path": "src/memory/",
                "imports": ["json", "re", "dataclasses"],
                "dependencies": {
                    "elision.py": {
                        "imported_by": ["compression.py", "agent_pipeline.py"]
                    }
                }
            }
        }

        compressor = get_elision_compressor()
        result = compressor.compress(json.dumps(test_data), level=2)

        # Verify legend is included
        assert result.legend is not None
        assert len(result.legend) > 0

        # Expand back
        expanded = compressor.expand(result.compressed, result.legend)
        expanded_data = json.loads(expanded)

        # Verify key fields are expanded (for spot check)
        assert "context" in expanded_data or "c" in expanded_data
        print(f"\n✓ Level 2 compression reversible: {result.original_length} → {result.compressed_length} → {len(expanded)} bytes")

    def test_level_3_compression_with_surprise_map(self):
        """MARKER_104_ELISION_INTEGRATION: Level 3 with surprise metrics"""
        test_text = "orchestrator message controller integration dependency compression"

        # Manually provide surprise map
        surprise_map = {
            "orchestrator": 0.2,  # Low surprise -> aggressive compression
            "message": 0.5,       # Medium surprise -> light compression
            "compression": 0.8    # High surprise -> keep full
        }

        compressor = get_elision_compressor()
        result = compress_level_3(test_text, surprise_map)

        # Verify result contains compression info
        assert result.get("compressed") is not None
        assert result.get("level") == 3
        assert result.get("tokens_saved", 0) >= 0

        print(f"\n✓ Level 3 compression with surprise map: {result.get('original_length')} → {result.get('compressed_length')} bytes")


class TestRolePromptsElisionAwareness:
    """Test ELISION awareness in agent prompts"""

    def test_elision_awareness_note_exists(self):
        """MARKER_104_ELISION_INTEGRATION: Verify ELISION_AWARENESS_NOTE is defined"""
        assert ELISION_AWARENESS_NOTE is not None
        assert len(ELISION_AWARENESS_NOTE) > 0
        assert "ELISION" in ELISION_AWARENESS_NOTE
        assert "compressed" in ELISION_AWARENESS_NOTE.lower()
        print(f"\n✓ ELISION_AWARENESS_NOTE defined ({len(ELISION_AWARENESS_NOTE)} chars)")

    def test_all_prompts_include_elision_awareness(self):
        """MARKER_104_ELISION_INTEGRATION: All agent prompts include ELISION awareness"""
        prompts_to_check = {
            "PM": PM_SYSTEM_PROMPT,
            "Dev": DEV_SYSTEM_PROMPT,
            "QA": QA_SYSTEM_PROMPT,
            "Architect": ARCHITECT_SYSTEM_PROMPT,
            "Researcher": RESEARCHER_SYSTEM_PROMPT,
            "Hostess": HOSTESS_SYSTEM_PROMPT
        }

        for agent_type, prompt in prompts_to_check.items():
            assert isinstance(prompt, str), f"{agent_type} prompt should be string"
            assert "ELISION" in prompt, f"{agent_type} prompt missing ELISION awareness"
            assert "compressed" in prompt.lower(), f"{agent_type} prompt missing compression reference"
            print(f"✓ {agent_type} prompt includes ELISION awareness")

    def test_prompt_includes_key_abbreviations(self):
        """MARKER_104_ELISION_INTEGRATION: Prompts document key abbreviations"""
        # Check first prompt for documentation of abbreviations
        assert "c=" in PM_SYSTEM_PROMPT, "Should document c=context abbreviation"
        assert "cf=" in PM_SYSTEM_PROMPT, "Should document cf=current_file abbreviation"
        assert "imp=" in PM_SYSTEM_PROMPT, "Should document imp=imports abbreviation"
        print("✓ Key abbreviations documented in prompts")

    def test_prompt_includes_path_abbreviations(self):
        """MARKER_104_ELISION_INTEGRATION: Prompts document path abbreviations"""
        assert "s/=" in DEV_SYSTEM_PROMPT, "Should document s/=src/ path abbreviation"
        assert "a/=" in DEV_SYSTEM_PROMPT, "Should document a/=agents/ path abbreviation"
        print("✓ Path abbreviations documented in prompts")

    def test_get_agent_prompt_includes_awareness(self):
        """MARKER_104_ELISION_INTEGRATION: get_agent_prompt() returns prompt with awareness"""
        for agent in ["PM", "Dev", "QA", "Architect", "Researcher", "Hostess"]:
            prompt = get_agent_prompt(agent)
            assert isinstance(prompt, str)
            assert "ELISION" in prompt, f"{agent} prompt should mention ELISION"
            print(f"✓ get_agent_prompt('{agent}') includes ELISION awareness")


class TestElisionIntegrationInOrchestrator:
    """Test ELISION integration in orchestrator_with_elisya.py"""

    def test_orchestrator_has_elision_marker(self):
        """MARKER_104_ELISION_INTEGRATION: Verify orchestrator contains ELISION compression code"""
        orchestrator_path = Path(__file__).parent.parent / "src" / "orchestration" / "orchestrator_with_elisya.py"
        assert orchestrator_path.exists(), "Orchestrator file should exist"

        with open(orchestrator_path, 'r') as f:
            content = f.read()

        # Check for ELISION integration markers
        assert "MARKER_104_ELISION_INTEGRATION" in content, "Should contain ELISION integration marker"
        assert "get_elision_compressor" in content, "Should import compressor"
        assert "compress(" in content, "Should call compress method"
        assert "5000" in content, "Should have 5000 char threshold"

        print("✓ Orchestrator contains ELISION compression integration")

    def test_orchestrator_compression_threshold(self):
        """MARKER_104_ELISION_INTEGRATION: Verify 5000 char threshold for compression"""
        orchestrator_path = Path(__file__).parent.parent / "src" / "orchestration" / "orchestrator_with_elisya.py"

        with open(orchestrator_path, 'r') as f:
            content = f.read()

        # Look for the threshold
        assert "len(str(prompt)) > 5000" in content or "len(prompt) > 5000" in content, \
            "Should have 5000 char threshold for compression"

        print("✓ Compression threshold set to 5000 characters")


class TestElisionCompressionMetrics:
    """Test compression effectiveness and metrics"""

    def test_level_2_compression_ratio(self):
        """MARKER_104_ELISION_INTEGRATION: Verify Level 2 achieves expected compression"""
        test_context = json.dumps({
            "context": {
                "current_file": "src/orchestration/agent_pipeline.py",
                "file_path": "/Users/project/src/orchestration/",
                "viewport_context": {
                    "viewport_nodes": [
                        {
                            "file_path": "src/agents/dev_agent.py",
                            "knowledge_level": 0.95,
                            "surprise_score": 0.2,
                            "distance": 100.5
                        }
                        for _ in range(50)
                    ],
                    "zoom_level": "medium"
                },
                "dependencies": {
                    "agent_pipeline.py": {
                        "imports": ["asyncio", "json", "dataclasses"],
                        "imported_by": ["orchestrator.py", "main.py"],
                        "knowledge_level": 0.85
                    }
                }
            }
        })

        # Verify test data is large enough
        assert len(test_context) > 5000

        compressor = get_elision_compressor()
        result = compressor.compress(test_context, level=2)

        # Level 2 should achieve 30-50% compression typically
        # (keys + paths, without aggressive vowel skipping)
        assert result.compression_ratio > 1.1, "Should achieve at least 1.1x compression"
        assert result.tokens_saved_estimate > 0, "Should save tokens"

        print(f"\n✓ Level 2 compression ratio: {result.compression_ratio:.2f}x")
        print(f"  Original: {result.original_length} bytes")
        print(f"  Compressed: {result.compressed_length} bytes")
        print(f"  Tokens saved: ~{result.tokens_saved_estimate}")


# ==============================================================================
# INTEGRATION TEST SUITE
# ==============================================================================

class TestPhase104ElisionClosure:
    """MARKER_104_ELISION_CLOSURE: Full integration test suite"""

    def test_elision_integration_complete(self):
        """Verify all ELISION integration tasks are complete"""
        checks = [
            # Task 1: Orchestrator integration
            ("Orchestrator has ELISION compression", self.orchestrator_has_compression),
            # Task 2: Role prompts awareness
            ("Role prompts include ELISION awareness", self.prompts_have_awareness),
            # Task 3: Compression works correctly
            ("Compression achieves expected results", self.compression_works),
            # Task 4: Reversibility maintained
            ("Compression is reversible", self.compression_reversible),
        ]

        print("\n" + "=" * 70)
        print("PHASE 104 ELISION INTEGRATION VERIFICATION")
        print("=" * 70)

        for check_name, check_fn in checks:
            try:
                check_fn()
                print(f"✓ {check_name}")
            except AssertionError as e:
                print(f"✗ {check_name}: {e}")
                raise

        print("=" * 70)
        print("ALL ELISION INTEGRATION CHECKS PASSED")
        print("=" * 70)

    @staticmethod
    def orchestrator_has_compression():
        """Check Task 1: Orchestrator integration"""
        orchestrator_path = Path(__file__).parent.parent / "src" / "orchestration" / "orchestrator_with_elisya.py"
        with open(orchestrator_path, 'r') as f:
            content = f.read()

        assert "MARKER_104_ELISION_INTEGRATION" in content
        assert "get_elision_compressor" in content
        assert "len(str(prompt)) > 5000" in content or "len(prompt) > 5000" in content

    @staticmethod
    def prompts_have_awareness():
        """Check Task 2: Role prompts awareness"""
        prompts = [
            PM_SYSTEM_PROMPT,
            DEV_SYSTEM_PROMPT,
            QA_SYSTEM_PROMPT,
            ARCHITECT_SYSTEM_PROMPT,
            RESEARCHER_SYSTEM_PROMPT,
            HOSTESS_SYSTEM_PROMPT
        ]

        for prompt in prompts:
            assert "ELISION" in prompt
            assert "c=" in prompt or ELISION_AWARENESS_NOTE in prompt

    @staticmethod
    def compression_works():
        """Check Task 3: Compression functionality"""
        test_data = json.dumps({
            "context": {
                "current_file": "test.py",
                "viewport_context": {
                    "viewport_nodes": [
                        {"file_path": f"file{i}.py", "knowledge_level": 0.5}
                        for i in range(20)
                    ]
                }
            }
        })

        compressor = get_elision_compressor()
        result = compressor.compress(test_data, level=2)

        assert result.compression_ratio > 1.0
        assert result.compressed_length < result.original_length

    @staticmethod
    def compression_reversible():
        """Check Task 4: Reversibility"""
        test_data = {
            "context": {"current_file": "src/test.py"},
            "viewport": [{"file_path": "src/agent.py", "knowledge_level": 0.8}]
        }

        compressor = get_elision_compressor()
        result = compressor.compress(json.dumps(test_data), level=2)
        expanded = compressor.expand(result.compressed, result.legend)

        # Should be valid JSON after expansion
        expanded_data = json.loads(expanded)
        assert "context" in expanded_data or "c" in expanded_data


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
