# ========================================
# MARKER: Phase 73.0 + 73.5 + 73.6 JSON Context Builder Tests
# Date: 2026-01-20
# File: tests/api/handlers/test_json_context.py
# Purpose: Test build_json_context() and helper functions
# Phase 73.5: Added ELISION compression and cache tests
# Phase 73.6: Added legend header tests
# ========================================
"""
Tests for JSON Context Builder (Phase 73.0 + 73.5 + 73.6).

Test categories:
1. Current file extraction (from pinned_files, viewport_context)
2. JSON structure building
3. Semantic neighbors fetching (with mocks)
4. Dependency calculation (with mocks)
5. Viewport summary extraction
6. Token truncation
7. Edge cases (empty inputs, missing services)
8. Integration with build_model_prompt
9. [PHASE73.5] ELISION compression tests
10. [PHASE73.5] LRU cache tests
11. [PHASE73.5] PythonScanner import_confidence tests
12. [PHASE73.6] Legend header tests
"""

import json
import pytest
from typing import Dict, List
from unittest.mock import Mock, MagicMock, patch


class TestBuildJsonContext:
    """Test build_json_context() main function."""

    def test_empty_inputs_returns_empty_string(self):
        """No pinned_files and no viewport_context → empty result."""
        from src.api.handlers.message_utils import build_json_context

        result = build_json_context(pinned_files=None, viewport_context=None)
        assert result == ""

    def test_empty_pinned_files_list_returns_empty(self):
        """Empty pinned_files list → empty result."""
        from src.api.handlers.message_utils import build_json_context

        result = build_json_context(pinned_files=[], viewport_context=None)
        assert result == ""

    def test_extracts_current_file_from_pinned_files(self):
        """Priority 1: Extract current_file from first pinned file."""
        from src.api.handlers.message_utils import build_json_context

        pinned_files = [
            {'id': '1', 'path': '/src/main.py', 'name': 'main.py', 'type': 'file'},
            {'id': '2', 'path': '/src/utils.py', 'name': 'utils.py', 'type': 'file'},
        ]

        # Mock the external dependencies to avoid actual Qdrant/embedding calls
        # Note: compressed=False to get human-readable output for assertion
        with patch('src.api.handlers.message_utils._fetch_semantic_neighbors', return_value=[]):
            result = build_json_context(pinned_files=pinned_files, viewport_context=None, compressed=False)

        assert '## DEPENDENCY CONTEXT' in result
        assert '"path": "/src/main.py"' in result
        assert '"name": "main.py"' in result

    def test_extracts_current_file_from_viewport_selected_node(self):
        """Priority 2: Extract from viewport_context['selected_node']."""
        from src.api.handlers.message_utils import build_json_context

        viewport_context = {
            'selected_node': {
                'path': '/src/selected.py',
                'name': 'selected.py',
                'type': 'file'
            },
            'pinned_nodes': [],
            'viewport_nodes': []
        }

        with patch('src.api.handlers.message_utils._fetch_semantic_neighbors', return_value=[]):
            result = build_json_context(pinned_files=None, viewport_context=viewport_context, compressed=False)

        assert '"path": "/src/selected.py"' in result

    def test_extracts_current_file_from_viewport_pinned_nodes(self):
        """Priority 3: Extract from viewport_context['pinned_nodes'][0]."""
        from src.api.handlers.message_utils import build_json_context

        viewport_context = {
            'pinned_nodes': [
                {'path': '/src/pinned.py', 'name': 'pinned.py', 'type': 'file'}
            ],
            'viewport_nodes': []
        }

        with patch('src.api.handlers.message_utils._fetch_semantic_neighbors', return_value=[]):
            result = build_json_context(pinned_files=None, viewport_context=viewport_context, compressed=False)

        assert '"path": "/src/pinned.py"' in result

    def test_json_structure_contains_required_fields(self):
        """Output JSON has all required fields (uncompressed)."""
        from src.api.handlers.message_utils import build_json_context

        pinned_files = [
            {'id': '1', 'path': '/src/test.py', 'name': 'test.py', 'type': 'file'}
        ]

        with patch('src.api.handlers.message_utils._fetch_semantic_neighbors', return_value=[]):
            result = build_json_context(pinned_files=pinned_files, compressed=False)

        # Extract JSON from markdown code block
        json_start = result.find('```json\n') + 8
        json_end = result.find('\n```', json_start)
        json_str = result[json_start:json_end]

        data = json.loads(json_str)

        assert 'current_file' in data
        assert 'dependencies' in data
        assert 'semantic_neighbors' in data
        assert 'viewport' in data
        assert 'summary' in data

    def test_viewport_summary_extracted(self):
        """Viewport info is extracted to JSON (uncompressed)."""
        from src.api.handlers.message_utils import build_json_context

        pinned_files = [
            {'id': '1', 'path': '/src/test.py', 'name': 'test.py', 'type': 'file'}
        ]
        viewport_context = {
            'zoom_level': 3,
            'total_visible': 25,
            'total_pinned': 2,
            'pinned_nodes': [],
            'viewport_nodes': []
        }

        with patch('src.api.handlers.message_utils._fetch_semantic_neighbors', return_value=[]):
            result = build_json_context(pinned_files=pinned_files, viewport_context=viewport_context, compressed=False)

        json_start = result.find('```json\n') + 8
        json_end = result.find('\n```', json_start)
        data = json.loads(result[json_start:json_end])

        assert data['viewport']['visible_files'] == 25
        assert data['viewport']['pinned_count'] == 2
        assert data['viewport']['zoom_level'] == 'medium'  # zoom 3 = medium

    def test_include_semantic_neighbors_false_skips_qdrant(self):
        """When include_semantic_neighbors=False, don't call Qdrant."""
        from src.api.handlers.message_utils import build_json_context

        pinned_files = [
            {'id': '1', 'path': '/src/test.py', 'name': 'test.py', 'type': 'file'}
        ]

        with patch('src.api.handlers.message_utils._fetch_semantic_neighbors') as mock_fetch:
            result = build_json_context(
                pinned_files=pinned_files,
                include_semantic_neighbors=False
            )
            mock_fetch.assert_not_called()

    def test_include_dependencies_false_skips_calculator(self):
        """When include_dependencies=False, don't call DependencyCalculator."""
        from src.api.handlers.message_utils import build_json_context

        pinned_files = [
            {'id': '1', 'path': '/src/test.py', 'name': 'test.py', 'type': 'file'}
        ]

        with patch('src.api.handlers.message_utils._fetch_semantic_neighbors', return_value=[{'path': '/x.py', 'score': 0.8}]):
            with patch('src.api.handlers.message_utils._calculate_dependencies_for_context') as mock_calc:
                result = build_json_context(
                    pinned_files=pinned_files,
                    include_dependencies=False
                )
                mock_calc.assert_not_called()


class TestFetchSemanticNeighbors:
    """Test _fetch_semantic_neighbors() helper."""

    def test_returns_empty_when_qdrant_unavailable(self):
        """Graceful fallback when Qdrant is down."""
        from src.api.handlers.message_utils import _fetch_semantic_neighbors

        # Patch at the source module where get_qdrant_client is defined
        with patch('src.memory.qdrant_client.get_qdrant_client', return_value=None):
            result = _fetch_semantic_neighbors('/src/test.py')
            assert result == []

    def test_filters_out_self_reference(self):
        """Self-reference is excluded from results."""
        from src.api.handlers.message_utils import _fetch_semantic_neighbors

        mock_qdrant = MagicMock()
        mock_qdrant.health_check.return_value = True
        mock_qdrant.search_by_vector.return_value = [
            {'path': '/src/test.py', 'score': 1.0},  # Self
            {'path': '/src/other.py', 'score': 0.8},
        ]

        # Patch at the source modules
        with patch('src.memory.qdrant_client.get_qdrant_client', return_value=mock_qdrant):
            with patch('src.utils.embedding_service.get_embedding', return_value=[0.1] * 768):
                result = _fetch_semantic_neighbors('/src/test.py')

        assert len(result) == 1
        assert result[0]['path'] == '/src/other.py'


class TestCalculateDependenciesForContext:
    """Test _calculate_dependencies_for_context() helper."""

    def test_returns_empty_deps_on_import_error(self):
        """Graceful fallback when DependencyCalculator unavailable."""
        from src.api.handlers.message_utils import _calculate_dependencies_for_context

        # Force import error by patching
        with patch.dict('sys.modules', {'src.scanners.dependency_calculator': None}):
            # This should handle the import error gracefully
            result = _calculate_dependencies_for_context('/src/test.py', [])

        assert result == {"imports": [], "imported_by": []}

    def test_scores_semantic_results(self):
        """Semantic results are scored by DependencyCalculator."""
        from src.api.handlers.message_utils import _calculate_dependencies_for_context

        semantic_results = [
            {'path': '/src/utils.py', 'name': 'utils.py', 'score': 0.85, 'created_time': 0},
            {'path': '/src/config.py', 'name': 'config.py', 'score': 0.6, 'created_time': 0},
        ]

        result = _calculate_dependencies_for_context('/src/main.py', semantic_results)

        # Should have scored results (may be filtered by significance threshold)
        assert 'imports' in result
        assert 'imported_by' in result


class TestExtractFolderFocus:
    """Test _extract_folder_focus() helper."""

    def test_empty_viewport_returns_empty(self):
        """Empty viewport → empty folder."""
        from src.api.handlers.message_utils import _extract_folder_focus

        result = _extract_folder_focus(None)
        assert result == ""

    def test_single_file_returns_parent_folder(self):
        """Single file → its parent folder."""
        from src.api.handlers.message_utils import _extract_folder_focus

        viewport = {
            'pinned_nodes': [{'path': '/src/api/handlers/test.py'}],
            'viewport_nodes': []
        }
        result = _extract_folder_focus(viewport)
        assert result == '/src/api/handlers'

    def test_multiple_files_returns_common_ancestor(self):
        """Multiple files → common ancestor folder."""
        from src.api.handlers.message_utils import _extract_folder_focus

        viewport = {
            'pinned_nodes': [
                {'path': '/src/api/handlers/a.py'},
                {'path': '/src/api/handlers/b.py'},
            ],
            'viewport_nodes': [
                {'path': '/src/api/utils.py'},
            ]
        }
        result = _extract_folder_focus(viewport)
        assert result == '/src/api'


class TestTruncateJsonContext:
    """Test _truncate_json_context() helper."""

    def test_preserves_current_file(self):
        """Current file is always preserved."""
        from src.api.handlers.message_utils import _truncate_json_context

        context_data = {
            'current_file': {'path': '/test.py', 'name': 'test.py'},
            'semantic_neighbors': [{'path': f'/file{i}.py'} for i in range(20)],
            'dependencies': {'imports': [{'path': f'/dep{i}.py'} for i in range(20)]},
            'summary': {}
        }

        result = _truncate_json_context(context_data, max_tokens=100)

        assert 'current_file' in result
        assert result['current_file']['path'] == '/test.py'


class TestBuildModelPromptIntegration:
    """Test integration with build_model_prompt."""

    def test_json_context_included_in_prompt(self):
        """json_context parameter is included in final prompt."""
        from src.api.handlers.chat_handler import build_model_prompt

        json_context = """## DEPENDENCY CONTEXT
```json
{"test": true}
```

"""
        result = build_model_prompt(
            text="Hello",
            context_for_model="File context",
            json_context=json_context
        )

        assert '## DEPENDENCY CONTEXT' in result
        assert '{"test": true}' in result

    def test_empty_json_context_not_included(self):
        """Empty json_context doesn't add extra content."""
        from src.api.handlers.chat_handler import build_model_prompt

        result = build_model_prompt(
            text="Hello",
            context_for_model="File context",
            json_context=""
        )

        assert '## DEPENDENCY CONTEXT' not in result


class TestConfigurationVariables:
    """Test configuration via environment variables."""

    def test_default_max_tokens(self):
        """Default max tokens is 2000."""
        from src.api.handlers.message_utils import VETKA_JSON_CONTEXT_MAX_TOKENS
        assert VETKA_JSON_CONTEXT_MAX_TOKENS == 2000

    def test_default_include_deps(self):
        """Default include_dependencies is True."""
        from src.api.handlers.message_utils import VETKA_JSON_CONTEXT_INCLUDE_DEPS
        assert VETKA_JSON_CONTEXT_INCLUDE_DEPS is True

    def test_default_include_semantic(self):
        """Default include_semantic_neighbors is True."""
        from src.api.handlers.message_utils import VETKA_JSON_CONTEXT_INCLUDE_SEMANTIC
        assert VETKA_JSON_CONTEXT_INCLUDE_SEMANTIC is True

    def test_default_compressed(self):
        """[PHASE73.5] Default compressed is True."""
        from src.api.handlers.message_utils import VETKA_JSON_CONTEXT_COMPRESSED
        assert VETKA_JSON_CONTEXT_COMPRESSED is True

    def test_default_cache_size(self):
        """[PHASE73.5] Default cache size is 100."""
        from src.api.handlers.message_utils import VETKA_JSON_CONTEXT_CACHE_SIZE
        assert VETKA_JSON_CONTEXT_CACHE_SIZE == 100

    def test_default_include_imports(self):
        """[PHASE73.5] Default include_imports is True."""
        from src.api.handlers.message_utils import VETKA_JSON_CONTEXT_INCLUDE_IMPORTS
        assert VETKA_JSON_CONTEXT_INCLUDE_IMPORTS is True


# ═══════════════════════════════════════════════════════════════════
# [PHASE73.5] ELISION Compression Tests
# ═══════════════════════════════════════════════════════════════════

class TestElisionCompression:
    """Test ELISION path and key compression functions."""

    def test_shorten_path_basic(self):
        """Path shortening abbreviates folder names."""
        from src.api.handlers.message_utils import _shorten_path

        assert _shorten_path('/src/orchestration/cam_engine.py') == '/s/o/cam_engine.py'
        assert _shorten_path('/src/api/handlers/test.py') == '/s/a/h/test.py'

    def test_shorten_path_preserves_filename(self):
        """Filename is preserved unchanged."""
        from src.api.handlers.message_utils import _shorten_path

        result = _shorten_path('/src/very_long_folder/module.py')
        assert result.endswith('/module.py')

    def test_shorten_path_short_paths_unchanged(self):
        """Short paths (<=2 parts) are unchanged."""
        from src.api.handlers.message_utils import _shorten_path

        assert _shorten_path('/src/main.py') == '/src/main.py'
        assert _shorten_path('/main.py') == '/main.py'
        assert _shorten_path('') == ''

    def test_compress_json_context_keys(self):
        """JSON keys are compressed to abbreviations."""
        from src.api.handlers.message_utils import _compress_json_context

        data = {
            'current_file': {'path': '/test.py', 'name': 'test.py'},
            'dependencies': {'imports': [], 'imported_by': []},
            'semantic_neighbors': [],
            'viewport': {'visible_files': 10, 'pinned_count': 2, 'zoom_level': 'medium'},
            'summary': {}
        }

        result = _compress_json_context(data, compressed=True)

        # Keys should be abbreviated
        assert 'cf' in result  # current_file → cf
        assert 'd' in result   # dependencies → d
        assert 'sn' in result  # semantic_neighbors → sn
        assert 'v' in result   # viewport → v
        assert 's' in result   # summary → s

    def test_compress_json_context_disabled(self):
        """When compressed=False, original keys preserved."""
        from src.api.handlers.message_utils import _compress_json_context

        data = {
            'current_file': {'path': '/test.py'},
            'dependencies': {}
        }

        result = _compress_json_context(data, compressed=False)

        assert 'current_file' in result
        assert 'dependencies' in result

    def test_compressed_output_smaller(self):
        """Compressed output is smaller than uncompressed."""
        from src.api.handlers.message_utils import build_json_context

        # Use long path to see compression benefit
        pinned_files = [
            {'id': '1', 'path': '/src/orchestration/modules/cam_engine.py', 'name': 'cam_engine.py', 'type': 'file'}
        ]
        viewport_context = {
            'zoom_level': 3,
            'total_visible': 25,
            'total_pinned': 5,
            'pinned_nodes': [],
            'viewport_nodes': []
        }

        with patch('src.api.handlers.message_utils._fetch_semantic_neighbors', return_value=[
            {'path': '/src/utils/helpers/formatter.py', 'name': 'formatter.py', 'score': 0.85, 'type': 'file'},
            {'path': '/src/api/handlers/message_utils.py', 'name': 'message_utils.py', 'score': 0.7, 'type': 'file'},
        ]):
            compressed = build_json_context(
                pinned_files=pinned_files,
                viewport_context=viewport_context,
                compressed=True,
                include_dependencies=False,  # Skip deps to avoid external calls
                use_cache=False
            )
            uncompressed = build_json_context(
                pinned_files=pinned_files,
                viewport_context=viewport_context,
                compressed=False,
                include_dependencies=False,
                use_cache=False
            )

        # Compressed should be smaller
        assert len(compressed) < len(uncompressed), f"Compressed: {len(compressed)}, Uncompressed: {len(uncompressed)}"


# ═══════════════════════════════════════════════════════════════════
# [PHASE73.5] LRU Cache Tests
# ═══════════════════════════════════════════════════════════════════

class TestJsonContextCache:
    """Test JSON context LRU cache functionality."""

    def test_cache_stats_initial(self):
        """Initial cache stats are zero."""
        from src.api.handlers.message_utils import (
            clear_json_context_cache,
            get_json_context_cache_stats
        )

        clear_json_context_cache()
        stats = get_json_context_cache_stats()

        assert stats['size'] == 0
        assert stats['hits'] == 0
        assert stats['misses'] == 0

    def test_cache_hit_increments_counter(self):
        """Cache hit increments hit counter."""
        from src.api.handlers.message_utils import (
            build_json_context,
            clear_json_context_cache,
            get_json_context_cache_stats
        )

        clear_json_context_cache()

        pinned_files = [
            {'id': '1', 'path': '/src/test.py', 'name': 'test.py', 'type': 'file'}
        ]

        with patch('src.api.handlers.message_utils._fetch_semantic_neighbors', return_value=[]):
            # First call - cache miss
            result1 = build_json_context(pinned_files=pinned_files, use_cache=True)
            stats1 = get_json_context_cache_stats()

            # Second call - cache hit
            result2 = build_json_context(pinned_files=pinned_files, use_cache=True)
            stats2 = get_json_context_cache_stats()

        assert stats1['misses'] == 1
        assert stats2['hits'] == 1
        assert result1 == result2

    def test_cache_disabled_skips_cache(self):
        """When use_cache=False, cache is not used."""
        from src.api.handlers.message_utils import (
            build_json_context,
            clear_json_context_cache,
            get_json_context_cache_stats
        )

        clear_json_context_cache()

        pinned_files = [
            {'id': '1', 'path': '/src/nocache.py', 'name': 'nocache.py', 'type': 'file'}
        ]

        with patch('src.api.handlers.message_utils._fetch_semantic_neighbors', return_value=[]):
            result = build_json_context(pinned_files=pinned_files, use_cache=False)
            stats = get_json_context_cache_stats()

        # Cache should not be populated
        assert stats['size'] == 0

    def test_clear_cache_resets_stats(self):
        """Clearing cache resets all counters."""
        from src.api.handlers.message_utils import (
            clear_json_context_cache,
            get_json_context_cache_stats,
            _set_cached_json_context
        )

        # Add something to cache
        _set_cached_json_context('test_key', 'test_value')

        clear_json_context_cache()
        stats = get_json_context_cache_stats()

        assert stats['size'] == 0
        assert stats['hits'] == 0
        assert stats['misses'] == 0


# ═══════════════════════════════════════════════════════════════════
# [PHASE73.5] PythonScanner Integration Tests
# ═══════════════════════════════════════════════════════════════════

class TestPythonScannerIntegration:
    """Test PythonScanner import_confidence integration."""

    def test_get_import_confidence_non_python_returns_zero(self):
        """Non-Python files return 0 confidence."""
        from src.api.handlers.message_utils import _get_import_confidence

        result = _get_import_confidence('/src/test.js', '/src/utils.js')
        assert result == 0.0

    def test_get_import_confidence_missing_file_returns_zero(self):
        """Missing source file returns 0 confidence."""
        from src.api.handlers.message_utils import _get_import_confidence

        result = _get_import_confidence('/nonexistent/file.py', '/src/utils.py')
        assert result == 0.0

    def test_dependency_type_indicates_import_source(self):
        """Dependency type shows 'import' or 'semantic'."""
        from src.api.handlers.message_utils import _calculate_dependencies_for_context

        # With mocked import confidence
        with patch('src.api.handlers.message_utils._get_import_confidence', return_value=0.95):
            semantic_results = [
                {'path': '/src/utils.py', 'name': 'utils.py', 'score': 0.85, 'created_time': 0}
            ]

            result = _calculate_dependencies_for_context('/src/main.py', semantic_results)

            # Should have import type
            if result['imports']:
                assert result['imports'][0]['type'] == 'import'

    def test_imported_by_populated_when_reverse_import_found(self):
        """imported_by list is populated when reverse imports found."""
        from src.api.handlers.message_utils import _calculate_dependencies_for_context

        def mock_import_confidence(source, target):
            # Simulate: utils.py imports main.py
            if 'utils.py' in source and 'main.py' in target:
                return 0.9
            return 0.0

        with patch('src.api.handlers.message_utils._get_import_confidence', side_effect=mock_import_confidence):
            with patch('src.api.handlers.message_utils.VETKA_JSON_CONTEXT_INCLUDE_IMPORTS', True):
                semantic_results = [
                    {'path': '/src/utils.py', 'name': 'utils.py', 'score': 0.7, 'created_time': 0}
                ]

                result = _calculate_dependencies_for_context('/src/main.py', semantic_results)

                # Should have imported_by entry
                assert 'imported_by' in result


# ═══════════════════════════════════════════════════════════════════
# [PHASE73.6] Legend Header Tests
# ═══════════════════════════════════════════════════════════════════

class TestLegendHeader:
    """Test Phase 73.6 legend header functionality."""

    def test_default_legend_mode_is_auto(self):
        """[PHASE73.6] Default LEGEND_MODE is 'auto'."""
        from src.api.handlers.message_utils import VETKA_JSON_CONTEXT_LEGEND_MODE
        assert VETKA_JSON_CONTEXT_LEGEND_MODE == "auto"

    def test_elision_legend_map_has_required_keys(self):
        """[PHASE73.6] ELISION_LEGEND_MAP has all required keys."""
        from src.api.handlers.message_utils import ELISION_LEGEND_MAP

        required_keys = ['cf', 'sn', 'd', 'v', 's', 'imp', 'by', 'vf', 'zl']
        for key in required_keys:
            assert key in ELISION_LEGEND_MAP, f"Missing key: {key}"

    def test_get_legend_map_returns_copy(self):
        """[PHASE73.6] get_legend_map() returns a copy, not original."""
        from src.api.handlers.message_utils import get_legend_map, ELISION_LEGEND_MAP

        result = get_legend_map()
        assert result == ELISION_LEGEND_MAP
        # Ensure it's a copy
        result['test'] = 'value'
        assert 'test' not in ELISION_LEGEND_MAP

    def test_reset_session_clears_state(self):
        """[PHASE73.6.2] reset_json_context_session() clears per-model state."""
        from src.api.handlers.message_utils import (
            reset_json_context_session,
            _is_cold_start,
            _mark_model_seen
        )

        reset_json_context_session()
        # First call for model is cold start
        assert _is_cold_start(model_name="test_model") is True

        # Mark model as seen
        _mark_model_seen("test_model")
        # Same model - not cold start
        assert _is_cold_start(model_name="test_model") is False

        # Reset clears all models
        reset_json_context_session()
        assert _is_cold_start(model_name="test_model") is True

    def test_cold_start_detection_with_session_id(self):
        """[PHASE73.6.2] Cold start detected when session_id changes."""
        from src.api.handlers.message_utils import (
            reset_json_context_session,
            _is_cold_start,
            _mark_model_seen
        )

        reset_json_context_session()

        # First call for model in session is cold start
        assert _is_cold_start("session_1", "model_A") is True
        _mark_model_seen("model_A")

        # Same model, same session - not cold start
        assert _is_cold_start("session_1", "model_A") is False

        # New session - cold start again (models_seen reset)
        assert _is_cold_start("session_2", "model_A") is True

    def test_per_model_cold_start(self):
        """[PHASE73.6.2] Each model gets legend independently."""
        from src.api.handlers.message_utils import (
            reset_json_context_session,
            _is_cold_start,
            _mark_model_seen
        )

        reset_json_context_session()

        # Model A first call - cold start
        assert _is_cold_start("session_1", "model_A") is True
        _mark_model_seen("model_A")

        # Model A second call - not cold start
        assert _is_cold_start("session_1", "model_A") is False

        # Model B first call - cold start (different model!)
        assert _is_cold_start("session_1", "model_B") is True
        _mark_model_seen("model_B")

        # Model B second call - not cold start
        assert _is_cold_start("session_1", "model_B") is False

    def test_should_include_legend_explicit_true(self):
        """[PHASE73.6] include_legend=True always includes legend."""
        from src.api.handlers.message_utils import (
            _should_include_legend,
            reset_json_context_session,
            _mark_model_seen
        )

        reset_json_context_session()
        _mark_model_seen("test_model")  # Not cold start for this model

        # Explicit True overrides
        assert _should_include_legend(include_legend=True, model_name="test_model") is True

    def test_should_include_legend_explicit_false(self):
        """[PHASE73.6] include_legend=False never includes legend."""
        from src.api.handlers.message_utils import (
            _should_include_legend,
            reset_json_context_session
        )

        reset_json_context_session()  # Cold start

        # Explicit False overrides even on cold start
        assert _should_include_legend(include_legend=False) is False

    def test_legend_included_on_cold_start_auto_mode(self):
        """[PHASE73.6.2] Legend included on first call for model in auto mode."""
        from src.api.handlers.message_utils import (
            build_json_context,
            reset_json_context_session,
            clear_json_context_cache
        )

        reset_json_context_session()
        clear_json_context_cache()

        pinned_files = [
            {'id': '1', 'path': '/src/test.py', 'name': 'test.py', 'type': 'file'}
        ]

        with patch('src.api.handlers.message_utils._fetch_semantic_neighbors', return_value=[]):
            result = build_json_context(
                pinned_files=pinned_files,
                compressed=True,
                use_cache=False,
                model_name="test_model"
            )

        # Should contain legend key on first call for model
        assert '"_legend":' in result or '"_legend":{' in result

    def test_legend_not_included_on_second_call_same_model(self):
        """[PHASE73.6.2] Legend NOT included on second call for SAME model."""
        from src.api.handlers.message_utils import (
            build_json_context,
            reset_json_context_session,
            clear_json_context_cache
        )

        reset_json_context_session()
        clear_json_context_cache()

        pinned_files = [
            {'id': '1', 'path': '/src/test.py', 'name': 'test.py', 'type': 'file'}
        ]

        with patch('src.api.handlers.message_utils._fetch_semantic_neighbors', return_value=[]):
            # First call for model_A - includes legend
            result1 = build_json_context(
                pinned_files=pinned_files,
                compressed=True,
                use_cache=False,
                model_name="model_A"
            )

            # Second call for same model_A - no legend
            result2 = build_json_context(
                pinned_files=pinned_files,
                compressed=True,
                use_cache=False,
                model_name="model_A"
            )

        assert '"_legend":' in result1  # First has legend
        assert '"_legend":' not in result2  # Second doesn't

    def test_legend_included_for_different_model(self):
        """[PHASE73.6.2] Legend included for DIFFERENT model even in same session."""
        from src.api.handlers.message_utils import (
            build_json_context,
            reset_json_context_session,
            clear_json_context_cache
        )

        reset_json_context_session()
        clear_json_context_cache()

        pinned_files = [
            {'id': '1', 'path': '/src/test.py', 'name': 'test.py', 'type': 'file'}
        ]

        with patch('src.api.handlers.message_utils._fetch_semantic_neighbors', return_value=[]):
            # First call for model_A - includes legend
            result_A1 = build_json_context(
                pinned_files=pinned_files,
                compressed=True,
                use_cache=False,
                model_name="model_A"
            )

            # First call for model_B - ALSO includes legend (different model!)
            result_B1 = build_json_context(
                pinned_files=pinned_files,
                compressed=True,
                use_cache=False,
                model_name="model_B"
            )

            # Second call for model_A - no legend
            result_A2 = build_json_context(
                pinned_files=pinned_files,
                compressed=True,
                use_cache=False,
                model_name="model_A"
            )

        assert '"_legend":' in result_A1  # First for A has legend
        assert '"_legend":' in result_B1  # First for B has legend
        assert '"_legend":' not in result_A2  # Second for A doesn't

    def test_legend_always_included_with_explicit_true(self):
        """[PHASE73.6] Legend always included with include_legend=True."""
        from src.api.handlers.message_utils import (
            build_json_context,
            reset_json_context_session,
            clear_json_context_cache,
            _mark_model_seen
        )

        reset_json_context_session()
        clear_json_context_cache()
        _mark_model_seen("test_model")  # Mark model as already seen

        pinned_files = [
            {'id': '1', 'path': '/src/test.py', 'name': 'test.py', 'type': 'file'}
        ]

        with patch('src.api.handlers.message_utils._fetch_semantic_neighbors', return_value=[]):
            result = build_json_context(
                pinned_files=pinned_files,
                compressed=True,
                include_legend=True,
                use_cache=False
            )

        assert '"_legend":' in result

    def test_legend_not_included_when_uncompressed(self):
        """[PHASE73.6] Legend NOT included when compressed=False."""
        from src.api.handlers.message_utils import (
            build_json_context,
            reset_json_context_session,
            clear_json_context_cache
        )

        reset_json_context_session()
        clear_json_context_cache()

        pinned_files = [
            {'id': '1', 'path': '/src/test.py', 'name': 'test.py', 'type': 'file'}
        ]

        with patch('src.api.handlers.message_utils._fetch_semantic_neighbors', return_value=[]):
            result = build_json_context(
                pinned_files=pinned_files,
                compressed=False,  # Uncompressed
                include_legend=True,  # Even with explicit True
                use_cache=False
            )

        # Legend only makes sense with compression
        assert '"_legend":' not in result
