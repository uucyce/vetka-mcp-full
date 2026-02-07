"""
Phase 117.7: Chat Naming + Solo @dragon chat_id + Weaviate v4 Migration

MARKER_117.7: Tests for three fixes:
  A. Solo @dragon chat_id — pipeline gets client_chat_id (not None)
  B. Chat naming fallback — display_name never None
  C. Weaviate v4 migration — connect_to_local instead of Client()

Root cause: Second live @dragon test showed Polza API calls in logs,
but pipeline couldn't emit progress (chat_id=None → timeout).
Chat names stuck as "unknown". Weaviate VetkaLeaf empty (v3→v4 API mismatch).
"""

import inspect
import pytest
from pathlib import Path


# ============================================================================
# MARKER_117.7A: Solo @dragon chat_id passed to pipeline
# ============================================================================

class TestSoloChatIdFix:
    """Test that _dispatch_solo_system_command passes chat_id to pipeline."""

    def test_dispatch_solo_accepts_chat_id_param(self):
        """MARKER_117.7A: _dispatch_solo_system_command should accept chat_id parameter."""
        from src.api.handlers.user_message_handler import _dispatch_solo_system_command
        sig = inspect.signature(_dispatch_solo_system_command)
        params = list(sig.parameters.keys())
        assert "chat_id" in params, (
            f"_dispatch_solo_system_command should accept 'chat_id' parameter. Got: {params}"
        )

    def test_dispatch_solo_chat_id_is_optional(self):
        """MARKER_117.7A: chat_id should have default value (backward compat)."""
        from src.api.handlers.user_message_handler import _dispatch_solo_system_command
        sig = inspect.signature(_dispatch_solo_system_command)
        chat_id_param = sig.parameters.get("chat_id")
        assert chat_id_param is not None
        assert chat_id_param.default is None or chat_id_param.default == inspect.Parameter.empty or chat_id_param.default is None, (
            f"chat_id default should be None, got {chat_id_param.default}"
        )

    def test_dispatch_solo_passes_chat_id_to_pipeline(self):
        """MARKER_117.7A→117.8A: Source should pass chat_id to AgentPipeline (not None)."""
        handler_file = Path(__file__).parent.parent / "src" / "api" / "handlers" / "user_message_handler.py"
        source = handler_file.read_text()
        # Phase 117.8 upgraded to also pass sio+sid, so check for chat_id=chat_id presence
        assert "chat_id=chat_id" in source, (
            "AgentPipeline should be created with chat_id=chat_id (not None)"
        )

    def test_dispatch_call_site_passes_chat_id(self):
        """MARKER_117.7A: Call site should pass client_chat_id to dispatch."""
        handler_file = Path(__file__).parent.parent / "src" / "api" / "handlers" / "user_message_handler.py"
        source = handler_file.read_text()
        assert "chat_id=client_chat_id," in source, (
            "Dispatch call should pass chat_id=client_chat_id"
        )

    def test_emit_progress_handles_none_chat_id(self):
        """MARKER_117.7A→117.8B: _emit_progress should handle None chat_id gracefully."""
        pipeline_file = Path(__file__).parent.parent / "src" / "orchestration" / "agent_pipeline.py"
        source = pipeline_file.read_text()
        # Phase 117.8 replaced guard with SocketIO route + conditional check
        assert "if self.chat_id:" in source, (
            "_emit_progress should conditionally check chat_id before HTTP emit"
        )

    def test_emit_progress_no_none_in_url(self):
        """MARKER_117.7A: Pipeline source should NOT have chat_id=None in _dispatch_solo."""
        handler_file = Path(__file__).parent.parent / "src" / "api" / "handlers" / "user_message_handler.py"
        source = handler_file.read_text()
        # Should NOT have AgentPipeline(chat_id=None) anymore
        assert "AgentPipeline(chat_id=None)" not in source, (
            "AgentPipeline should NOT be created with chat_id=None"
        )


# ============================================================================
# MARKER_117.7B: Chat naming fallback
# ============================================================================

class TestChatNamingFallback:
    """Test that display_name never ends up as None."""

    def test_display_name_fallback_in_source(self):
        """MARKER_117.7B: chat_history_manager should have fallback for display_name."""
        manager_file = Path(__file__).parent.parent / "src" / "chat" / "chat_history_manager.py"
        source = manager_file.read_text()
        assert "MARKER_117.7B" in source, (
            "chat_history_manager should have MARKER_117.7B for display_name fallback"
        )

    def test_display_name_not_none_fallback(self):
        """MARKER_117.7B: display_name should fallback to Chat HH:MM, not None."""
        manager_file = Path(__file__).parent.parent / "src" / "chat" / "chat_history_manager.py"
        source = manager_file.read_text()
        # Should have fallback pattern like `or f"Chat {datetime...}"`
        assert 'or f"Chat {' in source, (
            "display_name should have fallback to 'Chat HH:MM'"
        )

    def test_no_unknown_file_path_in_handlers(self):
        """MARKER_117.7B: No file_path='unknown' in handlers."""
        for handler_name in ["user_message_handler.py", "group_message_handler.py"]:
            handler_file = Path(__file__).parent.parent / "src" / "api" / "handlers" / handler_name
            if handler_file.exists():
                source = handler_file.read_text()
                count = source.count('file_path="unknown"')
                assert count == 0, (
                    f"Found {count} occurrences of file_path='unknown' in {handler_name}"
                )


# ============================================================================
# MARKER_117.7C: Weaviate v3→v4 migration
# ============================================================================

class TestWeaviateV4Migration:
    """Test that triple_write_manager uses Weaviate v4 API."""

    def test_weaviate_uses_connect_to_local(self):
        """MARKER_117.7C: Should use weaviate.connect_to_local (v4), not Client() (v3)."""
        tw_file = Path(__file__).parent.parent / "src" / "orchestration" / "triple_write_manager.py"
        source = tw_file.read_text()
        assert "connect_to_local" in source, (
            "triple_write_manager should use weaviate.connect_to_local (v4 API)"
        )
        # Should NOT have old v3 Client(url) call
        assert "weaviate.Client(" not in source, (
            "triple_write_manager should NOT use weaviate.Client() (v3 API)"
        )

    def test_weaviate_v4_imports(self):
        """MARKER_117.7C: v4 imports should be present (Configure, Property, DataType)."""
        tw_file = Path(__file__).parent.parent / "src" / "orchestration" / "triple_write_manager.py"
        source = tw_file.read_text()
        assert "from weaviate.classes.config import Configure" in source
        assert "Property" in source
        assert "DataType" in source

    def test_weaviate_v4_collections_api(self):
        """MARKER_117.7C: Should use collections.create (v4), not schema.create_class (v3)."""
        tw_file = Path(__file__).parent.parent / "src" / "orchestration" / "triple_write_manager.py"
        source = tw_file.read_text()
        assert "collections.create(" in source, (
            "Should use v4 collections.create() for schema"
        )
        assert "schema.create_class" not in source, (
            "Should NOT use v3 schema.create_class()"
        )

    def test_weaviate_v4_data_api(self):
        """MARKER_117.7C: Should use collection.data.insert (v4), not data_object.create (v3)."""
        tw_file = Path(__file__).parent.parent / "src" / "orchestration" / "triple_write_manager.py"
        source = tw_file.read_text()
        assert "collection.data.insert(" in source or "data.insert(" in source, (
            "Should use v4 collection.data.insert()"
        )
        assert "data_object.create(" not in source, (
            "Should NOT use v3 data_object.create()"
        )

    def test_weaviate_v4_collections_list(self):
        """MARKER_117.7C: Should use collections.list_all (v4), not schema.get (v3)."""
        tw_file = Path(__file__).parent.parent / "src" / "orchestration" / "triple_write_manager.py"
        source = tw_file.read_text()
        assert "collections.list_all()" in source, (
            "Should use v4 collections.list_all()"
        )
        assert "schema.get()" not in source, (
            "Should NOT use v3 schema.get()"
        )

    def test_marker_117_7c_present(self):
        """MARKER_117.7C: Marker should be present in source."""
        tw_file = Path(__file__).parent.parent / "src" / "orchestration" / "triple_write_manager.py"
        source = tw_file.read_text()
        assert "MARKER_117.7C" in source, (
            "triple_write_manager should have MARKER_117.7C for v4 migration"
        )
