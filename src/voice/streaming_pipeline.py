"""
VETKA Phase 104.7 - Streaming LLM → TTS Pipeline

Generates audio in real-time as LLM produces text.
Dramatically reduces perceived latency by starting playback early.

@file streaming_pipeline.py
@status experimental
@phase 104.7
@depends jarvis_llm, tts_engine

Architecture:
1. LLM generates text tokens via streaming
2. Accumulate until sentence boundary (. ! ?)
3. Immediately send sentence to TTS
4. Yield audio chunks as they're ready
5. Frontend plays chunks sequentially

Target: First audio chunk in <2s (vs current 10s)
"""

import logging
import asyncio
import re
from typing import AsyncGenerator, Optional, Dict, Any, Tuple
from dataclasses import dataclass

from .jarvis_llm import get_jarvis_llm, get_jarvis_context
from .tts_engine import Qwen3TTSClient

logger = logging.getLogger(__name__)


@dataclass
class StreamingConfig:
    """Configuration for streaming pipeline"""
    min_sentence_length: int = 10  # Min chars before TTS
    max_buffer_length: int = 200   # Max chars before force-flush
    tts_server_url: str = "http://127.0.0.1:5003"
    language: str = "English"
    speaker: str = "ryan"


class StreamingPipeline:
    """
    Real-time LLM → TTS pipeline.

    Usage:
        pipeline = StreamingPipeline()
        async for audio_chunk, text_chunk in pipeline.generate("Hello!"):
            # Send to frontend
            await websocket.send(audio_chunk)
    """

    def __init__(self, config: Optional[StreamingConfig] = None):
        self.config = config or StreamingConfig()
        self._tts_client: Optional[Qwen3TTSClient] = None

    async def _get_tts_client(self) -> Qwen3TTSClient:
        """Get or create TTS client"""
        if self._tts_client is None:
            self._tts_client = Qwen3TTSClient(server_url=self.config.tts_server_url)
        return self._tts_client

    async def close(self):
        """Cleanup resources"""
        if self._tts_client:
            await self._tts_client.close()
            self._tts_client = None

    def _should_flush(self, buffer: str) -> Tuple[bool, str, str]:
        """
        Check if buffer should be flushed to TTS.

        Returns:
            (should_flush, text_to_flush, remaining_buffer)
        """
        if not buffer:
            return False, "", ""

        # Look for sentence boundaries
        match = re.search(r'([^.!?]*[.!?])\s*', buffer)
        if match:
            sentence = match.group(1).strip()
            remaining = buffer[match.end():].strip()

            # Only flush if sentence is long enough
            if len(sentence) >= self.config.min_sentence_length:
                return True, sentence, remaining

        # Force flush if buffer is too long
        if len(buffer) >= self.config.max_buffer_length:
            # Find last space to avoid cutting words
            last_space = buffer.rfind(' ', 0, self.config.max_buffer_length)
            if last_space > self.config.min_sentence_length:
                return True, buffer[:last_space], buffer[last_space:].strip()

        return False, "", buffer

    async def generate(
        self,
        transcript: str,
        user_id: str = "default_user",
        context: Optional[Dict[str, Any]] = None
    ) -> AsyncGenerator[Tuple[bytes, str], None]:
        """
        Stream LLM → TTS generation.

        Args:
            transcript: User's speech transcript
            user_id: User identifier
            context: Optional memory context

        Yields:
            Tuples of (audio_bytes, text_chunk)
        """
        import time
        pipeline_start = time.perf_counter()
        first_audio_time = None

        llm = get_jarvis_llm()
        tts = await self._get_tts_client()

        # Get context if not provided
        if context is None:
            context = await get_jarvis_context(user_id, transcript)

        buffer = ""
        full_response = ""
        sentence_count = 0

        logger.info(f"[StreamingPipeline] Starting for: {transcript[:50]}...")

        try:
            async for token in llm.generate_stream(transcript, user_id, context):
                buffer += token
                full_response += token

                # Check if we should flush to TTS
                should_flush, text_to_flush, remaining = self._should_flush(buffer)

                if should_flush:
                    sentence_count += 1
                    buffer = remaining

                    logger.debug(f"[StreamingPipeline] Flushing sentence {sentence_count}: {text_to_flush[:30]}...")

                    # Generate TTS for this sentence
                    try:
                        tts_start = time.perf_counter()
                        audio_bytes = await tts.synthesize(
                            text=text_to_flush,
                            language=self.config.language,
                            speaker=self.config.speaker
                        )
                        tts_duration = time.perf_counter() - tts_start

                        if audio_bytes:
                            if first_audio_time is None:
                                first_audio_time = time.perf_counter() - pipeline_start
                                logger.info(f"[StreamingPipeline] First audio in {first_audio_time:.2f}s!")

                            logger.debug(f"[StreamingPipeline] TTS {sentence_count} in {tts_duration:.2f}s")
                            yield audio_bytes, text_to_flush

                    except Exception as e:
                        logger.error(f"[StreamingPipeline] TTS error: {e}")
                        continue

            # Flush remaining buffer
            if buffer.strip():
                logger.debug(f"[StreamingPipeline] Flushing final: {buffer[:30]}...")
                try:
                    audio_bytes = await tts.synthesize(
                        text=buffer.strip(),
                        language=self.config.language,
                        speaker=self.config.speaker
                    )
                    if audio_bytes:
                        yield audio_bytes, buffer.strip()
                except Exception as e:
                    logger.error(f"[StreamingPipeline] Final TTS error: {e}")

            total_time = time.perf_counter() - pipeline_start
            logger.info(
                f"[StreamingPipeline] Complete: {sentence_count} sentences, "
                f"first audio: {first_audio_time:.2f}s, total: {total_time:.2f}s"
            )

        except Exception as e:
            logger.error(f"[StreamingPipeline] Error: {e}", exc_info=True)
            raise


# === Convenience Functions ===

_pipeline: Optional[StreamingPipeline] = None


def get_streaming_pipeline() -> StreamingPipeline:
    """Get or create streaming pipeline singleton"""
    global _pipeline
    if _pipeline is None:
        _pipeline = StreamingPipeline()
    return _pipeline


async def streaming_jarvis_respond(
    transcript: str,
    user_id: str = "default_user"
) -> AsyncGenerator[Tuple[bytes, str], None]:
    """
    Convenience function for streaming Jarvis response.

    Args:
        transcript: User's speech
        user_id: User identifier

    Yields:
        (audio_bytes, text_chunk) tuples
    """
    pipeline = get_streaming_pipeline()
    async for audio, text in pipeline.generate(transcript, user_id):
        yield audio, text
