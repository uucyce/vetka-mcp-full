# === PHASE 56: MODEL API ROUTES ===
"""
FastAPI routes for model phonebook management.

Provides endpoints for listing, selecting, and managing AI models.

@status: active
@phase: 96
@depends: fastapi, model_registry, model_duplicator
@used_by: main.py router registration
"""

import asyncio
import time
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

from src.services.model_registry import get_model_registry

router = APIRouter(prefix="/api/models", tags=["models"])


# MARKER_155.PERF.MODELS_SINGLEFLIGHT:
# Keep /api/models fast on startup and avoid duplicate remote fetches.
_models_cache = {
    "ts": 0.0,
    "response": None,
}
_MODELS_TTL_SEC = 60.0
_models_lock = asyncio.Lock()


# MARKER_138.S2_5_MODEL_AUTODETECT
async def _detect_qwen_tts_server() -> Dict[str, Any]:
    """MARKER_138.S2_5_QWEN_TTS_DETECT: Detect local Qwen TTS service."""
    import httpx

    url = "http://127.0.0.1:5003/health"
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            resp = await client.get(url)
        if resp.status_code == 200:
            payload = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {}
            return {
                "running": True,
                "url": url,
                "details": payload,
            }
    except Exception:
        pass
    return {"running": False, "url": url}


def _infer_provider_badge(model: Dict[str, Any]) -> str:
    source = (model.get("source") or "").lower()
    provider = (model.get("provider") or "").lower()
    if source == "polza" or provider == "polza":
        return "Polza"
    if source == "poe" or provider == "poe":
        return "Poe"
    if source == "openrouter" or provider == "openrouter":
        return "OpenRouter"
    if provider in {"ollama", "local", "browser"}:
        return "Local"
    if source:
        return source.title()
    if provider:
        return provider.title()
    return "Unknown"


def _categorize_models(models: List[Dict[str, Any]]) -> Dict[str, int]:
    result = {"text": 0, "voice": 0, "image": 0, "embedding": 0}
    for m in models:
        m_type = (m.get("type") or "").lower()
        caps = [str(c).lower() for c in (m.get("capabilities") or [])]

        if m_type == "voice" or "tts" in caps or "stt" in caps:
            result["voice"] += 1
        elif "embeddings" in caps or "embedding" in caps:
            result["embedding"] += 1
        elif "vision" in caps or "image_gen" in caps or "video_gen" in caps:
            result["image"] += 1
        else:
            result["text"] += 1
    return result


async def _build_autodetect_payload(force_refresh: bool = False) -> Dict[str, Any]:
    """MARKER_138.S2_5_MODEL_AUTODETECT: Unified dynamic model inventory."""
    from src.elisya.model_fetcher import get_all_models, classify_model_type

    registry = get_model_registry()

    # Keep discovery dynamic: no hardcoded provider list here.
    await registry.discover_ollama_models()
    await registry.discover_voice_models()

    cloud_models = await get_all_models(force_refresh=force_refresh)
    for model in cloud_models:
        classify_model_type(model)
        model.setdefault("provider", model.get("provider") or "openrouter")
        model.setdefault("source", model.get("source") or "openrouter")
        model.setdefault("source_display", _infer_provider_badge(model))

    local_models = [m.to_dict() for m in registry.get_local()]
    mcp_agents = [m.to_dict() for m in registry.get_mcp_agents()]

    qwen_tts = await _detect_qwen_tts_server()
    if qwen_tts.get("running"):
        local_models.append(
            {
                "id": "qwen3-tts/local",
                "name": "Qwen3 TTS (Local)",
                "provider": "local",
                "type": "voice",
                "capabilities": ["tts"],
                "context_window": 0,
                "pricing": {"prompt": "0", "completion": "0"},
                "available": True,
                "source": "local",
                "source_display": "Local",
            }
        )

    combined = []
    combined.extend(cloud_models)
    combined.extend(local_models)
    combined.extend(mcp_agents)

    return {
        "success": True,
        "models": combined,
        "cloud_models": cloud_models,
        "local_models": local_models,
        "mcp_agents": mcp_agents,
        "qwen_tts": qwen_tts,
        "categories": _categorize_models(combined),
        "count": len(combined),
        "force_refresh": force_refresh,
    }


@router.get("/autodetect")
async def autodetect_models(force_refresh: bool = Query(False)):
    return await _build_autodetect_payload(force_refresh=force_refresh)


class AddKeyRequest(BaseModel):
    provider: str
    key: str


@router.get("")
async def list_models():
    """
    Get all models in phonebook.

    MARKER_112_LIST_MODELS: Returns models from fetcher with multi-source support.
    Phase 112: Uses model_fetcher directly for proper source tracking.
    """
    cached = _models_cache.get("response")
    now = time.monotonic()
    if cached is not None and (now - float(_models_cache.get("ts", 0.0))) <= _MODELS_TTL_SEC:
        return cached

    async with _models_lock:
        cached = _models_cache.get("response")
        now = time.monotonic()
        if cached is not None and (now - float(_models_cache.get("ts", 0.0))) <= _MODELS_TTL_SEC:
            return cached

        from src.services.model_duplicator import create_duplicates, get_duplication_stats
        from src.elisya.model_fetcher import get_all_models

        # Phase 112: Use model_fetcher for proper source tracking
        base_models = await get_all_models()

        # Phase 112: Generate duplicates for models with multiple sources
        expanded_models = create_duplicates(base_models)

        stats = get_duplication_stats()

        response = {
            "models": expanded_models,
            "count": len(expanded_models),
            "base_count": len(base_models),
            "duplicates_added": len(expanded_models) - len(base_models),
            "duplication_stats": stats,
        }
        _models_cache["ts"] = time.monotonic()
        _models_cache["response"] = response
        return response


@router.get("/available")
async def list_available():
    """Get available models only."""
    registry = get_model_registry()
    return {
        'models': [m.to_dict() for m in registry.get_available()]
    }


@router.get("/local")
async def list_local():
    """Get local (Ollama) models."""
    registry = get_model_registry()
    return {
        'models': [m.to_dict() for m in registry.get_local()]
    }


@router.get("/free")
async def list_free():
    """Get free models (local + cloud free tier)."""
    registry = get_model_registry()
    return {
        'models': [m.to_dict() for m in registry.get_free()]
    }


@router.get("/favorites")
async def list_favorites():
    """Get favorite models."""
    registry = get_model_registry()
    return {
        'models': registry.get_favorites()
    }


@router.get("/recent")
async def list_recent():
    """Get recently used models."""
    registry = get_model_registry()
    return {
        'models': registry.get_recent()
    }


@router.post("/favorites/{model_id}")
async def add_favorite(model_id: str):
    """Add model to favorites."""
    registry = get_model_registry()
    registry.add_to_favorites(model_id)
    return {'success': True}


@router.delete("/favorites/{model_id}")
async def remove_favorite(model_id: str):
    """Remove model from favorites."""
    registry = get_model_registry()
    registry.remove_from_favorites(model_id)
    return {'success': True}


@router.post("/keys")
async def add_api_key(body: AddKeyRequest):
    """Add API key for provider."""
    registry = get_model_registry()
    registry.add_api_key(body.provider, body.key)
    return {'success': True, 'provider': body.provider}


@router.delete("/keys/{provider}")
async def remove_api_key(provider: str):
    """Remove API key for provider (all keys)."""
    registry = get_model_registry()
    if registry.remove_api_key(provider):
        return {'success': True}
    raise HTTPException(status_code=404, detail="Key not found")


# MARKER_126.10: Fix DELETE endpoint mismatch — frontend sends key_id (masked)
@router.delete("/keys/{provider}/{key_id}")
async def remove_specific_key(provider: str, key_id: str):
    """
    Remove specific API key by masked ID.

    Frontend sends: /api/keys/openrouter/sk-o****b296
    key_id is the masked key (first4 + **** + last4)
    """
    from src.utils.unified_key_manager import get_key_manager, ProviderType

    km = get_key_manager()

    # Convert provider string to ProviderType if possible
    try:
        provider_key = ProviderType(provider.lower())
    except ValueError:
        provider_key = provider.lower()

    # Find key by masked ID
    keys_list = km.keys.get(provider_key, [])
    for idx, record in enumerate(keys_list):
        if record.mask() == key_id:
            if km.remove_key_by_index(provider_key, idx):
                return {'success': True, 'removed': key_id}
            break

    raise HTTPException(status_code=404, detail=f"Key {key_id} not found for {provider}")


@router.get("/select")
async def select_model(
    task_type: str,
    context_size: int = 4096,
    prefer_local: bool = True,
    prefer_free: bool = True
):
    """Auto-select best model for task."""
    registry = get_model_registry()
    model = registry.select_best(task_type, context_size, prefer_local, prefer_free)

    if model:
        return {'model': model.to_dict()}

    raise HTTPException(status_code=404, detail="No suitable model found")


@router.post("/health/{model_id}")
async def check_health(model_id: str):
    """Check model health."""
    registry = get_model_registry()
    available = await registry.check_health(model_id)
    return {'model_id': model_id, 'available': available}


# === PHASE 93.11: MODEL STATUS FOR UI ===

@router.get("/status")
async def get_model_status():
    """
    Get online/offline status for all models.

    Phase 93.11: Returns status info for phonebook UI:
    - status: "online" | "offline" | "unknown"
    - last_success: Unix timestamp (last seen)
    - last_error: Unix timestamp
    - error_code: HTTP error code or None
    - call_count: Total calls made

    Used for:
    - Blue/gray status dots in model list
    - "last seen" timestamps (e.g., "5m ago")
    - Error detection for offline models
    """
    from src.elisya.model_router_v2 import get_model_status_for_ui
    from src.elisya.provider_registry import ProviderRegistry

    status_data = get_model_status_for_ui()

    # Add via_openrouter flag based on provider detection
    result = {}
    for model_id, status in status_data.items():
        provider = ProviderRegistry.detect_provider(model_id)
        via_or = provider.value == "openrouter" or "/" in model_id

        result[model_id] = {
            **status,
            "via_openrouter": via_or
        }

    return {"models": result}


# === PHASE 111: MODEL CACHE REFRESH ===

@router.post("/refresh")
async def refresh_model_cache(provider: Optional[str] = None):
    """
    Force refresh model cache.

    Phase 111: Manual cache invalidation for model discovery.
    Bypasses 24-hour cache to fetch latest models from providers.

    Args:
        provider: Optional provider to refresh (openrouter, gemini, polza)
                  If None, refreshes all providers.

    Returns:
        success: bool
        count: number of models after refresh
        new_count: number of newly discovered models
    """
    from src.elisya.model_fetcher import load_cache

    # Get old count for comparison
    old_cache = load_cache()
    old_count = len(old_cache.get('models', [])) if old_cache else 0
    old_ids = {m['id'] for m in old_cache.get('models', [])} if old_cache else set()

    payload = await _build_autodetect_payload(force_refresh=True)
    models = payload.get("models", [])

    # Calculate new models
    new_ids = {m['id'] for m in models}
    new_model_ids = new_ids - old_ids
    new_count = len(new_model_ids)

    return {
        "success": True,
        "count": len(models),
        "previous_count": old_count,
        "new_count": new_count,
        "categories": payload.get("categories", {}),
        "qwen_tts": payload.get("qwen_tts", {}),
        "new_models": list(new_model_ids)[:10] if new_count > 0 else [],  # First 10 new model IDs
        "message": f"Refreshed: {len(models)} models ({'+' if new_count > 0 else ''}{new_count} new)"
    }


# === PHASE 80.3: MCP AGENTS ===

@router.get("/mcp-agents")
async def list_mcp_agents():
    """
    Get MCP agents (Claude Code, Browser Haiku).

    Phase 80.3: External agents with special permissions.
    These agents can be added to group chats and have extended capabilities.
    """
    registry = get_model_registry()
    agents = registry.get_mcp_agents()

    # Add extended info for UI
    agent_info = []
    for agent in agents:
        info = agent.to_dict()
        # Add role descriptions
        if 'claude_code' in agent.id:
            info['role'] = 'Executor'
            info['description'] = 'Code executor with MCP access'
            info['icon'] = 'terminal'
        elif 'browser_haiku' in agent.id:
            info['role'] = 'Tester'
            info['description'] = 'QA/Observer in Chrome Console'
            info['icon'] = 'eye'
        agent_info.append(info)

    return {
        'agents': agent_info,
        'count': len(agent_info),
        'note': 'MCP agents can be added to group chats with extended permissions'
    }
