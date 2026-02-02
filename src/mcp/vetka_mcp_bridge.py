#!/usr/bin/env python3
"""VETKA MCP Bridge - Connects Claude Desktop/Code to VETKA tools.

Provides standard MCP stdio transport for VETKA REST API.
Claude Desktop and Claude Code can use VETKA tools via this bridge.

Architecture:
- MCP stdio protocol (JSON-RPC over stdin/stdout)
- REST API client -> VETKA FastAPI server (localhost:5001)
- 29+ tools mapped to VETKA endpoints including:
  - Search (semantic, file)
  - File operations (read, edit, list)
  - Git operations (status, commit)
  - LLM calls (via provider_registry)
  - Session management (init, status)
  - Workflow execution (PM -> Architect -> Dev -> QA)
  - Memory tools (context, preferences, CAM)
  - ARC suggestions for workflow optimization
  - Artifact management (edit, approve, reject, list) - Phase 108.4

Usage:
  # Register in Claude Code:
  claude mcp add vetka -- python /path/to/vetka_mcp_bridge.py

  # Or in Claude Desktop config:
  {
    "mcpServers": {
      "vetka": {
        "command": "python",
        "args": ["/path/to/vetka_mcp_bridge.py"]
      }
    }
  }

@status: active
@phase: 108.4
@depends: mcp.server, mcp.types, httpx, src.mcp.tools (session, compound, workflow), src.elisya.provider_registry, src.memory (elision, engram, compression), src.agents.arc_solver_agent, src.services.artifact_scanner
@used_by: Claude Code, Claude Desktop (via MCP stdio protocol)
"""

# Phase 107: Fix imports for OpenCode MCP - ensure project root is in path
import sys
import os
_project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

import asyncio
import httpx
import json
import sys
import os
import signal
import uuid
import contextvars
import argparse
from typing import Any, Optional
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent
import logging

# Phase 107.3: Logger for MCP bridge (required for pipeline tools)
logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

# MARKER_106a_1: CLI arguments with env var support
def parse_args():
    """Parse CLI args safely - returns defaults if called via MCP stdio"""
    try:
        parser = argparse.ArgumentParser(description='VETKA MCP Bridge')
        parser.add_argument('--http', action='store_true',
                            default=os.getenv('MCP_HTTP_MODE', '').lower() == 'true',
                            help='Use HTTP transport')
        parser.add_argument('--ws', action='store_true',
                            default=os.getenv('MCP_WS_MODE', '').lower() == 'true',
                            help='Enable WebSocket endpoint')
        parser.add_argument('--port', type=int,
                            default=int(os.getenv('MCP_PORT', '5002')),
                            help='HTTP/WS port')
        parser.add_argument('--session-id', type=str,
                            default=os.getenv('MCP_SESSION_ID'),
                            help='Session ID for isolation')
        # parse_known_args ignores unknown args (safe for MCP stdio)
        args, _ = parser.parse_known_args()
        return args
    except Exception:
        # Fallback to defaults if parsing fails
        class DefaultArgs:
            http = os.getenv('MCP_HTTP_MODE', '').lower() == 'true'
            ws = os.getenv('MCP_WS_MODE', '').lower() == 'true'
            port = int(os.getenv('MCP_PORT', '5002'))
            session_id = os.getenv('MCP_SESSION_ID')
        return DefaultArgs()

# Session context for async propagation
session_context: contextvars.ContextVar[str] = contextvars.ContextVar('session_id', default='default')

# Phase 55.1: MCP tools registration
from src.mcp.tools.session_tools import register_session_tools
from src.mcp.tools.compound_tools import register_compound_tools
from src.mcp.tools.workflow_tools import register_workflow_tools

# VETKA server configuration
VETKA_BASE_URL = "http://localhost:5001"
VETKA_TIMEOUT = 90.0  # FIX_95.6: Increased from 30s for LLM calls (Grok can take 60s+)

# Create MCP server
server = Server("vetka")

# HTTP client for VETKA API
http_client: Optional[httpx.AsyncClient] = None


# ============================================================================
# LIFECYCLE
# ============================================================================

async def init_client(session_id: str = None):
    """Initialize HTTP clients with session isolation (MARKER_106a_2)"""
    global http_client

    if session_id is None:
        session_id = str(uuid.uuid4())

    # Set in context for downstream use
    session_context.set(session_id)

    headers = {
        "X-Session-ID": session_id,
        "X-Agent-ID": f"mcp_{session_id[:8]}",
        "X-Client-Version": "106.0"
    }

    http_client = httpx.AsyncClient(
        base_url=VETKA_BASE_URL,
        timeout=httpx.Timeout(
            connect=10.0,
            read=90.0,
            write=30.0,
            pool=5.0
        ),
        follow_redirects=True,
        headers=headers,
        limits=httpx.Limits(
            max_connections=50,
            max_keepalive_connections=10,
            keepalive_expiry=30.0
        )
    )

    return session_id


async def cleanup_client():
    """Cleanup HTTP clients"""
    global http_client
    if http_client:
        await http_client.aclose()
        http_client = None


# ============================================================================
# MCP GROUP CHAT LOGGING
# ============================================================================
# Logs MCP tool calls to VETKA group chat for visibility

MCP_LOG_GROUP_ID = "5e2198c2-8b1a-45df-807f-5c73c5496aa8"  # Claude Architect group
MCP_LOG_ENABLED = True  # Set to False to disable logging

async def log_to_group_chat(message: str, msg_type: str = "system"):
    """Send log message to VETKA group chat"""
    if not MCP_LOG_ENABLED or not http_client:
        return
    try:
        await http_client.post(
            f"/api/debug/mcp/groups/{MCP_LOG_GROUP_ID}/send",
            json={
                "agent_id": "claude_mcp",
                "content": message,
                "message_type": msg_type
            }
        )
    except Exception as e:
        print(f"[MCP] Failed to log to group: {e}", file=sys.stderr)


async def log_mcp_request(tool_name: str, arguments: dict, request_id: str):
    """Log MCP request to VETKA group chat"""
    args_short = json.dumps(arguments, ensure_ascii=False)
    # FIX_107.2: Increased truncation limit for better debugging
    if len(args_short) > 2000:
        args_short = args_short[:2000] + "..."
    await log_to_group_chat(f"🔧 **{tool_name}** `{request_id}`\n```\n{args_short}\n```", "chat")


async def log_mcp_response(tool_name: str, result: dict, request_id: str, duration_ms: float, error: str = None):
    """Log MCP response to VETKA group chat"""
    if error:
        await log_to_group_chat(f"❌ **{tool_name}** failed: {error} ({int(duration_ms)}ms)", "error")
    else:
        await log_to_group_chat(f"✅ **{tool_name}** done ({int(duration_ms)}ms)", "response")


# OLD CONSOLE LOGGING (archived)
# async def log_mcp_request(tool_name: str, arguments: dict, request_id: str):
#     """Log MCP request to standalone console on port 5002"""
#     print(f"[MCP_DEBUG] log_mcp_request called: {tool_name}, console_client={console_client is not None}", file=sys.stderr)
#     try:
#         from datetime import datetime
#         if console_client:
#             print(f"[MCP_DEBUG] Sending to console...", file=sys.stderr)
#             resp = await console_client.post(
#                 "/api/log",
#                 json={
#                     "id": request_id,
#                     "type": "request",
#                     "timestamp": datetime.now().isoformat(),
#                     "agent": "claude_desktop",
#                     "model": "opus-4",
#                     "tool": tool_name,
#                     "content": json.dumps(arguments, ensure_ascii=False, indent=2)
#                 }
#             )
#             print(f"[MCP_DEBUG] Console response: {resp.status_code}", file=sys.stderr)
#         else:
#             print(f"[MCP_DEBUG] console_client is None!", file=sys.stderr)
#     except Exception as e:
#         print(f"[MCP] Failed to log request: {e}", file=sys.stderr)


# async def log_mcp_response(tool_name: str, result: dict, request_id: str, duration_ms: float, error: str = None):
#     """Log MCP response to standalone console on port 5002"""
#     try:
#         from datetime import datetime
#         if console_client:
#             # Truncate large results for display
#             content = json.dumps(result, ensure_ascii=False, indent=2) if result else ""
#             if len(content) > 5000:
#                 content = content[:5000] + "\n... [truncated]"
#
#             await console_client.post(
#                 "/api/log",
#                 json={
#                     "id": request_id.replace("req-", "res-"),
#                     "type": "response",
#                     "timestamp": datetime.now().isoformat(),
#                     "tool": tool_name,
#                     "agent": "claude_code",
#                     "model": "opus-4",
#                     "content": content,
#                     "duration_ms": int(duration_ms),
#                     "success": error is None,
#                     "error": error or ""
#                 }
#             )
#     except Exception as e:
#         # Silently fail - logging should not break functionality
#         print(f"[MCP] Failed to log response: {e}", file=sys.stderr)


# ============================================================================
# TOOL DEFINITIONS
# ============================================================================

@server.list_tools()
async def list_tools() -> list[Tool]:
    """Return list of available VETKA tools"""
    tools = [
        Tool(
            name="vetka_search_semantic",
            description="Semantic search in VETKA knowledge base using Qdrant vector search. "
                       "Search for concepts, ideas, or topics across all indexed documents.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Semantic search query (e.g., 'authentication logic', 'API error handling')"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Max results to return (default: 10, max: 50)",
                        "default": 10,
                        "minimum": 1,
                        "maximum": 50
                    }
                },
                "required": ["query"]
            }
        ),
        Tool(
            name="vetka_read_file",
            description="Read file content from VETKA project. Returns full file content with line numbers.",
            inputSchema={
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Path to file (relative to project root, e.g., 'src/main.py')"
                    }
                },
                "required": ["file_path"]
            }
        ),
        Tool(
            name="vetka_get_tree",
            description="Get VETKA 3D tree structure showing files and folders hierarchy. "
                       "Useful for understanding project structure and navigating codebase.",
            inputSchema={
                "type": "object",
                "properties": {
                    "format": {
                        "type": "string",
                        "enum": ["tree", "summary", "simple"],
                        "description": "Output format: 'tree' for full structure, 'summary'/'simple' for stats only",
                        "default": "summary"
                    }
                }
            }
        ),
        Tool(
            name="vetka_health",
            description="Check VETKA server health and component status. Shows which components "
                       "(Qdrant, metrics, model router, etc.) are available and healthy.",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        Tool(
            name="vetka_list_files",
            description="List files in a directory or matching a pattern. Returns file paths with metadata.",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Directory path to list (default: project root)",
                        "default": "."
                    },
                    "pattern": {
                        "type": "string",
                        "description": "Glob pattern to filter files (e.g., '*.py', 'src/**/*.ts')"
                    },
                    "recursive": {
                        "type": "boolean",
                        "description": "Recursively list subdirectories",
                        "default": False
                    }
                }
            }
        ),
        Tool(
            name="vetka_search_files",
            description="Search for files by name or content pattern using ripgrep-style search. "
                       "Fast full-text search across the codebase.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query (file name or content pattern)"
                    },
                    "search_type": {
                        "type": "string",
                        "enum": ["filename", "content", "both"],
                        "description": "Search in filenames, file content, or both",
                        "default": "both"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Max results (default: 20)",
                        "default": 20
                    }
                },
                "required": ["query"]
            }
        ),
        Tool(
            name="vetka_get_metrics",
            description="Get VETKA metrics and analytics. Shows system performance, query stats, and usage data.",
            inputSchema={
                "type": "object",
                "properties": {
                    "metric_type": {
                        "type": "string",
                        "enum": ["dashboard", "agents", "all"],
                        "description": "Type of metrics to retrieve",
                        "default": "dashboard"
                    }
                }
            }
        ),
        Tool(
            name="vetka_get_knowledge_graph",
            description="Get VETKA knowledge graph structure showing relationships between code entities, "
                       "concepts, and documents. Useful for understanding architecture and dependencies.",
            inputSchema={
                "type": "object",
                "properties": {
                    "format": {
                        "type": "string",
                        "enum": ["json", "summary"],
                        "description": "Output format",
                        "default": "summary"
                    }
                }
            }
        ),
        # ═══════════════════════════════════════════════════════════════════════
        # WRITE TOOLS (Phase 65.2) - Require approval or dry_run
        # ═══════════════════════════════════════════════════════════════════════
        Tool(
            name="vetka_edit_file",
            description="Edit or create a file. Creates backup before changes. "
                       "Default: dry_run=true (preview only). Set dry_run=false to apply changes.",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "File path (relative to project root, e.g., 'src/main.py')"
                    },
                    "content": {
                        "type": "string",
                        "description": "New file content"
                    },
                    "mode": {
                        "type": "string",
                        "enum": ["write", "append"],
                        "description": "Write mode: 'write' replaces file, 'append' adds to end",
                        "default": "write"
                    },
                    "create_dirs": {
                        "type": "boolean",
                        "description": "Create parent directories if they don't exist",
                        "default": False
                    },
                    "dry_run": {
                        "type": "boolean",
                        "description": "Preview only (no actual write). Set to false to apply changes.",
                        "default": True
                    }
                },
                "required": ["path", "content"]
            }
        ),
        Tool(
            name="vetka_git_commit",
            description="Create a git commit. Default: dry_run=true (preview only). "
                       "Set dry_run=false to actually commit.",
            inputSchema={
                "type": "object",
                "properties": {
                    "message": {
                        "type": "string",
                        "description": "Commit message (min 5 characters)"
                    },
                    "files": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Files to stage (empty = all changed files)"
                    },
                    "dry_run": {
                        "type": "boolean",
                        "description": "Preview only. Set to false to commit.",
                        "default": True
                    }
                },
                "required": ["message"]
            }
        ),
        Tool(
            name="vetka_run_tests",
            description="Run pytest tests with output capture. Returns stdout/stderr/exit code.",
            inputSchema={
                "type": "object",
                "properties": {
                    "test_path": {
                        "type": "string",
                        "description": "Path to test file or directory",
                        "default": "tests/"
                    },
                    "pattern": {
                        "type": "string",
                        "description": "Test name pattern (-k flag)"
                    },
                    "verbose": {
                        "type": "boolean",
                        "description": "Verbose output",
                        "default": True
                    },
                    "timeout": {
                        "type": "integer",
                        "description": "Timeout in seconds (max 300)",
                        "default": 60,
                        "minimum": 1,
                        "maximum": 300
                    }
                }
            }
        ),
        Tool(
            name="vetka_camera_focus",
            description="Move 3D camera to focus on a specific file, branch, or overview. "
                       "Use to show user something important in the visualization. "
                       "Requires active VETKA UI session.",
            inputSchema={
                "type": "object",
                "properties": {
                    "target": {
                        "type": "string",
                        "description": "File path (e.g., 'src/main.py'), branch name, or 'overview' for full tree"
                    },
                    "zoom": {
                        "type": "string",
                        "enum": ["close", "medium", "far"],
                        "description": "Zoom level",
                        "default": "medium"
                    },
                    "highlight": {
                        "type": "boolean",
                        "description": "Highlight target with glow effect",
                        "default": True
                    }
                },
                "required": ["target"]
            }
        ),
        Tool(
            name="vetka_git_status",
            description="Get git status showing modified, staged, and untracked files. "
                       "Also shows current branch and last commit.",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        Tool(
            name="vetka_call_model",
            description="Call any LLM model through VETKA infrastructure (Grok, GPT, Claude, Gemini, Ollama). "
                       "Supports function calling for compatible models.",
            inputSchema={
                "type": "object",
                "properties": {
                    "model": {
                        "type": "string",
                        "description": "Model: grok-4, gpt-4o, claude-opus-4-5, gemini-2.0-flash, llama3.1:8b, etc."
                    },
                    "messages": {
                        "type": "array",
                        "description": "Chat messages [{role, content}]",
                        "items": {
                            "type": "object",
                            "properties": {
                                "role": {"type": "string", "enum": ["user", "assistant", "system"]},
                                "content": {"type": "string"}
                            },
                            "required": ["role", "content"]
                        }
                    },
                    "temperature": {
                        "type": "number",
                        "description": "Temperature (0.0-2.0, default: 0.7)",
                        "default": 0.7,
                        "minimum": 0.0,
                        "maximum": 2.0
                    },
                    "max_tokens": {
                        "type": "integer",
                        "description": "Max tokens to generate (default: 4096)",
                        "default": 4096,
                        "minimum": 1
                    },
                    "tools": {
                        "type": "array",
                        "description": "Optional function calling tools (OpenAI format)",
                        "items": {"type": "object"}
                    },
                    "inject_context": {
                        "type": "object",
                        "description": "Phase 55.2: Auto-inject VETKA context into system prompt. Saves tokens!",
                        "properties": {
                            "files": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "File paths to inject (e.g., ['src/main.py'])"
                            },
                            "session_id": {
                                "type": "string",
                                "description": "MCPStateManager session ID"
                            },
                            "include_prefs": {
                                "type": "boolean",
                                "description": "Include Engram user preferences"
                            },
                            "include_cam": {
                                "type": "boolean",
                                "description": "Include CAM active nodes"
                            },
                            "semantic_query": {
                                "type": "string",
                                "description": "Semantic search to find relevant context"
                            },
                            "compress": {
                                "type": "boolean",
                                "description": "Apply ELISION compression (default: true)"
                            }
                        }
                    }
                },
                "required": ["model", "messages"]
            }
        ),
        Tool(
            name="vetka_read_group_messages",
            description="Read messages from VETKA group chat. Use to see what other agents wrote.",
            inputSchema={
                "type": "object",
                "properties": {
                    "group_id": {
                        "type": "string",
                        "description": "Group ID (default: MCP log group)",
                        "default": "609c0d9a-b5bc-426b-b134-d693023bdac8"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Max messages to return (default: 10)",
                        "default": 10
                    }
                }
            }
        ),
        # MARKER_108_3: Chat digest for MCP context
        Tool(
            name="vetka_get_chat_digest",
            description="Get chat digest for MCP context injection. Returns recent messages, agent logs, "
                       "and summary for a specific chat. Use this to understand chat context efficiently.",
            inputSchema={
                "type": "object",
                "properties": {
                    "chat_id": {
                        "type": "string",
                        "description": "Chat UUID to get digest for"
                    },
                    "max_messages": {
                        "type": "integer",
                        "description": "Max recent messages to include (default: 10)",
                        "default": 10
                    }
                },
                "required": ["chat_id"]
            }
        ),
        # MARKER_108_2: MCP → VETKA message bridge
        Tool(
            name="vetka_send_message",
            description="Send message from MCP to VETKA chat. Works with both regular chats and group chats. "
                       "Use this to post updates, results, or notifications to VETKA UI.",
            inputSchema={
                "type": "object",
                "properties": {
                    "message": {
                        "type": "string",
                        "description": "Message content to send"
                    },
                    "chat_id": {
                        "type": "string",
                        "description": "Chat ID (for regular chats) or Group ID (for group chats)"
                    },
                    "sender": {
                        "type": "string",
                        "description": "Sender ID (default: mcp_agent)",
                        "default": "mcp_agent"
                    },
                    "message_type": {
                        "type": "string",
                        "description": "Message type: assistant, user, system, error, chat",
                        "enum": ["assistant", "user", "system", "error", "chat"],
                        "default": "assistant"
                    },
                    "is_group": {
                        "type": "boolean",
                        "description": "True for group chats, False for regular chats (default: False)",
                        "default": False
                    }
                },
                "required": ["message", "chat_id"]
            }
        ),
        # ═══════════════════════════════════════════════════════════════════════
        # MEMORY TOOLS (Phase 93.6) - Context and preferences access
        # ═══════════════════════════════════════════════════════════════════════
        Tool(
            name="vetka_get_conversation_context",
            description="Get ELISION-compressed conversation context. Use before responding to get "
                       "relevant conversation history with 40-60% token savings. Returns compressed "
                       "context suitable for prompt injection.",
            inputSchema={
                "type": "object",
                "properties": {
                    "group_id": {
                        "type": "string",
                        "description": "Group ID to get context from (optional)"
                    },
                    "max_messages": {
                        "type": "integer",
                        "description": "Max messages to include in context (default: 20)",
                        "default": 20
                    },
                    "compress": {
                        "type": "boolean",
                        "description": "Apply ELISION compression (default: true)",
                        "default": True
                    }
                }
            }
        ),
        Tool(
            name="vetka_get_user_preferences",
            description="Get user preferences from Engram memory. Returns hot preferences (frequently "
                       "accessed) from RAM cache plus cold preferences from Qdrant. Use to personalize "
                       "responses based on user's communication style, favorite topics, etc.",
            inputSchema={
                "type": "object",
                "properties": {
                    "user_id": {
                        "type": "string",
                        "description": "User ID (default: 'danila')",
                        "default": "danila"
                    },
                    "category": {
                        "type": "string",
                        "description": "Preference category to fetch (optional, returns all if not specified)",
                        "enum": ["communication_style", "viewport_patterns", "code_preferences", "topics", "all"]
                    }
                }
            }
        ),
        Tool(
            name="vetka_get_memory_summary",
            description="Get CAM (Context-Aware Memory) and Elisium compression summary. Returns: "
                       "active memory nodes, compression stats, age distribution, quality scores. "
                       "Use to understand what context is available and its quality level.",
            inputSchema={
                "type": "object",
                "properties": {
                    "include_stats": {
                        "type": "boolean",
                        "description": "Include compression statistics (default: true)",
                        "default": True
                    },
                    "include_nodes": {
                        "type": "boolean",
                        "description": "Include list of active memory nodes (default: false)",
                        "default": False
                    }
                }
            }
        ),
        # Phase 95: ARC Integration - MCP Tool
        Tool(
            name="vetka_arc_suggest",
            description="Generate ARC (Adaptive Reasoning Context) suggestions for workflow graphs. "
                       "Uses abstraction and reasoning to find creative improvements, connections, and "
                       "optimizations in workflow structures. Returns top-ranked transformation suggestions.",
            inputSchema={
                "type": "object",
                "properties": {
                    "context": {
                        "type": "string",
                        "description": "Task or problem context (human-readable description)"
                    },
                    "workflow_id": {
                        "type": "string",
                        "description": "Optional workflow ID for tracking (default: 'mcp_workflow')",
                        "default": "mcp_workflow"
                    },
                    "graph_data": {
                        "type": "object",
                        "description": "Optional graph data with 'nodes' and 'edges' keys. If not provided, "
                                     "a minimal graph will be created from context.",
                        "properties": {
                            "nodes": {
                                "type": "array",
                                "description": "List of nodes with 'id' and optional 'type' fields"
                            },
                            "edges": {
                                "type": "array",
                                "description": "List of edges with 'source' and 'target' fields"
                            }
                        }
                    },
                    "num_candidates": {
                        "type": "integer",
                        "description": "Number of transformation candidates to generate (default: 10, range: 3-20)",
                        "default": 10,
                        "minimum": 3,
                        "maximum": 20
                    },
                    "min_score": {
                        "type": "number",
                        "description": "Minimum quality score to include in results (0.0-1.0, default: 0.5)",
                        "default": 0.5,
                        "minimum": 0.0,
                        "maximum": 1.0
                    }
                },
                "required": ["context"]
            }
        ),
        # MARKER_102.9_START: Agent Pipeline tool
        # MARKER_103.5: Added auto_write parameter
        Tool(
            name="vetka_spawn_pipeline",
            description=(
                "Spawn fractal agent pipeline for task execution. "
                "Auto-triggers Grok researcher on unclear parts (?). "
                "Phases: research (explore), fix (debug), build (implement). "
                "Progress streams to chat in real-time! "
                "Use auto_write=false for staging mode (safe review before file creation)."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "task": {
                        "type": "string",
                        "description": "Task description to execute through pipeline"
                    },
                    "phase_type": {
                        "type": "string",
                        "enum": ["research", "fix", "build"],
                        "description": "Pipeline type: research (explore), fix (debug), build (implement)",
                        "default": "research"
                    },
                    "chat_id": {
                        "type": "string",
                        "description": "Optional chat ID for progress streaming (default: Lightning chat)"
                    },
                    "auto_write": {
                        "type": "boolean",
                        "description": "If true (default), write files immediately. If false, save to JSON for later review with retro_apply_spawn.py",
                        "default": True
                    }
                },
                "required": ["task"]
            }
        ),
        # MARKER_102.9_END
        # MARKER_108_4_MCP_REGISTER: Artifact management tools (Phase 108.4)
        Tool(
            name="vetka_edit_artifact",
            description="Edit artifact content by artifact_id. Updates artifact file on disk. "
                       "Use for modifying code artifacts generated by workflow agents.",
            inputSchema={
                "type": "object",
                "properties": {
                    "artifact_id": {
                        "type": "string",
                        "description": "Artifact ID (e.g., 'art_123', file path in artifacts/)"
                    },
                    "content": {
                        "type": "string",
                        "description": "New artifact content"
                    },
                    "reason": {
                        "type": "string",
                        "description": "Reason for edit (optional)",
                        "default": "Manual edit via MCP"
                    }
                },
                "required": ["artifact_id", "content"]
            }
        ),
        Tool(
            name="vetka_approve_artifact",
            description="Approve an artifact for deployment/integration. Marks artifact as approved "
                       "in approval service. Use after reviewing generated code artifacts.",
            inputSchema={
                "type": "object",
                "properties": {
                    "artifact_id": {
                        "type": "string",
                        "description": "Artifact ID to approve"
                    },
                    "reason": {
                        "type": "string",
                        "description": "Approval reason (optional)",
                        "default": "Approved via MCP"
                    }
                },
                "required": ["artifact_id"]
            }
        ),
        Tool(
            name="vetka_reject_artifact",
            description="Reject an artifact and provide feedback. Marks artifact as rejected in "
                       "approval service. Include specific feedback for agent improvement.",
            inputSchema={
                "type": "object",
                "properties": {
                    "artifact_id": {
                        "type": "string",
                        "description": "Artifact ID to reject"
                    },
                    "feedback": {
                        "type": "string",
                        "description": "Rejection reason/feedback for improvement"
                    }
                },
                "required": ["artifact_id", "feedback"]
            }
        ),
        Tool(
            name="vetka_list_artifacts",
            description="List artifacts by status (pending, approved, rejected, all). Returns artifact "
                       "metadata including file path, type, language, size, and approval status.",
            inputSchema={
                "type": "object",
                "properties": {
                    "status": {
                        "type": "string",
                        "enum": ["pending", "approved", "rejected", "all"],
                        "description": "Filter by approval status (default: all)",
                        "default": "all"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Max artifacts to return (default: 50)",
                        "default": 50,
                        "minimum": 1,
                        "maximum": 200
                    }
                }
            }
        ),
    ]

    # Phase 55.1: Register new MCP tools
    mcp_tools = []
    register_session_tools(mcp_tools)
    register_compound_tools(mcp_tools)
    register_workflow_tools(mcp_tools)

    # Convert to MCP format (handle both dict and BaseMCPTool objects)
    for tool in mcp_tools:
        if isinstance(tool, dict):
            # Legacy dict format
            tool_name = tool.get("name")
            tool_desc = tool.get("description", "")
            tool_params = tool.get("parameters", {})
        else:
            # BaseMCPTool instance (Phase 55.1)
            tool_name = tool.name
            tool_desc = tool.description
            tool_params = tool.schema
        tools.append(Tool(
            name=tool_name,
            description=tool_desc,
            inputSchema=tool_params
        ))

    return tools


# ============================================================================
# TOOL IMPLEMENTATIONS
# ============================================================================

@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    """Execute a VETKA tool via REST API"""
    import time
    import uuid

    # Generate request ID for logging
    request_id = f"req-{uuid.uuid4().hex[:8]}"
    start_time = time.time()

    # Log request to VETKA group chat
    await log_mcp_request(name, arguments, request_id)

    if not http_client:
        error_msg = "Error: HTTP client not initialized. Please restart the MCP server."
        await log_mcp_response(name, None, request_id, 0, error=error_msg)
        return [TextContent(type="text", text=error_msg)]

    try:
        if name == "vetka_search_semantic":
            # Semantic search via REST
            query = arguments.get("query", "")
            limit = arguments.get("limit", 10)

            response = await http_client.get(
                "/api/search/semantic",
                params={"q": query, "limit": limit}
            )

        elif name == "vetka_read_file":
            # Read file via REST
            file_path = arguments.get("file_path", "")

            response = await http_client.post(
                "/api/files/read",
                json={"file_path": file_path}
            )

        elif name == "vetka_get_tree":
            # Get tree structure
            format_type = arguments.get("format", "summary")
            # Normalize 'simple' to 'summary'
            if format_type == "simple":
                format_type = "summary"

            response = await http_client.get("/api/tree/data")

            if response.status_code == 200:
                data = response.json()

                if format_type == "summary":
                    # Return summary instead of full tree
                    tree_data = data.get("tree", {})
                    nodes = tree_data.get("nodes", [])

                    # Count by type - FIX_101.6: API returns "leaf" not "file"
                    file_count = sum(1 for n in nodes if n.get("type") in ["file", "leaf"])
                    folder_count = sum(1 for n in nodes if n.get("type") in ["branch", "folder"])

                    summary = (
                        f"VETKA Tree Summary\n"
                        f"==================\n"
                        f"Total nodes: {len(nodes)}\n"
                        f"Files: {file_count}\n"
                        f"Folders: {folder_count}\n"
                        f"Root: {tree_data.get('name', 'VETKA')}\n"
                        f"\nUse format='tree' to see full structure."
                    )

                    return [TextContent(type="text", text=summary)]
                else:
                    # Return full tree
                    return [TextContent(
                        type="text",
                        text=json.dumps(data, indent=2, ensure_ascii=False)
                    )]

        elif name == "vetka_health":
            # Health check
            response = await http_client.get("/api/health")

        elif name == "vetka_list_files":
            # List files - use tree endpoint with filtering
            # TODO: Implement proper file listing endpoint in VETKA
            path = arguments.get("path", ".")
            pattern = arguments.get("pattern")

            response = await http_client.get("/api/tree/data")

            if response.status_code == 200:
                data = response.json()
                tree_data = data.get("tree", {})
                nodes = tree_data.get("nodes", [])

                # Filter files (accept both "file" and "leaf" types)
                files = [
                    n for n in nodes
                    if n.get("type") in ["file", "leaf"] and
                    (not pattern or pattern in n.get("metadata", {}).get("path", ""))
                ]

                file_list = "\n".join([
                    f"- {n.get('metadata', {}).get('path', n.get('name', 'unknown'))}"
                    for n in files[:50]  # Limit to 50 files
                ])

                result_text = (
                    f"Found {len(files)} files\n"
                    f"{'(showing first 50)' if len(files) > 50 else ''}\n\n"
                    f"{file_list}"
                )

                return [TextContent(type="text", text=result_text)]

        elif name == "vetka_search_files":
            # File search - use semantic endpoint with filename filter
            query = arguments.get("query", "")
            search_type = arguments.get("search_type", "both")
            limit = arguments.get("limit", 20)

            # For now, use semantic search
            # TODO: Add dedicated file search endpoint
            response = await http_client.get(
                "/api/search/semantic",
                params={"q": query, "limit": limit}
            )

        elif name == "vetka_get_metrics":
            # Get metrics
            metric_type = arguments.get("metric_type", "dashboard")

            if metric_type == "dashboard":
                response = await http_client.get("/api/metrics/dashboard")
            elif metric_type == "agents":
                response = await http_client.get("/api/metrics/agents")
            else:
                # Get both
                dashboard_resp = await http_client.get("/api/metrics/dashboard")
                agents_resp = await http_client.get("/api/metrics/agents")

                combined = {
                    "dashboard": dashboard_resp.json() if dashboard_resp.status_code == 200 else None,
                    "agents": agents_resp.json() if agents_resp.status_code == 200 else None
                }

                return [TextContent(
                    type="text",
                    text=json.dumps(combined, indent=2, ensure_ascii=False)
                )]

        elif name == "vetka_get_knowledge_graph":
            # Get knowledge graph
            format_type = arguments.get("format", "summary")

            response = await http_client.get("/api/tree/knowledge-graph")

            if response.status_code == 200:
                data = response.json()

                if format_type == "summary":
                    nodes_count = len(data.get("nodes", []))
                    edges_count = len(data.get("edges", []))

                    summary = (
                        f"VETKA Knowledge Graph Summary\n"
                        f"============================\n"
                        f"Nodes: {nodes_count}\n"
                        f"Edges: {edges_count}\n"
                        f"\nUse format='json' to see full graph data."
                    )

                    return [TextContent(type="text", text=summary)]
                else:
                    return [TextContent(
                        type="text",
                        text=json.dumps(data, indent=2, ensure_ascii=False)
                    )]

        # ═══════════════════════════════════════════════════════════════════════
        # WRITE TOOLS (Phase 65.2) - Execute via internal tools
        # ═══════════════════════════════════════════════════════════════════════

        elif name == "vetka_edit_file":
            # Edit file - uses internal tool
            from src.mcp.tools.edit_file_tool import EditFileTool
            tool = EditFileTool()

            # Validate
            validation_error = tool.validate_arguments(arguments)
            if validation_error:
                return [TextContent(type="text", text=f"❌ Validation error: {validation_error}")]

            result = tool.execute(arguments)
            return [TextContent(type="text", text=format_write_result("vetka_edit_file", result))]

        elif name == "vetka_git_commit":
            # Git commit - uses internal tool
            from src.mcp.tools.git_tool import GitCommitTool
            tool = GitCommitTool()

            # Validate
            validation_error = tool.validate_arguments(arguments)
            if validation_error:
                return [TextContent(type="text", text=f"❌ Validation error: {validation_error}")]

            result = tool.execute(arguments)
            return [TextContent(type="text", text=format_write_result("vetka_git_commit", result))]

        elif name == "vetka_git_status":
            # Git status - read-only, uses internal tool
            from src.mcp.tools.git_tool import GitStatusTool
            tool = GitStatusTool()
            result = tool.execute(arguments)
            return [TextContent(type="text", text=format_git_status(result))]

        elif name == "vetka_run_tests":
            # Run tests - uses internal tool
            from src.mcp.tools.run_tests_tool import RunTestsTool
            tool = RunTestsTool()

            # Validate
            validation_error = tool.validate_arguments(arguments)
            if validation_error:
                return [TextContent(type="text", text=f"❌ Validation error: {validation_error}")]

            result = tool.execute(arguments)
            return [TextContent(type="text", text=format_test_result(result))]

        elif name == "vetka_camera_focus":
            # Camera focus - uses internal tool (requires UI)
            from src.mcp.tools.camera_tool import CameraControlTool
            tool = CameraControlTool()
            result = tool.execute(arguments)
            return [TextContent(type="text", text=format_camera_result(result, arguments))]

        elif name == "vetka_call_model":
            # LLM call - uses internal tool
            from src.mcp.tools.llm_call_tool import LLMCallTool
            tool = LLMCallTool()

            # Validate
            validation_error = tool.validate_arguments(arguments)
            if validation_error:
                return [TextContent(type="text", text=f"❌ Validation error: {validation_error}")]

            result = tool.execute(arguments)
            return [TextContent(type="text", text=format_llm_result(result))]

        elif name == "vetka_read_group_messages":
            # Read group messages via REST API
            group_id = arguments.get("group_id", MCP_LOG_GROUP_ID)
            limit = arguments.get("limit", 10)

            response = await http_client.get(
                f"/api/groups/{group_id}/messages",
                params={"limit": limit}
            )

        # MARKER_108_3: Chat digest for MCP context
        elif name == "vetka_get_chat_digest":
            # Get chat digest for MCP agents
            chat_id = arguments.get("chat_id", "")
            max_messages = arguments.get("max_messages", 10)

            try:
                from src.chat.chat_history_manager import get_chat_history_manager

                manager = get_chat_history_manager()
                digest = manager.get_chat_digest(chat_id, max_messages)

                duration_ms = (time.time() - start_time) * 1000
                await log_mcp_response(name, digest, request_id, duration_ms)
                return [TextContent(type="text", text=format_chat_digest(digest))]

            except Exception as e:
                return [TextContent(type="text", text=f"❌ Error getting chat digest: {e}")]

        # MARKER_108_2: MCP → VETKA message bridge
        elif name == "vetka_send_message":
            # Send message to VETKA chat (group or regular)
            message = arguments.get("message", "")
            chat_id = arguments.get("chat_id", "")
            sender = arguments.get("sender", "mcp_agent")
            message_type = arguments.get("message_type", "assistant")
            is_group = arguments.get("is_group", False)

            if not message or not chat_id:
                return [TextContent(type="text", text="❌ Error: message and chat_id are required")]

            try:
                # Choose endpoint based on chat type
                if is_group:
                    # Group chat endpoint
                    endpoint = f"/api/groups/{chat_id}/messages"
                    payload = {
                        "sender_id": sender,
                        "content": message,
                        "message_type": message_type
                    }
                else:
                    # Regular chat endpoint
                    endpoint = f"/api/chats/{chat_id}/messages"
                    payload = {
                        "role": message_type if message_type in ["user", "assistant", "system"] else "assistant",
                        "content": message,
                        "agent": sender,
                        "metadata": {"source": "mcp_bridge"}
                    }

                # Send message via REST API
                response = await http_client.post(endpoint, json=payload)

                if response.status_code == 200:
                    result = response.json()
                    duration_ms = (time.time() - start_time) * 1000
                    await log_mcp_response(name, result, request_id, duration_ms)

                    return [TextContent(type="text", text=(
                        f"✅ Message Sent\n"
                        f"━{'━' * 39}\n"
                        f"Chat: {chat_id[:8]}...\n"
                        f"Type: {'Group' if is_group else 'Regular'}\n"
                        f"Sender: {sender}\n"
                        f"Length: {len(message)} chars"
                    ))]
                else:
                    # API returned error
                    error_msg = f"API error {response.status_code}: {response.text}"
                    duration_ms = (time.time() - start_time) * 1000
                    await log_mcp_response(name, None, request_id, duration_ms, error=error_msg)
                    return [TextContent(type="text", text=f"❌ {error_msg}")]

            except httpx.ConnectError:
                # Server not available - save to local buffer
                error_msg = "VETKA server unavailable, message buffered locally"
                try:
                    # Save to local buffer for retry
                    from pathlib import Path
                    buffer_path = Path("data/mcp_message_buffer.json")
                    buffer_path.parent.mkdir(parents=True, exist_ok=True)

                    buffer_data = []
                    if buffer_path.exists():
                        buffer_data = json.loads(buffer_path.read_text())

                    buffer_data.append({
                        "chat_id": chat_id,
                        "message": message,
                        "sender": sender,
                        "message_type": message_type,
                        "is_group": is_group,
                        "timestamp": time.time()
                    })

                    buffer_path.write_text(json.dumps(buffer_data, indent=2, ensure_ascii=False))

                    return [TextContent(type="text", text=(
                        f"⚠️  Message Buffered (Server Offline)\n"
                        f"━{'━' * 39}\n"
                        f"Chat: {chat_id[:8]}...\n"
                        f"Saved to: {buffer_path}\n"
                        f"Will retry when server is available"
                    ))]
                except Exception as buffer_error:
                    return [TextContent(type="text", text=f"❌ Server offline and buffer failed: {buffer_error}")]

            except Exception as e:
                duration_ms = (time.time() - start_time) * 1000
                error_msg = f"Error sending message: {e}"
                await log_mcp_response(name, None, request_id, duration_ms, error=error_msg)
                return [TextContent(type="text", text=f"❌ {error_msg}")]

        # ═══════════════════════════════════════════════════════════════════════
        # MEMORY TOOLS (Phase 93.6) - Direct implementation
        # ═══════════════════════════════════════════════════════════════════════

        elif name == "vetka_get_conversation_context":
            # Get ELISION-compressed conversation context
            group_id = arguments.get("group_id")
            max_messages = arguments.get("max_messages", 20)
            compress = arguments.get("compress", True)

            try:
                # Get messages from group or recent chat
                if group_id:
                    msg_response = await http_client.get(
                        f"/api/groups/{group_id}/messages",
                        params={"limit": max_messages}
                    )
                else:
                    # Use default chat history endpoint
                    msg_response = await http_client.get(
                        "/api/chat/history",
                        params={"limit": max_messages}
                    )

                if msg_response.status_code != 200:
                    return [TextContent(type="text", text=f"❌ Failed to get messages: {msg_response.status_code}")]

                messages = msg_response.json().get("messages", [])

                # Apply ELISION compression if requested
                if compress and messages:
                    from src.memory.elision import compress_context
                    context_data = {"messages": messages}
                    compressed = compress_context(context_data)
                    result = {
                        "context": compressed,
                        "original_messages": len(messages),
                        "compression_applied": True,
                        "savings_estimate": "40-60% tokens"
                    }
                else:
                    result = {
                        "context": messages,
                        "original_messages": len(messages),
                        "compression_applied": False
                    }

                duration_ms = (time.time() - start_time) * 1000
                await log_mcp_response(name, result, request_id, duration_ms)
                return [TextContent(type="text", text=format_context_result(result))]

            except Exception as e:
                return [TextContent(type="text", text=f"❌ Error getting context: {e}")]

        elif name == "vetka_get_user_preferences":
            # Get user preferences from Engram memory
            user_id = arguments.get("user_id", "danila")
            category = arguments.get("category", "all")

            try:
                from src.memory.engram_user_memory import EngramUserMemory
                from src.memory.qdrant_client import get_qdrant_client

                qdrant = get_qdrant_client()
                memory = EngramUserMemory(qdrant)

                if category == "all":
                    prefs = memory.get_all_preferences(user_id)
                else:
                    prefs = memory.get_preference(user_id, category)

                result = {
                    "user_id": user_id,
                    "category": category,
                    "preferences": prefs if prefs else {},
                    "source": "engram_ram_cache" if memory.ram_cache.get(user_id) else "qdrant"
                }

                duration_ms = (time.time() - start_time) * 1000
                await log_mcp_response(name, result, request_id, duration_ms)
                return [TextContent(type="text", text=format_preferences_result(result))]

            except Exception as e:
                return [TextContent(type="text", text=f"❌ Error getting preferences: {e}")]

        elif name == "vetka_get_memory_summary":
            # Get CAM + Elisium memory summary
            include_stats = arguments.get("include_stats", True)
            include_nodes = arguments.get("include_nodes", False)

            try:
                from src.memory.compression import MemoryCompression

                compressor = MemoryCompression()
                stats = compressor.get_stats() if include_stats else {}

                result = {
                    "memory_system": "CAM + Elisium",
                    "stats": {
                        "compression_schedule": [
                            {"days": "0-6", "dim": 768, "quality": "100%"},
                            {"days": "7-29", "dim": 384, "quality": "90%"},
                            {"days": "30-89", "dim": 256, "quality": "80%"},
                            {"days": "90+", "dim": 64, "quality": "60%"}
                        ],
                        "active_nodes": stats.get("active_nodes", 0) if stats else "N/A",
                        "archived_nodes": stats.get("archived_nodes", 0) if stats else "N/A",
                        "total_embeddings": stats.get("total_embeddings", 0) if stats else "N/A"
                    } if include_stats else None,
                    "nodes": stats.get("nodes", [])[:10] if include_nodes and stats else None
                }

                duration_ms = (time.time() - start_time) * 1000
                await log_mcp_response(name, result, request_id, duration_ms)
                return [TextContent(type="text", text=format_memory_summary(result))]

            except Exception as e:
                return [TextContent(type="text", text=f"❌ Error getting memory summary: {e}")]

        elif name == "vetka_arc_suggest":
            # Phase 95: ARC suggestions for MCP clients
            context = arguments.get("context", "")
            workflow_id = arguments.get("workflow_id", "mcp_workflow")
            graph_data = arguments.get("graph_data")
            num_candidates = arguments.get("num_candidates", 10)
            min_score = arguments.get("min_score", 0.5)

            try:
                from src.agents.arc_solver_agent import ARCSolverAgent

                # Create ARC solver instance (local mode for MCP)
                arc_solver = ARCSolverAgent(use_api=False, learner=None)

                # If no graph_data provided, create minimal graph from context
                if not graph_data:
                    graph_data = {
                        "nodes": [{"id": "context", "type": "task"}],
                        "edges": []
                    }

                # Get ARC suggestions
                arc_result = arc_solver.suggest_connections(
                    workflow_id=workflow_id,
                    graph_data=graph_data,
                    task_context=context,
                    num_candidates=num_candidates,
                    min_score=min_score
                )

                # Format result
                result = {
                    "workflow_id": workflow_id,
                    "suggestions_count": len(arc_result.get("suggestions", [])),
                    "top_suggestions": arc_result.get("top_suggestions", []),
                    "stats": arc_result.get("stats", {}),
                    "timestamp": arc_result.get("timestamp", "")
                }

                duration_ms = (time.time() - start_time) * 1000
                await log_mcp_response(name, result, request_id, duration_ms)
                return [TextContent(type="text", text=format_arc_suggestions(result))]

            except Exception as e:
                return [TextContent(type="text", text=f"❌ Error generating ARC suggestions: {e}")]

        # ========================================================================
        # Phase 55.1: Session, Compound, and Workflow Tools
        # ========================================================================

        elif name == "vetka_session_init":
            # Initialize MCP session with fat context
            try:
                from src.mcp.tools.session_tools import vetka_session_init
                result = await vetka_session_init(**arguments)
                duration_ms = (time.time() - start_time) * 1000
                await log_mcp_response(name, result, request_id, duration_ms)
                return [TextContent(type="text", text=json.dumps(result, indent=2, ensure_ascii=False))]
            except Exception as e:
                return [TextContent(type="text", text=f"❌ Error in session_init: {e}")]

        elif name == "vetka_session_status":
            # Get current session status
            try:
                from src.mcp.tools.session_tools import vetka_session_status
                result = await vetka_session_status(**arguments)
                duration_ms = (time.time() - start_time) * 1000
                await log_mcp_response(name, result, request_id, duration_ms)
                return [TextContent(type="text", text=json.dumps(result, indent=2, ensure_ascii=False))]
            except Exception as e:
                return [TextContent(type="text", text=f"❌ Error in session_status: {e}")]

        elif name == "vetka_research":
            # Compound research tool
            try:
                from src.mcp.tools.compound_tools import vetka_research
                result = await vetka_research(**arguments)
                duration_ms = (time.time() - start_time) * 1000
                await log_mcp_response(name, result, request_id, duration_ms)
                return [TextContent(type="text", text=json.dumps(result, indent=2, ensure_ascii=False))]
            except Exception as e:
                return [TextContent(type="text", text=f"❌ Error in research: {e}")]

        elif name == "vetka_implement":
            # Compound implement tool
            try:
                from src.mcp.tools.compound_tools import vetka_implement
                result = await vetka_implement(**arguments)
                duration_ms = (time.time() - start_time) * 1000
                await log_mcp_response(name, result, request_id, duration_ms)
                return [TextContent(type="text", text=json.dumps(result, indent=2, ensure_ascii=False))]
            except Exception as e:
                return [TextContent(type="text", text=f"❌ Error in implement: {e}")]

        elif name == "vetka_review":
            # Compound review tool
            try:
                from src.mcp.tools.compound_tools import vetka_review
                result = await vetka_review(**arguments)
                duration_ms = (time.time() - start_time) * 1000
                await log_mcp_response(name, result, request_id, duration_ms)
                return [TextContent(type="text", text=json.dumps(result, indent=2, ensure_ascii=False))]
            except Exception as e:
                return [TextContent(type="text", text=f"❌ Error in review: {e}")]

        elif name == "vetka_execute_workflow":
            # Execute a workflow
            try:
                from src.mcp.tools.workflow_tools import vetka_execute_workflow
                result = await vetka_execute_workflow(**arguments)
                duration_ms = (time.time() - start_time) * 1000
                await log_mcp_response(name, result, request_id, duration_ms)
                return [TextContent(type="text", text=json.dumps(result, indent=2, ensure_ascii=False))]
            except Exception as e:
                return [TextContent(type="text", text=f"❌ Error in execute_workflow: {e}")]

        elif name == "vetka_workflow_status":
            # MARKER_102.21_START: Combined workflow + pipeline status
            # Get workflow status OR pipeline task status
            try:
                workflow_id = arguments.get("workflow_id", "")

                # Check if it's a pipeline task (starts with "task_")
                if workflow_id.startswith("task_"):
                    from src.orchestration.agent_pipeline import AgentPipeline
                    pipeline = AgentPipeline()
                    task_data = pipeline.get_task_status(workflow_id)

                    if task_data:
                        # Format pipeline task status
                        subtasks = task_data.get("subtasks", [])
                        completed = sum(1 for s in subtasks if s.get("status") == "done")
                        result_text = (
                            f"📋 Pipeline Task Status\n"
                            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                            f"ID: {workflow_id}\n"
                            f"Status: {task_data.get('status', 'unknown')}\n"
                            f"Phase: {task_data.get('phase_type', 'N/A')}\n"
                            f"Subtasks: {completed}/{len(subtasks)} completed\n\n"
                        )

                        for i, st in enumerate(subtasks, 1):
                            status_icon = "✅" if st.get("status") == "done" else "⏳" if st.get("status") == "executing" else "📋"
                            result_text += f"{status_icon} {i}. {st.get('description', 'N/A')[:60]}...\n"

                        return [TextContent(type="text", text=result_text)]
                    else:
                        return [TextContent(type="text", text=f"❌ Pipeline task not found: {workflow_id}")]

                # If no workflow_id, show recent pipeline tasks
                if not workflow_id:
                    from src.orchestration.agent_pipeline import AgentPipeline
                    pipeline = AgentPipeline()
                    recent = pipeline.get_recent_tasks(5)

                    if recent:
                        result_text = "📋 Recent Pipeline Tasks\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                        for task in recent:
                            status_icon = "✅" if task.get("status") == "done" else "⏳" if task.get("status") == "executing" else "❌"
                            result_text += f"{status_icon} {task.get('task_id')}: {task.get('task', 'N/A')[:40]}...\n"
                        return [TextContent(type="text", text=result_text)]

                # Fall back to original workflow status
                from src.mcp.tools.workflow_tools import vetka_workflow_status
                result = await vetka_workflow_status(**arguments)
                duration_ms = (time.time() - start_time) * 1000
                await log_mcp_response(name, result, request_id, duration_ms)
                return [TextContent(type="text", text=json.dumps(result, indent=2, ensure_ascii=False))]
            except Exception as e:
                return [TextContent(type="text", text=f"❌ Error in workflow_status: {e}")]
            # MARKER_102.21_END

        # MARKER_102.10_START: Agent Pipeline handler (fire-and-forget)
        elif name == "vetka_spawn_pipeline":
            # MARKER_102.19_START: Async fire-and-forget pipeline
            # Phase 102.2: Don't wait for completion - return task_id immediately
            # Pipeline runs in background, results saved to pipeline_tasks.json
            # MARKER_102.29: Added chat_id for progress streaming
            # MARKER_103.5: Added auto_write flag for staging mode
            try:
                from src.orchestration.agent_pipeline import AgentPipeline
                import time as time_module

                task = arguments.get("task", "")
                phase_type = arguments.get("phase_type", "research")
                chat_id = arguments.get("chat_id", MCP_LOG_GROUP_ID)  # Use MCP log group as default
                # MARKER_103.5: auto_write flag
                # True (default): Write files to disk immediately
                # False: Only save to JSON, use retro_apply_spawn.py later
                auto_write = arguments.get("auto_write", True)

                # Create pipeline with chat_id for progress streaming
                pipeline = AgentPipeline(chat_id=chat_id, auto_write=auto_write)
                task_id = f"task_{int(time_module.time())}"

                # Fire-and-forget: schedule execution without awaiting
                async def run_pipeline_background():
                    try:
                        await pipeline.execute(task, phase_type)
                        logger.info(f"[MCP] Pipeline {task_id} completed")
                    except Exception as e:
                        logger.error(f"[MCP] Pipeline {task_id} failed: {e}")

                # Schedule background execution
                asyncio.create_task(run_pipeline_background())

                # Return immediately with task_id
                mode_text = "Auto-write: ON (files created immediately)" if auto_write else "Staging mode: ON (use retro_apply_spawn.py)"
                response_text = (
                    f"🚀 Pipeline Started\n"
                    f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                    f"Task ID: {task_id}\n"
                    f"Phase: {phase_type}\n"
                    f"Task: {task[:80]}...\n"
                    f"Streaming to: {chat_id[:8]}...\n"
                    f"{mode_text}\n\n"
                    f"Pipeline running in background.\n"
                    f"Progress will stream to chat in real-time!\n"
                    f"Check status: vetka_workflow_status or read data/pipeline_tasks.json"
                )

                return [TextContent(type="text", text=response_text)]
            except Exception as e:
                logger.error(f"[MCP] vetka_spawn_pipeline error: {e}")
                return [TextContent(type="text", text=f"❌ Pipeline error: {e}")]
            # MARKER_102.19_END
        # MARKER_102.10_END

        # MARKER_108_4_MCP_REGISTER: Artifact tool handlers (Phase 108.4)
        elif name == "vetka_edit_artifact":
            # Edit artifact content via artifact scanner/service
            artifact_id = arguments.get("artifact_id", "")
            content = arguments.get("content", "")
            reason = arguments.get("reason", "Manual edit via MCP")

            # Direct file write to artifacts directory
            from pathlib import Path
            artifacts_dir = Path(__file__).parent.parent.parent / "artifacts"
            artifact_path = artifacts_dir / artifact_id

            try:
                if not artifact_path.exists():
                    return [TextContent(type="text", text=f"❌ Artifact not found: {artifact_id}")]

                # Write new content
                artifact_path.write_text(content, encoding='utf-8')

                response_text = (
                    f"✅ Artifact Edited\n"
                    f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                    f"Artifact: {artifact_id}\n"
                    f"Size: {len(content)} bytes\n"
                    f"Reason: {reason}\n"
                )
                return [TextContent(type="text", text=response_text)]
            except Exception as e:
                return [TextContent(type="text", text=f"❌ Error editing artifact: {e}")]

        elif name == "vetka_approve_artifact":
            # Approve artifact via approval service REST API
            artifact_id = arguments.get("artifact_id", "")
            reason = arguments.get("reason", "Approved via MCP")

            response = await http_client.post(
                f"/api/approvals/{artifact_id}/approve",
                json={"reason": reason}
            )

        elif name == "vetka_reject_artifact":
            # Reject artifact via approval service REST API
            artifact_id = arguments.get("artifact_id", "")
            feedback = arguments.get("feedback", "")

            response = await http_client.post(
                f"/api/approvals/{artifact_id}/reject",
                json={"reason": feedback}
            )

        elif name == "vetka_list_artifacts":
            # List artifacts by scanning artifacts directory
            status_filter = arguments.get("status", "all")
            limit = arguments.get("limit", 50)

            try:
                from src.services.artifact_scanner import scan_artifacts
                artifacts = scan_artifacts()

                # Filter by status if needed
                if status_filter != "all":
                    # Get approval status from approval service
                    approval_resp = await http_client.get("/api/approvals/pending")
                    if approval_resp.status_code == 200:
                        approval_data = approval_resp.json()
                        pending_ids = {req['id'] for req in approval_data.get('pending', [])}

                        # Filter based on status
                        if status_filter == "pending":
                            artifacts = [a for a in artifacts if a['id'] in pending_ids]
                        elif status_filter == "approved":
                            # Artifacts not in pending are considered approved/processed
                            artifacts = [a for a in artifacts if a['id'] not in pending_ids]
                        # rejected status would need additional tracking

                # Limit results
                artifacts = artifacts[:limit]

                # Format output
                artifact_list = []
                for art in artifacts:
                    meta = art.get('metadata', {})
                    artifact_list.append(
                        f"  - {art['id']}\n"
                        f"    Type: {meta.get('artifact_type', 'unknown')}\n"
                        f"    Language: {meta.get('language', 'unknown')}\n"
                        f"    Size: {meta.get('size_bytes', 0)} bytes\n"
                        f"    Status: {meta.get('status', 'unknown')}\n"
                        f"    Source: {meta.get('source_chat_id', 'unknown')[:8]}..."
                    )

                response_text = (
                    f"📦 Artifacts List (filter: {status_filter})\n"
                    f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                    f"Total: {len(artifacts)}\n\n"
                    + "\n\n".join(artifact_list)
                )

                return [TextContent(type="text", text=response_text)]
            except Exception as e:
                return [TextContent(type="text", text=f"❌ Error listing artifacts: {e}")]

        else:
            return [TextContent(
                type="text",
                text=f"Unknown tool: {name}"
            )]

        # Process response for standard tools
        if response.status_code == 200:
            data = response.json()
            duration_ms = (time.time() - start_time) * 1000

            # Log successful response to group chat
            await log_mcp_response(name, data, request_id, duration_ms)

            return [TextContent(
                type="text",
                text=format_result(name, data)
            )]
        else:
            error_text = f"Error: HTTP {response.status_code}\n{response.text}"
            duration_ms = (time.time() - start_time) * 1000

            # Log error response to group chat
            await log_mcp_response(name, None, request_id, duration_ms, error=error_text)

            return [TextContent(type="text", text=error_text)]

    except httpx.ConnectError:
        duration_ms = (time.time() - start_time) * 1000
        error_msg = "Error: Cannot connect to VETKA server at localhost:5001.\nMake sure VETKA is running: python main.py"

        # Log connection error to group chat
        await log_mcp_response(name, None, request_id, duration_ms, error=error_msg)

        return [TextContent(type="text", text=error_msg)]
    except Exception as e:
        duration_ms = (time.time() - start_time) * 1000
        error_msg = f"Error executing {name}: {str(e)}"

        # Log exception to group chat
        await log_mcp_response(name, None, request_id, duration_ms, error=error_msg)

        return [TextContent(type="text", text=error_msg)]


def format_result(tool_name: str, data: Any) -> str:
    """Format tool result for display"""

    # Special formatting for specific tools
    if tool_name == "vetka_search_semantic":
        if isinstance(data, dict):
            # FIX_101.2: REST API returns "files" not "results"
            results = data.get("files", data.get("results", []))
            if not results:
                return "No results found."

            formatted = f"Found {len(results)} results:\n\n"
            for i, result in enumerate(results, 1):
                # REST API returns flat structure with path/name/score
                file_path = result.get("path", result.get("metadata", {}).get("file_path", "unknown"))
                score = result.get("score", 0.0)
                name = result.get("name", "")

                formatted += f"{i}. [{name}] (score: {score:.2f})\n"
                formatted += f"   {file_path}\n\n"

            return formatted

    elif tool_name == "vetka_read_group_messages":
        if isinstance(data, dict):
            messages = data.get("messages", [])
            if not messages:
                return "No messages found in this group."

            formatted = f"📬 Group Messages ({len(messages)})\n"
            formatted += "=" * 40 + "\n\n"

            for i, msg in enumerate(messages, 1):
                sender = msg.get("sender_id", "unknown")
                content = msg.get("content", "")
                timestamp = msg.get("timestamp", "")
                msg_type = msg.get("message_type", "chat")

                # Truncate long messages
                display_content = content if len(content) <= 150 else content[:150] + "..."

                formatted += f"{i}. [{sender}] ({timestamp})\n"
                formatted += f"   Type: {msg_type}\n"
                formatted += f"   {display_content}\n\n"

            return formatted

    elif tool_name == "vetka_read_file":
        if isinstance(data, dict):
            content = data.get("content", "")
            if not content:
                return "File is empty or could not be read."
            return content

    elif tool_name == "vetka_health":
        if isinstance(data, dict):
            status = data.get("status", "unknown")
            version = data.get("version", "unknown")
            phase = data.get("phase", "unknown")
            components = data.get("components", {})

            formatted = f"VETKA Health Status\n"
            formatted += f"===================\n"
            formatted += f"Status: {status}\n"
            formatted += f"Version: {version}\n"
            formatted += f"Phase: {phase}\n\n"
            formatted += f"Components:\n"

            for comp_name, comp_status in components.items():
                status_icon = "✅" if comp_status else "❌"
                formatted += f"  {status_icon} {comp_name}\n"

            return formatted

    # Default: pretty-print JSON
    return json.dumps(data, indent=2, ensure_ascii=False)


def format_write_result(tool_name: str, result: dict) -> str:
    """Format write operation result"""
    if not result.get("success", False):
        error = result.get("error", "Unknown error")
        return f"❌ {tool_name} failed: {error}"

    data = result.get("result", {})
    status = data.get("status", "unknown")

    if status == "dry_run":
        # Preview mode
        lines = [
            "🔍 DRY RUN - Preview Only",
            "━" * 40,
        ]

        if tool_name == "vetka_edit_file":
            lines.extend([
                f"Path: {data.get('path', '?')}",
                f"Mode: {data.get('mode', 'write')}",
                f"File exists: {data.get('exists', False)}",
                f"Content length: {data.get('content_length', 0)} chars",
                "",
                "⚠️  Set dry_run=false to apply changes"
            ])
        elif tool_name == "vetka_git_commit":
            lines.extend([
                f"Message: {data.get('message', '?')}",
                f"Files: {', '.join(data.get('files', ['all changed']))}",
                "",
                "⚠️  Set dry_run=false to commit"
            ])

        return "\n".join(lines)

    elif status == "written":
        # File written
        return (
            f"✅ File Written\n"
            f"━{'━' * 39}\n"
            f"Path: {data.get('path', '?')}\n"
            f"Bytes: {data.get('bytes_written', 0)}\n"
            f"Backup: {data.get('backup', 'none')}"
        )

    elif status == "committed":
        # Git committed
        return (
            f"✅ Git Commit Created\n"
            f"━{'━' * 39}\n"
            f"Hash: {data.get('hash', '?')}\n"
            f"Message: {data.get('message', '?')}"
        )

    # Unknown status
    return json.dumps(data, indent=2)


def format_git_status(result: dict) -> str:
    """Format git status result"""
    if not result.get("success", False):
        return f"❌ Git error: {result.get('error', 'Unknown')}"

    data = result.get("result", {})
    files = data.get("files", {})

    lines = [
        "📊 Git Status",
        "━" * 40,
        f"Branch: {data.get('branch', '?')}",
        f"Last commit: {data.get('last_commit', '?')}",
        f"Clean: {'✅ Yes' if data.get('clean') else '❌ No'}",
        ""
    ]

    if files.get("staged"):
        lines.append(f"📦 Staged ({len(files['staged'])}):")
        for f in files["staged"][:10]:
            lines.append(f"   + {f}")
        if len(files["staged"]) > 10:
            lines.append(f"   ... and {len(files['staged']) - 10} more")
        lines.append("")

    if files.get("modified"):
        lines.append(f"📝 Modified ({len(files['modified'])}):")
        for f in files["modified"][:10]:
            lines.append(f"   M {f}")
        if len(files["modified"]) > 10:
            lines.append(f"   ... and {len(files['modified']) - 10} more")
        lines.append("")

    if files.get("untracked"):
        lines.append(f"❓ Untracked ({len(files['untracked'])}):")
        for f in files["untracked"][:10]:
            lines.append(f"   ? {f}")
        if len(files["untracked"]) > 10:
            lines.append(f"   ... and {len(files['untracked']) - 10} more")

    return "\n".join(lines)


def format_test_result(result: dict) -> str:
    """Format test execution result"""
    if not result.get("success", False):
        error = result.get("error", "Unknown error")
        return f"❌ Tests failed: {error}"

    data = result.get("result", {})
    passed = data.get("passed", False)
    returncode = data.get("returncode", 1)
    stdout = data.get("stdout", "")
    stderr = data.get("stderr", "")

    icon = "✅" if passed else "❌"
    status = "PASSED" if passed else "FAILED"

    lines = [
        f"{icon} Tests {status}",
        "━" * 40,
        f"Exit code: {returncode}",
        ""
    ]

    if stdout:
        lines.append("📋 Output:")
        lines.append(stdout[:3000])
        if len(stdout) > 3000:
            lines.append("... (truncated)")

    if stderr and not passed:
        lines.append("\n⚠️  Stderr:")
        lines.append(stderr[:1000])

    return "\n".join(lines)


def format_camera_result(result: dict, arguments: dict) -> str:
    """Format camera control result"""
    target = arguments.get("target", "overview")
    zoom = arguments.get("zoom", "medium")
    highlight = arguments.get("highlight", True)

    if result.get("success", False):
        return (
            f"📷 Camera Focus\n"
            f"━{'━' * 39}\n"
            f"Target: {target}\n"
            f"Zoom: {zoom}\n"
            f"Highlight: {'✅' if highlight else '❌'}\n"
            f"\n{result.get('message', 'Camera focused')}"
        )
    else:
        return (
            f"⚠️  Camera Control (UI Required)\n"
            f"━{'━' * 39}\n"
            f"Target: {target}\n"
            f"Zoom: {zoom}\n"
            f"\n{result.get('error', 'SocketIO not available')}\n"
            f"\nNote: Camera control requires active VETKA UI session.\n"
            f"Start the UI with 'npm run dev' in client/"
        )


def format_llm_result(result: dict) -> str:
    """Format LLM call result"""
    if not result.get("success", False):
        error = result.get("error", "Unknown error")
        return f"❌ LLM call failed: {error}"

    data = result.get("result", {})
    content = data.get("content", "")
    model = data.get("model", "unknown")
    provider = data.get("provider", "unknown")
    usage = data.get("usage", {})
    tool_calls = data.get("tool_calls")

    lines = [
        "🤖 LLM Response",
        "━" * 40,
        f"Model: {model}",
        f"Provider: {provider}",
    ]

    if usage:
        prompt_tokens = usage.get("prompt_tokens", 0)
        completion_tokens = usage.get("completion_tokens", 0)
        total_tokens = usage.get("total_tokens", 0)
        lines.append(f"Tokens: {prompt_tokens} → {completion_tokens} (total: {total_tokens})")

    lines.append("")
    lines.append("📝 Content:")
    lines.append(content)

    if tool_calls:
        lines.append("")
        lines.append(f"🔧 Tool Calls ({len(tool_calls)}):")
        for i, tc in enumerate(tool_calls, 1):
            func = tc.get("function", {})
            lines.append(f"  {i}. {func.get('name', 'unknown')}")

    return "\n".join(lines)


# ============================================================================
# MEMORY TOOL FORMATTERS (Phase 93.6)
# ============================================================================

def format_context_result(result: dict) -> str:
    """Format conversation context result"""
    lines = [
        "📜 Conversation Context",
        "━" * 40,
        f"Messages: {result.get('original_messages', 0)}",
        f"Compression: {'✅ ELISION' if result.get('compression_applied') else '❌ Raw'}",
    ]

    if result.get("compression_applied"):
        lines.append(f"Savings: {result.get('savings_estimate', 'N/A')}")

    lines.append("")
    lines.append("Context:")

    context = result.get("context", {})
    if isinstance(context, dict):
        # Compressed context
        lines.append(json.dumps(context, indent=2, ensure_ascii=False)[:2000])
    elif isinstance(context, list):
        # Raw messages
        for msg in context[:5]:
            sender = msg.get("sender_id", "?")
            content = msg.get("content", "")[:100]
            lines.append(f"  [{sender}]: {content}...")
        if len(context) > 5:
            lines.append(f"  ... and {len(context) - 5} more messages")

    return "\n".join(lines)


def format_preferences_result(result: dict) -> str:
    """Format user preferences result"""
    lines = [
        "👤 User Preferences",
        "━" * 40,
        f"User: {result.get('user_id', '?')}",
        f"Category: {result.get('category', 'all')}",
        f"Source: {result.get('source', 'unknown')}",
        ""
    ]

    prefs = result.get("preferences", {})
    if prefs:
        lines.append("Preferences:")
        for key, value in list(prefs.items())[:10]:
            if isinstance(value, dict):
                lines.append(f"  {key}:")
                for k, v in list(value.items())[:3]:
                    lines.append(f"    {k}: {v}")
            else:
                lines.append(f"  {key}: {value}")
    else:
        lines.append("No preferences found.")

    return "\n".join(lines)


def format_memory_summary(result: dict) -> str:
    """Format memory system summary"""
    lines = [
        "🧠 Memory Summary",
        "━" * 40,
        f"System: {result.get('memory_system', 'CAM + Elisium')}",
        ""
    ]

    stats = result.get("stats")
    if stats:
        lines.append("Compression Schedule:")
        schedule = stats.get("compression_schedule", [])
        for item in schedule:
            lines.append(f"  {item['days']}: {item['dim']}D ({item['quality']})")

        lines.append("")
        lines.append(f"Active Nodes: {stats.get('active_nodes', 'N/A')}")
        lines.append(f"Archived Nodes: {stats.get('archived_nodes', 'N/A')}")
        lines.append(f"Total Embeddings: {stats.get('total_embeddings', 'N/A')}")

    nodes = result.get("nodes")
    if nodes:
        lines.append("")
        lines.append(f"Sample Nodes ({len(nodes)}):")
        for node in nodes[:5]:
            lines.append(f"  - {node.get('path', '?')} ({node.get('embedding_dim', '?')}D)")

    return "\n".join(lines)


def format_arc_suggestions(result: dict) -> str:
    """Format ARC suggestions result (Phase 95)"""
    lines = [
        "🔮 ARC Workflow Suggestions",
        "━" * 40,
        f"Workflow: {result.get('workflow_id', '?')}",
        f"Total Suggestions: {result.get('suggestions_count', 0)}",
        ""
    ]

    top_suggestions = result.get("top_suggestions", [])
    if top_suggestions:
        lines.append("Top Suggestions:")
        for i, suggestion in enumerate(top_suggestions, 1):
            suggestion_type = suggestion.get("type", "transformation")
            score = suggestion.get("score", 0.0)
            explanation = suggestion.get("explanation", "No explanation")
            success = suggestion.get("success", False)

            # Format: rank, type, score, explanation
            status_icon = "✅" if success else "⚠️"
            lines.append(f"\n{i}. {status_icon} {suggestion_type.upper()} (score: {score:.2f})")
            lines.append(f"   {explanation}")

            # Show code snippet if available and short enough
            code = suggestion.get("code", "")
            if code and len(code) < 200:
                lines.append(f"   Code: {code[:100]}...")
    else:
        lines.append("No suggestions generated.")

    # Add stats if available
    stats = result.get("stats", {})
    if stats:
        lines.append("")
        lines.append("Statistics:")
        lines.append(f"  Generated: {stats.get('total_generated', 0)}")
        lines.append(f"  Tested: {stats.get('total_tested', 0)}")
        lines.append(f"  Successful: {stats.get('total_successful', 0)}")
        lines.append(f"  Avg Score: {stats.get('avg_score', 0.0):.2f}")

    return "\n".join(lines)


# MARKER_108_3: Chat digest formatter
def format_chat_digest(result: dict) -> str:
    """Format chat digest result (Phase 108.3)"""
    if result.get("error"):
        return f"❌ Error: {result['error']}"

    lines = [
        "💬 Chat Digest",
        "━" * 40,
        f"Chat ID: {result.get('chat_id', '?')[:16]}...",
        f"Context: {result.get('context_type', 'file')}",
        f"File: {result.get('file_path', 'unknown')}",
        f"Total Messages: {result.get('total_messages', 0)}",
        ""
    ]

    # Summary
    summary = result.get("summary", "")
    if summary:
        lines.append("Summary:")
        lines.append(f"  {summary}")
        lines.append("")

    # Recent messages
    recent_messages = result.get("recent_messages", [])
    if recent_messages:
        lines.append(f"Recent Messages ({len(recent_messages)}):")
        for i, msg in enumerate(recent_messages[-5:], 1):  # Show last 5
            role = msg.get("role", "?")
            sender = msg.get("sender", role)
            content = msg.get("content", "")[:100]
            timestamp = msg.get("timestamp", "")[:19] if msg.get("timestamp") else ""

            role_icon = "👤" if role == "user" else "🤖" if role == "assistant" else "⚙️"
            lines.append(f"  {i}. {role_icon} [{sender}] {timestamp}")
            lines.append(f"     {content}...")
        lines.append("")

    # Agent logs
    agent_logs = result.get("agent_logs", [])
    if agent_logs:
        lines.append(f"Agent Logs ({len(agent_logs)}):")
        for i, log in enumerate(agent_logs[:3], 1):  # Show first 3
            sender = log.get("sender", "unknown")
            content = log.get("content", "")
            log_type = log.get("type", "chat")

            lines.append(f"  {i}. [{sender}] ({log_type})")
            lines.append(f"     {content}...")
        if len(agent_logs) > 3:
            lines.append(f"  ... and {len(agent_logs) - 3} more")

    return "\n".join(lines)


# MARKER_102.11_START: Pipeline result formatter
def format_pipeline_result(result: dict) -> str:
    """Format agent pipeline result (Phase 102)"""
    status = result.get("status", "unknown")
    status_icons = {
        "pending": "⏳",
        "planning": "📋",
        "executing": "🔄",
        "done": "✅",
        "failed": "❌"
    }
    icon = status_icons.get(status, "❓")

    lines = [
        f"{icon} Agent Pipeline Result",
        "━" * 40,
        f"Task ID: {result.get('task_id', '?')}",
        f"Status: {status}",
        f"Phase Type: {result.get('phase_type', '?')}",
        f"Task: {result.get('task', '?')[:80]}...",
        ""
    ]

    # Subtasks summary
    subtasks = result.get("subtasks", [])
    if subtasks:
        done_count = len([s for s in subtasks if s.get("status") == "done"])
        lines.append(f"Subtasks: {done_count}/{len(subtasks)} completed")
        lines.append("")

        for i, st in enumerate(subtasks[:5], 1):  # Show first 5
            st_status = st.get("status", "?")
            st_icon = "✅" if st_status == "done" else "🔄" if st_status == "executing" else "🔍" if st_status == "researching" else "⏳"
            desc = st.get("description", "?")[:50]
            lines.append(f"  {i}. {st_icon} {desc}")

            # Show research insights if available
            if st.get("context") and st["context"].get("insights"):
                for insight in st["context"]["insights"][:2]:
                    lines.append(f"      💡 {insight[:60]}")

        if len(subtasks) > 5:
            lines.append(f"  ... and {len(subtasks) - 5} more")

    # Results summary
    results = result.get("results", {})
    if results:
        lines.append("")
        if results.get("error"):
            lines.append(f"Error: {results['error']}")
        else:
            lines.append(f"Execution order: {results.get('execution_order', '?')}")
            complexity = results.get("plan", {}).get("estimated_complexity", "?")
            lines.append(f"Complexity: {complexity}")

    return "\n".join(lines)
# MARKER_102.11_END


# ============================================================================
# MAIN
# ============================================================================

# MARKER_106a_3: Graceful shutdown handler
_shutdown_event = asyncio.Event()

def signal_handler(signum, frame):
    print(f"[MCP] Received signal {signum}, initiating shutdown...", file=sys.stderr)
    _shutdown_event.set()

async def graceful_shutdown():
    """Cleanup all resources on shutdown"""
    print("[MCP] Shutting down...", file=sys.stderr)

    try:
        # Stop all actors
        from src.mcp.mcp_actor import get_dispatcher
        await get_dispatcher().cleanup_all()
    except ImportError:
        pass
    except Exception as e:
        print(f"[MCP] Actor cleanup error: {e}", file=sys.stderr)

    try:
        # Close client pools
        from src.mcp.client_pool import get_pool_manager
        await get_pool_manager().shutdown()
    except ImportError:
        pass
    except Exception as e:
        print(f"[MCP] Pool cleanup error: {e}", file=sys.stderr)

    # Close main client
    await cleanup_client()

    print("[MCP] Shutdown complete", file=sys.stderr)


# MARKER_106a_4: Enhanced main with HTTP/WS/stdio modes
async def main():
    """Run the MCP server with multi-transport support"""
    args = parse_args()

    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    session_id = await init_client(session_id=args.session_id)
    print(f"[MCP] Started with session_id={session_id[:8]}...", file=sys.stderr)

    try:
        if args.http or args.ws:
            # HTTP/WS mode - use enhanced MCP server
            from src.mcp.vetka_mcp_server import run_http
            print(f"[MCP] Starting HTTP server on port {args.port} (WS={args.ws})", file=sys.stderr)
            await run_http(port=args.port, enable_ws=args.ws)
        else:
            # stdio mode - original behavior
            print("[MCP] Starting stdio mode", file=sys.stderr)
            async with stdio_server() as (read_stream, write_stream):
                init_options = server.create_initialization_options()

                server_task = asyncio.create_task(
                    server.run(read_stream, write_stream, init_options)
                )
                shutdown_task = asyncio.create_task(_shutdown_event.wait())

                done, pending = await asyncio.wait(
                    [server_task, shutdown_task],
                    return_when=asyncio.FIRST_COMPLETED
                )

                for task in pending:
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        pass

    finally:
        await graceful_shutdown()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        sys.exit(0)
