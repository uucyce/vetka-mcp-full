"""
Tests for MARKER_198.P2.1: MCP Bridge Pre/Post Tool Hooks

@phase: 198.P2.1
@depends: src/mcp/bridge_hooks.py
"""

import pytest
from src.mcp.bridge_hooks import (
    register_pre_hook,
    register_post_hook,
    clear_hooks,
    run_pre_hooks,
    run_post_hooks,
    get_hook_stats,
)


@pytest.fixture(autouse=True)
def reset_hooks():
    """Clear all hooks before each test."""
    clear_hooks()
    yield
    clear_hooks()


# ---------------------------------------------------------------------------
# Registration tests
# ---------------------------------------------------------------------------

def test_register_pre_hook():
    """Register a pre-hook and verify stats show 1."""
    async def my_pre_hook(tool_name, args, session_id):
        return None

    register_pre_hook(my_pre_hook)
    stats = get_hook_stats()
    assert stats["pre_hooks"] == 1
    assert stats["post_hooks"] == 0


def test_register_post_hook():
    """Register a post-hook and verify stats show 1."""
    async def my_post_hook(tool_name, args, result_text, session_id, error):
        return None

    register_post_hook(my_post_hook)
    stats = get_hook_stats()
    assert stats["pre_hooks"] == 0
    assert stats["post_hooks"] == 1


# ---------------------------------------------------------------------------
# Pre-hook behaviour tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_pre_hook_proceeds():
    """Hook returning None → args unchanged, early_return is None."""
    async def passthrough(tool_name, args, session_id):
        return None

    register_pre_hook(passthrough)
    args = {"query": "test"}
    returned_args, early = await run_pre_hooks("vetka_search_semantic", args, "sid-1")
    assert early is None
    assert returned_args == {"query": "test"}


@pytest.mark.asyncio
async def test_pre_hook_blocks():
    """Hook returning a dict → early_return is that dict, tool not called."""
    block_value = {"blocked": True, "reason": "test block"}

    async def blocker(tool_name, args, session_id):
        return block_value

    register_pre_hook(blocker)
    args = {"query": "test"}
    returned_args, early = await run_pre_hooks("vetka_search_semantic", args, "sid-1")
    assert early is block_value


# ---------------------------------------------------------------------------
# Post-hook behaviour tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_post_hook_no_suggestion():
    """Post-hook returning None → run_post_hooks returns None."""
    async def silent(tool_name, args, result_text, session_id, error):
        return None

    register_post_hook(silent)
    result = await run_post_hooks("vetka_search_semantic", {}, "some result", "sid-1")
    assert result is None


@pytest.mark.asyncio
async def test_post_hook_with_suggestion():
    """Post-hook returning 'try X' → run_post_hooks returns that string."""
    async def suggester(tool_name, args, result_text, session_id, error):
        return "try X"

    register_post_hook(suggester)
    result = await run_post_hooks("vetka_search_semantic", {}, "some result", "sid-1")
    assert result == "try X"


@pytest.mark.asyncio
async def test_post_hook_multiple_suggestions_joined():
    """Multiple post-hooks with suggestions → joined with newlines."""
    async def hook_a(tool_name, args, result_text, session_id, error):
        return "suggestion A"

    async def hook_b(tool_name, args, result_text, session_id, error):
        return "suggestion B"

    register_post_hook(hook_a)
    register_post_hook(hook_b)
    result = await run_post_hooks("vetka_search_semantic", {}, "some result", "sid-1")
    assert result == "suggestion A\nsuggestion B"


# ---------------------------------------------------------------------------
# Error resilience tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_hook_error_non_fatal():
    """Hook raising Exception → no propagation, returns None."""
    async def broken_hook(tool_name, args, session_id):
        raise RuntimeError("boom")

    register_pre_hook(broken_hook)
    # Should not raise; should return (args, None)
    args = {"query": "test"}
    returned_args, early = await run_pre_hooks("vetka_search_semantic", args, "sid-1")
    assert early is None
    assert returned_args == args


@pytest.mark.asyncio
async def test_post_hook_error_non_fatal():
    """Post-hook raising Exception → no propagation, returns None."""
    async def broken_post(tool_name, args, result_text, session_id, error):
        raise ValueError("post boom")

    register_post_hook(broken_post)
    result = await run_post_hooks("vetka_search_semantic", {}, "result", "sid-1")
    assert result is None


# ---------------------------------------------------------------------------
# Clear hooks test
# ---------------------------------------------------------------------------

def test_clear_hooks():
    """Register hooks, clear, verify stats show 0."""
    async def pre(tool_name, args, session_id):
        return None

    async def post(tool_name, args, result_text, session_id, error):
        return None

    register_pre_hook(pre)
    register_post_hook(post)
    assert get_hook_stats() == {"pre_hooks": 1, "post_hooks": 1}

    clear_hooks()
    assert get_hook_stats() == {"pre_hooks": 0, "post_hooks": 0}
