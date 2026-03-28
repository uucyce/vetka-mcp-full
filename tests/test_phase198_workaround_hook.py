"""
Tests for MARKER_198.P2.4: Post-failure memory trigger — REFLEX workaround lookup.
"""
import pytest
from unittest.mock import patch, MagicMock


# Test 1: Hook returns None on success (no error, no Error prefix)
@pytest.mark.asyncio
async def test_no_suggestion_on_success():
    from src.services.reflex_workaround_hook import failure_workaround_post_hook
    result = await failure_workaround_post_hook(
        "vetka_search_files", {"q": "test"}, "Found 5 results", "sess1", error=None
    )
    assert result is None


# Test 2: Hook fires on error (Exception passed)
@pytest.mark.asyncio
async def test_fires_on_exception():
    from src.services.reflex_workaround_hook import failure_workaround_post_hook
    # Mock ENGRAM to return a danger entry
    mock_entry = MagicMock()
    mock_entry.key = "vetka_read_file"
    mock_entry.value = "Low success rate: 0% over 85 calls | fix"
    mock_entry.hit_count = 5

    mock_cache = MagicMock()
    mock_cache.get_danger_entries.return_value = [mock_entry]

    with patch("src.services.reflex_workaround_hook.get_engram_cache", return_value=mock_cache):
        result = await failure_workaround_post_hook(
            "vetka_read_file", {}, "Error: file not found", "sess1", error=Exception("fail")
        )
    assert result is not None
    assert "Known issue" in result


# Test 3: Hook fires on "Error" prefix in result_text (no exception)
@pytest.mark.asyncio
async def test_fires_on_error_prefix():
    from src.services.reflex_workaround_hook import failure_workaround_post_hook
    with patch("src.services.reflex_workaround_hook.get_engram_cache") as mock_gc:
        mock_gc.return_value.get_danger_entries.return_value = []
        # Mock CORTEX with low success rate
        mock_fb = MagicMock()
        mock_fb.get_feedback_summary.return_value = {
            "per_tool": {"vetka_edit_file": {"count": 10, "success_rate": 0.1}}
        }
        with patch("src.services.reflex_workaround_hook.get_reflex_feedback", return_value=mock_fb):
            result = await failure_workaround_post_hook(
                "vetka_edit_file", {}, "Error: edit failed", "sess1", error=None
            )
    assert result is not None
    assert "10%" in result or "CORTEX" in result


# Test 4: No ENGRAM + no CORTEX data → None
@pytest.mark.asyncio
async def test_no_data_returns_none():
    from src.services.reflex_workaround_hook import failure_workaround_post_hook
    with patch("src.services.reflex_workaround_hook.get_engram_cache") as mock_gc:
        mock_gc.return_value.get_danger_entries.return_value = []
        mock_fb = MagicMock()
        mock_fb.get_feedback_summary.return_value = {"per_tool": {}}
        with patch("src.services.reflex_workaround_hook.get_reflex_feedback", return_value=mock_fb):
            result = await failure_workaround_post_hook(
                "some_tool", {}, "Error: unknown", "sess1", error=Exception("x")
            )
    assert result is None


# Test 5: ENGRAM/CORTEX errors are non-fatal
@pytest.mark.asyncio
async def test_subsystem_errors_non_fatal():
    from src.services.reflex_workaround_hook import failure_workaround_post_hook
    with patch("src.services.reflex_workaround_hook.get_engram_cache", side_effect=RuntimeError("boom")):
        with patch("src.services.reflex_workaround_hook.get_reflex_feedback", side_effect=RuntimeError("boom")):
            result = await failure_workaround_post_hook(
                "broken_tool", {}, "Error: fail", "sess1", error=Exception("x")
            )
    assert result is None  # graceful degradation


# Test 6: register_workaround_hook works
def test_register_hook():
    from src.mcp.bridge_hooks import clear_hooks, get_hook_stats
    clear_hooks()
    from src.services.reflex_workaround_hook import register_workaround_hook
    register_workaround_hook()
    stats = get_hook_stats()
    assert stats["post_hooks"] == 1
    clear_hooks()
