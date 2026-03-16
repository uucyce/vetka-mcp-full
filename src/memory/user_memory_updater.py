"""
VETKA Phase 76.3 - User Memory Updater
Implicit learning from user interactions

@file user_memory_updater.py
@status ACTIVE
@phase Phase 76.3 - JARVIS Memory Layer
@calledBy API handlers, websocket handlers
@lastAudit 2026-01-20

Strategy (from Grok #2 Research):
- 70% implicit: Auto-track actions passively
- 20% confirm: Ask after 5 consistent patterns
- 10% explicit: Direct user commands

Weighted moving average: alpha=0.2 for new data
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from collections import Counter

from .aura_store import AuraStore, get_aura_store
from .user_memory import UserPreferences

logger = logging.getLogger(__name__)


class UserMemoryUpdater:
    """
    Implicit Learning for JARVIS Memory (from Grok #2).

    Strategy:
    - 70% implicit: Track actions passively (viewport, tree, tools)
    - 20% confirm: Ask after 5 consistent patterns
    - 10% explicit: Direct user commands ("set formality 0.5")

    Uses weighted moving average (alpha=0.2) for smooth updates.

    Usage:
        updater = UserMemoryUpdater()
        await updater.update_viewport_pattern('danila', zoom=1.5, focus='src/')
        await updater.update_communication_style('danila', message="...")
    """

    # Weighted moving average alpha (how much new data influences result)
    ALPHA = 0.2

    # Rolling window size for pattern detection
    WINDOW_SIZE = 10

    # Confirmation threshold (ask user after N consistent patterns)
    CONFIRM_THRESHOLD = 5

    def __init__(self, aura_store: Optional[AuraStore] = None):
        """
        Initialize User Memory Updater.

        Args:
            aura_store: AuraStore instance (uses singleton if None)
        """
        self.memory = aura_store or get_aura_store()
        self.pending_confirmations: Dict[str, List[Dict]] = {}  # user_id → [patterns to confirm]

    async def update_viewport_pattern(
        self,
        user_id: str,
        zoom_level: Optional[float] = None,
        focus_area: Optional[str] = None,
        navigation_style: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Implicit update: Viewport zoom/focus (from Grok #2).

        Rolling window of last 10 actions.
        Weighted moving average alpha=0.2.

        Args:
            user_id: User identifier
            zoom_level: Current zoom level (e.g., 1.5)
            focus_area: Focused folder/file (e.g., "src/agents/")
            navigation_style: keyboard/mouse/voice

        Returns:
            Update status dict
        """
        result = {'updated': [], 'user_id': user_id}

        # Update zoom levels
        if zoom_level is not None:
            current_zooms = self.memory.get_preference(
                user_id, 'viewport_patterns', 'zoom_levels'
            ) or []

            current_zooms.append(zoom_level)

            # Keep rolling window
            if len(current_zooms) > self.WINDOW_SIZE:
                current_zooms = current_zooms[-self.WINDOW_SIZE:]

            # Compute confidence based on observation count
            confidence = min(1.0, 0.5 + len(current_zooms) * 0.05)

            self.memory.set_preference(
                user_id,
                'viewport_patterns',
                'zoom_levels',
                current_zooms,
                confidence=confidence
            )
            result['updated'].append('zoom_levels')

        # Update focus areas
        if focus_area:
            current_areas = self.memory.get_preference(
                user_id, 'viewport_patterns', 'focus_areas'
            ) or []

            # Add if not already in top areas
            if focus_area not in current_areas:
                current_areas.append(focus_area)
                # Keep top 5 most recent
                current_areas = current_areas[-5:]

                confidence = min(1.0, len(current_areas) * 0.15)

                self.memory.set_preference(
                    user_id,
                    'viewport_patterns',
                    'focus_areas',
                    current_areas,
                    confidence=confidence
                )
                result['updated'].append('focus_areas')

        # Update navigation style
        if navigation_style:
            self.memory.set_preference(
                user_id,
                'viewport_patterns',
                'navigation_style',
                navigation_style,
                confidence=0.7
            )
            result['updated'].append('navigation_style')

        logger.debug(f"[UserMemoryUpdater] Viewport update for {user_id}: {result['updated']}")
        return result

    async def update_tree_structure(
        self,
        user_id: str,
        grouping: Optional[str] = None,
        preferred_depth: Optional[int] = None,
        hidden_folder: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Implicit update: Tree grouping preference.

        Confirms after 5 consistent actions.

        Args:
            user_id: User identifier
            grouping: by-module/by-feature/by-time
            preferred_depth: Max depth before collapse
            hidden_folder: Folder to hide

        Returns:
            Update status dict
        """
        result = {'updated': [], 'needs_confirmation': False, 'user_id': user_id}

        # Track grouping pattern
        if grouping:
            pattern = self._track_pattern(user_id, 'tree_grouping', grouping)

            # Check if pattern is confirmed (5+ consistent)
            if pattern['confirmed']:
                self.memory.set_preference(
                    user_id,
                    'tree_structure',
                    'grouping',
                    pattern['dominant_value'],
                    confidence=0.9
                )
                result['updated'].append('grouping')
            elif pattern['needs_confirmation']:
                result['needs_confirmation'] = True
                result['pending_value'] = pattern['dominant_value']

        # Update depth
        if preferred_depth is not None:
            current_depth = self.memory.get_preference(
                user_id, 'tree_structure', 'preferred_depth'
            ) or 3

            # Weighted average
            new_depth = int(self.ALPHA * preferred_depth + (1 - self.ALPHA) * current_depth)

            self.memory.set_preference(
                user_id,
                'tree_structure',
                'preferred_depth',
                new_depth,
                confidence=0.7
            )
            result['updated'].append('preferred_depth')

        # Add hidden folder
        if hidden_folder:
            hidden_folders = self.memory.get_preference(
                user_id, 'tree_structure', 'hidden_folders'
            ) or []

            if hidden_folder not in hidden_folders:
                hidden_folders.append(hidden_folder)
                self.memory.set_preference(
                    user_id,
                    'tree_structure',
                    'hidden_folders',
                    hidden_folders,
                    confidence=0.8
                )
                result['updated'].append('hidden_folders')

        logger.debug(f"[UserMemoryUpdater] Tree structure update for {user_id}: {result}")
        return result

    async def update_communication_style(
        self,
        user_id: str,
        message: str
    ) -> Dict[str, Any]:
        """
        Implicit update: Communication style from user messages.

        Analyzes message length and formality via simple heuristics.
        Updates every interaction with weighted moving average.

        Args:
            user_id: User identifier
            message: User's message text

        Returns:
            Update status dict with detected style
        """
        result = {'user_id': user_id, 'detected': {}}

        if not message:
            return result

        # Simple heuristics (can be enhanced with NLP)
        word_count = len(message.split())

        # Detect formality (0=casual, 1=formal)
        formal_markers = [
            'please', 'could', 'would', 'kindly', 'might',
            'пожалуйста', 'было бы', 'не могли бы', 'будьте добры'
        ]
        casual_markers = [
            'hey', 'yo', 'lol', 'btw', 'gonna', 'wanna',
            'привет', 'чо', 'норм', 'кста', 'ваще'
        ]

        message_lower = message.lower()
        formal_count = sum(1 for m in formal_markers if m in message_lower)
        casual_count = sum(1 for m in casual_markers if m in message_lower)

        if formal_count > casual_count:
            detected_formality = min(1.0, 0.5 + formal_count * 0.15)
        elif casual_count > formal_count:
            detected_formality = max(0.0, 0.5 - casual_count * 0.15)
        else:
            detected_formality = 0.5

        result['detected']['formality'] = detected_formality

        # Detect detail level (0=concise, 1=verbose)
        # Normalize to ~50 words
        detail_level = min(1.0, word_count / 50)
        result['detected']['detail_level'] = detail_level

        # Detect language preference
        russian_chars = sum(1 for c in message if '\u0400' <= c <= '\u04FF')
        prefers_russian = russian_chars > len(message) * 0.3
        result['detected']['prefers_russian'] = prefers_russian

        # Get current values
        current_formality = self.memory.get_preference(
            user_id, 'communication_style', 'formality'
        ) or 0.5

        current_detail = self.memory.get_preference(
            user_id, 'communication_style', 'detail_level'
        ) or 0.5

        # Apply weighted moving average
        new_formality = self.ALPHA * detected_formality + (1 - self.ALPHA) * current_formality
        new_detail = self.ALPHA * detail_level + (1 - self.ALPHA) * current_detail

        # Update preferences
        self.memory.set_preference(
            user_id, 'communication_style', 'formality', round(new_formality, 2)
        )
        self.memory.set_preference(
            user_id, 'communication_style', 'detail_level', round(new_detail, 2)
        )
        self.memory.set_preference(
            user_id, 'communication_style', 'prefers_russian', prefers_russian
        )

        result['updated'] = ['formality', 'detail_level', 'prefers_russian']

        logger.debug(f"[UserMemoryUpdater] Communication style for {user_id}: formality={new_formality:.2f}, detail={new_detail:.2f}")
        return result

    async def update_temporal_pattern(
        self,
        user_id: str,
        action: str
    ) -> Dict[str, Any]:
        """
        Implicit update: Time of day patterns (from Grok #2).

        Tracks most common action per time period.

        Args:
            user_id: User identifier
            action: Action type (e.g., "code review", "implementation")

        Returns:
            Update status dict
        """
        result = {'user_id': user_id, 'updated': False}

        hour = datetime.now().hour

        # Determine time period
        if 5 <= hour < 12:
            period = "morning"
        elif 12 <= hour < 18:
            period = "afternoon"
        else:
            period = "evening"

        # Get current patterns
        time_patterns = self.memory.get_preference(
            user_id, 'temporal_patterns', 'time_of_day'
        ) or {}

        # Initialize period tracking
        if period not in time_patterns:
            time_patterns[period] = []

        # Track action (store as list for counting)
        if isinstance(time_patterns[period], list):
            time_patterns[period].append(action)
            # Keep last 10 actions
            time_patterns[period] = time_patterns[period][-self.WINDOW_SIZE:]
        else:
            # Convert old format
            time_patterns[period] = [action]

        # Find dominant action
        if time_patterns[period]:
            counter = Counter(time_patterns[period])
            most_common = counter.most_common(1)[0]
            dominant_action = most_common[0]
            confidence = most_common[1] / len(time_patterns[period])

            # Update if confidence > 0.5
            if confidence > 0.5:
                # Convert back to simple dict for storage
                simplified_patterns = {
                    p: Counter(actions).most_common(1)[0][0] if isinstance(actions, list) and actions else actions
                    for p, actions in time_patterns.items()
                }

                self.memory.set_preference(
                    user_id,
                    'temporal_patterns',
                    'time_of_day',
                    simplified_patterns,
                    confidence=confidence
                )
                result['updated'] = True
                result['period'] = period
                result['dominant_action'] = dominant_action
                result['confidence'] = confidence

        logger.debug(f"[UserMemoryUpdater] Temporal pattern for {user_id}: {result}")
        return result

    async def update_tool_usage(
        self,
        user_id: str,
        tool_name: str,
        previous_tool: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Implicit update: Tool usage patterns.

        Tracks frequent tools and tool sequences.

        Args:
            user_id: User identifier
            tool_name: Current tool being used
            previous_tool: Previous tool (for sequence tracking)

        Returns:
            Update status dict
        """
        result = {'user_id': user_id, 'updated': []}

        # Update frequent tools
        frequent_tools = self.memory.get_preference(
            user_id, 'tool_usage_patterns', 'frequent_tools'
        ) or []

        if tool_name not in frequent_tools:
            frequent_tools.append(tool_name)
            # Keep top 10
            frequent_tools = frequent_tools[-10:]

        self.memory.set_preference(
            user_id,
            'tool_usage_patterns',
            'frequent_tools',
            frequent_tools,
            confidence=min(1.0, len(frequent_tools) * 0.1)
        )
        result['updated'].append('frequent_tools')

        # Track tool sequence pattern
        if previous_tool:
            patterns = self.memory.get_preference(
                user_id, 'tool_usage_patterns', 'patterns'
            ) or {}

            sequence = f"{previous_tool} -> {tool_name}"
            patterns[previous_tool] = sequence

            self.memory.set_preference(
                user_id,
                'tool_usage_patterns',
                'patterns',
                patterns,
                confidence=0.6
            )
            result['updated'].append('patterns')
            result['sequence'] = sequence

        logger.debug(f"[UserMemoryUpdater] Tool usage for {user_id}: {result}")
        return result

    async def explicit_set(
        self,
        user_id: str,
        category: str,
        key: str,
        value: Any
    ) -> Dict[str, Any]:
        """
        Explicit update: Direct user command.

        Handles commands like "set formality 0.5".

        Args:
            user_id: User identifier
            category: Preference category
            key: Preference key
            value: Value to set

        Returns:
            Update status dict
        """
        self.memory.set_preference(
            user_id, category, key, value, confidence=1.0  # Explicit = full confidence
        )

        logger.info(f"[UserMemoryUpdater] Explicit set for {user_id}: {category}.{key} = {value}")

        return {
            'user_id': user_id,
            'category': category,
            'key': key,
            'value': value,
            'confidence': 1.0,
            'explicit': True
        }

    def _track_pattern(
        self,
        user_id: str,
        pattern_type: str,
        value: Any
    ) -> Dict[str, Any]:
        """
        Track pattern for confirmation (20% confirm strategy).

        Returns pattern status.
        """
        if user_id not in self.pending_confirmations:
            self.pending_confirmations[user_id] = []

        # Add pattern observation
        self.pending_confirmations[user_id].append({
            'type': pattern_type,
            'value': value,
            'timestamp': datetime.now().isoformat()
        })

        # Keep only recent observations
        self.pending_confirmations[user_id] = self.pending_confirmations[user_id][-20:]

        # Count patterns of this type
        recent = [
            p for p in self.pending_confirmations[user_id][-self.WINDOW_SIZE:]
            if p['type'] == pattern_type
        ]

        if not recent:
            return {'confirmed': False, 'needs_confirmation': False}

        # Find dominant value
        value_counts = Counter([p['value'] for p in recent])
        most_common = value_counts.most_common(1)[0]
        dominant_value = most_common[0]
        count = most_common[1]

        # Check if confirmed
        if count >= self.CONFIRM_THRESHOLD:
            # Clear pending for this type
            self.pending_confirmations[user_id] = [
                p for p in self.pending_confirmations[user_id]
                if p['type'] != pattern_type
            ]
            return {
                'confirmed': True,
                'needs_confirmation': False,
                'dominant_value': dominant_value,
                'count': count
            }

        # Check if needs confirmation (close to threshold)
        if count >= self.CONFIRM_THRESHOLD - 2:
            return {
                'confirmed': False,
                'needs_confirmation': True,
                'dominant_value': dominant_value,
                'count': count
            }

        return {'confirmed': False, 'needs_confirmation': False, 'count': count}

    def get_pending_confirmations(self, user_id: str) -> List[Dict]:
        """Get pending confirmations for a user."""
        return self.pending_confirmations.get(user_id, [])

    def confirm_pattern(self, user_id: str, pattern_type: str) -> Dict[str, Any]:
        """
        User confirmed a pending pattern.

        Args:
            user_id: User identifier
            pattern_type: Type of pattern being confirmed

        Returns:
            Confirmation result
        """
        patterns = [
            p for p in self.pending_confirmations.get(user_id, [])
            if p['type'] == pattern_type
        ]

        if not patterns:
            return {'success': False, 'reason': 'no_pending_pattern'}

        # Get dominant value
        value_counts = Counter([p['value'] for p in patterns])
        dominant_value = value_counts.most_common(1)[0][0]

        # Apply based on pattern type
        category_map = {
            'tree_grouping': ('tree_structure', 'grouping'),
            'navigation_style': ('viewport_patterns', 'navigation_style'),
            # Add more mappings as needed
        }

        if pattern_type in category_map:
            category, key = category_map[pattern_type]
            self.memory.set_preference(
                user_id, category, key, dominant_value, confidence=0.95
            )

            # Clear pending
            self.pending_confirmations[user_id] = [
                p for p in self.pending_confirmations.get(user_id, [])
                if p['type'] != pattern_type
            ]

            return {
                'success': True,
                'category': category,
                'key': key,
                'value': dominant_value
            }

        return {'success': False, 'reason': 'unknown_pattern_type'}


# ============ FACTORY FUNCTION ============

_updater_instance: Optional[UserMemoryUpdater] = None


def get_user_memory_updater(
    aura_store: Optional[AuraStore] = None
) -> UserMemoryUpdater:
    """
    Factory function - returns singleton UserMemoryUpdater.

    Args:
        aura_store: AuraStore instance

    Returns:
        UserMemoryUpdater singleton instance
    """
    global _updater_instance

    if _updater_instance is None:
        _updater_instance = UserMemoryUpdater(aura_store)

    return _updater_instance
