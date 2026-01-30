"""
Phase 60.5: Voice Integration Handler.

STT (Speech-to-Text) + TTS (Text-to-Speech) pipeline with local and cloud support.

@status: active
@phase: 96
@depends: httpx, whisper (optional), piper (optional)
@used_by: voice_socket_handler.py
"""

import base64
import logging
import os
import tempfile
from typing import Optional, Dict, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)


# ============================================
# TTS PROVIDERS
# ============================================

async def tts_elevenlabs(text: str, voice_id: str = "EXAVITQu4vr4xnSDxMaL", api_key: Optional[str] = None) -> bytes:
    """
    ElevenLabs TTS - Premium quality voices

    voice_id examples:
    - EXAVITQu4vr4xnSDxMaL = Bella (female)
    - pNInz6obpgDQGcFmaJgB = Adam (male)
    """
    if not api_key:
        api_key = os.environ.get("ELEVENLABS_API_KEY")

    if not api_key:
        logger.warning("[TTS] No ElevenLabs key, falling back to local")
        return await tts_piper_local(text)

    try:
        import httpx

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}",
                headers={
                    "xi-api-key": api_key,
                    "Content-Type": "application/json"
                },
                json={
                    "text": text,
                    "model_id": "eleven_monolingual_v1",
                    "voice_settings": {
                        "stability": 0.5,
                        "similarity_boost": 0.75
                    }
                },
                timeout=30.0
            )

            if resp.status_code == 200:
                logger.info(f"[TTS] ElevenLabs: {len(text)} chars -> {len(resp.content)} bytes")
                return resp.content
            else:
                logger.error(f"[TTS] ElevenLabs error: {resp.status_code} - {resp.text}")
                return await tts_piper_local(text)

    except Exception as e:
        logger.error(f"[TTS] ElevenLabs error: {e}")
        return await tts_piper_local(text)


async def tts_piper_local(text: str, voice: str = "en_US-amy-medium") -> bytes:
    """
    Piper TTS - Local offline TTS

    Requires piper installed: pip install piper-tts
    or: brew install piper
    """
    try:
        import subprocess

        # Piper CLI: echo "text" | piper --model voice --output_raw
        proc = subprocess.run(
            ["piper", "--model", voice, "--output_raw"],
            input=text.encode('utf-8'),
            capture_output=True,
            timeout=30
        )

        if proc.returncode == 0:
            logger.info(f"[TTS] Piper: {len(text)} chars -> {len(proc.stdout)} bytes")
            return proc.stdout
        else:
            logger.error(f"[TTS] Piper error: {proc.stderr.decode()}")
            return b""

    except FileNotFoundError:
        logger.warning("[TTS] Piper not installed, returning empty audio")
        return b""
    except Exception as e:
        logger.error(f"[TTS] Piper error: {e}")
        return b""


async def tts_browser(text: str) -> Dict[str, Any]:
    """
    Web Speech API - send text for browser to speak
    Returns instruction dict, not audio bytes
    """
    # Detect language
    is_russian = any('\u0400' <= char <= '\u04FF' for char in text)
    lang = "ru-RU" if is_russian else "en-US"

    return {
        "method": "browser",
        "text": text,
        "lang": lang,
        "rate": 0.9,
        "pitch": 1.0
    }


# ============================================
# STT PROVIDERS
# ============================================

async def stt_whisper_local(audio_bytes: bytes, model_size: str = "base") -> str:
    """
    Whisper STT - Local OpenAI Whisper

    Requires: pip install openai-whisper
    model_size: tiny, base, small, medium, large
    """
    try:
        import whisper

        # Save to temp file (whisper needs file path)
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            f.write(audio_bytes)
            temp_path = f.name

        try:
            # Load model (cached after first call)
            model = whisper.load_model(model_size)
            result = model.transcribe(temp_path)
            text = result.get("text", "").strip()

            logger.info(f"[STT] Whisper: {len(audio_bytes)} bytes -> '{text[:50]}...'")
            return text

        finally:
            # Cleanup temp file
            os.unlink(temp_path)

    except ImportError:
        logger.warning("[STT] Whisper not installed, returning empty")
        return ""
    except Exception as e:
        logger.error(f"[STT] Whisper error: {e}")
        return ""


async def stt_deepgram(audio_bytes: bytes, api_key: Optional[str] = None) -> str:
    """
    Deepgram Nova 2 STT - Fast cloud transcription
    """
    if not api_key:
        api_key = os.environ.get("DEEPGRAM_API_KEY")

    if not api_key:
        logger.warning("[STT] No Deepgram key, falling back to Whisper")
        return await stt_whisper_local(audio_bytes)

    try:
        import httpx

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                "https://api.deepgram.com/v1/listen?model=nova-2&smart_format=true",
                headers={
                    "Authorization": f"Token {api_key}",
                    "Content-Type": "audio/wav"
                },
                content=audio_bytes,
                timeout=30.0
            )

            if resp.status_code == 200:
                data = resp.json()
                text = data["results"]["channels"][0]["alternatives"][0]["transcript"]
                logger.info(f"[STT] Deepgram: {len(audio_bytes)} bytes -> '{text[:50]}...'")
                return text
            else:
                logger.error(f"[STT] Deepgram error: {resp.status_code}")
                return await stt_whisper_local(audio_bytes)

    except Exception as e:
        logger.error(f"[STT] Deepgram error: {e}")
        return await stt_whisper_local(audio_bytes)


async def stt_openai_whisper(audio_bytes: bytes, api_key: Optional[str] = None) -> str:
    """
    OpenAI Whisper API - Cloud STT
    """
    if not api_key:
        api_key = os.environ.get("OPENAI_API_KEY")

    if not api_key:
        logger.warning("[STT] No OpenAI key, falling back to local Whisper")
        return await stt_whisper_local(audio_bytes)

    try:
        import httpx

        # Create temp file for upload
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
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
                        timeout=60.0
                    )

                    if resp.status_code == 200:
                        data = resp.json()
                        text = data.get("text", "").strip()
                        logger.info(f"[STT] OpenAI Whisper: {len(audio_bytes)} bytes -> '{text[:50]}...'")
                        return text
                    else:
                        logger.error(f"[STT] OpenAI error: {resp.status_code}")
                        return await stt_whisper_local(audio_bytes)
        finally:
            os.unlink(temp_path)

    except Exception as e:
        logger.error(f"[STT] OpenAI Whisper error: {e}")
        return await stt_whisper_local(audio_bytes)


# ============================================
# VOICE SERVICE CLASS
# ============================================

@dataclass
class VoiceConfig:
    """Voice service configuration"""
    tts_provider: str = "browser"  # browser | elevenlabs | piper
    stt_provider: str = "whisper"  # whisper | deepgram | openai
    tts_voice_id: str = "EXAVITQu4vr4xnSDxMaL"  # ElevenLabs Bella
    whisper_model: str = "base"  # tiny | base | small | medium | large


class VoiceService:
    """
    Unified voice service for VETKA

    Handles TTS (Text-to-Speech) and STT (Speech-to-Text)
    with automatic fallback to local models when cloud keys unavailable
    """

    def __init__(self, config: Optional[VoiceConfig] = None):
        self.config = config or VoiceConfig()
        self._api_keys: Dict[str, str] = {}

        # Load keys from environment
        self._load_env_keys()

    def _load_env_keys(self):
        """Load API keys from environment"""
        key_vars = [
            ("elevenlabs", "ELEVENLABS_API_KEY"),
            ("deepgram", "DEEPGRAM_API_KEY"),
            ("openai", "OPENAI_API_KEY"),
        ]

        for provider, env_var in key_vars:
            key = os.environ.get(env_var)
            if key:
                self._api_keys[provider] = key
                logger.info(f"[Voice] Loaded {provider} API key")

    def set_api_key(self, provider: str, key: str):
        """Set API key for provider"""
        self._api_keys[provider] = key
        logger.info(f"[Voice] Set {provider} API key")

    def get_api_key(self, provider: str) -> Optional[str]:
        """Get API key for provider"""
        return self._api_keys.get(provider)

    async def text_to_speech(
        self,
        text: str,
        provider: Optional[str] = None,
        voice_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Convert text to audio

        Returns:
            For audio providers: {"audio": base64_string, "format": "mp3"|"wav"}
            For browser: {"method": "browser", "text": str, "lang": str}
        """
        provider = provider or self.config.tts_provider

        if provider == "elevenlabs":
            key = self.get_api_key("elevenlabs")
            voice = voice_id or self.config.tts_voice_id
            audio = await tts_elevenlabs(text, voice, key)

            if audio:
                return {
                    "audio": base64.b64encode(audio).decode('utf-8'),
                    "format": "mp3"
                }
            else:
                # Fallback to browser
                return await tts_browser(text)

        elif provider == "piper":
            audio = await tts_piper_local(text)

            if audio:
                return {
                    "audio": base64.b64encode(audio).decode('utf-8'),
                    "format": "wav"
                }
            else:
                return await tts_browser(text)

        else:  # browser (default)
            return await tts_browser(text)

    async def speech_to_text(
        self,
        audio_base64: str,
        provider: Optional[str] = None
    ) -> str:
        """
        Convert audio to text

        Args:
            audio_base64: Base64 encoded audio (WAV/WebM)
            provider: STT provider (whisper|deepgram|openai)

        Returns:
            Transcribed text
        """
        provider = provider or self.config.stt_provider

        # Decode base64 audio
        try:
            audio_bytes = base64.b64decode(audio_base64)
        except Exception as e:
            logger.error(f"[STT] Failed to decode audio: {e}")
            return ""

        if provider == "deepgram":
            key = self.get_api_key("deepgram")
            return await stt_deepgram(audio_bytes, key)

        elif provider == "openai":
            key = self.get_api_key("openai")
            return await stt_openai_whisper(audio_bytes, key)

        else:  # whisper local (default)
            return await stt_whisper_local(audio_bytes, self.config.whisper_model)

    def get_available_providers(self) -> Dict[str, Dict[str, bool]]:
        """Get available TTS/STT providers based on API keys"""
        return {
            "tts": {
                "browser": True,  # Always available
                "elevenlabs": "elevenlabs" in self._api_keys,
                "piper": True,  # Requires local install but no API key
            },
            "stt": {
                "whisper": True,  # Requires local install but no API key
                "deepgram": "deepgram" in self._api_keys,
                "openai": "openai" in self._api_keys,
            }
        }


# ============================================
# SINGLETON
# ============================================

_voice_service: Optional[VoiceService] = None


def get_voice_service() -> VoiceService:
    """Get or create singleton VoiceService"""
    global _voice_service
    if _voice_service is None:
        _voice_service = VoiceService()
    return _voice_service
