# MARKER_102.2_START
"""Voice module configuration settings."""

import os
from pathlib import Path

# Model paths
MODEL_DIR = Path(__file__).parent.parent.parent / "models"
WHISPER_MODEL_PATH = MODEL_DIR / "whisper"
TTS_MODEL_PATH = MODEL_DIR / "tts"

# Audio configuration
AUDIO_CONFIG = {
    "sample_rate": 16000,
    "channels": 1,
    "chunk_size": 1024,
    "format": "wav",
    "max_duration": 30,  # seconds
    "silence_threshold": 0.01,
    "silence_duration": 1.0,  # seconds
}

# Whisper configuration
WHISPER_CONFIG = {
    "model_size": "base",
    "language": "en",
    "task": "transcribe",
    "temperature": 0.0,
    "beam_size": 5,
    "best_of": 5,
    "patience": 1.0,
}

# TTS configuration
TTS_CONFIG = {
    "voice": "default",
    "speed": 1.0,
    "pitch": 1.0,
    "volume": 0.8,
    "output_format": "wav",
}

# Device configuration
DEVICE_CONFIG = {
    "use_gpu": True,
    "gpu_memory_fraction": 0.8,
    "cpu_threads": 4,
}

# File paths
TEMP_DIR = Path("/tmp/voice_assistant")
AUDIO_CACHE_DIR = TEMP_DIR / "audio_cache"
MODEL_CACHE_DIR = TEMP_DIR / "model_cache"

# Ensure directories exist
for directory in [MODEL_DIR, TEMP_DIR, AUDIO_CACHE_DIR, MODEL_CACHE_DIR]:
    directory.mkdir(parents=True, exist_ok=True)
# MARKER_102.2_END