"""
@file chat_utils.py
@status ACTIVE
@phase Phase 37.3
@lastAudit 2026-01-04

Chat utility functions - pure utilities without state dependencies.
Functions that depend on main.py globals (CHAT_HISTORY_DIR, etc.) remain in main.py
and are accessed via lazy imports in handlers.
"""


def detect_response_type(text: str) -> str:
    """
    Determine if response is: text, code, json, markdown
    """
    if text.strip().startswith('{') or text.strip().startswith('['):
        return 'json'
    elif '```' in text or 'def ' in text or 'class ' in text:
        return 'code'
    elif '###' in text or '##' in text or '# ' in text:
        return 'markdown'
    else:
        return 'text'


def get_agent_model_name(agent_instance) -> str:
    """
    Extract model name from agent instance.
    Returns short name like 'qwen2:7b' or 'llama3.1:8b' (not 'ollama/...')
    Works with both old (src/agents) and new (app/src/agents) agent types
    """
    try:
        if not agent_instance:
            return "unknown"

        # Try current_model() method (new app/src/agents agents)
        if hasattr(agent_instance, 'current_model') and callable(agent_instance.current_model):
            try:
                model = agent_instance.current_model()
                if model:
                    return model.replace('ollama/', '')
            except Exception as e:
                print(f"[MODEL] current_model() failed: {e}")

        # Try .model attribute (old src/agents agents)
        if hasattr(agent_instance, 'model'):
            model = agent_instance.model
            if isinstance(model, str) and model:
                return model.replace('ollama/', '')

        # Try get_model() method
        if hasattr(agent_instance, 'get_model') and callable(agent_instance.get_model):
            try:
                model = agent_instance.get_model()
                if model:
                    return model.replace('ollama/', '')
            except Exception as e:
                print(f"[MODEL] get_model() failed: {e}")

        # Try model_pool attribute with index
        if hasattr(agent_instance, 'model_pool') and hasattr(agent_instance, 'model_index'):
            if isinstance(agent_instance.model_pool, list) and agent_instance.model_pool:
                model = agent_instance.model_pool[agent_instance.model_index % len(agent_instance.model_pool)]
                if model:
                    return model.replace('ollama/', '')

    except Exception as e:
        print(f"[MODEL] Error extracting model name: {e}")

    return "unknown"
