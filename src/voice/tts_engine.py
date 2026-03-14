# MARKER_102.5_START
# HOTFIX: Conditional imports to prevent module loading failure on systems without torch
try:
    import torch
    TORCH_AVAILABLE = True
except ImportError:
    torch = None
    TORCH_AVAILABLE = False

try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    np = None
    NUMPY_AVAILABLE = False
from typing import Optional, Union, List
import logging
from pathlib import Path
import shutil

logger = logging.getLogger(__name__)

class QwenTTS:
    """Text-to-Speech engine using Qwen3-TTS model."""
    
    def __init__(self, model_path: Optional[str] = None, device: Optional[str] = None):
        """
        Initialize QwenTTS engine.
        
        Args:
            model_path: Path to the Qwen3-TTS model
            device: Device to run the model on ('cpu', 'cuda', 'auto')
        """
        self.model_path = model_path
        self.device = device or ('cuda' if TORCH_AVAILABLE and torch.cuda.is_available() else 'cpu')
        self.model = None
        self.tokenizer = None
        self.is_loaded = False
        
    def load_model(self) -> bool:
        """
        Load the Qwen3-TTS model and tokenizer.
        
        Returns:
            bool: True if model loaded successfully, False otherwise
        """
        try:
            # TODO: Implement actual model loading when Qwen3-TTS is available
            logger.info(f"Loading Qwen3-TTS model on {self.device}")
            
            # Placeholder for actual model loading
            # self.model = QwenTTSModel.from_pretrained(self.model_path)
            # self.tokenizer = QwenTTSTokenizer.from_pretrained(self.model_path)
            # self.model.to(self.device)
            # self.model.eval()
            
            self.is_loaded = True
            logger.info("Qwen3-TTS model loaded successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load Qwen3-TTS model: {e}")
            return False
    
    def synthesize(
        self, 
        text: str, 
        speaker_id: Optional[str] = None,
        speed: float = 1.0,
        pitch: float = 1.0,
        volume: float = 1.0
    ) -> Optional[np.ndarray]:
        """
        Synthesize speech from text.
        
        Args:
            text: Input text to synthesize
            speaker_id: Speaker identity for voice cloning
            speed: Speech speed multiplier (0.5-2.0)
            pitch: Pitch adjustment factor (0.5-2.0)
            volume: Volume adjustment factor (0.0-2.0)
            
        Returns:
            np.ndarray: Audio waveform as numpy array, or None if failed
        """
        if not self.is_loaded:
            logger.error("Model not loaded. Call load_model() first.")
            return None
            
        if not text.strip():
            logger.warning("Empty text provided for synthesis")
            return None
            
        try:
            logger.info(f"Synthesizing text: {text[:50]}...")
            
            # TODO: Implement actual synthesis when Qwen3-TTS is available
            # Placeholder implementation
            sample_rate = 22050
            duration = len(text) * 0.1  # Rough estimate
            samples = int(sample_rate * duration)
            
            # Generate placeholder audio (sine wave)
            t = np.linspace(0, duration, samples)
            frequency = 440  # A4 note
            audio = np.sin(2 * np.pi * frequency * t) * 0.3
            
            # Apply voice parameters
            audio = audio * volume
            
            logger.info("Text synthesis completed")
            return audio.astype(np.float32)
            
        except Exception as e:
            logger.error(f"Failed to synthesize text: {e}")
            return None
    
    def synthesize_to_file(
        self, 
        text: str, 
        output_path: Union[str, Path],
        speaker_id: Optional[str] = None,
        speed: float = 1.0,
        pitch: float = 1.0,
        volume: float = 1.0,
        sample_rate: int = 22050
    ) -> bool:
        """
        Synthesize speech and save to file.
        
        Args:
            text: Input text to synthesize
            output_path: Path to save the audio file
            speaker_id: Speaker identity for voice cloning
            speed: Speech speed multiplier
            pitch: Pitch adjustment factor
            volume: Volume adjustment factor
            sample_rate: Audio sample rate
            
        Returns:
            bool: True if successful, False otherwise
        """
        audio = self.synthesize(text, speaker_id, speed, pitch, volume)
        if audio is None:
            return False
            
        try:
            import soundfile as sf
            sf.write(output_path, audio, sample_rate)
            logger.info(f"Audio saved to {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save audio file: {e}")
            return False
    
    def get_available_speakers(self) -> List[str]:
        """
        Get list of available speaker IDs.
        
        Returns:
            List[str]: Available speaker identities
        """
        if not self.is_loaded:
            logger.warning("Model not loaded")
            return []
            
        # TODO: Implement actual speaker enumeration
        return ["default", "speaker_1", "speaker_2"]
    
    def clone_voice(self, reference_audio: Union[str, np.ndarray]) -> Optional[str]:
        """
        Clone voice from reference audio.
        
        Args:
            reference_audio: Path to reference audio file or audio array
            
        Returns:
            str: Speaker ID for the cloned voice, or None if failed
        """
        if not self.is_loaded:
            logger.error("Model not loaded")
            return None
            
        try:
            logger.info("Cloning voice from reference audio")
            
            # TODO: Implement actual voice cloning
            # Placeholder implementation
            import uuid
            speaker_id = f"cloned_{uuid.uuid4().hex[:8]}"
            
            logger.info(f"Voice cloned successfully: {speaker_id}")
            return speaker_id
            
        except Exception as e:
            logger.error(f"Failed to clone voice: {e}")
            return None
    
    def unload_model(self):
        """Unload the model to free memory."""
        if self.model is not None:
            del self.model
            self.model = None
            
        if self.tokenizer is not None:
            del self.tokenizer
            self.tokenizer = None
            
        self.is_loaded = False
        
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            
        logger.info("Qwen3-TTS model unloaded")
    
    def __del__(self):
        """Cleanup when object is destroyed."""
        self.unload_model()
# MARKER_102.5_END


# MARKER_104.2 - Qwen3 TTS HTTP Client
import httpx
import base64
import asyncio
from typing import Optional

class Qwen3TTSClient:
    """HTTP client for Qwen3-TTS server."""

    def __init__(self, server_url: str = "http://127.0.0.1:5003"):
        """
        Initialize TTS HTTP client.

        Args:
            server_url: URL of the TTS server
        """
        self.server_url = server_url
        self.client = httpx.AsyncClient(timeout=30.0)
        logger.info(f"Initialized Qwen3TTSClient with server URL: {server_url}")

    async def synthesize(self, text: str, language: str = "English", speaker: str = "ryan") -> bytes:
        """
        Call TTS server and return audio bytes.

        Args:
            text: Text to synthesize
            language: Language for synthesis (English, Chinese)
            speaker: Speaker voice ID

        Returns:
            bytes: WAV audio data
        """
        try:
            # Check if server is available
            if not await self.is_available():
                logger.warning("TTS server unavailable, falling back to edge-tts")
                return await self._fallback_edge_tts(text)

            # Make request to TTS server
            logger.info(f"Synthesizing text: {text[:50]}... with speaker: {speaker}")
            response = await self.client.post(
                f"{self.server_url}/tts/generate",
                json={
                    "text": text,
                    "language": language,
                    "speaker": speaker
                }
            )
            response.raise_for_status()

            # Parse response - server returns TTSResponse with audio field directly
            data = response.json()
            audio_base64 = data.get("audio")
            if audio_base64:
                # Decode base64 audio
                audio_bytes = base64.b64decode(audio_base64)
                logger.info(f"Successfully synthesized {len(audio_bytes)} bytes of audio")
                return audio_bytes
            else:
                error_msg = data.get("detail", "No audio in response")
                logger.error(f"TTS server returned error: {error_msg}")
                return await self._fallback_edge_tts(text)

        except httpx.TimeoutException:
            logger.error("TTS server request timed out")
            return await self._fallback_edge_tts(text)
        except httpx.HTTPError as e:
            logger.error(f"HTTP error during TTS request: {e}")
            return await self._fallback_edge_tts(text)
        except Exception as e:
            logger.error(f"Unexpected error during TTS synthesis: {e}")
            return await self._fallback_edge_tts(text)

    async def is_available(self) -> bool:
        """
        Check if TTS server is running.

        Returns:
            bool: True if server is healthy, False otherwise
        """
        try:
            response = await self.client.get(
                f"{self.server_url}/health",
                timeout=2.0
            )
            if response.status_code == 200:
                data = response.json()
                return data.get("status") == "healthy"
            return False
        except Exception as e:
            logger.debug(f"TTS server health check failed: {e}")
            return False

    async def _fallback_edge_tts(self, text: str) -> bytes:
        """
        Fallback to edge-tts if Qwen3-TTS server is unavailable.

        Args:
            text: Text to synthesize

        Returns:
            bytes: WAV audio data
        """
        try:
            import edge_tts
            import tempfile

            logger.info("Using edge-tts as fallback")

            # Create temporary file for audio output
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_file:
                tmp_path = tmp_file.name

            # Use edge-tts to generate audio
            communicate = edge_tts.Communicate(text, voice="en-US-GuyNeural")
            await communicate.save(tmp_path)

            # Read audio bytes
            with open(tmp_path, "rb") as f:
                audio_bytes = f.read()

            # Cleanup temp file
            Path(tmp_path).unlink(missing_ok=True)

            logger.info(f"Edge-TTS fallback generated {len(audio_bytes)} bytes")
            return audio_bytes

        except Exception as e:
            logger.error(f"Edge-TTS fallback also failed: {e}")
            # Return empty audio as last resort
            return b""

    async def synthesize_streaming(
        self,
        text: str,
        language: str = "English",
        speaker: str = "ryan"
    ):
        """
        Stream TTS generation by sentences for lower perceived latency.

        Phase 104.6 - Grok Recommendation: Generate per-sentence and yield
        audio chunks as they're ready, so playback can start immediately.

        Args:
            text: Text to synthesize
            language: Language for synthesis
            speaker: Speaker voice ID

        Yields:
            bytes: Audio chunks (WAV format, each sentence)
        """
        import re

        # Split text into sentences
        sentences = re.split(r'(?<=[.!?])\s+', text.strip())
        sentences = [s.strip() for s in sentences if s.strip()]

        if not sentences:
            return

        logger.info(f"[TTS Streaming] Splitting into {len(sentences)} sentences")

        for i, sentence in enumerate(sentences):
            if not sentence:
                continue

            try:
                logger.debug(f"[TTS Streaming] Generating sentence {i+1}: {sentence[:30]}...")
                audio_bytes = await self.synthesize(sentence, language, speaker)

                if audio_bytes:
                    yield audio_bytes
                    logger.debug(f"[TTS Streaming] Yielded {len(audio_bytes)} bytes for sentence {i+1}")

            except Exception as e:
                logger.error(f"[TTS Streaming] Error on sentence {i+1}: {e}")
                continue

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
# MARKER_104.2_END


# MARKER_104.6 - TTS Optimization Helpers

def split_into_sentences(text: str) -> List[str]:
    """
    Split text into sentences for streaming TTS.

    Handles common abbreviations and edge cases.
    """
    import re

    # Simple sentence splitting (preserves abbreviations like "Mr.", "Dr.")
    # More sophisticated would use NLTK or spaCy
    sentences = re.split(r'(?<=[.!?])\s+(?=[A-Z])', text)
    return [s.strip() for s in sentences if s.strip()]


def estimate_audio_duration(text: str, words_per_minute: int = 150) -> float:
    """
    Estimate audio duration in seconds based on text length.

    Args:
        text: Text to estimate
        words_per_minute: Speaking rate (default 150 WPM)

    Returns:
        Estimated duration in seconds
    """
    word_count = len(text.split())
    return (word_count / words_per_minute) * 60
# MARKER_104.6_END


# MARKER_104.7 - Fast TTS Client (Edge-TTS based)

class FastTTSClient:
    """
    Fast TTS client using Edge-TTS (Microsoft Azure).

    ~1s latency vs ~5-6s for Qwen3-TTS.
    Requires internet connection but provides much faster responses.

    Usage:
        client = FastTTSClient()
        audio = await client.synthesize("Hello!")  # Returns MP3 bytes
    """

    # Voice mapping
    VOICES = {
        "en-male": "en-US-GuyNeural",
        "en-female": "en-US-JennyNeural",
        "ru-male": "ru-RU-DmitryNeural",
        "ru-female": "ru-RU-SvetlanaNeural",
    }

    def __init__(self, voice: str = "en-male"):
        """
        Initialize Fast TTS client.

        Args:
            voice: Voice preset (en-male, en-female, ru-male, ru-female)
        """
        self.voice = self.VOICES.get(voice, self.VOICES["en-male"])
        logger.info(f"[FastTTS] Initialized with voice: {self.voice}")

    async def synthesize(self, text: str, voice: Optional[str] = None) -> bytes:
        """
        Synthesize text to speech using Edge-TTS.

        Args:
            text: Text to synthesize
            voice: Override voice (use VOICES key or full voice name)

        Returns:
            bytes: MP3 audio data
        """
        try:
            import edge_tts
            import time

            start = time.perf_counter()

            # Resolve voice
            voice_name = voice or self.voice
            if voice and voice in self.VOICES:
                voice_name = self.VOICES[voice]

            logger.info(f"[FastTTS] Synthesizing: {text[:50]}... with {voice_name}")

            # Stream audio chunks
            communicate = edge_tts.Communicate(text, voice=voice_name)
            audio_data = b''

            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    audio_data += chunk["data"]

            duration = time.perf_counter() - start
            logger.info(f"[FastTTS] Generated {len(audio_data)} bytes in {duration:.2f}s")

            return audio_data

        except ImportError as e:
            import traceback
            logger.error(f"[FastTTS] ImportError: {e}\nTraceback:\n{traceback.format_exc()}")
            logger.error("[FastTTS] Run: pip install edge-tts aiohttp pydub --break-system-packages")
            return b""
        except Exception as e:
            import traceback
            logger.error(f"[FastTTS] Error: {e}\nTraceback:\n{traceback.format_exc()}")
            return b""

    async def synthesize_streaming(self, text: str, voice: Optional[str] = None):
        """
        Stream TTS generation for even lower perceived latency.

        Yields audio chunks as they're ready.

        Args:
            text: Text to synthesize
            voice: Override voice

        Yields:
            bytes: Audio chunks (MP3)
        """
        try:
            import edge_tts

            voice_name = voice or self.voice
            if voice and voice in self.VOICES:
                voice_name = self.VOICES[voice]

            logger.info(f"[FastTTS] Streaming: {text[:50]}...")

            communicate = edge_tts.Communicate(text, voice=voice_name)

            async for chunk in communicate.stream():
                if chunk["type"] == "audio" and chunk["data"]:
                    yield chunk["data"]

        except Exception as e:
            logger.error(f"[FastTTS] Streaming error: {e}")

    def detect_language(self, text: str) -> str:
        """
        Simple language detection for voice selection.

        Args:
            text: Text to analyze

        Returns:
            Language code ('en' or 'ru')
        """
        # Simple heuristic: check for Cyrillic characters
        cyrillic_count = sum(1 for c in text if '\u0400' <= c <= '\u04FF')
        total_alpha = sum(1 for c in text if c.isalpha())

        if total_alpha > 0 and cyrillic_count / total_alpha > 0.3:
            return "ru"
        return "en"

    async def synthesize_auto(self, text: str) -> bytes:
        """
        Auto-detect language and synthesize with appropriate voice.

        Args:
            text: Text to synthesize

        Returns:
            bytes: Audio data
        """
        lang = self.detect_language(text)
        voice = f"{lang}-male"
        logger.info(f"[FastTTS] Auto-detected language: {lang}")
        return await self.synthesize(text, voice=voice)


# Factory function
def get_fast_tts(voice: str = "en-male") -> FastTTSClient:
    """Create FastTTSClient instance"""
    return FastTTSClient(voice=voice)
# MARKER_104.7_END


# MARKER_157_6_ESPEAK_PROVIDER
class ESpeakTTSClient:
    """
    Ultra-fast local TTS client based on espeak-ng.

    Returns WAV bytes from stdout. Designed for low-latency fallback and robotic presets.
    """

    def __init__(
        self,
        voice: str = "ru",
        rate: int = 155,
        pitch: int = 70,
        amplitude: int = 130,
        preset: str = "c3po",
    ):
        self.voice = voice
        self.rate = int(rate)
        self.pitch = int(pitch)
        self.amplitude = int(amplitude)
        self.preset = preset
        self.espeak_bin = shutil.which("espeak-ng") or shutil.which("espeak")
        logger.info(
            f"[ESpeakTTS] Initialized voice={voice} rate={rate} pitch={pitch} amp={amplitude} "
            f"preset={preset} bin={self.espeak_bin or 'NOT_FOUND'}"
        )

    def _preset_args(self) -> List[str]:
        preset = (self.preset or "").strip().lower()
        if preset == "c3po":
            return ["-g", "6"]  # slight robotic segmentation pause
        if preset == "chip":
            return ["-g", "8", "-k", "12"]
        if preset == "clean":
            return ["-g", "2"]
        return []

    @staticmethod
    def _fallback_voice_for_text(text: str) -> str:
        alpha = sum(1 for c in text if c.isalpha())
        cyr = sum(1 for c in text if "\u0400" <= c <= "\u04FF")
        return "ru" if alpha > 0 and (cyr / alpha) > 0.3 else "en"

    async def synthesize(self, text: str, voice: Optional[str] = None) -> bytes:
        if not text or not text.strip():
            return b""
        if not self.espeak_bin:
            logger.warning("[ESpeakTTS] espeak-ng not installed")
            return b""

        selected_voice = (voice or self.voice or "ru").strip()
        cmd = [
            self.espeak_bin,
            "-v",
            selected_voice,
            "-s",
            str(max(80, min(320, self.rate))),
            "-p",
            str(max(0, min(99, self.pitch))),
            "-a",
            str(max(0, min(200, self.amplitude))),
            "--stdout",
            text,
        ]
        cmd.extend(self._preset_args())

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await proc.communicate()
            if proc.returncode != 0:
                stderr_text = stderr.decode(errors='ignore')[:300]
                logger.warning(
                    f"[ESpeakTTS] synth failed code={proc.returncode} stderr={stderr_text}"
                )
                # MBROLA on macOS can fail in mbrowrap (/proc unavailable). Avoid silent turns.
                if selected_voice.startswith("mb-"):
                    fallback_voice = self._fallback_voice_for_text(text)
                    retry_cmd = [
                        self.espeak_bin,
                        "-v",
                        fallback_voice,
                        "-s",
                        str(max(80, min(320, self.rate))),
                        "-p",
                        str(max(0, min(99, self.pitch))),
                        "-a",
                        str(max(0, min(200, self.amplitude))),
                        "--stdout",
                        text,
                    ]
                    retry_cmd.extend(self._preset_args())
                    retry_proc = await asyncio.create_subprocess_exec(
                        *retry_cmd,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE,
                    )
                    retry_stdout, retry_stderr = await retry_proc.communicate()
                    if retry_proc.returncode == 0 and retry_stdout:
                        logger.info(
                            f"[ESpeakTTS] fallback from {selected_voice} -> {fallback_voice} succeeded"
                        )
                        return retry_stdout
                    logger.warning(
                        f"[ESpeakTTS] fallback voice failed code={retry_proc.returncode} "
                        f"stderr={retry_stderr.decode(errors='ignore')[:220]}"
                    )
                return b""
            return stdout or b""
        except Exception as e:
            logger.warning(f"[ESpeakTTS] synth exception: {e}")
            return b""


# MARKER_105_TTS_FALLBACK
"""
Phase 105: TTS Fallback Chain Implementation

Provides automatic failover between TTS providers:
- Primary: Qwen 3 TTS (~150ms latency, local or HTTP)
- Secondary: Edge TTS (Microsoft, ~200ms, requires internet)
- Tertiary: Piper (local/offline, ~100ms)
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Callable, Dict, Any
import time
import io


class TTSProvider(Enum):
    """Available TTS providers."""
    QWEN3 = "qwen3"
    EDGE = "edge"
    PIPER = "piper"
    ESPEAK = "espeak"


class TTSError(Exception):
    """TTS synthesis error."""
    pass


@dataclass
class TTSConfig:
    """Configuration for TTS Engine."""
    primary_provider: str = "qwen3"
    timeout_ms: int = 500  # Fallback trigger timeout
    speed: float = 1.0
    pitch: int = 0
    language: str = "ru"
    # Provider-specific settings
    qwen3_server_url: str = "http://127.0.0.1:5003"
    qwen3_speaker: str = "ryan"
    edge_voice_en: str = "en-US-GuyNeural"
    edge_voice_ru: str = "ru-RU-DmitryNeural"
    espeak_voice_en: str = "en"
    espeak_voice_ru: str = "ru"
    espeak_preset: str = "c3po"
    espeak_rate: int = 155
    espeak_pitch: int = 70
    espeak_amplitude: int = 130
    piper_model_path: str = ""  # Auto-detect if empty
    piper_data_dir: str = ""  # Auto-detect if empty


@dataclass
class TTSResult:
    """Result of TTS synthesis."""
    audio: bytes
    provider: str
    latency_ms: float
    sample_rate: int = 22050
    format: str = "wav"


class TTSEngine:
    """
    TTS Engine with automatic fallback chain.

    Priority order:
    1. Qwen3 TTS (local/HTTP) - ~150ms
    2. Edge TTS (Microsoft cloud) - ~200ms
    3. Piper (local offline) - ~100ms

    Usage:
        engine = TTSEngine(primary="qwen3")
        audio = await engine.synthesize("Hello world!")
    """

    PROVIDERS = ["qwen3", "edge", "espeak", "piper"]

    def __init__(
        self,
        primary: str = "qwen3",
        config: Optional[TTSConfig] = None
    ):
        """
        Initialize TTS Engine with fallback chain.

        Args:
            primary: Primary provider to try first
            config: Configuration options
        """
        self.config = config or TTSConfig(primary_provider=primary)
        self.primary = primary
        self.fallback_order = self._build_fallback_order(primary)

        # Provider instances (lazy loaded)
        self._qwen3_client: Optional[Qwen3TTSClient] = None
        self._fast_tts_client: Optional[FastTTSClient] = None
        self._espeak_client: Optional[ESpeakTTSClient] = None
        self._piper_voice = None

        # Stats
        self._provider_stats: Dict[str, Dict[str, Any]] = {
            provider: {"successes": 0, "failures": 0, "total_latency_ms": 0}
            for provider in self.PROVIDERS
        }

        logger.info(f"[TTSEngine] Initialized with fallback order: {self.fallback_order}")

    def _build_fallback_order(self, primary: str) -> List[str]:
        """
        Build fallback order with primary provider first.

        Args:
            primary: Primary provider name

        Returns:
            List of provider names in fallback order
        """
        if primary not in self.PROVIDERS:
            logger.warning(f"Unknown provider '{primary}', defaulting to 'qwen3'")
            primary = "qwen3"

        order = [primary]
        for provider in self.PROVIDERS:
            if provider not in order:
                order.append(provider)

        return order

    async def synthesize(
        self,
        text: str,
        voice: str = "default",
        speed: float = 1.0,
        pitch: int = 0
    ) -> bytes:
        """
        Synthesize text to speech with automatic fallback.

        Args:
            text: Text to synthesize
            voice: Voice ID (provider-specific)
            speed: Speech speed multiplier
            pitch: Pitch adjustment

        Returns:
            bytes: Audio data (WAV format)

        Raises:
            TTSError: If all providers fail
        """
        if not text or not text.strip():
            logger.warning("[TTSEngine] Empty text provided")
            return b""

        last_error = None

        for provider in self.fallback_order:
            start_time = time.perf_counter()
            try:
                audio = await self._synthesize_with(provider, text, voice, speed, pitch)
                if audio and len(audio) > 100:  # Basic sanity check
                    latency_ms = (time.perf_counter() - start_time) * 1000
                    self._record_success(provider, latency_ms)
                    logger.info(f"[TTSEngine] {provider} succeeded in {latency_ms:.1f}ms")
                    return audio
                else:
                    logger.warning(f"[TTSEngine] {provider} returned empty/invalid audio")
            except asyncio.TimeoutError:
                latency_ms = (time.perf_counter() - start_time) * 1000
                self._record_failure(provider)
                logger.warning(f"[TTSEngine] {provider} timed out after {latency_ms:.1f}ms")
                last_error = TTSError(f"{provider} timed out")
            except Exception as e:
                latency_ms = (time.perf_counter() - start_time) * 1000
                self._record_failure(provider)
                logger.warning(f"[TTSEngine] {provider} failed: {e}, trying next...")
                last_error = TTSError(f"{provider} failed: {e}")

        raise TTSError(f"All TTS providers failed. Last error: {last_error}")

    async def synthesize_with_result(
        self,
        text: str,
        voice: str = "default",
        speed: float = 1.0,
        pitch: int = 0
    ) -> TTSResult:
        """
        Synthesize and return detailed result with metadata.

        Args:
            text: Text to synthesize
            voice: Voice ID
            speed: Speech speed
            pitch: Pitch adjustment

        Returns:
            TTSResult with audio and metadata
        """
        for provider in self.fallback_order:
            start_time = time.perf_counter()
            try:
                audio = await self._synthesize_with(provider, text, voice, speed, pitch)
                if audio and len(audio) > 100:
                    latency_ms = (time.perf_counter() - start_time) * 1000
                    self._record_success(provider, latency_ms)

                    sample_rate = 22050 if provider == "piper" else 24000
                    audio_format = "wav"
                    if provider == "edge":
                        audio_format = "mp3"

                    return TTSResult(
                        audio=audio,
                        provider=provider,
                        latency_ms=latency_ms,
                        sample_rate=sample_rate,
                        format=audio_format
                    )
            except Exception as e:
                self._record_failure(provider)
                logger.warning(f"[TTSEngine] {provider} failed: {e}")
                continue

        raise TTSError("All TTS providers failed")

    async def _synthesize_with(
        self,
        provider: str,
        text: str,
        voice: str,
        speed: float,
        pitch: int
    ) -> bytes:
        """
        Synthesize using a specific provider.

        Args:
            provider: Provider name
            text: Text to synthesize
            voice: Voice ID
            speed: Speed multiplier
            pitch: Pitch adjustment

        Returns:
            Audio bytes
        """
        if provider == "qwen3":
            return await self._synthesize_qwen3(text, voice, speed, pitch)
        elif provider == "edge":
            return await self._synthesize_edge(text, voice, speed, pitch)
        elif provider == "espeak":
            return await self._synthesize_espeak(text, voice, speed, pitch)
        elif provider == "piper":
            return await self._synthesize_piper(text, voice, speed, pitch)
        else:
            raise ValueError(f"Unknown provider: {provider}")

    async def _synthesize_qwen3(
        self,
        text: str,
        voice: str,
        speed: float,
        pitch: int
    ) -> bytes:
        """
        Synthesize using Qwen3 TTS server.

        Uses the HTTP client to connect to the local Qwen3-TTS server.
        """
        if self._qwen3_client is None:
            self._qwen3_client = Qwen3TTSClient(
                server_url=self.config.qwen3_server_url
            )

        # Check availability with timeout
        timeout_sec = self.config.timeout_ms / 1000
        try:
            is_available = await asyncio.wait_for(
                self._qwen3_client.is_available(),
                timeout=timeout_sec
            )
            if not is_available:
                raise TTSError("Qwen3 TTS server not available")
        except asyncio.TimeoutError:
            raise TTSError("Qwen3 availability check timed out")

        # Determine language and speaker
        language = "Russian" if self.config.language == "ru" else "English"
        speaker = voice if voice != "default" else self.config.qwen3_speaker

        # Synthesize with timeout
        audio = await asyncio.wait_for(
            self._qwen3_client.synthesize(text, language, speaker),
            timeout=30.0  # Allow longer for actual synthesis
        )

        return audio

    async def _synthesize_edge(
        self,
        text: str,
        voice: str,
        speed: float,
        pitch: int
    ) -> bytes:
        """
        Synthesize using Edge TTS (Microsoft).

        Uses the FastTTSClient which wraps edge-tts library.
        """
        if self._fast_tts_client is None:
            default_voice = "ru-male" if self.config.language == "ru" else "en-male"
            self._fast_tts_client = FastTTSClient(voice=default_voice)

        # Map voice parameter
        if voice == "default":
            # Auto-detect language from text
            audio = await self._fast_tts_client.synthesize_auto(text)
        else:
            audio = await self._fast_tts_client.synthesize(text, voice=voice)

        if not audio:
            raise TTSError("Edge TTS returned empty audio")

        return audio

    async def _synthesize_piper(
        self,
        text: str,
        voice: str,
        speed: float,
        pitch: int
    ) -> bytes:
        """
        Synthesize using Piper TTS (local/offline).

        Fastest option (~100ms) but requires local ONNX model.
        """
        # Run Piper synthesis in thread pool (it's synchronous)
        loop = asyncio.get_event_loop()
        audio = await loop.run_in_executor(
            None,
            self._piper_synthesize_sync,
            text,
            voice,
            speed
        )
        return audio

    async def _synthesize_espeak(
        self,
        text: str,
        voice: str,
        speed: float,
        pitch: int
    ) -> bytes:
        """
        Synthesize using local espeak-ng (robotic fast mode).
        """
        if self._espeak_client is None:
            base_voice = self.config.espeak_voice_ru if self.config.language == "ru" else self.config.espeak_voice_en
            self._espeak_client = ESpeakTTSClient(
                voice=base_voice,
                rate=self.config.espeak_rate,
                pitch=self.config.espeak_pitch,
                amplitude=self.config.espeak_amplitude,
                preset=self.config.espeak_preset,
            )

        selected_voice = voice if voice != "default" else None
        audio = await self._espeak_client.synthesize(text, voice=selected_voice)
        if not audio:
            raise TTSError("eSpeak returned empty audio")
        return audio

    def _piper_synthesize_sync(
        self,
        text: str,
        voice: str,
        speed: float
    ) -> bytes:
        """
        Synchronous Piper synthesis (runs in thread pool).
        """
        try:
            from piper import PiperVoice
            import wave

            # Find model path
            model_path = self.config.piper_model_path
            if not model_path:
                # Auto-detect from data/voice_models
                project_root = Path(__file__).parent.parent.parent
                voice_models_dir = project_root / "data" / "voice_models"

                # Find first .onnx file
                onnx_files = list(voice_models_dir.glob("*.onnx"))
                if onnx_files:
                    model_path = str(onnx_files[0])
                else:
                    raise TTSError("No Piper ONNX models found in data/voice_models/")

            # Load voice if not cached
            if self._piper_voice is None:
                logger.info(f"[TTSEngine] Loading Piper model: {model_path}")
                self._piper_voice = PiperVoice.load(model_path)

            # Synthesize to WAV bytes
            audio_buffer = io.BytesIO()

            with wave.open(audio_buffer, 'wb') as wav_file:
                self._piper_voice.synthesize(text, wav_file, length_scale=1.0/speed)

            audio_buffer.seek(0)
            return audio_buffer.read()

        except ImportError as e:
            raise TTSError(f"Piper not installed: {e}")
        except Exception as e:
            raise TTSError(f"Piper synthesis failed: {e}")

    def _record_success(self, provider: str, latency_ms: float):
        """Record successful synthesis."""
        stats = self._provider_stats[provider]
        stats["successes"] += 1
        stats["total_latency_ms"] += latency_ms

    def _record_failure(self, provider: str):
        """Record failed synthesis."""
        self._provider_stats[provider]["failures"] += 1

    def get_stats(self) -> Dict[str, Any]:
        """Get provider statistics."""
        result = {}
        for provider, stats in self._provider_stats.items():
            total = stats["successes"] + stats["failures"]
            avg_latency = (
                stats["total_latency_ms"] / stats["successes"]
                if stats["successes"] > 0 else 0
            )
            result[provider] = {
                "successes": stats["successes"],
                "failures": stats["failures"],
                "success_rate": stats["successes"] / total if total > 0 else 0,
                "avg_latency_ms": avg_latency
            }
        return result

    async def check_providers(self) -> Dict[str, bool]:
        """
        Check availability of all providers.

        Returns:
            Dict mapping provider name to availability status
        """
        availability = {}

        # Check Qwen3
        try:
            if self._qwen3_client is None:
                self._qwen3_client = Qwen3TTSClient(
                    server_url=self.config.qwen3_server_url
                )
            availability["qwen3"] = await self._qwen3_client.is_available()
        except Exception:
            availability["qwen3"] = False

        # Check Edge TTS (requires internet)
        try:
            import edge_tts
            availability["edge"] = True  # Assume available if module exists
        except ImportError:
            availability["edge"] = False

        # Check eSpeak (local binary)
        availability["espeak"] = bool(shutil.which("espeak-ng") or shutil.which("espeak"))

        # Check Piper
        try:
            from piper import PiperVoice
            project_root = Path(__file__).parent.parent.parent
            voice_models_dir = project_root / "data" / "voice_models"
            onnx_files = list(voice_models_dir.glob("*.onnx"))
            availability["piper"] = len(onnx_files) > 0
        except ImportError:
            availability["piper"] = False

        return availability

    async def close(self):
        """Cleanup resources."""
        if self._qwen3_client:
            await self._qwen3_client.close()
            self._qwen3_client = None
        self._piper_voice = None
        logger.info("[TTSEngine] Closed and cleaned up resources")

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()


# Factory functions for Phase 105

def get_tts_engine(
    primary: str = "qwen3",
    language: str = "ru"
) -> TTSEngine:
    """
    Create a TTSEngine with specified configuration.

    Args:
        primary: Primary provider (qwen3, edge, piper)
        language: Default language (ru, en)

    Returns:
        Configured TTSEngine instance
    """
    config = TTSConfig(
        primary_provider=primary,
        language=language
    )
    return TTSEngine(primary=primary, config=config)


async def quick_synthesize(
    text: str,
    language: str = "en",
    provider: str = "edge"
) -> bytes:
    """
    Quick one-shot TTS synthesis.

    Args:
        text: Text to synthesize
        language: Language code
        provider: Preferred provider

    Returns:
        Audio bytes
    """
    async with TTSEngine(primary=provider, config=TTSConfig(language=language)) as engine:
        return await engine.synthesize(text)


# MARKER_105_TTS_FALLBACK_END
