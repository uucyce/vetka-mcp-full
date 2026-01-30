"""
VETKA Config Routes - FastAPI Version

@file config_routes.py
@status ACTIVE
@phase Phase 39.2
@lastAudit 2026-01-05

Configuration and tools API routes.
Migrated from src/server/routes/config_routes.py (Flask Blueprint)

Changes from Flask version:
- Blueprint -> APIRouter
- request.get_json() -> Pydantic BaseModel
- current_app.config -> request.app.state
- return jsonify({}) -> return {}
- def -> async def
"""

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from typing import Optional, Dict, Any


router = APIRouter(prefix="/api", tags=["config"])


# ============================================================
# PYDANTIC MODELS
# ============================================================

class ConfigUpdate(BaseModel):
    """Configuration update request - any JSON object."""
    # Accept any fields for flexible config updates
    class Config:
        extra = "allow"


class ToolExecuteRequest(BaseModel):
    """Tool execution request."""
    tool: str
    params: Optional[Dict[str, Any]] = {}


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def _get_agentic_components(request: Request) -> dict:
    """Get agentic tools components from app state."""
    flask_config = getattr(request.app.state, 'flask_config', {})
    return {
        'available': flask_config.get('AGENTIC_TOOLS_AVAILABLE', False),
        'load_config': flask_config.get('load_agentic_config', lambda: {}),
        'save_config': flask_config.get('save_agentic_config', lambda c: False),
        'get_mentions': flask_config.get('get_available_mentions', lambda: []),
        'tool_definitions': flask_config.get('TOOL_DEFINITIONS', {}),
        'tool_executor_cls': flask_config.get('ToolExecutor'),
        'reactions_store': flask_config.get('REACTIONS_STORE', {}),
    }


def _deep_merge(base: dict, update: dict) -> None:
    """Deep merge update into base dict."""
    for key, value in update.items():
        if key in base and isinstance(base[key], dict) and isinstance(value, dict):
            _deep_merge(base[key], value)
        else:
            base[key] = value


# ============================================================
# ROUTES
# ============================================================

@router.get("/config")
async def get_config(request: Request):
    """
    Get current agentic config (models, routing, scenarios).

    Returns configuration without sensitive API keys.
    Returns empty config with note if agentic tools not available.
    """
    components = _get_agentic_components(request)

    if not components['available']:
        # Graceful degradation - return empty config instead of 503
        return {'success': True, 'config': {}, 'note': 'Agentic tools not configured'}

    config = components['load_config']()
    # Remove sensitive API keys from response
    safe_config = {k: v for k, v in config.items() if k != 'api_keys'}

    return {'success': True, 'config': safe_config}


@router.post("/config")
async def update_config(request: Request):
    """
    Update agentic config (partial update supported).

    Accepts any JSON object for flexible updates.
    API keys cannot be updated through this endpoint.
    """
    components = _get_agentic_components(request)

    if not components['available']:
        raise HTTPException(status_code=503, detail="Agentic tools not available")

    try:
        updates = await request.json()
        if not updates:
            raise HTTPException(status_code=400, detail="No data provided")

        # Load current config and merge updates
        config = components['load_config']()

        # Prevent updating API keys through this endpoint
        if 'api_keys' in updates:
            del updates['api_keys']

        # Deep merge
        _deep_merge(config, updates)

        if components['save_config'](config):
            return {'success': True, 'message': 'Config updated'}
        else:
            raise HTTPException(status_code=500, detail="Failed to save config")

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/mentions")
async def get_mentions(request: Request):
    """
    Get available @mentions for autocomplete.

    Returns list of available mentions like @PM, @Dev, @QA, etc.
    """
    components = _get_agentic_components(request)
    mentions = components['get_mentions']()

    return {
        'success': True,
        'mentions': mentions,
        'count': len(mentions)
    }


@router.get("/models/available")
async def get_available_models(request: Request):
    """
    Get list of available models by tier.

    Returns available models, defaults, and aliases.
    Returns empty if agentic tools not available.
    """
    components = _get_agentic_components(request)

    if not components['available']:
        # Graceful degradation
        return {'success': True, 'available': {}, 'defaults': {}, 'aliases': {}}

    config = components['load_config']()
    models = config.get('models', {})

    return {
        'success': True,
        'available': models.get('available', {}),
        'defaults': models.get('defaults', {}),
        'aliases': models.get('aliases', {})
    }


@router.get("/tools/available")
async def get_available_tools(request: Request):
    """
    Get list of available agent tools.

    Returns tool names and their definitions.
    """
    components = _get_agentic_components(request)
    tool_definitions = components['tool_definitions']

    return {
        'success': True,
        'tools': list(tool_definitions.keys()),
        'definitions': tool_definitions
    }


@router.get("/reactions")
async def get_reactions(request: Request):
    """
    Get all saved reactions for restoring UI state on page load.

    Returns reaction data keyed by message ID.
    """
    components = _get_agentic_components(request)
    reactions_store = components['reactions_store']

    return {
        'success': True,
        'reactions': reactions_store,
        'count': len(reactions_store)
    }


@router.post("/tools/execute")
async def execute_tool(req: ToolExecuteRequest, request: Request):
    """
    Execute a single tool (for testing/debugging).

    Args:
        tool: Tool name to execute
        params: Tool parameters (optional)
    """
    components = _get_agentic_components(request)

    if not components['available']:
        raise HTTPException(status_code=503, detail="Agentic tools not available")

    tool_definitions = components['tool_definitions']
    if req.tool not in tool_definitions:
        raise HTTPException(status_code=400, detail=f"Unknown tool: {req.tool}")

    ToolExecutor = components['tool_executor_cls']
    if not ToolExecutor:
        raise HTTPException(status_code=503, detail="ToolExecutor not available")

    try:
        executor = ToolExecutor()
        result = executor.execute(req.tool, req.params or {})

        return {
            'success': result.get('success', False),
            'tool': req.tool,
            'params': req.params,
            'result': result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# PHASE 47: API KEY MANAGEMENT ROUTES
# ============================================================

class AddKeyRequest(BaseModel):
    """Request to add an API key."""
    key: str
    provider: str = "openrouter"
    is_paid: bool = False


@router.get("/keys/status")
async def get_keys_status():
    """
    Get API keys status (without exposing actual keys).

    Returns count of keys per provider and validation status.
    """
    try:
        from src.utils.unified_key_manager import get_key_manager

        km = get_key_manager()
        stats = km.get_stats()

        return {
            'success': True,
            'stats': stats,
            'message': f"OpenRouter: {stats['openrouter_keys']} keys loaded"
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'stats': {}
        }


@router.post("/keys/add")
async def add_api_key(req: AddKeyRequest):
    """
    Add a new API key.

    Args:
        key: The API key to add
        provider: Provider name (openrouter, gemini)
        is_paid: For OpenRouter, whether this is a paid key
    """
    try:
        from src.utils.unified_key_manager import get_key_manager, ProviderType

        km = get_key_manager()
        km.load_from_config()  # Load existing keys first

        if req.provider.lower() == "openrouter":
            result = km.add_openrouter_key(req.key, is_paid=req.is_paid)
        else:
            # Generic add
            provider = ProviderType(req.provider.lower())
            success = km.add_key_direct(provider, req.key)
            if success:
                km.save_to_config()
                result = {
                    'success': True,
                    'message': f'Key added for {req.provider}',
                    'saved_to_config': True
                }
            else:
                result = {
                    'success': False,
                    'message': f'Invalid key format for {req.provider}'
                }

        return result

    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid provider: {req.provider}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class SmartKeyRequest(BaseModel):
    """Request for smart key detection/addition."""
    key: str


@router.post("/keys/detect")
async def detect_key_type(req: SmartKeyRequest):
    """
    Phase 57.12: Detect API key type/provider.

    Args:
        key: The API key to analyze

    Returns:
        Detected provider info with confidence
    """
    try:
        from src.elisya.api_key_detector import detect_api_key
        from src.elisya.key_learner import get_key_learner

        key = req.key.strip()
        if not key:
            return {'success': False, 'error': 'No key provided'}

        # Try static pattern detection
        detected = detect_api_key(key)

        # If not detected, try learned patterns
        if not detected or not detected.get('provider'):
            learner = get_key_learner()
            learned = learner.check_learned_pattern(key)
            if learned:
                detected = learned
                detected['source'] = 'learned'

        if detected and detected.get('provider'):
            # Normalize provider names (openai_new, openai_legacy -> openai)
            provider = detected['provider']
            if provider.startswith('openai'):
                provider = 'openai'

            return {
                'success': True,
                'detected': True,
                'provider': provider,
                'display_name': detected.get('display_name', provider.title()),
                'confidence': detected.get('confidence', 0.9),
                'source': detected.get('source', 'static')
            }
        else:
            # Unknown key - analyze for user
            learner = get_key_learner()
            analysis = learner.analyze_key(key)
            return {
                'success': True,
                'detected': False,
                'analysis': analysis,
                'message': 'Unknown key type - please specify provider'
            }

    except Exception as e:
        import traceback
        traceback.print_exc()
        return {'success': False, 'error': str(e)}


@router.post("/keys/add-smart")
async def add_key_smart(req: SmartKeyRequest):
    """
    Phase 57.12: Smart key addition with auto-detection.

    Auto-detects provider and saves key to config.
    If provider unknown, returns error asking for manual input.

    Args:
        key: The API key to add

    Returns:
        Success/failure with provider info
    """
    try:
        from src.elisya.api_key_detector import detect_api_key
        from src.elisya.key_learner import get_key_learner

        key = req.key.strip()
        if not key:
            return {'success': False, 'error': 'No key provided'}

        # Detect provider
        detected = detect_api_key(key)

        # Try learned patterns if not detected
        if not detected or not detected.get('provider'):
            learner = get_key_learner()
            learned = learner.check_learned_pattern(key)
            if learned:
                detected = learned

        if not detected or not detected.get('provider'):
            return {
                'success': False,
                'error': 'Unknown key type',
                'message': 'Could not detect provider. Please specify manually.'
            }

        # Normalize provider names (openai_new, openai_legacy -> openai)
        provider = detected['provider']
        if provider.startswith('openai'):
            provider = 'openai'

        # Save key using KeyLearner (handles config persistence)
        learner = get_key_learner()
        saved = learner._save_key_to_config(provider, key)

        if saved:
            return {
                'success': True,
                'provider': provider,
                'display_name': detected.get('display_name', provider.title()),
                'confidence': detected.get('confidence', 0.9),
                'message': f'{detected.get("display_name", provider)} key saved!'
            }
        else:
            return {
                'success': False,
                'error': 'Failed to save key to config'
            }

    except Exception as e:
        import traceback
        traceback.print_exc()
        return {'success': False, 'error': str(e)}


@router.get("/keys/validate")
async def validate_keys():
    """
    Validate all stored API keys.

    Returns validation status for each provider.
    """
    try:
        from src.utils.unified_key_manager import get_key_manager

        km = get_key_manager()
        validation = km.validate_keys()

        return {
            'success': True,
            'validation': validation,
            'message': 'Keys validated'
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }


@router.get("/keys")
async def get_keys_list():
    """
    Phase 57.9: Get all saved API keys by provider.

    Returns keys grouped by provider with masked values for UI display.
    This endpoint is used by ModelDirectory to show saved keys.
    """
    try:
        from pathlib import Path
        import json

        config_file = Path(__file__).parent.parent.parent.parent / "data" / "config.json"
        providers = []

        if config_file.exists():
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
                api_keys = config.get('api_keys', {})

                # Helper to mask keys
                def mask_key(key: str) -> str:
                    if not key or len(key) < 12:
                        return "***"
                    return f"{key[:8]}...{key[-4:]}"

                # Handle each provider's keys
                for provider_name, keys_data in api_keys.items():
                    if provider_name == 'anthropic' and keys_data is None:
                        continue  # Skip null anthropic

                    keys_list = []

                    # Handle different key formats (string, dict, array)
                    if isinstance(keys_data, str) and keys_data:
                        # Single string key (tavily, nanogpt, etc)
                        keys_list.append({
                            'id': f'{provider_name}-1',
                            'provider': provider_name,
                            'key': mask_key(keys_data),
                            'key_full': keys_data,  # For deletion operations
                            'status': 'active'
                        })
                    elif isinstance(keys_data, dict):
                        # OpenRouter format: {'paid': key, 'free': [keys]}
                        if keys_data.get('paid'):
                            keys_list.append({
                                'id': f'{provider_name}-paid',
                                'provider': provider_name,
                                'key': mask_key(keys_data['paid']),
                                'key_full': keys_data['paid'],
                                'status': 'active',
                                'type': 'paid'
                            })
                        for i, key in enumerate(keys_data.get('free', [])):
                            if key:
                                keys_list.append({
                                    'id': f'{provider_name}-free-{i}',
                                    'provider': provider_name,
                                    'key': mask_key(key),
                                    'key_full': key,
                                    'status': 'active',
                                    'type': 'free'
                                })
                    elif isinstance(keys_data, list):
                        # Array of keys (gemini, nanogpt)
                        for i, key in enumerate(keys_data):
                            if key:
                                keys_list.append({
                                    'id': f'{provider_name}-{i}',
                                    'provider': provider_name,
                                    'key': mask_key(key),
                                    'key_full': key,
                                    'status': 'active'
                                })

                    if keys_list:
                        providers.append({
                            'provider': provider_name,
                            'keys': keys_list,
                            'status': 'active',
                            'count': len(keys_list)
                        })

        return {
            'success': True,
            'providers': providers,
            'count': len(providers)
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
        return {
            'success': False,
            'error': str(e),
            'providers': []
        }


@router.get("/agents/status")
async def get_agents_status():
    """
    Get status of initialized agents (PM, Dev, QA, Architect).
    """
    try:
        from src.api.handlers.handler_utils import get_agents
        from src.initialization.components_init import get_agents_available

        agents = get_agents()
        available = get_agents_available()

        return {
            'success': True,
            'agents_available': available,
            'agents': list(agents.keys()) if agents else [],
            'count': len(agents) if agents else 0
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'agents_available': False
        }


# ============================================================
# PHASE 48: MODEL DIRECTORY API
# ============================================================

@router.get("/models")
async def list_models(refresh: bool = False):
    """
    Get all available models with pricing information.

    Args:
        refresh: Force refresh from APIs (bypass cache)

    Returns:
        List of models with id, name, pricing, context_length, provider
    """
    try:
        from src.elisya.model_fetcher import get_all_models, categorize_models

        models = await get_all_models(force_refresh=refresh)

        # Phase 60.5.1: Add Grok voice models (X.AI direct API + OpenRouter fallback)
        # Updated Jan 2026: grok-beta retired, using current model IDs
        grok_voice_models = [
            {
                'id': 'grok-3-mini',  # Direct X.AI API name
                'name': 'Grok 3 Mini (Voice)',
                'type': 'voice',
                'capabilities': ['tts', 'realtime'],
                'context_length': 131072,
                'pricing': {'prompt': '0.00', 'completion': '0.00'},  # Free tier!
                'description': 'Fast Grok 3 Mini - free tier, great for voice',
            },
            {
                'id': 'grok-4',  # Direct X.AI API name
                'name': 'Grok 4 (Voice)',
                'type': 'voice',
                'capabilities': ['tts', 'realtime', 'reasoning'],
                'context_length': 256000,
                'pricing': {'prompt': '0.003', 'completion': '0.015'},
                'description': 'Latest Grok 4 with reasoning support',
            },
        ]
        models.extend(grok_voice_models)

        # Format response
        formatted = []
        for m in models:
            model_id = m.get('id', '')
            provider = model_id.split('/')[0] if '/' in model_id else 'unknown'
            pricing = m.get('pricing', {})

            formatted.append({
                'id': model_id,
                'name': m.get('name', model_id),
                'provider': provider,
                'context_length': m.get('context_length', 4096),
                'pricing': {
                    'prompt': pricing.get('prompt', '0'),
                    'completion': pricing.get('completion', '0')
                },
                'description': m.get('description', '')[:100] if m.get('description') else '',
                # Phase 60.5: Voice model support
                'type': m.get('type'),  # 'voice' for audio models
                'capabilities': m.get('capabilities', []),  # ['stt', 'tts', 'vision', etc.]
            })

        # MARKER_94.4_CONFIG_DUPLICATION: Add source markers and duplicates for multi-provider models
        from src.services.model_duplicator import create_duplicates
        formatted = create_duplicates(formatted)

        # Get categories for summary
        categories = categorize_models(models)

        return {
            'success': True,
            'count': len(formatted),
            'summary': {
                'free': len(categories['free']),
                'cheap': len(categories['cheap']),
                'premium': len(categories['premium']),
                'voice': len(categories.get('voice', [])),  # Phase 60.5
                'providers': list(categories['by_provider'].keys())
            },
            'models': formatted
        }

    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'count': 0,
            'models': []
        }


@router.get("/models/categories")
async def get_model_categories():
    """
    Get models organized by category (free, cheap, premium, by provider).
    """
    try:
        from src.elisya.model_fetcher import get_all_models, categorize_models

        models = await get_all_models()
        categories = categorize_models(models)

        # Simplify for API response
        result = {
            'free': [{'id': m['id'], 'name': m.get('name', m['id'])} for m in categories['free'][:20]],
            'cheap': [{'id': m['id'], 'name': m.get('name', m['id'])} for m in categories['cheap'][:20]],
            'premium': [{'id': m['id'], 'name': m.get('name', m['id'])} for m in categories['premium'][:20]],
            'providers': {
                p: len(models) for p, models in categories['by_provider'].items()
            }
        }

        return {
            'success': True,
            'categories': result
        }

    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }
