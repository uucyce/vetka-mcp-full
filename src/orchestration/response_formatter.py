"""
Response Formatter - Format agent responses with source citations

This module provides:
1. Source citation formatting
2. File reference formatting (clickable)
3. Tool result formatting
4. Response enrichment with VETKA context

@status: active
@phase: 96
@depends: json, re, dataclasses
@used_by: src.orchestration.orchestrator_with_elisya, src.api.handlers.chat_handler
"""

import re
import json
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class SourceCitation:
    """Represents a source citation"""

    path: str
    score: float = 0.0
    snippet: str = ""
    line_number: Optional[int] = None
    source_type: str = "file"  # file, search, tool


@dataclass
class FormattedResponse:
    """Formatted response with sources"""

    content: str
    sources: List[SourceCitation] = field(default_factory=list)
    tool_results: List[Dict] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class ResponseFormatter:
    """
    Formats agent responses for rich UI display.

    Features:
    - Adds source citations from semantic search results
    - Formats file references as clickable links
    - Formats tool execution results
    - Provides markdown-compatible output
    """

    # File reference pattern: detects paths like src/main.py or ./config.json
    FILE_REF_PATTERN = re.compile(
        r"(?<![`\[])("
        r"(?:\.{0,2}/)?"  # Optional ./ or ../
        r"(?:[\w\-]+/)*"  # Directory path
        r"[\w\-]+\.[a-zA-Z0-9]{1,10}"  # filename.ext
        r")(?![`\]])"
    )

    @staticmethod
    def format_file_reference(path: str, line_number: Optional[int] = None) -> str:
        """
        Create a clickable file reference.

        Args:
            path: File path
            line_number: Optional line number

        Returns:
            Markdown-formatted file reference
        """
        filename = path.split("/")[-1]
        if line_number:
            return f"[`{filename}:{line_number}`]({path}#L{line_number})"
        return f"[`{filename}`]({path})"

    @staticmethod
    def format_code_block(
        content: str, language: str = "", max_lines: int = 1000
    ) -> str:
        """
        Format code with syntax highlighting.

        Args:
            content: Code content
            language: Programming language for highlighting
            max_lines: Maximum lines to show (INCREASED TO 1000)

        Returns:
            Markdown code block
        """
        lines = content.split("\n")
        # MARKER_TRUNCATION_FIX: NO LIMITS for artifacts
        # truncated = len(lines) > max_lines
        # if truncated:
        #     content = "\n".join(lines[:max_lines])
        #     content += f"\n\n... [{len(lines) - max_lines} more lines]"

        return f"```{language}\n{content}\n```"

    @classmethod
    def add_source_citations(
        cls, response: str, sources: List[Dict], max_sources: int = 5
    ) -> str:
        """
        Add source citations to response.

        Args:
            response: Agent response text
            sources: List of source dicts with path, score, snippet

        Returns:
            Response with appended source section
        """
        if not sources:
            return response

        # Deduplicate and sort by score
        seen_paths = set()
        unique_sources = []
        for src in sources:
            path = src.get("path", "")
            if path and path not in seen_paths:
                seen_paths.add(path)
                unique_sources.append(src)

        unique_sources.sort(key=lambda x: x.get("score", 0), reverse=True)
        unique_sources = unique_sources[:max_sources]

        if not unique_sources:
            return response

        # Build citations section
        citations = ["\n\n---\n**Sources:**\n"]

        for i, src in enumerate(unique_sources, 1):
            path = src.get("path", "unknown")
            score = src.get("score", 0)
            snippet = src.get("snippet", "")[:100].replace("\n", " ")

            # Format score as percentage
            score_pct = f"{score * 100:.0f}%" if score <= 1 else f"{score:.1f}"

            citations.append(f"{i}. [`{path}`]({path}) (relevance: {score_pct})")
            if snippet:
                citations.append(f"   > _{snippet}..._")
            citations.append("")

        return response + "\n".join(citations)

    @classmethod
    def format_tool_result(cls, tool_name: str, result: Dict) -> str:
        """
        Format a tool execution result.

        Args:
            tool_name: Name of the executed tool
            result: Tool result dict with success, result, error

        Returns:
            Formatted result string
        """
        if not result.get("success"):
            error = result.get("error", "Unknown error")
            return f"**{tool_name}** failed: {error}"

        data = result.get("result", {})

        # Format based on tool type
        if tool_name == "read_code_file":
            content = data if isinstance(data, str) else str(data)
            # MARKER_90.2.1_START: Remove all limits for models
            # NO LIMITS - Let models write full responses
            # MAX_RESPONSE_BYTES = 100 * 1024  # 100KB
            # if len(content.encode('utf-8')) > MAX_RESPONSE_BYTES:
            #     content = content[:MAX_RESPONSE_BYTES] + "\n\n[Response truncated at 100KB for safety]"
            return cls.format_code_block(content, "")
            # MARKER_90.2_END

        elif tool_name == "search_semantic":
            results = data.get("results", []) if isinstance(data, dict) else []
            if not results:
                return f'**{tool_name}:** No results for "{data.get("query", "")}"'

            output = [f"**Semantic Search:** {data.get('query', '')}"]
            for r in results[:5]:
                output.append(
                    f"- [`{r.get('path', 'unknown')}`]({r.get('path', '')}) (score: {r.get('score', 0):.2f})"
                )
            return "\n".join(output)

        elif tool_name == "search_codebase":
            matches = data if isinstance(data, list) else []
            if not matches:
                return f"**{tool_name}:** No matches found"

            output = [f"**Code Search:** {len(matches)} matches"]
            for m in matches[:10]:
                file_ref = cls.format_file_reference(
                    m.get("file", ""), int(m.get("line", 0))
                )
                content = m.get("content", "")[:80]
                output.append(f"- {file_ref}: `{content}`")
            return "\n".join(output)

        elif tool_name == "list_files":
            files = (
                data.get("files", [])
                if isinstance(data, dict)
                else (data if isinstance(data, list) else [])
            )
            total = (
                data.get("total", len(files)) if isinstance(data, dict) else len(files)
            )
            folder = data.get("folder", ".") if isinstance(data, dict) else "."

            output = [f"**Files in** `{folder}` ({total} total):"]
            for f in files[:20]:
                if isinstance(f, dict):
                    path = f.get("path", str(f))
                    size = f.get("size", 0)
                    output.append(f"- `{path}` ({size / 1024:.1f} KB)")
                else:
                    output.append(f"- `{f}`")

            if total > 20:
                output.append(f"... and {total - 20} more")
            return "\n".join(output)

        elif tool_name == "get_tree_context":
            if not isinstance(data, dict):
                return f"**{tool_name}:** {data}"

            path = data.get("path", "unknown")
            node_type = data.get("type", "file")
            parent = data.get("parent", "")
            children = data.get("children", [])
            siblings = data.get("siblings", [])
            related = data.get("related", [])
            metadata = data.get("metadata", {})

            output = [f"**Tree Context:** `{path}` ({node_type})"]
            output.append(f"- Parent: `{parent}`")

            if children:
                output.append(
                    f"- Children ({len(children)}): {', '.join(f'`{c}`' for c in children[:5])}"
                )
            if siblings:
                output.append(
                    f"- Siblings ({len(siblings)}): {', '.join(f'`{s}`' for s in siblings[:5])}"
                )
            if related:
                output.append("- Related files:")
                for rel in related[:3]:
                    output.append(
                        f"  - [`{rel.get('path', '')}`]({rel.get('path', '')}) (similarity: {rel.get('score', 0):.2f})"
                    )
            if metadata:
                if "line_count" in metadata:
                    output.append(f"- Lines: {metadata['line_count']}")
                if "size_bytes" in metadata:
                    output.append(f"- Size: {metadata['size_bytes'] / 1024:.1f} KB")

            return "\n".join(output)

        elif tool_name == "get_file_info":
            if not isinstance(data, dict):
                return f"**{tool_name}:** {data}"

            output = [f"**File Info:** `{data.get('path', 'unknown')}`"]
            output.append(f"- Size: {data.get('size_human', 'unknown')}")
            output.append(f"- Lines: {data.get('line_count', 'unknown')}")
            output.append(f"- Modified: {data.get('modified', 'unknown')}")
            output.append(f"- Extension: {data.get('extension', 'unknown')}")
            return "\n".join(output)

        elif tool_name == "validate_syntax":
            if not isinstance(data, dict):
                return f"**{tool_name}:** {data}"

            if data.get("valid"):
                return f"**Syntax Valid**"
            else:
                error = data.get("error", "Unknown error")
                line = data.get("line", "")
                return f"**Syntax Error** (line {line}): {error}"

        elif tool_name == "run_tests":
            if not isinstance(data, dict):
                return f"**{tool_name}:** {data}"

            passed = data.get("passed", 0)
            failed = data.get("failed", 0)
            output_text = data.get("output", "")[:500]

            status = "" if failed == 0 else ""
            output = [f"**Test Results:** {status} {passed} passed, {failed} failed"]
            if output_text:
                output.append(cls.format_code_block(output_text, ""))
            return "\n".join(output)

        elif tool_name == "create_artifact":
            if not isinstance(data, dict):
                return f"**{tool_name}:** {data}"

            return f"**Artifact Created:** {data.get('name', 'unknown')} ({data.get('type', 'unknown')}, {data.get('size', 0)} bytes)"

        # Default JSON formatting
        try:
            return f"**{tool_name}:**\n```json\n{json.dumps(data, indent=2, ensure_ascii=False)[:2000]}\n```"
        except:
            return f"**{tool_name}:** {str(data)[:500]}"

    @classmethod
    def extract_tool_calls(cls, response: str) -> List[Dict]:
        """
        Extract tool calls from agent response.

        Tool calls are formatted as:
        ```tool
        {"name": "tool_name", "args": {"arg1": "value1"}}
        ```

        Returns:
            List of parsed tool call dicts
        """
        pattern = r"```tool\s*\n({.*?})\s*\n```"
        matches = re.findall(pattern, response, re.DOTALL)

        tool_calls = []
        for match in matches:
            try:
                call = json.loads(match)
                if "name" in call:
                    tool_calls.append(
                        {
                            "name": call.get("name"),
                            "args": call.get("args", call.get("arguments", {})),
                        }
                    )
            except json.JSONDecodeError:
                continue

        return tool_calls

    @classmethod
    def enrich_with_file_links(cls, response: str, base_path: str = "") -> str:
        """
        Convert file paths in response to clickable links.

        Args:
            response: Response text
            base_path: Base path prefix for relative paths

        Returns:
            Response with clickable file references
        """

        def replace_match(match):
            path = match.group(1)
            # Skip if already a link
            if f"[`{path}`]" in response or f"[{path}]" in response:
                return match.group(0)
            # Skip common false positives
            if path in ["e.g.", "i.e.", "etc.", "vs."]:
                return match.group(0)
            return cls.format_file_reference(path)

        return cls.FILE_REF_PATTERN.sub(replace_match, response)

    @classmethod
    def format_full_response(
        cls,
        response: str,
        tool_results: List[Dict] = None,
        sources: List[Dict] = None,
        add_file_links: bool = True,
    ) -> FormattedResponse:
        """
        Full response formatting pipeline.

        Args:
            response: Raw agent response
            tool_results: List of tool execution results
            sources: List of source citations
            add_file_links: Whether to convert file paths to links

        Returns:
            FormattedResponse with formatted content and metadata
        """
        formatted = response

        # 1. Format tool results if any
        formatted_tools = []
        if tool_results:
            for tr in tool_results:
                tool_name = tr.get("name", "unknown")
                result = tr.get("result", {})
                formatted_result = cls.format_tool_result(tool_name, result)
                formatted_tools.append(
                    {"name": tool_name, "formatted": formatted_result, "raw": result}
                )

        # 2. Add file links
        if add_file_links:
            formatted = cls.enrich_with_file_links(formatted)

        # 3. Add source citations
        all_sources = sources or []

        # Extract sources from search_semantic tool results
        if tool_results:
            for tr in tool_results:
                if tr.get("name") == "search_semantic":
                    result = tr.get("result", {})
                    if isinstance(result, dict) and result.get("success"):
                        data = result.get("result", {})
                        if isinstance(data, dict):
                            all_sources.extend(data.get("results", []))

        formatted = cls.add_source_citations(formatted, all_sources)

        # Build response object
        source_citations = [
            SourceCitation(
                path=s.get("path", ""),
                score=s.get("score", 0),
                snippet=s.get("snippet", ""),
                source_type="search",
            )
            for s in all_sources
        ]

        return FormattedResponse(
            content=formatted,
            sources=source_citations,
            tool_results=formatted_tools,
            metadata={
                "formatted_at": datetime.now().isoformat(),
                "source_count": len(source_citations),
                "tool_count": len(formatted_tools),
            },
        )


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================


def format_response(
    response: str, tool_results: List[Dict] = None, sources: List[Dict] = None
) -> str:
    """
    Convenience function for simple response formatting.

    Returns formatted string (not FormattedResponse object).
    """
    result = ResponseFormatter.format_full_response(response, tool_results, sources)
    return result.content


def format_with_sources(response: str, sources: List[Dict]) -> str:
    """Add source citations to response."""
    return ResponseFormatter.add_source_citations(response, sources)


def format_tool_output(tool_name: str, result: Dict) -> str:
    """Format a single tool result."""
    return ResponseFormatter.format_tool_result(tool_name, result)


# ============================================================================
# EXPORTS
# ============================================================================

__all__ = [
    "ResponseFormatter",
    "FormattedResponse",
    "SourceCitation",
    "format_response",
    "format_with_sources",
    "format_tool_output",
]
