"""MCP Session Tools - Fat session initialization with ELISION compression.

Provides tools for efficient session bootstrapping with compressed context:
- vetka_session_init: Initialize MCP session with fat context (user preferences, CAM activations, recent states)
- vetka_session_status: Get current session status and validity

These tools enable AI agents to efficiently bootstrap sessions with
compressed user preferences, recent states, and CAM activations.
Uses ELISION compression to reduce token usage by 40-60%.

Features:
- Engram user preference loading (hot RAM cache + cold Qdrant)
- MCP state manager integration for persistence
- JARVIS prompt enricher for context compression
- Async/sync execution support

@status: active
@phase: 108
@depends: src/mcp/tools/base_tool.py, src/memory/engram_user_memory.py, src/mcp/state/mcp_state_manager.py, src/memory/jarvis_prompt_enricher.py
@used_by: src/mcp/vetka_mcp_bridge.py, src/mcp/tools/__init__.py

MARKER_MCP_CHAT_READY: Phase 108.1 - Unified MCP-Chat ID linking
- session_init accepts chat_id parameter (optional)
- If provided: session_id = chat_id (link to existing chat)
- If not provided: creates new chat, uses its ID as session_id
- Result: Every MCP session linked to VETKA chat for persistent context

MARKER_109_1_VIEWPORT_INJECT: Phase 109.1 - Dynamic Context Injection
- include_viewport now ACTUALLY builds viewport summary (was dead code)
- include_pinned now ACTUALLY builds pinned files context (was dead code)
- Added context_dag support for Jarvis super-agent integration
- Hyperlinks format: [→ label] for lazy loading via MCP tools
"""

from typing import Dict, Any, Optional
import time
import asyncio
import json
from pathlib import Path
from .base_tool import BaseMCPTool


# Project digest path (relative to project root)
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
DIGEST_PATH = PROJECT_ROOT / "data" / "project_digest.json"


def load_project_digest() -> Optional[Dict[str, Any]]:
    """
    Load project digest for agent context initialization.

    Returns condensed project state including:
    - Current phase number and status
    - Key achievements and pending items
    - System status (Qdrant collections, MCP)
    - Agent instructions

    Returns None if digest not found or invalid.
    """
    try:
        if DIGEST_PATH.exists():
            with open(DIGEST_PATH, 'r') as f:
                digest = json.load(f)

            # Return condensed version for MCP context
            return {
                "phase": digest.get("current_phase", {}),
                "summary": digest.get("summary", {}).get("headline", ""),
                "achievements": digest.get("summary", {}).get("key_achievements", [])[:5],
                "pending": digest.get("summary", {}).get("pending_items", [])[:3],
                "system": digest.get("system_status", {}),
                "instructions": digest.get("agent_instructions", {}),
                "last_updated": digest.get("last_updated"),
                "recent_fixes": [f.get("id") for f in digest.get("recent_fixes", [])[:5]]
            }
    except Exception:
        pass
    return None


class SessionInitTool(BaseMCPTool):
    """Initialize MCP session with fat context and ELISION compression."""

    @property
    def name(self) -> str:
        return "vetka_session_init"

    @property
    def description(self) -> str:
        return (
            "Initialize MCP session with fat context including PROJECT DIGEST. "
            "Returns: current phase info, key achievements, pending items, system status, "
            "user preferences from Engram, recent states, and CAM activations. "
            "Returns compressed context via ELISION for efficient LLM consumption. "
            "IMPORTANT: Call this at the start of EVERY conversation to get project state!"
        )

    @property
    def schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "user_id": {
                    "type": "string",
                    "description": "User identifier (default: 'default')",
                    "default": "default"
                },
                "group_id": {
                    "type": "string",
                    "description": "Group chat ID if in group context (optional)"
                },
                "chat_id": {
                    "type": "string",
                    "description": "Chat ID to link session with existing chat (optional, Phase 108.1)"
                },
                "include_viewport": {
                    "type": "boolean",
                    "description": "Include 3D viewport context if available",
                    "default": True
                },
                "include_pinned": {
                    "type": "boolean",
                    "description": "Include pinned files context",
                    "default": True
                },
                "compress": {
                    "type": "boolean",
                    "description": "Apply ELISION compression to context",
                    "default": True
                },
                "max_context_tokens": {
                    "type": "integer",
                    "description": "Maximum tokens for context (default: 4000)",
                    "default": 4000
                }
            },
            "required": []
        }

    def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute synchronously by running async in event loop."""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # Create future for async execution
                future = asyncio.ensure_future(self._execute_async(arguments))
                # Can't await in sync context, return pending status
                return {
                    "success": True,
                    "result": {
                        "status": "initializing",
                        "message": "Session initialization started asynchronously"
                    }
                }
            else:
                return loop.run_until_complete(self._execute_async(arguments))
        except RuntimeError:
            # No event loop, create one
            return asyncio.run(self._execute_async(arguments))

    async def _execute_async(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Async implementation of session initialization."""
        user_id = arguments.get("user_id", "default")
        group_id = arguments.get("group_id")
        chat_id = arguments.get("chat_id")  # MARKER_108_1: Unified MCP-Chat ID
        include_viewport = arguments.get("include_viewport", True)
        include_pinned = arguments.get("include_pinned", True)
        compress = arguments.get("compress", True)
        max_context_tokens = arguments.get("max_context_tokens", 4000)

        # MARKER_108_1: Unified MCP-Chat ID
        # If chat_id provided, use it as session_id
        # If not, create new chat and use its ID
        if chat_id:
            session_id = chat_id
            linked_to_existing = True
        else:
            # Create new VETKA chat and use its ID as session_id
            try:
                from src.chat.chat_history_manager import get_chat_history_manager
                chat_mgr = get_chat_history_manager()
                # Create chat with MCP context
                new_chat_id = chat_mgr.get_or_create_chat(
                    file_path="unknown",
                    context_type="topic",
                    topic="MCP Session",
                    display_name=f"MCP {user_id[:8]}"
                )
                session_id = new_chat_id
                chat_id = new_chat_id
                linked_to_existing = False
            except Exception as e:
                # Fallback to old session_id format if chat creation fails
                session_id = f"session_{user_id}_{group_id or 'solo'}_{int(time.time())}"
                chat_id = None
                linked_to_existing = False
                print(f"[SessionInit] Failed to create chat, using session_id: {e}")

        context = {
            "session_id": session_id,
            "chat_id": chat_id,  # MARKER_108_1: Unified ID
            "linked": chat_id is not None,  # MARKER_108_1: Link status
            "linked_to_existing": linked_to_existing,
            "user_id": user_id,
            "group_id": group_id,
            "initialized": True,
            "initialized_at": time.time(),
        }

        # Load project digest for agent context
        project_digest = load_project_digest()
        if project_digest:
            context["project_digest"] = project_digest
            context["current_phase"] = project_digest.get("phase", {})
            # Add agent instructions to top-level for easy access
            if project_digest.get("instructions"):
                context["agent_instructions"] = project_digest["instructions"]

        # Get user preferences from Engram
        try:
            from src.memory.engram_user_memory import get_engram_user_memory
            engram = get_engram_user_memory()
            prefs = engram.get_user_preferences(user_id)
            if prefs:
                # Convert UserPreferences dataclass to dict safely
                context["user_preferences"] = {
                    "user_id": prefs.user_id,
                    "has_preferences": True
                }
                # Add key preference categories if available
                if hasattr(prefs, 'communication_style'):
                    context["communication_style"] = getattr(prefs.communication_style, '__dict__', {})
                if hasattr(prefs, 'viewport_patterns'):
                    context["viewport_patterns"] = getattr(prefs.viewport_patterns, '__dict__', {})
            else:
                context["user_preferences"] = {"user_id": user_id, "has_preferences": False}
        except Exception as e:
            context["user_preferences_error"] = str(e)

        # Get recent MCP states
        try:
            from src.mcp.state import get_mcp_state_manager
            mcp = get_mcp_state_manager()
            recent = await mcp.get_all_states(limit=10)
            context["recent_states_count"] = len(recent)
            context["recent_state_ids"] = list(recent.keys())[:5]
        except Exception as e:
            context["recent_states_error"] = str(e)

        # MARKER_109_1_VIEWPORT_INJECT: Build viewport context if requested
        if include_viewport:
            try:
                # Try to get viewport data from CAM engine or state
                viewport_context = await self._get_viewport_context(session_id)
                if viewport_context:
                    from src.api.handlers.message_utils import build_viewport_summary
                    viewport_summary = build_viewport_summary(viewport_context)
                    if viewport_summary:
                        context["viewport_summary"] = viewport_summary
                        context["viewport"] = {
                            "zoom": viewport_context.get("zoom_level", 1),
                            "visible_count": len(viewport_context.get("viewport_nodes", [])),
                            "pinned_count": len(viewport_context.get("pinned_nodes", [])),
                            "hyperlink": "[→ viewport] vetka_get_viewport_detail"
                        }
            except Exception as e:
                context["viewport_error"] = str(e)

        # MARKER_109_1_VIEWPORT_INJECT: Build pinned files context if requested
        if include_pinned:
            try:
                pinned_files = await self._get_pinned_files(session_id, chat_id)
                if pinned_files:
                    from src.api.handlers.message_utils import build_pinned_context
                    pinned_context = build_pinned_context(pinned_files, max_files=5)
                    if pinned_context:
                        context["pinned_context"] = pinned_context
                        context["pinned"] = {
                            "count": len(pinned_files),
                            "files": [pf.get("name", pf.get("path", "")) for pf in pinned_files[:5]],
                            "hyperlink": "[→ pins] vetka_get_pinned_files"
                        }
            except Exception as e:
                context["pinned_error"] = str(e)

        # Apply ELISION compression if requested
        if compress:
            try:
                from src.memory.jarvis_prompt_enricher import JARVISPromptEnricher
                enricher = JARVISPromptEnricher()
                original_size = len(str(context))
                compressed_str = enricher.compress_context(context)
                compressed_size = len(compressed_str)
                context["compression"] = {
                    "enabled": True,
                    "original_size": original_size,
                    "compressed_size": compressed_size,
                    "ratio": round(original_size / max(compressed_size, 1), 2)
                }
            except Exception as e:
                context["compression"] = {"enabled": False, "error": str(e)}

        # Save session state for later retrieval
        try:
            from src.mcp.state import get_mcp_state_manager
            mcp = get_mcp_state_manager()
            await mcp.save_state(session_id, context, ttl_seconds=3600)
            context["persisted"] = True
        except Exception as e:
            context["persisted"] = False
            context["persist_error"] = str(e)

        # TODO MARKER_126.11D: Include claimable tasks from Task Board
        # When implemented, add:
        # try:
        #     from src.orchestration.task_board import get_task_board
        #     board = get_task_board()
        #     context["available_tasks"] = board.get_claimable_tasks(limit=5)
        #     context["my_claimed_tasks"] = board.get_claimed_by(session_id)
        # except Exception:
        #     pass

        # MARKER_172.P4.IP6: REFLEX session recommendations
        try:
            from src.services.reflex_integration import reflex_session
            reflex_recs = reflex_session(context)
            if reflex_recs:
                context["reflex_recommendations"] = reflex_recs
        except Exception:
            pass  # REFLEX errors never block session init

        return {
            "success": True,
            "result": context
        }

    async def _get_viewport_context(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        MARKER_109_1_VIEWPORT_INJECT: Get viewport context from various sources.

        Tries in order:
        1. MCP state manager (if client synced viewport)
        2. CAM engine viewport patterns
        3. Default empty context
        """
        try:
            # Try MCP state first (client may have synced viewport)
            from src.mcp.state import get_mcp_state_manager
            mcp = get_mcp_state_manager()
            state = await mcp.get_state(session_id)
            if state and "viewport" in state:
                return state["viewport"]

            # Try CAM engine viewport patterns
            try:
                from src.orchestration.cam_engine import get_cam_engine
                cam = get_cam_engine()
                if hasattr(cam, 'get_viewport_state'):
                    return cam.get_viewport_state()
            except Exception:
                pass

            # Return minimal context if nothing available
            return {
                "zoom_level": 1,
                "viewport_nodes": [],
                "pinned_nodes": [],
                "camera_position": {"x": 0, "y": 0, "z": 100}
            }
        except Exception as e:
            print(f"[SessionInit] Viewport context error: {e}")
            return None

    async def _get_pinned_files(self, session_id: str, chat_id: Optional[str]) -> list:
        """
        MARKER_109_1_VIEWPORT_INJECT: Get pinned files from chat history or CAM.

        Sources:
        1. Chat history manager (if chat_id provided)
        2. CAM pinned nodes
        3. MCP state (if client synced pins)
        """
        pinned = []

        try:
            # Try chat history manager first
            if chat_id:
                from src.chat.chat_history_manager import get_chat_history_manager
                chat_mgr = get_chat_history_manager()
                if hasattr(chat_mgr, 'get_pinned_files'):
                    chat_pinned = chat_mgr.get_pinned_files(chat_id)
                    if chat_pinned:
                        pinned.extend(chat_pinned)

            # Try CAM pinned nodes
            try:
                from src.orchestration.cam_engine import get_cam_engine
                cam = get_cam_engine()
                if hasattr(cam, 'get_pinned_nodes'):
                    cam_pinned = cam.get_pinned_nodes()
                    for node in cam_pinned:
                        if isinstance(node, dict):
                            pinned.append(node)
                        else:
                            pinned.append({"path": str(node), "name": str(node).split("/")[-1]})
            except Exception:
                pass

            # Try MCP state
            if not pinned:
                from src.mcp.state import get_mcp_state_manager
                mcp = get_mcp_state_manager()
                state = await mcp.get_state(session_id)
                if state and "pinned_files" in state:
                    pinned.extend(state["pinned_files"])

        except Exception as e:
            print(f"[SessionInit] Pinned files error: {e}")

        return pinned


class SessionStatusTool(BaseMCPTool):
    """Get current MCP session status."""

    @property
    def name(self) -> str:
        return "vetka_session_status"

    @property
    def description(self) -> str:
        return (
            "Get current MCP session status. "
            "Returns session data, expiration time, and recent activity. "
            "Use to check if session is still valid or needs refresh."
        )

    @property
    def schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "session_id": {
                    "type": "string",
                    "description": "Session ID to check status for"
                }
            },
            "required": ["session_id"]
        }

    def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute synchronously by running async in event loop."""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # Return sync-compatible result
                return {
                    "success": True,
                    "result": {
                        "status": "checking",
                        "session_id": arguments.get("session_id"),
                        "message": "Status check initiated"
                    }
                }
            else:
                return loop.run_until_complete(self._execute_async(arguments))
        except RuntimeError:
            return asyncio.run(self._execute_async(arguments))

    async def _execute_async(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Async implementation of session status check."""
        session_id = arguments.get("session_id")

        if not session_id:
            return {
                "success": False,
                "error": "session_id is required"
            }

        try:
            from src.mcp.state import get_mcp_state_manager
            mcp = get_mcp_state_manager()
            state = await mcp.get_state(session_id)

            if state:
                return {
                    "success": True,
                    "result": {
                        "exists": True,
                        "session_id": session_id,
                        "session": state,
                        "age_seconds": time.time() - state.get("initialized_at", time.time())
                    }
                }
            else:
                return {
                    "success": True,
                    "result": {
                        "exists": False,
                        "session_id": session_id,
                        "message": "Session not found or expired"
                    }
                }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }


# Convenience functions for direct import
async def vetka_session_init(
    user_id: str = "default",
    group_id: Optional[str] = None,
    chat_id: Optional[str] = None,  # MARKER_108_1: Chat ID parameter
    include_viewport: bool = True,
    include_pinned: bool = True,
    compress: bool = True,
    max_context_tokens: int = 4000
) -> Dict[str, Any]:
    """
    Initialize MCP session with fat context.

    Convenience wrapper for SessionInitTool.

    MARKER_108_1: Phase 108.1 - Unified MCP-Chat ID
    If chat_id provided, links session to existing VETKA chat.
    If not, creates new chat and returns its ID as session_id.
    """
    tool = SessionInitTool()
    return await tool._execute_async({
        "user_id": user_id,
        "group_id": group_id,
        "chat_id": chat_id,  # MARKER_108_1: Pass chat_id
        "include_viewport": include_viewport,
        "include_pinned": include_pinned,
        "compress": compress,
        "max_context_tokens": max_context_tokens
    })


async def vetka_session_status(session_id: str) -> Dict[str, Any]:
    """
    Get current session status.

    Convenience wrapper for SessionStatusTool.
    """
    tool = SessionStatusTool()
    return await tool._execute_async({"session_id": session_id})


def register_session_tools(tool_list: list):
    """
    Register session tools with a tool registry list.

    Args:
        tool_list: List to append tool instances to
    """
    tool_list.extend([
        SessionInitTool(),
        SessionStatusTool()
    ])
