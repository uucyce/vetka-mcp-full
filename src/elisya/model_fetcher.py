"""
VETKA Model Fetcher - Phase 48.
Fetches available models from OpenRouter and Gemini APIs with caching.

@status: active
@phase: 96
@depends: httpx, json, asyncio, pathlib, datetime, typing, logging
@used_by: model_registry, config_routes
"""

import httpx
import json
import asyncio
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

# Cache configuration
CACHE_FILE = Path(__file__).parent.parent.parent / "data" / "models_cache.json"
CACHE_DURATION = timedelta(hours=24)


async def fetch_openrouter_models(api_key: str) -> List[Dict[str, Any]]:
    """
    Fetch all available models from OpenRouter API.
    Phase 60.5: Also classifies voice/audio capabilities.

    Args:
        api_key: OpenRouter API key

    Returns:
        List of model dictionaries with id, name, pricing, capabilities, type, etc.
    """
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            resp = await client.get(
                'https://openrouter.ai/api/v1/models',
                headers={
                    'Authorization': f'Bearer {api_key}',
                    'Content-Type': 'application/json'
                }
            )
            if resp.status_code == 200:
                data = resp.json()
                models = data.get('data', [])

                # Phase 60.5: Classify each model
                voice_count = 0
                for model in models:
                    classify_model_type(model)
                    if model.get('type') == 'voice':
                        voice_count += 1

                logger.info(f"Fetched {len(models)} models from OpenRouter ({voice_count} voice)")
                return models
            else:
                logger.error(f"OpenRouter API error: {resp.status_code}")
                return []
        except Exception as e:
            logger.error(f"Failed to fetch OpenRouter models: {e}")
            return []


async def fetch_gemini_models(api_key: str) -> List[Dict[str, Any]]:
    """
    Fetch available models from Gemini API.

    Args:
        api_key: Gemini API key

    Returns:
        List of model dictionaries normalized to OpenRouter format
    """
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            resp = await client.get(
                f'https://generativelanguage.googleapis.com/v1beta/models?key={api_key}'
            )
            if resp.status_code == 200:
                data = resp.json()
                raw_models = data.get('models', [])

                # Normalize to OpenRouter-like format
                models = []
                for m in raw_models:
                    model_id = m.get('name', '').replace('models/', '')
                    models.append({
                        'id': f'google/{model_id}',
                        'name': m.get('displayName', model_id),
                        'description': m.get('description', ''),
                        'context_length': m.get('inputTokenLimit', 32000),
                        'pricing': {
                            'prompt': '0.00015',  # Approximate Gemini pricing
                            'completion': '0.0006'
                        },
                        'provider': 'google',
                        'source': 'gemini_direct'  # Mark as direct API
                    })

                logger.info(f"Fetched {len(models)} models from Gemini")
                return models
            else:
                logger.error(f"Gemini API error: {resp.status_code}")
                return []
        except Exception as e:
            logger.error(f"Failed to fetch Gemini models: {e}")
            return []


def load_cache() -> Optional[Dict[str, Any]]:
    """Load models from cache if valid."""
    if not CACHE_FILE.exists():
        return None

    try:
        with open(CACHE_FILE, 'r', encoding='utf-8') as f:
            cache = json.load(f)

        cached_at = datetime.fromisoformat(cache.get('cached_at', '2000-01-01'))
        if datetime.now() - cached_at < CACHE_DURATION:
            logger.debug(f"Using cached models from {cached_at}")
            return cache
        else:
            logger.debug("Cache expired")
            return None
    except Exception as e:
        logger.error(f"Failed to load cache: {e}")
        return None


def save_cache(models: List[Dict[str, Any]], source: str = 'mixed') -> None:
    """Save models to cache file."""
    try:
        CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump({
                'cached_at': datetime.now().isoformat(),
                'source': source,
                'count': len(models),
                'models': models
            }, f, indent=2)
        logger.info(f"Cached {len(models)} models to {CACHE_FILE}")
    except Exception as e:
        logger.error(f"Failed to save cache: {e}")


async def get_all_models(force_refresh: bool = False) -> List[Dict[str, Any]]:
    """
    Get all available models with caching.

    Args:
        force_refresh: If True, bypass cache and fetch fresh

    Returns:
        List of all available models from all providers
    """
    # Check cache first
    if not force_refresh:
        cache = load_cache()
        if cache:
            return cache.get('models', [])

    # Fetch fresh models
    from src.utils.unified_key_manager import get_key_manager
    km = get_key_manager()

    all_models = []

    # Fetch from OpenRouter (primary source - has most models)
    openrouter_key = km.get_openrouter_key()
    if openrouter_key:
        openrouter_models = await fetch_openrouter_models(openrouter_key)
        all_models.extend(openrouter_models)

    # Optionally fetch Gemini direct models (for direct API access)
    gemini_key = km.get_key('gemini')
    if gemini_key:
        gemini_models = await fetch_gemini_models(gemini_key)
        # Add only models not already in OpenRouter list
        openrouter_ids = {m['id'] for m in all_models}
        for gm in gemini_models:
            if gm['id'] not in openrouter_ids:
                all_models.append(gm)

    # Save to cache
    if all_models:
        save_cache(all_models)

    return all_models


def get_models_sync(force_refresh: bool = False) -> List[Dict[str, Any]]:
    """
    Synchronous wrapper for get_all_models().

    Args:
        force_refresh: If True, bypass cache

    Returns:
        List of models
    """
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    return loop.run_until_complete(get_all_models(force_refresh))


def classify_model_type(model: Dict[str, Any]) -> Dict[str, Any]:
    """
    Phase 60.5: Classify model type based on modalities.

    Adds 'type' and 'capabilities' fields to model dict.
    Detects voice (STT/TTS), vision, video capabilities.
    """
    arch = model.get('architecture', {})
    input_modalities = arch.get('input_modalities', [])
    output_modalities = arch.get('output_modalities', [])

    capabilities = []
    model_type = None

    # Detect audio/voice capabilities
    has_audio_input = 'audio' in input_modalities or 'speech' in input_modalities
    has_audio_output = 'audio' in output_modalities or 'speech' in output_modalities

    if has_audio_input:
        capabilities.append('stt')  # Speech-to-Text
    if has_audio_output:
        capabilities.append('tts')  # Text-to-Speech

    # Voice type = models with any audio capability
    if has_audio_input or has_audio_output:
        model_type = 'voice'

    # Detect vision capabilities
    if 'image' in input_modalities or 'video' in input_modalities:
        capabilities.append('vision')

    # Detect image/video generation
    if 'image' in output_modalities:
        capabilities.append('image_gen')
    if 'video' in output_modalities:
        capabilities.append('video_gen')

    # Add to model
    if capabilities:
        model['capabilities'] = capabilities
    if model_type:
        model['type'] = model_type

    return model


def categorize_models(models: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """
    Categorize models by provider and type.

    Returns:
        Dict with categories: 'free', 'cheap', 'premium', 'voice', 'by_provider'
    """
    categorized = {
        'free': [],
        'cheap': [],  # < $0.001 per 1K tokens
        'premium': [],  # >= $0.001 per 1K tokens
        'voice': [],  # Phase 60.5: Models with audio/speech capabilities
        'by_provider': {}
    }

    for model in models:
        # Phase 60.5: Classify model type first
        classify_model_type(model)

        pricing = model.get('pricing', {})
        prompt_price = float(pricing.get('prompt', '0') or '0')

        # Phase 60.5: Add to voice category if has audio capabilities
        if model.get('type') == 'voice':
            categorized['voice'].append(model)

        # Categorize by price
        if prompt_price == 0:
            categorized['free'].append(model)
        elif prompt_price < 0.001:
            categorized['cheap'].append(model)
        else:
            categorized['premium'].append(model)

        # Categorize by provider
        model_id = model.get('id', '')
        provider = model_id.split('/')[0] if '/' in model_id else 'unknown'
        if provider not in categorized['by_provider']:
            categorized['by_provider'][provider] = []
        categorized['by_provider'][provider].append(model)

    return categorized


# Quick test
if __name__ == '__main__':
    import asyncio

    async def test():
        models = await get_all_models()
        print(f"Total models: {len(models)}")

        cats = categorize_models(models)
        print(f"Free: {len(cats['free'])}")
        print(f"Cheap: {len(cats['cheap'])}")
        print(f"Premium: {len(cats['premium'])}")
        print(f"Providers: {list(cats['by_provider'].keys())}")

    asyncio.run(test())
