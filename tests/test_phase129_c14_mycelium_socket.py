"""
MARKER_129.C14 Tests: useMyceliumSocket hook + DevPanel integration.

Tests verify:
- MARKER_129.C14A: Hook file exists with correct structure
- MARKER_129.C14B: DevPanel imports and uses the hook
- WebSocket message dispatch to CustomEvents
"""

import pytest
from pathlib import Path

# Project root
PROJECT_ROOT = Path(__file__).parent.parent


class TestPhase129_C14A_MyceliumSocketHook:
    """Tests for useMyceliumSocket hook file."""

    def test_marker_c14a_in_hook_file(self):
        """MARKER_129.C14A should exist in useMyceliumSocket.ts."""
        hook_path = PROJECT_ROOT / "client/src/hooks/useMyceliumSocket.ts"
        assert hook_path.exists(), "useMyceliumSocket.ts should exist"

        content = hook_path.read_text()
        assert "MARKER_129.C14A" in content, "MARKER_129.C14A should be in hook file"

    def test_hook_exports_function(self):
        """Hook should export useMyceliumSocket function."""
        hook_path = PROJECT_ROOT / "client/src/hooks/useMyceliumSocket.ts"
        content = hook_path.read_text()

        assert "export function useMyceliumSocket" in content
        assert "return { connected }" in content

    def test_hook_connects_to_port_8082(self):
        """Hook should connect to MYCELIUM on port 8082."""
        hook_path = PROJECT_ROOT / "client/src/hooks/useMyceliumSocket.ts"
        content = hook_path.read_text()

        assert "ws://localhost:8082" in content

    def test_hook_dispatches_custom_events(self):
        """Hook should dispatch same CustomEvents as useSocket.ts."""
        hook_path = PROJECT_ROOT / "client/src/hooks/useMyceliumSocket.ts"
        content = hook_path.read_text()

        # Must dispatch these exact events for DevPanel compatibility
        assert "pipeline-activity" in content
        assert "task-board-updated" in content
        assert "pipeline-stats" in content

    def test_hook_has_reconnect_logic(self):
        """Hook should auto-reconnect on disconnect."""
        hook_path = PROJECT_ROOT / "client/src/hooks/useMyceliumSocket.ts"
        content = hook_path.read_text()

        assert "RECONNECT_INTERVAL" in content
        assert "setTimeout(connect" in content

    def test_hook_has_ping_keepalive(self):
        """Hook should ping server to keep connection alive."""
        hook_path = PROJECT_ROOT / "client/src/hooks/useMyceliumSocket.ts"
        content = hook_path.read_text()

        assert "PING_INTERVAL" in content
        assert "type: 'ping'" in content


class TestPhase129_C14B_DevPanelIntegration:
    """Tests for DevPanel using useMyceliumSocket."""

    def test_marker_c14b_in_devpanel(self):
        """MARKER_129.C14B should exist in DevPanel.tsx."""
        devpanel_path = PROJECT_ROOT / "client/src/components/panels/DevPanel.tsx"
        assert devpanel_path.exists()

        content = devpanel_path.read_text()
        assert "MARKER_129.C14B" in content

    def test_devpanel_imports_mycelium_hook(self):
        """DevPanel should import useMyceliumSocket."""
        devpanel_path = PROJECT_ROOT / "client/src/components/panels/DevPanel.tsx"
        content = devpanel_path.read_text()

        assert "import { useMyceliumSocket }" in content
        assert "useMyceliumSocket" in content

    def test_devpanel_has_mycelium_connected_state(self):
        """DevPanel should use connected state from hook."""
        devpanel_path = PROJECT_ROOT / "client/src/components/panels/DevPanel.tsx"
        content = devpanel_path.read_text()

        assert "myceliumConnected" in content

    def test_devpanel_shows_connection_indicator(self):
        """DevPanel should show MYC connection indicator."""
        devpanel_path = PROJECT_ROOT / "client/src/components/panels/DevPanel.tsx"
        content = devpanel_path.read_text()

        # Should show "MYC" label
        assert "MYC" in content
        # Should have green color when connected
        assert "#4a4" in content


class TestPhase129_C14_MessageTypes:
    """Tests for supported message types."""

    def test_handles_pipeline_activity(self):
        """Hook should handle pipeline_activity messages."""
        hook_path = PROJECT_ROOT / "client/src/hooks/useMyceliumSocket.ts"
        content = hook_path.read_text()

        assert "case 'pipeline_activity'" in content

    def test_handles_task_board_updated(self):
        """Hook should handle task_board_updated messages."""
        hook_path = PROJECT_ROOT / "client/src/hooks/useMyceliumSocket.ts"
        content = hook_path.read_text()

        assert "case 'task_board_updated'" in content

    def test_handles_pipeline_complete(self):
        """Hook should handle pipeline_complete messages."""
        hook_path = PROJECT_ROOT / "client/src/hooks/useMyceliumSocket.ts"
        content = hook_path.read_text()

        assert "case 'pipeline_complete'" in content

    def test_handles_pipeline_failed(self):
        """Hook should handle pipeline_failed messages."""
        hook_path = PROJECT_ROOT / "client/src/hooks/useMyceliumSocket.ts"
        content = hook_path.read_text()

        assert "case 'pipeline_failed'" in content

    def test_handles_pong(self):
        """Hook should handle pong (heartbeat response)."""
        hook_path = PROJECT_ROOT / "client/src/hooks/useMyceliumSocket.ts"
        content = hook_path.read_text()

        assert "case 'pong'" in content
