"""
VETKA MCP Server Test Suite
Tests the MCP (Model Context Protocol) server functionality.

Run: python -m pytest tests/test_mcp_server.py -v
Or:  python tests/test_mcp_server.py (standalone)
"""

import json
import time
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class MockSocketIO:
    """Mock SocketIO for testing without Flask"""

    def __init__(self):
        self.emissions = []

    def emit(self, event, data, namespace=None):
        self.emissions.append({
            'event': event,
            'data': data,
            'namespace': namespace
        })


def test_mcp_server_initialization():
    """Test 1: MCP Server initializes correctly with 4 tools"""
    from src.mcp.mcp_server import MCPServer

    socketio = MockSocketIO()
    server = MCPServer(socketio)

    # Register tools manually for testing
    from src.mcp.tools import SearchTool, GetTreeTool, GetNodeTool, CreateBranchTool

    server.register_tool(SearchTool())
    server.register_tool(GetTreeTool())
    server.register_tool(GetNodeTool())
    server.register_tool(CreateBranchTool())

    assert len(server.tools) == 4, f"Expected 4 tools, got {len(server.tools)}"
    assert 'vetka_search' in server.tools
    assert 'vetka_get_tree' in server.tools
    assert 'vetka_get_node' in server.tools
    assert 'vetka_create_branch' in server.tools

    print("✅ Test 1: MCP Server initialization - PASSED")
    return True


def test_list_tools_openai_format():
    """Test 2: list_tools returns OpenAI-compatible schema"""
    from src.mcp.mcp_server import MCPServer
    from src.mcp.tools import SearchTool, GetTreeTool, GetNodeTool, CreateBranchTool

    socketio = MockSocketIO()
    server = MCPServer(socketio)

    server.register_tool(SearchTool())
    server.register_tool(GetTreeTool())
    server.register_tool(GetNodeTool())
    server.register_tool(CreateBranchTool())

    tools = server.list_tools()

    assert len(tools) == 4, f"Expected 4 tools, got {len(tools)}"

    for tool in tools:
        # OpenAI format validation
        assert 'type' in tool, "Missing 'type' field"
        assert tool['type'] == 'function', f"Expected type='function', got '{tool['type']}'"
        assert 'function' in tool, "Missing 'function' field"
        assert 'name' in tool['function'], "Missing 'function.name'"
        assert 'description' in tool['function'], "Missing 'function.description'"
        assert 'parameters' in tool['function'], "Missing 'function.parameters'"
        assert 'type' in tool['function']['parameters'], "Missing 'parameters.type'"
        assert tool['function']['parameters']['type'] == 'object', "Parameters type should be 'object'"

    print("✅ Test 2: list_tools OpenAI format - PASSED")
    return True


def test_search_tool_schema():
    """Test 3: vetka_search tool has correct schema"""
    from src.mcp.tools import SearchTool

    tool = SearchTool()

    assert tool.name == 'vetka_search'
    assert 'semantic' in tool.description.lower() or 'search' in tool.description.lower()

    schema = tool.schema
    assert schema['type'] == 'object'
    assert 'query' in schema['properties']
    assert 'query' in schema.get('required', [])

    # Check optional params
    assert 'limit' in schema['properties']

    print("✅ Test 3: vetka_search schema - PASSED")
    return True


def test_tree_tool_schema():
    """Test 4: vetka_get_tree tool has correct schema"""
    from src.mcp.tools import GetTreeTool

    tool = GetTreeTool()

    assert tool.name == 'vetka_get_tree'

    schema = tool.schema
    assert schema['type'] == 'object'
    assert 'path' in schema['properties']
    assert 'depth' in schema['properties']

    print("✅ Test 4: vetka_get_tree schema - PASSED")
    return True


def test_node_tool_schema():
    """Test 5: vetka_get_node tool has correct schema"""
    from src.mcp.tools import GetNodeTool

    tool = GetNodeTool()

    assert tool.name == 'vetka_get_node'

    schema = tool.schema
    assert schema['type'] == 'object'
    assert 'path' in schema['properties']
    assert 'path' in schema.get('required', [])

    print("✅ Test 5: vetka_get_node schema - PASSED")
    return True


def test_branch_tool_schema():
    """Test 6: vetka_create_branch tool has correct schema (dry-run)"""
    from src.mcp.tools import CreateBranchTool

    tool = CreateBranchTool()

    assert tool.name == 'vetka_create_branch'

    schema = tool.schema
    assert schema['type'] == 'object'
    assert 'name' in schema['properties']
    assert 'parent_path' in schema['properties']
    assert 'name' in schema.get('required', [])
    assert 'parent_path' in schema.get('required', [])

    # Test dry-run execution
    result = tool.safe_execute({
        'name': 'test_branch',
        'parent_path': 'src/modules'
    })

    assert result['success'] == True
    assert result['result']['status'] == 'dry_run'
    assert 'test_branch' in result['result']['full_path']

    print("✅ Test 6: vetka_create_branch schema & dry-run - PASSED")
    return True


def test_tool_call_unknown_tool():
    """Test 7: Handle unknown tool gracefully"""
    from src.mcp.mcp_server import MCPServer
    from src.mcp.tools import SearchTool

    socketio = MockSocketIO()
    server = MCPServer(socketio)
    server.register_tool(SearchTool())

    response = server.handle_tool_call('test-agent', {
        'id': 'req-001',
        'name': 'unknown_tool',
        'arguments': {}
    })

    assert response['jsonrpc'] == '2.0'
    assert response['id'] == 'req-001'
    assert 'error' in response
    assert response['error']['code'] == -32601  # Method not found

    print("✅ Test 7: Unknown tool error handling - PASSED")
    return True


def test_tool_validation():
    """Test 8: Tool validates required arguments"""
    from src.mcp.tools import SearchTool

    tool = SearchTool()

    # Missing required 'query'
    error = tool.validate_arguments({})
    assert error is not None
    assert 'query' in error.lower()

    # Valid arguments
    error = tool.validate_arguments({'query': 'test search'})
    assert error is None

    print("✅ Test 8: Tool argument validation - PASSED")
    return True


def test_agent_session_tracking():
    """Test 9: Agent sessions are tracked correctly"""
    from src.mcp.mcp_server import MCPServer

    socketio = MockSocketIO()
    server = MCPServer(socketio)

    # Connect agent
    server.agent_sessions['agent-001'] = {
        'connected_at': time.time(),
        'tools': ['vetka_search'],
        'requests': 0
    }

    assert 'agent-001' in server.agent_sessions
    assert len(server.agent_sessions) == 1

    # Disconnect agent
    server.handle_disconnect('agent-001')
    assert 'agent-001' not in server.agent_sessions

    print("✅ Test 9: Agent session tracking - PASSED")
    return True


def test_json_rpc_response_format():
    """Test 10: Responses follow JSON-RPC 2.0 format"""
    from src.mcp.mcp_server import MCPServer
    from src.mcp.tools import CreateBranchTool

    socketio = MockSocketIO()
    server = MCPServer(socketio)
    server.register_tool(CreateBranchTool())

    response = server.handle_tool_call('agent-001', {
        'id': 'req-123',
        'name': 'vetka_create_branch',
        'arguments': {
            'name': 'test',
            'parent_path': 'src'
        }
    })

    # JSON-RPC 2.0 fields
    assert response['jsonrpc'] == '2.0'
    assert response['id'] == 'req-123'
    assert 'result' in response or 'error' in response

    # Success response should have result
    if 'result' in response:
        assert response['result'] is not None

    print("✅ Test 10: JSON-RPC 2.0 format - PASSED")
    return True


# ============== Phase 22-MCP-2 Tests ==============

def test_all_11_tools_registered():
    """Test 11: All 11 tools registered"""
    from src.mcp.mcp_server import MCPServer
    from src.mcp import tools

    socketio = MockSocketIO()
    server = MCPServer(socketio)

    # Register all tools
    server.register_tool(tools.SearchTool())
    server.register_tool(tools.SearchKnowledgeTool())
    server.register_tool(tools.GetTreeTool())
    server.register_tool(tools.GetNodeTool())
    server.register_tool(tools.ListFilesTool())
    server.register_tool(tools.ReadFileTool())
    server.register_tool(tools.GitStatusTool())
    server.register_tool(tools.CreateBranchTool())
    server.register_tool(tools.EditFileTool())
    server.register_tool(tools.GitCommitTool())
    server.register_tool(tools.RunTestsTool())

    assert len(server.tools) == 11, f"Expected 11 tools, got {len(server.tools)}"
    print("✅ Test 11: All 11 tools registered - PASSED")
    return True


def test_list_files_tool():
    """Test 12: vetka_list_files works"""
    from src.mcp.tools import ListFilesTool

    tool = ListFilesTool()
    result = tool.safe_execute({"path": "src", "depth": 1})

    assert result["success"], f"Failed: {result.get('error')}"
    assert "items" in result["result"]
    assert result["result"]["count"] > 0
    print("✅ Test 12: vetka_list_files - PASSED")
    return True


def test_read_file_tool():
    """Test 13: vetka_read_file works"""
    from src.mcp.tools import ReadFileTool

    tool = ReadFileTool()
    result = tool.safe_execute({"path": "main.py", "max_lines": 50})

    assert result["success"], f"Failed: {result.get('error')}"
    assert "content" in result["result"]
    assert len(result["result"]["content"]) > 0
    print("✅ Test 13: vetka_read_file - PASSED")
    return True


def test_edit_file_dry_run():
    """Test 14: vetka_edit_file dry_run works"""
    from src.mcp.tools import EditFileTool

    tool = EditFileTool()
    result = tool.safe_execute({
        "path": "test_temp_file.txt",
        "content": "test content",
        "dry_run": True
    })

    assert result["success"]
    assert result["result"]["status"] == "dry_run"
    print("✅ Test 14: vetka_edit_file dry_run - PASSED")
    return True


def test_git_status():
    """Test 15: vetka_git_status works"""
    from src.mcp.tools import GitStatusTool

    tool = GitStatusTool()
    result = tool.safe_execute({})

    assert result["success"], f"Failed: {result.get('error')}"
    assert "branch" in result["result"]
    assert "files" in result["result"]
    print("✅ Test 15: vetka_git_status - PASSED")
    return True


def test_git_commit_dry_run():
    """Test 16: vetka_git_commit dry_run works"""
    from src.mcp.tools import GitCommitTool

    tool = GitCommitTool()
    result = tool.safe_execute({
        "message": "Test commit message",
        "dry_run": True
    })

    assert result["success"]
    assert result["result"]["status"] == "dry_run"
    print("✅ Test 16: vetka_git_commit dry_run - PASSED")
    return True


def test_path_traversal_blocked():
    """Test 17: Path traversal is blocked"""
    from src.mcp.tools import ReadFileTool, ListFilesTool, EditFileTool

    # Test ReadFileTool
    tool1 = ReadFileTool()
    error = tool1.validate_arguments({"path": "../etc/passwd"})
    assert error is not None and "traversal" in error.lower()

    # Test ListFilesTool
    tool2 = ListFilesTool()
    error = tool2.validate_arguments({"path": "../../.."})
    assert error is not None and "traversal" in error.lower()

    # Test EditFileTool
    tool3 = EditFileTool()
    error = tool3.validate_arguments({"path": "../secret.txt", "content": "hack"})
    assert error is not None and "traversal" in error.lower()

    print("✅ Test 17: Path traversal blocked - PASSED")
    return True


def test_search_knowledge_tool():
    """Test 18: vetka_search_knowledge schema valid"""
    from src.mcp.tools import SearchKnowledgeTool

    tool = SearchKnowledgeTool()
    assert tool.name == "vetka_search_knowledge"

    schema = tool.schema
    assert schema["type"] == "object"
    assert "query" in schema["properties"]
    assert "query" in schema.get("required", [])

    # Validate arguments
    error = tool.validate_arguments({})
    assert error is not None  # Missing query

    error = tool.validate_arguments({"query": "test"})
    assert error is None  # Valid

    print("✅ Test 18: vetka_search_knowledge schema - PASSED")
    return True


def test_run_tests_tool_schema():
    """Test 19: vetka_run_tests schema valid"""
    from src.mcp.tools import RunTestsTool

    tool = RunTestsTool()
    assert tool.name == "vetka_run_tests"

    schema = tool.schema
    assert schema["type"] == "object"
    assert "test_path" in schema["properties"]
    assert "timeout" in schema["properties"]

    # Validate path traversal
    error = tool.validate_arguments({"test_path": "../../../etc"})
    assert error is not None

    # Validate timeout
    error = tool.validate_arguments({"timeout": 500})
    assert error is not None  # > 300

    error = tool.validate_arguments({"test_path": "tests/", "timeout": 60})
    assert error is None

    print("✅ Test 19: vetka_run_tests schema - PASSED")
    return True


def test_openai_schema_format():
    """Test 20: All tools produce valid OpenAI schema"""
    from src.mcp import tools

    all_tools = [
        tools.SearchTool(),
        tools.SearchKnowledgeTool(),
        tools.GetTreeTool(),
        tools.GetNodeTool(),
        tools.ListFilesTool(),
        tools.ReadFileTool(),
        tools.EditFileTool(),
        tools.RunTestsTool(),
        tools.GitStatusTool(),
        tools.GitCommitTool(),
        tools.CreateBranchTool(),
    ]

    for tool in all_tools:
        schema = tool.to_openai_schema()
        assert schema["type"] == "function", f"{tool.name}: missing type=function"
        assert "function" in schema, f"{tool.name}: missing function key"
        assert "name" in schema["function"], f"{tool.name}: missing name"
        assert "description" in schema["function"], f"{tool.name}: missing description"
        assert "parameters" in schema["function"], f"{tool.name}: missing parameters"

    print("✅ Test 20: All 11 tools have valid OpenAI schema - PASSED")
    return True


def run_all_tests():
    """Run all MCP server tests"""
    print("\n" + "=" * 60)
    print("🧪 VETKA MCP SERVER TEST SUITE (Phase 22-MCP-5)")
    print("=" * 60 + "\n")

    tests = [
        # Original tests (1-10)
        test_mcp_server_initialization,
        test_list_tools_openai_format,
        test_search_tool_schema,
        test_tree_tool_schema,
        test_node_tool_schema,
        test_branch_tool_schema,
        test_tool_call_unknown_tool,
        test_tool_validation,
        test_agent_session_tracking,
        test_json_rpc_response_format,
        # New tests (11-20)
        test_all_11_tools_registered,
        test_list_files_tool,
        test_read_file_tool,
        test_edit_file_dry_run,
        test_git_status,
        test_git_commit_dry_run,
        test_path_traversal_blocked,
        test_search_knowledge_tool,
        test_run_tests_tool_schema,
        test_openai_schema_format,
        # Phase 22-MCP-3 tests (21-26)
        test_rate_limiter,
        test_audit_logger,
        test_approval_manager,
        test_approval_needs_check,
        test_rate_limiter_reset,
        test_audit_sanitize,
        # Phase 22-MCP-4 tests (27-32)
        test_claude_config_generator,
        test_claude_config_sse,
        test_installation_instructions,
        test_memory_transfer_export,
        test_memory_transfer_import_validation,
        test_memory_transfer_list_exports,
        # Phase 22-MCP-5 tests (33-38)
        test_youtube_intake_patterns,
        test_web_intake_patterns,
        test_intake_manager_processor_selection,
        test_intake_result_format,
        test_intake_tools_schema,
        test_intake_manager_list,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            failed += 1
            print(f"❌ {test.__name__}: FAILED - {e}")

    print("\n" + "=" * 60)
    print(f"📊 RESULTS: {passed} passed, {failed} failed")
    print("=" * 60 + "\n")

    return failed == 0


# ============================================================
# PHASE 22-MCP-3 TESTS
# ============================================================

def test_rate_limiter():
    """Test 21: Rate limiting works"""
    from src.mcp.rate_limiter import RateLimiter

    limiter = RateLimiter(max_calls=3, window_seconds=60)

    # First 3 calls allowed
    assert limiter.is_allowed("test-client")[0] == True
    assert limiter.is_allowed("test-client")[0] == True
    assert limiter.is_allowed("test-client")[0] == True

    # 4th call blocked
    allowed, retry = limiter.is_allowed("test-client")
    assert allowed == False
    assert retry > 0

    # Check usage stats
    usage = limiter.get_usage("test-client")
    assert usage["calls_made"] == 3
    assert usage["calls_remaining"] == 0

    print("✅ Test 21: Rate limiter works - PASSED")
    return True


def test_audit_logger():
    """Test 22: Audit logging works"""
    import tempfile
    from src.mcp.audit_logger import MCPAuditLogger

    with tempfile.TemporaryDirectory() as tmpdir:
        logger = MCPAuditLogger(log_dir=tmpdir)
        logger.log_call(
            "vetka_search",
            {"query": "test"},
            "test-client",
            True,
            {"count": 5},
            duration_ms=50.5
        )

        entries = logger.get_recent_calls()
        assert len(entries) == 1
        assert entries[0]["tool"] == "vetka_search"
        assert entries[0]["success"] == True
        assert entries[0]["client_id"] == "test-client"

    print("✅ Test 22: Audit logger works - PASSED")
    return True


def test_approval_manager():
    """Test 23: Approval flow works"""
    from src.mcp.approval import ApprovalManager

    manager = ApprovalManager(expiry_minutes=5)

    # Create request
    req = manager.create_request("vetka_edit_file", {"path": "test.txt"}, "test-client")
    assert req["status"] == "pending"
    assert "id" in req

    # Get pending
    pending = manager.get_pending()
    assert len(pending) >= 1

    # Approve
    result = manager.approve(req["id"])
    assert result["status"] == "approved"

    print("✅ Test 23: Approval manager works - PASSED")
    return True


def test_approval_needs_check():
    """Test 24: Approval needs_approval logic"""
    from src.mcp.approval import ApprovalManager

    manager = ApprovalManager()

    # Dangerous tools with dry_run=false need approval
    assert manager.needs_approval("vetka_edit_file", dry_run=False) == True
    assert manager.needs_approval("vetka_git_commit", dry_run=False) == True

    # Dry run never needs approval
    assert manager.needs_approval("vetka_edit_file", dry_run=True) == False
    assert manager.needs_approval("vetka_git_commit", dry_run=True) == False

    # Read-only tools never need approval
    assert manager.needs_approval("vetka_search", dry_run=False) == False
    assert manager.needs_approval("vetka_list_files", dry_run=False) == False

    print("✅ Test 24: Approval needs_approval logic - PASSED")
    return True


def test_rate_limiter_reset():
    """Test 25: Rate limiter reset works"""
    from src.mcp.rate_limiter import RateLimiter

    limiter = RateLimiter(max_calls=2, window_seconds=60)

    # Use up quota
    limiter.is_allowed("client-x")
    limiter.is_allowed("client-x")
    assert limiter.is_allowed("client-x")[0] == False

    # Reset
    limiter.reset("client-x")
    assert limiter.is_allowed("client-x")[0] == True

    print("✅ Test 25: Rate limiter reset works - PASSED")
    return True


def test_audit_sanitize():
    """Test 26: Audit logger sanitizes sensitive data"""
    from src.mcp.audit_logger import MCPAuditLogger

    logger = MCPAuditLogger()

    # Test sanitization
    args = {
        "path": "test.txt",
        "content": "secret data here",
        "password": "hunter2",
        "long_text": "x" * 1000
    }

    sanitized = logger._sanitize_args(args)
    assert sanitized["path"] == "test.txt"
    assert sanitized["content"] == "[REDACTED]"
    assert sanitized["password"] == "[REDACTED]"
    assert "[truncated]" in sanitized["long_text"]

    print("✅ Test 26: Audit sanitizes sensitive data - PASSED")
    return True


# ============== PHASE 22-MCP-4 TESTS ==============

def test_claude_config_generator():
    """Test 27: Claude Desktop config generator"""
    from src.mcp.claude_desktop import generate_claude_config

    # Generate config with stdio transport
    config = generate_claude_config(server_name="vetka-test")

    assert "mcpServers" in config
    assert "vetka-test" in config["mcpServers"]

    server_config = config["mcpServers"]["vetka-test"]
    assert "command" in server_config
    assert "args" in server_config
    assert "env" in server_config

    # Verify env has required vars
    assert "VETKA_PROJECT_PATH" in server_config["env"]
    assert "PYTHONPATH" in server_config["env"]

    print("✅ Test 27: Claude Desktop config generator - PASSED")
    return True


def test_claude_config_sse():
    """Test 28: Claude config with SSE transport"""
    from src.mcp.claude_desktop import generate_claude_config

    config = generate_claude_config(use_sse=True, sse_url="http://localhost:5005")

    server_config = config["mcpServers"]["vetka-mcp"]
    assert server_config.get("transport") == "sse"
    assert "url" in server_config
    assert "5005" in server_config["url"]

    print("✅ Test 28: Claude config SSE transport - PASSED")
    return True


def test_installation_instructions():
    """Test 29: Installation instructions generation"""
    from src.mcp.claude_desktop import get_installation_instructions

    instructions = get_installation_instructions()

    assert "VETKA MCP" in instructions
    assert "Claude Desktop" in instructions
    assert "mcpServers" in instructions
    assert "vetka_search" in instructions
    assert "vetka_edit_file" in instructions

    print("✅ Test 29: Installation instructions - PASSED")
    return True


def test_memory_transfer_export():
    """Test 30: Memory export to .vetka-mem"""
    import tempfile
    import os
    from src.mcp.memory_transfer import MemoryTransfer

    # Create transfer with temp directory
    with tempfile.TemporaryDirectory() as tmpdir:
        transfer = MemoryTransfer(project_path=tmpdir)

        # Create data directories
        os.makedirs(os.path.join(tmpdir, "data", "chat_history"), exist_ok=True)
        os.makedirs(os.path.join(tmpdir, "data"), exist_ok=True)

        # Export
        result = transfer.export_memory(filename="test_export.vetka-mem")

        assert result["success"] == True
        assert "path" in result
        assert os.path.exists(result["path"])
        assert result["path"].endswith(".vetka-mem")

    print("✅ Test 30: Memory export - PASSED")
    return True


def test_memory_transfer_import_validation():
    """Test 31: Memory import validation"""
    import tempfile
    import json
    import os
    from src.mcp.memory_transfer import MemoryTransfer

    with tempfile.TemporaryDirectory() as tmpdir:
        transfer = MemoryTransfer(project_path=tmpdir)

        # Test import of non-existent file
        result = transfer.import_memory("/nonexistent/file.vetka-mem")
        assert result["success"] == False
        assert "not found" in result["error"].lower()

        # Test import of invalid format
        invalid_file = os.path.join(tmpdir, "invalid.vetka-mem")
        with open(invalid_file, "w") as f:
            json.dump({"wrong": "format"}, f)

        result = transfer.import_memory(invalid_file)
        assert result["success"] == False
        assert "header" in result["error"].lower()

    print("✅ Test 31: Memory import validation - PASSED")
    return True


def test_memory_transfer_list_exports():
    """Test 32: List memory exports"""
    import tempfile
    import os
    from src.mcp.memory_transfer import MemoryTransfer

    with tempfile.TemporaryDirectory() as tmpdir:
        transfer = MemoryTransfer(project_path=tmpdir)

        # Export a file
        os.makedirs(os.path.join(tmpdir, "data"), exist_ok=True)
        transfer.export_memory(filename="list_test.vetka-mem")

        # List exports
        exports = transfer.list_exports()
        assert len(exports) >= 1
        assert any("list_test" in e["filename"] for e in exports)

        # Check export has expected fields
        export = exports[0]
        assert "filename" in export
        assert "path" in export
        assert "size_bytes" in export
        assert "created_at" in export

    print("✅ Test 32: List memory exports - PASSED")
    return True


# ============== PHASE 22-MCP-5 TESTS ==============

def test_youtube_intake_patterns():
    """Test 33: YouTube intake pattern matching"""
    from src.intake.youtube import YouTubeIntake

    intake = YouTubeIntake()

    # Test pattern matching
    assert intake.can_process("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
    assert intake.can_process("https://youtu.be/dQw4w9WgXcQ")
    assert intake.can_process("https://youtube.com/shorts/abc123")
    assert not intake.can_process("https://example.com/video")
    assert not intake.can_process("https://vimeo.com/12345")

    print("✅ Test 33: YouTube intake pattern matching - PASSED")
    return True


def test_web_intake_patterns():
    """Test 34: Web page intake pattern matching"""
    from src.intake.web import WebIntake

    intake = WebIntake()

    # Test pattern matching
    assert intake.can_process("https://example.com/article")
    assert intake.can_process("https://news.ycombinator.com/")
    assert not intake.can_process("https://youtube.com/watch?v=123")
    assert not intake.can_process("https://youtu.be/abc")
    assert not intake.can_process("https://t.me/channel")

    print("✅ Test 34: Web intake pattern matching - PASSED")
    return True


def test_intake_manager_processor_selection():
    """Test 35: Intake manager processor selection"""
    import tempfile
    from src.intake.manager import IntakeManager

    with tempfile.TemporaryDirectory() as tmpdir:
        manager = IntakeManager(project_root=tmpdir)

        # Test processor selection
        processor = manager.get_processor("https://youtube.com/watch?v=abc")
        assert processor is not None
        assert processor.source_type == "youtube"

        processor = manager.get_processor("https://example.com/article")
        assert processor is not None
        assert processor.source_type == "web"

    print("✅ Test 35: Intake manager processor selection - PASSED")
    return True


def test_intake_result_format():
    """Test 36: IntakeResult dataclass format"""
    from src.intake.base import IntakeResult, ContentType

    result = IntakeResult(
        source_url="https://example.com",
        source_type="web",
        content_type=ContentType.ARTICLE,
        title="Test Article",
        text="This is test content"
    )

    data = result.to_dict()
    assert data["source_url"] == "https://example.com"
    assert data["source_type"] == "web"
    assert data["content_type"] == "article"
    assert data["title"] == "Test Article"
    assert data["text_length"] == len("This is test content")
    assert "processed_at" in data

    print("✅ Test 36: IntakeResult format - PASSED")
    return True


def test_intake_tools_schema():
    """Test 37: Intake MCP tools have valid schemas"""
    from src.intake.tools import IntakeURLTool, ListIntakesTool, GetIntakeTool

    # IntakeURLTool
    tool = IntakeURLTool()
    assert tool.name == "vetka_intake_url"
    schema = tool.to_openai_schema()
    assert schema["type"] == "function"
    assert "url" in schema["function"]["parameters"]["properties"]

    # ListIntakesTool
    tool = ListIntakesTool()
    assert tool.name == "vetka_list_intakes"
    schema = tool.to_openai_schema()
    assert "source_type" in schema["function"]["parameters"]["properties"]

    # GetIntakeTool
    tool = GetIntakeTool()
    assert tool.name == "vetka_get_intake"
    schema = tool.to_openai_schema()
    assert "filename" in schema["function"]["parameters"]["properties"]

    print("✅ Test 37: Intake tools schema - PASSED")
    return True


def test_intake_manager_list():
    """Test 38: Intake manager list function"""
    import tempfile
    import json
    import os
    from src.intake.manager import IntakeManager

    with tempfile.TemporaryDirectory() as tmpdir:
        manager = IntakeManager(project_root=tmpdir)

        # Create test intake file
        test_intake = {
            "source_url": "https://example.com",
            "source_type": "web",
            "content_type": "article",
            "title": "Test",
            "text": "content",
            "text_length": 7,
            "processed_at": "2024-01-01T00:00:00"
        }

        intake_file = manager.intake_dir / "web_test123_20240101.json"
        with open(intake_file, "w") as f:
            json.dump(test_intake, f)

        # List intakes
        intakes = manager.list_intakes()
        assert len(intakes) >= 1
        assert intakes[0]["source_type"] == "web"

        # Get intake
        intake = manager.get_intake("web_test123_20240101.json")
        assert intake is not None
        assert intake["title"] == "Test"

        # Delete intake
        assert manager.delete_intake("web_test123_20240101.json") == True
        assert manager.get_intake("web_test123_20240101.json") is None

    print("✅ Test 38: Intake manager list/get/delete - PASSED")
    return True


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
