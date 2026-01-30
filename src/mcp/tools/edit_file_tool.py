"""
Edit file tool - REQUIRES APPROVAL, creates backups.

@status: active
@phase: 96
@depends: base_tool, pathlib, shutil, datetime
@used_by: mcp_server, stdio_server
"""
import shutil
from pathlib import Path
from datetime import datetime
from typing import Any, Dict
from .base_tool import BaseMCPTool

PROJECT_ROOT = Path("/Users/danilagulin/Documents/VETKA_Project/vetka_live_03")
BACKUP_DIR = PROJECT_ROOT / ".vetka_backups"


class EditFileTool(BaseMCPTool):
    """Edit or create a file. REQUIRES APPROVAL. Creates backup before changes."""

    @property
    def name(self) -> str:
        return "vetka_edit_file"

    @property
    def description(self) -> str:
        return "Edit or create a file. REQUIRES APPROVAL. Creates backup before changes. Default: dry_run=true"

    @property
    def schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "File path (relative to project root)"
                },
                "content": {
                    "type": "string",
                    "description": "New file content"
                },
                "mode": {
                    "type": "string",
                    "enum": ["write", "append"],
                    "default": "write",
                    "description": "Write mode: 'write' replaces, 'append' adds to end"
                },
                "create_dirs": {
                    "type": "boolean",
                    "default": False,
                    "description": "Create parent directories if they don't exist"
                },
                "dry_run": {
                    "type": "boolean",
                    "default": True,
                    "description": "Preview only (no actual write). Set to false to apply changes."
                }
            },
            "required": ["path", "content"]
        }

    @property
    def requires_approval(self) -> bool:
        return True

    def validate_arguments(self, args: Dict[str, Any]) -> str:
        path = args.get("path", "")
        if not path:
            return "Path is required"
        if ".." in path:
            return "Path traversal not allowed"
        content = args.get("content")
        if content is None:
            return "Content is required"
        return None

    def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        rel_path = arguments["path"].strip("/")
        content = arguments["content"]
        mode = arguments.get("mode", "write")
        create_dirs = arguments.get("create_dirs", False)
        dry_run = arguments.get("dry_run", True)

        full_path = PROJECT_ROOT / rel_path
        exists = full_path.exists()

        # Dry run - just preview
        if dry_run:
            return {
                "success": True,
                "result": {
                    "status": "dry_run",
                    "path": rel_path,
                    "exists": exists,
                    "mode": mode,
                    "content_length": len(content),
                    "would_create_dirs": create_dirs and not full_path.parent.exists(),
                    "message": "Preview only. Set dry_run=false to apply changes."
                },
                "error": None
            }

        try:
            backup_path = None

            # Create backup if file exists
            if exists:
                BACKUP_DIR.mkdir(exist_ok=True)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_name = f"{full_path.name}.{timestamp}.bak"
                backup_path = BACKUP_DIR / backup_name
                shutil.copy2(full_path, backup_path)

            # Create parent directories if requested
            if create_dirs:
                full_path.parent.mkdir(parents=True, exist_ok=True)
            elif not full_path.parent.exists():
                return {
                    "success": False,
                    "error": f"Parent directory does not exist: {full_path.parent}. Set create_dirs=true to create it.",
                    "result": None
                }

            # Write content
            write_mode = "a" if mode == "append" else "w"
            with open(full_path, write_mode, encoding="utf-8") as f:
                f.write(content)

            return {
                "success": True,
                "result": {
                    "status": "written",
                    "path": rel_path,
                    "mode": mode,
                    "bytes_written": len(content.encode('utf-8')),
                    "backup": str(backup_path.relative_to(PROJECT_ROOT)) if backup_path else None
                },
                "error": None
            }
        except Exception as e:
            return {"success": False, "error": str(e), "result": None}
