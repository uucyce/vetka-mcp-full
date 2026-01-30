"""
@file model_utils.py
@status ACTIVE
@phase Phase 38.1
@lastAudit 2026-01-05

Model-related utility functions.
Extracted from main.py by markers HELPER_*_PHASE38.1
"""

# Model configuration - economic models for cost control
MODEL_CONFIG = {
    'banned': [
        'anthropic/claude-3.5-sonnet',
        'anthropic/claude-3-opus',
        'openai/gpt-4',
        'openai/gpt-4-turbo',
        'openai/gpt-4-turbo-preview',
        'openai/gpt-4o',
        'google/gemini-pro-1.5',
        'google/gemini-ultra',
    ],
    'cheap': {
        'default': 'deepseek/deepseek-chat',
        'code': 'deepseek/deepseek-coder',
        'fast': 'openai/gpt-4o-mini',
        'summarize': 'deepseek/deepseek-chat',
        'analyze': 'deepseek/deepseek-chat',
    },
    'ollama': {
        'default': 'qwen2:7b',
        'code': 'deepseek-coder:6.7b',
        'fast': 'llama3.1:8b',
    }
}


def get_model_for_task(task_type: str = 'default', tier: str = 'cheap') -> str:
    """
    Get appropriate model for task type and cost tier.
    Returns model string suitable for OpenRouter or Ollama.

    Args:
        task_type: Type of task (default, code, fast, summarize, analyze)
        tier: Cost tier (cheap, ollama, banned)

    Returns:
        Model string for API calls
    """
    tier_config = MODEL_CONFIG.get(tier, MODEL_CONFIG['cheap'])
    return tier_config.get(task_type, tier_config.get('default', 'deepseek/deepseek-chat'))


def is_model_banned(model: str) -> bool:
    """
    Check if model is in banned list (too expensive).

    Args:
        model: Model name to check

    Returns:
        True if model is banned, False otherwise
    """
    return model in MODEL_CONFIG['banned']


def get_model_config() -> dict:
    """
    Get the full MODEL_CONFIG dictionary.

    Returns:
        Complete model configuration dict
    """
    return MODEL_CONFIG.copy()
