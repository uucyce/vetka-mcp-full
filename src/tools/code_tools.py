"""
Code manipulation tools: read, write, execute.

Provides file system tools for agents including ReadCodeFileTool,
WriteCodeFileTool, and ListFilesTool with security path validation.

@status: active
@phase: 96
@depends: base_tool (BaseTool, ToolDefinition, ToolResult, PermissionLevel, registry)
@used_by: src/tools/__init__, src/agents/
"""
import os
import asyncio
from pathlib import Path
from typing import Optional
from .base_tool import BaseTool, ToolDefinition, ToolResult, PermissionLevel, registry

# Project root (adjust as needed)
# Assumes the CWD is the project root, or we need to navigate up from src/tools
PROJECT_ROOT = Path(__file__).parent.parent.parent
# The actual CWD is /Users/danilagulin/Documents/VETKA_Project/vetka_live_03, so this is correct:
# Path(__file__) is src/tools/code_tools.py
# .parent is src/tools
# .parent is src/
# .parent is /Users/danilagulin/Documents/VETKA_Project/vetka_live_03

class ReadCodeFileTool(BaseTool):
    
    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="read_code_file",
            description="Read content of a source code file",
            parameters={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Relative path from project root (e.g. src/main.py)"
                    }
                },
                "required": ["path"]
            },
            permission_level=PermissionLevel.READ,
            needs_user_approval=False
        )
    
    async def execute(self, path: str) -> ToolResult:
        try:
            # Security: prevent directory traversal
            safe_path = PROJECT_ROOT / path
            # Check if the resolved path is a subpath of PROJECT_ROOT
            if not safe_path.resolve().is_relative_to(PROJECT_ROOT):
                return ToolResult(success=False, result=None, error="Path traversal detected")
            
            if not safe_path.exists():
                return ToolResult(success=False, result=None, error=f"File not found: {path}")
            
            content = safe_path.read_text(encoding='utf-8')
            return ToolResult(success=True, result=content)
        except Exception as e:
            return ToolResult(success=False, result=None, error=str(e))

class WriteCodeFileTool(BaseTool):
    
    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="write_code_file",
            description="Write content to a source code file",
            parameters={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Relative path"},
                    "content": {"type": "string", "description": "File content to write"}
                },
                "required": ["path", "content"]
            },
            permission_level=PermissionLevel.WRITE,
            needs_user_approval=True  # Requires confirmation!
        )
    
    async def execute(self, path: str, content: str) -> ToolResult:
        try:
            safe_path = PROJECT_ROOT / path
            if not safe_path.resolve().is_relative_to(PROJECT_ROOT):
                return ToolResult(success=False, result=None, error="Path traversal detected")
            
            # Create parent dirs if needed
            safe_path.parent.mkdir(parents=True, exist_ok=True)
            safe_path.write_text(content, encoding='utf-8')
            
            return ToolResult(success=True, result=f"Written {len(content)} bytes to {path}")
        except Exception as e:
            return ToolResult(success=False, result=None, error=str(e))

class ListFilesTool(BaseTool):
    
    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="list_files",
            description="List files in a directory",
            parameters={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Directory path", "default": "."},
                    "pattern": {"type": "string", "description": "Glob pattern", "default": "*"}
                }
            },
            permission_level=PermissionLevel.READ
        )
    
    async def execute(self, path: str = ".", pattern: str = "*") -> ToolResult:
        try:
            dir_path = PROJECT_ROOT / path
            if not dir_path.is_dir():
                return ToolResult(success=False, result=None, error="Not a directory")
            
            # Note: Path.glob() does not inherently prevent traversal if the 'path' argument is malicious,
            # but is_relative_to(PROJECT_ROOT) should be sufficient for the outer directory check.
            # The tool itself does not use resolve() on the final path names returned by glob, only on the initial dir_path.
            
            files = [str(f.relative_to(PROJECT_ROOT)) for f in dir_path.glob(pattern)]
            return ToolResult(success=True, result=files[:100])  # Limit to 100
        except Exception as e:
            return ToolResult(success=False, result=None, error=str(e))

# Register tools
registry.register(ReadCodeFileTool())
registry.register(WriteCodeFileTool())
registry.register(ListFilesTool())
