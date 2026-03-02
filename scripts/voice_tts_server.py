#!/usr/bin/env python3
"""
MLX Qwen3-TTS FastAPI Microservice
MARKER_104.1

FastAPI server providing text-to-speech using MLX-optimized Qwen3-TTS model.
Runs on port 5002 with custom voice generation capabilities.
"""

import base64
import io
import os
import time
from typing import Optional

import numpy as np
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import uvicorn
from src.voice.audio_postprocess import apply_prosody_to_audio, float_audio_to_wav_bytes

# MLX audio imports
try:
    from mlx_audio.tts import load_model
except ImportError:
    print("ERROR: mlx_audio not installed. Install with: pip install mlx-audio")
    raise


# Request/Response models
class TTSRequest(BaseModel):
    text: str
    language: str = "English"
    speaker: str = "ryan"
    speed: Optional[float] = None
    pitch: Optional[int] = None
    energy: Optional[float] = None
    pause_profile: Optional[str] = None


class TTSResponse(BaseModel):
    audio: str  # base64 encoded
    format: str = "wav"
    sample_rate: int = 24000
    duration: float


# Global model instance
model = None
_MODEL_PROFILES = {
    "4bit": "mlx-community/Qwen3-TTS-12Hz-0.6B-CustomVoice-4bit",
    "5bit": "mlx-community/Qwen3-TTS-12Hz-0.6B-CustomVoice-5bit",
    "6bit": "mlx-community/Qwen3-TTS-12Hz-0.6B-CustomVoice-6bit",
    "8bit": "mlx-community/Qwen3-TTS-12Hz-0.6B-CustomVoice-8bit",
}


def _resolve_model_config() -> tuple[str, str]:
    """
    MARKER_156.VOICE.S6_QWEN_PROFILE_SWITCH:
    Select active model by profile with optional direct override.
    """
    explicit_model = os.getenv("QWEN_TTS_MODEL", "").strip()
    if explicit_model:
        return "custom", explicit_model

    profile = os.getenv("QWEN_TTS_PROFILE", "4bit").strip().lower()
    if profile not in _MODEL_PROFILES:
        print(f"[TTS] Unknown QWEN_TTS_PROFILE={profile!r}, fallback to 4bit")
        profile = "4bit"
    return profile, _MODEL_PROFILES[profile]


MODEL_PROFILE, MODEL_NAME = _resolve_model_config()

# FastAPI app
app = FastAPI(
    title="MLX Qwen3-TTS Server",
    description="Text-to-speech microservice using MLX-optimized Qwen3-TTS",
    version="1.0.0"
)


@app.on_event("startup")
async def load_tts_model():
    """Load MLX TTS model on server startup."""
    global model
    print(f"Loading MLX TTS model: {MODEL_NAME}")
    start_time = time.time()

    try:
        model = load_model(MODEL_NAME)
        load_time = time.time() - start_time
        print(f"✓ Model loaded successfully in {load_time:.2f}s")
    except Exception as e:
        print(f"✗ Failed to load model: {e}")
        raise


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy" if model is not None else "unhealthy",
        "profile": MODEL_PROFILE,
        "model": MODEL_NAME,
        "model_loaded": model is not None,
        "available_profiles": sorted(_MODEL_PROFILES.keys()),
    }


@app.post("/tts/generate", response_model=TTSResponse)
async def generate_speech(request: TTSRequest):
    """
    Generate speech from text using MLX Qwen3-TTS.

    Args:
        request: TTSRequest with text, language, and speaker

    Returns:
        TTSResponse with base64-encoded audio and metadata
    """
    if model is None:
        raise HTTPException(status_code=503, detail="Model not loaded")

    if not request.text.strip():
        raise HTTPException(status_code=400, detail="Text cannot be empty")

    try:
        start_time = time.time()

        # Generate audio using custom voice
        # model.generate_custom_voice returns a generator yielding chunks
        audio_generator = model.generate_custom_voice(
            text=request.text,
            language=request.language,
            speaker=request.speaker
        )

        # Collect all audio chunks
        audio_chunks = []
        for chunk in audio_generator:
            # Convert MLX array to numpy
            audio_array = np.array(chunk.audio.tolist(), dtype=np.float32)
            audio_chunks.append(audio_array)

        if not audio_chunks:
            raise HTTPException(status_code=500, detail="No audio generated")

        # Concatenate all chunks
        full_audio = np.concatenate(audio_chunks)

        # S6.4.1: Apply local prosody controls (speed/pitch/energy/pause) post generation.
        processed_audio = apply_prosody_to_audio(
            full_audio,
            sample_rate=24000,
            speed=request.speed,
            pitch=request.pitch,
            energy=request.energy,
            pause_profile=request.pause_profile,
        )

        # Calculate duration in seconds
        sample_rate = 24000
        duration = len(processed_audio) / sample_rate

        # Convert to real WAV bytes and encode as base64.
        audio_bytes = float_audio_to_wav_bytes(processed_audio, sample_rate=sample_rate)
        audio_base64 = base64.b64encode(audio_bytes).decode("utf-8")

        generation_time = time.time() - start_time
        print(f"Generated {duration:.2f}s audio in {generation_time:.2f}s (RTF: {generation_time/duration:.2f}x)")

        return TTSResponse(
            audio=audio_base64,
            format="wav",
            sample_rate=sample_rate,
            duration=duration
        )

    except Exception as e:
        print(f"Error generating speech: {e}")
        raise HTTPException(status_code=500, detail=f"Speech generation failed: {str(e)}")


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "service": "MLX Qwen3-TTS Server",
        "version": "1.0.0",
        "profile": MODEL_PROFILE,
        "model": MODEL_NAME,
        "endpoints": {
            "health": "GET /health",
            "generate": "POST /tts/generate",
            "docs": "GET /docs"
        }
    }


if __name__ == "__main__":
    import sys
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 5003
    print(f"Starting MLX Qwen3-TTS Server on port {port}...")
    print(f"Profile: {MODEL_PROFILE}")
    print(f"Model: {MODEL_NAME}")
    print("Endpoints:")
    print(f"  - POST http://localhost:{port}/tts/generate")
    print(f"  - GET  http://localhost:{port}/health")
    print(f"  - GET  http://localhost:{port}/docs")

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        log_level="info"
    )
