"""
VETKA Phase 76.3 - User Preferences Schema
Dataclasses for JARVIS Memory personalization layer

@file user_memory.py
@status ACTIVE
@phase Phase 76.3 - JARVIS Memory Layer
@calledBy engram_user_memory.py, jarvis_prompt_enricher.py
@lastAudit 2026-01-20

Schema categories (from Grok #2 Research):
1. ViewportPatterns - 3D navigation preferences
2. TreeStructure - Code organization preferences
3. ProjectHighlights - Current focus areas
4. CommunicationStyle - Response formatting
5. TemporalPatterns - Time-based behavior
6. ToolUsagePatterns - Tool interaction patterns

All categories have:
- last_updated: ISO timestamp
- confidence: 0-1 based on observation count
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Dict, List, Optional, Any
import json


@dataclass
class ViewportPatterns:
    """
    User's viewport interaction patterns (from Grok #2).

    Tracks 3D navigation preferences:
    - zoom_levels: Most used zoom levels
    - focus_areas: Frequently visited folders/files
    - navigation_style: keyboard/mouse/voice
    """
    zoom_levels: List[float] = field(default_factory=lambda: [1.0, 1.5, 2.0])
    focus_areas: List[str] = field(default_factory=list)
    navigation_style: str = "keyboard-driven"  # keyboard-driven/mouse-driven/voice
    # MARKER_155.MEMORY.ENGRAM_DAG_PREFS.V1:
    # Cross-surface DAG layout intent profiles keyed by scope (MCC/VETKA shared).
    dag_layout_profiles: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    last_updated: str = field(default_factory=lambda: datetime.now().isoformat())
    confidence: float = 0.5  # 0-1, increases with usage

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class TreeStructure:
    """
    User's tree organization preferences (from Grok #2).

    Controls how code is displayed in 3D tree:
    - preferred_depth: Max depth before auto-collapse
    - grouping: How to group items (by-module/by-feature/by-time)
    - hidden_folders: Folders to hide by default
    - layout_mode: vertical/horizontal/hybrid
    """
    preferred_depth: int = 3
    grouping: str = "by-module"  # by-module/by-feature/by-time
    hidden_folders: List[str] = field(default_factory=lambda: [".venv", "node_modules", "__pycache__", ".git"])
    layout_mode: str = "vertical"  # vertical/horizontal/hybrid
    last_updated: str = field(default_factory=lambda: datetime.now().isoformat())
    confidence: float = 0.5

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ProjectHighlights:
    """
    User's project focus areas (from Grok #2).

    Tracks what the user is currently working on:
    - current_project: Active project name
    - priorities: Top priority areas
    - highlights: Project -> [important files] mapping
    """
    current_project: str = "vetka"
    priorities: List[str] = field(default_factory=lambda: ["learning", "3D viz", "agents"])
    highlights: Dict[str, List[str]] = field(default_factory=dict)
    last_updated: str = field(default_factory=lambda: datetime.now().isoformat())
    confidence: float = 0.5

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class CommunicationStyle:
    """
    User's communication preferences (from Grok #2).

    Adapts AI response style:
    - formality: 0=casual, 1=formal
    - detail_level: 0=concise, 1=verbose
    - prefers_russian: Language preference
    - response_length: short/medium/long
    """
    formality: float = 0.3  # 0=casual, 1=formal
    detail_level: float = 0.8  # 0=concise, 1=verbose
    prefers_russian: bool = True
    response_length: str = "medium"  # short/medium/long
    technical_depth: str = "high"  # low/medium/high (for code explanations)
    last_updated: str = field(default_factory=lambda: datetime.now().isoformat())
    confidence: float = 0.5

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class TemporalPatterns:
    """
    User's time-based patterns (from Grok #2).

    Tracks when user does what:
    - time_of_day: {morning: "code review", afternoon: "implementation"}
    - seasonality: {month_start: "planning", month_end: "deployment"}
    - decay_rate: How fast old patterns lose confidence
    """
    time_of_day: Dict[str, str] = field(default_factory=dict)  # {morning: "code review"}
    seasonality: Dict[str, str] = field(default_factory=dict)  # {month_start: "planning"}
    decay_rate: float = 0.05  # Weekly decay rate
    active_hours: List[int] = field(default_factory=lambda: list(range(9, 22)))  # 9am-10pm
    last_updated: str = field(default_factory=lambda: datetime.now().isoformat())
    confidence: float = 0.5

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ToolUsagePatterns:
    """
    User's tool interaction patterns (from CAM research).

    Tracks how user interacts with VETKA tools:
    - frequent_tools: Most used tools
    - patterns: Sequence patterns (e.g., "viewport -> query_deps")
    - shortcuts: Preferred keyboard shortcuts
    """
    frequent_tools: List[str] = field(default_factory=list)
    patterns: Dict[str, str] = field(default_factory=dict)  # {viewport: "zoom -> query deps"}
    shortcuts: Dict[str, str] = field(default_factory=dict)  # {action: shortcut}
    last_updated: str = field(default_factory=lambda: datetime.now().isoformat())
    confidence: float = 0.5

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class UserPreferences:
    """
    Complete user preference schema (from Grok #2).

    Combines all category schemas into unified structure.
    This is the primary interface for JARVIS Memory.

    Usage:
        prefs = UserPreferences(user_id="danila")
        prefs.communication_style.formality = 0.2
        enriched = prefs.to_dict()
    """
    user_id: str
    viewport_patterns: ViewportPatterns = field(default_factory=ViewportPatterns)
    tree_structure: TreeStructure = field(default_factory=TreeStructure)
    project_highlights: ProjectHighlights = field(default_factory=ProjectHighlights)
    communication_style: CommunicationStyle = field(default_factory=CommunicationStyle)
    temporal_patterns: TemporalPatterns = field(default_factory=TemporalPatterns)
    tool_usage_patterns: ToolUsagePatterns = field(default_factory=ToolUsagePatterns)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize all preferences to dict for Engram/Qdrant storage."""
        return {
            'user_id': self.user_id,
            'viewport_patterns': self.viewport_patterns.to_dict(),
            'tree_structure': self.tree_structure.to_dict(),
            'project_highlights': self.project_highlights.to_dict(),
            'communication_style': self.communication_style.to_dict(),
            'temporal_patterns': self.temporal_patterns.to_dict(),
            'tool_usage_patterns': self.tool_usage_patterns.to_dict()
        }

    def to_json(self) -> str:
        """Serialize to JSON string."""
        return json.dumps(self.to_dict(), indent=2, ensure_ascii=False)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'UserPreferences':
        """Deserialize from Engram/Qdrant payload."""
        return cls(
            user_id=data.get('user_id', 'unknown'),
            viewport_patterns=ViewportPatterns(**data.get('viewport_patterns', {})) if data.get('viewport_patterns') else ViewportPatterns(),
            tree_structure=TreeStructure(**data.get('tree_structure', {})) if data.get('tree_structure') else TreeStructure(),
            project_highlights=ProjectHighlights(**data.get('project_highlights', {})) if data.get('project_highlights') else ProjectHighlights(),
            communication_style=CommunicationStyle(**data.get('communication_style', {})) if data.get('communication_style') else CommunicationStyle(),
            temporal_patterns=TemporalPatterns(**data.get('temporal_patterns', {})) if data.get('temporal_patterns') else TemporalPatterns(),
            tool_usage_patterns=ToolUsagePatterns(**data.get('tool_usage_patterns', {})) if data.get('tool_usage_patterns') else ToolUsagePatterns()
        )

    @classmethod
    def from_json(cls, json_str: str) -> 'UserPreferences':
        """Deserialize from JSON string."""
        return cls.from_dict(json.loads(json_str))

    def get_high_confidence_prefs(self, threshold: float = 0.7) -> Dict[str, Any]:
        """
        Get only preferences with confidence above threshold.

        Used for token-efficient prompt enrichment.
        """
        result = {'user_id': self.user_id}

        if self.viewport_patterns.confidence >= threshold:
            result['viewport_patterns'] = self.viewport_patterns.to_dict()

        if self.tree_structure.confidence >= threshold:
            result['tree_structure'] = self.tree_structure.to_dict()

        if self.project_highlights.confidence >= threshold:
            result['project_highlights'] = self.project_highlights.to_dict()

        if self.communication_style.confidence >= threshold:
            result['communication_style'] = self.communication_style.to_dict()

        if self.temporal_patterns.confidence >= threshold:
            result['temporal_patterns'] = self.temporal_patterns.to_dict()

        if self.tool_usage_patterns.confidence >= threshold:
            result['tool_usage_patterns'] = self.tool_usage_patterns.to_dict()

        return result

    def merge(self, other: 'UserPreferences') -> 'UserPreferences':
        """
        Merge another preferences object, keeping higher confidence values.

        Useful for combining preferences from different sources.
        """
        if other.viewport_patterns.confidence > self.viewport_patterns.confidence:
            self.viewport_patterns = other.viewport_patterns

        if other.tree_structure.confidence > self.tree_structure.confidence:
            self.tree_structure = other.tree_structure

        if other.project_highlights.confidence > self.project_highlights.confidence:
            self.project_highlights = other.project_highlights

        if other.communication_style.confidence > self.communication_style.confidence:
            self.communication_style = other.communication_style

        if other.temporal_patterns.confidence > self.temporal_patterns.confidence:
            self.temporal_patterns = other.temporal_patterns

        if other.tool_usage_patterns.confidence > self.tool_usage_patterns.confidence:
            self.tool_usage_patterns = other.tool_usage_patterns

        return self


# ============ FACTORY FUNCTION ============

def create_user_preferences(user_id: str, **kwargs) -> UserPreferences:
    """
    Factory function to create UserPreferences with optional overrides.

    Args:
        user_id: Unique user identifier
        **kwargs: Override default values

    Returns:
        UserPreferences instance
    """
    prefs = UserPreferences(user_id=user_id)

    # Apply overrides
    for key, value in kwargs.items():
        if hasattr(prefs, key):
            setattr(prefs, key, value)

    return prefs
