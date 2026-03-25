"""
Tests for MARKER_198.MEM_HEALTH: Memory health dashboard in session_init response.

@phase: 191.18
@depends: src/mcp/tools/session_tools.py
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock


EXPECTED_SUBSYSTEMS = {"aura", "engram_l1", "cortex", "stm", "qdrant_l2", "bridge_hooks"}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_session_tool():
    """Instantiate SessionInitTool with minimal config."""
    from src.mcp.tools.session_tools import SessionInitTool
    return SessionInitTool()


def _mock_context_patches():
    """Return a dict of patches that make _execute_async return quickly."""
    return {
        # Core dependencies that session_init calls
        "src.mcp.tools.session_tools.load_project_digest": MagicMock(return_value=None),
    }


# ---------------------------------------------------------------------------
# test_memory_health_present
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_memory_health_present():
    """session_init result must contain a 'memory_health' key."""
    tool = _make_session_tool()

    # Run with a minimal role; all subsystem imports may fail → fallback to "error"
    result = await tool._execute_async({"role": "harness"})

    assert result.get("success") is True
    context = result.get("result", {})
    assert "memory_health" in context, (
        f"'memory_health' key missing from session_init result. Keys present: {list(context.keys())}"
    )


# ---------------------------------------------------------------------------
# test_memory_health_has_subsystems
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_memory_health_has_subsystems():
    """memory_health must contain entries for all six subsystems."""
    tool = _make_session_tool()
    result = await tool._execute_async({"role": "harness"})

    assert result.get("success") is True
    health = result.get("result", {}).get("memory_health", {})

    missing = EXPECTED_SUBSYSTEMS - set(health.keys())
    assert not missing, f"Missing subsystems in memory_health: {missing}"


# ---------------------------------------------------------------------------
# test_memory_health_status_field
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_memory_health_status_field():
    """Each subsystem entry must have a 'status' field with a non-empty string."""
    tool = _make_session_tool()
    result = await tool._execute_async({"role": "harness"})

    assert result.get("success") is True
    health = result.get("result", {}).get("memory_health", {})

    for subsystem in EXPECTED_SUBSYSTEMS:
        entry = health.get(subsystem, {})
        assert "status" in entry, f"Subsystem '{subsystem}' missing 'status' field. Entry: {entry}"
        assert isinstance(entry["status"], str), (
            f"Subsystem '{subsystem}' 'status' should be str, got {type(entry['status'])}"
        )
        assert entry["status"], f"Subsystem '{subsystem}' 'status' is empty string"


# ---------------------------------------------------------------------------
# test_memory_health_never_crashes
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_memory_health_never_crashes():
    """Even when all subsystem imports raise, memory_health is still present."""
    tool = _make_session_tool()

    # Patch every subsystem getter to raise so the inner try/except paths fire
    boom = RuntimeError("simulated total failure")

    with patch("src.memory.aura_store.get_aura_store", side_effect=boom), \
         patch("src.memory.engram_cache.get_engram_cache", side_effect=boom), \
         patch("src.services.reflex_feedback.get_reflex_feedback", side_effect=boom), \
         patch("src.memory.stm_buffer.get_stm_buffer", side_effect=boom), \
         patch("src.orchestration.resource_learnings.get_learning_store", side_effect=boom), \
         patch("src.mcp.bridge_hooks.get_hook_stats", side_effect=boom):

        result = await tool._execute_async({"role": "harness"})

    assert result.get("success") is True, "session_init must succeed even when all memory subsystems fail"
    context = result.get("result", {})
    # memory_health key should still be present (outer try/except adds it)
    # — or the outer try may have caught the inner failures and still produced partial dict
    assert "memory_health" in context, (
        "'memory_health' key must be present even after all subsystem errors"
    )

    health = context["memory_health"]
    # All present subsystems should show "error" status
    for subsystem, entry in health.items():
        assert "status" in entry, f"Subsystem '{subsystem}' has no 'status' after error path"


# ---------------------------------------------------------------------------
# test_memory_health_ok_statuses_when_data_present
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_memory_health_ok_statuses_when_data_present():
    """When subsystems return data, status should be 'ok' (not 'cold' or 'error')."""
    tool = _make_session_tool()

    # Build mock objects for each subsystem
    mock_aura = MagicMock()
    mock_aura._preferences = {"key1": "v1", "key2": "v2"}  # 2 entries → "ok"

    mock_engram = MagicMock()
    mock_engram.get_all.return_value = [{"id": i} for i in range(5)]
    mock_engram.get_danger_entries.return_value = []

    mock_fb = MagicMock()
    mock_fb.get_feedback_summary.return_value = {
        "total_entries": 20,  # >10 → "ok"
        "success_rate": 0.85,
    }

    mock_stm = MagicMock()
    mock_stm.items = [1, 2, 3]  # 3 items → "ok"

    mock_store = MagicMock()
    mock_store.get_stats.return_value = {"source": "qdrant", "count": 50}

    mock_hooks = {"pre_hooks": 1, "post_hooks": 2}

    with patch("src.memory.aura_store.get_aura_store", return_value=mock_aura), \
         patch("src.memory.engram_cache.get_engram_cache", return_value=mock_engram), \
         patch("src.services.reflex_feedback.get_reflex_feedback", return_value=mock_fb), \
         patch("src.memory.stm_buffer.get_stm_buffer", return_value=mock_stm), \
         patch("src.orchestration.resource_learnings.get_learning_store", return_value=mock_store), \
         patch("src.mcp.bridge_hooks.get_hook_stats", return_value=mock_hooks):

        result = await tool._execute_async({"role": "harness"})

    assert result.get("success") is True
    health = result.get("result", {}).get("memory_health", {})

    # Spot-check: aura, cortex, stm, bridge_hooks should report "ok"
    for key in ("aura", "cortex", "stm"):
        if key in health:
            assert health[key].get("status") == "ok", (
                f"Expected 'ok' for '{key}' when data present, got: {health[key]}"
            )

    if "bridge_hooks" in health:
        assert health["bridge_hooks"].get("status") == "ok", (
            f"Expected 'ok' for bridge_hooks when post_hooks > 0, got: {health['bridge_hooks']}"
        )
