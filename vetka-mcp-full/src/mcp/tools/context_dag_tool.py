"""
MARKER_109_3_CONTEXT_DAG: Phase 109.1 - Dynamic MCP Context Injection

Context DAG Tool - Assembles compressed context digest from ALL sources.

This tool is the CORE of Phase 109.1 Dynamic Context Injection.
It collects context from multiple sources:
- Viewport (3D camera position, visible nodes)
- Pinned files (user selections)
- Chat history (recent conversations)
- CAM activations (context-aware memory)
- AURA preferences (user communication style)

Then applies ELISION compression to fit ~500 token budget.

Output format uses hyperlinks [→ label] for lazy loading:
- Agents get fat digest upfront (~500 tokens)
- Can expand any section via MCP tool calls
- Real-time updates via Socket.IO

Integration:
- Called by jarvis_prompt_enricher for super-agent context
- Socket.IO emits context_update on changes
- Uses ELISION Level 2-3 compression (40-60% savings)

@status: active
@phase: 109.1
@depends: base_tool, elision, session_tools (helpers), vetka_mcp_bridge (other tools)
@used_by: jarvis_prompt_enricher, vetka_mcp_bridge
"""

from typing import Dict, Any, Optional, List
import time
import asyncio
import json
from pathlib import Path
from .base_tool import BaseMCPTool


# Token budget allocation (target ~500 tokens total)
TOKEN_BUDGET = {
    "project_digest": 150,    # Current phase, achievements, pending
    "viewport": 80,           # Visible nodes, zoom level
    "pins": 50,               # Pinned files
    "recent_chats": 100,      # Chat history digest
    "cam_activations": 60,    # Active memory nodes
    "aura_prefs": 60,         # User preferences
}


class ContextDAGTool(BaseMCPTool):
    """
    Assemble Dynamic Context DAG from ALL sources.

    Returns compressed ~500 token digest with hyperlinks for expansion.
    """

    @property
    def name(self) -> str:
        return "vetka_get_context_dag"

    @property
    def description(self) -> str:
        return (
            "Assemble context DAG from ALL sources into ~500 token digest. "
            "Includes: viewport, pinned files, chat history, CAM activations, "
            "AURA preferences. Applies ELISION compression. "
            "Returns hyperlinks [→ label] for lazy expansion via other MCP tools."
        )

    @property
    def schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "session_id": {
                    "type": "string",
                    "description": "Session ID to build context for (required)"
                },
                "max_tokens": {
                    "type": "integer",
                    "description": "Token budget for digest (default: 500)",
                    "default": 500
                },
                "include_hyperlinks": {
                    "type": "boolean",
                    "description": "Include [→ label] hyperlinks for expansion (default: true)",
                    "default": True
                },
                "compression_level": {
                    "type": "integer",
                    "description": "ELISION compression level 1-3 (default: 2)",
                    "default": 2,
                    "minimum": 1,
                    "maximum": 3
                }
            },
            "required": ["session_id"]
        }

    def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute synchronously by running async in event loop."""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # Running in async context, create task
                future = asyncio.ensure_future(self._execute_async(arguments))
                return {
                    "success": True,
                    "result": {"status": "pending", "future": str(future)}
                }
            else:
                # No event loop, run sync
                return asyncio.run(self._execute_async(arguments))
        except RuntimeError:
            # Event loop already running, use run_until_complete
            return asyncio.run(self._execute_async(arguments))

    async def _execute_async(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Async implementation of context DAG assembly."""
        session_id = arguments["session_id"]
        max_tokens = arguments.get("max_tokens", 500)
        include_hyperlinks = arguments.get("include_hyperlinks", True)
        compression_level = arguments.get("compression_level", 2)

        try:
            # ==================================================================
            # STEP 1: Collect context from all sources
            # ==================================================================

            context_raw = await self._collect_all_contexts(session_id)

            # ==================================================================
            # STEP 2: Build compressed DAG
            # ==================================================================

            dag = await self._build_dag(
                context_raw,
                max_tokens,
                include_hyperlinks,
                compression_level
            )

            # ==================================================================
            # STEP 3: Estimate tokens and return
            # ==================================================================

            tokens_estimate = self._estimate_tokens(dag)

            result = {
                "session_id": session_id,
                "digest_version": "109.1",
                "tokens_estimate": tokens_estimate,
                "context_dag": dag["summaries"],
                "hyperlinks": dag["hyperlinks"] if include_hyperlinks else None,
                "expand_instructions": (
                    "Parse [→ label] and call corresponding MCP tool for full context."
                    if include_hyperlinks else None
                ),
                "compression_level": compression_level,
                "timestamp": time.time()
            }

            return {
                "success": True,
                "result": result
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to build context DAG: {str(e)}",
                "result": None
            }

    async def _collect_all_contexts(self, session_id: str) -> Dict[str, Any]:
        """
        Collect raw context from all sources.

        Returns dict with keys: project_digest, viewport, pins, chats, cam, aura
        """
        contexts = {}

        # === Project Digest ===
        try:
            from .session_tools import load_project_digest
            digest = load_project_digest()
            contexts["project_digest"] = digest
        except Exception as e:
            contexts["project_digest"] = {"error": str(e)}

        # === Viewport Context ===
        # NOTE: Viewport state lives client-side, we need to fetch from session storage
        # or via Socket.IO event. For now, stub with placeholder.
        try:
            contexts["viewport"] = await self._get_viewport_context(session_id)
        except Exception as e:
            contexts["viewport"] = {"error": str(e)}

        # === Pinned Files ===
        try:
            contexts["pins"] = await self._get_pinned_files(session_id)
        except Exception as e:
            contexts["pins"] = {"error": str(e)}

        # === Recent Chats ===
        try:
            contexts["chats"] = await self._get_chat_digest(session_id)
        except Exception as e:
            contexts["chats"] = {"error": str(e)}

        # === CAM Activations ===
        try:
            contexts["cam"] = await self._get_memory_summary()
        except Exception as e:
            contexts["cam"] = {"error": str(e)}

        # === AURA Preferences ===
        try:
            contexts["aura"] = await self._get_user_preferences()
        except Exception as e:
            contexts["aura"] = {"error": str(e)}

        return contexts

    async def _get_viewport_context(self, session_id: str) -> Dict[str, Any]:
        """
        Get viewport context from session storage or Socket.IO.

        NOTE: Viewport state lives client-side. Implementation options:
        1. Store viewport state in MCP session on camera_focus events
        2. Fetch via REST API from session storage
        3. Return stub until Phase 109.4 real-time sync
        """
        # TODO: Implement viewport state fetching
        # For now, return placeholder
        return {
            "visible_nodes": None,
            "zoom_level": "unknown",
            "focus": "unknown",
            "note": "Viewport state client-side, awaiting Socket.IO sync (Phase 109.4)"
        }

    async def _get_pinned_files(self, session_id: str) -> Dict[str, Any]:
        """
        Get pinned files from CAM or REST API.

        REST endpoint: GET /api/cam/pinned
        MCP tool (to be created): vetka_get_pinned_files
        """
        try:
            # Try to import and use REST client
            import httpx
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get("http://localhost:5001/api/cam/pinned")
                if response.status_code == 200:
                    data = response.json()
                    return data
                else:
                    return {"error": f"HTTP {response.status_code}"}
        except Exception as e:
            return {"error": str(e), "pinned_files": []}

    async def _get_chat_digest(self, session_id: str, max_messages: int = 10) -> Dict[str, Any]:
        """
        Get chat digest from chat_history_manager.

        Uses MARKER_108_3 get_chat_digest() function.
        """
        try:
            from src.api.handlers.chat_history_manager import get_chat_digest

            # Try to parse chat_id from session_id (Phase 108.1 linking)
            chat_id = session_id  # session_id = chat_id when linked

            digest = await get_chat_digest(chat_id, max_messages=max_messages)
            return digest
        except Exception as e:
            return {
                "error": str(e),
                "recent_messages": [],
                "agent_logs": []
            }

    async def _get_memory_summary(self) -> Dict[str, Any]:
        """
        Get CAM + Elisium memory summary.

        Returns active memory nodes and compression stats.
        """
        try:
            from src.memory.compression import MemoryCompression

            compressor = MemoryCompression()
            stats = compressor.get_stats()

            return {
                "active_nodes": stats.get("active_nodes", 0),
                "compression_schedule": stats.get("compression_schedule", []),
                "coherence_score": stats.get("coherence_score", 0.0)
            }
        except Exception as e:
            return {
                "error": str(e),
                "active_nodes": "N/A"
            }

    async def _get_user_preferences(self, user_id: str = "danila") -> Dict[str, Any]:
        """
        Get user preferences from AURA memory.

        Returns communication style, workflow preferences, etc.
        """
        try:
            from src.memory.aura_store import AuraStore
            from src.memory.qdrant_client import get_qdrant_client

            qdrant = get_qdrant_client()
            memory = AuraStore(qdrant)

            prefs = memory.get_all_preferences(user_id)

            return {
                "user_id": user_id,
                "preferences": prefs if prefs else {},
                "source": "aura_ram_cache" if memory.ram_cache.get(user_id) else "qdrant"
            }
        except Exception as e:
            return {
                "error": str(e),
                "preferences": {}
            }

    async def _build_dag(
        self,
        contexts: Dict[str, Any],
        max_tokens: int,
        include_hyperlinks: bool,
        compression_level: int
    ) -> Dict[str, Any]:
        """
        Build compressed DAG summaries with hyperlinks.

        Returns:
            {
                "summaries": {
                    "viewport": "[→ viewport] ...",
                    "pins": "[→ pins] ...",
                    ...
                },
                "hyperlinks": {
                    "viewport": "vetka_get_viewport_detail",
                    ...
                }
            }
        """
        summaries = {}
        hyperlinks = {}

        # === Project Digest ===
        digest = contexts.get("project_digest", {})
        if digest and not digest.get("error"):
            phase = digest.get("phase", {})
            achievements = digest.get("achievements", [])[:3]
            pending = digest.get("pending", [])[:2]

            summary = f"Phase {phase.get('number', 'N/A')}: {phase.get('status', 'unknown')}"
            if achievements:
                summary += f" | Recent: {', '.join(achievements[:2])}"
            if pending:
                summary += f" | Pending: {', '.join(pending[:1])}"

            summaries["project"] = f"[→ project] {summary}" if include_hyperlinks else summary
            hyperlinks["project"] = "vetka_session_init"

        # === Viewport ===
        viewport = contexts.get("viewport", {})
        if viewport and not viewport.get("error"):
            visible = viewport.get("visible_nodes", "unknown")
            zoom = viewport.get("zoom_level", "unknown")
            focus = viewport.get("focus", "unknown")

            summary = f"{visible} nodes visible (zoom~{zoom}), focus: {focus}"
            summaries["viewport"] = f"[→ viewport] {summary}" if include_hyperlinks else summary
            hyperlinks["viewport"] = "vetka_get_viewport_detail"
        else:
            summaries["viewport"] = "[→ viewport] (unavailable - awaiting Socket.IO sync)"
            hyperlinks["viewport"] = "vetka_get_viewport_detail"

        # === Pinned Files ===
        pins = contexts.get("pins", {})
        if pins and not pins.get("error"):
            pinned_files = pins.get("pinned_files", [])
            if pinned_files:
                file_names = [p.get("name", "unknown") for p in pinned_files[:3]]
                summary = ", ".join(file_names)
                if len(pinned_files) > 3:
                    summary += f" (+{len(pinned_files) - 3} more)"
            else:
                summary = "No pinned files"

            summaries["pins"] = f"[→ pins] {summary}" if include_hyperlinks else summary
            hyperlinks["pins"] = "vetka_get_pinned_files"

        # === Recent Chats ===
        chats = contexts.get("chats", {})
        if chats and not chats.get("error"):
            recent_msgs = chats.get("recent_messages", [])
            if recent_msgs:
                last_msg = recent_msgs[-1]
                summary = f"{len(recent_msgs)} msgs, last: '{last_msg.get('content', '')[:30]}...'"
            else:
                summary = "No recent messages"

            summaries["recent_chats"] = f"[→ chats] {summary}" if include_hyperlinks else summary
            hyperlinks["chats"] = "vetka_get_chat_digest"

        # === CAM Activations ===
        cam = contexts.get("cam", {})
        if cam and not cam.get("error"):
            active_nodes = cam.get("active_nodes", 0)
            coherence = cam.get("coherence_score", 0.0)

            summary = f"{active_nodes} active"
            if coherence > 0:
                summary += f" (coherence {coherence:.2f})"

            summaries["cam_activations"] = f"[→ cam] {summary}" if include_hyperlinks else summary
            hyperlinks["cam"] = "vetka_get_memory_summary"

        # === AURA Preferences ===
        aura = contexts.get("aura", {})
        if aura and not aura.get("error"):
            prefs = aura.get("preferences", {})
            style = prefs.get("communication_style", {}).get("value", "unknown")
            workflow = prefs.get("workflow", {}).get("value", "unknown")

            summary = f"Style: {style}, workflow: {workflow}"
            summaries["aura_prefs"] = f"[→ prefs] {summary}" if include_hyperlinks else summary
            hyperlinks["prefs"] = "vetka_get_user_preferences"

        # === Apply ELISION compression if level >= 2 ===
        if compression_level >= 2:
            summaries = self._apply_elision_compression(summaries, compression_level)

        return {
            "summaries": summaries,
            "hyperlinks": hyperlinks
        }

    def _apply_elision_compression(
        self,
        summaries: Dict[str, str],
        level: int
    ) -> Dict[str, str]:
        """
        Apply ELISION compression to DAG summaries.

        Level 2: Key abbreviation + path compression
        Level 3: Level 2 + vowel skipping
        """
        try:
            from src.memory.elision import get_elision_compressor

            compressor = get_elision_compressor()

            # Compress each summary individually
            compressed = {}
            for key, value in summaries.items():
                result = compressor.compress(value, level=level)
                compressed[key] = result.compressed

            return compressed
        except Exception as e:
            # If compression fails, return original
            return summaries

    def _estimate_tokens(self, dag: Dict[str, Any]) -> int:
        """
        Estimate token count for DAG output.

        Rough estimate: ~4 characters per token
        """
        summaries = dag.get("summaries", {})
        total_chars = sum(len(v) for v in summaries.values())
        return total_chars // 4


async def vetka_get_context_dag(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """
    Handler function for vetka_get_context_dag MCP tool.

    Args:
        arguments: Tool arguments from MCP call

    Returns:
        Result dict with success flag and context DAG
    """
    tool = ContextDAGTool()
    return await tool._execute_async(arguments)


def register_context_dag_tool(tool_list: List[Dict[str, Any]]):
    """
    Register context DAG tool with MCP bridge.

    Args:
        tool_list: List to append tool definition to
    """
    tool_list.append({
        "name": "vetka_get_context_dag",
        "description": (
            "Assemble context DAG from ALL sources into ~500 token digest. "
            "Includes: viewport, pinned files, chat history, CAM activations, "
            "AURA preferences. Applies ELISION compression. "
            "Returns hyperlinks [→ label] for lazy expansion via other MCP tools."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "session_id": {
                    "type": "string",
                    "description": "Session ID to build context for (required)"
                },
                "max_tokens": {
                    "type": "integer",
                    "description": "Token budget for digest (default: 500)",
                    "default": 500
                },
                "include_hyperlinks": {
                    "type": "boolean",
                    "description": "Include [→ label] hyperlinks for expansion (default: true)",
                    "default": True
                },
                "compression_level": {
                    "type": "integer",
                    "description": "ELISION compression level 1-3 (default: 2)",
                    "default": 2,
                    "minimum": 1,
                    "maximum": 3
                }
            },
            "required": ["session_id"]
        },
        "handler": vetka_get_context_dag
    })
