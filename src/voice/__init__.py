# MARKER_105: Voice module with LLM + Streaming + TTS Fallback
"""Voice processing module for STT, TTS, LLM and streaming pipeline."""

from .tts_engine import (
    Qwen3TTSClient,
    FastTTSClient,
    # Phase 105: TTS Fallback Chain
    TTSEngine,
    TTSConfig,
    TTSResult,
    TTSError,
    TTSProvider,
    get_tts_engine,
    quick_synthesize,
    get_fast_tts,
)
from .tts_server_manager import start_tts_server, stop_tts_server, is_tts_running
from .jarvis_llm import JarvisLLM, get_jarvis_llm, jarvis_respond, get_jarvis_context
from .streaming_pipeline import StreamingPipeline, get_streaming_pipeline, streaming_jarvis_respond

__all__ = [
    # TTS (Phase 102.5-104.7)
    'Qwen3TTSClient',
    'FastTTSClient',
    'start_tts_server',
    'stop_tts_server',
    'is_tts_running',
    'get_fast_tts',
    # TTS Fallback Chain (Phase 105)
    'TTSEngine',
    'TTSConfig',
    'TTSResult',
    'TTSError',
    'TTSProvider',
    'get_tts_engine',
    'quick_synthesize',
    # LLM (Phase 104.6)
    'JarvisLLM',
    'get_jarvis_llm',
    'jarvis_respond',
    'get_jarvis_context',
    # Streaming Pipeline (Phase 104.7)
    'StreamingPipeline',
    'get_streaming_pipeline',
    'streaming_jarvis_respond',
]
