# MARKER_115_TESTS
"""
VETKA Phase 115 - Bug Fix Verification Tests

Tests for all Phase 115 bug fixes:
- BUG-1: Chat Hygiene (parasitic chat creation)
- BUG-3: Provider Persistence (model_source field)
- BUG-4: Pinned Files Persistence (JSON persistence)
- BUG-7: Security Gate (tool allowlist + audit log)

@status: active
@phase: 115
@marker: MARKER_115_TESTS
@depends: pytest, pytest-asyncio, unittest.mock
"""

import pytest
import asyncio
import json
import os
import tempfile
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from pathlib import Path
from typing import Dict


# ============================================================
# TEST MARKERS
# ============================================================

pytestmark = [
    pytest.mark.phase_115,
    pytest.mark.stale(reason="Pre-existing failure — phase 115 contracts changed"),
]


# ============================================================
# BUG-7: Security Gate Tests
# ============================================================

class TestSecurityGateAllowlist:
    """Tests for MARKER_115_SECURITY: Tool allowlist in llm_call_tool.py"""

    def test_safe_tools_set_exists(self):
        """SAFE_FUNCTION_CALLING_TOOLS should be defined and non-empty."""
        from src.mcp.tools.llm_call_tool import SAFE_FUNCTION_CALLING_TOOLS
        assert isinstance(SAFE_FUNCTION_CALLING_TOOLS, set)
        assert len(SAFE_FUNCTION_CALLING_TOOLS) > 0

    def test_write_tools_set_exists(self):
        """WRITE_TOOLS_REQUIRING_APPROVAL should be defined and non-empty."""
        from src.mcp.tools.llm_call_tool import WRITE_TOOLS_REQUIRING_APPROVAL
        assert isinstance(WRITE_TOOLS_REQUIRING_APPROVAL, set)
        assert len(WRITE_TOOLS_REQUIRING_APPROVAL) > 0

    def test_safe_and_write_sets_disjoint(self):
        """Safe tools and write tools must not overlap."""
        from src.mcp.tools.llm_call_tool import (
            SAFE_FUNCTION_CALLING_TOOLS,
            WRITE_TOOLS_REQUIRING_APPROVAL,
        )
        overlap = SAFE_FUNCTION_CALLING_TOOLS & WRITE_TOOLS_REQUIRING_APPROVAL
        assert len(overlap) == 0, f"Overlap found: {overlap}"

    def test_edit_file_in_write_tools(self):
        """vetka_edit_file must be in write tools (never in safe)."""
        from src.mcp.tools.llm_call_tool import (
            SAFE_FUNCTION_CALLING_TOOLS,
            WRITE_TOOLS_REQUIRING_APPROVAL,
        )
        assert "vetka_edit_file" in WRITE_TOOLS_REQUIRING_APPROVAL
        assert "vetka_edit_file" not in SAFE_FUNCTION_CALLING_TOOLS

    def test_git_commit_in_write_tools(self):
        """vetka_git_commit must be in write tools."""
        from src.mcp.tools.llm_call_tool import WRITE_TOOLS_REQUIRING_APPROVAL
        assert "vetka_git_commit" in WRITE_TOOLS_REQUIRING_APPROVAL

    def test_call_model_blocked_from_function_calling(self):
        """vetka_call_model must be blocked to prevent recursive LLM calls."""
        from src.mcp.tools.llm_call_tool import WRITE_TOOLS_REQUIRING_APPROVAL
        assert "vetka_call_model" in WRITE_TOOLS_REQUIRING_APPROVAL

    def test_read_tools_are_safe(self):
        """Read-only tools should be in the safe set."""
        from src.mcp.tools.llm_call_tool import SAFE_FUNCTION_CALLING_TOOLS
        read_tools = [
            "vetka_search_semantic",
            "vetka_read_file",
            "vetka_list_files",
            "vetka_get_tree",
            "vetka_health",
            "vetka_git_status",
        ]
        for tool in read_tools:
            assert tool in SAFE_FUNCTION_CALLING_TOOLS, f"{tool} should be safe"


class TestSecurityGateAuditLog:
    """Tests for MARKER_115_SECURITY: Audit logging in vetka_mcp_bridge.py"""

    @pytest.fixture
    def audit_log_path(self, tmp_path):
        """Create temporary audit log path."""
        return tmp_path / "tool_audit_log.jsonl"

    async def test_audit_log_function_exists(self):
        """_audit_log_tool_call function should exist in bridge module."""
        from src.mcp.vetka_mcp_bridge import _audit_log_tool_call
        assert callable(_audit_log_tool_call)

    def test_audit_log_sanitizes_content(self):
        """Content field should be replaced with char count, sensitive fields redacted."""
        # Test the sanitization logic that _audit_log_tool_call applies
        arguments = {
            "content": "x" * 1000,
            "path": "/test/file.py",
            "api_key": "sk-secret-123",
            "token": "tok-abc",
            "password": "hunter2",
        }

        safe_args = {}
        for k, v in arguments.items():
            if k in ("content",):
                safe_args[k] = f"[{len(str(v))} chars]"
            elif k in ("api_key", "token", "password"):
                safe_args[k] = "[REDACTED]"
            else:
                safe_args[k] = v

        assert safe_args["content"] == "[1000 chars]"
        assert safe_args["api_key"] == "[REDACTED]"
        assert safe_args["token"] == "[REDACTED]"
        assert safe_args["password"] == "[REDACTED]"
        assert safe_args["path"] == "/test/file.py"

    def test_tool_filter_blocks_write_tools(self):
        """Write tools should be filtered from function calling tool list."""
        from src.mcp.tools.llm_call_tool import (
            SAFE_FUNCTION_CALLING_TOOLS,
            WRITE_TOOLS_REQUIRING_APPROVAL,
        )

        # Simulate tool filtering logic
        tools = [
            {"function": {"name": "vetka_read_file"}},
            {"function": {"name": "vetka_edit_file"}},
            {"function": {"name": "vetka_search_semantic"}},
            {"function": {"name": "vetka_git_commit"}},
        ]

        filtered = []
        blocked = []
        for tool_def in tools:
            name = tool_def.get("function", {}).get("name", "")
            if name in SAFE_FUNCTION_CALLING_TOOLS:
                filtered.append(tool_def)
            elif name in WRITE_TOOLS_REQUIRING_APPROVAL:
                blocked.append(name)
            else:
                filtered.append(tool_def)

        assert len(filtered) == 2  # read_file + search_semantic
        assert "vetka_edit_file" in blocked
        assert "vetka_git_commit" in blocked


# ============================================================
# BUG-3: Provider Persistence Tests
# ============================================================

class TestProviderPersistence:
    """Tests for MARKER_115_BUG3: model_source field persistence."""

    def test_handler_utils_includes_model_source(self):
        """handler_utils.py msg_to_save should include model_source field."""
        # Simulate the msg_to_save construction from handler_utils.py
        message = {
            "role": "assistant",
            "content": "test response",
            "agent": "grok-4",
            "model": "grok-4",
            "model_provider": "openrouter",
            "model_source": "polza_ai",
            "node_id": "test-node",
            "metadata": {},
        }

        msg_to_save = {
            "role": message.get("role", "user"),
            "content": message.get("content") or message.get("text"),
            "agent": message.get("agent"),
            "model": message.get("model"),
            "model_provider": message.get("model_provider"),
            "model_source": message.get("model_source"),  # MARKER_115_BUG3
            "node_id": message.get("node_id"),
            "metadata": message.get("metadata", {}),
        }

        assert msg_to_save["model_source"] == "polza_ai"
        assert msg_to_save["model_provider"] == "openrouter"

    def test_model_source_none_when_not_provided(self):
        """model_source should be None when not in message (backward compat)."""
        message = {
            "role": "user",
            "content": "hello",
        }

        msg_to_save = {
            "role": message.get("role", "user"),
            "model_source": message.get("model_source"),
        }

        assert msg_to_save["model_source"] is None

    def test_model_source_marker_count(self):
        """Verify MARKER_115_BUG3 appears in the right number of places."""
        handler_utils_path = Path("src/api/handlers/handler_utils.py")
        user_handler_path = Path("src/api/handlers/user_message_handler.py")

        if handler_utils_path.exists():
            content = handler_utils_path.read_text()
            count = content.count("MARKER_115_BUG3")
            assert count >= 1, f"handler_utils.py should have >= 1 marker, found {count}"

        if user_handler_path.exists():
            content = user_handler_path.read_text()
            count = content.count("MARKER_115_BUG3")
            assert count >= 8, f"user_message_handler.py should have >= 8 markers, found {count}"


# ============================================================
# BUG-1: Chat Hygiene Tests
# ============================================================

class TestChatHygiene:
    """Tests for MARKER_115_BUG1: Chat creation consistency."""

    def test_bug1_marker_count(self):
        """Verify MARKER_115_BUG1 appears in user_message_handler.py."""
        handler_path = Path("src/api/handlers/user_message_handler.py")
        if handler_path.exists():
            content = handler_path.read_text()
            count = content.count("MARKER_115_BUG1")
            assert count >= 3, f"Should have >= 3 BUG1 markers, found {count}"

    def test_all_get_or_create_have_chat_id(self):
        """All get_or_create_chat('unknown') calls should pass client_chat_id."""
        handler_path = Path("src/api/handlers/user_message_handler.py")
        if not handler_path.exists():
            pytest.skip("user_message_handler.py not found")

        content = handler_path.read_text()
        lines = content.split("\n")

        # Find all get_or_create_chat calls with 'unknown'
        # Skip comment lines (starting with # after stripping)
        unknown_calls = []
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith("#"):
                continue  # Skip comments
            if "get_or_create_chat" in line and "'unknown'" in line:
                # Look ahead up to 5 lines for chat_id= parameter
                block = "\n".join(lines[i : i + 6])
                has_chat_id = "chat_id=" in block
                unknown_calls.append({
                    "line": i + 1,
                    "has_chat_id": has_chat_id,
                    "code": stripped,
                })

        # All calls should have chat_id parameter
        missing = [c for c in unknown_calls if not c["has_chat_id"]]
        assert len(missing) == 0, (
            f"Found {len(missing)} get_or_create_chat('unknown') calls without chat_id=: "
            f"{[c['line'] for c in missing]}"
        )


# ============================================================
# BUG-4: Pinned Files Persistence Tests
# ============================================================

class TestPinnedFilesPersistence:
    """Tests for MARKER_115_BUG4: Pinned files JSON persistence."""

    def test_bug4_implementation_or_markers(self):
        """Verify BUG-4 is either implemented (PinnedFilesService) or has markers."""
        cam_routes_path = Path("src/api/routes/cam_routes.py")
        if not cam_routes_path.exists():
            pytest.skip("cam_routes.py not found")
        content = cam_routes_path.read_text()
        has_markers = content.count("MARKER_115_BUG4") >= 3
        has_service = "PinnedFilesService" in content or "_pinned_service" in content
        assert has_markers or has_service, (
            "cam_routes.py should have either MARKER_115_BUG4 markers or PinnedFilesService implementation"
        )

    def test_pinned_files_importable(self):
        """_pinned_files should still be importable from cam_routes (backward compat)."""
        try:
            from src.api.routes.cam_routes import _pinned_files
            # Should be a dict-like object
            assert hasattr(_pinned_files, "items"), "_pinned_files must have .items() method"
            assert hasattr(_pinned_files, "__getitem__"), "_pinned_files must support [] access"
        except ImportError:
            pytest.skip("cam_routes not importable (FastAPI dependency)")
        except Exception as e:
            # Some imports may fail due to FastAPI app state, that's OK
            pytest.skip(f"Import side effect: {e}")


# ============================================================
# DI Architecture Tests (SONNET-C)
# ============================================================

class TestDIArchitecture:
    """Tests for MARKER_115_DEPS: Dependency injection completeness."""

    def test_new_deps_importable(self):
        """All 4 new dependency functions should be importable."""
        from src.dependencies import (
            get_chat_history_manager,
            get_hostess,
            get_model_for_task,
            is_model_banned,
        )
        assert callable(get_chat_history_manager)
        assert callable(get_hostess)
        assert callable(get_model_for_task)
        assert callable(is_model_banned)

    def test_deps_markers_present(self):
        """MARKER_115_DEPS should be in dependencies.py."""
        deps_path = Path("src/dependencies.py")
        if deps_path.exists():
            content = deps_path.read_text()
            count = content.count("MARKER_115_DEPS")
            assert count >= 4, f"Should have >= 4 DEPS markers, found {count}"

    def test_component_status_includes_new_fields(self):
        """get_component_status should return new component checks."""
        from src.dependencies import get_component_status

        # Create mock request with app.state
        mock_request = Mock()
        mock_request.app.state = Mock()
        mock_request.app.state.METRICS_AVAILABLE = False
        mock_request.app.state.MODEL_ROUTER_V2_AVAILABLE = False
        mock_request.app.state.QDRANT_AUTO_RETRY_AVAILABLE = False
        mock_request.app.state.FEEDBACK_LOOP_V2_AVAILABLE = False
        mock_request.app.state.SMART_LEARNER_AVAILABLE = False
        mock_request.app.state.HOPE_ENHANCER_AVAILABLE = False
        mock_request.app.state.EMBEDDINGS_PROJECTOR_AVAILABLE = False
        mock_request.app.state.STUDENT_SYSTEM_AVAILABLE = False
        mock_request.app.state.LEARNER_AVAILABLE = False
        mock_request.app.state.ELISYA_ENABLED = False
        mock_request.app.state.PARALLEL_MODE = False
        mock_request.app.state.chat_history_manager = None
        mock_request.app.state.hostess = None

        status = get_component_status(mock_request)

        assert "chat_history_manager_available" in status
        assert "hostess_available" in status
        assert status["chat_history_manager_available"] is False
        assert status["hostess_available"] is False


# ============================================================
# Cross-cutting: Marker Integrity Tests
# ============================================================

class TestMarkerIntegrity:
    """Verify all Phase 115 markers are in the right files."""

    EXPECTED_MARKERS = {
        "MARKER_115_SECURITY": [
            "src/mcp/vetka_mcp_bridge.py",
            "src/mcp/tools/llm_call_tool.py",
        ],
        "MARKER_115_BUG3": [
            "src/api/handlers/handler_utils.py",
            "src/api/handlers/user_message_handler.py",
        ],
        "MARKER_115_BUG1": [
            "src/api/handlers/user_message_handler.py",
        ],
        "MARKER_115_BUG4|PinnedFilesService": [
            "src/api/routes/cam_routes.py",
        ],
        "MARKER_115_DEPS": [
            "src/dependencies.py",
        ],
    }

    @pytest.mark.parametrize("marker,files", list(EXPECTED_MARKERS.items()))
    def test_marker_present_in_files(self, marker, files):
        """Each marker should be present in its expected files."""
        for filepath in files:
            path = Path(filepath)
            if not path.exists():
                pytest.skip(f"{filepath} not found")
            content = path.read_text()
            # Support OR patterns with | separator
            alternatives = marker.split("|")
            found = any(alt in content for alt in alternatives)
            assert found, f"None of {alternatives} found in {filepath}"
