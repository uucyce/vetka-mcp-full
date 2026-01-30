"""
Phase 60.5.1: Voice Realtime Providers.

STT, LLM, and TTS providers for realtime voice pipeline.

@status: active
@phase: 96
@depends: unified_key_manager, httpx, whisper
@used_by: voice_router.py, voice_socket_handler.py
"""

import os
import base64
import logging
import tempfile
import struct
from typing import Optional, AsyncGenerator, List

from src.utils.unified_key_manager import get_key_manager

logger = logging.getLogger(__name__)


def _get_api_key(provider: str) -> Optional[str]:
    """Get API key from UnifiedKeyManager"""
    try:
        km = get_key_manager()
        return km.get_key(provider)
    except Exception as e:
        logger.warning(f"[Keys] Failed to get {provider} key: {e}")
        return None


# ============================================
# WAV HEADER HELPER
# ============================================

def create_wav_header(data_size: int, sample_rate: int = 16000, channels: int = 1, bits: int = 16) -> bytes:
    """Create WAV header for raw PCM data"""
    byte_rate = sample_rate * channels * bits // 8
    block_align = channels * bits // 8

    return (
        b'RIFF' +
        struct.pack('<I', 36 + data_size) +
        b'WAVE' +
        b'fmt ' +
        struct.pack('<IHHIIHH', 16, 1, channels, sample_rate, byte_rate, block_align, bits) +
        b'data' +
        struct.pack('<I', data_size)
    )


# ============================================
# STT PROVIDERS
# ============================================

async def stt_whisper_local(audio_bytes: bytes, model_size: str = "base") -> str:
    """
    Local Whisper STT

    Requires: pip install openai-whisper
    """
    try:
        import whisper

        # Save to temp file (whisper needs file path)
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            # Add WAV header
            wav_header = create_wav_header(len(audio_bytes))
            f.write(wav_header)
            f.write(audio_bytes)
            temp_path = f.name

        try:
            # Load model (cached after first call)
            model = whisper.load_model(model_size)
            result = model.transcribe(temp_path, language=None)  # Auto-detect language
            text = result.get("text", "").strip()

            logger.info(f"[STT Whisper] {len(audio_bytes)} bytes -> '{text[:50]}...'")
            return text

        finally:
            os.unlink(temp_path)

    except ImportError:
        logger.warning("[STT] Whisper not installed")
        return ""
    except Exception as e:
        logger.error(f"[STT Whisper] Error: {e}")
        return ""


async def stt_deepgram(audio_bytes: bytes) -> str:
    """
    Deepgram Nova 2 STT - Fast cloud transcription
    NO FALLBACK - returns empty string if fails
    """
    api_key = _get_api_key("deepgram")

    if not api_key:
        logger.warning("[STT Deepgram] No Deepgram key available")
        return ""

    try:
        import httpx

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                "https://api.deepgram.com/v1/listen",
                headers={
                    "Authorization": f"Token {api_key}",
                    "Content-Type": "audio/raw",
                },
                params={
                    "encoding": "linear16",
                    "sample_rate": 16000,
                    "channels": 1,
                    "model": "nova-2",
                    "smart_format": "true",
                },
                content=audio_bytes,
                timeout=15.0,
            )

            if resp.status_code == 200:
                data = resp.json()
                text = data["results"]["channels"][0]["alternatives"][0]["transcript"]
                logger.info(f"[STT Deepgram] {len(audio_bytes)} bytes -> '{text[:50]}...'")
                return text
            else:
                logger.error(f"[STT Deepgram] Error: {resp.status_code}")
                return ""

    except Exception as e:
        logger.error(f"[STT Deepgram] Error: {e}")
        return ""


async def stt_gemini(audio_bytes: bytes) -> str:
    """
    Google Gemini STT via multimodal API
    Uses KeyManager rotation - marks key as rate-limited on 429
    NO RECURSIVE FALLBACK - returns empty string if all keys exhausted
    """
    km = get_key_manager()
    api_key = km.get_key("gemini")

    if not api_key:
        logger.warning("[STT Gemini] No available Gemini key (all rate-limited?)")
        return ""

    try:
        import httpx

        # Create temp WAV file
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            wav_header = create_wav_header(len(audio_bytes))
            f.write(wav_header)
            f.write(audio_bytes)
            temp_path = f.name

        try:
            # Read audio as base64
            with open(temp_path, 'rb') as audio_file:
                audio_base64 = base64.b64encode(audio_file.read()).decode()

            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}",
                    json={
                        "contents": [{
                            "parts": [
                                {
                                    "inline_data": {
                                        "mime_type": "audio/wav",
                                        "data": audio_base64
                                    }
                                },
                                {
                                    "text": "Transcribe this audio exactly. Return only the transcription, no explanations."
                                }
                            ]
                        }]
                    },
                    timeout=30.0,
                )

                if resp.status_code == 200:
                    km.report_success(api_key)
                    data = resp.json()
                    text = data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "").strip()
                    logger.info(f"[STT Gemini] {len(audio_bytes)} bytes -> '{text[:50]}...'")
                    return text
                elif resp.status_code == 429:
                    # Rate limited - mark key for 24h cooldown
                    km.report_failure(api_key, mark_cooldown=True)
                    logger.warning(f"[STT Gemini] Key {api_key[:10]}... rate-limited for 24h")
                    return ""  # Let stt_from_pcm_bytes try next provider
                else:
                    logger.error(f"[STT Gemini] Error: {resp.status_code} - {resp.text[:200]}")
                    return ""
        finally:
            os.unlink(temp_path)

    except Exception as e:
        logger.error(f"[STT Gemini] Error: {e}")
        return ""


async def stt_openai(audio_bytes: bytes) -> str:
    """
    OpenAI Whisper API - Cloud STT
    Uses KeyManager rotation with rate limit tracking
    NO RECURSIVE FALLBACK - returns empty string if all keys exhausted
    """
    km = get_key_manager()
    api_key = km.get_key("openai")

    if not api_key:
        logger.warning("[STT OpenAI] No available OpenAI key")
        return ""

    try:
        import httpx

        # Create temp WAV file
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            wav_header = create_wav_header(len(audio_bytes))
            f.write(wav_header)
            f.write(audio_bytes)
            temp_path = f.name

        try:
            async with httpx.AsyncClient() as client:
                with open(temp_path, 'rb') as audio_file:
                    resp = await client.post(
                        "https://api.openai.com/v1/audio/transcriptions",
                        headers={"Authorization": f"Bearer {api_key}"},
                        files={"file": ("audio.wav", audio_file, "audio/wav")},
                        data={"model": "whisper-1"},
                        timeout=30.0,
                    )

                    if resp.status_code == 200:
                        km.report_success(api_key)
                        data = resp.json()
                        text = data.get("text", "").strip()
                        logger.info(f"[STT OpenAI] {len(audio_bytes)} bytes -> '{text[:50]}...'")
                        return text
                    elif resp.status_code == 429:
                        # Rate limited - mark key for cooldown
                        km.report_failure(api_key, mark_cooldown=True)
                        logger.warning(f"[STT OpenAI] Key {api_key[:15]}... rate-limited for 24h")
                        return ""  # Let stt_from_pcm_bytes try next provider
                    else:
                        logger.error(f"[STT OpenAI] Error: {resp.status_code}")
                        return ""
        finally:
            os.unlink(temp_path)

    except Exception as e:
        logger.error(f"[STT OpenAI] Error: {e}")
        return ""


async def stt_from_pcm_bytes(audio_bytes: bytes, provider: str = "gemini") -> str:
    """
    Main STT entry point - LINEAR fallback chain (NO recursion!)

    Args:
        audio_bytes: Raw PCM audio bytes (Int16 LE, 16kHz, mono)
        provider: Preferred STT provider name

    Fallback chain: preferred -> gemini -> openai -> deepgram -> whisper_local
    Each provider returns "" on failure, we try next in chain.
    """
    # Build provider chain starting with preferred
    providers = []
    if provider == "deepgram":
        providers = ["deepgram", "gemini", "openai", "whisper"]
    elif provider == "openai":
        providers = ["openai", "gemini", "deepgram", "whisper"]
    elif provider == "whisper":
        providers = ["whisper", "gemini", "openai", "deepgram"]
    else:
        providers = ["gemini", "openai", "deepgram", "whisper"]

    # Try each provider in order
    for prov in providers:
        logger.info(f"[STT] Trying provider: {prov}")
        result = ""

        if prov == "gemini":
            result = await stt_gemini(audio_bytes)
        elif prov == "openai":
            result = await stt_openai(audio_bytes)
        elif prov == "deepgram":
            result = await stt_deepgram(audio_bytes)
        elif prov == "whisper":
            result = await stt_whisper_local(audio_bytes)

        if result and result.strip():
            logger.info(f"[STT] Success with {prov}")
            return result
        else:
            logger.warning(f"[STT] {prov} failed, trying next...")

    logger.error("[STT] All providers failed!")
    return ""


# ============================================
# LLM PROVIDERS (Streaming)
# ============================================

async def llm_stream_grok(
    messages: List[dict],
    model: str = "grok-3-mini"
) -> AsyncGenerator[str, None]:
    """
    Stream LLM response via X.AI (Grok) API directly - PRIORITY

    X.AI model names: grok-3, grok-3-mini, grok-4
    """
    api_key = _get_api_key("xai")

    if not api_key:
        logger.debug("[LLM] No X.AI key, will fallback to OpenRouter")
        return

    try:
        import httpx
        import json

        async with httpx.AsyncClient() as client:
            async with client.stream(
                "POST",
                "https://api.x.ai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model,
                    "messages": messages,
                    "stream": True,
                    "max_tokens": 500,
                    "temperature": 0.7,
                },
                timeout=60.0,
            ) as resp:
                if resp.status_code != 200:
                    error_text = await resp.aread()
                    logger.error(f"[LLM Grok] Error: {resp.status_code} - {error_text}")
                    return

                async for line in resp.aiter_lines():
                    if line.startswith("data: "):
                        data = line[6:]
                        if data == "[DONE]":
                            break

                        try:
                            chunk = json.loads(data)
                            delta = chunk.get("choices", [{}])[0].get("delta", {})
                            token = delta.get("content", "")

                            if token:
                                yield token
                        except json.JSONDecodeError:
                            continue

    except Exception as e:
        logger.error(f"[LLM Grok] Error: {e}", exc_info=True)


async def llm_stream_response(
    prompt: str,
    model: str = "grok-3-mini",
    conversation_history: Optional[List[dict]] = None
) -> AsyncGenerator[str, None]:
    """
    Stream LLM response - tries X.AI (Grok) first, then OpenRouter

    Args:
        prompt: User's message
        model: Model name (will be prefixed with provider if needed)
        conversation_history: Previous messages for context
    """
    # Build messages
    messages = [
        {
            "role": "system",
            "content": (
                "You are VETKA's voice assistant. "
                "You speak concisely and naturally. "
                "Keep responses short (1-3 sentences) unless more detail is needed. "
                "You can speak Russian and English fluently."
            )
        }
    ]

    # Add conversation history
    if conversation_history:
        for msg in conversation_history[-10:]:
            messages.append({
                "role": msg.get("role", "user"),
                "content": msg.get("content", "")
            })
    else:
        messages.append({"role": "user", "content": prompt})

    # Try X.AI (Grok) API directly first - PRIORITY
    if "grok" in model.lower():
        grok_model = model if not "/" in model else model.split("/")[-1]
        has_response = False
        async for token in llm_stream_grok(messages, grok_model):
            has_response = True
            yield token
        if has_response:
            return

    # Fallback to OpenRouter
    km = get_key_manager()
    api_key = km.get_openrouter_key()

    if not api_key:
        logger.error("[LLM] No OpenRouter key in KeyManager!")
        yield "Sorry, I couldn't process that."
        return

    # Build model ID for OpenRouter
    model_id = model
    if not "/" in model_id:
        if "grok" in model_id.lower():
            # Map old Grok names to current OpenRouter model IDs
            grok_map = {
                "grok-beta": "x-ai/grok-3-mini-beta",  # grok-beta -> grok-3-mini (fast, free tier)
                "grok-2": "x-ai/grok-3-mini-beta",     # grok-2 retired -> grok-3-mini
                "grok-3": "x-ai/grok-3-mini-beta",     # grok-3 -> grok-3-mini
                "grok-3-mini": "x-ai/grok-3-mini-beta",
                "grok-4": "x-ai/grok-4",
            }
            model_id = grok_map.get(model_id.lower(), "x-ai/grok-3-mini-beta")
        elif "claude" in model_id.lower():
            model_id = f"anthropic/{model_id}"
        elif "gpt" in model_id.lower():
            model_id = f"openai/{model_id}"
        elif "gemini" in model_id.lower():
            model_id = f"google/{model_id}"

    # messages already built above
    try:
        import httpx
        import json

        async with httpx.AsyncClient() as client:
            async with client.stream(
                "POST",
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "https://vetka.app",
                    "X-Title": "VETKA Voice",
                },
                json={
                    "model": model_id,
                    "messages": messages,
                    "stream": True,
                    "max_tokens": 500,
                    "temperature": 0.7,
                },
                timeout=60.0,
            ) as resp:
                if resp.status_code != 200:
                    error_text = await resp.aread()
                    logger.error(f"[LLM] OpenRouter error: {resp.status_code} - {error_text}")
                    yield "Sorry, I couldn't process that."
                    return

                async for line in resp.aiter_lines():
                    if line.startswith("data: "):
                        data = line[6:]
                        if data == "[DONE]":
                            break

                        try:
                            chunk = json.loads(data)
                            delta = chunk.get("choices", [{}])[0].get("delta", {})
                            token = delta.get("content", "")

                            if token:
                                yield token
                        except json.JSONDecodeError:
                            continue

    except Exception as e:
        logger.error(f"[LLM] Error: {e}", exc_info=True)
        yield "Sorry, something went wrong."


# ============================================
# TTS PROVIDERS
# ============================================

async def tts_elevenlabs(text: str, voice_id: str = "EXAVITQu4vr4xnSDxMaL") -> str:
    """
    ElevenLabs TTS - returns base64 MP3

    Voice IDs:
    - EXAVITQu4vr4xnSDxMaL = Bella (female, warm)
    - 21m00Tcm4TlvDq8ikWAM = Rachel (female, calm)
    - TxGEqnHWrfWFTfGW9XjX = Josh (male, deep)
    - pNInz6obpgDQGcFmaJgB = Adam (male, warm)
    """
    api_key = _get_api_key("elevenlabs")

    if not api_key:
        logger.warning("[TTS] No ElevenLabs key in KeyManager")
        return ""

    # Voice name to ID mapping
    voice_map = {
        "bella": "EXAVITQu4vr4xnSDxMaL",
        "rachel": "21m00Tcm4TlvDq8ikWAM",
        "josh": "TxGEqnHWrfWFTfGW9XjX",
        "adam": "pNInz6obpgDQGcFmaJgB",
    }

    # Resolve voice name to ID
    if voice_id.lower() in voice_map:
        voice_id = voice_map[voice_id.lower()]

    try:
        import httpx

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}",
                headers={
                    "xi-api-key": api_key,
                    "Content-Type": "application/json",
                },
                json={
                    "text": text,
                    "model_id": "eleven_turbo_v2_5",  # Fastest model
                    "voice_settings": {
                        "stability": 0.5,
                        "similarity_boost": 0.75,
                    }
                },
                timeout=30.0,
            )

            if resp.status_code == 200:
                audio_base64 = base64.b64encode(resp.content).decode()
                logger.info(f"[TTS ElevenLabs] {len(text)} chars -> {len(resp.content)} bytes")
                return audio_base64
            else:
                logger.error(f"[TTS ElevenLabs] Error: {resp.status_code}")
                return ""

    except Exception as e:
        logger.error(f"[TTS ElevenLabs] Error: {e}")
        return ""


async def tts_piper_local(text: str, voice: str = "en_US-amy-medium") -> str:
    """
    Piper local TTS - returns base64 WAV

    Requires: pip install piper-tts OR brew install piper
    """
    try:
        import subprocess

        proc = subprocess.run(
            ["piper", "--model", voice, "--output_raw"],
            input=text.encode('utf-8'),
            capture_output=True,
            timeout=30
        )

        if proc.returncode == 0:
            audio_base64 = base64.b64encode(proc.stdout).decode()
            logger.info(f"[TTS Piper] {len(text)} chars -> {len(proc.stdout)} bytes")
            return audio_base64
        else:
            logger.error(f"[TTS Piper] Error: {proc.stderr.decode()}")
            return ""

    except FileNotFoundError:
        logger.warning("[TTS] Piper not installed")
        return ""
    except Exception as e:
        logger.error(f"[TTS Piper] Error: {e}")
        return ""


async def tts_sentence_to_base64(text: str, voice: str = "bella") -> str:
    """
    Main TTS entry point - routes to appropriate provider

    Args:
        text: Text to speak
        voice: Voice name/ID
    """
    # Try ElevenLabs first
    result = await tts_elevenlabs(text, voice)
    if result:
        return result

    # Fallback to Piper local
    result = await tts_piper_local(text)
    if result:
        return result

    # No TTS available - frontend will use browser TTS
    logger.warning("[TTS] No TTS provider available, frontend should use browser TTS")
    return ""
