"""
Key Learning System for VETKA
Phase 57.9: Auto-learn API keys via Hostess

Automatically learns new API key patterns from user input.
When a user pastes an unknown key, the system:
1. Analyzes the key pattern
2. Asks user for provider name
3. Learns the pattern for future detection
4. Saves the key to config

@file key_learner.py
@status ACTIVE
@phase Phase 57.9
@lastUpdate 2026-01-10
"""

import json
import re
import os
from pathlib import Path
from typing import Optional, Dict, Tuple, List
from dataclasses import dataclass, asdict
from datetime import datetime

# Project root
PROJECT_ROOT = Path(__file__).parent.parent.parent

# Config paths
LEARNED_PATTERNS_FILE = PROJECT_ROOT / "data" / "learned_key_patterns.json"
CONFIG_FILE = PROJECT_ROOT / "data" / "config.json"


@dataclass
class KeyPattern:
    """Represents a learned key pattern"""
    provider: str
    prefix: Optional[str]
    suffix: Optional[str]
    length_min: int
    length_max: int
    charset: str  # 'alphanumeric', 'hex', 'base64', 'mixed'
    separator: Optional[str]  # '-', '_', '.', etc.
    confidence: float = 0.85
    learned_at: str = ""
    example_masked: str = ""  # Masked example for reference


class KeyLearner:
    """
    Learns new API key patterns and adds them to the detector.
    Works with Hostess agent for user interaction.

    Usage:
        learner = get_key_learner()

        # When user pastes unknown key
        analysis = learner.analyze_key("tvly-dev-abc123...")
        # Returns: {'prefix': 'tvly-dev-', 'length': 45, 'charset': 'alphanumeric', ...}

        # After user confirms provider
        success, msg = learner.learn_key_type("tvly-dev-abc123...", "tavily")
        # Now Tavily keys will be recognized
    """

    def __init__(self):
        self.learned_patterns: Dict[str, KeyPattern] = {}
        self._load_patterns()

    def _load_patterns(self):
        """Load previously learned patterns from disk"""
        if LEARNED_PATTERNS_FILE.exists():
            try:
                with open(LEARNED_PATTERNS_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for provider, pattern_dict in data.items():
                        self.learned_patterns[provider] = KeyPattern(**pattern_dict)
                print(f"[KeyLearner] Loaded {len(self.learned_patterns)} learned patterns")
            except Exception as e:
                print(f"[KeyLearner] Failed to load patterns: {e}")

    def _save_patterns(self):
        """Save learned patterns to disk"""
        try:
            # Ensure data directory exists
            LEARNED_PATTERNS_FILE.parent.mkdir(parents=True, exist_ok=True)

            data = {}
            for provider, pattern in self.learned_patterns.items():
                data[provider] = asdict(pattern)

            with open(LEARNED_PATTERNS_FILE, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            print(f"[KeyLearner] Saved {len(data)} patterns to {LEARNED_PATTERNS_FILE}")
            return True
        except Exception as e:
            print(f"[KeyLearner] Failed to save patterns: {e}")
            return False

    def analyze_key(self, key: str) -> Dict:
        """
        Analyze a key to extract its pattern characteristics.

        Args:
            key: The API key to analyze

        Returns:
            dict with pattern info:
            {
                'length': 45,
                'prefix': 'tvly-dev-',
                'suffix': None,
                'separator': '-',
                'charset': 'alphanumeric',
                'parts': ['tvly', 'dev', 'abc123...'],
                'masked': 'tvly-dev-...6M9F'
            }
        """
        key = key.strip()

        analysis = {
            'length': len(key),
            'prefix': None,
            'suffix': None,
            'separator': None,
            'charset': 'unknown',
            'parts': [],
            'masked': self._mask_key(key)
        }

        # Detect separators
        for sep in ['-', '_', '.', ':']:
            if sep in key:
                parts = key.split(sep)
                if len(parts) >= 2:
                    analysis['separator'] = sep
                    analysis['parts'] = parts

                    # Extract prefix (first 1-2 parts if they look like a prefix)
                    prefix_parts = []
                    for p in parts[:3]:  # Check first 3 parts
                        if len(p) <= 8 and p.replace('-', '').replace('_', '').isalnum():
                            prefix_parts.append(p)
                        else:
                            break

                    if prefix_parts:
                        analysis['prefix'] = sep.join(prefix_parts) + sep
                    break

        # If no separator found, check for common prefix patterns
        if not analysis['prefix']:
            common_prefixes = ['sk-', 'pk-', 'api-', 'key-', 'token-', 'secret-']
            for prefix in common_prefixes:
                if key.lower().startswith(prefix):
                    analysis['prefix'] = key[:len(prefix)]
                    break

        # Detect charset
        key_clean = key.replace('-', '').replace('_', '').replace('.', '').replace(':', '')

        if re.match(r'^[a-fA-F0-9]+$', key_clean):
            analysis['charset'] = 'hex'
        elif re.match(r'^[a-zA-Z0-9+/=]+$', key_clean):
            analysis['charset'] = 'base64'
        elif re.match(r'^[a-zA-Z0-9]+$', key_clean):
            analysis['charset'] = 'alphanumeric'
        elif re.match(r'^[a-zA-Z0-9_-]+$', key_clean):
            analysis['charset'] = 'alphanumeric_extended'
        else:
            analysis['charset'] = 'mixed'

        return analysis

    def _mask_key(self, key: str) -> str:
        """Create a masked version of the key for display"""
        if len(key) < 12:
            return "***"
        return f"{key[:8]}...{key[-4:]}"

    def learn_key_type(
        self,
        key: str,
        provider_name: str,
        save_key: bool = True
    ) -> Tuple[bool, str]:
        """
        Learn a new key type from user input.

        Args:
            key: The API key
            provider_name: Name of the provider (from user)
            save_key: Whether to also save the key to config

        Returns:
            (success, message)
        """
        key = key.strip()

        if not key or len(key) < 10:
            return False, "Key is too short (minimum 10 characters)"

        if not provider_name:
            return False, "Provider name is required"

        # Normalize provider name
        provider = provider_name.lower().strip().replace(' ', '_').replace('-', '_')

        # Analyze key pattern
        analysis = self.analyze_key(key)

        # Create pattern
        pattern = KeyPattern(
            provider=provider,
            prefix=analysis['prefix'],
            suffix=None,
            length_min=len(key) - 10,  # Allow some variance
            length_max=len(key) + 10,
            charset=analysis['charset'],
            separator=analysis['separator'],
            confidence=0.85,  # User-provided, slightly lower confidence
            learned_at=datetime.now().isoformat(),
            example_masked=analysis['masked']
        )

        # Save pattern
        self.learned_patterns[provider] = pattern
        self._save_patterns()

        # Update the main detector dynamically
        self._register_learned_pattern(provider, pattern)

        # Save key to config if requested
        if save_key:
            self._save_key_to_config(provider, key)

        # Phase 57.9: Auto-register in KeyManager for immediate availability
        self._auto_register_in_key_manager(provider, key, pattern)

        message = f"Learned pattern for {provider}: prefix='{pattern.prefix or 'none'}', length={len(key)}"
        print(f"[KeyLearner] {message}")

        return True, message

    def _auto_register_in_key_manager(self, provider: str, key: str, pattern: KeyPattern):
        """
        Phase 57.9: Auto-register learned provider in UnifiedKeyManager.
        Phase 57.12: Updated to use UnifiedKeyManager.

        This ensures that newly learned providers are immediately available
        in the KeyManager system for key rotation, validation, etc.

        Args:
            provider: Provider name (lowercase)
            key: The API key
            pattern: The learned pattern
        """
        try:
            # Phase 57.12: Use UnifiedKeyManager
            from src.utils.unified_key_manager import get_key_manager, ProviderType, APIKeyRecord

            km = get_key_manager()
            provider_upper = provider.upper()

            # Check if this provider is in ProviderType enum
            if hasattr(ProviderType, provider_upper):
                provider_key = ProviderType[provider_upper]
            else:
                # Dynamic provider - use string key
                provider_key = provider.lower()

            # Ensure provider is initialized
            km._ensure_provider_initialized(provider_key)

            # Check if key already exists
            existing_keys = [r.key for r in km.keys.get(provider_key, [])]
            if key not in existing_keys:
                record = APIKeyRecord(
                    provider=provider_key,
                    key=key,
                    alias=f'{provider}_learned'
                )
                km.keys[provider_key].append(record)
                print(f"[KeyLearner] Added key to UnifiedKeyManager for {provider}")
            else:
                print(f"[KeyLearner] Key already exists in UnifiedKeyManager for {provider}")

        except Exception as e:
            print(f"[KeyLearner] Could not auto-register in KeyManager: {e}")
            # Not critical - key is saved to config.json anyway

    def _register_learned_pattern(self, provider: str, pattern: KeyPattern):
        """
        Register learned pattern with the API key detector dynamically.
        This allows immediate recognition without restart.
        """
        try:
            from src.elisya.api_key_detector import APIKeyDetector, ProviderConfig, ProviderCategory

            # Build regex pattern
            if pattern.prefix:
                prefix_escaped = re.escape(pattern.prefix)
                regex = f"^{prefix_escaped}[a-zA-Z0-9\\-_]{{10,100}}$"
            else:
                # Generic pattern based on charset and length
                if pattern.charset == 'hex':
                    char_class = '[a-fA-F0-9]'
                elif pattern.charset == 'base64':
                    char_class = '[a-zA-Z0-9+/=]'
                else:
                    char_class = '[a-zA-Z0-9\\-_]'

                regex = f"^{char_class}{{{pattern.length_min},{pattern.length_max}}}$"

            # Create provider config
            config = ProviderConfig(
                prefix=pattern.prefix or "",
                regex=regex,
                base_url=f"https://api.{provider}.com/v1",  # Placeholder
                category=ProviderCategory.LLM,  # Default category
                display_name=provider.replace('_', ' ').title()
            )

            # Add to detector patterns
            APIKeyDetector.PATTERNS[provider] = config

            # Add to detection order (high priority for prefix, low for generic)
            if pattern.prefix and provider not in APIKeyDetector.DETECTION_ORDER:
                # Insert after unique prefixes (around position 20)
                APIKeyDetector.DETECTION_ORDER.insert(20, provider)
            elif provider not in APIKeyDetector.DETECTION_ORDER:
                APIKeyDetector.DETECTION_ORDER.append(provider)

            print(f"[KeyLearner] Registered {provider} pattern with detector")

        except Exception as e:
            print(f"[KeyLearner] Failed to register pattern with detector: {e}")

    def _save_key_to_config(self, provider: str, key: str) -> bool:
        """Save the key to data/config.json"""
        try:
            config = {}
            if CONFIG_FILE.exists():
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    config = json.load(f)

            # Ensure api_keys section exists
            if 'api_keys' not in config:
                config['api_keys'] = {}

            # Handle different storage formats
            existing = config['api_keys'].get(provider)

            if existing is None:
                # New provider - store as single key or list
                config['api_keys'][provider] = key
            elif isinstance(existing, list):
                # Already a list - append if not duplicate
                if key not in existing:
                    existing.append(key)
            elif isinstance(existing, str):
                # Convert to list if adding second key
                if existing != key:
                    config['api_keys'][provider] = [existing, key]
            elif isinstance(existing, dict):
                # Handle OpenRouter-style structure
                if 'free' in existing:
                    if isinstance(existing['free'], list):
                        if key not in existing['free']:
                            existing['free'].append(key)
                    else:
                        existing['free'] = [existing.get('free'), key] if existing.get('free') else [key]
                else:
                    existing['free'] = [key]

            # Update timestamp
            config['updated_at'] = datetime.now().isoformat()

            # Write back
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)

            print(f"[KeyLearner] Saved {provider} key to config")
            return True

        except Exception as e:
            print(f"[KeyLearner] Failed to save key: {e}")
            return False

    def get_learned_providers(self) -> List[str]:
        """Get list of learned providers"""
        return list(self.learned_patterns.keys())

    def get_pattern_info(self, provider: str) -> Optional[Dict]:
        """Get info about a learned pattern"""
        pattern = self.learned_patterns.get(provider)
        if pattern:
            return asdict(pattern)
        return None

    def check_learned_pattern(self, key: str) -> Optional[Dict]:
        """
        Check if key matches any learned pattern.

        Returns:
            dict with provider info if matched, None otherwise
        """
        key = key.strip()

        for provider, pattern in self.learned_patterns.items():
            # Check prefix first
            if pattern.prefix:
                if not key.startswith(pattern.prefix):
                    continue

            # Check length
            if not (pattern.length_min <= len(key) <= pattern.length_max):
                continue

            # Basic charset check
            key_clean = key.replace('-', '').replace('_', '').replace('.', '')

            if pattern.charset == 'hex' and not re.match(r'^[a-fA-F0-9]+$', key_clean):
                continue
            elif pattern.charset == 'alphanumeric' and not re.match(r'^[a-zA-Z0-9]+$', key_clean):
                continue

            # Match found
            return {
                'provider': provider,
                'display_name': provider.replace('_', ' ').title(),
                'confidence': pattern.confidence,
                'learned': True,
                'learned_at': pattern.learned_at
            }

        return None


# Singleton instance
_key_learner: Optional[KeyLearner] = None


def get_key_learner() -> KeyLearner:
    """Get or create the KeyLearner singleton"""
    global _key_learner
    if _key_learner is None:
        _key_learner = KeyLearner()
    return _key_learner


def reset_key_learner():
    """Reset the singleton (for testing)"""
    global _key_learner
    _key_learner = None


# ============================================================================
# EXPORTS
# ============================================================================

__all__ = [
    'KeyLearner',
    'KeyPattern',
    'get_key_learner',
    'reset_key_learner'
]
