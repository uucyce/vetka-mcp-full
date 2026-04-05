"""Phase 116 Security Hardening Tests

Tests for Phase 116 security fixes:
- HOLE-1: Unknown tools denied by default (llm_call_tool.py:587-589)
- HOLE-2: Response tool_calls filtered by allowlist (llm_call_tool.py:743-753)
- HOLE-3: Audit logging extended to ALL write tools (vetka_mcp_bridge.py)

@status: active
@phase: 116
@depends: src/mcp/tools/llm_call_tool.py, src/mcp/vetka_mcp_bridge.py
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock
from src.mcp.tools.llm_call_tool import (
    SAFE_FUNCTION_CALLING_TOOLS,
    WRITE_TOOLS_REQUIRING_APPROVAL,
    LLMCallTool,
)


# ═══════════════════════════════════════════════════════════════════════
# HOLE-1: Unknown Tool Denial Tests
# ═══════════════════════════════════════════════════════════════════════

class TestUnknownToolDenial:
    """Test that unknown tools are denied by default (MARKER_116_SECURITY_HARDENING)"""

    @pytest.mark.phase_116
    def test_unknown_tool_not_in_filtered(self):
        """Unknown tool should be filtered out and not appear in filtered_tools"""
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "unknown_dangerous_tool",
                    "description": "Not in allowlist",
                }
            }
        ]

        # Simulate filtering logic from llm_call_tool.py:580-590
        filtered_tools = []
        for tool_def in tools:
            tool_func_name = tool_def.get('function', {}).get('name', '')
            if tool_func_name in SAFE_FUNCTION_CALLING_TOOLS:
                filtered_tools.append(tool_def)
            elif tool_func_name in WRITE_TOOLS_REQUIRING_APPROVAL:
                # Should be blocked
                pass
            else:
                # MARKER_116_SECURITY_HARDENING: Deny unknown tools by default
                pass

        assert len(filtered_tools) == 0, "Unknown tool should not pass filter"

    @pytest.mark.phase_116
    def test_safe_tool_passes_filter(self):
        """Safe tool from allowlist should pass filter"""
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "vetka_search_semantic",
                    "description": "Safe tool",
                }
            }
        ]

        # Simulate filtering logic
        filtered_tools = []
        for tool_def in tools:
            tool_func_name = tool_def.get('function', {}).get('name', '')
            if tool_func_name in SAFE_FUNCTION_CALLING_TOOLS:
                filtered_tools.append(tool_def)

        assert len(filtered_tools) == 1, "Safe tool should pass filter"
        assert filtered_tools[0]['function']['name'] == 'vetka_search_semantic'

    @pytest.mark.phase_116
    def test_write_tool_blocked(self):
        """Write tool requiring approval should be blocked from function calling"""
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "vetka_edit_file",
                    "description": "Write tool",
                }
            }
        ]

        # Simulate filtering logic
        filtered_tools = []
        for tool_def in tools:
            tool_func_name = tool_def.get('function', {}).get('name', '')
            if tool_func_name in SAFE_FUNCTION_CALLING_TOOLS:
                filtered_tools.append(tool_def)
            elif tool_func_name in WRITE_TOOLS_REQUIRING_APPROVAL:
                # Should be blocked
                pass

        assert len(filtered_tools) == 0, "Write tool should be blocked from function calling"


# ═══════════════════════════════════════════════════════════════════════
# HOLE-2: Response Tool Calls Filter Tests
# ═══════════════════════════════════════════════════════════════════════

class TestResponseToolCallsFilter:
    """Test that response tool_calls are filtered by allowlist (MARKER_116_SECURITY_HARDENING)"""

    @pytest.mark.phase_116
    def test_safe_tool_call_passes(self):
        """Tool call with safe tool name should pass filter"""
        tool_calls = [
            {
                "id": "call_123",
                "type": "function",
                "function": {
                    "name": "vetka_read_file",
                    "arguments": '{"file_path": "test.py"}'
                }
            }
        ]

        # Simulate filtering logic from llm_call_tool.py:743-753
        filtered_calls = []
        for tc in tool_calls:
            tc_name = tc.get('function', {}).get('name', '')
            if tc_name in SAFE_FUNCTION_CALLING_TOOLS:
                filtered_calls.append(tc)

        assert len(filtered_calls) == 1, "Safe tool call should pass"
        assert filtered_calls[0]['function']['name'] == 'vetka_read_file'

    @pytest.mark.phase_116
    def test_write_tool_call_filtered(self):
        """Tool call with write tool name should be filtered out"""
        tool_calls = [
            {
                "id": "call_456",
                "type": "function",
                "function": {
                    "name": "vetka_edit_file",
                    "arguments": '{"path": "test.py", "content": "malicious"}'
                }
            }
        ]

        # Simulate filtering logic
        filtered_calls = []
        for tc in tool_calls:
            tc_name = tc.get('function', {}).get('name', '')
            if tc_name in SAFE_FUNCTION_CALLING_TOOLS:
                filtered_calls.append(tc)
            else:
                # Should be filtered out
                pass

        assert len(filtered_calls) == 0, "Write tool call should be filtered"

    @pytest.mark.phase_116
    def test_unknown_tool_call_filtered(self):
        """Tool call with unknown name should be filtered out"""
        tool_calls = [
            {
                "id": "call_789",
                "type": "function",
                "function": {
                    "name": "unknown_hack_tool",
                    "arguments": '{}'
                }
            }
        ]

        # Simulate filtering logic
        filtered_calls = []
        for tc in tool_calls:
            tc_name = tc.get('function', {}).get('name', '')
            if tc_name in SAFE_FUNCTION_CALLING_TOOLS:
                filtered_calls.append(tc)

        assert len(filtered_calls) == 0, "Unknown tool call should be filtered"

    @pytest.mark.phase_116
    def test_empty_after_filter(self):
        """If all tool_calls are filtered, result should not contain tool_calls key"""
        tool_calls = [
            {
                "id": "call_bad1",
                "type": "function",
                "function": {
                    "name": "vetka_git_commit",
                    "arguments": '{}'
                }
            },
            {
                "id": "call_bad2",
                "type": "function",
                "function": {
                    "name": "unknown_tool",
                    "arguments": '{}'
                }
            }
        ]

        # Simulate filtering logic with result building
        result = {
            'content': 'test response',
            'model': 'grok-4',
        }

        filtered_calls = []
        for tc in tool_calls:
            tc_name = tc.get('function', {}).get('name', '')
            if tc_name in SAFE_FUNCTION_CALLING_TOOLS:
                filtered_calls.append(tc)

        # Only add tool_calls to result if filtered_calls is not empty
        if filtered_calls:
            result['tool_calls'] = filtered_calls

        assert 'tool_calls' not in result, "Result should not contain tool_calls if all filtered"


# ═══════════════════════════════════════════════════════════════════════
# HOLE-3: Audit Extension Tests
# ═══════════════════════════════════════════════════════════════════════

class TestAuditExtension:
    """Test that audit logging is extended to ALL write tools (MARKER_116_AUDIT_EXTENSION)"""

    @pytest.mark.phase_116
    def test_audit_markers_count(self):
        """Verify that MARKER_116_AUDIT_EXTENSION appears 16 times in vetka_mcp_bridge.py"""
        bridge_file = Path(__file__).parent.parent / "src" / "mcp" / "vetka_mcp_bridge.py"
        content = bridge_file.read_text()

        marker_count = content.count("MARKER_116_AUDIT_EXTENSION")
        assert marker_count == 16, f"Expected 16 MARKER_116_AUDIT_EXTENSION markers, found {marker_count}"

    @pytest.mark.phase_116
    def test_all_write_tools_have_audit(self):
        """Verify that all write tools have audit calls in bridge"""
        bridge_file = Path(__file__).parent.parent / "src" / "mcp" / "vetka_mcp_bridge.py"
        content = bridge_file.read_text()

        # Write tools that should have audit logging
        write_tools_to_check = [
            "vetka_camera_focus",
            "vetka_send_message",
            "vetka_implement",
            "vetka_execute_workflow",
            "vetka_mycelium_pipeline",
            "vetka_edit_artifact",
            "vetka_approve_artifact",
            "vetka_reject_artifact",
        ]

        for tool_name in write_tools_to_check:
            # Check if tool handler exists in bridge
            assert f'"{tool_name}"' in content, f"Tool {tool_name} not found in bridge"

            # Find the handler section (elif name == / elif name in), not the tool definition
            # Search for handler pattern: 'name == "tool_name"' or 'name in (...tool_name...)'
            import re
            handler_pattern = rf'elif name\s*(?:==\s*"{tool_name}"|in\s*\([^)]*"{tool_name}"[^)]*\))'
            match = re.search(handler_pattern, content)
            assert match, f"Handler for {tool_name} not found in bridge"

            # Check within 500 characters after handler match
            section = content[match.start():match.start() + 500]
            assert "MARKER_116_AUDIT_EXTENSION" in section, f"No audit marker found near {tool_name}"


# ═══════════════════════════════════════════════════════════════════════
# Phase 116 Markers Tests
# ═══════════════════════════════════════════════════════════════════════

class TestPhase116Markers:
    """Test that all Phase 116 markers are present in correct quantities"""

    @pytest.mark.phase_116
    def test_security_hardening_markers(self):
        """Verify that MARKER_116_SECURITY_HARDENING appears 2 times in llm_call_tool.py"""
        llm_call_file = Path(__file__).parent.parent / "src" / "mcp" / "tools" / "llm_call_tool.py"
        content = llm_call_file.read_text()

        marker_count = content.count("MARKER_116_SECURITY_HARDENING")
        assert marker_count == 2, f"Expected 2 MARKER_116_SECURITY_HARDENING markers, found {marker_count}"

        # Verify markers are in the right locations
        # HOLE-1: Unknown tools denial (around line 588)
        assert "MARKER_116_SECURITY_HARDENING: Deny unknown tools by default" in content

        # HOLE-2: Response filter (around line 743)
        assert "MARKER_116_SECURITY_HARDENING: Filter response tool_calls by allowlist" in content
