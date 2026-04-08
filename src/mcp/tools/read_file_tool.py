"""
Read file tool - safe read-only file content access.

@status: active
@phase: 96
@depends: base_tool, pathlib, base64, mimetypes
@used_by: mcp_server, stdio_server
"""
import base64
from pathlib import Path
from mimetypes import guess_type
from typing import Any, Dict
from .base_tool import BaseMCPTool

PROJECT_ROOT = Path("/Users/danilagulin/Documents/VETKA_Project/vetka_live_03")
MAX_SIZE = 500_000  # 500KB


class ReadFileTool(BaseMCPTool):
    """Read file content (text or base64 for binary)"""

    @property
    def name(self) -> str:
        return "vetka_read_file"

    @property
    def description(self) -> str:
        return "Read file content (text or base64 for binary). Max 500KB."

    @property
    def schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "File path (relative to project root)"
                },
                "max_lines": {
                    "type": "integer",
                    "default": 500,
                    "description": "Max lines for text files (default: 500)"
                },
                "encoding": {
                    "type": "string",
                    "default": "utf-8",
                    "description": "Text encoding (default: utf-8)"
                }
            },
            "required": ["path"]
        }

    def validate_arguments(self, args: Dict[str, Any]) -> str:
        path = args.get("path", "")
        if not path:
            return "Path is required"
        if ".." in path:
            return "Path traversal not allowed"
        return None

    def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        rel_path = arguments["path"].strip("/")
        max_lines = arguments.get("max_lines", 500)
        encoding = arguments.get("encoding", "utf-8")

        # MARKER_195.6: Record read action for protocol tracking
        try:
            from src.services.session_tracker import get_session_tracker
            get_session_tracker().record_action("mcp_default", "vetka_read_file", {"file_path": rel_path})
        except Exception:
            pass

        full_path = PROJECT_ROOT / rel_path

        if not full_path.is_file():
            return {"success": False, "error": f"File not found: {rel_path}", "result": None}

        try:
            size = full_path.stat().st_size
        except OSError as e:
            return {"success": False, "error": f"Cannot access file: {e}", "result": None}

        if size > MAX_SIZE:
            return {
                "success": False,
                "error": f"File too large: {size} bytes (max {MAX_SIZE})",
                "result": None
            }

        mime, _ = guess_type(str(full_path))
        is_text = mime is None or mime.startswith('text/') or mime in [
            'application/json', 'application/javascript', 'application/xml',
            'application/x-python', 'application/x-sh', 'application/x-yaml'
        ]

        # Also check common text extensions
        text_extensions = {'.py', '.js', '.ts', '.tsx', '.jsx', '.json', '.md', '.txt',
                          '.yaml', '.yml', '.toml', '.ini', '.cfg', '.sh', '.bash',
                          '.html', '.css', '.scss', '.less', '.xml', '.svg', '.sql'}
        if full_path.suffix.lower() in text_extensions:
            is_text = True

        try:
            if is_text:
                lines = full_path.read_text(encoding=encoding, errors='replace').splitlines()
                content = "\n".join(lines[:max_lines])

                # MARKER_123.1C: Phase 123.1 - Emit glow for MCP file read (low intensity)
                try:
                    from src.services.activity_hub import get_activity_hub
                    hub = get_activity_hub()
                    hub.emit_glow_sync(str(full_path), 0.4, "mcp:read")
                except Exception:
                    pass  # Non-critical

                return {
                    "success": True,
                    "result": {
                        "path": rel_path,
                        "content": content,
                        "encoding": encoding,
                        "mime_type": mime or "text/plain",
                        "truncated": len(lines) > max_lines,
                        "total_lines": len(lines),
                        "size": size
                    },
                    "error": None
                }
            else:
                content = base64.b64encode(full_path.read_bytes()).decode()
                return {
                    "success": True,
                    "result": {
                        "path": rel_path,
                        "content": content,
                        "encoding": "base64",
                        "mime_type": mime or "application/octet-stream",
                        "size": size
                    },
                    "error": None
                }
        except Exception as e:
            return {"success": False, "error": str(e), "result": None}
