# MARKER_156.VOICE.LAZY_IMPORT_INIT
"""Voice package with lazy exports to avoid heavyweight imports at package load time."""

from importlib import import_module
from typing import Any, Dict, Tuple

_EXPORTS: Dict[str, Tuple[str, str]] = {
    # tts_engine
    "Qwen3TTSClient": (".tts_engine", "Qwen3TTSClient"),
    "FastTTSClient": (".tts_engine", "FastTTSClient"),
    "TTSEngine": (".tts_engine", "TTSEngine"),
    "TTSConfig": (".tts_engine", "TTSConfig"),
    "TTSResult": (".tts_engine", "TTSResult"),
    "TTSError": (".tts_engine", "TTSError"),
    "TTSProvider": (".tts_engine", "TTSProvider"),
    "get_tts_engine": (".tts_engine", "get_tts_engine"),
    "quick_synthesize": (".tts_engine", "quick_synthesize"),
    "get_fast_tts": (".tts_engine", "get_fast_tts"),
    # tts_server_manager
    "start_tts_server": (".tts_server_manager", "start_tts_server"),
    "stop_tts_server": (".tts_server_manager", "stop_tts_server"),
    "is_tts_running": (".tts_server_manager", "is_tts_running"),
    # jarvis_llm
    "JarvisLLM": (".jarvis_llm", "JarvisLLM"),
    "get_jarvis_llm": (".jarvis_llm", "get_jarvis_llm"),
    "jarvis_respond": (".jarvis_llm", "jarvis_respond"),
    "get_jarvis_context": (".jarvis_llm", "get_jarvis_context"),
    # streaming_pipeline
    "StreamingPipeline": (".streaming_pipeline", "StreamingPipeline"),
    "get_streaming_pipeline": (".streaming_pipeline", "get_streaming_pipeline"),
    "streaming_jarvis_respond": (".streaming_pipeline", "streaming_jarvis_respond"),
}

__all__ = list(_EXPORTS.keys())


def __getattr__(name: str) -> Any:
    if name not in _EXPORTS:
        raise AttributeError(f"module 'src.voice' has no attribute '{name}'")
    module_name, attr_name = _EXPORTS[name]
    module = import_module(module_name, __name__)
    value = getattr(module, attr_name)
    globals()[name] = value
    return value
