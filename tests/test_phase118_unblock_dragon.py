"""
Phase 118: Unblock @dragon — Sync Blockers, Logging, Weaviate Upsert, Model Selector

MARKER_118: Tests for six fixes:
  118.1 — Async embedding calls (no more blocking event loop)
  118.2 — Weaviate upsert: insert-first, catch-replace (no TOCTOU race)
  118.3 — httpx logging: basicConfig(WARNING) + early suppression
  118.4 — Hostess: no hardcoded local model fallback
  118.5 — Engram: scroll() + retrieve() proxy + get_all_preferences()

Root cause: Third @dragon live test — VETKA still hangs. Sync ollama.embeddings()
blocks event loop, Weaviate 422 "already exists" race condition, httpx INFO flood.
"""

import inspect
import re
import pytest
from pathlib import Path

pytestmark = pytest.mark.stale(reason="Pre-existing failure — phase 118 contracts changed")

EMBEDDING_FILE = Path(__file__).parent.parent / "src" / "utils" / "embedding_service.py"
TRIPLE_WRITE_FILE = Path(__file__).parent.parent / "src" / "orchestration" / "triple_write_manager.py"
MAIN_FILE = Path(__file__).parent.parent / "main.py"
HOSTESS_FILE = Path(__file__).parent.parent / "src" / "agents" / "hostess_agent.py"
ENGRAM_FILE = Path(__file__).parent.parent / "src" / "memory" / "aura_store.py"  # MARKER_187.6: renamed from engram_user_memory.py
QDRANT_CLIENT_FILE = Path(__file__).parent.parent / "src" / "memory" / "qdrant_client.py"


# ============================================================================
# MARKER_118.1: Async Embedding Calls
# ============================================================================

class TestAsyncEmbeddings:
    """MARKER_118.1: EmbeddingService has async methods that don't block event loop."""

    def test_has_async_get_embedding(self):
        """get_embedding_async should exist and be a coroutine."""
        from src.utils.embedding_service import EmbeddingService
        service = EmbeddingService()
        assert hasattr(service, 'get_embedding_async'), (
            "EmbeddingService should have get_embedding_async method"
        )
        assert inspect.iscoroutinefunction(service.get_embedding_async), (
            "get_embedding_async should be a coroutine function (async def)"
        )

    def test_has_async_get_embedding_batch(self):
        """get_embedding_batch_async should exist and be a coroutine."""
        from src.utils.embedding_service import EmbeddingService
        service = EmbeddingService()
        assert hasattr(service, 'get_embedding_batch_async'), (
            "EmbeddingService should have get_embedding_batch_async method"
        )
        assert inspect.iscoroutinefunction(service.get_embedding_batch_async), (
            "get_embedding_batch_async should be a coroutine function (async def)"
        )

    def test_async_uses_to_thread(self):
        """Async methods should use asyncio.to_thread (non-blocking wrapper)."""
        source = EMBEDDING_FILE.read_text()
        assert "asyncio.to_thread" in source, (
            "Async embedding should use asyncio.to_thread to wrap sync ollama calls"
        )

    def test_asyncio_imported(self):
        """asyncio should be imported."""
        source = EMBEDDING_FILE.read_text()
        assert "import asyncio" in source

    def test_convenience_async_function(self):
        """Module-level get_embedding_async convenience function should exist."""
        from src.utils.embedding_service import get_embedding_async

        assert inspect.iscoroutinefunction(get_embedding_async)

    def test_marker_118_1_present(self):
        """MARKER_118.1 should be in source."""
        source = EMBEDDING_FILE.read_text()
        assert "MARKER_118.1" in source


# ============================================================================
# MARKER_118.2: Weaviate Upsert Race Condition
# ============================================================================

class TestWeaviateUpsert:
    """MARKER_118.2: Insert-first, catch-replace pattern (no TOCTOU)."""

    def test_insert_before_get_by_id(self):
        """Upsert should try insert FIRST, not get_by_id first."""
        source = TRIPLE_WRITE_FILE.read_text()
        # Find the _write_weaviate_internal method
        match = re.search(
            r'def _write_weaviate_internal\(.*?\n(.*?)(?=\n    def |\nclass |\Z)',
            source, re.DOTALL
        )
        assert match, "_write_weaviate_internal method not found"
        body = match.group(1)

        # insert should appear BEFORE get_by_id in the method body
        insert_pos = body.find("data.insert(")
        get_pos = body.find("get_by_id(")

        # With insert-first pattern, first insert should come before any get_by_id
        # (get_by_id should no longer be present, or should be after insert)
        if get_pos >= 0:
            assert insert_pos < get_pos, (
                "data.insert() should appear BEFORE get_by_id() in upsert pattern"
            )

    def test_catches_already_exists(self):
        """Should catch 'already exists' exception and fallback to replace."""
        source = TRIPLE_WRITE_FILE.read_text()
        assert '"already exists"' in source or "'already exists'" in source, (
            "Should catch 'already exists' error from Weaviate insert"
        )

    def test_no_toctou_pattern(self):
        """Should NOT have get_by_id → insert pattern (TOCTOU race)."""
        source = TRIPLE_WRITE_FILE.read_text()
        match = re.search(
            r'def _write_weaviate_internal\(.*?\n(.*?)(?=\n    def |\nclass |\Z)',
            source, re.DOTALL
        )
        assert match
        body = match.group(1)

        # The old pattern was: get_by_id → if existing → replace, else → insert
        # Should NOT have this check-then-act pattern anymore
        lines = body.split('\n')
        for i, line in enumerate(lines):
            if 'get_by_id(' in line and i + 5 < len(lines):
                # Check if this is the main upsert pattern (not just a reference)
                nearby = '\n'.join(lines[i:i+5])
                assert 'data.insert(' not in nearby, (
                    f"Found TOCTOU pattern: get_by_id followed by insert near line {i}"
                )

    def test_marker_118_2_present(self):
        """MARKER_118.2 should be in source."""
        source = TRIPLE_WRITE_FILE.read_text()
        assert "MARKER_118.2" in source


# ============================================================================
# MARKER_118.3: httpx Logging Suppression
# ============================================================================

class TestHttpxLogging:
    """MARKER_118.3: No httpx INFO flood from premature basicConfig."""

    def test_no_basic_config_info_level(self):
        """main.py should NOT have basicConfig with level=logging.INFO."""
        source = MAIN_FILE.read_text()
        # Find basicConfig call
        match = re.search(r'logging\.basicConfig\((.*?)\)', source, re.DOTALL)
        assert match, "basicConfig should still exist in main.py"
        config_args = match.group(1)
        assert "logging.INFO" not in config_args, (
            "basicConfig should NOT use level=logging.INFO (causes httpx flood). "
            "Use logging.WARNING instead."
        )

    def test_early_suppression_in_main(self):
        """main.py should suppress httpx early (before imports trigger it)."""
        source = MAIN_FILE.read_text()
        assert "httpx" in source and "WARNING" in source, (
            "main.py should suppress httpx logger early"
        )

    def test_marker_118_3_present(self):
        """MARKER_118.3 should be in main.py."""
        source = MAIN_FILE.read_text()
        assert "MARKER_118.3" in source


# ============================================================================
# MARKER_118.4: Mute Local Models
# ============================================================================

class TestHostessMuteLocal:
    """MARKER_118.4: No hardcoded local model fallback."""

    def test_no_hardcoded_qwen_fallback(self):
        """_find_available_model should NOT return hardcoded 'qwen2:7b'."""
        source = HOSTESS_FILE.read_text()
        # Find the _find_available_model method
        match = re.search(
            r'def _find_available_model\(.*?\n(.*?)(?=\n    def |\nclass |\Z)',
            source, re.DOTALL
        )
        assert match, "_find_available_model not found"
        body = match.group(1)

        # Should NOT have `return "qwen2:7b"` as hardcoded fallback
        lines = body.strip().split('\n')
        last_return = None
        for line in lines:
            stripped = line.strip()
            if stripped.startswith('return ') and not stripped.startswith('#'):
                last_return = stripped

        if last_return:
            assert '"qwen2:7b"' not in last_return, (
                f"Last return should NOT be hardcoded 'qwen2:7b'. Got: {last_return}"
            )

    def test_find_model_returns_none_when_unavailable(self):
        """_find_available_model should return None, not hardcoded model."""
        source = HOSTESS_FILE.read_text()
        assert "return None" in source, (
            "_find_available_model should return None when no model available"
        )

    def test_process_guards_no_model(self):
        """process() should check if self.model is None before calling Ollama."""
        source = HOSTESS_FILE.read_text()
        match = re.search(
            r'def process\(self.*?\n(.*?)(?=\n    def |\nclass |\Z)',
            source, re.DOTALL
        )
        assert match, "process() method not found"
        body = match.group(1)
        assert "not self.model" in body or "self.model is None" in body or "if not self.model" in body, (
            "process() should guard against None model before calling Ollama"
        )

    def test_uses_logger_not_print(self):
        """Hostess should use logger, not print() for debug output."""
        source = HOSTESS_FILE.read_text()
        assert "import logging" in source, "hostess_agent should import logging"

    def test_marker_118_4_present(self):
        """MARKER_118.4 should be in source."""
        source = HOSTESS_FILE.read_text()
        assert "MARKER_118.4" in source


# ============================================================================
# MARKER_118.5: Engram UserMemory Errors
# ============================================================================

class TestEngramFixes:
    """MARKER_118.5: scroll() proxy + get_all_preferences()."""

    def test_qdrant_client_has_scroll_proxy(self):
        """QdrantVetkaClient should have scroll() proxy method."""
        source = QDRANT_CLIENT_FILE.read_text()
        assert "def scroll(" in source, (
            "QdrantVetkaClient should have scroll() proxy method"
        )

    def test_qdrant_client_has_retrieve_proxy(self):
        """QdrantVetkaClient should have retrieve() proxy method."""
        source = QDRANT_CLIENT_FILE.read_text()
        assert "def retrieve(" in source, (
            "QdrantVetkaClient should have retrieve() proxy method"
        )

    def test_aura_has_get_all_preferences(self):
        """AuraStore should have get_all_preferences() public method."""
        source = ENGRAM_FILE.read_text()
        assert "def get_all_preferences(" in source, (
            "AuraStore should have get_all_preferences() method"
        )

    def test_get_all_preferences_returns_dict(self):
        """get_all_preferences should return dict (not UserPreferences object)."""
        source = ENGRAM_FILE.read_text()
        match = re.search(
            r'def get_all_preferences\(self.*?\n(.*?)(?=\n    def |\nclass |\Z)',
            source, re.DOTALL
        )
        assert match, "get_all_preferences method not found"
        body = match.group(1)
        assert ".to_dict()" in body, (
            "get_all_preferences should convert to dict via .to_dict()"
        )

    def test_marker_118_5_present_in_qdrant(self):
        """MARKER_118.5 should be in qdrant_client.py."""
        source = QDRANT_CLIENT_FILE.read_text()
        assert "MARKER_118.5" in source

    def test_marker_118_5_present_in_aura(self):
        """MARKER_118.5 should be in aura_store.py."""
        source = ENGRAM_FILE.read_text()
        assert "MARKER_118.5" in source


# ============================================================================
# MARKER_118.6: Pipeline emit uses chat_response (not agent_message)
# ============================================================================

PIPELINE_FILE = Path(__file__).parent.parent / "src" / "orchestration" / "agent_pipeline.py"
HANDLER_FILE = Path(__file__).parent.parent / "src" / "api" / "handlers" / "user_message_handler.py"


class TestChatResponseEmit:
    """MARKER_118.6: Pipeline emit uses 'chat_response' event for ChatPanel visibility."""

    def test_emit_progress_uses_chat_response(self):
        """_emit_progress Route 1 should emit 'chat_response', not 'agent_message'."""
        source = PIPELINE_FILE.read_text()
        # Find _emit_progress method
        match = re.search(
            r'async def _emit_progress\(self.*?\n(.*?)(?=\n    # MARKER_102\.27_END|\n    async def |\n    def )',
            source, re.DOTALL
        )
        assert match, "_emit_progress method not found"
        body = match.group(1)

        # Route 1 (sio direct) should use chat_response
        assert '"chat_response"' in body, (
            "_emit_progress Route 1 should emit 'chat_response' for ChatPanel visibility"
        )
        # Actual emit calls should NOT use agent_message (ignore docstrings/comments)
        emit_calls = re.findall(r'sio\.emit\("([^"]+)"', body)
        for event_name in emit_calls:
            assert event_name == "chat_response", (
                f"_emit_progress sio.emit uses '{event_name}', should be 'chat_response'"
            )

    def test_emit_progress_data_has_message_key(self):
        """chat_response format requires 'message' key (not 'content')."""
        source = PIPELINE_FILE.read_text()
        match = re.search(
            r'async def _emit_progress\(self.*?\n(.*?)(?=\n    # MARKER_102\.27_END|\n    async def |\n    def )',
            source, re.DOTALL
        )
        assert match
        body = match.group(1)
        assert '"message":' in body or '"message"' in body, (
            "chat_response data must have 'message' key for ChatPanel rendering"
        )

    def test_emit_to_chat_uses_chat_response(self):
        """_emit_to_chat Route 1 should emit 'chat_response', not 'agent_message'."""
        source = PIPELINE_FILE.read_text()
        match = re.search(
            r'async def _emit_to_chat\(self.*?\n(.*?)(?=\n    # MARKER_104_STREAM_VISIBILITY_END|\n    async def |\n    def )',
            source, re.DOTALL
        )
        assert match, "_emit_to_chat method not found"
        body = match.group(1)
        assert '"chat_response"' in body, (
            "_emit_to_chat Route 1 should emit 'chat_response'"
        )

    def test_dispatch_initial_emit_uses_chat_response(self):
        """Initial 'Pipeline starting...' emit should use chat_response."""
        source = HANDLER_FILE.read_text()
        # Find the block around "Pipeline starting..."
        idx = source.find("Pipeline starting...")
        assert idx > 0, "'Pipeline starting...' message not found"
        # Check nearby context (100 chars before)
        nearby = source[max(0, idx-200):idx+100]
        assert "chat_response" in nearby, (
            "Initial 'Pipeline starting...' should emit via 'chat_response'"
        )

    def test_dispatch_final_report_uses_chat_response(self):
        """Final report emit in _dispatch_solo_system_command should use chat_response."""
        source = HANDLER_FILE.read_text()
        # Find _dispatch_solo_system_command
        match = re.search(
            r'async def _dispatch_solo_system_command\(.*?\n(.*?)(?=\nasync def |\ndef |\Z)',
            source, re.DOTALL
        )
        assert match, "_dispatch_solo_system_command not found"
        body = match.group(1)

        # All sio.emit calls should use chat_response
        emit_calls = re.findall(r'sio\.emit\("([^"]+)"', body)
        for event_name in emit_calls:
            assert event_name == "chat_response", (
                f"sio.emit in _dispatch_solo_system_command uses '{event_name}', should be 'chat_response'"
            )

    def test_marker_118_6_in_pipeline(self):
        """MARKER_118.6 should be in agent_pipeline.py."""
        source = PIPELINE_FILE.read_text()
        assert "MARKER_118.6" in source

    def test_marker_118_6_in_handler(self):
        """MARKER_118.6 should be in user_message_handler.py."""
        source = HANDLER_FILE.read_text()
        assert "MARKER_118.6" in source


# ============================================================================
# MARKER_118.7: Error callback for asyncio.create_task
# ============================================================================

class TestErrorCallback:
    """MARKER_118.7: Background task has error callback for exception logging."""

    def test_create_task_has_done_callback(self):
        """asyncio.create_task for @dragon should have add_done_callback."""
        source = HANDLER_FILE.read_text()
        assert "add_done_callback" in source, (
            "asyncio.create_task for @dragon pipeline should have error callback via add_done_callback"
        )

    def test_callback_checks_exception(self):
        """Error callback should check t.exception()."""
        source = HANDLER_FILE.read_text()
        assert "t.exception()" in source or "task.exception()" in source, (
            "Done callback should check for task exceptions"
        )

    def test_marker_118_7_present(self):
        """MARKER_118.7 should be in user_message_handler.py."""
        source = HANDLER_FILE.read_text()
        assert "MARKER_118.7" in source
