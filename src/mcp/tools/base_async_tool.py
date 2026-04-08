"""
Base class for MYCELIUM async MCP tools.

MYCELIUM tools inherit from BaseAsyncMCPTool (async execute).
VETKA tools stay on sync BaseMCPTool. Clean boundary, no cross-contamination.

MARKER_129.1: Phase 129 — MYCELIUM async tool foundation

@status: active
@phase: 129
@depends: abc, typing
@used_by: llm_call_tool_async.py, mycelium_mcp_server.py
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


# MARKER_129.1_START: BaseAsyncMCPTool — async foundation for MYCELIUM tools
class BaseAsyncMCPTool(ABC):
    """Abstract base class for MYCELIUM async MCP tools.

    All MYCELIUM tools inherit from this class and implement:
    - name property
    - description property
    - schema property
    - async execute() method (native async, no ThreadPoolExecutor)

    This is the async counterpart to BaseMCPTool (which stays sync for VETKA).
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Tool name (e.g., 'mycelium_call_model')"""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Tool description for agents"""
        pass

    @property
    @abstractmethod
    def schema(self) -> Dict[str, Any]:
        """OpenAI-compatible tool schema with 'type': 'object' and 'properties'"""
        pass

    @abstractmethod
    async def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the tool with given arguments (async).

        Args:
            arguments: Dict matching the schema parameters

        Returns:
            {'success': bool, 'result': Any, 'error': Optional[str]}
        """
        pass

    def to_openai_schema(self) -> Dict[str, Any]:
        """Convert to OpenAI function calling format"""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.schema
            }
        }

    def validate_arguments(self, arguments: Dict[str, Any]) -> Optional[str]:
        """Validate arguments against schema.

        Returns:
            Error message if invalid, None if valid
        """
        schema = self.schema
        properties = schema.get('properties', {})
        required = schema.get('required', [])

        # Check required arguments
        for req_field in required:
            if req_field not in arguments:
                return f"Missing required argument: {req_field}"

        # Check argument types (basic validation)
        for arg_name, arg_value in arguments.items():
            if arg_name not in properties:
                continue  # Allow extra args (lenient for forward compat)

            prop_schema = properties[arg_name]
            expected_type = prop_schema.get('type', 'string')

            if expected_type == 'string' and not isinstance(arg_value, str):
                return f"Expected {arg_name} to be string, got {type(arg_value).__name__}"
            elif expected_type == 'integer' and not isinstance(arg_value, int):
                return f"Expected {arg_name} to be integer, got {type(arg_value).__name__}"
            elif expected_type == 'number' and not isinstance(arg_value, (int, float)):
                return f"Expected {arg_name} to be number, got {type(arg_value).__name__}"
            elif expected_type == 'boolean' and not isinstance(arg_value, bool):
                return f"Expected {arg_name} to be boolean, got {type(arg_value).__name__}"

        return None  # Valid

    async def safe_execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute with validation and error handling (async).

        Returns:
            {'success': bool, 'result': Any, 'error': Optional[str]}
        """
        # Validate
        validation_error = self.validate_arguments(arguments)
        if validation_error:
            return {
                'success': False,
                'error': validation_error,
                'result': None
            }

        # Execute
        try:
            result = await self.execute(arguments)
            if isinstance(result, dict) and 'success' in result:
                return result
            else:
                return {'success': True, 'result': result, 'error': None}
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'result': None
            }
# MARKER_129.1_END
