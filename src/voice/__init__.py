# MARKER_104.7: Voice module with LLM + Streaming
"""Voice processing module for STT, TTS, LLM and streaming pipeline."""

from .tts_engine import Qwen3TTSClient
from .tts_server_manager import start_tts_server, stop_tts_server, is_tts_running
from .jarvis_llm import JarvisLLM, get_jarvis_llm, jarvis_respond, get_jarvis_context
from .streaming_pipeline import StreamingPipeline, get_streaming_pipeline, streaming_jarvis_respond

__all__ = [
    # TTS
    'Qwen3TTSClient',
    'start_tts_server',
    'stop_tts_server',
    'is_tts_running',
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
