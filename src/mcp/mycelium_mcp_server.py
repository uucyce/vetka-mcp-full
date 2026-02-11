#!/usr/bin/env python3
"""MYCELIUM MCP Server — Autonomous Pipeline MCP for VETKA.

MARKER_129.6: Second MCP server handling heavy/async pipeline tools.
Runs alongside MCP VETKA (which handles fast stateless tools).

Architecture:
- MCP stdio protocol (JSON-RPC over stdin/stdout) — same as vetka_mcp_bridge.py
- 17 tools with mycelium_* namespace (pipelines, tasks, workflows, LLM calls)
- Native async: no ThreadPoolExecutor, no asyncio.run() hacks
- WebSocket broadcaster on port 8082 for DevPanel real-time updates
- HTTP client for VETKA API callbacks (chat relay, board notify)

Tools:
  Pipeline:     mycelium_pipeline, mycelium_call_model
  Task Board:   mycelium_task_board, mycelium_task_dispatch, mycelium_task_import
  Heartbeat:    mycelium_heartbeat_tick, mycelium_heartbeat_status
  Workflow:     mycelium_execute_workflow, mycelium_workflow_status
  Compound:     mycelium_research, mycelium_implement, mycelium_review
  Artifacts:    mycelium_list_artifacts, mycelium_approve_artifact, mycelium_reject_artifact
  System:       mycelium_health, mycelium_devpanel_stream

Usage:
  # Register in Claude Code alongside vetka:
  claude mcp add mycelium -- python /path/to/mycelium_mcp_server.py

  # Or in .mcp.json:
  {
    "mcpServers": {
      "mycelium": {
        "command": "python3",
        "args": ["/path/to/mycelium_mcp_server.py"],
        "env": {"MYCELIUM_WS_PORT": "8082"}
      }
    }
  }

@status: active
@phase: 129
@depends: mcp.server, mcp.types, src.mcp.tools (base_async_tool, llm_call_tool_async, task_board_tools, compound_tools, workflow_tools, artifact_tools), src.mcp.mycelium_http_client, src.mcp.mycelium_ws_server, src.orchestration (agent_pipeline, mycelium_heartbeat)
@used_by: Claude Code, Claude Desktop (via MCP stdio protocol)
"""

# Ensure project root in path
import sys
import os
_project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

import asyncio
import json
import signal
import time
import logging
from pathlib import Path
from typing import Any, Dict, Optional

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

# MARKER_129.6: Logging
logging.basicConfig(level=logging.INFO, format='[MYCELIUM] %(message)s')
logger = logging.getLogger(__name__)

# ============================================================
# Server instance
# ============================================================
server = Server("mycelium")

# Global state
_start_time = time.time()
_shutdown_event = asyncio.Event()
_active_pipelines: Dict[str, asyncio.Task] = {}
_http_client = None
_ws_broadcaster = None


# ============================================================
# Lazy component init
# ============================================================
async def _get_http_client():
    """Lazy init HTTP client for VETKA API callbacks."""
    global _http_client
    if _http_client is None:
        from src.mcp.mycelium_http_client import get_mycelium_client
        _http_client = get_mycelium_client()
        await _http_client.start()
    return _http_client


async def _get_ws_broadcaster():
    """Lazy init WebSocket broadcaster for DevPanel."""
    global _ws_broadcaster
    if _ws_broadcaster is None:
        try:
            from src.mcp.mycelium_ws_server import get_ws_broadcaster
            _ws_broadcaster = get_ws_broadcaster()
            await _ws_broadcaster.start()
            logger.info(f"WebSocket broadcaster started on port {_ws_broadcaster.port}")
        except ImportError:
            logger.warning("websockets not installed — DevPanel WS disabled")
        except Exception as e:
            logger.warning(f"WebSocket broadcaster failed to start: {e}")
    return _ws_broadcaster


# ============================================================
# Tool definitions — 17 tools
# ============================================================
MYCELIUM_TOOLS = [
    # --- Pipeline ---
    Tool(
        name="mycelium_pipeline",
        description="Mycelium agent pipeline for fractal task execution. "
                    "Auto-triggers researcher on unclear parts. "
                    "Phases: research (explore), fix (debug), build (implement). "
                    "Progress streams to chat + DevPanel WebSocket in real-time. "
                    "NON-BLOCKING: returns immediately, pipeline runs in background.",
        inputSchema={
            "type": "object",
            "properties": {
                "task": {"type": "string", "description": "Task description"},
                "phase_type": {"type": "string", "description": "Pipeline phase: research, fix, build"},
                "preset": {"type": "string", "description": "Team preset: dragon_bronze, dragon_silver, dragon_gold"},
                "provider": {"type": "string", "description": "LLM provider override"},
                "chat_id": {"type": "string", "description": "Chat ID for progress streaming"},
                "auto_write": {"type": "boolean", "description": "Auto-write files (false=staging mode)"},
            },
            "required": ["task"],
        },
    ),
    Tool(
        name="mycelium_call_model",
        description="Call any LLM model through MYCELIUM async infrastructure "
                    "(Grok, GPT, Claude, Gemini, Ollama). Native async — never blocks. "
                    "Supports function calling for compatible models.",
        inputSchema={
            "type": "object",
            "properties": {
                "model": {"type": "string", "description": "Model name (e.g., grok-4, gpt-4o, claude-sonnet)"},
                "messages": {"type": "array", "description": "Chat messages [{role, content}]"},
                "temperature": {"type": "number", "description": "Temperature 0-2"},
                "max_tokens": {"type": "number", "description": "Max response tokens"},
                "model_source": {"type": "string", "description": "Provider: polza, openai, anthropic, google, ollama"},
                "inject_context": {"type": "object", "description": "Context injection config"},
                "tools": {"type": "array", "description": "Function calling tools"},
            },
            "required": ["model", "messages"],
        },
    ),
    # --- Task Board ---
    Tool(
        name="mycelium_task_board",
        description="Manage Task Board: add/list/get/update/remove/summary. "
                    "Priority queue for pipeline dispatch.",
        inputSchema={
            "type": "object",
            "properties": {
                "action": {"type": "string", "description": "Action: add, list, get, update, remove, summary"},
                "title": {"type": "string"}, "description": {"type": "string"},
                "priority": {"type": "number"}, "phase_type": {"type": "string"},
                "complexity": {"type": "string"}, "preset": {"type": "string"},
                "tags": {"type": "array"}, "dependencies": {"type": "array"},
                "task_id": {"type": "string"}, "status": {"type": "string"},
                "filter_status": {"type": "string"},
            },
            "required": ["action"],
        },
    ),
    Tool(
        name="mycelium_task_dispatch",
        description="Dispatch tasks from Task Board to pipeline. "
                    "If task_id given, dispatches that task. Otherwise picks highest-priority pending task.",
        inputSchema={
            "type": "object",
            "properties": {
                "task_id": {"type": "string", "description": "Specific task ID to dispatch"},
                "chat_id": {"type": "string", "description": "Chat ID for progress"},
            },
        },
    ),
    Tool(
        name="mycelium_task_import",
        description="Import tasks from a todo text file into the Task Board. "
                    "Auto-detects priority and phase_type from content.",
        inputSchema={
            "type": "object",
            "properties": {
                "file_path": {"type": "string", "description": "Path to todo file"},
                "source_tag": {"type": "string", "description": "Tag for imported tasks"},
            },
            "required": ["file_path"],
        },
    ),
    # --- Heartbeat ---
    Tool(
        name="mycelium_heartbeat_tick",
        description="Execute one heartbeat tick: read new messages from group chat, "
                    "parse task triggers (@dragon, /task, /fix, /build, /research), "
                    "dispatch via pipeline.",
        inputSchema={
            "type": "object",
            "properties": {
                "group_id": {"type": "string", "description": "Group chat ID to monitor"},
                "dry_run": {"type": "boolean", "description": "Preview tasks without executing"},
            },
        },
    ),
    Tool(
        name="mycelium_heartbeat_status",
        description="Get Heartbeat Engine status: last tick, total ticks, "
                    "tasks dispatched/completed/failed.",
        inputSchema={"type": "object", "properties": {}},
    ),
    # --- Task Tracker ---
    Tool(
        name="mycelium_track_done",
        description="Mark a task as completed. Updates project digest + tracker. "
                    "Use for any agent: dragon, cursor, opus, titan.",
        inputSchema={
            "type": "object",
            "properties": {
                "marker": {"type": "string", "description": "Task marker (e.g. C33E, MARKER_133.FIX1)"},
                "description": {"type": "string", "description": "What was done"},
                "source": {"type": "string", "description": "Who did it: cursor, dragon, opus, titan"},
                "files_changed": {"type": "array", "description": "List of changed file paths"},
            },
            "required": ["marker", "description"],
        },
    ),
    Tool(
        name="mycelium_track_started",
        description="Mark a task as started. Any agent can call this.",
        inputSchema={
            "type": "object",
            "properties": {
                "task_id": {"type": "string", "description": "Task ID or marker"},
                "title": {"type": "string", "description": "Task title"},
                "source": {"type": "string", "description": "Who started: cursor, dragon, opus"},
            },
            "required": ["task_id", "title"],
        },
    ),
    Tool(
        name="mycelium_tracker_status",
        description="Get task tracker status: in-progress tasks, completed count, last completed, digest headline.",
        inputSchema={"type": "object", "properties": {}},
    ),
    # --- Workflow ---
    Tool(
        name="mycelium_execute_workflow",
        description="Execute full VETKA workflow. Types: pm_to_qa, pm_only, dev_qa.",
        inputSchema={
            "type": "object",
            "properties": {
                "request": {"type": "string", "description": "Workflow request"},
                "workflow_type": {"type": "string", "description": "pm_to_qa, pm_only, dev_qa"},
                "include_eval": {"type": "boolean"}, "timeout": {"type": "number"},
            },
            "required": ["request"],
        },
    ),
    Tool(
        name="mycelium_workflow_status",
        description="Get status of a workflow execution by workflow ID.",
        inputSchema={
            "type": "object",
            "properties": {
                "workflow_id": {"type": "string", "description": "Workflow ID"},
            },
            "required": ["workflow_id"],
        },
    ),
    # --- Compound ---
    Tool(
        name="mycelium_research",
        description="Research a topic: semantic search → read files → summarize.",
        inputSchema={
            "type": "object",
            "properties": {
                "topic": {"type": "string", "description": "Research topic"},
                "depth": {"type": "string", "description": "quick, medium, deep"},
            },
            "required": ["topic"],
        },
    ),
    Tool(
        name="mycelium_implement",
        description="Plan implementation for a task (use workflow for execution).",
        inputSchema={
            "type": "object",
            "properties": {
                "task": {"type": "string", "description": "Task to plan"},
                "dry_run": {"type": "boolean"},
            },
            "required": ["task"],
        },
    ),
    Tool(
        name="mycelium_review",
        description="Review a file and suggest improvements.",
        inputSchema={
            "type": "object",
            "properties": {
                "file_path": {"type": "string", "description": "File to review"},
            },
            "required": ["file_path"],
        },
    ),
    # --- Artifacts ---
    Tool(
        name="mycelium_list_artifacts",
        description="List artifacts by status (pending, approved, rejected, all).",
        inputSchema={
            "type": "object",
            "properties": {
                "status": {"type": "string", "description": "Filter: pending, approved, rejected, all"},
                "limit": {"type": "number"},
            },
        },
    ),
    Tool(
        name="mycelium_approve_artifact",
        description="Approve an artifact for deployment/integration.",
        inputSchema={
            "type": "object",
            "properties": {
                "artifact_id": {"type": "string", "description": "Artifact ID"},
                "reason": {"type": "string"},
            },
            "required": ["artifact_id"],
        },
    ),
    Tool(
        name="mycelium_reject_artifact",
        description="Reject an artifact with feedback.",
        inputSchema={
            "type": "object",
            "properties": {
                "artifact_id": {"type": "string", "description": "Artifact ID"},
                "feedback": {"type": "string", "description": "Rejection feedback"},
            },
            "required": ["artifact_id"],
        },
    ),
    # --- System ---
    Tool(
        name="mycelium_health",
        description="MYCELIUM health check: uptime, active pipelines, WS clients, VETKA connectivity.",
        inputSchema={"type": "object", "properties": {}},
    ),
    Tool(
        name="mycelium_devpanel_stream",
        description="Get DevPanel WebSocket broadcaster info: connected clients, port, status.",
        inputSchema={"type": "object", "properties": {}},
    ),
]


# ============================================================
# list_tools handler
# ============================================================
@server.list_tools()
async def list_tools() -> list[Tool]:
    """Return all 17 MYCELIUM tools."""
    return MYCELIUM_TOOLS


# ============================================================
# Tool handlers
# ============================================================
async def _handle_pipeline(arguments: Dict[str, Any]) -> str:
    """Fire-and-forget pipeline — returns immediately, runs in background."""
    import uuid
    task = arguments.get("task", "")
    chat_id = arguments.get("chat_id")
    preset = arguments.get("preset", "dragon_silver")
    phase_type = arguments.get("phase_type", "build")
    provider = arguments.get("provider")
    # MARKER_133.FIX2: Default auto_write=True — Dragon writes real code
    auto_write = arguments.get("auto_write", True)

    task_id = f"myc_{uuid.uuid4().hex[:8]}"

    # MARKER_135.BREADCRUMB: File-based pipeline status for debugging
    import time as _time
    _breadcrumb_dir = Path(__file__).resolve().parent.parent.parent / "data" / "feedback" / "pipeline_runs"
    _breadcrumb_dir.mkdir(parents=True, exist_ok=True)
    _breadcrumb_file = _breadcrumb_dir / f"{task_id}.json"

    def _write_breadcrumb(status: str, detail: str = ""):
        """Write pipeline status breadcrumb to file for debugging."""
        try:
            import json as _json
            _breadcrumb_file.write_text(_json.dumps({
                "task_id": task_id, "status": status,
                "task": task[:200], "preset": preset,
                "detail": detail[:500],
                "ts": _time.strftime("%Y-%m-%dT%H:%M:%SZ", _time.gmtime()),
            }, indent=2))
        except Exception:
            pass

    async def _run():
        http_client = await _get_http_client()
        ws_broadcaster = await _get_ws_broadcaster()
        _write_breadcrumb("started", f"http_client={'yes' if http_client else 'no'}, ws={'yes' if ws_broadcaster else 'no'}")
        try:
            from src.orchestration.agent_pipeline import AgentPipeline
            pipeline = AgentPipeline(
                chat_id=chat_id,
                auto_write=auto_write,
                provider=provider,
                preset=preset,
                async_mode=True,  # MARKER_129.6: Native async
                http_client=http_client,
                ws_broadcaster=ws_broadcaster,
            )
            _write_breadcrumb("pipeline_created")

            # Notify start
            if ws_broadcaster:
                await ws_broadcaster.broadcast_pipeline_activity(
                    role="system",
                    message=f"Pipeline started: {task[:80]}",
                    task_id=task_id,
                    preset=preset,
                )

            result = await pipeline.execute(task, phase_type=phase_type)
            _write_breadcrumb("completed", str(result)[:500] if result else "no result")

            # Notify completion
            if ws_broadcaster:
                await ws_broadcaster.broadcast({
                    "type": "pipeline_complete",
                    "task_id": task_id,
                    "success": True,
                    "summary": str(result)[:500] if result else "completed",
                })
            if http_client:
                await http_client.notify_board_update("pipeline_complete", f"Pipeline {task_id} completed")

        except Exception as e:
            logger.error(f"Pipeline {task_id} failed: {e}", exc_info=True)
            _write_breadcrumb("failed", f"{type(e).__name__}: {e}")
            if ws_broadcaster:
                await ws_broadcaster.broadcast({
                    "type": "pipeline_failed",
                    "task_id": task_id,
                    "error": str(e)[:300],
                })
        finally:
            _active_pipelines.pop(task_id, None)

    # Fire-and-forget
    bg_task = asyncio.create_task(_run())
    _active_pipelines[task_id] = bg_task

    return json.dumps({
        "success": True,
        "task_id": task_id,
        "status": "dispatched",
        "message": f"Pipeline running in background (preset={preset}, phase={phase_type})",
        "note": "Non-blocking. Progress streams to DevPanel WebSocket (ws://localhost:8082) and chat.",
    })


async def _handle_call_model(arguments: Dict[str, Any]) -> str:
    """Native async LLM call — the core Phase 129 fix."""
    from src.mcp.tools.llm_call_tool_async import LLMCallToolAsync
    tool = LLMCallToolAsync()
    result = await tool.execute(arguments)
    return json.dumps(result, default=str)


async def _handle_task_board(arguments: Dict[str, Any]) -> str:
    """Task Board CRUD — delegates to existing handler."""
    from src.mcp.tools.task_board_tools import handle_task_board
    result = handle_task_board(arguments)
    return json.dumps(result, default=str)


async def _handle_task_dispatch(arguments: Dict[str, Any]) -> str:
    """Dispatch from Task Board — async."""
    from src.mcp.tools.task_board_tools import handle_task_dispatch
    result = await handle_task_dispatch(arguments)
    return json.dumps(result, default=str)


async def _handle_task_import(arguments: Dict[str, Any]) -> str:
    """Import tasks from todo file."""
    from src.mcp.tools.task_board_tools import handle_task_import
    result = handle_task_import(arguments)
    return json.dumps(result, default=str)


async def _handle_heartbeat_tick(arguments: Dict[str, Any]) -> str:
    """Heartbeat tick — scan chat for task triggers."""
    from src.orchestration.mycelium_heartbeat import heartbeat_tick
    group_id = arguments.get("group_id")
    dry_run = arguments.get("dry_run", False)
    kwargs = {"dry_run": dry_run}
    if group_id:
        kwargs["group_id"] = group_id
    result = heartbeat_tick(**kwargs)
    return json.dumps(result, default=str)


async def _handle_heartbeat_status(arguments: Dict[str, Any]) -> str:
    """Heartbeat engine status."""
    from src.orchestration.mycelium_heartbeat import get_heartbeat_status
    result = get_heartbeat_status()
    return json.dumps(result, default=str)


async def _handle_execute_workflow(arguments: Dict[str, Any]) -> str:
    """Execute VETKA workflow (PM→Architect→Dev→QA)."""
    from src.mcp.tools.workflow_tools import vetka_execute_workflow
    result = await vetka_execute_workflow(
        request=arguments.get("request", ""),
        workflow_type=arguments.get("workflow_type", "pm_to_qa"),
        include_eval=arguments.get("include_eval", True),
        timeout=arguments.get("timeout", 300),
    )
    return json.dumps(result, default=str)


async def _handle_workflow_status(arguments: Dict[str, Any]) -> str:
    """Get workflow execution status."""
    from src.mcp.tools.workflow_tools import vetka_workflow_status
    result = await vetka_workflow_status(
        workflow_id=arguments.get("workflow_id", ""),
    )
    return json.dumps(result, default=str)


async def _handle_research(arguments: Dict[str, Any]) -> str:
    """Compound research: semantic search → read → summarize."""
    from src.mcp.tools.compound_tools import vetka_research
    result = await vetka_research(
        topic=arguments.get("topic", ""),
        depth=arguments.get("depth", "medium"),
    )
    return json.dumps(result, default=str)


async def _handle_implement(arguments: Dict[str, Any]) -> str:
    """Plan implementation for a task."""
    from src.mcp.tools.compound_tools import vetka_implement
    result = await vetka_implement(
        task=arguments.get("task", ""),
        dry_run=arguments.get("dry_run", True),
    )
    return json.dumps(result, default=str)


async def _handle_review(arguments: Dict[str, Any]) -> str:
    """Review a file."""
    from src.mcp.tools.compound_tools import vetka_review
    result = await vetka_review(
        file_path=arguments.get("file_path", ""),
    )
    return json.dumps(result, default=str)


async def _handle_list_artifacts(arguments: Dict[str, Any]) -> str:
    """List artifacts by status."""
    from src.mcp.tools.artifact_tools import ListArtifactsTool
    tool = ListArtifactsTool()
    result = tool.execute({
        "status_filter": arguments.get("status", "all"),
    })
    return json.dumps(result, default=str)


async def _handle_approve_artifact(arguments: Dict[str, Any]) -> str:
    """Approve an artifact."""
    from src.mcp.tools.artifact_tools import ApproveArtifactTool
    tool = ApproveArtifactTool()
    result = tool.execute({
        "artifact_id": arguments.get("artifact_id", ""),
    })
    return json.dumps(result, default=str)


async def _handle_reject_artifact(arguments: Dict[str, Any]) -> str:
    """Reject an artifact with feedback."""
    from src.mcp.tools.artifact_tools import RejectArtifactTool
    tool = RejectArtifactTool()
    result = tool.execute({
        "artifact_id": arguments.get("artifact_id", ""),
        "feedback": arguments.get("feedback", ""),
    })
    return json.dumps(result, default=str)


async def _handle_health(arguments: Dict[str, Any]) -> str:
    """MYCELIUM health: uptime, pipelines, WS, VETKA connectivity."""
    uptime = time.time() - _start_time

    # Check VETKA connectivity
    vetka_ok = False
    try:
        http_client = await _get_http_client()
        vetka_ok = await http_client.check_vetka_health()
    except Exception:
        pass

    # WS status
    ws_status = None
    if _ws_broadcaster:
        ws_status = _ws_broadcaster.get_status()

    return json.dumps({
        "success": True,
        "server": "mycelium",
        "uptime_seconds": round(uptime, 1),
        "uptime_human": f"{int(uptime // 3600)}h {int((uptime % 3600) // 60)}m {int(uptime % 60)}s",
        "active_pipelines": len(_active_pipelines),
        "pipeline_ids": list(_active_pipelines.keys()),
        "vetka_connected": vetka_ok,
        "websocket": ws_status,
        "version": "129.6",
    })


async def _handle_devpanel_stream(arguments: Dict[str, Any]) -> str:
    """DevPanel WebSocket broadcaster info."""
    if _ws_broadcaster:
        status = _ws_broadcaster.get_status()
        return json.dumps({"success": True, **status})
    else:
        return json.dumps({
            "success": True,
            "running": False,
            "message": "WebSocket broadcaster not initialized. Will start on first pipeline.",
        })


# ============================================================
# MARKER_133.TRACKER_MCP: Task tracker handlers
# ============================================================

async def _handle_track_done(arguments: Dict[str, Any]) -> str:
    """Mark task as completed — any agent can call."""
    from src.services.task_tracker import on_cursor_task_completed, on_task_completed
    marker = arguments.get("marker", "unknown")
    description = arguments.get("description", "")
    source = arguments.get("source", "mcp")
    files_changed = arguments.get("files_changed", [])

    if source == "cursor":
        await on_cursor_task_completed(marker, description, files_changed)
    else:
        await on_task_completed(
            task_id=marker,
            task_title=description,
            status="done",
            source=source,
        )
    return json.dumps({"success": True, "marker": marker, "source": source, "tracked": True})


async def _handle_track_started(arguments: Dict[str, Any]) -> str:
    """Mark task as started."""
    from src.services.task_tracker import on_task_started
    on_task_started(
        task_id=arguments.get("task_id", "unknown"),
        task_title=arguments.get("title", ""),
        source=arguments.get("source", "unknown"),
    )
    return json.dumps({"success": True, "started": True})


async def _handle_tracker_status(arguments: Dict[str, Any]) -> str:
    """Get tracker status for DevPanel."""
    from src.services.task_tracker import get_tracker_status
    status = get_tracker_status()
    return json.dumps({"success": True, **status}, default=str)


# ============================================================
# Tool dispatch table
# ============================================================
_TOOL_DISPATCH = {
    # --- Task Tracker handlers (MARKER_133.TRACKER_MCP) ---
    "mycelium_track_done": _handle_track_done,
    "mycelium_track_started": _handle_track_started,
    "mycelium_tracker_status": _handle_tracker_status,
    # --- Pipeline ---
    "mycelium_pipeline": _handle_pipeline,
    "mycelium_call_model": _handle_call_model,
    "mycelium_task_board": _handle_task_board,
    "mycelium_task_dispatch": _handle_task_dispatch,
    "mycelium_task_import": _handle_task_import,
    "mycelium_heartbeat_tick": _handle_heartbeat_tick,
    "mycelium_heartbeat_status": _handle_heartbeat_status,
    "mycelium_execute_workflow": _handle_execute_workflow,
    "mycelium_workflow_status": _handle_workflow_status,
    "mycelium_research": _handle_research,
    "mycelium_implement": _handle_implement,
    "mycelium_review": _handle_review,
    "mycelium_list_artifacts": _handle_list_artifacts,
    "mycelium_approve_artifact": _handle_approve_artifact,
    "mycelium_reject_artifact": _handle_reject_artifact,
    "mycelium_health": _handle_health,
    "mycelium_devpanel_stream": _handle_devpanel_stream,
}


# ============================================================
# call_tool handler
# ============================================================
@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Dispatch tool calls to handlers. MARKER_129.6."""
    handler = _TOOL_DISPATCH.get(name)
    if handler is None:
        # Check if it's a vetka_* tool — provide migration message
        if name.startswith("vetka_"):
            return [TextContent(
                type="text",
                text=json.dumps({
                    "error": f"Tool '{name}' is on MCP VETKA server, not MYCELIUM. "
                             f"Use the 'vetka' MCP server for this tool.",
                    "hint": "MYCELIUM handles: pipeline, task_board, heartbeat, "
                            "workflow, artifacts, call_model, research, implement, review",
                })
            )]
        return [TextContent(
            type="text",
            text=json.dumps({"error": f"Unknown tool: {name}"})
        )]

    try:
        result_text = await handler(arguments or {})
        return [TextContent(type="text", text=result_text)]
    except Exception as e:
        logger.error(f"Tool {name} failed: {e}", exc_info=True)
        return [TextContent(
            type="text",
            text=json.dumps({"error": f"Tool execution failed: {str(e)[:500]}"})
        )]


# ============================================================
# Signal handling + graceful shutdown
# ============================================================
def _signal_handler(signum, frame):
    """Handle SIGINT/SIGTERM."""
    logger.info(f"Signal {signum} received, shutting down...")
    _shutdown_event.set()


async def _graceful_shutdown():
    """Clean shutdown: cancel pipelines, close connections."""
    # Cancel active pipelines
    for task_id, task in list(_active_pipelines.items()):
        logger.info(f"Cancelling pipeline {task_id}...")
        task.cancel()
        try:
            await asyncio.wait_for(task, timeout=5.0)
        except (asyncio.CancelledError, asyncio.TimeoutError):
            pass

    # Close WS broadcaster
    if _ws_broadcaster:
        await _ws_broadcaster.stop()
        logger.info("WebSocket broadcaster stopped")

    # Close HTTP client
    if _http_client:
        await _http_client.stop()
        logger.info("HTTP client stopped")

    logger.info("Shutdown complete")


# ============================================================
# Main entry point
# ============================================================
async def main():
    """Run MYCELIUM MCP server (stdio mode)."""
    signal.signal(signal.SIGINT, _signal_handler)
    signal.signal(signal.SIGTERM, _signal_handler)

    logger.info("Starting MYCELIUM MCP server v129.6")

    # Pre-init WebSocket broadcaster (DevPanel needs it immediately)
    await _get_ws_broadcaster()

    try:
        # stdio mode — standard MCP protocol
        async with stdio_server() as (read_stream, write_stream):
            init_options = server.create_initialization_options()
            logger.info("stdio transport ready, serving 17 tools")

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
        await _graceful_shutdown()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        sys.exit(0)
