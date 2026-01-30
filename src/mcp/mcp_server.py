"""
MCP (Model Context Protocol) Server for VETKA.

Handles WebSocket connections from AI agents and routes tool calls using JSON-RPC 2.0.

Features:
- Rate limiting (60/min API, 10/min writes)
- Audit logging (all calls logged to data/mcp_audit/)
- Approval flow (dangerous operations require human approval)

Format:
{
  "jsonrpc": "2.0",
  "id": "request-id",
  "method": "tool_call",
  "params": {
    "name": "tool_name",
    "arguments": {tool_arguments}
  }
}

@status: active
@phase: 96
@depends: rate_limiter, audit_logger, approval, tools
@used_by: main.py, socket handlers

MARKER: CLEANUP41_FLASK_REMOVED - Removed Flask imports
Now using python-socketio direct emit via self.socketio
"""
import json
import uuid
import time
from typing import Dict, Any, Optional
import threading

# Security imports
from .rate_limiter import api_limiter, write_limiter
from .audit_logger import audit_logger
from .approval import approval_manager


class MCPServer:
    """Main MCP (Model Context Protocol) Server
    
    Handles:
    - Agent connections
    - Tool registration
    - JSON-RPC 2.0 request/response
    - Error handling
    """
    
    def __init__(self, socketio):
        self.socketio = socketio
        self.tools = {}
        self.agent_sessions = {}  # agent_id -> {tools, metadata}
        self._lock = threading.Lock()
        
    def register_tool(self, tool):
        """Register an MCP tool
        
        Args:
            tool: Instance of BaseMCPTool
        """
        self.tools[tool.name] = tool
        print(f"[MCP] Registered tool: {tool.name}")
    
    def list_tools(self) -> list:
        """Return list of available tools in OpenAI-compatible format"""
        return [tool.to_openai_schema() for tool in self.tools.values()]
    
    def handle_connect(self, agent_id: str):
        """Handle agent connection"""
        with self._lock:
            self.agent_sessions[agent_id] = {
                'connected_at': __import__('time').time(),
                'tools': list(self.tools.keys()),
                'requests': 0
            }
        
        print(f"[MCP] Agent connected: {agent_id} ({len(self.agent_sessions)} total)")

        # Emit list of available tools
        # MARKER: CLEANUP41_FLASK_REMOVED - Changed from Flask-SocketIO emit() to self.socketio.emit()
        if self.socketio is not None:
            try:
                self.socketio.emit('tools_list', {
                    'tools': self.list_tools(),
                    'count': len(self.tools)
                }, to=agent_id)
            except Exception as e:
                print(f"[MCP] Emit error: {e}")
    
    def handle_disconnect(self, agent_id: str):
        """Handle agent disconnection"""
        with self._lock:
            session = self.agent_sessions.pop(agent_id, None)
        
        if session:
            print(f"[MCP] Agent disconnected: {agent_id} ({session.get('requests', 0)} requests)")
    
    def handle_tool_call(self, agent_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle tool call from agent with security checks

        Expects data format:
        {
            "id": "request-id",
            "name": "tool_name",
            "arguments": {...}
        }

        Returns:
        {
            "jsonrpc": "2.0",
            "id": "request-id",
            "result": {...} or "error": {...}
        }
        """
        start_time = time.time()
        request_id = data.get('id', str(uuid.uuid4()))
        tool_name = data.get('name', '')
        arguments = data.get('arguments', {}).copy()

        # Track request
        with self._lock:
            if agent_id in self.agent_sessions:
                self.agent_sessions[agent_id]['requests'] += 1

        # Validate tool exists
        if tool_name not in self.tools:
            audit_logger.log_call(tool_name, arguments, agent_id, False, error="tool_not_found")
            return {
                'jsonrpc': '2.0',
                'id': request_id,
                'error': {
                    'code': -32601,
                    'message': 'Method not found',
                    'data': f'Unknown tool: {tool_name}'
                }
            }

        # 1. Rate limiting
        is_write = tool_name in ("vetka_edit_file", "vetka_git_commit", "vetka_create_branch", "vetka_run_tests")
        limiter = write_limiter if is_write else api_limiter

        allowed, retry_after = limiter.is_allowed(agent_id)
        if not allowed:
            audit_logger.log_call(tool_name, arguments, agent_id, False, error="rate_limited")
            return {
                'jsonrpc': '2.0',
                'id': request_id,
                'error': {
                    'code': -32000,
                    'message': f'Rate limited. Retry after {retry_after} seconds',
                    'data': {'retry_after': retry_after}
                }
            }

        # 2. Approval check (only for non-dry-run writes)
        dry_run = arguments.get("dry_run", True)
        if approval_manager.needs_approval(tool_name, dry_run):
            # Check if we have an approval_id
            approval_id = arguments.pop("_approval_id", None)
            if approval_id:
                approval = approval_manager.get_request(approval_id)
                if not approval or approval["status"] != "approved":
                    audit_logger.log_call(tool_name, arguments, agent_id, False, error="invalid_approval")
                    return {
                        'jsonrpc': '2.0',
                        'id': request_id,
                        'error': {
                            'code': -32001,
                            'message': f'Invalid or expired approval: {approval_id}'
                        }
                    }
            else:
                # Create approval request
                req = approval_manager.create_request(tool_name, arguments, agent_id)
                audit_logger.log_call(tool_name, arguments, agent_id, False, error="approval_required")
                return {
                    'jsonrpc': '2.0',
                    'id': request_id,
                    'result': {
                        'needs_approval': True,
                        'approval_id': req['id'],
                        'expires_at': req['expires_at'],
                        'message': f"This operation requires approval. Use _approval_id='{req['id']}' after approval."
                    }
                }

        # 3. Execute tool
        try:
            tool = self.tools[tool_name]
            result = tool.safe_execute(arguments)
            duration_ms = (time.time() - start_time) * 1000

            # Audit log
            audit_logger.log_call(
                tool_name, arguments, agent_id,
                result.get("success", False),
                result.get("result"),
                result.get("error"),
                duration_ms
            )

            print(f"[MCP] Tool executed: {tool_name} (request: {request_id}, success: {result.get('success')}, {duration_ms:.1f}ms)")

            if result.get('success'):
                return {
                    'jsonrpc': '2.0',
                    'id': request_id,
                    'result': result.get('result')
                }
            else:
                return {
                    'jsonrpc': '2.0',
                    'id': request_id,
                    'error': {
                        'code': -32603,
                        'message': 'Internal error',
                        'data': result.get('error')
                    }
                }

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            audit_logger.log_call(tool_name, arguments, agent_id, False, error=str(e), duration_ms=duration_ms)
            return {
                'jsonrpc': '2.0',
                'id': request_id,
                'error': {
                    'code': -32603,
                    'message': 'Internal error',
                    'data': str(e)
                }
            }
    
    def emit_response(self, agent_id: str, response: Dict[str, Any]):
        """Emit JSON-RPC response to agent"""
        # MARKER: CLEANUP41_FLASK_REMOVED - Added None check
        if self.socketio is not None:
            try:
                self.socketio.emit('tool_result', response, to=agent_id)
            except Exception as e:
                print(f"[MCP] Emit response error: {e}")


# Global MCP server instance
_mcp_server = None


def get_mcp_server(socketio=None):
    """Get or create global MCP server instance"""
    global _mcp_server

    if _mcp_server is None and socketio is not None:
        _mcp_server = MCPServer(socketio)

        # Register ALL 15 tools
        from .tools import (
            SearchTool, GetTreeTool, GetNodeTool, CreateBranchTool,
            ListFilesTool, ReadFileTool, EditFileTool,
            RunTestsTool, GitStatusTool, GitCommitTool, SearchKnowledgeTool,
            CameraControlTool
        )

        # Read-only tools (safe)
        _mcp_server.register_tool(SearchTool())
        _mcp_server.register_tool(SearchKnowledgeTool())
        _mcp_server.register_tool(GetTreeTool())
        _mcp_server.register_tool(GetNodeTool())
        _mcp_server.register_tool(ListFilesTool())
        _mcp_server.register_tool(ReadFileTool())
        _mcp_server.register_tool(GitStatusTool())
        _mcp_server.register_tool(CameraControlTool())

        # Write tools (require approval, dry_run default)
        _mcp_server.register_tool(CreateBranchTool())
        _mcp_server.register_tool(EditFileTool())
        _mcp_server.register_tool(GitCommitTool())
        _mcp_server.register_tool(RunTestsTool())

        # Intake tools (Phase 22-MCP-5)
        try:
            from src.intake.tools import IntakeURLTool, ListIntakesTool, GetIntakeTool
            _mcp_server.register_tool(IntakeURLTool())
            _mcp_server.register_tool(ListIntakesTool())
            _mcp_server.register_tool(GetIntakeTool())
            print("[MCP] Intake tools registered: vetka_intake_url, vetka_list_intakes, vetka_get_intake")
        except ImportError as e:
            print(f"[MCP] Intake tools not available: {e}")

        # ARC Gap tools (Phase 99.3)
        try:
            from .tools.arc_gap_tool import ARCGapTool, ARCConceptsTool
            _mcp_server.register_tool(ARCGapTool())
            _mcp_server.register_tool(ARCConceptsTool())
            print("[MCP] ARC tools registered: vetka_arc_gap, vetka_arc_concepts")
        except ImportError as e:
            print(f"[MCP] ARC tools not available: {e}")

        print(f"[MCP] Server initialized with {len(_mcp_server.tools)} tools")

    return _mcp_server
