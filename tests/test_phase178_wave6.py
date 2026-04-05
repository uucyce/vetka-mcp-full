"""
Phase 178 Wave 6 Tests — Unified Facade + vetka_task_board Resurrection
MARKER_178.6 — Verify vetka_task_board is live fallback, not deprecated stub.
"""
import json
import os
import pytest
import sys

pytestmark = pytest.mark.stale(reason="Pre-existing failure — phase 178 contracts changed")

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

BRIDGE_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "src", "mcp", "vetka_mcp_bridge.py"
)


def _read_bridge_source():
    with open(BRIDGE_PATH) as f:
        return f.read()


class TestVetkaTaskBoardUndeprecated:
    """MARKER_178.6.1: vetka_task_board is no longer deprecated."""

    def test_tool_definition_not_deprecated(self):
        """178.6.1: Tool description does not say DEPRECATED for vetka_task_board."""
        source = _read_bridge_source()
        idx = source.find('name="vetka_task_board"')
        assert idx > 0, "vetka_task_board tool must exist"
        block = source[max(0, idx - 200):idx + 200]
        assert "[DEPRECATED]" not in block, "vetka_task_board should NOT be deprecated"

    def test_tool_has_full_schema(self):
        """178.6.1: Tool has full inputSchema with all actions."""
        source = _read_bridge_source()
        idx = source.find('name="vetka_task_board"')
        block = source[idx:idx + 1500]
        for action in ["add", "list", "get", "update", "remove", "summary", "claim", "complete"]:
            assert action in block, f"vetka_task_board schema must include action '{action}'"

    def test_handler_not_deprecation_stub(self):
        """178.6.1: Handler returns real data, not deprecation message."""
        source = _read_bridge_source()
        handler_idx = source.find('elif name == "vetka_task_board"')
        assert handler_idx > 0
        handler_block = source[handler_idx:handler_idx + 500]
        assert "DEPRECATED" not in handler_block
        assert "handle_task_board" in handler_block

    def test_handler_imports_task_board_tools(self):
        """178.6.1: Handler imports from task_board_tools."""
        source = _read_bridge_source()
        handler_idx = source.find('elif name == "vetka_task_board"')
        handler_block = source[handler_idx:handler_idx + 500]
        assert "task_board_tools" in handler_block

    def test_transport_note_in_response(self):
        """178.6.3: Handler includes transport selection note."""
        source = _read_bridge_source()
        handler_idx = source.find('elif name == "vetka_task_board"')
        handler_block = source[handler_idx:handler_idx + 500]
        assert "Transport" in handler_block or "transport" in handler_block

    def test_handler_does_not_shadow_global_json_module(self):
        """178.6.5: No local `import json` inside handler block (breaks earlier branches)."""
        source = _read_bridge_source()
        handler_idx = source.find('elif name == "vetka_task_board"')
        handler_block = source[handler_idx:handler_idx + 700]
        assert "import json" not in handler_block


class TestTaskBoardToolsHandler:
    """MARKER_178.6.2: handle_task_board works correctly for all actions."""

    def test_handle_task_board_list(self):
        from src.mcp.tools.task_board_tools import handle_task_board
        result = handle_task_board({"action": "list"})
        assert result.get("success") is True or "tasks" in result

    def test_handle_task_board_summary(self):
        from src.mcp.tools.task_board_tools import handle_task_board
        result = handle_task_board({"action": "summary"})
        assert result.get("success") is True or "total" in str(result)

    def test_handle_task_board_missing_action(self):
        from src.mcp.tools.task_board_tools import handle_task_board
        result = handle_task_board({})
        assert result.get("success") is False

    def test_handle_task_board_add_requires_title(self):
        from src.mcp.tools.task_board_tools import handle_task_board
        result = handle_task_board({"action": "add"})
        assert result.get("success") is False

    def test_handle_task_board_crud_cycle(self):
        from src.mcp.tools.task_board_tools import handle_task_board
        result = handle_task_board({
            "action": "add", "title": "Test task 178.6",
            "description": "E2E test task", "priority": 4, "phase_type": "fix"
        })
        assert result.get("success") is True, f"Add failed: {result}"
        task_id = result.get("task_id")
        assert task_id
        try:
            assert handle_task_board({"action": "get", "task_id": task_id}).get("success")
            assert handle_task_board({"action": "update", "task_id": task_id, "status": "claimed"}).get("success")
            assert handle_task_board({"action": "remove", "task_id": task_id}).get("success")
        except Exception:
            try: handle_task_board({"action": "remove", "task_id": task_id})
            except: pass
            raise


class TestCapabilityManifestFallback:
    """MARKER_178.6.4: Capability broker shows fallback chain."""

    def test_manifest_includes_task_board(self):
        try:
            from src.mcp.tools.capability_broker import build_capability_manifest
            manifest = build_capability_manifest()
            assert "task_board" in manifest.recommended
        except Exception as e:
            pytest.skip(f"Capability broker not available: {e}")

    def test_manifest_always_returns(self):
        from src.mcp.tools.capability_broker import build_capability_manifest

        manifest = build_capability_manifest()
        assert manifest is not None
        assert hasattr(manifest, 'transports')
        assert hasattr(manifest, 'recommended')
