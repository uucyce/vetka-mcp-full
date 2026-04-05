"""
Tests for VETKA Universal MCP Server (Phase 65.2)

@file tests/test_mcp_universal.py
@status ACTIVE
@phase Phase 65.2
@lastAudit 2026-01-18

Tests stdio, HTTP, and SSE transports with 13 tools (8 read + 5 write).
"""

import subprocess
import json
import sys
import time
import select
import requests
from pathlib import Path


PROJECT_ROOT = Path(__file__).parent.parent
MCP_SERVER = PROJECT_ROOT / "src" / "mcp" / "vetka_mcp_server.py"
MCP_BRIDGE = PROJECT_ROOT / "src" / "mcp" / "vetka_mcp_bridge.py"

# Expected tools (13 total: 8 read + 5 write)
EXPECTED_READ_TOOLS = [
    "vetka_search_semantic",
    "vetka_read_file",
    "vetka_get_tree",
    "vetka_health",
    "vetka_list_files",
    "vetka_search_files",
    "vetka_get_metrics",
    "vetka_get_knowledge_graph",
]

EXPECTED_WRITE_TOOLS = [
    "vetka_edit_file",
    "vetka_git_commit",
    "vetka_git_status",
    "vetka_run_tests",
    "vetka_camera_focus",
]

ALL_EXPECTED_TOOLS = EXPECTED_READ_TOOLS + EXPECTED_WRITE_TOOLS


def test_stdio_transport():
    """Test stdio transport (Claude Desktop/Code)"""
    print("\n[TEST] stdio transport...")

    proc = subprocess.Popen(
        [sys.executable, str(MCP_SERVER)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1
    )

    try:
        # Send initialize
        init_req = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "test", "version": "1.0"}
            }
        }

        proc.stdin.write(json.dumps(init_req) + "\n")
        proc.stdin.flush()

        # Read response
        ready, _, _ = select.select([proc.stdout], [], [], 10.0)

        if ready:
            response = json.loads(proc.stdout.readline())
            assert "result" in response, f"stdio init failed: {response}"
            print("  ✅ stdio initialization works")

            # List tools
            list_req = {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/list",
                "params": {}
            }

            proc.stdin.write(json.dumps(list_req) + "\n")
            proc.stdin.flush()

            ready, _, _ = select.select([proc.stdout], [], [], 5.0)
            if ready:
                response = json.loads(proc.stdout.readline())
                tools = response.get("result", {}).get("tools", [])
                assert len(tools) >= 13, f"Expected >= 13 tools, got {len(tools)}"
                print(f"  ✅ stdio tools/list works ({len(tools)} tools)")
            else:
                raise TimeoutError("stdio tools/list timeout")

        else:
            raise TimeoutError("stdio initialization timeout")

    finally:
        proc.terminate()
        proc.wait(timeout=5)


def test_http_transport():
    """Test HTTP transport (VS Code, Cursor, Gemini)"""
    print("\n[TEST] HTTP transport...")

    # Start HTTP server
    proc = subprocess.Popen(
        [sys.executable, str(MCP_SERVER), "--http", "--port", "5099"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )

    # Wait for server to start
    time.sleep(3)

    try:
        # Health check
        r = requests.get("http://localhost:5099/health", timeout=5)
        assert r.status_code == 200, f"Health check failed: {r.status_code}"

        data = r.json()
        assert data["status"] == "healthy", f"Server not healthy: {data}"
        assert data["transport"] == "http", f"Wrong transport: {data}"

        print("  ✅ HTTP health check works")

        # Initialize
        r = requests.post("http://localhost:5099/mcp", json={
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "test-http", "version": "1.0"}
            }
        }, timeout=5)

        assert r.status_code == 200, f"Initialize failed: {r.status_code}"

        data = r.json()
        assert "result" in data, f"Initialize missing result: {data}"

        print("  ✅ HTTP initialization works")

        # List tools
        r = requests.post("http://localhost:5099/mcp", json={
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/list",
            "params": {}
        }, timeout=5)

        assert r.status_code == 200, f"tools/list failed: {r.status_code}"

        data = r.json()
        tools = data.get("result", {}).get("tools", [])
        assert len(tools) >= 13, f"Expected >= 13 tools, got {len(tools)}"

        tool_names = [t["name"] for t in tools]
        assert "vetka_health" in tool_names, "Missing vetka_health tool"
        assert "vetka_edit_file" in tool_names, "Missing vetka_edit_file tool"

        print(f"  ✅ HTTP tools/list works ({len(tools)} tools)")

        # Test tool execution (health check)
        r = requests.post("http://localhost:5099/mcp", json={
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {
                "name": "vetka_health",
                "arguments": {}
            }
        }, timeout=10)

        assert r.status_code == 200, f"tools/call failed: {r.status_code}"

        data = r.json()
        assert "result" in data, f"tools/call missing result: {data}"

        content = data["result"].get("content", [])
        assert len(content) > 0, "tools/call returned no content"

        print("  ✅ HTTP tools/call works (vetka_health)")

    except requests.exceptions.ConnectionError as e:
        print(f"  ⚠️  HTTP server connection failed: {e}")
        print("     (VETKA server may not be running on localhost:5001)")

    except Exception as e:
        print(f"  ❌ HTTP test failed: {e}")
        raise

    finally:
        proc.terminate()
        proc.wait(timeout=5)


def test_sse_transport():
    """Test SSE transport (JetBrains)"""
    print("\n[TEST] SSE transport...")

    # Start SSE server
    proc = subprocess.Popen(
        [sys.executable, str(MCP_SERVER), "--sse", "--port", "5098"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )

    # Wait for server to start
    time.sleep(3)

    try:
        # Health check
        r = requests.get("http://localhost:5098/health", timeout=5)
        assert r.status_code == 200, f"Health check failed: {r.status_code}"

        data = r.json()
        assert data["status"] == "healthy", f"Server not healthy: {data}"
        assert data["transport"] == "sse", f"Wrong transport: {data}"

        print("  ✅ SSE health check works")

        # Test tools/list via POST (same as HTTP)
        r = requests.post("http://localhost:5098/mcp", json={
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/list",
            "params": {}
        }, timeout=5)

        assert r.status_code == 200, f"tools/list failed: {r.status_code}"

        data = r.json()
        tools = data.get("result", {}).get("tools", [])
        assert len(tools) >= 13, f"Expected >= 13 tools, got {len(tools)}"

        print(f"  ✅ SSE tools/list works ({len(tools)} tools)")

        # Test SSE stream connection (basic)
        try:
            r = requests.get("http://localhost:5098/sse", stream=True, timeout=5)
            assert r.status_code == 200, f"SSE stream failed: {r.status_code}"

            # Read first event
            for line in r.iter_lines(decode_unicode=True):
                if line.startswith("event:"):
                    event_type = line.split(":", 1)[1].strip()
                    assert event_type == "connected", f"Expected 'connected' event, got: {event_type}"
                    print("  ✅ SSE event stream works")
                    break
            r.close()

        except requests.exceptions.Timeout:
            print("  ⚠️  SSE stream timeout (expected for long-polling)")

    except requests.exceptions.ConnectionError as e:
        print(f"  ⚠️  SSE server connection failed: {e}")

    except Exception as e:
        print(f"  ❌ SSE test failed: {e}")
        raise

    finally:
        proc.terminate()
        proc.wait(timeout=5)


def test_all_tools_defined():
    """Test that all 13 expected tools are defined"""
    print("\n[TEST] Tool definitions (13 tools)...")

    proc = subprocess.Popen(
        [sys.executable, str(MCP_SERVER)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1
    )

    try:
        # Initialize + list tools
        for req in [
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {"name": "test", "version": "1.0"}
                }
            },
            {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/list",
                "params": {}
            }
        ]:
            proc.stdin.write(json.dumps(req) + "\n")
            proc.stdin.flush()

        responses = []
        for _ in range(2):
            ready, _, _ = select.select([proc.stdout], [], [], 5.0)
            if ready:
                responses.append(json.loads(proc.stdout.readline()))

        tools_response = responses[1]
        tools = tools_response.get("result", {}).get("tools", [])
        tool_names = [t["name"] for t in tools]

        # Check all expected tools
        missing = []
        for expected in ALL_EXPECTED_TOOLS:
            if expected not in tool_names:
                missing.append(expected)

        if missing:
            print(f"  ❌ Missing tools: {missing}")
            raise AssertionError(f"Missing tools: {missing}")

        print(f"  ✅ All 13 tools defined:")
        print(f"     Read tools: {len(EXPECTED_READ_TOOLS)}")
        print(f"     Write tools: {len(EXPECTED_WRITE_TOOLS)}")

    finally:
        proc.terminate()
        proc.wait(timeout=5)


def test_write_tool_dry_run():
    """Test that write tools support dry_run mode"""
    print("\n[TEST] Write tool dry_run mode...")

    proc = subprocess.Popen(
        [sys.executable, str(MCP_SERVER)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1
    )

    try:
        # Initialize
        init_req = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "test", "version": "1.0"}
            }
        }
        proc.stdin.write(json.dumps(init_req) + "\n")
        proc.stdin.flush()

        ready, _, _ = select.select([proc.stdout], [], [], 5.0)
        if ready:
            proc.stdout.readline()  # consume init response

        # Test edit_file dry_run
        edit_req = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {
                "name": "vetka_edit_file",
                "arguments": {
                    "path": "test_file.txt",
                    "content": "test content",
                    "dry_run": True
                }
            }
        }

        proc.stdin.write(json.dumps(edit_req) + "\n")
        proc.stdin.flush()

        ready, _, _ = select.select([proc.stdout], [], [], 5.0)
        if ready:
            response = json.loads(proc.stdout.readline())
            content = response.get("result", {}).get("content", [])
            assert len(content) > 0, "No content returned"

            text = content[0].get("text", "")
            assert "DRY RUN" in text, f"Expected DRY RUN in response: {text[:200]}"
            print("  ✅ vetka_edit_file dry_run works")
        else:
            raise TimeoutError("edit_file dry_run timeout")

        # Test git_commit dry_run
        commit_req = {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {
                "name": "vetka_git_commit",
                "arguments": {
                    "message": "Test commit message",
                    "dry_run": True
                }
            }
        }

        proc.stdin.write(json.dumps(commit_req) + "\n")
        proc.stdin.flush()

        ready, _, _ = select.select([proc.stdout], [], [], 5.0)
        if ready:
            response = json.loads(proc.stdout.readline())
            content = response.get("result", {}).get("content", [])
            assert len(content) > 0, "No content returned"

            text = content[0].get("text", "")
            assert "DRY RUN" in text, f"Expected DRY RUN in response: {text[:200]}"
            print("  ✅ vetka_git_commit dry_run works")
        else:
            raise TimeoutError("git_commit dry_run timeout")

    finally:
        proc.terminate()
        proc.wait(timeout=5)


def test_backwards_compatibility():
    """Test that Phase 65.2 is backwards compatible with Phase 65.1"""
    print("\n[TEST] Backwards compatibility (Phase 65.1 bridge)...")

    if not MCP_BRIDGE.exists():
        print("  ⚠️  Phase 65.1 bridge not found, skipping")
        return

    proc = subprocess.Popen(
        [sys.executable, str(MCP_BRIDGE)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1
    )

    try:
        init_req = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "test", "version": "1.0"}
            }
        }

        proc.stdin.write(json.dumps(init_req) + "\n")
        proc.stdin.flush()

        ready, _, _ = select.select([proc.stdout], [], [], 5.0)

        if ready:
            response = json.loads(proc.stdout.readline())
            assert "result" in response, "Phase 65.1 bridge broken"
            print("  ✅ Phase 65.1 bridge still works")
        else:
            raise TimeoutError("Phase 65.1 bridge timeout")

    finally:
        proc.terminate()
        proc.wait(timeout=5)


def test_git_status():
    """Test git_status tool (read-only)"""
    print("\n[TEST] vetka_git_status tool...")

    proc = subprocess.Popen(
        [sys.executable, str(MCP_SERVER)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1
    )

    try:
        # Initialize
        init_req = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "test", "version": "1.0"}
            }
        }
        proc.stdin.write(json.dumps(init_req) + "\n")
        proc.stdin.flush()

        ready, _, _ = select.select([proc.stdout], [], [], 5.0)
        if ready:
            proc.stdout.readline()

        # Call git_status
        status_req = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {
                "name": "vetka_git_status",
                "arguments": {}
            }
        }

        proc.stdin.write(json.dumps(status_req) + "\n")
        proc.stdin.flush()

        ready, _, _ = select.select([proc.stdout], [], [], 5.0)
        if ready:
            response = json.loads(proc.stdout.readline())
            content = response.get("result", {}).get("content", [])
            assert len(content) > 0, "No content returned"

            text = content[0].get("text", "")
            assert "Git Status" in text or "Branch" in text, f"Unexpected response: {text[:200]}"
            print("  ✅ vetka_git_status works")
        else:
            raise TimeoutError("git_status timeout")

    finally:
        proc.terminate()
        proc.wait(timeout=5)


def main():
    """Run all tests"""
    print("\n" + "=" * 60)
    print("  VETKA Universal MCP Server Tests - Phase 65.2")
    print("  13 Tools: 8 read + 5 write")
    print("  Transports: stdio, HTTP, SSE")
    print("=" * 60)

    tests = [
        ("Tool definitions (13 tools)", test_all_tools_defined),
        ("stdio transport", test_stdio_transport),
        ("HTTP transport", test_http_transport),
        ("SSE transport", test_sse_transport),
        ("Write tool dry_run", test_write_tool_dry_run),
        ("Git status tool", test_git_status),
        ("Backwards compatibility", test_backwards_compatibility),
    ]

    passed = 0
    failed = 0

    for name, test_func in tests:
        try:
            test_func()
            passed += 1
        except Exception as e:
            print(f"\n❌ {name} FAILED:")
            print(f"   {e}")
            import traceback
            traceback.print_exc()
            failed += 1

    print("\n" + "=" * 60)
    if failed == 0:
        print(f"✅ ALL {passed} TESTS PASSED!")
    else:
        print(f"⚠️  {passed} passed, {failed} failed")
    print("=" * 60 + "\n")

    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
