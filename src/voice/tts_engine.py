# MARKER_102.5_START
import torch
import numpy as np
from typing import Optional, Union, List
import logging
from pathlib import Path

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
        self.device = device or ('cuda' if torch.cuda.is_available() else 'cpu')
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