"""
MARKER_198.P2.1: MCP Bridge Pre/Post Tool Hooks

Extensible hook system for vetka_mcp_bridge.py call_tool().
Pre-hooks can enrich arguments or block calls.
Post-hooks can record outcomes, suggest workarounds on failure.

Hooks are registered via register_pre_hook() / register_post_hook().
All hooks are async and non-fatal — errors are logged, never propagate.

@status: active
@phase: 198.P2.1
@depends: src/mcp/vetka_mcp_bridge.py
"""

import logging
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger("VETKA_BRIDGE_HOOKS")

# Hook type signatures:
# PreHook:  async (tool_name, args, session_id) -> Optional[dict]
#           Returns None to proceed, or dict to override/block (returned as early result)
# PostHook: async (tool_name, args, result_text, session_id, error) -> Optional[str]
#           Returns None normally, or str workaround suggestion to append

PreHook = Callable  # async (str, Dict, str) -> Optional[Dict]
PostHook = Callable  # async (str, Dict, str, str, Optional[Exception]) -> Optional[str]

_pre_hooks: List[PreHook] = []
_post_hooks: List[PostHook] = []


def register_pre_hook(fn: PreHook) -> None:
    """Register a pre-tool-call hook."""
    _pre_hooks.append(fn)
    logger.info(f"[BridgeHooks] Pre-hook registered: {fn.__name__}")


def register_post_hook(fn: PostHook) -> None:
    """Register a post-tool-call hook."""
    _post_hooks.append(fn)
    logger.info(f"[BridgeHooks] Post-hook registered: {fn.__name__}")


def clear_hooks() -> None:
    """Clear all hooks (for testing)."""
    _pre_hooks.clear()
    _post_hooks.clear()


async def run_pre_hooks(
    tool_name: str,
    arguments: Dict[str, Any],
    session_id: str,
) -> Tuple[Dict[str, Any], Optional[Any]]:
    """Run all pre-hooks. Returns (args, early_return_or_None).

    If a pre-hook returns a non-None value, that value is used as
    early return from call_tool() — the actual tool is NOT called.
    """
    for hook in _pre_hooks:
        try:
            result = await hook(tool_name, arguments, session_id)
            if result is not None:
                logger.info(f"[BridgeHooks] Pre-hook {hook.__name__} blocked {tool_name}")
                return arguments, result
        except Exception as e:
            logger.debug(f"[BridgeHooks] Pre-hook {hook.__name__} error (non-fatal): {e}")
    return arguments, None


async def run_post_hooks(
    tool_name: str,
    arguments: Dict[str, Any],
    result_text: str,
    session_id: str,
    error: Optional[Exception] = None,
) -> Optional[str]:
    """Run all post-hooks. Returns combined workaround suggestions or None.

    Each post-hook can return an Optional[str] suggestion. All non-None
    suggestions are joined with newlines and returned.
    """
    suggestions = []
    for hook in _post_hooks:
        try:
            suggestion = await hook(tool_name, arguments, result_text, session_id, error)
            if suggestion:
                suggestions.append(suggestion)
        except Exception as e:
            logger.debug(f"[BridgeHooks] Post-hook {hook.__name__} error (non-fatal): {e}")
    return "\n".join(suggestions) if suggestions else None


def get_hook_stats() -> Dict[str, int]:
    """Return count of registered hooks."""
    return {
        "pre_hooks": len(_pre_hooks),
        "post_hooks": len(_post_hooks),
    }
