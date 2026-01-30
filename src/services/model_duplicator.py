# === PHASE 94.4: MODEL DUPLICATOR ===
"""
MARKER_94.4_DUPLICATOR: Generate duplicate entries for multi-source models.

Shows same model via different providers IF keys exist (Direct vs OpenRouter).

@status: active
@phase: 96
@depends: unified_key_manager
@used_by: model_routes.py
"""

import logging
from typing import List, Dict, Any, Optional
from src.utils.unified_key_manager import get_key_manager, ProviderType

logger = logging.getLogger(__name__)


# MARKER_94.4_DUAL_SOURCE: Models available from both direct API and OpenRouter
DUAL_SOURCE_MODELS = {
    # === XAI / GROK (2026 models) ===
    "grok-4": {
        "direct": {
            "provider": "xai",
            "requires_key": ProviderType.XAI,
            "display_suffix": "xAI"
        },
        "openrouter": {
            "id_format": "x-ai/grok-4",
            "display_suffix": "OR"
        }
    },
    "grok-4-fast": {
        "direct": {
            "provider": "xai",
            "requires_key": ProviderType.XAI,
            "display_suffix": "xAI"
        },
        "openrouter": {
            "id_format": "x-ai/grok-4-fast",
            "display_suffix": "OR"
        }
    },
    "grok-4.1-fast": {
        "direct": {
            "provider": "xai",
            "requires_key": ProviderType.XAI,
            "display_suffix": "xAI"
        },
        "openrouter": {
            "id_format": "x-ai/grok-4.1-fast",
            "display_suffix": "OR"
        }
    },
    "grok-3": {
        "direct": {
            "provider": "xai",
            "requires_key": ProviderType.XAI,
            "display_suffix": "xAI"
        },
        "openrouter": {
            "id_format": "x-ai/grok-3",
            "display_suffix": "OR"
        }
    },
    "grok-3-mini": {
        "direct": {
            "provider": "xai",
            "requires_key": ProviderType.XAI,
            "display_suffix": "xAI"
        },
        "openrouter": {
            "id_format": "x-ai/grok-3-mini",
            "display_suffix": "OR"
        }
    },
    "grok-3-beta": {
        "direct": {
            "provider": "xai",
            "requires_key": ProviderType.XAI,
            "display_suffix": "xAI"
        },
        "openrouter": {
            "id_format": "x-ai/grok-3-beta",
            "display_suffix": "OR"
        }
    },
    "grok-3-mini-beta": {
        "direct": {
            "provider": "xai",
            "requires_key": ProviderType.XAI,
            "display_suffix": "xAI"
        },
        "openrouter": {
            "id_format": "x-ai/grok-3-mini-beta",
            "display_suffix": "OR"
        }
    },
    "grok-code-fast-1": {
        "direct": {
            "provider": "xai",
            "requires_key": ProviderType.XAI,
            "display_suffix": "xAI"
        },
        "openrouter": {
            "id_format": "x-ai/grok-code-fast-1",
            "display_suffix": "OR"
        }
    },
    # Legacy Grok models
    "grok-2-latest": {
        "direct": {
            "provider": "xai",
            "requires_key": ProviderType.XAI,
            "display_suffix": "xAI"
        },
        "openrouter": {
            "id_format": "x-ai/grok-2-latest",
            "display_suffix": "OR"
        }
    },
    "grok-2-1212": {
        "direct": {
            "provider": "xai",
            "requires_key": ProviderType.XAI,
            "display_suffix": "xAI"
        },
        "openrouter": {
            "id_format": "x-ai/grok-2-1212",
            "display_suffix": "OR"
        }
    },
    "grok-2-vision-1212": {
        "direct": {
            "provider": "xai",
            "requires_key": ProviderType.XAI,
            "display_suffix": "xAI"
        },
        "openrouter": {
            "id_format": "x-ai/grok-2-vision-1212",
            "display_suffix": "OR"
        }
    },
    "grok-vision-beta": {
        "direct": {
            "provider": "xai",
            "requires_key": ProviderType.XAI,
            "display_suffix": "xAI"
        },
        "openrouter": {
            "id_format": "x-ai/grok-vision-beta",
            "display_suffix": "OR"
        }
    },

    # === OPENAI / GPT ===
    "gpt-4o": {
        "direct": {
            "provider": "openai",
            "requires_key": ProviderType.OPENAI,
            "display_suffix": "Direct"
        },
        "openrouter": {
            "id_format": "openai/gpt-4o",
            "display_suffix": "OR"
        }
    },
    "gpt-4o-mini": {
        "direct": {
            "provider": "openai",
            "requires_key": ProviderType.OPENAI,
            "display_suffix": "Direct"
        },
        "openrouter": {
            "id_format": "openai/gpt-4o-mini",
            "display_suffix": "OR"
        }
    },
    "gpt-4-turbo": {
        "direct": {
            "provider": "openai",
            "requires_key": ProviderType.OPENAI,
            "display_suffix": "Direct"
        },
        "openrouter": {
            "id_format": "openai/gpt-4-turbo",
            "display_suffix": "OR"
        }
    },

    # === ANTHROPIC / CLAUDE ===
    "claude-3-5-sonnet-latest": {
        "direct": {
            "provider": "anthropic",
            "requires_key": ProviderType.ANTHROPIC,
            "display_suffix": "Direct"
        },
        "openrouter": {
            "id_format": "anthropic/claude-3.5-sonnet",
            "display_suffix": "OR"
        }
    },
    "claude-3-5-haiku-latest": {
        "direct": {
            "provider": "anthropic",
            "requires_key": ProviderType.ANTHROPIC,
            "display_suffix": "Direct"
        },
        "openrouter": {
            "id_format": "anthropic/claude-3.5-haiku",
            "display_suffix": "OR"
        }
    },
    "claude-3-opus-latest": {
        "direct": {
            "provider": "anthropic",
            "requires_key": ProviderType.ANTHROPIC,
            "display_suffix": "Direct"
        },
        "openrouter": {
            "id_format": "anthropic/claude-3-opus",
            "display_suffix": "OR"
        }
    },

    # === GOOGLE / GEMINI ===
    "gemini-2.0-flash-exp": {
        "direct": {
            "provider": "google",
            "requires_key": ProviderType.GEMINI,
            "display_suffix": "Direct"
        },
        "openrouter": {
            "id_format": "google/gemini-2.0-flash-exp:free",
            "display_suffix": "OR"
        }
    },
    "gemini-exp-1206": {
        "direct": {
            "provider": "google",
            "requires_key": ProviderType.GEMINI,
            "display_suffix": "Direct"
        },
        "openrouter": {
            "id_format": "google/gemini-exp-1206:free",
            "display_suffix": "OR"
        }
    },
    "gemini-pro": {
        "direct": {
            "provider": "google",
            "requires_key": ProviderType.GEMINI,
            "display_suffix": "Direct"
        },
        "openrouter": {
            "id_format": "google/gemini-pro",
            "display_suffix": "OR"
        }
    },
}


def has_active_key(provider_type: ProviderType) -> bool:
    """
    Check if provider has an active (non-rate-limited) API key.

    MARKER_94.4_KEY_CHECK: Determines if direct API version should be shown.
    """
    km = get_key_manager()
    key = km.get_active_key(provider_type)
    return key is not None


def create_duplicates(base_models: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    MARKER_94.4_CREATE_DUPLICATES: Main duplication logic.

    Takes base model list, returns expanded list with duplicates.

    Logic:
    1. Check which API keys are active
    2. For each model in DUAL_SOURCE_MODELS:
       - If direct key exists → add direct version
       - Always add OpenRouter version (fallback available)
    3. Mark duplicates with source: "direct" | "openrouter"

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

        # Check if this model has dual sources
        # Try to match by ID or by stripping provider prefix
        clean_id = model_id.split('/')[-1] if '/' in model_id else model_id

        if clean_id in DUAL_SOURCE_MODELS:
            config = DUAL_SOURCE_MODELS[clean_id]

            # Skip if already processed (avoid duplicating duplicates)
            if clean_id in processed_ids:
                continue
            processed_ids.add(clean_id)

            # === Direct API version ===
            direct_cfg = config['direct']
            if has_active_key(direct_cfg['requires_key']):
                direct_model = {**model}
                direct_model['id'] = clean_id  # Use clean ID for direct API
                direct_model['provider'] = direct_cfg['provider']
                direct_model['source'] = 'direct'
                direct_model['source_display'] = direct_cfg['display_suffix']
                direct_model['name'] = f"{base_name} ({direct_cfg['display_suffix']})"
                result.append(direct_model)
                logger.debug(f"[ModelDuplicator] Added direct: {direct_model['id']} ({direct_cfg['display_suffix']})")

            # === OpenRouter version (always available as fallback) ===
            or_cfg = config['openrouter']
            or_model = {**model}
            or_model['id'] = or_cfg['id_format']
            or_model['provider'] = 'openrouter'
            or_model['source'] = 'openrouter'
            or_model['source_display'] = or_cfg['display_suffix']
            or_model['name'] = f"{base_name} ({or_cfg['display_suffix']})"
            result.append(or_model)
            logger.debug(f"[ModelDuplicator] Added OR: {or_model['id']}")

        else:
            # Not a dual-source model, keep as-is
            # Add default source field
            model_copy = {**model}
            if 'source' not in model_copy:
                # Determine source from ID
                if '/' in model_id:
                    model_copy['source'] = 'openrouter'
                    model_copy['source_display'] = 'OR'
                elif model.get('provider') == 'ollama':
                    model_copy['source'] = 'local'
                    model_copy['source_display'] = 'Local'
                else:
                    model_copy['source'] = 'direct'
                    model_copy['source_display'] = model.get('provider', '').upper()[:3]
            result.append(model_copy)

    return result


def get_duplication_stats() -> Dict[str, Any]:
    """
    Get statistics about model duplication.

    Returns info about:
    - How many models have dual sources
    - Which providers have active keys
    - Total models after duplication
    """
    stats = {
        'dual_source_models': len(DUAL_SOURCE_MODELS),
        'providers_with_keys': {},
        'total_possible_duplicates': 0
    }

    for provider in [ProviderType.XAI, ProviderType.OPENAI, ProviderType.ANTHROPIC, ProviderType.GEMINI]:
        has_key = has_active_key(provider)
        stats['providers_with_keys'][provider.value] = has_key
        if has_key:
            # Count how many models use this provider
            count = sum(1 for cfg in DUAL_SOURCE_MODELS.values()
                       if cfg['direct']['requires_key'] == provider)
            stats['total_possible_duplicates'] += count

    return stats
