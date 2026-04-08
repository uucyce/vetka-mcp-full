"""VETKA MCP (Model Context Protocol) Server Package.

This module implements an MCP server that allows ANY AI agent (Claude, GPT, Gemini, Grok, Ollama)
to connect and interact with VETKA's knowledge system via Socket.IO or REST API.

Vision: "VETKA — workshop for agents, spacesuit for humans"

Architecture:
- Socket.IO transport with 'tool_call' / 'tool_result' events
- FastAPI backend with REST alternatives for some endpoints
- OpenAI-compatible tool schemas for model compatibility
- 15+ tools: search, knowledge search, tree, node, files, read, edit, git, tests, intake, camera

Security (Phase 22-MCP-3):
- Rate limiting: 60 req/min API, 10 req/min writes
- Audit logging: all calls logged to data/mcp_audit/
- Approval flow: dangerous operations require human approval

Claude Desktop Integration (Phase 22-MCP-4 + Phase 65.1):
- Stdio transport via stdio_server.py
- Configuration generator via claude_desktop.py
- Memory export/import via memory_transfer.py
- **NEW Phase 65.1:** MCP Bridge (vetka_mcp_bridge.py) - Standard MCP stdio for Claude Code/Desktop

Usage:
    from src.mcp import get_mcp_server

    mcp_server = get_mcp_server(socketio)

Claude Desktop/Code (Phase 65.1):
    # Via MCP Bridge (recommended)
    python src/mcp/vetka_mcp_bridge.py

    # Or legacy stdio server
    from src.mcp.claude_desktop import generate_claude_config, get_installation_instructions
    print(get_installation_instructions())

@status: active
@phase: 96
@depends: mcp_server, rate_limiter, audit_logger, approval, claude_desktop, memory_transfer
@used_by: main.py, run_mcp.py, src/initialization/components_init.py
"""

from .mcp_server import MCPServer, get_mcp_server
from .rate_limiter import RateLimiter, api_limiter, write_limiter
from .audit_logger import MCPAuditLogger, audit_logger
from .approval import ApprovalManager, ApprovalStatus, approval_manager
from .claude_desktop import generate_claude_config, save_claude_config, get_installation_instructions
from .memory_transfer import MemoryTransfer, memory_transfer

__all__ = [
    # Server
    'MCPServer',
    'get_mcp_server',
    # Rate limiting
    'RateLimiter',
    'api_limiter',
    'write_limiter',
    # Audit
    'MCPAuditLogger',
    'audit_logger',
    # Approval
    'ApprovalManager',
    'ApprovalStatus',
    'approval_manager',
    # Claude Desktop
    'generate_claude_config',
    'save_claude_config',
    'get_installation_instructions',
    # Memory Transfer
    'MemoryTransfer',
    'memory_transfer',
]
