#!/usr/bin/env python3
"""
VETKA MCP Server with stdio transport for Claude Desktop.

This server communicates via stdin/stdout using JSON-RPC 2.0 protocol.
It's designed to be spawned by Claude Desktop as a subprocess.

Protocol:
- Receives JSON-RPC 2.0 requests on stdin (one per line)
- Sends JSON-RPC 2.0 responses on stdout (one per line)
- Logs to stderr (doesn't interfere with protocol)

Usage:
    python stdio_server.py

Environment:
    VETKA_PROJECT_PATH - Path to VETKA project (required)
    PYTHONPATH - Should include project root

@status: active
@phase: 96
@depends: sys, json, os, pathlib, tools
@used_by: Claude Desktop
"""

import sys
import json
import os
from pathlib import Path
from typing import Dict, Any, Optional

# Ensure project is in path
project_path = os.environ.get('VETKA_PROJECT_PATH')
if project_path:
    sys.path.insert(0, project_path)
else:
    # Fallback to parent directories
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))


def log(message: str):
    """Log to stderr (doesn't interfere with stdio protocol)"""
    print(f"[VETKA-MCP] {message}", file=sys.stderr, flush=True)


class StdioMCPServer:
    """MCP Server using stdio transport"""

    def __init__(self):
        self.tools = {}
        self._register_tools()
        log(f"Initialized with {len(self.tools)} tools")

    def _register_tools(self):
        """Register all VETKA MCP tools"""
        try:
            from src.mcp.tools import (
                SearchTool, GetTreeTool, GetNodeTool, CreateBranchTool,
                ListFilesTool, ReadFileTool, EditFileTool,
                RunTestsTool, GitStatusTool, GitCommitTool, SearchKnowledgeTool
            )

            # Read-only tools
            self.tools['vetka_search'] = SearchTool()
            self.tools['vetka_search_knowledge'] = SearchKnowledgeTool()
            self.tools['vetka_get_tree'] = GetTreeTool()
            self.tools['vetka_get_node'] = GetNodeTool()
            self.tools['vetka_list_files'] = ListFilesTool()
            self.tools['vetka_read_file'] = ReadFileTool()
            self.tools['vetka_git_status'] = GitStatusTool()

            # Write tools (dry_run default)
            self.tools['vetka_create_branch'] = CreateBranchTool()
            self.tools['vetka_edit_file'] = EditFileTool()
            self.tools['vetka_git_commit'] = GitCommitTool()
            self.tools['vetka_run_tests'] = RunTestsTool()

            log(f"Registered tools: {list(self.tools.keys())}")

            # ARC Gap tools (Phase 99.3)
            try:
                from src.mcp.tools.arc_gap_tool import ARCGapTool, ARCConceptsTool
                self.tools['vetka_arc_gap'] = ARCGapTool()
                self.tools['vetka_arc_concepts'] = ARCConceptsTool()
                log("ARC tools registered: vetka_arc_gap, vetka_arc_concepts")
            except ImportError as e:
                log(f"ARC tools not available: {e}")

        except ImportError as e:
            log(f"Warning: Could not import tools: {e}")

    def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle a JSON-RPC 2.0 request"""
        request_id = request.get('id')
        method = request.get('method', '')
        params = request.get('params', {})

        log(f"Request: method={method}, id={request_id}")

        try:
            if method == 'initialize':
                return self._handle_initialize(request_id, params)
            elif method == 'tools/list':
                return self._handle_list_tools(request_id)
            elif method == 'tools/call':
                return self._handle_call_tool(request_id, params)
            elif method == 'ping':
                return self._success_response(request_id, {'pong': True})
            else:
                return self._error_response(
                    request_id, -32601, f"Method not found: {method}"
                )
        except Exception as e:
            log(f"Error handling request: {e}")
            return self._error_response(request_id, -32603, str(e))

    def _handle_initialize(self, request_id: str, params: Dict) -> Dict:
        """Handle initialize request from Claude Desktop"""
        return self._success_response(request_id, {
            'protocolVersion': '2024-11-05',
            'capabilities': {
                'tools': {},
                'prompts': {},
                'resources': {}
            },
            'serverInfo': {
                'name': 'vetka-mcp',
                'version': '1.0.0',
                'description': 'VETKA Knowledge Graph MCP Server'
            }
        })

    def _handle_list_tools(self, request_id: str) -> Dict:
        """Handle tools/list request"""
        tools = []
        for name, tool in self.tools.items():
            schema = tool.to_openai_schema()
            # Convert to MCP format
            tools.append({
                'name': name,
                'description': schema['function']['description'],
                'inputSchema': schema['function']['parameters']
            })

        return self._success_response(request_id, {'tools': tools})

    def _handle_call_tool(self, request_id: str, params: Dict) -> Dict:
        """Handle tools/call request"""
        tool_name = params.get('name', '')
        arguments = params.get('arguments', {})

        if tool_name not in self.tools:
            return self._error_response(
                request_id, -32601, f"Unknown tool: {tool_name}"
            )

        tool = self.tools[tool_name]
        log(f"Executing tool: {tool_name}")

        try:
            result = tool.safe_execute(arguments)

            if result.get('success'):
                # Format as MCP content
                content = result.get('result', {})
                if isinstance(content, dict):
                    text = json.dumps(content, indent=2, ensure_ascii=False)
                else:
                    text = str(content)

                return self._success_response(request_id, {
                    'content': [{'type': 'text', 'text': text}],
                    'isError': False
                })
            else:
                return self._success_response(request_id, {
                    'content': [{'type': 'text', 'text': result.get('error', 'Unknown error')}],
                    'isError': True
                })

        except Exception as e:
            log(f"Tool execution error: {e}")
            return self._success_response(request_id, {
                'content': [{'type': 'text', 'text': str(e)}],
                'isError': True
            })

    def _success_response(self, request_id: Optional[str], result: Any) -> Dict:
        """Create success response"""
        return {
            'jsonrpc': '2.0',
            'id': request_id,
            'result': result
        }

    def _error_response(self, request_id: Optional[str], code: int, message: str) -> Dict:
        """Create error response"""
        return {
            'jsonrpc': '2.0',
            'id': request_id,
            'error': {
                'code': code,
                'message': message
            }
        }

    def run(self):
        """Main loop: read from stdin, write to stdout"""
        log("Starting stdio server...")

        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue

            try:
                request = json.loads(line)
                response = self.handle_request(request)
                print(json.dumps(response), flush=True)
            except json.JSONDecodeError as e:
                log(f"Invalid JSON: {e}")
                error_response = self._error_response(None, -32700, f"Parse error: {e}")
                print(json.dumps(error_response), flush=True)

        log("Server stopped")


def main():
    """Entry point for stdio server"""
    server = StdioMCPServer()
    server.run()


if __name__ == "__main__":
    main()
