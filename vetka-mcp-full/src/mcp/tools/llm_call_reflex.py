"""Helpers for REFLEX-aware direct tool calling in MCP LLM tools.

MARKER_173.P6.DIRECT_LOCAL_TOOL_PATH
"""

from __future__ import annotations

import copy
import json
import logging
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple

logger = logging.getLogger(__name__)

READ_ONLY_TASK_BOARD_ACTIONS = {"list", "get", "summary", "active_agents"}
TASK_BOARD_TOOL_NAMES = {"vetka_task_board", "mycelium_task_board"}
EDIT_FILE_TOOL_NAME = "vetka_edit_file"
LOCAL_MODEL_EXTRA_SAFE_TOOLS = {
    "select_best_local_qwen_model",
    "vetka_task_board",
    "mycelium_task_board",
}


def extend_safe_tool_allowlist(base_tools: Set[str]) -> Set[str]:
    """Return a copy of the allowlist with local-model helper tools added."""
    return set(base_tools) | LOCAL_MODEL_EXTRA_SAFE_TOOLS


def get_effective_allowed_tool_names(
    base_tools: Set[str],
    *,
    allow_edit_file_writes: bool = False,
) -> Set[str]:
    """Build the request-specific tool allowlist."""
    allowed = set(base_tools)
    if allow_edit_file_writes:
        allowed.add(EDIT_FILE_TOOL_NAME)
    return allowed


def is_opted_in_write_tool(
    tool_name: str,
    *,
    allow_edit_file_writes: bool = False,
) -> bool:
    """True when a normally blocked write tool is explicitly enabled."""
    return bool(allow_edit_file_writes and tool_name == EDIT_FILE_TOOL_NAME)


def infer_model_tier(
    provider_name: str,
    model: str,
    explicit_tier: Optional[str] = None,
) -> str:
    """Infer REFLEX filter tier for direct MCP calls."""
    if explicit_tier in {"bronze", "silver", "gold"}:
        return explicit_tier

    provider = str(provider_name or "").strip().lower()
    model_name = str(model or "").strip().lower()
    if provider == "ollama":
        if any(token in model_name for token in ("qwen3.5", "qwen3:32b", "qwen3:30b", "qwen2.5:32b")):
            return "silver"
        return "bronze"
    return "silver"


def maybe_apply_reflex_to_direct_tools(
    *,
    arguments: Dict[str, Any],
    messages: List[Dict[str, Any]],
    tools: Optional[List[Dict[str, Any]]],
    provider_name: str,
) -> Tuple[List[Dict[str, Any]], Optional[List[Dict[str, Any]]], List[Dict[str, Any]], Dict[str, Any]]:
    """Apply REFLEX scoring/filtering to direct local-model tool schemas."""
    metadata = {
        "enabled": False,
        "applied": False,
        "provider": provider_name,
        "phase": arguments.get("_reflex_phase", "research"),
        "role": arguments.get("_reflex_role", "coder"),
        "model_tier": None,
        "tool_count_before": len(tools or []),
        "tool_count_after": len(tools or []),
        "recommended_tools": [],
    }

    if not tools or str(provider_name).lower() != "ollama":
        return messages, tools, [], metadata

    try:
        from src.services.reflex_integration import reflex_filter_schemas, reflex_pre_fc, _is_enabled

        if not _is_enabled():
            return messages, tools, [], metadata

        metadata["enabled"] = True
        allow_task_board_writes = bool(arguments.get("_allow_task_board_writes"))
        task_text = _extract_task_text(arguments)
        phase = metadata["phase"]
        role = metadata["role"]
        model_tier = infer_model_tier(
            provider_name=provider_name,
            model=arguments.get("model", ""),
            explicit_tier=arguments.get("_reflex_model_tier"),
        )
        metadata["model_tier"] = model_tier

        subtask = _make_reflex_subtask(task_text, phase, role)
        reflex_recs = reflex_pre_fc(subtask, phase_type=phase, agent_role=role)
        metadata["recommended_tools"] = [rec.get("tool_id") for rec in reflex_recs]

        safe_tools = sanitize_tool_schemas(
            tools,
            allow_task_board_writes=allow_task_board_writes,
        )
        filtered_tools = reflex_filter_schemas(
            safe_tools,
            subtask=subtask,
            phase_type=phase,
            agent_role=role,
            model_tier=model_tier,
        )
        ordered_tools = reorder_tool_schemas(filtered_tools, reflex_recs)
        hinted_messages = inject_reflex_system_hint(messages, reflex_recs)

        metadata["applied"] = True
        metadata["tool_count_after"] = len(ordered_tools)
        return hinted_messages, ordered_tools, reflex_recs, metadata
    except Exception as exc:
        logger.debug("[REFLEX DIRECT] Non-fatal direct-tool path error: %s", exc)
        return messages, tools, [], metadata


def sanitize_tool_schemas(
    tools: Sequence[Dict[str, Any]],
    *,
    allow_task_board_writes: bool = False,
) -> List[Dict[str, Any]]:
    """Restrict task-board schemas to read-only actions unless explicitly enabled."""
    sanitized: List[Dict[str, Any]] = []
    for tool_def in tools:
        if not isinstance(tool_def, dict):
            sanitized.append(tool_def)
            continue

        tool_name = tool_def.get("function", {}).get("name", "")
        if tool_name not in TASK_BOARD_TOOL_NAMES or allow_task_board_writes:
            sanitized.append(copy.deepcopy(tool_def))
            continue

        sanitized_tool = copy.deepcopy(tool_def)
        function = sanitized_tool.setdefault("function", {})
        parameters = function.setdefault("parameters", {"type": "object", "properties": {}})
        properties = parameters.setdefault("properties", {})
        action_property = properties.setdefault("action", {"type": "string"})
        action_property["enum"] = sorted(READ_ONLY_TASK_BOARD_ACTIONS)
        description = function.get("description", "")
        read_only_note = (
            " Read-only in direct local-model calls: only "
            "list/get/summary/active_agents actions are allowed."
        )
        if read_only_note.strip() not in description:
            function["description"] = f"{description}{read_only_note}".strip()
        sanitized.append(sanitized_tool)
    return sanitized


def reorder_tool_schemas(
    tools: Sequence[Dict[str, Any]],
    reflex_recs: Sequence[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Move recommended tools to the front without dropping any filtered schema."""
    if not tools or not reflex_recs:
        return list(tools)

    rank = {
        rec.get("tool_id"): idx
        for idx, rec in enumerate(reflex_recs)
        if rec.get("tool_id")
    }

    def _sort_key(tool_def: Dict[str, Any]) -> Tuple[int, int]:
        name = tool_def.get("function", {}).get("name", "")
        return (rank.get(name, len(rank)), 0)

    return sorted(list(tools), key=_sort_key)


def inject_reflex_system_hint(
    messages: List[Dict[str, Any]],
    reflex_recs: Sequence[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Inject a compact system hint so local models see the top REFLEX path."""
    if not reflex_recs:
        return messages

    hint_lines = ["[REFLEX Direct Recommendations]"]
    for rec in reflex_recs[:3]:
        tool_id = rec.get("tool_id", "")
        reason = rec.get("reason", "")
        if tool_id:
            if reason:
                hint_lines.append(f"- {tool_id}: {reason}")
            else:
                hint_lines.append(f"- {tool_id}")
    hint = "\n".join(hint_lines)

    updated = list(messages)
    for idx, message in enumerate(updated):
        if message.get("role") == "system":
            content = str(message.get("content", ""))
            if hint not in content:
                updated[idx] = {**message, "content": f"{content}\n\n{hint}".strip()}
            return updated

    return [{"role": "system", "content": hint}, *updated]


def filter_tool_calls(
    tool_calls: Sequence[Any],
    *,
    allowed_tool_names: Set[str],
    allow_task_board_writes: bool = False,
) -> List[Dict[str, Any]]:
    """Filter returned tool calls by allowlist and task-board action policy."""
    filtered: List[Dict[str, Any]] = []
    for tool_call in tool_calls:
        normalized = _normalize_tool_call(tool_call)
        if not normalized:
            continue
        function = normalized.get("function", {})
        tool_name = function.get("name", "")
        if tool_name not in allowed_tool_names:
            continue
        if (
            tool_name in TASK_BOARD_TOOL_NAMES
            and not allow_task_board_writes
            and not _is_task_board_tool_call_read_only(function.get("arguments"))
        ):
            logger.warning("[SECURITY] Filtered mutating task-board tool call '%s'", tool_name)
            continue
        filtered.append(normalized)
    return filtered


def _extract_task_text(arguments: Dict[str, Any]) -> str:
    messages = arguments.get("messages", [])
    for message in reversed(messages):
        if message.get("role") == "user":
            return str(message.get("content", ""))[:200]
    return ""


def _make_reflex_subtask(task_text: str, phase: str, role: str) -> Any:
    class _ReflexSubtask:
        def __init__(self, desc: str, ctx: Dict[str, Any]):
            self.description = desc
            self.context = ctx

    return _ReflexSubtask(task_text, {"phase_type": phase, "agent_role": role})


def _is_task_board_tool_call_read_only(raw_arguments: Any) -> bool:
    if raw_arguments is None:
        return False

    parsed: Any = raw_arguments
    if isinstance(raw_arguments, str):
        try:
            parsed = json.loads(raw_arguments)
        except Exception:
            return False

    if not isinstance(parsed, dict):
        return False

    return parsed.get("action") in READ_ONLY_TASK_BOARD_ACTIONS


def _normalize_tool_call(tool_call: Any) -> Optional[Dict[str, Any]]:
    if isinstance(tool_call, dict):
        function = tool_call.get("function", {})
        if not isinstance(function, dict):
            return None
        arguments = function.get("arguments", {})
        if isinstance(arguments, dict):
            function = {**function, "arguments": json.dumps(arguments)}
        return {
            "id": tool_call.get("id"),
            "type": tool_call.get("type", "function"),
            "function": function,
        }

    function = getattr(tool_call, "function", None)
    if function is None:
        return None

    tool_name = getattr(function, "name", "")
    raw_arguments = getattr(function, "arguments", {})
    if isinstance(raw_arguments, str):
        normalized_arguments = raw_arguments
    else:
        normalized_arguments = json.dumps(raw_arguments)

    return {
        "id": getattr(tool_call, "id", None),
        "type": getattr(tool_call, "type", "function") or "function",
        "function": {
            "name": tool_name,
            "arguments": normalized_arguments,
        },
    }
