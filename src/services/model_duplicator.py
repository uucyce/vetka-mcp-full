# === PHASE 112: MULTI-SOURCE MODEL DUPLICATOR ===
"""
MARKER_112_DUPLICATOR: Generate duplicate entries for multi-source models.

Phase 112: Extended from DUAL_SOURCE to MULTI_SOURCE.
Shows same model via different providers IF keys exist.
Supports: Direct API, OpenRouter, Polza, NanoGPT, Poe.

@status: active
@phase: 112
@depends: unified_key_manager
@used_by: model_routes.py
"""

import logging
from typing import List, Dict, Any, Optional
from src.utils.unified_key_manager import get_key_manager, ProviderType

logger = logging.getLogger(__name__)


# Phase 112: Source configuration for all supported routes
class SourceConfig:
    """Configuration for a model source/route."""
    def __init__(self, source_type: str, requires_key: ProviderType,
                 display_suffix: str, id_transform: Optional[str] = None):
        self.source_type = source_type  # 'direct', 'openrouter', 'polza', etc.
        self.requires_key = requires_key
        self.display_suffix = display_suffix
        self.id_transform = id_transform  # e.g., "x-ai/{id}" for OpenRouter format


# MARKER_112_MULTI_SOURCE: Models available from multiple providers
# Phase 112: Extended from DUAL_SOURCE to support N sources per model
# Format: model_base_id -> list of sources (each source generates a separate entry)
MULTI_SOURCE_MODELS = {
    # === XAI / GROK (2026 models) ===
    "grok-4": {
        "sources": [
            {"type": "direct", "provider": "xai", "requires_key": ProviderType.XAI, "display": "xAI"},
            {"type": "openrouter", "id_format": "x-ai/grok-4", "requires_key": ProviderType.OPENROUTER, "display": "OR"},
        ]
    },
    "grok-4-fast": {
        "sources": [
            {"type": "direct", "provider": "xai", "requires_key": ProviderType.XAI, "display": "xAI"},
            {"type": "openrouter", "id_format": "x-ai/grok-4-fast", "requires_key": ProviderType.OPENROUTER, "display": "OR"},
        ]
    },
    "grok-4.1-fast": {
        "sources": [
            {"type": "direct", "provider": "xai", "requires_key": ProviderType.XAI, "display": "xAI"},
            {"type": "openrouter", "id_format": "x-ai/grok-4.1-fast", "requires_key": ProviderType.OPENROUTER, "display": "OR"},
        ]
    },
    "grok-3": {
        "sources": [
            {"type": "direct", "provider": "xai", "requires_key": ProviderType.XAI, "display": "xAI"},
            {"type": "openrouter", "id_format": "x-ai/grok-3", "requires_key": ProviderType.OPENROUTER, "display": "OR"},
        ]
    },
    "grok-3-mini": {
        "sources": [
            {"type": "direct", "provider": "xai", "requires_key": ProviderType.XAI, "display": "xAI"},
            {"type": "openrouter", "id_format": "x-ai/grok-3-mini", "requires_key": ProviderType.OPENROUTER, "display": "OR"},
        ]
    },
    "grok-3-beta": {
        "sources": [
            {"type": "direct", "provider": "xai", "requires_key": ProviderType.XAI, "display": "xAI"},
            {"type": "openrouter", "id_format": "x-ai/grok-3-beta", "requires_key": ProviderType.OPENROUTER, "display": "OR"},
        ]
    },
    "grok-3-mini-beta": {
        "sources": [
            {"type": "direct", "provider": "xai", "requires_key": ProviderType.XAI, "display": "xAI"},
            {"type": "openrouter", "id_format": "x-ai/grok-3-mini-beta", "requires_key": ProviderType.OPENROUTER, "display": "OR"},
        ]
    },
    "grok-code-fast-1": {
        "sources": [
            {"type": "direct", "provider": "xai", "requires_key": ProviderType.XAI, "display": "xAI"},
            {"type": "openrouter", "id_format": "x-ai/grok-code-fast-1", "requires_key": ProviderType.OPENROUTER, "display": "OR"},
        ]
    },
    "grok-2-latest": {
        "sources": [
            {"type": "direct", "provider": "xai", "requires_key": ProviderType.XAI, "display": "xAI"},
            {"type": "openrouter", "id_format": "x-ai/grok-2-latest", "requires_key": ProviderType.OPENROUTER, "display": "OR"},
        ]
    },
    "grok-2-1212": {
        "sources": [
            {"type": "direct", "provider": "xai", "requires_key": ProviderType.XAI, "display": "xAI"},
            {"type": "openrouter", "id_format": "x-ai/grok-2-1212", "requires_key": ProviderType.OPENROUTER, "display": "OR"},
        ]
    },
    "grok-2-vision-1212": {
        "sources": [
            {"type": "direct", "provider": "xai", "requires_key": ProviderType.XAI, "display": "xAI"},
            {"type": "openrouter", "id_format": "x-ai/grok-2-vision-1212", "requires_key": ProviderType.OPENROUTER, "display": "OR"},
        ]
    },
    "grok-vision-beta": {
        "sources": [
            {"type": "direct", "provider": "xai", "requires_key": ProviderType.XAI, "display": "xAI"},
            {"type": "openrouter", "id_format": "x-ai/grok-vision-beta", "requires_key": ProviderType.OPENROUTER, "display": "OR"},
        ]
    },

    # === OPENAI / GPT - Multi-source with Polza ===
    "gpt-4o": {
        "sources": [
            {"type": "direct", "provider": "openai", "requires_key": ProviderType.OPENAI, "display": "Direct"},
            {"type": "openrouter", "id_format": "openai/gpt-4o", "requires_key": ProviderType.OPENROUTER, "display": "OR"},
            {"type": "polza", "id_format": "openai/gpt-4o", "requires_key": ProviderType.POLZA, "display": "Polza"},
        ]
    },
    "gpt-4o-mini": {
        "sources": [
            {"type": "direct", "provider": "openai", "requires_key": ProviderType.OPENAI, "display": "Direct"},
            {"type": "openrouter", "id_format": "openai/gpt-4o-mini", "requires_key": ProviderType.OPENROUTER, "display": "OR"},
            {"type": "polza", "id_format": "openai/gpt-4o-mini", "requires_key": ProviderType.POLZA, "display": "Polza"},
        ]
    },
    "gpt-4-turbo": {
        "sources": [
            {"type": "direct", "provider": "openai", "requires_key": ProviderType.OPENAI, "display": "Direct"},
            {"type": "openrouter", "id_format": "openai/gpt-4-turbo", "requires_key": ProviderType.OPENROUTER, "display": "OR"},
            {"type": "polza", "id_format": "openai/gpt-4-turbo", "requires_key": ProviderType.POLZA, "display": "Polza"},
        ]
    },

    # === ANTHROPIC / CLAUDE - Multi-source with Polza ===
    "claude-3-5-sonnet-latest": {
        "sources": [
            {"type": "direct", "provider": "anthropic", "requires_key": ProviderType.ANTHROPIC, "display": "Direct"},
            {"type": "openrouter", "id_format": "anthropic/claude-3.5-sonnet", "requires_key": ProviderType.OPENROUTER, "display": "OR"},
            {"type": "polza", "id_format": "anthropic/claude-3.5-sonnet", "requires_key": ProviderType.POLZA, "display": "Polza"},
        ]
    },
    "claude-3-5-haiku-latest": {
        "sources": [
            {"type": "direct", "provider": "anthropic", "requires_key": ProviderType.ANTHROPIC, "display": "Direct"},
            {"type": "openrouter", "id_format": "anthropic/claude-3.5-haiku", "requires_key": ProviderType.OPENROUTER, "display": "OR"},
            {"type": "polza", "id_format": "anthropic/claude-3.5-haiku", "requires_key": ProviderType.POLZA, "display": "Polza"},
        ]
    },
    "claude-3-opus-latest": {
        "sources": [
            {"type": "direct", "provider": "anthropic", "requires_key": ProviderType.ANTHROPIC, "display": "Direct"},
            {"type": "openrouter", "id_format": "anthropic/claude-3-opus", "requires_key": ProviderType.OPENROUTER, "display": "OR"},
            {"type": "polza", "id_format": "anthropic/claude-3-opus", "requires_key": ProviderType.POLZA, "display": "Polza"},
        ]
    },

    # === GOOGLE / GEMINI ===
    "gemini-2.0-flash-exp": {
        "sources": [
            {"type": "direct", "provider": "google", "requires_key": ProviderType.GEMINI, "display": "Direct"},
            {"type": "openrouter", "id_format": "google/gemini-2.0-flash-exp:free", "requires_key": ProviderType.OPENROUTER, "display": "OR"},
        ]
    },
    "gemini-exp-1206": {
        "sources": [
            {"type": "direct", "provider": "google", "requires_key": ProviderType.GEMINI, "display": "Direct"},
            {"type": "openrouter", "id_format": "google/gemini-exp-1206:free", "requires_key": ProviderType.OPENROUTER, "display": "OR"},
        ]
    },
    "gemini-pro": {
        "sources": [
            {"type": "direct", "provider": "google", "requires_key": ProviderType.GEMINI, "display": "Direct"},
            {"type": "openrouter", "id_format": "google/gemini-pro", "requires_key": ProviderType.OPENROUTER, "display": "OR"},
        ]
    },

    # === MISTRAL - Multi-source ===
    "mistral-large-latest": {
        "sources": [
            {"type": "direct", "provider": "mistral", "requires_key": ProviderType.MISTRAL, "display": "Direct"},
            {"type": "openrouter", "id_format": "mistralai/mistral-large", "requires_key": ProviderType.OPENROUTER, "display": "OR"},
            {"type": "polza", "id_format": "mistralai/mistral-large", "requires_key": ProviderType.POLZA, "display": "Polza"},
        ]
    },
}

# Backwards compatibility alias
DUAL_SOURCE_MODELS = MULTI_SOURCE_MODELS


def has_active_key(provider_type: ProviderType) -> bool:
    """
    Check if provider has an active (non-rate-limited) API key.

    MARKER_112_KEY_CHECK: Determines if source version should be shown.
    """
    km = get_key_manager()
    key = km.get_active_key(provider_type)
    return key is not None


def create_duplicates(base_models: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    MARKER_112_CREATE_DUPLICATES: Multi-source duplication logic.

    Phase 112: Extended to support N sources per model (not just 2).

    Takes base model list, returns expanded list with duplicates.

    Logic:
    1. Check which API keys are active
    2. For each model in MULTI_SOURCE_MODELS:
       - For each source with active key → add that version
    3. Mark duplicates with source: "direct" | "openrouter" | "polza" | etc.
    4. Add 'routes' array to model showing all available sources

    Args:
        base_models: List of model dicts from registry

    Returns:
        Expanded list with duplicate entries for multi-source models
    """
    result = []
    processed_ids = set()

    for model in base_models:
        model_id = model.get('id', '')
        base_name = model.get('name', model_id)

        # Check if this model has multi-sources
        # Try to match by ID or by stripping provider prefix
        clean_id = model_id.split('/')[-1] if '/' in model_id else model_id

        if clean_id in MULTI_SOURCE_MODELS:
            config = MULTI_SOURCE_MODELS[clean_id]

            # Skip if already processed (avoid duplicating duplicates)
            if clean_id in processed_ids:
                continue
            processed_ids.add(clean_id)

            sources = config.get('sources', [])

            # Calculate all available routes for this model
            available_routes = []
            for src in sources:
                if has_active_key(src['requires_key']):
                    available_routes.append({
                        'type': src['type'],
                        'display': src['display'],
                        'id': src.get('id_format', clean_id)
                    })

            # Create entry for each source with active key
            for src in sources:
                if not has_active_key(src['requires_key']):
                    continue

                source_model = {**model}
                source_type = src['type']

                # Set model ID based on source type
                if source_type == 'direct':
                    source_model['id'] = clean_id
                    source_model['provider'] = src.get('provider', 'unknown')
                else:
                    # For aggregators (openrouter, polza, etc.)
                    source_model['id'] = src.get('id_format', clean_id)
                    source_model['provider'] = source_type

                source_model['source'] = source_type
                source_model['source_display'] = src['display']
                source_model['name'] = f"{base_name} ({src['display']})"
                source_model['routes'] = available_routes  # Phase 112: All available routes
                # Phase 112.5: Set compound key for React deduplication
                source_model['_compound_key'] = f"{source_model['id']}@{source_type}"

                result.append(source_model)
                logger.debug(f"[ModelDuplicator] Added {source_type}: {source_model['id']} ({src['display']})")

        else:
            # Not a multi-source model, keep as-is
            # Add default source field
            model_copy = {**model}
            if 'source' not in model_copy:
                # Determine source from ID or provider
                # Phase 112.4b: Removed dead code checking 'polza_direct' (doesn't exist)
                if '/' in model_id:
                    model_copy['source'] = 'openrouter'
                    model_copy['source_display'] = 'OR'
                elif model.get('provider') == 'ollama':
                    model_copy['source'] = 'local'
                    model_copy['source_display'] = 'Local'
                else:
                    model_copy['source'] = 'direct'
                    model_copy['source_display'] = model.get('provider', '').upper()[:3]

            # Single route for non-multi-source models
            model_copy['routes'] = [{
                'type': model_copy.get('source', 'unknown'),
                'display': model_copy.get('source_display', '?'),
                'id': model_id
            }]
            # Phase 112.5: Set compound key for React deduplication
            model_copy['_compound_key'] = f"{model_id}@{model_copy.get('source', 'unknown')}"

            result.append(model_copy)

    # Phase 112.5: Add ALL Polza models as separate entries
    # Even if same model exists from OpenRouter, Polza version should appear separately
    # This enables multi-source display: "GPT-4o (OR)" and "GPT-4o (Polza)" both visible
    polza_models = [m for m in base_models if m.get('source') == 'polza']
    polza_added = set()  # Track compound keys to avoid duplicating within Polza

    # DEBUG: Log what we're working with
    logger.info(f"[ModelDuplicator] Found {len(polza_models)} Polza models in base_models")
    logger.info(f"[ModelDuplicator] Current result size before Polza: {len(result)}")
    if polza_models:
        logger.info(f"[ModelDuplicator] Sample Polza IDs: {[m.get('id') for m in polza_models[:3]]}")

    # Build set of already-added compound keys for O(1) lookup
    existing_compound_keys = {r.get('_compound_key') for r in result if r.get('_compound_key')}
    existing_polza_ids = {r.get('id') for r in result if r.get('source') == 'polza'}

    for pm in polza_models:
        pm_id = pm.get('id', '')
        compound_key = pm.get('_compound_key', f"{pm_id}@polza")

        # Skip if we already added this exact Polza model in this loop
        if compound_key in polza_added:
            continue

        # CRITICAL FIX (Kimi K2.5): Check if already added via MULTI_SOURCE_MODELS
        if compound_key in existing_compound_keys or pm_id in existing_polza_ids:
            logger.debug(f"[ModelDuplicator] Skipping Polza (already in result): {pm_id}")
            continue

        polza_added.add(compound_key)

        polza_copy = {**pm}
        # Ensure source fields are set
        polza_copy['source'] = 'polza'
        if 'source_display' not in polza_copy:
            polza_copy['source_display'] = 'Polza'
        # Ensure compound key for React
        polza_copy['_compound_key'] = compound_key
        # Update name to include source suffix if not already present
        base_name = pm.get('name', pm_id.split('/')[-1] if '/' in pm_id else pm_id)
        if '(Polza)' not in base_name and '(polza)' not in base_name.lower():
            polza_copy['name'] = f"{base_name} (Polza)"
        polza_copy['routes'] = [{
            'type': 'polza',
            'display': polza_copy.get('source_display', 'Polza'),
            'id': pm_id
        }]
        result.append(polza_copy)

    # Final stats
    total_polza_in_result = len([r for r in result if r.get('source') == 'polza'])
    logger.info(f"[ModelDuplicator] Added {len(polza_added)} NEW Polza models, total Polza in result: {total_polza_in_result}")

    return result


def get_duplication_stats() -> Dict[str, Any]:
    """
    Get statistics about model duplication.

    Phase 112: Extended for multi-source support.

    Returns info about:
    - How many models have multiple sources
    - Which providers have active keys
    - Total models after duplication
    """
    stats = {
        'multi_source_models': len(MULTI_SOURCE_MODELS),
        'providers_with_keys': {},
        'total_possible_duplicates': 0,
        'sources_summary': {}
    }

    # Check all providers
    all_providers = [
        ProviderType.XAI, ProviderType.OPENAI, ProviderType.ANTHROPIC,
        ProviderType.GEMINI, ProviderType.OPENROUTER, ProviderType.POLZA,
        ProviderType.POE, ProviderType.MISTRAL, ProviderType.NANOGPT
    ]

    for provider in all_providers:
        has_key = has_active_key(provider)
        stats['providers_with_keys'][provider.value] = has_key

    # Count sources
    for model_id, config in MULTI_SOURCE_MODELS.items():
        sources = config.get('sources', [])
        for src in sources:
            src_type = src['type']
            if src_type not in stats['sources_summary']:
                stats['sources_summary'][src_type] = 0
            stats['sources_summary'][src_type] += 1

            # Count if key is available
            if has_active_key(src['requires_key']):
                stats['total_possible_duplicates'] += 1

    # Backwards compatibility
    stats['dual_source_models'] = stats['multi_source_models']

    return stats
