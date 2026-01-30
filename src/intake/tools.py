"""
MCP Tools for content intake.

Provides MCP-compatible tools for URL processing and intake management:
- IntakeURLTool: Process URL and extract content
- ListIntakesTool: List recent intakes
- GetIntakeTool: Get full intake content

@status: active
@phase: 96
@depends: manager, src.mcp.tools.base_tool, asyncio
@used_by: src.mcp.tools, src.intake
"""
import asyncio
from typing import Any, Dict

from src.mcp.tools.base_tool import BaseMCPTool
from .manager import get_intake_manager


class IntakeURLTool(BaseMCPTool):
    """Process URL and extract content (YouTube, web pages)"""

    @property
    def name(self) -> str:
        return "vetka_intake_url"

    @property
    def description(self) -> str:
        return "Extract content from URL (YouTube video transcript, web article text)"

    @property
    def schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "URL to process (YouTube, web page)"
                },
                "transcribe": {
                    "type": "boolean",
                    "description": "For YouTube: transcribe if no subtitles (slower)"
                }
            },
            "required": ["url"]
        }

    def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        url = arguments.get("url", "")
        options = {
            "transcribe": arguments.get("transcribe", False)
        }

        manager = get_intake_manager()

        # Run async in sync context
        loop = asyncio.new_event_loop()
        try:
            result = loop.run_until_complete(manager.process_url(url, options))
            return {
                "success": True,
                "result": {
                    "source_type": result.source_type,
                    "title": result.title,
                    "text_preview": result.text[:2000] if result.text else "",
                    "text_length": len(result.text),
                    "author": result.author,
                    "duration_seconds": result.duration_seconds,
                    "metadata": result.metadata
                }
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
        finally:
            loop.close()


class ListIntakesTool(BaseMCPTool):
    """List processed content intakes"""

    @property
    def name(self) -> str:
        return "vetka_list_intakes"

    @property
    def description(self) -> str:
        return "List recent content intakes (YouTube, web pages)"

    @property
    def schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "source_type": {
                    "type": "string",
                    "description": "Filter by source (youtube, web)"
                },
                "limit": {
                    "type": "integer",
                    "description": "Number of results"
                }
            }
        }

    def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        manager = get_intake_manager()

        intakes = manager.list_intakes(
            source_type=arguments.get("source_type"),
            limit=arguments.get("limit", 10)
        )

        return {
            "success": True,
            "result": {
                "count": len(intakes),
                "intakes": intakes
            }
        }


class GetIntakeTool(BaseMCPTool):
    """Get full content of an intake"""

    @property
    def name(self) -> str:
        return "vetka_get_intake"

    @property
    def description(self) -> str:
        return "Get full text content of a processed intake"

    @property
    def schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "filename": {
                    "type": "string",
                    "description": "Intake filename from list_intakes"
                }
            },
            "required": ["filename"]
        }

    def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        manager = get_intake_manager()

        intake = manager.get_intake(arguments.get("filename", ""))
        if intake:
            return {
                "success": True,
                "result": intake
            }
        return {
            "success": False,
            "error": "Intake not found"
        }
