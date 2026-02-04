"""MCP Pinned Files Tool - Dynamic context injection for pinned files.

MARKER_109_2_PINNED_TOOL: Phase 109.1 - Dynamic Context Injection
- Provides vetka_get_pinned_files tool for MCP agents
- Returns pinned files with metadata (path, reason, timestamp)
- Supports filtering by session_id
- Optional content snippets for quick reference
- Integrates with existing REST endpoint /api/cam/pinned

Features:
- Get all pinned files or filter by session
- Include content snippets on demand
- Format optimized for LLM consumption
- Compact summary line for quick scanning

@status: active
@phase: 109.1
@depends: src/mcp/tools/base_tool.py, src/api/routes/cam_routes.py, src/chat/chat_history_manager.py
@used_by: src/mcp/vetka_mcp_bridge.py, src/mcp/tools/__init__.py
"""

from typing import Dict, Any, Optional, List
import asyncio
import logging
from pathlib import Path
from .base_tool import BaseMCPTool

logger = logging.getLogger(__name__)


class PinnedFilesTool(BaseMCPTool):
    """Get pinned files with metadata for dynamic context injection."""

    @property
    def name(self) -> str:
        return "vetka_get_pinned_files"

    @property
    def description(self) -> str:
        return (
            "Get list of pinned files with metadata (path, reason, timestamp). "
            "Pinned files are important context files that user wants to keep in view. "
            "Use this to understand which files are currently prioritized for the session. "
            "Returns formatted list with optional content snippets for quick reference."
        )

    @property
    def schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "session_id": {
                    "type": "string",
                    "description": "Optional session ID to filter pinned files by session"
                },
                "include_content": {
                    "type": "boolean",
                    "description": "Include file content snippets (first 10 lines). Default: false",
                    "default": False
                },
                "chat_id": {
                    "type": "string",
                    "description": "Optional chat ID to get pinned files for specific chat"
                }
            }
        }

    def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute synchronously by running async in event loop."""
        try:
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            if loop.is_running():
                # Return sync-compatible result
                future = asyncio.ensure_future(self._execute_async(arguments))
                return {
                    "success": True,
                    "result": {
                        "status": "fetching",
                        "message": "Fetching pinned files..."
                    }
                }
            else:
                return loop.run_until_complete(self._execute_async(arguments))
        except RuntimeError:
            return asyncio.run(self._execute_async(arguments))

    async def _execute_async(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Async implementation of pinned files retrieval."""
        session_id = arguments.get("session_id")
        include_content = arguments.get("include_content", False)
        chat_id = arguments.get("chat_id")

        try:
            # Get pinned files from chat history manager if chat_id provided
            if chat_id:
                pinned_files = await self._get_pinned_from_chat(chat_id, include_content)
            else:
                # Get from CAM routes (global pinned files)
                pinned_files = await self._get_pinned_from_cam(session_id, include_content)

            # Format result
            result = self._format_result(pinned_files)

            return {
                "success": True,
                "result": result
            }

        except Exception as e:
            logger.error(f"[PinnedFilesTool] Error retrieving pinned files: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def _get_pinned_from_chat(
        self,
        chat_id: str,
        include_content: bool
    ) -> List[Dict[str, Any]]:
        """
        Get pinned files from chat history manager.

        Phase 100.2: Chat-specific pinned files stored in chat_history.json.
        Returns list of file node IDs with resolved paths.
        """
        try:
            from src.chat.chat_history_manager import get_chat_history_manager
            chat_mgr = get_chat_history_manager()

            pinned_file_ids = chat_mgr.get_pinned_files(chat_id)

            if not pinned_file_ids:
                return []

            # Resolve node IDs to file paths
            # In Phase 100.2, pinned_file_ids are node IDs from Zustand
            # Need to look them up in tree structure or file system
            pinned_files = []
            for file_id in pinned_file_ids:
                file_data = {
                    "path": file_id,  # For now, use ID as path
                    "reason": f"Pinned in chat {chat_id[:8]}",
                    "pinned_at": "",  # Chat history doesn't track individual pin timestamps
                    "source": "chat"
                }

                # Try to resolve to actual path if possible
                # Phase 109.2: Add path resolution logic here if needed

                if include_content:
                    content_snippet = await self._read_file_snippet(file_id)
                    if content_snippet:
                        file_data["content_snippet"] = content_snippet

                pinned_files.append(file_data)

            return pinned_files

        except Exception as e:
            logger.warning(f"[PinnedFilesTool] Could not get pinned files from chat: {e}")
            return []

    async def _get_pinned_from_cam(
        self,
        session_id: Optional[str],
        include_content: bool
    ) -> List[Dict[str, Any]]:
        """
        Get pinned files from CAM routes.

        Uses existing REST endpoint /api/cam/pinned.
        Phase 99.3: Global pinned files stored in cam_routes._pinned_files.
        """
        try:
            # Try to import from cam_routes (requires FastAPI to be available)
            try:
                from src.api.routes.cam_routes import _pinned_files
            except ImportError as e:
                logger.debug(f"[PinnedFilesTool] CAM routes not available: {e}")
                return []

            pinned_list = []

            for file_path, data in _pinned_files.items():
                # Filter by session if requested
                if session_id:
                    file_session = data.get("session_id", "")
                    if file_session != session_id:
                        continue

                file_data = {
                    "path": file_path,
                    "reason": data.get("reason", ""),
                    "pinned_at": data.get("timestamp", ""),
                    "source": "cam"
                }

                if include_content:
                    content_snippet = await self._read_file_snippet(file_path)
                    if content_snippet:
                        file_data["content_snippet"] = content_snippet

                pinned_list.append(file_data)

            # Sort by timestamp (most recent first)
            pinned_list.sort(key=lambda x: x["pinned_at"], reverse=True)

            return pinned_list

        except Exception as e:
            logger.warning(f"[PinnedFilesTool] Error getting pinned files from CAM: {e}")
            return []

    async def _read_file_snippet(self, file_path: str) -> Optional[str]:
        """
        Read first 10 lines of a file as a snippet.

        Args:
            file_path: Path to file (absolute or relative to project root)

        Returns:
            Content snippet or None if file can't be read
        """
        try:
            # Resolve path if relative
            path = Path(file_path)
            if not path.is_absolute():
                # Try relative to project root
                project_root = Path(__file__).parent.parent.parent.parent
                path = project_root / file_path

            if not path.exists():
                return None

            # Read first 10 lines
            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = []
                for i, line in enumerate(f):
                    if i >= 10:
                        break
                    lines.append(line.rstrip())

                if lines:
                    snippet = "\n".join(lines)
                    if i >= 9:  # If we stopped at line 10
                        snippet += "\n... (truncated)"
                    return snippet

            return None

        except Exception as e:
            logger.debug(f"[PinnedFilesTool] Could not read snippet from {file_path}: {e}")
            return None

    def _format_result(self, pinned_files: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Format pinned files result for LLM consumption.

        Returns dict with:
        - pinned_files: List of file dicts
        - count: Total count
        - summary: Compact one-line summary
        """
        count = len(pinned_files)

        # Create compact summary
        if count == 0:
            summary = "[→ pins] None"
        else:
            # Extract file names (last component of path)
            file_names = []
            for f in pinned_files[:5]:  # Show max 5 in summary
                path = f.get("path", "")
                name = Path(path).name if path else "unknown"
                file_names.append(name)

            files_str = ", ".join(file_names)
            if count > 5:
                files_str += f" (+{count - 5} more)"

            summary = f"[→ pins] {files_str}"

        return {
            "pinned_files": pinned_files,
            "count": count,
            "summary": summary
        }


# Convenience function for direct import
async def vetka_get_pinned_files(
    session_id: Optional[str] = None,
    include_content: bool = False,
    chat_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Get pinned files with metadata.

    Convenience wrapper for PinnedFilesTool.

    Args:
        session_id: Optional session ID to filter by
        include_content: Include file content snippets (first 10 lines)
        chat_id: Optional chat ID to get chat-specific pins

    Returns:
        Dict with pinned_files list, count, and summary
    """
    tool = PinnedFilesTool()
    return await tool._execute_async({
        "session_id": session_id,
        "include_content": include_content,
        "chat_id": chat_id
    })


def register_pinned_files_tool(tool_list: list):
    """
    Register pinned files tool with a tool registry list.

    Args:
        tool_list: List to append tool instance to
    """
    tool_list.append(PinnedFilesTool())
