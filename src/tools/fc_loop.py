"""
Function Calling Loop — Shared Async FC Utility for Pipeline & Orchestrator.

Phase 123.1: Extracted from orchestrator_with_elisya.py:_call_llm_with_tools_loop.
Gives pipeline agents (especially coder) the ability to call read-only tools
(vetka_read_file, vetka_search_semantic, etc.) during LLM generation.

MARKER_123.1_FC_LOOP: Core FC loop
MARKER_123.1_SCHEMAS: Hardcoded tool schemas for pipeline coder

@status: active
@phase: 123.1
@depends: provider_registry (call_model_v2), executor (SafeToolExecutor), base_tool (ToolCall, ToolResult)
@used_by: agent_pipeline.py, orchestrator_with_elisya.py (future refactor)
"""

import json
import logging
import re
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

from src.tools.executor import SafeToolExecutor
from src.tools.base_tool import ToolCall, ToolResult

# Lazy import for call_model_v2 to avoid circular imports at module load
# Tests can patch src.tools.fc_loop.call_model_v2 directly
call_model_v2 = None
Provider = None

def _ensure_provider_imports():
    """Lazy-load provider_registry on first use."""
    global call_model_v2, Provider
    if call_model_v2 is None:
        from src.elisya.provider_registry import call_model_v2 as _call, Provider as _prov
        call_model_v2 = _call
        Provider = _prov

logger = logging.getLogger(__name__)

# --- Constants ---

PIPELINE_CODER_TOOLS = [
    "vetka_read_file",
    "vetka_search_semantic",
    "vetka_search_files",
    "vetka_list_files",
]

MAX_FC_TURNS_CODER = 3
MAX_FC_TURNS_DEFAULT = 5
MAX_AUTO_READ_CHARS = 6000  # Max chars for auto-injected file content

# MARKER_123.1_SCHEMAS: Hardcoded OpenAI-format tool schemas for pipeline coder.
# Using hardcoded schemas avoids circular imports with MCP bridge and is more reliable.
# These match SAFE_FUNCTION_CALLING_TOOLS in llm_call_tool.py.
CODER_TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "vetka_read_file",
            "description": "Read file content from VETKA project. Returns full file content with line numbers.",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Path to the file to read (relative to project root)"
                    }
                },
                "required": ["file_path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "vetka_search_semantic",
            "description": "Semantic search in VETKA knowledge base using Qdrant vector search. Search for concepts, ideas, or topics across all indexed documents.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query — concept, idea, or topic to find"
                    },
                    "limit": {
                        "type": "number",
                        "description": "Max number of results (default: 5)"
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "vetka_search_files",
            "description": "Search for files by name or content pattern using ripgrep-style search. Fast full-text search across the codebase.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query (text pattern or regex)"
                    },
                    "search_type": {
                        "type": "string",
                        "description": "Type of search: 'content' (default) or 'filename'"
                    },
                    "limit": {
                        "type": "number",
                        "description": "Max number of results (default: 10)"
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "vetka_list_files",
            "description": "List files in a directory or matching a pattern. Returns file paths with metadata.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Directory path to list (relative to project root)"
                    },
                    "pattern": {
                        "type": "string",
                        "description": "File pattern to filter (e.g., '*.tsx', '*.py')"
                    },
                    "recursive": {
                        "type": "boolean",
                        "description": "Search recursively in subdirectories"
                    }
                }
            }
        }
    },
]


# --- Helper Functions ---

def extract_tool_calls(response: Union[Dict, Any]) -> Optional[List[Dict]]:
    """
    Extract tool_calls from call_model_v2 response.
    Handles both dict (OpenRouter) and Pydantic (Ollama) response formats.

    MARKER_123.1B: Ported from orchestrator_with_elisya.py lines 1050-1058

    Returns:
        List of tool call dicts, or None if no tool calls.
    """
    tool_calls_data = None

    # Pydantic object from Ollama
    if hasattr(response, "message") and hasattr(response.message, "tool_calls"):
        tool_calls_data = response.message.tool_calls
    # Dict response (OpenRouter, call_model_v2)
    elif isinstance(response, dict):
        message = response.get("message", {})
        if isinstance(message, dict):
            tool_calls_data = message.get("tool_calls")
        # Some providers put tool_calls at top level
        if not tool_calls_data:
            tool_calls_data = response.get("tool_calls")

    # Filter out empty/None tool_calls
    if tool_calls_data and len(tool_calls_data) > 0:
        return tool_calls_data
    return None


def _parse_tool_call(tool_call_data: Any, index: int) -> Tuple[str, Dict, str]:
    """
    Parse a single tool call into (func_name, func_args, call_id).
    Handles both Pydantic and dict formats.

    MARKER_123.1C: Ported from orchestrator_with_elisya.py lines 1069-1081
    """
    if hasattr(tool_call_data, "function"):
        # Pydantic ToolCall object (Ollama)
        func_name = tool_call_data.function.name
        func_args = tool_call_data.function.arguments
        call_id = getattr(tool_call_data, "id", f"call_{index}")
    else:
        # Dict format (OpenRouter, OpenAI)
        function = tool_call_data.get("function", tool_call_data)
        func_name = function.get("name", "")
        func_args = function.get("arguments", {})
        call_id = tool_call_data.get("id", f"call_{index}")

    # Handle string arguments (some providers return JSON string)
    if isinstance(func_args, str):
        try:
            func_args = json.loads(func_args)
        except (json.JSONDecodeError, TypeError):
            func_args = {}

    return func_name, func_args, call_id


def _format_assistant_message(response: Union[Dict, Any], tool_calls_data: List) -> Dict:
    """
    Format assistant message for appending to conversation history.
    Must include tool_calls for the LLM to understand the conversation flow.

    MARKER_123.1D: Ported from orchestrator_with_elisya.py lines 1154-1168
    """
    if hasattr(response, "message") and hasattr(response.message, "model_dump"):
        return response.message.model_dump()
    elif hasattr(response, "message"):
        return {
            "role": "assistant",
            "content": response.message.content or "",
            "tool_calls": tool_calls_data,
        }
    elif isinstance(response, dict):
        msg = response.get("message", {})
        if isinstance(msg, dict):
            return msg
        return {"role": "assistant", "content": str(msg), "tool_calls": tool_calls_data}
    return {"role": "assistant", "content": "", "tool_calls": tool_calls_data}


# MARKER_124.1B: Clean text-format tool calls from final LLM output
_TEXT_TOOL_CALL_RE = re.compile(
    r'<tool_call>\s*<function=[^>]*>.*?</function>\s*</tool_call>',
    re.DOTALL
)

def _clean_text_tool_calls(content: str) -> str:
    """
    Remove text-format tool calls from LLM output.

    Some models (Qwen3-coder via Polza) output <tool_call>...</tool_call>
    as plain text even when tools=None on last turn. These are NOT real
    tool calls — just text the model generated instead of code.

    If cleaning removes ALL content, return original (better than empty).
    """
    if not content or '<tool_call>' not in content:
        return content

    cleaned = _TEXT_TOOL_CALL_RE.sub('', content).strip()

    if not cleaned:
        logger.warning("[FC Loop] Final response was entirely text tool_calls — returning as-is")
        return content

    if cleaned != content.strip():
        logger.info(f"[FC Loop] Cleaned text tool_calls from final response ({len(content)} → {len(cleaned)} chars)")

    return cleaned
# MARKER_124.1B_END


# MARKER_124.3A: Auto-read file content after search tool calls
# Problem: Coder calls vetka_search_semantic/files 3 times but never vetka_read_file.
# Fix: After search returns file paths, auto-read the most relevant file and
# append its content to the tool result. Coder sees paths + actual code in one turn.

_FILE_PATH_PATTERNS = [
    # Relative paths: src/main.py, client/src/store/useStore.ts
    re.compile(r'(?:^|["\s,])([a-zA-Z_][\w/\-]*\.(?:tsx?|jsx?|py|rs|toml|json|css|html|md))(?:["\s,]|$)', re.MULTILINE),
    # Absolute paths: /Users/.../file.py (common in VETKA search results)
    re.compile(r'(/[\w\-./]+\.(?:tsx?|jsx?|py|rs|toml|json|css|html|md))(?:["\s,]|$)', re.MULTILINE),
]

def _extract_file_paths(result_text: str) -> List[str]:
    """Extract file paths from search result text.

    Handles both relative and absolute paths. For absolute paths,
    converts to relative if they contain a known project root marker.
    """
    paths = []
    for pat in _FILE_PATH_PATTERNS:
        for m in pat.finditer(result_text):
            p = m.group(1).strip()
            if p and len(p) > 3 and '/' in p:
                paths.append(p)
    # Also parse JSON result format: {"file_path": "...", "path": "..."}
    try:
        data = json.loads(result_text) if isinstance(result_text, str) else result_text
        if isinstance(data, dict):
            r = data.get("result", data)
            if isinstance(r, list):
                for item in r:
                    if isinstance(item, dict):
                        for key in ("file_path", "path", "payload"):
                            val = item.get(key)
                            if isinstance(val, str) and '/' in val:
                                paths.append(val)
                            elif isinstance(val, dict) and "file_path" in val:
                                paths.append(val["file_path"])
            elif isinstance(r, str):
                pass
    except (json.JSONDecodeError, TypeError):
        pass

    # MARKER_124.3E: Also extract paths from formatted text lines
    # Pattern: "  /path/to/file.py (score: 0.9)"
    for line in result_text.split('\n'):
        line = line.strip()
        if line.startswith('/') or line.startswith('client/') or line.startswith('src/'):
            # Extract path before any parenthetical (score: ...)
            path_part = line.split('(')[0].strip()
            if '.' in path_part and '/' in path_part:
                paths.append(path_part)

    # Deduplicate while preserving order
    seen = set()
    unique = []
    for p in paths:
        if p not in seen:
            seen.add(p)
            unique.append(p)
    return unique


def _normalize_path(fpath: str) -> str:
    """Convert absolute paths to relative (VetkaReadFileTool expects relative)."""
    # Look for project root markers in absolute path
    for marker in ("vetka_live_03/", "VETKA_Project/vetka_live_03/"):
        idx = fpath.find(marker)
        if idx >= 0:
            return fpath[idx + len(marker):]
    # If starts with /, try stripping common prefixes
    if fpath.startswith("/"):
        # Last resort: return as-is, ReadFileTool will handle
        return fpath
    return fpath


def _is_useful_file(fpath: str) -> bool:
    """Skip files that are not useful for coder context (init, tests, docs)."""
    name = fpath.split("/")[-1] if "/" in fpath else fpath
    if name == "__init__.py":
        return False
    if name.startswith("test_"):
        return False
    return True


async def _auto_read_top_file(
    executor: SafeToolExecutor,
    file_paths: List[str],
    progress_callback: Optional[Callable] = None,
) -> Optional[str]:
    """
    Auto-read the first valid file from search results.
    Returns file content string or None.
    """
    # Filter to useful files and normalize paths
    candidates = [_normalize_path(p) for p in file_paths if _is_useful_file(p)]
    if not candidates:
        candidates = [_normalize_path(p) for p in file_paths[:2]]  # Fallback: try first 2

    for fpath in candidates[:3]:  # Try top 3 candidates
        try:
            call = ToolCall(
                tool_name="vetka_read_file",
                arguments={"file_path": fpath},
                agent_type="Dev",
                call_id="auto_read",
            )
            result = await executor.execute(call)
            if result.success and result.result:
                content = result.result if isinstance(result.result, str) else str(result.result)
                if len(content) > MAX_AUTO_READ_CHARS:
                    content = content[:MAX_AUTO_READ_CHARS] + f"\n... (truncated, {len(content)} total chars)"
                if progress_callback:
                    try:
                        await progress_callback("@coder", f"📖 Auto-read: {fpath}")
                    except Exception:
                        pass
                logger.info(f"[FC Loop] Auto-read {fpath}: {len(content)} chars")
                return f"\n\n--- AUTO-READ: {fpath} ---\n{content}"
        except Exception as e:
            logger.debug(f"[FC Loop] Auto-read failed for {fpath}: {e}")
            continue
    return None
# MARKER_124.3A_END


def get_coder_tool_schemas() -> List[Dict]:
    """
    Get OpenAI-format tool schemas for pipeline coder.
    Uses hardcoded schemas (Approach B from plan) for reliability.

    Returns:
        List of tool schemas in OpenAI function calling format.
    """
    return list(CODER_TOOL_SCHEMAS)  # Return copy to prevent mutation


# --- Core FC Loop ---

# MARKER_123.1_FC_LOOP
async def execute_fc_loop(
    model: str,
    messages: List[Dict],
    tool_schemas: List[Dict],
    max_turns: int = MAX_FC_TURNS_CODER,
    temperature: float = 0.4,
    max_tokens: int = 4000,
    provider_source: Optional[str] = None,
    progress_callback: Optional[Callable] = None,
) -> Dict[str, Any]:
    """
    Shared async Function Calling loop.

    Calls call_model_v2 directly (bypasses sync LLMCallTool wrapper).
    Executes tool calls via SafeToolExecutor between LLM turns.

    Args:
        model: LLM model name (e.g., "qwen/qwen3-coder")
        messages: Initial conversation messages (system + user)
        tool_schemas: OpenAI-format tool definitions
        max_turns: Maximum FC turns before stopping (default: 3 for coder)
        temperature: LLM temperature
        max_tokens: Max tokens per LLM call
        provider_source: Provider routing hint (e.g., "polza", "openrouter")
        progress_callback: Optional async callback for progress updates
                          Signature: async def(agent: str, message: str)

    Returns:
        Dict with keys:
            - content: Final text response from LLM
            - tool_executions: List of {name, args, result} for each tool call
            - turns_used: Number of FC turns completed
            - model: Model that produced the final response
    """
    _ensure_provider_imports()

    # Resolve provider
    provider_enum = None
    if provider_source and Provider is not None:
        try:
            provider_enum = Provider(provider_source)
        except (ValueError, KeyError):
            pass  # Let call_model_v2 auto-detect from model name

    # Copy messages to avoid mutation
    messages = list(messages)
    all_tool_executions = []
    fc_turns_completed = 0
    executor = SafeToolExecutor()

    # Initial LLM call with tools
    response = await call_model_v2(
        messages=messages,
        model=model,
        provider=provider_enum,
        source=provider_source,
        tools=tool_schemas,
        temperature=temperature,
        max_tokens=max_tokens,
    )

    response_model = model
    if isinstance(response, dict):
        response_model = response.get("model", model)

    # FC turn loop
    for turn in range(max_turns):
        tool_calls_data = extract_tool_calls(response)

        if not tool_calls_data:
            # LLM responded with final text, no more tool calls
            logger.info(f"[FC Loop] Turn {turn}: No tool calls, returning final response")
            break

        logger.info(f"[FC Loop] Turn {turn + 1}/{max_turns}: {len(tool_calls_data)} tool call(s)")

        # Execute each tool call
        tool_results = []
        for i, tc_data in enumerate(tool_calls_data):
            func_name, func_args, call_id = _parse_tool_call(tc_data, i)

            # Safety: only allow known coder tools
            if func_name not in PIPELINE_CODER_TOOLS:
                logger.warning(f"[FC Loop] Blocked tool '{func_name}' — not in PIPELINE_CODER_TOOLS")
                tool_results.append({
                    "role": "tool",
                    "tool_call_id": call_id,
                    "content": json.dumps({"success": False, "error": f"Tool '{func_name}' not available"})
                })
                continue

            # Emit progress
            if progress_callback:
                try:
                    file_path = func_args.get("file_path", func_args.get("query", ""))
                    await progress_callback("@coder", f"📖 {func_name}: {file_path}")
                except Exception:
                    pass  # Progress emission should never block

            # Execute via SafeToolExecutor
            call = ToolCall(
                tool_name=func_name,
                arguments=func_args,
                agent_type="Dev",
                call_id=call_id,
            )

            try:
                result = await executor.execute(call)

                all_tool_executions.append({
                    "name": func_name,
                    "args": func_args,
                    "result": {
                        "success": result.success,
                        "result": result.result,
                        "error": result.error,
                    }
                })

                # Format tool result for LLM
                # Truncate large results to avoid token explosion
                result_content = result.result
                if isinstance(result_content, str) and len(result_content) > 8000:
                    result_content = result_content[:8000] + "\n... (truncated)"
                elif isinstance(result_content, dict):
                    result_str = json.dumps(result_content)
                    if len(result_str) > 8000:
                        result_content = result_str[:8000] + "\n... (truncated)"

                # MARKER_124.3B: Auto-read file after search tool
                # If search returned file paths, auto-read top file and append content
                if func_name in ("vetka_search_semantic", "vetka_search_files"):
                    result_str = json.dumps(result_content) if not isinstance(result_content, str) else result_content
                    found_paths = _extract_file_paths(result_str)
                    if found_paths:
                        auto_content = await _auto_read_top_file(executor, found_paths, progress_callback)
                        if auto_content:
                            if isinstance(result_content, str):
                                result_content = result_content + auto_content
                            else:
                                result_content = json.dumps(result_content) + auto_content
                            all_tool_executions.append({
                                "name": "vetka_read_file",
                                "args": {"file_path": found_paths[0]},
                                "result": {"success": True, "result": "(auto-injected)", "error": None},
                            })
                # MARKER_124.3B_END

                tool_results.append({
                    "role": "tool",
                    "tool_call_id": call_id,
                    "content": json.dumps({
                        "success": result.success,
                        "result": result_content,
                        "error": result.error,
                    })
                })

            except Exception as e:
                logger.warning(f"[FC Loop] Tool execution failed: {func_name} — {e}")
                tool_results.append({
                    "role": "tool",
                    "tool_call_id": call_id,
                    "content": json.dumps({"success": False, "error": str(e)})
                })
                all_tool_executions.append({
                    "name": func_name,
                    "args": func_args,
                    "result": {"success": False, "result": None, "error": str(e)}
                })

        fc_turns_completed += 1

        # Append assistant message + tool results to history
        assistant_msg = _format_assistant_message(response, tool_calls_data)
        messages.append(assistant_msg)
        messages.extend(tool_results)

        # Call LLM again with tool results
        # On last allowed turn: don't pass tools to force text output
        is_last_turn = (turn >= max_turns - 1)
        next_tools = None if is_last_turn else tool_schemas

        # MARKER_124.1A: Force code output on last turn
        # Some models (Qwen3-coder) output <tool_call> as text even when tools=None.
        # Adding explicit instruction prevents this.
        if is_last_turn:
            messages.append({
                "role": "user",
                "content": (
                    "You have finished exploring the codebase. "
                    "Now write your final code implementation based on what you learned. "
                    "Output ONLY code. Do NOT call any more tools. Do NOT output <tool_call> tags."
                ),
            })

        response = await call_model_v2(
            messages=messages,
            model=model,
            provider=provider_enum,
            source=provider_source,
            tools=next_tools,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        if isinstance(response, dict):
            response_model = response.get("model", model)

    # Extract final content
    content = ""
    if isinstance(response, dict):
        msg = response.get("message", {})
        if isinstance(msg, dict):
            content = msg.get("content", "")
        elif hasattr(msg, "content"):
            content = msg.content or ""
    elif hasattr(response, "message"):
        content = response.message.content or ""

    # MARKER_124.1B: Clean up text-format tool calls from final response
    # Some models output <tool_call>...</tool_call> as plain text even on last turn
    content = _clean_text_tool_calls(content)

    # MARKER_124.4B: Recovery when cleanup leaves empty content
    # If model returned tool_calls as text (Qwen behavior) and cleanup stripped everything,
    # make one more LLM call with all collected context summarized.
    if not content.strip() and all_tool_executions:
        logger.warning(f"[FC Loop] Empty content after cleanup — attempting recovery call")
        try:
            # Build summary of everything coder learned from tools
            tool_context = _build_tool_context_summary(all_tool_executions)
            recovery_messages = [
                messages[0],  # Keep original system prompt
                {
                    "role": "user",
                    "content": (
                        f"{messages[1]['content']}\n\n"
                        f"Here is what you found from reading the codebase:\n{tool_context}\n\n"
                        "Based on this context, write the complete code implementation. "
                        "Output ONLY the code wrapped in ```language ... ``` blocks. "
                        "Do NOT call tools. Do NOT ask questions."
                    ),
                },
            ]
            if progress_callback:
                await progress_callback("@coder", "🔄 Recovery: generating code from collected context")

            recovery_response = await call_model_v2(
                messages=recovery_messages,
                model=model,
                provider=provider_enum,
                source=provider_source,
                tools=None,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            if isinstance(recovery_response, dict):
                msg = recovery_response.get("message", {})
                if isinstance(msg, dict):
                    content = msg.get("content", "")
                elif hasattr(msg, "content"):
                    content = msg.content or ""
                content = _clean_text_tool_calls(content)
                if content.strip():
                    logger.info(f"[FC Loop] Recovery succeeded: {len(content)} chars")
                else:
                    logger.warning("[FC Loop] Recovery also returned empty content")
        except Exception as e:
            logger.warning(f"[FC Loop] Recovery call failed: {e}")
    # MARKER_124.4B_END

    logger.info(f"[FC Loop] Completed: {len(all_tool_executions)} tool calls, content length={len(content)}")

    return {
        "content": content,
        "tool_executions": all_tool_executions,
        "turns_used": fc_turns_completed,
        "model": response_model,
    }


def _build_tool_context_summary(tool_executions: List[Dict]) -> str:
    """Build a concise summary of tool execution results for recovery prompt.

    MARKER_124.4B helper: When FC loop's last turn is empty (Qwen text tool_calls),
    we need to feed the collected context back to the model in a new call.
    """
    parts = []
    for te in tool_executions:
        name = te.get("name", "")
        args = te.get("args", {})
        result = te.get("result", {})

        if name == "vetka_read_file" and result.get("success"):
            file_path = args.get("file_path", "unknown")
            content = str(result.get("result", ""))
            # Truncate long file contents
            if len(content) > 3000:
                content = content[:3000] + "\n... (truncated)"
            parts.append(f"--- File: {file_path} ---\n{content}")
        elif name in ("vetka_search_semantic", "vetka_search_files") and result.get("success"):
            parts.append(f"--- Search results ---\n{str(result.get('result', ''))[:1000]}")

    return "\n\n".join(parts) if parts else "No relevant context collected from tools."

# MARKER_123.1_FC_LOOP_END
