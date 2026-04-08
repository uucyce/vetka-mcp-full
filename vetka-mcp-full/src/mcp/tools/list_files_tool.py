"""
List files tool - safe read-only directory listing.

@status: active
@phase: 96
@depends: base_tool, pathlib
@used_by: mcp_server, stdio_server
"""
from pathlib import Path
from typing import Any, Dict, List
from .base_tool import BaseMCPTool

PROJECT_ROOT = Path("/Users/danilagulin/Documents/VETKA_Project/vetka_live_03")


class ListFilesTool(BaseMCPTool):
    """List files in a directory with optional recursion and pattern filtering"""

    @property
    def name(self) -> str:
        return "vetka_list_files"

    @property
    def description(self) -> str:
        return "List files in a directory with optional recursion and pattern filtering"

    @property
    def schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "default": "",
                    "description": "Directory path (relative to project root)"
                },
                "depth": {
                    "type": "integer",
                    "default": 1,
                    "description": "Recursion depth (1-5)"
                },
                "pattern": {
                    "type": "string",
                    "default": "*",
                    "description": "Glob pattern (e.g. *.py, *.md)"
                },
                "show_hidden": {
                    "type": "boolean",
                    "default": False,
                    "description": "Include hidden files (starting with .)"
                }
            },
            "required": []
        }

    def validate_arguments(self, args: Dict[str, Any]) -> str:
        path = args.get("path", "")
        if ".." in path:
            return "Path traversal not allowed"
        depth = args.get("depth", 1)
        if not isinstance(depth, int):
            return "Depth must be an integer"
        if depth < 1 or depth > 5:
            return "Depth must be between 1 and 5"
        return None

    def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        rel_path = arguments.get("path", "").strip("/")
        depth = min(max(arguments.get("depth", 1), 1), 5)
        pattern = arguments.get("pattern", "*")
        show_hidden = arguments.get("show_hidden", False)

        root = PROJECT_ROOT / rel_path if rel_path else PROJECT_ROOT
        if not root.is_dir():
            return {"success": False, "error": f"Not a directory: {rel_path or '/'}", "result": None}

        items: List[Dict] = []

        def collect(p: Path, d: int):
            if d <= 0:
                return
            try:
                for item in sorted(p.iterdir()):
                    # Skip hidden files unless requested
                    if not show_hidden and item.name.startswith('.'):
                        continue
                    # Skip __pycache__ and node_modules
                    if item.name in ('__pycache__', 'node_modules', '.git'):
                        continue

                    # Apply pattern filter for files
                    if pattern != "*" and item.is_file():
                        if not item.match(pattern):
                            continue

                    try:
                        stat = item.stat()
                        items.append({
                            "name": item.name,
                            "path": str(item.relative_to(PROJECT_ROOT)),
                            "type": "directory" if item.is_dir() else "file",
                            "size": stat.st_size if item.is_file() else None,
                            "modified": stat.st_mtime
                        })
                    except (PermissionError, OSError):
                        continue

                    # Recurse into directories
                    if item.is_dir() and d > 1:
                        collect(item, d - 1)
            except PermissionError:
                pass

        collect(root, depth)

        return {
            "success": True,
            "result": {
                "path": rel_path or "/",
                "pattern": pattern,
                "depth": depth,
                "count": len(items),
                "items": items[:200]  # Limit to 200 items
            },
            "error": None
        }
