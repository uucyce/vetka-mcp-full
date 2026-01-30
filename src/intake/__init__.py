"""
VETKA Content Intake Module.

Universal content extraction from various sources:
- YouTube videos (metadata + transcript)
- Web pages (article text extraction)

Usage:
    from src.intake import get_intake_manager

    manager = get_intake_manager()
    result = await manager.process_url("https://youtube.com/watch?v=...")

MCP Tools:
    - vetka_intake_url: Process URL and extract content
    - vetka_list_intakes: List processed intakes
    - vetka_get_intake: Get full intake content

@status: active
@phase: 96
@depends: base, youtube, web, manager, tools
@used_by: src.mcp.tools, src.api
"""

from .base import ContentIntake, IntakeResult, ContentType
from .youtube import YouTubeIntake
from .web import WebIntake
from .manager import IntakeManager, get_intake_manager
from .tools import IntakeURLTool, ListIntakesTool, GetIntakeTool

__all__ = [
    # Base
    'ContentIntake',
    'IntakeResult',
    'ContentType',
    # Processors
    'YouTubeIntake',
    'WebIntake',
    # Manager
    'IntakeManager',
    'get_intake_manager',
    # Tools
    'IntakeURLTool',
    'ListIntakesTool',
    'GetIntakeTool',
]
