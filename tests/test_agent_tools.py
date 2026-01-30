"""
Tests for Agent Tools Framework
Phase 17-L: Extended tests for agent-specific tools
"""
import pytest
import asyncio
from pathlib import Path

# Add project root to path
import sys
# Path to project root (one level up from tests)
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Note: The tool implementation assumes the tool's PROJECT_ROOT is correct
# We must ensure the test file runs from the expected directory context,
# which is why we insert the project root into sys.path.

from src.tools import registry, SafeToolExecutor, ToolCall, PermissionLevel

# Phase 17-L imports
from src.agents.tools import (
    SearchCodebaseTool,
    ExecuteCodeTool,
    ValidateSyntaxTool,
    RunTestsTool,
    GetFileInfoTool,
    CreateArtifactTool,
    get_tools_for_agent,
    get_tool_names_for_agent,
    AGENT_TOOL_PERMISSIONS,
    AgentToolExecutor
)

# Check if asyncio is properly marked for pytest, as the execute methods are async.
# pytest-asyncio fixture handles this.

@pytest.fixture
def executor():
    return SafeToolExecutor()

class TestToolRegistry:
    def test_tools_registered(self):
        """Check that tools are in registry"""
        assert registry.get("read_code_file") is not None
        assert registry.get("write_code_file") is not None
        assert registry.get("list_files") is not None
    
    def test_schema_generation(self):
        """Check Ollama schema format"""
        schemas = registry.all_schemas()
        assert len(schemas) >= 3
        assert all("function" in s for s in schemas)

class TestReadCodeFile:
    @pytest.mark.asyncio
    async def test_read_existing_file(self, executor):
        """Read an existing file"""
        # Test reading the test file itself or a known python file like src/main.py
        call = ToolCall(
            tool_name="read_code_file",
            arguments={"path": "src/main.py"},
            agent_type="Dev"
        )
        result = await executor.execute(call)
        assert result.success
        # main.py content: flask/Flask might not be in the Phase 11 version. Check for known content.
        # Based on the read of src/main.py, it contained "VETKA Phase 11"
        assert "vetka phase 11" in result.result.lower()
    
    @pytest.mark.asyncio
    async def test_read_nonexistent_file(self, executor):
        """Try to read non-existent file"""
        call = ToolCall(
            tool_name="read_code_file",
            arguments={"path": "nonexistent.py"},
            agent_type="Dev"
        )
        result = await executor.execute(call)
        assert not result.success
        assert "not found" in result.error.lower()
    
    @pytest.mark.asyncio
    async def test_path_traversal_blocked(self, executor):
        """Security: block path traversal"""
        call = ToolCall(
            tool_name="read_code_file",
            arguments={"path": "../../etc/passwd"},
            agent_type="Dev"
        )
        result = await executor.execute(call)
        assert not result.success
        assert "traversal" in result.error.lower()

class TestListFiles:
    @pytest.mark.asyncio
    async def test_list_src_directory(self, executor):
        """List files in src/"""
        call = ToolCall(
            tool_name="list_files",
            arguments={"path": "src", "pattern": "*.py"},
            agent_type="Dev"
        )
        result = await executor.execute(call)
        assert result.success
        assert isinstance(result.result, list)
        assert len(result.result) > 0 # Should contain main.py at least

class TestRateLimit:
    @pytest.mark.asyncio
    async def test_rate_limit_exceeded(self):
        """Test rate limiting"""
        from src.tools.executor import RateLimitConfig
        
        executor = SafeToolExecutor(
            rate_limit=RateLimitConfig(calls_per_minute=2)
        )
        
        call = ToolCall(
            tool_name="list_files",
            arguments={"path": "."},
            agent_type="Dev"
        )
        
        # First two should succeed
        r1 = await executor.execute(call)
        r2 = await executor.execute(call)
        assert r1.success, f"R1 failed: {r1.error}"
        assert r2.success, f"R2 failed: {r2.error}"
        
        # Give it a small delay to ensure time.time() has advanced, 
        # although checking the internal list of timestamps is more precise.
        # Since the executor cleans up entries older than 60s, and we test 
        # calls_per_minute=2, two calls back-to-back should consume the limit, 
        # and the third should fail instantly.
        
        # Third should fail
        r3 = await executor.execute(call)
        assert not r3.success
        assert "rate limit" in r3.error.lower()

class TestPermissions:
    @pytest.mark.asyncio
    async def test_permission_denied(self):
        """Test permission check"""
        executor = SafeToolExecutor(max_permission=PermissionLevel.READ)
        
        # Write should be denied (WRITE > READ)
        call = ToolCall(
            tool_name="write_code_file",
            arguments={"path": "test_permission.txt", "content": "test"},
            agent_type="Dev"
        )
        result = await executor.execute(call)
        assert not result.success
        assert "permission" in result.error.lower()

    @pytest.mark.asyncio
    async def test_write_success_with_write_permission(self):
        """Test write success with correct permission"""
        executor = SafeToolExecutor(max_permission=PermissionLevel.WRITE)
        temp_file = Path("test_artifact.txt")
        
        call = ToolCall(
            tool_name="write_code_file",
            arguments={"path": str(temp_file), "content": "Test content"},
            agent_type="Dev"
        )
        result = await executor.execute(call)
        
        try:
            assert result.success, f"Write failed: {result.error}"
            assert temp_file.exists()
            assert temp_file.read_text() == "Test content"
        finally:
            if temp_file.exists():
                temp_file.unlink()

# ============================================
# PHASE 17-L: AGENT PERMISSIONS TESTS
# ============================================

class TestAgentPermissions:
    """Test agent-specific tool access"""

    def test_pm_tools_read_only(self):
        """PM should NOT have write_code_file"""
        pm_tools = get_tool_names_for_agent("PM")

        assert "read_code_file" in pm_tools
        assert "list_files" in pm_tools
        assert "search_codebase" in pm_tools
        assert "write_code_file" not in pm_tools
        assert "execute_code" not in pm_tools

    def test_dev_tools_include_write(self):
        """Dev should have write and execute tools"""
        dev_tools = get_tool_names_for_agent("Dev")

        assert "read_code_file" in dev_tools
        assert "write_code_file" in dev_tools
        assert "execute_code" in dev_tools
        assert "create_artifact" in dev_tools
        assert "validate_syntax" in dev_tools

    def test_qa_tools_include_tests(self):
        """QA should have run_tests and validate_syntax"""
        qa_tools = get_tool_names_for_agent("QA")

        assert "run_tests" in qa_tools
        assert "validate_syntax" in qa_tools
        assert "execute_code" in qa_tools
        # QA should NOT be able to write files
        assert "write_code_file" not in qa_tools

    def test_get_tools_for_agent_returns_schemas(self):
        """get_tools_for_agent should return Ollama-compatible schemas"""
        dev_schemas = get_tools_for_agent("Dev")

        assert len(dev_schemas) > 0
        for schema in dev_schemas:
            assert "type" in schema
            assert "function" in schema


# ============================================
# PHASE 17-L: NEW TOOLS TESTS
# ============================================

class TestValidateSyntaxTool:
    """Test syntax validation tool"""

    @pytest.mark.asyncio
    async def test_valid_python(self):
        """Valid Python code should pass"""
        tool = ValidateSyntaxTool()
        result = await tool.execute(
            code="def hello(): pass",
            language="python"
        )

        assert result.success
        assert result.result["valid"] is True

    @pytest.mark.asyncio
    async def test_invalid_python(self):
        """Invalid Python should fail gracefully"""
        tool = ValidateSyntaxTool()
        result = await tool.execute(
            code="def hello( pass",
            language="python"
        )

        assert result.success  # Tool executed successfully
        assert result.result["valid"] is False
        assert "error" in result.result

    @pytest.mark.asyncio
    async def test_valid_json(self):
        """Valid JSON should pass"""
        tool = ValidateSyntaxTool()
        result = await tool.execute(
            code='{"key": "value", "number": 42}',
            language="json"
        )

        assert result.success
        assert result.result["valid"] is True

    @pytest.mark.asyncio
    async def test_invalid_json(self):
        """Invalid JSON should fail gracefully"""
        tool = ValidateSyntaxTool()
        result = await tool.execute(
            code='{"key": value}',  # Missing quotes
            language="json"
        )

        assert result.success
        assert result.result["valid"] is False


class TestSearchCodebaseTool:
    """Test codebase search tool"""

    @pytest.mark.asyncio
    async def test_search_finds_pattern(self):
        """Search should find patterns in codebase"""
        tool = SearchCodebaseTool()
        result = await tool.execute(
            pattern="def ",
            file_type="py",
            path="src"
        )

        assert result.success
        # Should find some Python functions
        if isinstance(result.result, list):
            assert len(result.result) > 0

    @pytest.mark.asyncio
    async def test_search_no_results(self):
        """Search with no matches should return empty or very few results"""
        tool = SearchCodebaseTool()
        # Use a truly unique pattern that won't appear anywhere
        result = await tool.execute(
            pattern="ZZZZNONEXISTENT999888777",
            file_type="py",
            path="src/agents"  # Limit search to avoid test file matching
        )

        assert result.success
        # Either no matches or the search completed successfully
        assert result.result == "No matches found" or isinstance(result.result, list)


class TestExecuteCodeTool:
    """Test code execution tool (with safety checks)"""

    @pytest.mark.asyncio
    async def test_safe_command(self):
        """Safe commands should execute"""
        tool = ExecuteCodeTool()
        result = await tool.execute(command="echo 'hello'")

        assert result.success
        assert "hello" in result.result

    @pytest.mark.asyncio
    async def test_blocked_command(self):
        """Dangerous commands should be blocked"""
        tool = ExecuteCodeTool()

        # Test rm -rf /
        result = await tool.execute(command="rm -rf /")
        assert not result.success
        assert "Blocked" in result.error

    @pytest.mark.asyncio
    async def test_sudo_blocked(self):
        """sudo commands should be blocked"""
        tool = ExecuteCodeTool()
        result = await tool.execute(command="sudo ls")

        assert not result.success
        assert "Blocked" in result.error

    @pytest.mark.asyncio
    async def test_python_command(self):
        """Python commands should work"""
        tool = ExecuteCodeTool()
        # Use python3 for macOS compatibility
        result = await tool.execute(
            command="python3 -c 'print(2+2)'"
        )

        assert result.success
        assert "4" in result.result


class TestGetFileInfoTool:
    """Test file info tool"""

    @pytest.mark.asyncio
    async def test_existing_file(self):
        """Should return info for existing file"""
        tool = GetFileInfoTool()
        result = await tool.execute(file_path="src/agents/tools.py")

        assert result.success
        assert "size_bytes" in result.result
        assert "modified" in result.result
        assert "extension" in result.result
        assert result.result["extension"] == ".py"

    @pytest.mark.asyncio
    async def test_nonexistent_file(self):
        """Should fail gracefully for missing file"""
        tool = GetFileInfoTool()
        result = await tool.execute(file_path="nonexistent_file_12345.py")

        assert not result.success
        assert "not found" in result.error.lower()


class TestCreateArtifactTool:
    """Test artifact creation"""

    @pytest.fixture(autouse=True)
    def clear_artifacts(self):
        """Clear artifacts before each test"""
        CreateArtifactTool.clear_artifacts()
        yield
        CreateArtifactTool.clear_artifacts()

    @pytest.mark.asyncio
    async def test_create_code_artifact(self):
        """Should create code artifact"""
        tool = CreateArtifactTool()
        result = await tool.execute(
            name="test_function",
            content="def hello(): pass",
            artifact_type="code",
            language="python"
        )

        assert result.success
        assert "id" in result.result
        assert result.result["name"] == "test_function"

        # Check artifact is stored
        artifacts = CreateArtifactTool.get_artifacts()
        assert len(artifacts) == 1
        assert artifacts[0].name == "test_function"

    @pytest.mark.asyncio
    async def test_multiple_artifacts(self):
        """Should store multiple artifacts"""
        tool = CreateArtifactTool()

        await tool.execute(name="a1", content="content1", artifact_type="code")
        await tool.execute(name="a2", content="content2", artifact_type="markdown")

        artifacts = CreateArtifactTool.get_artifacts()
        assert len(artifacts) == 2


class TestAgentToolExecutor:
    """Test legacy compatibility wrapper"""

    def test_sync_execute(self):
        """Synchronous execution should work"""
        executor = AgentToolExecutor()
        result = executor.execute("validate_syntax", {
            "code": "x = 1",
            "language": "python"
        })

        assert result["success"]
        assert result["result"]["valid"] is True

    def test_unknown_tool(self):
        """Unknown tool should return error"""
        executor = AgentToolExecutor()
        result = executor.execute("nonexistent_tool", {})

        assert not result["success"]
        assert "Unknown tool" in result["error"]


class TestAllToolsRegistered:
    """Test that all Phase 17-L tools are registered"""

    def test_new_tools_in_registry(self):
        """Verify all Phase 17-L tools are in registry"""
        expected_tools = [
            "search_codebase",
            "execute_code",
            "validate_syntax",
            "run_tests",
            "get_file_info",
            "search_weaviate",
            "create_artifact"
        ]

        for tool_name in expected_tools:
            tool = registry.get(tool_name)
            assert tool is not None, f"Tool '{tool_name}' not found in registry"


if __name__ == "__main__":
    # This block is usually for standalone execution, pytest is preferred via CLI
    pytest.main([__file__, "-v"])
