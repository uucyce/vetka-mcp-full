"""MCP Compound Tools - Multi-step tool compositions.

Provides high-level compound operations that combine multiple atomic tools:
- vetka_research: semantic search -> read files -> summarize findings
- vetka_implement: plan implementation (delegates to workflow for execution)
- vetka_review: read file -> analyze -> suggest improvements

These tools enable more natural task descriptions by chaining low-level operations.

@status: active
@phase: 96
@depends: src/bridge (SemanticSearchTool, ReadFileTool)
@used_by: src/mcp/vetka_mcp_bridge.py, src/mcp/tools/__init__.py
"""

from typing import Dict, Any, List


async def vetka_research(topic: str, depth: str = "medium") -> Dict[str, Any]:
    """
    Research a topic: semantic search -> read files -> summarize.

    Args:
        topic: Research topic
        depth: "quick" (3 files), "medium" (7 files), "deep" (15 files)
    """
    from src.bridge import SemanticSearchTool, ReadFileTool

    limits = {"quick": 3, "medium": 7, "deep": 15}
    limit = limits.get(depth, 7)

    # Step 1: Semantic search
    search_tool = SemanticSearchTool()
    search_result = await search_tool.execute({"query": topic, "limit": limit})

    findings = []
    if "results" in search_result:
        # Step 2: Read top files
        read_tool = ReadFileTool()
        for item in search_result["results"][:limit]:
            file_path = item.get("path") or item.get("file_path")
            if file_path:
                try:
                    content = await read_tool.execute({"file_path": file_path})
                    findings.append({
                        "path": file_path,
                        "score": item.get("score", 0),
                        "content_preview": str(content)[:500]
                    })
                except Exception as e:
                    findings.append({"path": file_path, "error": str(e)})

    return {
        "topic": topic,
        "depth": depth,
        "files_searched": len(search_result.get("results", [])),
        "files_read": len(findings),
        "findings": findings
    }


async def vetka_implement(task: str, dry_run: bool = True) -> Dict[str, Any]:
    """
    Implement a task: plan -> code -> (optionally) write.

    Args:
        task: Implementation task description
        dry_run: If True, only preview changes
    """
    return {
        "task": task,
        "dry_run": dry_run,
        "status": "requires_agent_execution",
        "suggestion": "Use vetka_execute_workflow for full implementation"
    }


async def vetka_review(file_path: str) -> Dict[str, Any]:
    """
    Review a file: read -> analyze -> suggest improvements.
    """
    from src.bridge import ReadFileTool

    read_tool = ReadFileTool()
    content = await read_tool.execute({"file_path": file_path})

    return {
        "file_path": file_path,
        "content_length": len(str(content)),
        "status": "requires_agent_analysis",
        "content_preview": str(content)[:1000]
    }


def register_compound_tools(tool_list: List[Dict[str, Any]]):
    """Register compound tools with MCP bridge."""
    tool_list.extend([
        {
            "name": "vetka_research",
            "description": "Research a topic: semantic search -> read files -> summarize",
            "parameters": {
                "type": "object",
                "properties": {
                    "topic": {"type": "string", "required": True},
                    "depth": {"type": "string", "enum": ["quick", "medium", "deep"], "default": "medium"}
                }
            },
            "handler": vetka_research
        },
        {
            "name": "vetka_implement",
            "description": "Plan implementation for a task (use workflow for execution)",
            "parameters": {
                "type": "object",
                "properties": {
                    "task": {"type": "string", "required": True},
                    "dry_run": {"type": "boolean", "default": True}
                }
            },
            "handler": vetka_implement
        },
        {
            "name": "vetka_review",
            "description": "Review a file and suggest improvements",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {"type": "string", "required": True}
                }
            },
            "handler": vetka_review
        }
    ])
