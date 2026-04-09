"""
Unified capability matrix for stream/tool execution planning.

MARKER_152.CAP_MATRIX.RUNTIME
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Dict, Optional


@dataclass
class CapabilitySnapshot:
    model: str
    provider: str
    model_source: Optional[str] = None
    stream_tokens: bool = True
    tool_calling: bool = False
    tool_calling_in_stream: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def build_capability_snapshot(
    *,
    model: str,
    provider_name: str,
    provider_instance: Optional[Any],
    model_source: Optional[str] = None,
) -> CapabilitySnapshot:
    """
    Build effective capability snapshot from provider + model.

    Note:
    - `tool_calling_in_stream` is currently False by design in VETKA stream path.
    - This field is explicit to avoid false claims in chat and to support future upgrades.
    """
    supports_tools = bool(getattr(provider_instance, "supports_tools", False))
    return CapabilitySnapshot(
        model=model,
        provider=str(provider_name),
        model_source=model_source,
        stream_tokens=True,
        tool_calling=supports_tools,
        tool_calling_in_stream=False,
    )


def resolve_tool_execution_mode(
    *,
    wants_tools: bool,
    snapshot: CapabilitySnapshot,
    tools_executed: bool = False,
) -> str:
    """
    Resolve mode label for socket metadata/UI.
    """
    if tools_executed:
        return "enabled_non_stream"
    if wants_tools and snapshot.tool_calling and snapshot.tool_calling_in_stream:
        return "enabled_stream"
    return "disabled_stream"
