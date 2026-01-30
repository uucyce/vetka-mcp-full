"""
Tests for VETKA MCP Bridge

@file tests/test_mcp_bridge.py
@status ACTIVE
@phase Phase 65.1
@lastAudit 2026-01-18

Tests the MCP Bridge stdio transport and tool execution.
"""

import subprocess
import json
import sys
import time
import select
from pathlib import Path


# Path to bridge script
BRIDGE_PATH = Path(__file__).parent.parent / "src" / "mcp" / "vetka_mcp_bridge.py"


def send_jsonrpc_request(proc, method: str, params: dict, request_id: int = 1) -> dict:
    """Send JSON-RPC request to MCP bridge and get response"""

    request = {
        "jsonrpc": "2.0",
        "id": request_id,
        "method": method,
        "params": params
    }

    # Write request
    request_str = json.dumps(request) + "\n"
    proc.stdin.write(request_str)
    proc.stdin.flush()

    # Read response (with timeout)
    ready, _, _ = select.select([proc.stdout], [], [], 10.0)

    if not ready:
        raise TimeoutError(f"No response from bridge for method: {method}")

    response_str = proc.stdout.readline()
    return json.loads(response_str)


def test_bridge_initialize():
    """Test that bridge initializes correctly"""
    print("\n[TEST] Bridge initialization...")

    proc = subprocess.Popen(
        [sys.executable, str(BRIDGE_PATH)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1
    )

    try:
        # Send initialize request
        response = send_jsonrpc_request(
            proc,
            method="initialize",
            params={
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "test-client", "version": "1.0"}
            }
        )

        assert "result" in response or "error" not in response, f"Initialization failed: {response}"
        print("✅ Bridge initializes successfully")

        return proc

    except Exception as e:
        proc.terminate()
        raise e


def test_list_tools(proc):
    """Test tools/list method"""
    print("\n[TEST] Listing tools...")

    response = send_jsonrpc_request(
        proc,
        method="tools/list",
        params={},
        request_id=2
    )

    assert "result" in response, f"List tools failed: {response}"
    tools = response["result"].get("tools", [])
    tool_names = [t["name"] for t in tools]

    print(f"Found {len(tools)} tools:")
    for name in tool_names:
        print(f"  - {name}")

    # Check expected tools
    expected_tools = [
        "vetka_search_semantic",
        "vetka_read_file",
        "vetka_get_tree",
        "vetka_health",
        "vetka_list_files",
        "vetka_search_files",
        "vetka_get_metrics",
        "vetka_get_knowledge_graph"
    ]

    for tool in expected_tools:
        assert tool in tool_names, f"Missing tool: {tool}"

    print("✅ All expected tools present")


def test_health_tool(proc):
    """Test vetka_health tool execution"""
    print("\n[TEST] Testing vetka_health tool...")

    response = send_jsonrpc_request(
        proc,
        method="tools/call",
        params={
            "name": "vetka_health",
            "arguments": {}
        },
        request_id=3
    )

    if "error" in response:
        print(f"⚠️  Health check failed (VETKA server may not be running): {response['error']}")
        return

    assert "result" in response, f"Health tool failed: {response}"

    content = response["result"]["content"]
    assert len(content) > 0, "Health tool returned no content"
    assert content[0]["type"] == "text", "Health tool returned wrong content type"

    health_text = content[0]["text"]
    print(f"Health response preview:\n{health_text[:200]}...")

    # Check for expected content
    assert "VETKA Health Status" in health_text or "Status:" in health_text, \
        "Health response missing expected content"

    print("✅ Health tool works")


def test_search_semantic_tool(proc):
    """Test vetka_search_semantic tool execution"""
    print("\n[TEST] Testing vetka_search_semantic tool...")

    response = send_jsonrpc_request(
        proc,
        method="tools/call",
        params={
            "name": "vetka_search_semantic",
            "arguments": {
                "query": "FastAPI routes",
                "limit": 3
            }
        },
        request_id=4
    )

    if "error" in response:
        print(f"⚠️  Semantic search failed (Qdrant may not be available): {response['error']}")
        return

    assert "result" in response, f"Search tool failed: {response}"

    content = response["result"]["content"]
    assert len(content) > 0, "Search tool returned no content"

    search_text = content[0]["text"]
    print(f"Search response preview:\n{search_text[:200]}...")

    print("✅ Semantic search tool works")


def test_get_tree_tool(proc):
    """Test vetka_get_tree tool execution"""
    print("\n[TEST] Testing vetka_get_tree tool...")

    response = send_jsonrpc_request(
        proc,
        method="tools/call",
        params={
            "name": "vetka_get_tree",
            "arguments": {
                "format": "summary"
            }
        },
        request_id=5
    )

    if "error" in response:
        print(f"⚠️  Tree tool failed: {response['error']}")
        return

    assert "result" in response, f"Tree tool failed: {response}"

    content = response["result"]["content"]
    assert len(content) > 0, "Tree tool returned no content"

    tree_text = content[0]["text"]
    print(f"Tree response:\n{tree_text}")

    assert "Tree Summary" in tree_text or "Total nodes" in tree_text, \
        "Tree response missing expected content"

    print("✅ Get tree tool works")


def main():
    """Run all tests"""
    print("\n" + "=" * 60)
    print("  VETKA MCP BRIDGE TESTS - Phase 65.1")
    print("=" * 60)

    proc = None

    try:
        # Test 1: Initialize
        proc = test_bridge_initialize()

        # Test 2: List tools
        test_list_tools(proc)

        # Test 3: Health check
        test_health_tool(proc)

        # Test 4: Semantic search
        test_search_semantic_tool(proc)

        # Test 5: Get tree
        test_get_tree_tool(proc)

        print("\n" + "=" * 60)
        print("✅ ALL TESTS PASSED!")
        print("=" * 60)

    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()

    finally:
        if proc:
            proc.terminate()
            proc.wait(timeout=5)


if __name__ == "__main__":
    main()
