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

    def test_mycelium_tool_schema_matches_canonical(self):
        """The mycelium_task_board Tool has the same schema content as canonical."""
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

    def test_no_inline_schema_in_bridge(self):
        """vetka_mcp_bridge must not contain inline action enum for task_board."""
        from pathlib import Path
        bridge_path = Path(__file__).parent.parent / "src" / "mcp" / "vetka_mcp_bridge.py"
        source = bridge_path.read_text()
        # Should NOT have inline "add", "list", "get" enum for task_board
        # The TASK_BOARD_SCHEMA import line should be present instead
        assert "from src.mcp.tools.task_board_tools import TASK_BOARD_SCHEMA" in source
        # Check no inline schema block with action enum near vetka_task_board
        lines = source.split("\n")
        for i, line in enumerate(lines):
            if '"vetka_task_board"' in line or "'vetka_task_board'" in line:
                # Look at surrounding 40 lines for inline enum
                block = "\n".join(lines[max(0, i-5):i+40])
                assert '"add", "list", "get"' not in block, (
                    f"Found inline action enum near vetka_task_board (line {i+1})"
                )

    def test_no_inline_schema_in_mycelium(self):
        """mycelium_mcp_server must not contain inline action enum for task_board."""
        from pathlib import Path
        myc_path = Path(__file__).parent.parent / "src" / "mcp" / "mycelium_mcp_server.py"
        source = myc_path.read_text()
        assert "from src.mcp.tools.task_board_tools import TASK_BOARD_SCHEMA" in source
        lines = source.split("\n")
        for i, line in enumerate(lines):
            if '"mycelium_task_board"' in line or "'mycelium_task_board'" in line:
                block = "\n".join(lines[max(0, i-5):i+40])
                assert '"add", "list", "get"' not in block, (
                    f"Found inline action enum near mycelium_task_board (line {i+1})"
                )
