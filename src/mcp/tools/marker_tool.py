"""
VETKA MCP Marker Tool — Add @status/@phase markers to Python/TypeScript files.

Phase 98.5: Tool for Claude Code and web agents to add standardized markers.

@file marker_tool.py
@status active
@phase 98
@depends base_tool, pathlib, re
@used_by vetka_mcp_bridge, Claude Code, web agents

Marker Format:
    @status: active|deprecated|experimental|stub
    @phase: <number> (e.g., 98, 76.3)
    @depends: comma-separated dependencies
    @used_by: comma-separated consumers

Usage via MCP:
    vetka_add_markers(
        file_path="/path/to/file.py",
        status="active",
        phase="98",
        depends="module1, module2",
        used_by="consumer1"
    )
"""

import re
import os
import logging
from typing import Any, Dict, Optional, List
from pathlib import Path

from .base_tool import BaseMCPTool

logger = logging.getLogger(__name__)

# Valid status values
VALID_STATUSES = ["active", "deprecated", "experimental", "stub", "legacy", "refactoring"]

# File extensions that support markers
SUPPORTED_EXTENSIONS = {
    ".py": {"comment_start": '"""', "comment_end": '"""', "line_comment": "#"},
    ".ts": {"comment_start": "/**", "comment_end": "*/", "line_comment": "//"},
    ".tsx": {"comment_start": "/**", "comment_end": "*/", "line_comment": "//"},
    ".js": {"comment_start": "/**", "comment_end": "*/", "line_comment": "//"},
    ".jsx": {"comment_start": "/**", "comment_end": "*/", "line_comment": "//"},
}


class MarkerTool(BaseMCPTool):
    """
    MCP Tool for adding @status/@phase markers to source files.

    Enables Claude Code and web agents to maintain consistent
    documentation markers across the VETKA codebase.
    """

    @property
    def name(self) -> str:
        return "vetka_add_markers"

    @property
    def description(self) -> str:
        return (
            "Add or update @status/@phase/@depends/@used_by markers in Python/TypeScript files. "
            "Markers help track file status, phase version, dependencies, and consumers. "
            "Supports .py, .ts, .tsx, .js, .jsx files."
        )

    @property
    def schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Absolute or relative path to the file"
                },
                "status": {
                    "type": "string",
                    "description": "File status",
                    "enum": VALID_STATUSES,
                    "default": "active"
                },
                "phase": {
                    "type": "string",
                    "description": "Phase number (e.g., '98', '76.3')"
                },
                "depends": {
                    "type": "string",
                    "description": "Comma-separated list of dependencies (optional)"
                },
                "used_by": {
                    "type": "string",
                    "description": "Comma-separated list of consumers (optional)"
                },
                "dry_run": {
                    "type": "boolean",
                    "description": "If true, return preview without writing",
                    "default": False
                }
            },
            "required": ["file_path", "phase"]
        }

    def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Add or update markers in a file."""
        try:
            file_path = arguments.get("file_path", "")
            status = arguments.get("status", "active")
            phase = arguments.get("phase", "")
            depends = arguments.get("depends", "")
            used_by = arguments.get("used_by", "")
            dry_run = arguments.get("dry_run", False)

            # Validate inputs
            if not file_path:
                return {"success": False, "error": "file_path is required", "result": None}

            if not phase:
                return {"success": False, "error": "phase is required", "result": None}

            if status not in VALID_STATUSES:
                return {
                    "success": False,
                    "error": f"Invalid status '{status}'. Valid: {VALID_STATUSES}",
                    "result": None
                }

            # Resolve path
            path = Path(file_path)
            if not path.is_absolute():
                # Try relative to project root
                project_root = Path(__file__).parent.parent.parent.parent
                path = project_root / file_path

            if not path.exists():
                return {"success": False, "error": f"File not found: {path}", "result": None}

            # Check extension
            ext = path.suffix.lower()
            if ext not in SUPPORTED_EXTENSIONS:
                return {
                    "success": False,
                    "error": f"Unsupported extension '{ext}'. Supported: {list(SUPPORTED_EXTENSIONS.keys())}",
                    "result": None
                }

            # Read file
            content = path.read_text(encoding="utf-8")

            # Build marker block
            markers = self._build_markers(status, phase, depends, used_by)

            # Update or insert markers
            new_content, action = self._apply_markers(content, markers, ext)

            if dry_run:
                # Show preview
                preview_lines = new_content.split("\n")[:30]
                return {
                    "success": True,
                    "result": {
                        "action": action,
                        "preview": "\n".join(preview_lines),
                        "dry_run": True,
                        "file": str(path)
                    },
                    "error": None
                }

            # Write file
            path.write_text(new_content, encoding="utf-8")

            logger.info(f"[Marker] {action} markers in {path.name}: @status={status}, @phase={phase}")

            return {
                "success": True,
                "result": {
                    "action": action,
                    "file": str(path),
                    "status": status,
                    "phase": phase,
                    "depends": depends,
                    "used_by": used_by
                },
                "error": None
            }

        except Exception as e:
            logger.error(f"[Marker] Error: {e}")
            return {"success": False, "error": str(e), "result": None}

    def _build_markers(
        self,
        status: str,
        phase: str,
        depends: str,
        used_by: str
    ) -> List[str]:
        """Build marker lines."""
        markers = [
            f"@status: {status}",
            f"@phase: {phase}"
        ]
        if depends:
            markers.append(f"@depends: {depends}")
        if used_by:
            markers.append(f"@used_by: {used_by}")
        return markers

    def _apply_markers(
        self,
        content: str,
        markers: List[str],
        ext: str
    ) -> tuple[str, str]:
        """
        Apply markers to content.

        Returns (new_content, action) where action is 'updated' or 'inserted'.
        """
        # Patterns for existing markers
        status_pattern = r'@status:\s*\w+'
        phase_pattern = r'@phase:\s*[\d.]+'
        depends_pattern = r'@depends:\s*[^\n]+'
        used_by_pattern = r'@used_by:\s*[^\n]+'

        # Check if markers already exist
        has_status = re.search(status_pattern, content)
        has_phase = re.search(phase_pattern, content)

        if has_status or has_phase:
            # Update existing markers
            new_content = content

            # Update @status
            if has_status:
                new_content = re.sub(
                    status_pattern,
                    markers[0],  # @status: value
                    new_content,
                    count=1
                )

            # Update @phase
            if has_phase:
                new_content = re.sub(
                    phase_pattern,
                    markers[1],  # @phase: value
                    new_content,
                    count=1
                )

            # Update @depends if provided and exists
            if len(markers) > 2 and "@depends" in markers[2]:
                if re.search(depends_pattern, new_content):
                    new_content = re.sub(depends_pattern, markers[2], new_content, count=1)
                elif has_phase:
                    # Insert after @phase
                    new_content = re.sub(
                        phase_pattern,
                        f"{markers[1]}\n{markers[2]}",
                        new_content,
                        count=1
                    )

            # Update @used_by if provided and exists
            used_by_marker = [m for m in markers if "@used_by" in m]
            if used_by_marker:
                if re.search(used_by_pattern, new_content):
                    new_content = re.sub(used_by_pattern, used_by_marker[0], new_content, count=1)

            return new_content, "updated"

        else:
            # Insert new markers at the beginning
            marker_block = "\n".join(markers)

            if ext == ".py":
                # Python: Insert into existing docstring or create one
                docstring_pattern = r'^("""|\'\'\')([^"\']*)("""|\'\'\')'
                match = re.match(r'^("""|\'\'\')(.*?)("""|\'\'\')', content, re.DOTALL)

                if match:
                    # Insert markers at end of existing docstring
                    docstring_content = match.group(2)
                    new_docstring = f'"""{docstring_content}\n\n{marker_block}\n"""'
                    new_content = re.sub(
                        r'^("""|\'\'\')(.*?)("""|\'\'\')',
                        new_docstring,
                        content,
                        count=1,
                        flags=re.DOTALL
                    )
                else:
                    # Create new docstring
                    new_content = f'"""\n{marker_block}\n"""\n\n{content}'
            else:
                # JS/TS: Insert as JSDoc comment
                new_content = f"/**\n * {marker_block.replace(chr(10), chr(10) + ' * ')}\n */\n\n{content}"

            return new_content, "inserted"


class MarkerVerifyTool(BaseMCPTool):
    """
    MCP Tool for verifying markers in source files.

    Checks if files have required markers and reports missing ones.
    """

    @property
    def name(self) -> str:
        return "vetka_verify_markers"

    @property
    def description(self) -> str:
        return (
            "Verify @status/@phase markers in files or directories. "
            "Returns list of files with missing or incomplete markers."
        )

    @property
    def schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "File or directory path to verify"
                },
                "recursive": {
                    "type": "boolean",
                    "description": "Search subdirectories",
                    "default": True
                }
            },
            "required": ["path"]
        }

    def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Verify markers in files."""
        try:
            path_str = arguments.get("path", "")
            recursive = arguments.get("recursive", True)

            if not path_str:
                return {"success": False, "error": "path is required", "result": None}

            path = Path(path_str)
            if not path.is_absolute():
                project_root = Path(__file__).parent.parent.parent.parent
                path = project_root / path_str

            if not path.exists():
                return {"success": False, "error": f"Path not found: {path}", "result": None}

            # Collect files
            files = []
            if path.is_file():
                files = [path]
            else:
                pattern = "**/*" if recursive else "*"
                for ext in SUPPORTED_EXTENSIONS:
                    files.extend(path.glob(f"{pattern}{ext}"))

            # Verify each file
            results = {
                "complete": [],
                "missing_status": [],
                "missing_phase": [],
                "no_markers": [],
                "total": len(files)
            }

            for file_path in files:
                try:
                    content = file_path.read_text(encoding="utf-8")
                    has_status = bool(re.search(r'@status:', content))
                    has_phase = bool(re.search(r'@phase:', content))

                    rel_path = str(file_path.relative_to(path.parent if path.is_file() else path))

                    if has_status and has_phase:
                        results["complete"].append(rel_path)
                    elif has_status:
                        results["missing_phase"].append(rel_path)
                    elif has_phase:
                        results["missing_status"].append(rel_path)
                    else:
                        results["no_markers"].append(rel_path)

                except Exception as e:
                    logger.warning(f"[Marker] Could not read {file_path}: {e}")

            # Summary
            complete_count = len(results["complete"])
            coverage = (complete_count / results["total"] * 100) if results["total"] > 0 else 0

            return {
                "success": True,
                "result": {
                    **results,
                    "coverage_percent": round(coverage, 1),
                    "summary": f"{complete_count}/{results['total']} files have complete markers ({coverage:.1f}%)"
                },
                "error": None
            }

        except Exception as e:
            logger.error(f"[Marker] Verify error: {e}")
            return {"success": False, "error": str(e), "result": None}


# Tool instances for registration
marker_tool = MarkerTool()
marker_verify_tool = MarkerVerifyTool()


def register_marker_tools(server) -> None:
    """Register marker tools with MCP server."""
    from mcp.types import Tool

    tools = [
        Tool(
            name=marker_tool.name,
            description=marker_tool.description,
            inputSchema=marker_tool.schema
        ),
        Tool(
            name=marker_verify_tool.name,
            description=marker_verify_tool.description,
            inputSchema=marker_verify_tool.schema
        )
    ]

    logger.info(f"[MCP] Registered {len(tools)} marker tools")
    return tools
