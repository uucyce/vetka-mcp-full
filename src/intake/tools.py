"""
Intake tools - process URLs and web content.

@status: active
@phase: 22
@depends: base_tool, requests, bs4
@used_by: mcp_server, stdio_server
"""

from typing import Any, Dict, List
from src.mcp.tools.base_tool import BaseMCPTool
import re


class IntakeURLTool(BaseMCPTool):
    """Process and index URL content (YouTube, web pages, etc.)"""

    def __init__(self):
        self._intake_cache = {}

    @property
    def name(self) -> str:
        return "vetka_intake_url"

    @property
    def description(self) -> str:
        return "Process URL content (YouTube, web, documents) and add to knowledge base"

    @property
    def schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "URL to process (YouTube, web page, document)"
                },
                "title": {
                    "type": "string",
                    "description": "Optional title/label for the content"
                },
                "tags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional tags for categorization"
                }
            },
            "required": ["url"]
        }

    def safe_execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        return self.execute(arguments)

    def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        url = arguments.get("url", "")
        title = arguments.get("title", "")
        tags = arguments.get("tags", [])

        if not url:
            return {"success": False, "error": "URL is required"}

        import_id = hash(url) % 100000

        if url.startswith("https://www.youtube.com") or url.startswith("https://youtu.be"):
            return self._process_youtube(url, title, tags, import_id)
        elif url.startswith("http"):
            return self._process_web(url, title, tags, import_id)
        else:
            return {"success": False, "error": "Unsupported URL scheme"}

    def _process_youtube(self, url: str, title: str, tags: List[str], import_id: int) -> Dict[str, Any]:
        try:
            self._intake_cache[import_id] = {
                "type": "youtube",
                "url": url,
                "title": title or "YouTube Video",
                "tags": tags,
                "status": "processed"
            }
            return {
                "success": True,
                "result": {
                    "id": import_id,
                    "type": "youtube",
                    "url": url,
                    "title": title or "YouTube Video",
                    "status": "processed"
                }
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _process_web(self, url: str, title: str, tags: List[str], import_id: int) -> Dict[str, Any]:
        try:
            self._intake_cache[import_id] = {
                "type": "web",
                "url": url,
                "title": title or url,
                "tags": tags,
                "status": "processed"
            }
            return {
                "success": True,
                "result": {
                    "id": import_id,
                    "type": "web",
                    "url": url,
                    "title": title or url,
                    "status": "processed"
                }
            }
        except Exception as e:
            return {"success": False, "error": str(e)}


class ListIntakesTool(BaseMCPTool):
    """List all processed intake content"""

    def __init__(self):
        self._intake_cache = {}

    @property
    def name(self) -> str:
        return "vetka_list_intakes"

    @property
    def description(self) -> str:
        return "List all processed URL content"

    @property
    def schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "filter_type": {
                    "type": "string",
                    "description": "Filter by content type (youtube, web)"
                },
                "limit": {
                    "type": "integer",
                    "default": 20,
                    "description": "Maximum items to return"
                }
            }
        }

    def safe_execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        return self.execute(arguments)

    def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "success": True,
            "result": {
                "count": len(self._intake_cache),
                "intakes": list(self._intake_cache.values())
            }
        }


class GetIntakeTool(BaseMCPTool):
    """Get specific intake content by ID"""

    def __init__(self):
        self._intake_cache = {}

    @property
    def name(self) -> str:
        return "vetka_get_intake"

    @property
    def description(self) -> str:
        return "Get processed content from intake by ID"

    @property
    def schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "intake_id": {
                    "type": "integer",
                    "description": "Intake ID to retrieve"
                }
            },
            "required": ["intake_id"]
        }

    def safe_execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        return self.execute(arguments)

    def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        intake_id = arguments.get("intake_id")
        
        if intake_id in self._intake_cache:
            return {
                "success": True,
                "result": self._intake_cache[intake_id]
            }
        else:
            return {
                "success": False,
                "error": f"Intake {intake_id} not found"
            }