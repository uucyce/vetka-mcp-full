"""
REFLEX Registry — Tool Catalog with metadata for intelligent tool selection.

MARKER_172.P1.REGISTRY

REFLEX = Reactive Execution & Function Linking EXchange
Layer 1: Static catalog of all VETKA tools with intent tags, trigger patterns,
cost metadata, and permission levels. Used by REFLEX Scorer (Layer 2) to
rank tools for context-aware selection.

Part of VETKA OS:
  VETKA > REFLEX > Registry (this file)
"""

import json
import logging
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Dict, List, Optional, Set

logger = logging.getLogger(__name__)

# Canonical location for the auto-generated tool catalog
CATALOG_PATH = Path(__file__).parent.parent.parent / "data" / "reflex" / "tool_catalog.json"

# Deprecated tool aliases → new canonical names
DEPRECATED_ALIASES: Dict[str, str] = {
    # Phase 129: VETKA → MYCELIUM migration
    "vetka_task_board": "mycelium_task_board",
    "vetka_task_dispatch": "mycelium_task_dispatch",
    "vetka_task_import": "mycelium_task_import",
    "vetka_mycelium_pipeline": "mycelium_pipeline",
    "vetka_heartbeat_tick": "mycelium_heartbeat_tick",
    "vetka_heartbeat_status": "mycelium_heartbeat_status",
    # Phase 114.1: Unified naming
    "search_semantic": "vetka_search_semantic",
    "camera_focus": "vetka_camera_focus",
    "create_artifact": "vetka_edit_artifact",
}


@dataclass
class ToolEntry:
    """Single tool in the REFLEX catalog."""
    tool_id: str
    namespace: str                         # vetka, mycelium, internal, cut
    kind: str                              # search, file_op, orchestration, memory, media, system
    description: str = ""
    intent_tags: List[str] = field(default_factory=list)
    trigger_patterns: Dict = field(default_factory=lambda: {
        "file_types": ["*"],
        "phase_types": ["research", "fix", "build"],
        "keywords": [],
    })
    cost: Dict = field(default_factory=lambda: {
        "latency_ms": 100,
        "tokens": 0,
        "risk_level": "read_only",         # read_only, write, execute, external
    })
    permission: str = "READ"               # READ, WRITE, EXECUTE, EXTERNAL, ADMIN
    roles: List[str] = field(default_factory=list)   # which agent roles can use this
    deprecated_aliases: List[str] = field(default_factory=list)
    active: bool = True

    def matches_intent(self, query_tags: List[str]) -> float:
        """Fuzzy match: fraction of query_tags found in this tool's intent_tags."""
        if not query_tags or not self.intent_tags:
            return 0.0
        query_set = set(t.lower() for t in query_tags)
        tool_set = set(t.lower() for t in self.intent_tags)
        intersection = query_set & tool_set
        return len(intersection) / len(query_set) if query_set else 0.0

    def matches_phase(self, phase_type: str) -> bool:
        """Check if this tool is relevant for the given phase type."""
        phases = self.trigger_patterns.get("phase_types", ["*"])
        return "*" in phases or phase_type.lower() in [p.lower() for p in phases]

    def matches_keywords(self, text: str) -> float:
        """Score based on keyword matches in text."""
        keywords = self.trigger_patterns.get("keywords", [])
        if not keywords or not text:
            return 0.0
        text_lower = text.lower()
        hits = sum(1 for kw in keywords if kw.lower() in text_lower)
        return hits / len(keywords) if keywords else 0.0


class ReflexRegistry:
    """
    REFLEX Layer 1: Tool catalog manager.

    Loads tool catalog from JSON, provides lookup by ID, role, intent, and phase.
    Resolves deprecated aliases to canonical names.
    """

    def __init__(self, catalog_path: Optional[Path] = None):
        self._catalog_path = catalog_path or CATALOG_PATH
        self._tools: Dict[str, ToolEntry] = {}
        self._loaded = False

    def load(self) -> "ReflexRegistry":
        """Load catalog from JSON file."""
        if not self._catalog_path.exists():
            logger.warning(f"[REFLEX] Catalog not found: {self._catalog_path}")
            self._loaded = True
            return self

        try:
            with open(self._catalog_path, "r") as f:
                data = json.load(f)

            tools_list = data.get("tools", [])
            for entry in tools_list:
                tool = ToolEntry(
                    tool_id=entry["tool_id"],
                    namespace=entry.get("namespace", "unknown"),
                    kind=entry.get("kind", "unknown"),
                    description=entry.get("description", ""),
                    intent_tags=entry.get("intent_tags", []),
                    trigger_patterns=entry.get("trigger_patterns", {}),
                    cost=entry.get("cost", {}),
                    permission=entry.get("permission", "READ"),
                    roles=entry.get("roles", []),
                    deprecated_aliases=entry.get("deprecated_aliases", []),
                    active=entry.get("active", True),
                )
                self._tools[tool.tool_id] = tool

            self._loaded = True
            logger.info(f"[REFLEX] Loaded {len(self._tools)} tools from catalog")

        except Exception as e:
            logger.error(f"[REFLEX] Failed to load catalog: {e}")
            self._loaded = True

        return self

    @property
    def tool_count(self) -> int:
        return len(self._tools)

    def get_tool(self, tool_id: str) -> Optional[ToolEntry]:
        """Get tool by ID, resolving deprecated aliases."""
        canonical = DEPRECATED_ALIASES.get(tool_id, tool_id)
        return self._tools.get(canonical)

    def get_all_tools(self) -> List[ToolEntry]:
        """Return all active tools."""
        return [t for t in self._tools.values() if t.active]

    def get_tool_ids(self) -> Set[str]:
        """Return set of all tool IDs."""
        return set(self._tools.keys())

    def get_tools_for_role(self, role: str) -> List[ToolEntry]:
        """Get tools available for a specific agent role."""
        return [
            t for t in self._tools.values()
            if t.active and (role in t.roles or "all" in t.roles)
        ]

    def get_tools_by_intent(self, intent_tags: List[str], min_score: float = 0.3) -> List[ToolEntry]:
        """Find tools matching intent tags (fuzzy). Returns sorted by match score desc."""
        scored = []
        for tool in self._tools.values():
            if not tool.active:
                continue
            score = tool.matches_intent(intent_tags)
            if score >= min_score:
                scored.append((tool, score))
        scored.sort(key=lambda x: x[1], reverse=True)
        return [t for t, _ in scored]

    def get_tools_by_kind(self, kind: str) -> List[ToolEntry]:
        """Get tools by kind (search, file_op, orchestration, etc.)."""
        return [
            t for t in self._tools.values()
            if t.active and t.kind == kind
        ]

    def get_tools_for_phase(self, phase_type: str) -> List[ToolEntry]:
        """Get tools relevant for a phase type (fix, build, research)."""
        return [
            t for t in self._tools.values()
            if t.active and t.matches_phase(phase_type)
        ]

    def resolve_alias(self, name: str) -> str:
        """Resolve deprecated tool name to canonical."""
        return DEPRECATED_ALIASES.get(name, name)

    def has_tool(self, tool_id: str) -> bool:
        """Check if tool exists (resolving aliases)."""
        canonical = DEPRECATED_ALIASES.get(tool_id, tool_id)
        return canonical in self._tools

    def to_dict(self) -> Dict:
        """Export catalog as dict (for JSON serialization)."""
        return {
            "version": "1.0.0",
            "tool_count": len(self._tools),
            "tools": [asdict(t) for t in self._tools.values()],
        }


# Singleton instance
_registry_instance: Optional[ReflexRegistry] = None


def get_reflex_registry() -> ReflexRegistry:
    """Get or create the singleton REFLEX Registry."""
    global _registry_instance
    if _registry_instance is None:
        _registry_instance = ReflexRegistry().load()
    return _registry_instance


def reset_reflex_registry():
    """Reset singleton (for testing)."""
    global _registry_instance
    _registry_instance = None
