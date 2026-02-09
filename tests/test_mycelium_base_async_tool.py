"""
Tests for BaseAsyncMCPTool — async foundation for MYCELIUM tools.

@phase: 129.1
@created: 2026-02-10
"""
import pytest
import asyncio
import inspect
from src.mcp.tools.base_async_tool import BaseAsyncMCPTool


class MockAsyncTool(BaseAsyncMCPTool):
    """Concrete implementation for testing."""

    @property
    def name(self): return "mock_tool"

    @property
    def description(self): return "Mock tool for tests"

    @property
    def schema(self):
        return {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "count": {"type": "integer"},
                "score": {"type": "number"},
                "verbose": {"type": "boolean"},
            },
            "required": ["query"],
        }

    async def execute(self, arguments):
        return {"success": True, "result": f"ok:{arguments.get('query')}", "error": None}


class MockFailingTool(BaseAsyncMCPTool):
    """Tool whose execute raises an exception."""

    @property
    def name(self): return "failing_tool"

    @property
    def description(self): return "Always fails"

    @property
    def schema(self):
        return {"type": "object", "properties": {"x": {"type": "string"}}, "required": []}

    async def execute(self, arguments):
        raise RuntimeError("boom")


class TestAbstractEnforcement:
    """Abstract methods must be implemented."""

    def test_cannot_instantiate_bare(self):
        with pytest.raises(TypeError):
            BaseAsyncMCPTool()

    def test_missing_name_raises(self):
        class Incomplete(BaseAsyncMCPTool):
            @property
            def description(self): return "d"
            @property
            def schema(self): return {}
            async def execute(self, arguments): return {}

        with pytest.raises(TypeError):
            Incomplete()

    def test_missing_execute_raises(self):
        class Incomplete(BaseAsyncMCPTool):
            @property
            def name(self): return "n"
            @property
            def description(self): return "d"
            @property
            def schema(self): return {}

        with pytest.raises(TypeError):
            Incomplete()

    def test_execute_is_coroutine(self):
        tool = MockAsyncTool()
        assert inspect.iscoroutinefunction(tool.execute)


class TestValidateArguments:
    """validate_arguments checks required, unknown, and types."""

    def test_missing_required_field(self):
        tool = MockAsyncTool()
        err = tool.validate_arguments({})
        assert err is not None
        assert "query" in err

    def test_valid_args_returns_none(self):
        tool = MockAsyncTool()
        assert tool.validate_arguments({"query": "hello"}) is None

    def test_valid_all_fields(self):
        tool = MockAsyncTool()
        assert tool.validate_arguments({"query": "hi", "count": 3, "score": 1.5, "verbose": True}) is None

    def test_extra_args_allowed(self):
        tool = MockAsyncTool()
        assert tool.validate_arguments({"query": "hi", "unknown_field": 42}) is None

    def test_wrong_type_string(self):
        tool = MockAsyncTool()
        err = tool.validate_arguments({"query": 123})
        assert err is not None and "string" in err

    def test_wrong_type_integer(self):
        tool = MockAsyncTool()
        err = tool.validate_arguments({"query": "hi", "count": "not_int"})
        assert err is not None and "integer" in err

    def test_wrong_type_number(self):
        tool = MockAsyncTool()
        err = tool.validate_arguments({"query": "hi", "score": "not_num"})
        assert err is not None and "number" in err

    def test_wrong_type_boolean(self):
        tool = MockAsyncTool()
        err = tool.validate_arguments({"query": "hi", "verbose": "yes"})
        assert err is not None and "boolean" in err

    def test_integer_accepted_as_number(self):
        tool = MockAsyncTool()
        assert tool.validate_arguments({"query": "hi", "score": 5}) is None


class TestToOpenaiSchema:
    """to_openai_schema returns correct OpenAI function calling format."""

    def test_format(self):
        tool = MockAsyncTool()
        schema = tool.to_openai_schema()
        assert schema["type"] == "function"
        assert schema["function"]["name"] == "mock_tool"
        assert schema["function"]["description"] == "Mock tool for tests"
        assert "properties" in schema["function"]["parameters"]


class TestSafeExecute:
    """safe_execute wraps validation + async execute."""

    def test_validation_error_returns_failure(self):
        tool = MockAsyncTool()
        result = asyncio.run(tool.safe_execute({}))
        assert result["success"] is False
        assert "query" in result["error"]
        assert result["result"] is None

    def test_successful_execute(self):
        tool = MockAsyncTool()
        result = asyncio.run(tool.safe_execute({"query": "test"}))
        assert result["success"] is True
        assert result["result"] == "ok:test"
        assert result["error"] is None

    def test_exception_caught(self):
        tool = MockFailingTool()
        result = asyncio.run(tool.safe_execute({"x": "anything"}))
        assert result["success"] is False
        assert "boom" in result["error"]

    def test_raw_return_wrapped(self):
        """If execute returns a non-dict or dict without 'success', it gets wrapped."""
        class RawTool(BaseAsyncMCPTool):
            @property
            def name(self): return "raw"
            @property
            def description(self): return "raw"
            @property
            def schema(self): return {"type": "object", "properties": {}, "required": []}
            async def execute(self, arguments): return {"data": 42}

        tool = RawTool()
        result = asyncio.run(tool.safe_execute({}))
        assert result["success"] is True
        assert result["result"] == {"data": 42}
