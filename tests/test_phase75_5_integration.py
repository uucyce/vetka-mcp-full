"""
Phase 75.5 Integration Tests — Spatial Context Flow Through LangGraph Chain

@file test_phase75_5_integration.py
@status ACTIVE
@phase Phase 75.5 — Context Fusion Integration
@lastAudit 2026-01-20

Tests verify that viewport_context and pinned_files flow correctly through:
1. VETKAState (langgraph_state.py)
2. LangGraph nodes (langgraph_nodes.py)
3. Orchestrator (orchestrator_with_elisya.py)
4. context_fusion module (Phase 75.3)
"""

import pytest
from typing import Dict, Any, List, Optional


# ════════════════════════════════════════════════════════════════════
# [PHASE75.5-TEST-1] VETKAState Field Tests
# ════════════════════════════════════════════════════════════════════

class TestVETKAStateSpatialFields:
    """Test that VETKAState properly stores spatial context fields."""

    def test_state_has_viewport_context_field(self):
        """VETKAState should have viewport_context field."""
        from src.orchestration.langgraph_state import VETKAState

        # TypedDict annotations check
        annotations = VETKAState.__annotations__
        assert 'viewport_context' in annotations
        assert annotations['viewport_context'] == Optional[Dict[str, Any]]

    def test_state_has_pinned_files_field(self):
        """VETKAState should have pinned_files field."""
        from src.orchestration.langgraph_state import VETKAState

        annotations = VETKAState.__annotations__
        assert 'pinned_files' in annotations
        assert annotations['pinned_files'] == Optional[List[Dict[str, Any]]]

    def test_state_has_code_context_field(self):
        """VETKAState should have code_context field."""
        from src.orchestration.langgraph_state import VETKAState

        annotations = VETKAState.__annotations__
        assert 'code_context' in annotations
        assert annotations['code_context'] == Optional[Dict[str, Any]]


# ════════════════════════════════════════════════════════════════════
# [PHASE75.5-TEST-2] create_initial_state() Tests
# ════════════════════════════════════════════════════════════════════

class TestCreateInitialStateSpatialParams:
    """Test create_initial_state() accepts and stores spatial context."""

    def test_create_state_with_viewport_context(self):
        """create_initial_state should accept viewport_context parameter."""
        from src.orchestration.langgraph_state import create_initial_state

        viewport = {
            'focus_node': 'src/main.py',
            'zoom': 2.5,
            'visible_files': ['src/main.py', 'src/utils.py']
        }

        state = create_initial_state(
            workflow_id='test-001',
            context='Test request',
            viewport_context=viewport
        )

        assert state['viewport_context'] == viewport
        assert state['viewport_context']['focus_node'] == 'src/main.py'

    def test_create_state_with_pinned_files(self):
        """create_initial_state should accept pinned_files parameter."""
        from src.orchestration.langgraph_state import create_initial_state

        pinned = [
            {'path': 'src/main.py', 'reason': 'entry point'},
            {'path': 'tests/test_main.py', 'reason': 'test file'}
        ]

        state = create_initial_state(
            workflow_id='test-002',
            context='Test request',
            pinned_files=pinned
        )

        assert state['pinned_files'] == pinned
        assert len(state['pinned_files']) == 2

    def test_create_state_with_code_context(self):
        """create_initial_state should accept code_context parameter."""
        from src.orchestration.langgraph_state import create_initial_state

        code_ctx = {
            'summary': 'Working on auth module',
            'last_operation': 'read_file',
            'files_modified': ['src/auth.py']
        }

        state = create_initial_state(
            workflow_id='test-003',
            context='Test request',
            code_context=code_ctx
        )

        assert state['code_context'] == code_ctx
        assert state['code_context']['summary'] == 'Working on auth module'

    def test_create_state_with_all_spatial_params(self):
        """create_initial_state should accept all spatial parameters together."""
        from src.orchestration.langgraph_state import create_initial_state

        viewport = {'focus_node': 'src/api.py', 'zoom': 1.0}
        pinned = [{'path': 'README.md', 'reason': 'documentation'}]
        code_ctx = {'summary': 'API development', 'last_operation': 'write_file'}

        state = create_initial_state(
            workflow_id='test-004',
            context='Create API endpoint',
            viewport_context=viewport,
            pinned_files=pinned,
            code_context=code_ctx
        )

        assert state['viewport_context'] == viewport
        assert state['pinned_files'] == pinned
        assert state['code_context'] == code_ctx

        # Also verify other fields still work
        assert state['workflow_id'] == 'test-004'
        assert state['context'] == 'Create API endpoint'

    def test_create_state_spatial_params_optional(self):
        """Spatial parameters should be optional (backward compatible)."""
        from src.orchestration.langgraph_state import create_initial_state

        # Call without any spatial params - should not raise
        state = create_initial_state(
            workflow_id='test-005',
            context='Legacy request'
        )

        assert state['viewport_context'] is None
        assert state['pinned_files'] is None
        assert state['code_context'] is None


# ════════════════════════════════════════════════════════════════════
# [PHASE75.5-TEST-3] Context Fusion Integration Tests
# ════════════════════════════════════════════════════════════════════

class TestContextFusionIntegration:
    """Test that context_fusion module integrates with state."""

    def test_build_context_for_hostess_with_viewport(self):
        """build_context_for_hostess should use viewport_context."""
        from src.orchestration.context_fusion import build_context_for_hostess

        viewport = {
            'focus_node': 'src/components/Button.tsx',
            'zoom': 3.0,
            'visible_files': ['src/components/Button.tsx', 'src/styles/button.css']
        }

        result = build_context_for_hostess(
            viewport_context=viewport,
            pinned_files=None,
            user_query='How does this button work?'
        )

        assert result is not None
        assert 'Button' in result or 'focus' in result.lower()

    def test_build_context_for_dev_with_all_context(self):
        """build_context_for_dev should combine all context types."""
        from src.orchestration.context_fusion import build_context_for_dev

        viewport = {'focus_node': 'src/api.py', 'zoom': 2.0}
        pinned = [{'path': 'src/models.py', 'reason': 'data models'}]
        code_ctx = {'summary': 'API work', 'last_operation': 'read_file'}

        result = build_context_for_dev(
            viewport_context=viewport,
            pinned_files=pinned,
            code_context=code_ctx,
            user_query='Add new endpoint'
        )

        assert result is not None
        # Should contain some spatial context
        assert len(result) > 0

    def test_context_fusion_with_empty_inputs(self):
        """Context fusion should handle empty inputs gracefully."""
        from src.orchestration.context_fusion import build_context_for_hostess

        # All None - should not crash
        result = build_context_for_hostess(
            viewport_context=None,
            pinned_files=None,
            user_query=''
        )

        # Should return empty or minimal context
        assert result is not None or result == ''


# ════════════════════════════════════════════════════════════════════
# [PHASE75.5-TEST-4] LangGraph Nodes Import Tests
# ════════════════════════════════════════════════════════════════════

class TestLangGraphNodesImports:
    """Test that langgraph_nodes imports context_fusion correctly."""

    def test_nodes_import_build_context_for_hostess(self):
        """langgraph_nodes should import build_context_for_hostess."""
        from src.orchestration import langgraph_nodes

        # Check module has the import
        assert hasattr(langgraph_nodes, 'build_context_for_hostess')

    def test_nodes_import_build_context_for_dev(self):
        """langgraph_nodes should import build_context_for_dev."""
        from src.orchestration import langgraph_nodes

        assert hasattr(langgraph_nodes, 'build_context_for_dev')


# ════════════════════════════════════════════════════════════════════
# [PHASE75.5-TEST-5] State Access Pattern Tests
# ════════════════════════════════════════════════════════════════════

class TestStateAccessPatterns:
    """Test that state.get() works correctly for spatial fields."""

    def test_state_get_viewport_context(self):
        """state.get('viewport_context') should work."""
        from src.orchestration.langgraph_state import create_initial_state

        viewport = {'focus_node': 'test.py'}
        state = create_initial_state(
            workflow_id='test-010',
            context='Test',
            viewport_context=viewport
        )

        # TypedDict supports .get()
        result = state.get('viewport_context')
        assert result == viewport

    def test_state_get_pinned_files(self):
        """state.get('pinned_files') should work."""
        from src.orchestration.langgraph_state import create_initial_state

        pinned = [{'path': 'file.py'}]
        state = create_initial_state(
            workflow_id='test-011',
            context='Test',
            pinned_files=pinned
        )

        result = state.get('pinned_files')
        assert result == pinned

    def test_state_get_with_default_none(self):
        """state.get() should return None for unset spatial fields."""
        from src.orchestration.langgraph_state import create_initial_state

        state = create_initial_state(
            workflow_id='test-012',
            context='Test'
        )

        # Should return None, not raise KeyError
        assert state.get('viewport_context') is None
        assert state.get('pinned_files') is None
        assert state.get('code_context') is None


# ════════════════════════════════════════════════════════════════════
# [PHASE75.5-TEST-6] Backward Compatibility Tests
# ════════════════════════════════════════════════════════════════════

class TestBackwardCompatibility:
    """Test that existing code continues to work."""

    def test_existing_state_fields_unchanged(self):
        """Existing VETKAState fields should still work."""
        from src.orchestration.langgraph_state import create_initial_state

        state = create_initial_state(
            workflow_id='test-020',
            context='Create a calculator',
            lod_level='MEDIUM',
            max_retries=3
        )

        # All existing fields should work
        assert state['workflow_id'] == 'test-020'
        assert state['context'] == 'Create a calculator'
        assert state['lod_level'] == 'MEDIUM'
        assert state['max_retries'] == 3
        assert state['messages'] is not None
        assert state['eval_score'] == 0.0
        assert state['retry_count'] == 0

    def test_state_to_elisya_dict_still_works(self):
        """state_to_elisya_dict should still work with new fields."""
        from src.orchestration.langgraph_state import (
            create_initial_state,
            state_to_elisya_dict
        )

        state = create_initial_state(
            workflow_id='test-021',
            context='Test',
            viewport_context={'focus': 'test.py'}
        )

        # Should not raise
        elisya_dict = state_to_elisya_dict(state)

        assert elisya_dict['workflow_id'] == 'test-021'
        assert elisya_dict['context'] == 'Test'


# ════════════════════════════════════════════════════════════════════
# [PHASE75.5-TEST-7] End-to-End Flow Test
# ════════════════════════════════════════════════════════════════════

class TestEndToEndFlow:
    """Test complete flow from state creation to node access."""

    def test_full_flow_viewport_to_node(self):
        """Test viewport flows from state creation to node access."""
        from src.orchestration.langgraph_state import create_initial_state
        from src.orchestration.context_fusion import build_context_for_hostess

        # 1. Create state with viewport
        viewport = {
            'focus_node': 'src/orchestration/langgraph_nodes.py',
            'zoom': 2.0,
            'visible_files': ['langgraph_nodes.py', 'langgraph_state.py']
        }

        state = create_initial_state(
            workflow_id='e2e-001',
            context='Explain the hostess node',
            viewport_context=viewport
        )

        # 2. Access viewport from state (as node would)
        vp = state.get('viewport_context')
        assert vp is not None
        assert vp['focus_node'] == 'src/orchestration/langgraph_nodes.py'

        # 3. Build context using viewport (as hostess_node would)
        context = build_context_for_hostess(
            viewport_context=vp,
            pinned_files=state.get('pinned_files'),
            user_query=state.get('context', '')
        )

        # Should have some content
        assert context is not None

    def test_full_flow_pinned_to_dev_context(self):
        """Test pinned_files flows to dev context building."""
        from src.orchestration.langgraph_state import create_initial_state
        from src.orchestration.context_fusion import build_context_for_dev

        # 1. Create state with pinned files
        pinned = [
            {'path': 'src/api/handlers.py', 'reason': 'API handlers'},
            {'path': 'tests/test_api.py', 'reason': 'API tests'}
        ]

        state = create_initial_state(
            workflow_id='e2e-002',
            context='Add authentication to API',
            pinned_files=pinned
        )

        # 2. Access from state
        pf = state.get('pinned_files')
        assert pf is not None
        assert len(pf) == 2

        # 3. Build dev context
        code_ctx = {'summary': 'Working on API', 'last_operation': 'analyzing'}

        dev_context = build_context_for_dev(
            viewport_context=state.get('viewport_context'),
            pinned_files=pf,
            code_context=code_ctx,
            user_query=state.get('context', '')
        )

        # Should include pinned file info
        assert dev_context is not None


# ════════════════════════════════════════════════════════════════════
# Run Configuration
# ════════════════════════════════════════════════════════════════════

if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
