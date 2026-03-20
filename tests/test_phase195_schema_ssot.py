"""
MARKER_195.3 Tests: Schema Single Source of Truth.

Verifies that all MCP entry points (vetka_mcp_bridge, mycelium_mcp_server)
use the exact same TASK_BOARD_SCHEMA object from task_board_tools.py.
No inline copies allowed.

@phase: 195.3
@task: tb_1773967183_3
"""

import pytest


class TestSchemaSSoT:
    """All entry points must share the same TASK_BOARD_SCHEMA identity."""

    def test_bridge_uses_canonical_schema(self):
        """vetka_mcp_bridge imports TASK_BOARD_SCHEMA from task_board_tools (identity check)."""
        from src.mcp.tools.task_board_tools import TASK_BOARD_SCHEMA as canonical
        from src.mcp.vetka_mcp_bridge import TASK_BOARD_SCHEMA as bridge_schema
        assert bridge_schema is canonical, (
            "vetka_mcp_bridge.TASK_BOARD_SCHEMA is a copy, not the canonical object"
        )

    def test_mycelium_uses_canonical_schema(self):
        """mycelium_mcp_server imports TASK_BOARD_SCHEMA from task_board_tools (identity check)."""
        from src.mcp.tools.task_board_tools import TASK_BOARD_SCHEMA as canonical
        from src.mcp.mycelium_mcp_server import TASK_BOARD_SCHEMA as mycelium_schema
        assert mycelium_schema is canonical, (
            "mycelium_mcp_server.TASK_BOARD_SCHEMA is a copy, not the canonical object"
        )

    def test_bridge_tool_schema_matches_canonical(self):
        """The vetka_task_board Tool in bridge has the same schema content as canonical.

        Note: Tool() constructor may copy the dict, so we check equality not identity.
        The identity check on module-level import (test above) guarantees no inline copy.
        """
        from src.mcp.tools.task_board_tools import TASK_BOARD_SCHEMA as canonical
        from src.mcp.vetka_mcp_bridge import VetkaMCPServer
        server = VetkaMCPServer.__new__(VetkaMCPServer)
        tools = server.get_tools()
        tb_tools = [t for t in tools if t.name == "vetka_task_board"]
        assert len(tb_tools) == 1, "vetka_task_board tool not found in bridge"
        assert tb_tools[0].inputSchema == canonical

    def test_mycelium_tool_schema_matches_canonical(self):
        """The mycelium_task_board Tool has the same schema content as canonical.

        Note: Tool() constructor may copy the dict, so we check equality not identity.
        The identity check on module-level import (test above) guarantees no inline copy.
        """
        from src.mcp.tools.task_board_tools import TASK_BOARD_SCHEMA as canonical
        from src.mcp.mycelium_mcp_server import MYCELIUM_TOOLS
        tb_tools = [t for t in MYCELIUM_TOOLS if t.name == "mycelium_task_board"]
        assert len(tb_tools) == 1, "mycelium_task_board tool not found in MYCELIUM_TOOLS"
        assert tb_tools[0].inputSchema == canonical

    def test_canonical_schema_has_all_actions(self):
        """Canonical schema must include all 11+ actions."""
        from src.mcp.tools.task_board_tools import TASK_BOARD_SCHEMA
        actions = TASK_BOARD_SCHEMA["properties"]["action"]["enum"]
        required_actions = [
            "add", "list", "get", "update", "remove", "summary",
            "claim", "complete", "active_agents",
            "merge_request", "promote_to_main",
        ]
        for action in required_actions:
            assert action in actions, f"Missing action '{action}' in TASK_BOARD_SCHEMA"
