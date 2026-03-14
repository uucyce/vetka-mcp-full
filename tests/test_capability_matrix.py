from src.elisya.capability_matrix import (
    build_capability_snapshot,
    resolve_tool_execution_mode,
)


class _ProviderWithTools:
    supports_tools = True


class _ProviderNoTools:
    supports_tools = False


def test_build_capability_snapshot_with_tools_provider():
    snap = build_capability_snapshot(
        model="x-ai/grok-4.1-fast",
        provider_name="polza",
        provider_instance=_ProviderWithTools(),
        model_source="polza",
    )
    assert snap.stream_tokens is True
    assert snap.tool_calling is True
    assert snap.tool_calling_in_stream is False


def test_resolve_tool_execution_mode_prefers_executed_non_stream():
    snap = build_capability_snapshot(
        model="test-model",
        provider_name="openrouter",
        provider_instance=_ProviderWithTools(),
    )
    mode = resolve_tool_execution_mode(
        wants_tools=True,
        snapshot=snap,
        tools_executed=True,
    )
    assert mode == "enabled_non_stream"


def test_resolve_tool_execution_mode_disabled_when_no_tools():
    snap = build_capability_snapshot(
        model="test-model",
        provider_name="ollama",
        provider_instance=_ProviderNoTools(),
    )
    mode = resolve_tool_execution_mode(
        wants_tools=True,
        snapshot=snap,
        tools_executed=False,
    )
    assert mode == "disabled_stream"
