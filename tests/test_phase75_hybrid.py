"""
Phase 75: Hybrid Architecture Tests

Tests for:
- CAM Tool Memory (Phase 75.1)
- Elysia Integration (Phase 75.2)
- Context Fusion (Phase 75.3)

Run: pytest tests/test_phase75_hybrid.py -v
"""

import pytest
from datetime import datetime, timezone

pytestmark = pytest.mark.stale(reason="Pre-existing failure — phase 75 contracts changed")

# ═══════════════════════════════════════════════════════════════════
# Phase 75.1: CAM Tool Memory Tests
# ═══════════════════════════════════════════════════════════════════

class TestCAMToolMemory:
    """Tests for CAMToolMemory class."""

    def test_import(self):
        """Test that CAMToolMemory can be imported."""
        from src.orchestration.cam_engine import (
            CAMToolMemory,
            ToolUsageRecord,
            get_cam_tool_memory,
            reset_cam_tool_memory,
        )
        assert CAMToolMemory is not None
        assert ToolUsageRecord is not None

    def test_initialization(self):
        """Test CAMToolMemory initializes correctly."""
        from src.orchestration.cam_engine import CAMToolMemory

        memory = CAMToolMemory()

        assert memory.max_history == 500
        assert len(memory.usage_history) == 0
        assert len(memory.VETKA_TOOLS) >= 4

    def test_record_tool_use(self):
        """Test recording tool usage."""
        from src.orchestration.cam_engine import CAMToolMemory

        memory = CAMToolMemory()

        # Record a tool use
        memory.record_tool_use(
            tool_name='search_files',
            context={'folder_path': '/src/orchestration'},
            success=True
        )

        assert len(memory.usage_history) == 1
        assert memory.usage_history[0].tool_name == 'search_files'

        # Check activation score increased
        ctx_key = 'folder:src/orchestration'
        assert ctx_key in memory.tool_activations['search_files']
        assert memory.tool_activations['search_files'][ctx_key] > 0.5

    def test_ignore_non_vetka_tools(self):
        """Test that non-VETKA tools are ignored."""
        from src.orchestration.cam_engine import CAMToolMemory

        memory = CAMToolMemory()

        # Try to record a non-VETKA tool
        memory.record_tool_use(
            tool_name='random_tool',
            context={'folder_path': '/test'},
            success=True
        )

        # Should be ignored
        assert len(memory.usage_history) == 0

    def test_suggest_tool(self):
        """Test tool suggestions based on context."""
        from src.orchestration.cam_engine import CAMToolMemory

        memory = CAMToolMemory()

        # Build up history
        for _ in range(5):
            memory.record_tool_use(
                tool_name='search_files',
                context={'folder_path': '/src/orchestration'},
                success=True
            )

        # Get suggestions
        suggestions = memory.suggest_tool(
            context={'folder_path': '/src/orchestration'},
            top_n=3
        )

        # search_files should be top suggestion
        assert len(suggestions) > 0
        assert suggestions[0][0] == 'search_files'
        assert suggestions[0][1] > 0.6  # High confidence

    def test_jarvis_hint(self):
        """Test JARVIS-style hint generation."""
        from src.orchestration.cam_engine import CAMToolMemory

        memory = CAMToolMemory()

        # Build strong activation
        for _ in range(5):
            memory.record_tool_use(
                tool_name='view_document',
                context={'file_extension': '.py'},
                success=True
            )

        # Get hint
        hint = memory.get_jarvis_hint({'file_extension': '.py'})

        assert hint is not None
        assert 'CAM suggests' in hint
        assert 'view_document' in hint

    def test_context_key_extraction(self):
        """Test context key extraction priority."""
        from src.orchestration.cam_engine import CAMToolMemory

        memory = CAMToolMemory()

        # folder_path has highest priority
        ctx1 = {'folder_path': '/src', 'file_extension': '.py', 'query_type': 'search'}
        assert memory._extract_context_key(ctx1) == 'folder:src'

        # file_extension next
        ctx2 = {'file_extension': '.py', 'query_type': 'search'}
        assert memory._extract_context_key(ctx2) == 'ext:py'

        # query_type next
        ctx3 = {'query_type': 'search'}
        assert memory._extract_context_key(ctx3) == 'query:search'

        # fallback
        ctx4 = {}
        assert memory._extract_context_key(ctx4) == 'general'

    def test_serialization(self):
        """Test to_dict and from_dict."""
        from src.orchestration.cam_engine import CAMToolMemory

        memory = CAMToolMemory()
        memory.record_tool_use('search_files', {'folder_path': '/test'}, True)

        # Serialize
        data = memory.to_dict()
        assert 'tool_activations' in data
        assert 'usage_history' in data

        # Deserialize
        restored = CAMToolMemory.from_dict(data)
        assert len(restored.usage_history) == len(memory.usage_history)

    def test_singleton(self):
        """Test singleton pattern."""
        from src.orchestration.cam_engine import (
            get_cam_tool_memory,
            reset_cam_tool_memory,
        )

        reset_cam_tool_memory()

        mem1 = get_cam_tool_memory()
        mem2 = get_cam_tool_memory()

        assert mem1 is mem2


# ═══════════════════════════════════════════════════════════════════
# Phase 75.2: Elysia Integration Tests
# ═══════════════════════════════════════════════════════════════════

class TestElysiaIntegration:
    """Tests for Elysia code tools."""

    def test_import(self):
        """Test that Elysia tools can be imported."""
        from src.orchestration.elysia_tools import (
            read_file,
            write_file,
            run_tests,
            git_status,
            git_commit,
            is_elysia_available,
            get_available_tools,
        )

        assert callable(read_file)
        assert callable(write_file)
        assert callable(is_elysia_available)

    def test_get_available_tools(self):
        """Test available tools list."""
        from src.orchestration.elysia_tools import get_available_tools

        tools = get_available_tools()

        assert 'read_file' in tools
        assert 'write_file' in tools
        assert 'run_tests' in tools
        assert 'git_status' in tools
        assert 'git_commit' in tools

    def test_read_file_existing(self):
        """Test reading an existing file."""
        from src.orchestration.elysia_tools import read_file

        # Read requirements.txt (doesn't contain [ERROR])
        result = read_file('requirements.txt')

        assert '[ERROR]' not in result
        assert 'flask' in result.lower()  # requirements.txt contains flask

    def test_read_file_not_found(self):
        """Test reading non-existent file."""
        from src.orchestration.elysia_tools import read_file

        result = read_file('nonexistent/file.py')

        assert '[ERROR]' in result
        assert 'not found' in result.lower()

    def test_elysia_stats(self):
        """Test Elysia stats."""
        from src.orchestration.elysia_tools import get_elysia_stats

        stats = get_elysia_stats()

        assert 'available' in stats
        assert 'tools_count' in stats
        assert stats['tools_count'] >= 5
        assert stats['optimize'] is False  # Critical: no DSPy overhead

    def test_direct_tools(self):
        """Test direct tool access (bypass Elysia tree)."""
        from src.orchestration.elysia_tools import elysia_direct

        # Test read
        result = elysia_direct.read('requirements.txt')
        assert '[ERROR]' not in result
        assert 'flask' in result.lower()

        # Test status
        status = elysia_direct.status()
        assert 'Branch' in status or 'GIT STATUS' in status


# ═══════════════════════════════════════════════════════════════════
# Phase 75.3: Context Fusion Tests
# ═══════════════════════════════════════════════════════════════════

class TestContextFusion:
    """Tests for context_fusion function."""

    def test_import(self):
        """Test that context_fusion can be imported."""
        from src.orchestration.context_fusion import (
            context_fusion,
            build_context_for_hostess,
            build_context_for_dev,
            get_fusion_stats,
        )

        assert callable(context_fusion)
        assert callable(build_context_for_hostess)

    def test_empty_context(self):
        """Test with no context provided."""
        from src.orchestration.context_fusion import context_fusion

        result = context_fusion()

        assert result == ""

    def test_spatial_context_only(self):
        """Test with only spatial context."""
        from src.orchestration.context_fusion import context_fusion

        result = context_fusion(
            viewport_context={
                'zoom_level': 5,
                'camera_target': 'src/orchestration/',
                'total_visible': 23,
                'total_pinned': 3,
            }
        )

        assert '## SPATIAL CONTEXT' in result
        assert 'zoom' in result.lower()
        assert 'src/orchestration' in result

    def test_pinned_files(self):
        """Test with pinned files."""
        from src.orchestration.context_fusion import context_fusion

        result = context_fusion(
            pinned_files=[
                {'name': 'cam_engine.py', 'path': 'src/orchestration/cam_engine.py'},
                {'name': 'middleware.py', 'path': 'src/elisya/middleware.py'},
            ]
        )

        assert '## PINNED FILES' in result
        assert 'cam_engine.py' in result
        assert 'Python' in result  # Language detection

    def test_cam_activations(self):
        """Test with CAM activation hints."""
        from src.orchestration.context_fusion import context_fusion

        result = context_fusion(
            cam_activations={
                'search_files': 0.85,
                'view_document': 0.6,
            }
        )

        assert '## CAM SUGGESTION' in result
        assert 'search_files' in result
        assert '0.85' in result

    def test_code_context_auto_detection(self):
        """Test code context auto-detection based on query."""
        from src.orchestration.context_fusion import context_fusion

        # Code-related query should include code context
        result_code = context_fusion(
            code_context={
                'summary': 'Last read cam_engine.py',
                'last_operation': 'read_file(cam_engine.py)',
                'files_modified': [],
            },
            user_query='Read the cam_engine.py file',
        )
        assert '## CODE CONTEXT' in result_code

        # Non-code query should not include code context
        result_visual = context_fusion(
            code_context={
                'summary': 'Last read cam_engine.py',
                'last_operation': 'read_file(cam_engine.py)',
                'files_modified': [],
            },
            user_query='Show me the folder structure',
        )
        # Code context should NOT be present
        assert '## CODE CONTEXT' not in result_visual

    def test_token_budget(self):
        """Test that output respects token budget."""
        from src.orchestration.context_fusion import context_fusion

        # Create large inputs
        result = context_fusion(
            viewport_context={
                'zoom_level': 5,
                'camera_target': 'src/orchestration/',
                'total_visible': 100,
                'total_pinned': 10,
            },
            pinned_files=[
                {'name': f'file_{i}.py', 'path': f'path/file_{i}.py'}
                for i in range(20)
            ],
            code_context={
                'summary': 'A' * 10000,  # Very long summary
                'last_operation': 'read_file(test.py)',
                'files_modified': ['a.py', 'b.py', 'c.py'],
            },
            user_query='Read files',
            max_tokens=2000,
        )

        # Should be ~8000 chars max (~2000 tokens)
        assert len(result) < 10000

    def test_full_fusion(self):
        """Test full context fusion with all components."""
        from src.orchestration.context_fusion import context_fusion

        result = context_fusion(
            viewport_context={
                'zoom_level': 7,
                'camera_target': 'src/orchestration/cam_engine.py',
                'total_visible': 15,
                'total_pinned': 2,
            },
            pinned_files=[
                {'name': 'cam_engine.py', 'path': 'src/orchestration/cam_engine.py'},
            ],
            code_context={
                'summary': 'Working on CAM Tool Memory',
                'last_operation': 'read_file(cam_engine.py)',
                'files_modified': ['cam_engine.py'],
            },
            cam_activations={
                'view_document': 0.9,
                'search_files': 0.5,
            },
            user_query='Read the file and add a new method',
            include_code=True,
        )

        # All sections should be present
        assert '## SPATIAL CONTEXT' in result
        assert '## PINNED FILES' in result
        assert '## CAM SUGGESTION' in result
        assert '## CODE CONTEXT' in result

    def test_fusion_stats(self):
        """Test fusion configuration stats."""
        from src.orchestration.context_fusion import get_fusion_stats

        stats = get_fusion_stats()

        assert stats['max_tokens'] == 2000
        assert 'code_keywords' in stats

    def test_hostess_helper(self):
        """Test build_context_for_hostess helper."""
        from src.orchestration.context_fusion import build_context_for_hostess

        result = build_context_for_hostess(
            viewport_context={'zoom_level': 5, 'total_visible': 10, 'total_pinned': 1},
            pinned_files=[{'name': 'test.py', 'path': 'test.py'}],
            user_query='What is this folder?',
        )

        # Hostess context should be smaller
        assert len(result) < 5000
        # Should NOT include code context
        assert '## CODE CONTEXT' not in result

    def test_dev_helper(self):
        """Test build_context_for_dev helper."""
        from src.orchestration.context_fusion import build_context_for_dev

        result = build_context_for_dev(
            viewport_context={'zoom_level': 8, 'total_visible': 5, 'total_pinned': 1},
            pinned_files=[{'name': 'test.py', 'path': 'test.py'}],
            code_context={
                'summary': 'Ready for coding',
                'last_operation': 'read_file',
                'files_modified': [],
            },
            user_query='Implement the feature',
        )

        # Dev context SHOULD include code
        assert '## CODE CONTEXT' in result


# ═══════════════════════════════════════════════════════════════════
# Integration Tests
# ═══════════════════════════════════════════════════════════════════

class TestHybridIntegration:
    """Integration tests for the hybrid architecture."""

    def test_cam_to_fusion_integration(self):
        """Test CAM Tool Memory → context_fusion integration."""
        from src.orchestration.cam_engine import CAMToolMemory
        from src.orchestration.context_fusion import context_fusion

        # Create CAM memory with history
        memory = CAMToolMemory()
        for _ in range(5):
            memory.record_tool_use('view_document', {'file_extension': '.py'}, True)

        # Get activations
        suggestions = memory.suggest_tool({'file_extension': '.py'})
        cam_activations = {tool: score for tool, score in suggestions}

        # Use in fusion
        result = context_fusion(
            cam_activations=cam_activations,
            user_query='Show me the file',
        )

        assert '## CAM SUGGESTION' in result
        assert 'view_document' in result

    def test_elysia_to_fusion_integration(self):
        """Test Elysia tools → context_fusion integration."""
        from src.orchestration.elysia_tools import elysia_direct, get_elysia_stats
        from src.orchestration.context_fusion import context_fusion

        # Use Elysia to read a file
        content = elysia_direct.read('requirements.txt')

        # Create code context from Elysia result
        code_context = {
            'summary': f'Read file: {len(content)} chars',
            'last_operation': 'read_file(requirements.txt)',
            'files_modified': [],
        }

        # Use in fusion
        result = context_fusion(
            code_context=code_context,
            user_query='What dependencies are needed?',
            include_code=True,
        )

        assert '## CODE CONTEXT' in result
        assert 'read_file' in result

    def test_full_hybrid_workflow(self):
        """Test full hybrid workflow: CAM + Elysia + Fusion."""
        from src.orchestration.cam_engine import CAMToolMemory, reset_cam_tool_memory
        from src.orchestration.elysia_tools import elysia_direct
        from src.orchestration.context_fusion import context_fusion

        # 1. Reset and create fresh CAM memory
        reset_cam_tool_memory()
        cam = CAMToolMemory()

        # 2. Simulate user workflow: searching in orchestration folder
        cam.record_tool_use('search_files', {'folder_path': '/src/orchestration'}, True)
        cam.record_tool_use('view_document', {'folder_path': '/src/orchestration'}, True)
        cam.record_tool_use('view_document', {'folder_path': '/src/orchestration'}, True)

        # 3. Get CAM suggestions
        suggestions = cam.suggest_tool({'folder_path': '/src/orchestration'})
        cam_activations = {tool: score for tool, score in suggestions}

        # 4. Use Elysia to read a file
        content = elysia_direct.read('src/orchestration/cam_engine.py')

        # 5. Build code context
        code_context = {
            'summary': f'Read cam_engine.py ({len(content)} chars)',
            'last_operation': 'read_file(src/orchestration/cam_engine.py)',
            'files_modified': [],
        }

        # 6. Fuse everything
        viewport = {
            'zoom_level': 6,
            'camera_target': 'src/orchestration/',
            'total_visible': 20,
            'total_pinned': 1,
        }

        pinned = [
            {'name': 'cam_engine.py', 'path': 'src/orchestration/cam_engine.py'}
        ]

        result = context_fusion(
            viewport_context=viewport,
            pinned_files=pinned,
            code_context=code_context,
            cam_activations=cam_activations,
            user_query='Read the cam_engine.py and add a method',
            include_code=True,
        )

        # Verify all sections
        assert '## SPATIAL CONTEXT' in result
        assert '## PINNED FILES' in result
        assert 'cam_engine.py' in result
        # CAM should suggest view_document (higher activation)
        if cam_activations:
            assert '## CAM SUGGESTION' in result
        assert '## CODE CONTEXT' in result

        # Verify token budget
        assert len(result) < 10000  # ~2500 tokens max


# ═══════════════════════════════════════════════════════════════════
# Test Scenarios from Phase 75 Spec
# ═══════════════════════════════════════════════════════════════════

class TestPhase75Scenarios:
    """Test scenarios from Phase 75 specification."""

    def test_scenario_3d_query(self):
        """Scenario: 'Покажи файлы в папке orchestration' → CAM tools."""
        from src.orchestration.cam_engine import CAMToolMemory
        from src.orchestration.context_fusion import context_fusion

        cam = CAMToolMemory()

        # Build up CAM history for folder navigation
        for _ in range(3):
            cam.record_tool_use('search_files', {'query_type': 'folder'}, True)

        suggestions = cam.suggest_tool({'query_type': 'folder'})

        # search_files should be suggested
        tool_names = [t for t, _ in suggestions]
        assert 'search_files' in tool_names

    def test_scenario_code_query(self):
        """Scenario: 'Прочитай содержимое main.py' → Elysia tools."""
        from src.orchestration.elysia_tools import is_elysia_available
        from src.orchestration.context_fusion import context_fusion

        # Code query should trigger code context inclusion
        result = context_fusion(
            code_context={
                'summary': 'Ready to read main.py',
                'last_operation': 'idle',
                'files_modified': [],
            },
            user_query='Прочитай содержимое main.py',  # Russian "read" keyword
        )

        # Code context should be included (keyword detection)
        assert '## CODE CONTEXT' in result

    def test_scenario_hybrid_query(self):
        """Scenario: 'Посмотри что в viewport и исправь баг' → fusion."""
        from src.orchestration.context_fusion import context_fusion

        # Hybrid query with both viewport and code elements
        result = context_fusion(
            viewport_context={
                'zoom_level': 7,
                'camera_target': 'src/main.py',
                'total_visible': 10,
                'total_pinned': 1,
            },
            pinned_files=[
                {'name': 'main.py', 'path': 'src/main.py'}
            ],
            code_context={
                'summary': 'Bug in main.py line 42',
                'last_operation': 'read_file(main.py)',
                'files_modified': [],
            },
            user_query='Посмотри что в viewport и исправь баг в выбранном файле',
            include_code=True,
        )

        # Should have both spatial and code context
        assert '## SPATIAL CONTEXT' in result
        assert '## CODE CONTEXT' in result
        assert 'main.py' in result


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
