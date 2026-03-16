# MARKER_138.S2_2_AURA_BRIDGE
"""Jarvis bridge to AURA memory and prompt enrichment."""

from __future__ import annotations

import asyncio
from typing import Any, Dict, Optional


class JarvisEngramBridge:
    """Collects compact user context for Jarvis MCP requests.

    Uses AURA store (src.memory.aura_store) for user preferences
    and JarvisPromptEnricher for context enrichment.
    """

    def __init__(self, enricher=None, memory=None):
        self._enricher = enricher
        self._memory = memory

    def _get_enricher(self):
        if self._enricher is None:
            from src.memory.jarvis_prompt_enricher import get_jarvis_enricher
            self._enricher = get_jarvis_enricher()
        return self._enricher

    def _get_memory(self):
        if self._memory is None:
            from src.memory.aura_store import get_aura_store
            self._memory = get_aura_store()
        return self._memory

    async def build_context(self, user_id: str, request: str) -> Dict[str, Any]:
        """Build compact memory context without blocking event loop."""
        loop = asyncio.get_running_loop()

        def _collect() -> Dict[str, Any]:
            enricher = self._get_enricher()
            memory = self._get_memory()

            user_context = enricher._get_user_context(  # noqa: SLF001 - intentional internal API reuse
                user_id=user_id,
                include_categories=[
                    "communication_style",
                    "project_highlights",
                    "temporal_patterns",
                ],
            )

            focus = memory.get_preference("default", user_id, "project_highlights", "current_project")
            detail = memory.get_preference("default", user_id, "communication_style", "detail_level")

            return {
                "user_id": user_id,
                "request": request,
                "context": user_context,
                "focus": focus,
                "detail_level": detail,
            }

        return await loop.run_in_executor(None, _collect)


_bridge_singleton: Optional[JarvisEngramBridge] = None


def get_jarvis_engram_bridge() -> JarvisEngramBridge:
    global _bridge_singleton
    if _bridge_singleton is None:
        _bridge_singleton = JarvisEngramBridge()
    return _bridge_singleton
