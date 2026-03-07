"""
JARVIS Voice Interface Socket.IO Handler
Handles real-time voice interaction with AI assistant (SEPARATE from chat).

State Machine: idle -> listening -> thinking -> speaking -> idle

MARKER_104.3: Jarvis voice interface handler
MARKER_105_EDGE_CASES: T9 prediction edge case handling
"""

import logging
import base64
import io
import wave
import tempfile
import asyncio
import time
import os
import json
import random
import hashlib
import numpy as np
from collections import deque
from dataclasses import dataclass, field
from typing import Dict, Optional, List, Tuple, Callable, Any
from enum import Enum
from pathlib import Path
from functools import wraps

logger = logging.getLogger(__name__)


# =============================================================================
# MARKER_105_EDGE_CASES: T9 Prediction Edge Case Handling
# =============================================================================

# Edge case thresholds
T9_LOW_CONFIDENCE_THRESHOLD = 0.3      # Below this: wait for more input
T9_MODERATE_CONFIDENCE_THRESHOLD = 0.5  # Below this: show with disclaimer
T9_STT_CONFIDENCE_THRESHOLD = 0.5       # Below this: ask to repeat
T9_MODEL_TIMEOUT_MS = 2000              # For T9 draft prediction (fast, 2s OK)
T9_MIN_WORDS = 2                        # Minimum words before prediction

# MARKER_105_JARVIS_TIMEOUT_FIX: Separate timeout for full LLM generation
JARVIS_LLM_TIMEOUT_MS = 30000           # Full LLM response (30s, matches Ollama)

# Phase 157.3.1: staged response orchestration
JARVIS_STAGE_MACHINE_ENABLE = os.getenv("JARVIS_STAGE_MACHINE_ENABLE", "1").lower() in {"1", "true", "yes", "on"}
JARVIS_STAGE2_MODEL = os.getenv("JARVIS_STAGE2_MODEL", "gemma3:1b")
JARVIS_STAGE3_PRIMARY_MODEL = os.getenv("JARVIS_STAGE3_PRIMARY_MODEL", "deepseek-r1:8b")
JARVIS_STAGE3_SECONDARY_MODEL = os.getenv("JARVIS_STAGE3_SECONDARY_MODEL", "llama3.2:3b")
JARVIS_STAGE4_ENABLE = os.getenv("JARVIS_STAGE4_ENABLE", "1").lower() in {"1", "true", "yes", "on"}
JARVIS_STAGE4_MODEL = os.getenv("JARVIS_STAGE4_MODEL", "")

JARVIS_PLANB_FILLER_ENABLE = os.getenv("JARVIS_PLANB_FILLER_ENABLE", "1").lower() in {"1", "true", "yes", "on"}
JARVIS_PLANB_FILLER_DELAY_SEC = float(os.getenv("JARVIS_PLANB_FILLER_DELAY_SEC", "0.15"))
JARVIS_FILLER_BANK_PATH = Path(os.getenv("JARVIS_FILLER_BANK_PATH", "data/jarvis_filler_bank.json"))
JARVIS_FILLER_BANK_USE_FILE = os.getenv("JARVIS_FILLER_BANK_USE_FILE", "0").lower() in {"1", "true", "yes", "on"}
JARVIS_PLANB_LEARN_ENABLE = os.getenv("JARVIS_PLANB_LEARN_ENABLE", "0").lower() in {"1", "true", "yes", "on"}
JARVIS_PLANB_LEARN_MIN_INTERVAL_SEC = float(os.getenv("JARVIS_PLANB_LEARN_MIN_INTERVAL_SEC", "1800"))
JARVIS_TRACE_MAX = int(os.getenv("JARVIS_TRACE_MAX", "200"))
JARVIS_FILLER_AUDIO_ENABLE = os.getenv("JARVIS_FILLER_AUDIO_ENABLE", "1").lower() in {"1", "true", "yes", "on"}
JARVIS_FILLER_AUDIO_WARMUP = os.getenv("JARVIS_FILLER_AUDIO_WARMUP", "1").lower() in {"1", "true", "yes", "on"}
JARVIS_FILLER_AUDIO_CACHE_DIR = Path(
    os.getenv("JARVIS_FILLER_AUDIO_CACHE_DIR", "data/jarvis_filler_audio")
)
JARVIS_FILLER_AUDIO_VOICE = os.getenv("JARVIS_FILLER_AUDIO_VOICE", "ru-female").strip() or "ru-female"
JARVIS_FAST_TTS_VOICE = os.getenv("JARVIS_FAST_TTS_VOICE", JARVIS_FILLER_AUDIO_VOICE).strip() or "ru-female"
JARVIS_CONTEXT_MAX_PINNED = int(os.getenv("JARVIS_CONTEXT_MAX_PINNED", "8"))
JARVIS_CONTEXT_MAX_VIEWPORT = int(os.getenv("JARVIS_CONTEXT_MAX_VIEWPORT", "24"))
JARVIS_CONTEXT_MAX_CHAT_MESSAGES = int(os.getenv("JARVIS_CONTEXT_MAX_CHAT_MESSAGES", "6"))
JARVIS_STAGE2_TIMEOUT_MS = int(os.getenv("JARVIS_STAGE2_TIMEOUT_MS", "4500"))
JARVIS_STAGE3_TIMEOUT_MS = int(os.getenv("JARVIS_STAGE3_TIMEOUT_MS", "5000"))
JARVIS_STAGE4_TIMEOUT_MS = int(os.getenv("JARVIS_STAGE4_TIMEOUT_MS", "6000"))

# MARKER_157_6_VOICE_PROFILE_BACKEND:
# Backend voice profiles. UI chooser can map to these IDs in future.
VOICE_PROFILES: Dict[str, Dict[str, str]] = {
    "vetka_ru_female": {"fast_tts_voice": "ru-female", "filler_voice": "ru-female"},
    "vetka_ru_male": {"fast_tts_voice": "ru-male", "filler_voice": "ru-male"},
    "vetka_en_female": {"fast_tts_voice": "en-female", "filler_voice": "en-female"},
    "vetka_en_male": {"fast_tts_voice": "en-male", "filler_voice": "en-male"},
}
JARVIS_VOICE_PROFILE = os.getenv("JARVIS_VOICE_PROFILE", "vetka_ru_female").strip() or "vetka_ru_female"
# MARKER_157_7_4_VOICE_LOCK_EDGE_RU_FEMALE.V1:
# Runtime voice lock for VETKA-JARVIS: single stable timbre (edge ru-female) with no backend switching.
JARVIS_VOICE_LOCK_EDGE_RU_FEMALE = os.getenv("JARVIS_VOICE_LOCK_EDGE_RU_FEMALE", "1").lower() in {"1", "true", "yes", "on"}


class T9PredictionStatus(str, Enum):
    """Status codes for T9 prediction edge cases"""
    CONFIDENT = "confident"                  # Full prediction, proceed
    LOW_CONFIDENCE_DRAFT = "low_confidence_draft"  # Weak prediction, show warning
    WAITING_FOR_INPUT = "waiting_for_input"  # Too few words, wait
    STT_RETRY = "stt_retry"                  # Audio unclear, ask to repeat
    INTERRUPTED = "interrupted"              # User interrupted, cancel
    TIMEOUT_FALLBACK = "timeout_fallback"    # Model slow, use template


# Template responses for timeout fallback
TIMEOUT_FALLBACK_TEMPLATES = {
    "greeting": "Hello! How can I help you today?",
    "question": "Let me think about that for a moment.",
    "command": "I'll process that request.",
    "default": "I'm here to help. What would you like to do?"
}

_jarvis_turn_traces: deque = deque(maxlen=JARVIS_TRACE_MAX)
_filler_audio_cache: Dict[str, Dict[str, Tuple[bytes, str]]] = {"ru": {}, "en": {}}
_filler_audio_warmup_started = False


def _append_jarvis_trace(trace: Dict[str, Any]) -> None:
    try:
        _jarvis_turn_traces.append(trace)
    except Exception as e:
        logger.debug(f"[JARVIS][TRACE] append failed: {e}")


def get_jarvis_turn_traces(limit: int = 20) -> List[Dict[str, Any]]:
    try:
        cap = max(1, min(int(limit), JARVIS_TRACE_MAX))
    except Exception:
        cap = 20
    return list(_jarvis_turn_traces)[-cap:]


def _classify_input_type(partial_input: str) -> str:
    """
    Classify input type for fallback template selection.

    Args:
        partial_input: The partial user input

    Returns:
        Input type: 'greeting', 'question', 'command', or 'default'
    """
    input_lower = partial_input.lower().strip()

    # Greeting patterns (EN + RU)
    greeting_patterns = [
        "hello", "hi", "hey", "good morning", "good evening",
        "привет", "здравствуй", "добрый", "доброе", "добрый день"
    ]
    if any(input_lower.startswith(p) for p in greeting_patterns):
        return "greeting"

    # Question patterns
    question_words = ["what", "how", "why", "when", "where", "who", "which",
                      "что", "как", "почему", "когда", "где", "кто", "какой"]
    if any(input_lower.startswith(w) for w in question_words) or input_lower.endswith("?"):
        return "question"

    # Command patterns
    command_words = ["open", "show", "create", "delete", "find", "search",
                     "открой", "покажи", "создай", "удали", "найди"]
    if any(input_lower.startswith(w) for w in command_words):
        return "command"

    return "default"


async def handle_prediction_edge_cases(
    partial_input: str,
    prediction_confidence: float,
    stt_confidence: float,
    is_interrupted: bool = False,
    prediction_response: Optional[str] = None
) -> Tuple[Optional[str], T9PredictionStatus]:
    """
    Handle edge cases in T9 prediction.

    MARKER_105_EDGE_CASES: Core edge case handling function.

    Args:
        partial_input: Partial user input from STT
        prediction_confidence: Confidence score of T9 prediction (0.0-1.0)
        stt_confidence: Confidence score of STT transcription (0.0-1.0)
        is_interrupted: Whether user interrupted during TTS playback
        prediction_response: The predicted response text (if any)

    Returns:
        Tuple of (response_or_none, status_code)

    Status codes:
        - "confident": Full prediction, proceed
        - "low_confidence_draft": Weak prediction, show with warning
        - "waiting_for_input": Too few words, wait
        - "stt_retry": Audio unclear, ask to repeat
        - "interrupted": User interrupted, cancel
        - "timeout_fallback": Model slow, use template
    """
    # Case 1: Too few words - need more input
    word_count = len(partial_input.split()) if partial_input else 0
    if word_count < T9_MIN_WORDS:
        logger.debug(f"[T9 Edge] Waiting for input: only {word_count} word(s)")
        return None, T9PredictionStatus.WAITING_FOR_INPUT

    # Case 2: Noisy audio - STT confidence too low
    if stt_confidence < T9_STT_CONFIDENCE_THRESHOLD:
        logger.info(f"[T9 Edge] STT confidence too low: {stt_confidence:.2f}")
        return "Не расслышал, повтори?", T9PredictionStatus.STT_RETRY

    # Case 3: User interrupt during TTS
    if is_interrupted:
        logger.info("[T9 Edge] User interrupted TTS playback")
        return None, T9PredictionStatus.INTERRUPTED

    # Case 4: Very low prediction confidence - wait for more
    if prediction_confidence < T9_LOW_CONFIDENCE_THRESHOLD:
        logger.debug(f"[T9 Edge] Prediction confidence too low: {prediction_confidence:.2f}")
        return None, T9PredictionStatus.WAITING_FOR_INPUT

    # Case 5: Moderate confidence - proceed with disclaimer
    if prediction_confidence < T9_MODERATE_CONFIDENCE_THRESHOLD:
        logger.info(f"[T9 Edge] Moderate confidence: {prediction_confidence:.2f}")
        return prediction_response, T9PredictionStatus.LOW_CONFIDENCE_DRAFT

    # Case 6: High confidence - full prediction
    logger.debug(f"[T9 Edge] Confident prediction: {prediction_confidence:.2f}")
    return prediction_response, T9PredictionStatus.CONFIDENT


def with_timeout_fallback(timeout_ms: int = T9_MODEL_TIMEOUT_MS):
    """
    Decorator for model calls with timeout fallback.

    MARKER_105_EDGE_CASES: Timeout handling wrapper.

    If the model takes longer than timeout_ms, returns a template response
    instead and logs a warning.

    Args:
        timeout_ms: Maximum time to wait in milliseconds

    Usage:
        @with_timeout_fallback(2000)
        async def predict_response(input_text: str) -> str:
            # LLM call here
            return response
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.perf_counter()
            timeout_sec = timeout_ms / 1000.0

            try:
                result = await asyncio.wait_for(
                    func(*args, **kwargs),
                    timeout=timeout_sec
                )
                elapsed_ms = (time.perf_counter() - start_time) * 1000
                logger.debug(f"[T9 Timeout] Model responded in {elapsed_ms:.0f}ms")
                return result

            except asyncio.TimeoutError:
                elapsed_ms = (time.perf_counter() - start_time) * 1000
                logger.warning(f"[T9 Timeout] Model timeout after {elapsed_ms:.0f}ms, using fallback")

                # Try to extract input for template selection
                partial_input = ""
                if args:
                    partial_input = str(args[0]) if args[0] else ""
                elif "partial_input" in kwargs:
                    partial_input = kwargs["partial_input"]
                elif "transcript" in kwargs:
                    partial_input = kwargs["transcript"]

                input_type = _classify_input_type(partial_input)
                fallback = TIMEOUT_FALLBACK_TEMPLATES.get(input_type, TIMEOUT_FALLBACK_TEMPLATES["default"])

                return fallback, T9PredictionStatus.TIMEOUT_FALLBACK

        return wrapper
    return decorator


async def timeout_wrapped_prediction(
    predict_func: Callable,
    partial_input: str,
    timeout_ms: int = T9_MODEL_TIMEOUT_MS,
    **kwargs
) -> Tuple[Optional[str], T9PredictionStatus]:
    """
    Wrap a prediction function with timeout handling.

    MARKER_105_EDGE_CASES: Alternative to decorator for dynamic timeout.

    Args:
        predict_func: Async function that returns prediction response
        partial_input: User's partial input
        timeout_ms: Timeout in milliseconds
        **kwargs: Additional arguments for predict_func

    Returns:
        Tuple of (response, status)
    """
    start_time = time.perf_counter()
    timeout_sec = timeout_ms / 1000.0

    try:
        result = await asyncio.wait_for(
            predict_func(partial_input, **kwargs),
            timeout=timeout_sec
        )
        elapsed_ms = (time.perf_counter() - start_time) * 1000
        logger.debug(f"[T9 Timeout] Prediction completed in {elapsed_ms:.0f}ms")

        # If result is a tuple (response, confidence), use it
        if isinstance(result, tuple):
            response, confidence = result
            if confidence >= T9_MODERATE_CONFIDENCE_THRESHOLD:
                return response, T9PredictionStatus.CONFIDENT
            elif confidence >= T9_LOW_CONFIDENCE_THRESHOLD:
                return response, T9PredictionStatus.LOW_CONFIDENCE_DRAFT
            else:
                return None, T9PredictionStatus.WAITING_FOR_INPUT
        else:
            # Simple string response, assume confident
            return result, T9PredictionStatus.CONFIDENT

    except asyncio.TimeoutError:
        elapsed_ms = (time.perf_counter() - start_time) * 1000
        logger.warning(f"[T9 Timeout] Prediction timeout after {elapsed_ms:.0f}ms")

        input_type = _classify_input_type(partial_input)
        fallback = TIMEOUT_FALLBACK_TEMPLATES.get(input_type, TIMEOUT_FALLBACK_TEMPLATES["default"])

        return fallback, T9PredictionStatus.TIMEOUT_FALLBACK


# Interrupt handling state
_active_tts_tasks: Dict[str, asyncio.Task] = {}


async def handle_jarvis_interrupt(
    sio,
    sid: str,
    user_id: str,
    new_input: Optional[str] = None
) -> bool:
    """
    Handle user interrupt during TTS playback.

    MARKER_105_EDGE_CASES: Interrupt handling for TTS.

    Cancels current TTS playback, emits interrupt event,
    and optionally restarts with new input.

    Args:
        sio: SocketIO instance
        sid: Socket session ID
        user_id: User identifier
        new_input: New input to process after cancellation

    Returns:
        True if interrupt was handled, False if no active TTS
    """
    # Check for active TTS task
    task_key = f"{sid}:{user_id}"
    active_task = _active_tts_tasks.get(task_key)

    if active_task and not active_task.done():
        logger.info(f"[T9 Interrupt] Cancelling TTS for {user_id}")
        active_task.cancel()

        try:
            await active_task
        except asyncio.CancelledError:
            logger.debug(f"[T9 Interrupt] TTS task cancelled successfully")

        # Remove from active tasks
        _active_tts_tasks.pop(task_key, None)

        # Emit interrupt event to client
        await sio.emit('jarvis_interrupt', {
            'user_id': user_id,
            'reason': 'user_interrupt',
            'new_input': new_input
        }, to=sid)

        return True

    return False


def register_tts_task(sid: str, user_id: str, task: asyncio.Task):
    """
    Register an active TTS task for interrupt handling.

    Args:
        sid: Socket session ID
        user_id: User identifier
        task: The asyncio Task running TTS
    """
    task_key = f"{sid}:{user_id}"
    _active_tts_tasks[task_key] = task
    logger.debug(f"[T9 Interrupt] Registered TTS task for {user_id}")


def unregister_tts_task(sid: str, user_id: str):
    """
    Unregister a TTS task after completion.

    Args:
        sid: Socket session ID
        user_id: User identifier
    """
    task_key = f"{sid}:{user_id}"
    _active_tts_tasks.pop(task_key, None)
    logger.debug(f"[T9 Interrupt] Unregistered TTS task for {user_id}")


# =============================================================================
# End of MARKER_105_EDGE_CASES
# =============================================================================


def pcm_to_wav(pcm_data: bytes, sample_rate: int = 24000, channels: int = 1, sample_width: int = 2) -> bytes:
    """
    Convert raw PCM data to WAV format with proper header.

    Args:
        pcm_data: Raw PCM audio bytes (int16)
        sample_rate: Audio sample rate (TTS uses 24000)
        channels: Number of audio channels (1 = mono)
        sample_width: Bytes per sample (2 = 16-bit)

    Returns:
        WAV formatted audio bytes
    """
    wav_buffer = io.BytesIO()
    with wave.open(wav_buffer, 'wb') as wav_file:
        wav_file.setnchannels(channels)
        wav_file.setsampwidth(sample_width)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(pcm_data)
    return wav_buffer.getvalue()


def _detect_audio_format(audio_bytes: bytes) -> str:
    if not audio_bytes:
        return "unknown"
    if len(audio_bytes) >= 12 and audio_bytes[:4] == b"RIFF" and audio_bytes[8:12] == b"WAVE":
        return "wav"
    if audio_bytes[:3] == b"ID3":
        return "mp3"
    if len(audio_bytes) >= 2 and audio_bytes[0] == 0xFF and (audio_bytes[1] & 0xE0) == 0xE0:
        return "mp3"
    if audio_bytes[:4] == b"OggS":
        return "ogg"
    return "pcm"


# Import STT and TTS engines
try:
    import mlx_whisper
    HAS_MLX_WHISPER = True
    logger.info("[JARVIS] mlx_whisper available")
except ImportError:
    HAS_MLX_WHISPER = False
    logger.warning("[JARVIS] mlx_whisper not available, STT disabled")

try:
    from src.voice.tts_engine import Qwen3TTSClient, FastTTSClient, ESpeakTTSClient
    HAS_TTS = True
    HAS_FAST_TTS = True
    HAS_ESPEAK_TTS = True
    logger.info("[JARVIS] TTS clients available (Qwen3 + Fast)")
except ImportError:
    HAS_TTS = False
    HAS_FAST_TTS = False
    HAS_ESPEAK_TTS = False
    logger.warning("[JARVIS] TTS client not available")

# TTS Mode: 'fast' (Edge-TTS, lower latency) or 'quality' (Qwen3-TTS)
# Default fast to prioritize live dialog latency/stability.
TTS_MODE = os.getenv("JARVIS_TTS_MODE", "fast").strip().lower()
JARVIS_TTS_PROVIDER = os.getenv("JARVIS_TTS_PROVIDER", "auto").strip().lower()  # edge|espeak|auto
JARVIS_TTS_FALLBACK_PROVIDER = os.getenv("JARVIS_TTS_FALLBACK_PROVIDER", "espeak").strip().lower()
JARVIS_ESPEAK_VOICE_RU = os.getenv("JARVIS_ESPEAK_VOICE_RU", "ru").strip() or "ru"
JARVIS_ESPEAK_VOICE_EN = os.getenv("JARVIS_ESPEAK_VOICE_EN", "en").strip() or "en"
JARVIS_ESPEAK_PRESET = os.getenv("JARVIS_ESPEAK_PRESET", "c3po").strip() or "c3po"
JARVIS_ESPEAK_RATE = int(os.getenv("JARVIS_ESPEAK_RATE", "155"))
JARVIS_ESPEAK_PITCH = int(os.getenv("JARVIS_ESPEAK_PITCH", "70"))
JARVIS_ESPEAK_AMPLITUDE = int(os.getenv("JARVIS_ESPEAK_AMPLITUDE", "130"))

# Phase 104.6: LLM Integration
try:
    from src.voice.jarvis_llm import get_jarvis_llm, get_jarvis_context
    HAS_LLM = True
    logger.info("[JARVIS] LLM integration available")
except ImportError as e:
    HAS_LLM = False
    logger.warning(f"[JARVIS] LLM integration not available: {e}")


def _is_hallucination(transcript: str) -> bool:
    """
    Detect Whisper hallucination patterns.

    Whisper sometimes generates repeated phrases when given silence or noise.
    Common patterns: "I'm going to...", "Thank you for watching", etc.

    Args:
        transcript: STT output to check

    Returns:
        True if likely hallucination
    """
    if not transcript:
        return False

    # Check for repeated phrases (split by sentence markers)
    import re
    sentences = re.split(r'[.!?]', transcript)
    sentences = [s.strip() for s in sentences if s.strip()]

    if len(sentences) >= 3:
        # If same sentence repeats 3+ times, it's hallucination
        from collections import Counter
        counts = Counter(sentences)
        most_common = counts.most_common(1)
        if most_common and most_common[0][1] >= 3:
            logger.warning(f"[JARVIS] Hallucination detected: '{most_common[0][0]}' repeated {most_common[0][1]} times")
            return True

    # Check for known hallucination phrases
    hallucination_patterns = [
        "thank you for watching",
        "please subscribe",
        "like and subscribe",
        "see you in the next",
        "i'm going to go to the next",
        "transcribed by",
        "subtitles by",
    ]
    transcript_lower = transcript.lower()
    for pattern in hallucination_patterns:
        if pattern in transcript_lower:
            logger.warning(f"[JARVIS] Known hallucination pattern: '{pattern}'")
            return True

    return False


def _default_filler_bank() -> Dict[str, List[str]]:
    return {
        "ru": [
            "Секунду, собираю ответ.",
            "Хм, интересный вопрос...",
            "Занимательно, дайте подумать.",
            "Ого, это заслуживает размышлений.",
            "Хм, любопытная тема.",
            "Интригующе, сейчас разберёмся.",
            "Хм, хороший повод для раздумий.",
            "Ух ты, это заставляет задуматься.",
            "Хм, необычный запрос.",
            "Занятно, давайте поразмыслим.",
            "Хм, это стоит обдумать.",
            "Ой, интересная мысль.",
            "Хм, давайте подумаем вместе.",
            "Вау, это круто, секунду.",
            "Хм, заманчивая идея.",
            "Любопытно, сейчас отвечу.",
            "Хм, это требует внимания.",
            "О, забавный вопрос.",
            "Хм, давайте разберём по полочкам.",
            "Интересно, что же вы имеете в виду?",
            "Хм, это вдохновляет на ответ.",
            "Ух, сложный, но интересный.",
            "Хм, давайте я подумаю.",
            "Занятно, сейчас соберу мысли.",
            "Хм, это свежий взгляд.",
            "Ого, давайте углубимся.",
            "Хм, привлекательная тема.",
            "Любопытно, подождите миг.",
            "Хм, это стоит обсудить.",
            "Вау, интересный поворот.",
            "Хм, давайте я обдумаю.",
            "Занимательно, секунду.",
            "Хм, это вызывает интерес.",
            "Ой, круто, сейчас отвечу.",
            "Хм, необычная идея.",
            "Интригующе, давайте разберём.",
            "Хм, хороший вопросик.",
            "Ух ты, это зацепило.",
            "Хм, давайте подумаем глубже.",
            "Занятно, сейчас подумаю.",
            "Хм, это мотивирует.",
            "Ого, интересная загадка.",
            "Хм, давайте я проанализирую.",
            "Любопытно, подождите.",
            "Хм, это стоит внимания.",
            "Вау, забавно, секунду.",
            "Хм, заманчиво.",
            "О, это вдохновляет.",
            "Хм, давайте разберёмся.",
            "Интересно, сейчас отвечу.",
            "Хм, это крутой вопрос.",
        ],
        "en": [
            "Hmm, interesting question...",
            "That's intriguing, let me think.",
            "Wow, that deserves some thought.",
            "Hmm, curious topic.",
            "Fascinating, let's figure this out.",
            "Hmm, good point to ponder.",
            "Whoa, that makes me think.",
            "Hmm, unusual request.",
            "Neat, let's mull it over.",
            "Hmm, worth considering.",
            "Oh, interesting idea.",
            "Hmm, let's think together.",
            "Wow, cool, just a sec.",
            "Hmm, tempting thought.",
            "Curious, I'll respond soon.",
            "Hmm, this needs attention.",
            "Oh, fun question.",
            "Hmm, let's break it down.",
            "Interesting, what do you mean?",
            "Hmm, this inspires an answer.",
            "Uh, tricky but interesting.",
            "Hmm, let me ponder.",
            "Neat, gathering thoughts.",
            "Hmm, fresh perspective.",
            "Whoa, let's dive in.",
            "Hmm, appealing topic.",
            "Curious, wait a moment.",
            "Hmm, worth discussing.",
            "Wow, interesting twist.",
            "Hmm, let me reflect.",
            "Neat, just a second.",
            "Hmm, this sparks interest.",
            "Oh, cool, responding now.",
            "Hmm, unique idea.",
            "Intriguing, let's unpack.",
            "Hmm, nice question.",
            "Whoa, that hooked me.",
            "Hmm, let's think deeper.",
            "Neat, thinking now.",
            "Hmm, this motivates.",
            "Whoa, interesting puzzle.",
            "Hmm, let me analyze.",
            "Curious, hold on.",
            "Hmm, deserves focus.",
            "Wow, fun, one sec.",
            "Hmm, enticing.",
            "Oh, this inspires.",
            "Hmm, let's sort it out.",
            "Interesting, answering now.",
            "Hmm, that's a great question.",
        ],
    }


def _load_filler_bank() -> Dict[str, List[str]]:
    bank = _default_filler_bank()
    if not JARVIS_FILLER_BANK_USE_FILE:
        return bank
    try:
        if JARVIS_FILLER_BANK_PATH.exists():
            payload = json.loads(JARVIS_FILLER_BANK_PATH.read_text(encoding="utf-8"))
            if isinstance(payload, dict):
                for lang in ("ru", "en"):
                    items = payload.get(lang)
                    if isinstance(items, list):
                        bank[lang] = [str(x).strip() for x in items if str(x).strip()]
    except Exception as e:
        logger.warning(f"[JARVIS] Could not load filler bank: {e}")
    return bank


def _save_filler_bank(bank: Dict[str, List[str]]) -> None:
    try:
        JARVIS_FILLER_BANK_PATH.parent.mkdir(parents=True, exist_ok=True)
        JARVIS_FILLER_BANK_PATH.write_text(
            json.dumps(bank, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except Exception as e:
        logger.warning(f"[JARVIS] Could not save filler bank: {e}")


def _filler_audio_file(lang: str, phrase: str) -> Path:
    key = hashlib.md5(phrase.encode("utf-8")).hexdigest()[:12]
    return JARVIS_FILLER_AUDIO_CACHE_DIR / lang / f"{key}.mp3"


def _store_cached_filler_audio(lang: str, phrase: str, audio_bytes: bytes, audio_format: str = "mp3") -> None:
    if not audio_bytes or len(audio_bytes) < 1024:
        return
    bucket = _filler_audio_cache.setdefault(lang, {})
    bucket[phrase] = (audio_bytes, audio_format)


def _load_cached_filler_audio_from_disk(lang: str, phrase: str) -> Tuple[bytes, str]:
    path = _filler_audio_file(lang, phrase)
    if not path.exists():
        return b"", "mp3"
    try:
        audio = path.read_bytes()
        if audio and len(audio) >= 1024:
            return audio, "mp3"
    except Exception as e:
        logger.debug(f"[JARVIS] Could not read filler audio cache {path}: {e}")
    return b"", "mp3"


async def _warmup_filler_audio_cache_once() -> None:
    global _filler_audio_warmup_started
    if _filler_audio_warmup_started or not JARVIS_FILLER_AUDIO_ENABLE or not JARVIS_FILLER_AUDIO_WARMUP:
        return
    _filler_audio_warmup_started = True

    bank = _load_filler_bank()
    target = {
        "ru": bank.get("ru", [])[:50],
        "en": bank.get("en", [])[:50],
    }
    generated = 0
    loaded = 0

    for lang, phrases in target.items():
        for phrase in phrases:
            if phrase in _filler_audio_cache.get(lang, {}):
                continue
            cached_bytes, cached_fmt = _load_cached_filler_audio_from_disk(lang, phrase)
            if cached_bytes:
                _store_cached_filler_audio(lang, phrase, cached_bytes, cached_fmt)
                loaded += 1
                continue
            if not HAS_FAST_TTS:
                continue
            try:
                _, filler_voice = _resolve_voice_setup()
                tts = FastTTSClient(voice=filler_voice)
                audio = await tts.synthesize(phrase)
                if audio and len(audio) >= 1024:
                    out_path = _filler_audio_file(lang, phrase)
                    out_path.parent.mkdir(parents=True, exist_ok=True)
                    out_path.write_bytes(audio)
                    _store_cached_filler_audio(lang, phrase, audio, "mp3")
                    generated += 1
            except Exception as e:
                logger.debug(f"[JARVIS] filler warmup failed ({lang}): {e}")

    logger.info(
        f"[JARVIS] Filler audio warmup done: loaded={loaded}, generated={generated}, "
        f"ru={len(_filler_audio_cache.get('ru', {}))}, en={len(_filler_audio_cache.get('en', {}))}"
    )


def _detect_language_hint(text: str) -> str:
    t = (text or "").lower()
    cyr = sum(1 for ch in t if "а" <= ch <= "я" or ch == "ё")
    lat = sum(1 for ch in t if "a" <= ch <= "z")
    return "ru" if cyr >= lat else "en"


def _resolve_voice_setup() -> Tuple[str, str]:
    if JARVIS_VOICE_LOCK_EDGE_RU_FEMALE:
        return "ru-female", "ru-female"
    profile = VOICE_PROFILES.get(JARVIS_VOICE_PROFILE, {})
    fast_voice = profile.get("fast_tts_voice") or JARVIS_FAST_TTS_VOICE
    filler_voice = profile.get("filler_voice") or JARVIS_FILLER_AUDIO_VOICE
    return fast_voice, filler_voice


def _language_stage_hint(transcript: str, context: Dict[str, Any]) -> str:
    """
    Memory-driven language guidance without hard lock.
    Priority: Engram preference -> STT transcript language.
    """
    preferred_language = ""
    if isinstance(context, dict):
        preferred_language = str(context.get("preferred_language") or "").strip().lower()
    if preferred_language == "ru":
        return "Prefer Russian for this response unless user explicitly asks another language."
    if preferred_language == "en":
        return "Prefer English for this response unless user explicitly asks another language."
    prefers_russian = context.get("prefers_russian") if isinstance(context, dict) else None
    if prefers_russian is True:
        return "Prefer Russian for this response unless user explicitly asks another language."
    if prefers_russian is False:
        return "Prefer English for this response unless user explicitly asks another language."
    inferred = _detect_language_hint(transcript)
    if inferred == "ru":
        return "Prefer the same language as user speech (Russian)."
    return "Prefer the same language as user speech (English)."


def _normalize_text_for_espeak(text: str, lang_hint: str) -> str:
    """
    eSpeak RU pronunciation normalization for key product words.
    """
    out = str(text or "").strip()
    if not out:
        return out
    if lang_hint == "ru":
        out = out.replace("VETKA", "ВЕТКА")
        out = out.replace("Vetka", "Ветка")
        out = out.replace("vetka", "ветка")
    return out


def _select_filler_phrase(partial_input: str) -> str:
    lang = _detect_language_hint(partial_input)
    bank = _load_filler_bank()
    pool = bank.get(lang) or bank.get("ru") or _default_filler_bank()["ru"]
    return random.choice(pool)


def _learn_filler_phrase(partial_input: str, response_text: str) -> None:
    if not JARVIS_PLANB_LEARN_ENABLE:
        return
    now = time.monotonic()
    last_saved = getattr(_learn_filler_phrase, "_last_saved_monotonic", 0.0)
    if now - last_saved < JARVIS_PLANB_LEARN_MIN_INTERVAL_SEC:
        return
    text = (response_text or "").strip()
    if not text:
        return
    first_sentence = text.split(".")[0].split("!")[0].split("?")[0].strip()
    if len(first_sentence) < 8 or len(first_sentence) > 80:
        return
    lang = _detect_language_hint(partial_input)
    bank = _load_filler_bank()
    items = bank.get(lang, [])
    if first_sentence not in items:
        items.append(first_sentence)
        bank[lang] = items[-20:]
        _save_filler_bank(bank)
        setattr(_learn_filler_phrase, "_last_saved_monotonic", now)


def _should_run_stage3(transcript: str, stage2_text: str) -> bool:
    """
    Stage3 is expensive: run only for deep queries or weak stage2 output.
    """
    t = (transcript or "").lower()
    context_sensitive_markers = (
        "как меня зовут",
        "моё имя",
        "мое имя",
        "кто я",
        "что ты видишь",
        "на что я смотрю",
        "what is my name",
        "do you know my name",
        "what do you see",
        "what am i looking at",
    )
    if any(marker in t for marker in context_sensitive_markers):
        return True
    if _is_deep_query(transcript):
        return True
    s2 = (stage2_text or "").strip()
    if not s2:
        return True
    # If stage2 already concise and non-empty, keep low-latency path.
    if len(s2) <= 220 and len(s2.split()) >= 4:
        return False
    return True


def _remember_user_language_preference(user_id: str, lang_hint: str) -> None:
    """
    Persist language preference to Engram so Jarvis keeps RU/EN consistently.
    """
    try:
        from src.memory.engram_user_memory import get_engram_user_memory
        engram = get_engram_user_memory()
        prefers_russian = (lang_hint == "ru")
        engram.set_preference(
            user_id=user_id,
            category="communication_style",
            key="prefers_russian",
            value=prefers_russian,
            confidence=0.9,
        )
    except Exception as e:
        logger.debug(f"[JARVIS] Could not persist language preference: {e}")


def _remember_last_assistant_language(user_id: str, response_text: str) -> None:
    try:
        from src.memory.engram_user_memory import get_engram_user_memory
        engram = get_engram_user_memory()
        lang = _detect_language_hint(response_text)
        engram.set_preference(
            user_id=user_id,
            category="communication_style",
            key="last_assistant_language",
            value=lang,
            confidence=0.9,
        )
    except Exception as e:
        logger.debug(f"[JARVIS] Could not persist last assistant language: {e}")


async def _emit_planb_filler_if_slow(
    *,
    sio,
    sid: str,
    user_id: str,
    partial_input: str,
    ready_event: asyncio.Event,
) -> bool:
    if not JARVIS_PLANB_FILLER_ENABLE:
        return False
    if ready_event.is_set():
        return False
    try:
        await asyncio.wait_for(ready_event.wait(), timeout=max(0.05, JARVIS_PLANB_FILLER_DELAY_SEC))
        return False
    except asyncio.TimeoutError:
        filler = _select_filler_phrase(partial_input)
        lang = _detect_language_hint(partial_input)
        await sio.emit(
            "jarvis_response",
            {
                "text": filler,
                "user_id": user_id,
                "status": "filler",
                "is_draft": True,
            },
            to=sid,
        )
        if JARVIS_FILLER_AUDIO_ENABLE:
            audio_bytes, audio_format = _filler_audio_cache.get(lang, {}).get(filler, (b"", "mp3"))
            if not audio_bytes:
                audio_bytes, audio_format = _load_cached_filler_audio_from_disk(lang, filler)
                if audio_bytes:
                    _store_cached_filler_audio(lang, filler, audio_bytes, audio_format)
            if audio_bytes:
                await sio.emit(
                    "jarvis_audio",
                    {
                        "audio": base64.b64encode(audio_bytes).decode("utf-8"),
                        "format": audio_format,
                        "user_id": user_id,
                        "status": "filler",
                    },
                    to=sid,
                )
        logger.info(f"[JARVIS] PlanB filler emitted ({lang}): {filler}")
        return True


def _is_deep_query(transcript: str) -> bool:
    t = (transcript or "").lower()
    if len(t.split()) >= 24:
        return True
    keywords = (
        "исслед",
        "deep",
        "подроб",
        "прочитай",
        "проанализ",
        "compare",
        "benchmark",
        "пошагов",
        "architecture",
        "архитект",
    )
    return any(k in t for k in keywords)


async def _generate_stage_response(
    *,
    llm,
    transcript: str,
    user_id: str,
    context: Dict[str, Any],
    model_id: str,
    stage_hint: str,
    timeout_ms: Optional[int] = None,
) -> str:
    local_context = dict(context or {})
    local_context["llm_model"] = model_id
    prompt = f"{stage_hint}\n\nUser input: {transcript}".strip()
    try:
        if timeout_ms and timeout_ms > 0:
            result = await asyncio.wait_for(
                llm.generate(prompt, user_id, local_context),
                timeout=timeout_ms / 1000.0,
            )
            return str(result or "").strip()
        return (await llm.generate(prompt, user_id, local_context)).strip()
    except asyncio.TimeoutError:
        logger.info(f"[JARVIS][Stage] {model_id} timeout after {timeout_ms}ms")
        return ""
    except Exception as e:
        logger.warning(f"[JARVIS][Stage] {model_id} failed: {e}")
        return ""


class JarvisState(str, Enum):
    """Jarvis session states"""
    IDLE = "idle"
    LISTENING = "listening"
    THINKING = "thinking"
    SPEAKING = "speaking"


# VAD Configuration
VAD_SILENCE_THRESHOLD = 500  # RMS energy threshold (lower = more sensitive)
VAD_SILENCE_DURATION = 1.5   # Seconds of silence to trigger auto-stop
VAD_MIN_SPEECH_DURATION = 0.5  # Minimum speech before allowing auto-stop


def calculate_audio_energy(pcm_bytes: bytes) -> float:
    """Calculate RMS energy of PCM audio chunk."""
    if len(pcm_bytes) < 2:
        return 0.0
    # Convert bytes to int16 array
    audio_array = np.frombuffer(pcm_bytes, dtype=np.int16)
    if len(audio_array) == 0:
        return 0.0
    # Calculate RMS
    rms = np.sqrt(np.mean(audio_array.astype(np.float32) ** 2))
    return rms


@dataclass
class JarvisSession:
    """
    Jarvis voice session state

    Attributes:
        user_id: Unique user identifier
        state: Current state in the state machine
        audio_buffer: Accumulated PCM audio chunks during listening
        sample_rate: Audio sample rate (default 16000 Hz)
        transcript: Latest STT transcript
        response_text: Latest AI response text
        silence_start: Timestamp when silence started (for VAD)
        has_speech: Whether speech has been detected
        total_duration: Total audio duration in seconds
        stt_confidence: STT transcription confidence (MARKER_105_EDGE_CASES)
        prediction_confidence: T9 prediction confidence (MARKER_105_EDGE_CASES)
        is_interrupted: Whether session was interrupted (MARKER_105_EDGE_CASES)
    """
    user_id: str
    state: JarvisState = JarvisState.IDLE
    audio_buffer: List[bytes] = field(default_factory=list)
    sample_rate: int = 16000
    transcript: str = ""
    response_text: str = ""
    silence_start: Optional[float] = None
    has_speech: bool = False
    total_duration: float = 0.0
    # MARKER_105_EDGE_CASES: Additional fields for edge case handling
    stt_confidence: float = 1.0
    prediction_confidence: float = 1.0
    is_interrupted: bool = False
    client_context: Dict[str, Any] = field(default_factory=dict)

    def reset_buffer(self):
        """Clear audio buffer and VAD state"""
        self.audio_buffer = []
        self.silence_start = None
        self.has_speech = False
        self.total_duration = 0.0
        # MARKER_105_EDGE_CASES: Reset edge case fields
        self.stt_confidence = 1.0
        self.prediction_confidence = 1.0
        self.is_interrupted = False

    def add_audio_chunk(self, chunk: bytes):
        """Add PCM chunk and update duration."""
        self.audio_buffer.append(chunk)
        self.total_duration += len(chunk) / 2 / self.sample_rate

    def get_full_audio(self) -> bytes:
        """Get concatenated PCM from current session."""
        return b"".join(self.audio_buffer)


def _extract_client_context(data: Dict[str, Any]) -> Dict[str, Any]:
    """Extract bounded Jarvis context payload from socket event data."""
    if not isinstance(data, dict):
        return {}

    context: Dict[str, Any] = {}

    viewport_context = data.get("viewport_context")
    if isinstance(viewport_context, dict):
        compact_viewport: Dict[str, Any] = {}
        for key in ("zoom_level", "total_visible", "total_pinned", "camera_position", "camera_target"):
            if key in viewport_context:
                compact_viewport[key] = viewport_context.get(key)

        def _compact_nodes(nodes: Any, limit: int) -> List[Dict[str, Any]]:
            if not isinstance(nodes, list):
                return []
            compact: List[Dict[str, Any]] = []
            for node in nodes[: max(1, limit)]:
                if not isinstance(node, dict):
                    continue
                compact.append(
                    {
                        "id": node.get("id"),
                        "name": node.get("name"),
                        "path": node.get("path"),
                        "type": node.get("type"),
                        "lod_level": node.get("lod_level"),
                        "distance_to_camera": node.get("distance_to_camera"),
                        "is_center": node.get("is_center"),
                        "is_pinned": node.get("is_pinned"),
                    }
                )
            return compact

        compact_viewport["pinned_nodes"] = _compact_nodes(
            viewport_context.get("pinned_nodes"),
            JARVIS_CONTEXT_MAX_PINNED,
        )
        compact_viewport["viewport_nodes"] = _compact_nodes(
            viewport_context.get("viewport_nodes"),
            JARVIS_CONTEXT_MAX_VIEWPORT,
        )
        context["viewport_context"] = compact_viewport

    pinned_files = data.get("pinned_files")
    if isinstance(pinned_files, list):
        compact_pinned = []
        for item in pinned_files[: max(1, JARVIS_CONTEXT_MAX_PINNED)]:
            if isinstance(item, dict):
                compact_pinned.append(
                    {
                        "id": item.get("id"),
                        "name": item.get("name"),
                        "path": item.get("path"),
                        "type": item.get("type"),
                    }
                )
            else:
                compact_pinned.append({"path": str(item)})
        context["pinned_files"] = compact_pinned

    open_chat_context = data.get("open_chat_context")
    if isinstance(open_chat_context, dict):
        messages = open_chat_context.get("messages")
        if isinstance(messages, list):
            compact_messages = []
            for msg in messages[-max(1, JARVIS_CONTEXT_MAX_CHAT_MESSAGES):]:
                if not isinstance(msg, dict):
                    continue
                compact_messages.append(
                    {
                        "role": msg.get("role"),
                        "content": str(msg.get("content") or "")[:220],
                        "timestamp": msg.get("timestamp"),
                    }
                )
            open_chat_context = {**open_chat_context, "messages": compact_messages}
        context["open_chat_context"] = open_chat_context

    cam_context = data.get("cam_context")
    if isinstance(cam_context, dict):
        context["cam_context"] = cam_context

    llm_model = data.get("llm_model")
    if isinstance(llm_model, str) and llm_model.strip():
        context["llm_model"] = llm_model.strip()

    # MARKER_157_7_2_VOICE_STATE_KEY_FIELDS.V1:
    # Drill/state fields (MYCO-style) for state-key retrieval in voice path.
    state_keys = (
        "nav_level",
        "navLevel",
        "task_drill_state",
        "taskDrillState",
        "roadmap_node_drill_state",
        "roadmapNodeDrillState",
        "workflow_inline_expanded",
        "workflowInlineExpanded",
        "roadmap_node_inline_expanded",
        "roadmapNodeInlineExpanded",
        "node_kind",
        "nodeKind",
        "active_task_id",
        "activeTaskId",
        "role",
        "label",
        "node_id",
        "nodeId",
    )
    for key in state_keys:
        if key in data and data.get(key) is not None:
            context[key] = data.get(key)

    return context


# Active sessions: sid -> JarvisSession
_active_sessions: Dict[str, JarvisSession] = {}


def register_jarvis_handlers(sio):
    """
    Register Jarvis voice interface Socket.IO event handlers

    Args:
        sio: SocketIO instance from main API setup
    """
    if JARVIS_FILLER_AUDIO_ENABLE and JARVIS_FILLER_AUDIO_WARMUP:
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(_warmup_filler_audio_cache_once())
        except Exception as e:
            logger.debug(f"[JARVIS] Filler warmup scheduling skipped: {e}")

    @sio.event
    async def jarvis_listen_start(sid, data):
        """
        Client starts voice input session

        Expected data: {user_id: str}
        Emits: jarvis_state with state='listening'
        """
        try:
            user_id = data.get('user_id')
            if not user_id:
                logger.error(f"[JARVIS] Missing user_id in jarvis_listen_start from {sid}")
                return

            # Create or reset session
            session = JarvisSession(user_id=user_id)
            session.state = JarvisState.LISTENING
            session.reset_buffer()
            session.client_context = _extract_client_context(data)

            _active_sessions[sid] = session

            logger.info(f"[JARVIS] Listen started for user {user_id}, sid={sid}")

            # Notify client of state change
            await sio.emit('jarvis_state', {
                'state': JarvisState.LISTENING,
                'user_id': user_id
            }, to=sid)

        except Exception as e:
            logger.error(f"[JARVIS] Error in jarvis_listen_start: {e}", exc_info=True)
            await sio.emit('jarvis_error', {
                'error': str(e),
                'event': 'jarvis_listen_start'
            }, to=sid)


    @sio.event
    async def jarvis_audio_chunk(sid, data):
        """
        Receive audio chunk during listening

        Expected data: {audio: bytes, sample_rate: int}
        Accumulates audio in session buffer
        """
        try:
            session = _active_sessions.get(sid)
            if not session:
                logger.warning(f"[JARVIS] No active session for sid={sid} in jarvis_audio_chunk")
                return

            if session.state != JarvisState.LISTENING:
                logger.debug(
                    f"[JARVIS] Ignoring audio chunk in state={session.state} for sid={sid}"
                )
                return

            audio_bytes = data.get('audio')
            sample_rate = data.get('sample_rate', 16000)

            if not audio_bytes:
                logger.warning(f"[JARVIS] Empty audio chunk from sid={sid}")
                return

            # Update sample rate if provided
            if sample_rate != session.sample_rate:
                session.sample_rate = sample_rate

            # Add to buffer
            session.add_audio_chunk(audio_bytes)

            # VAD: Check audio energy for silence detection
            import time
            energy = calculate_audio_energy(audio_bytes)
            current_time = time.time()

            if energy > VAD_SILENCE_THRESHOLD:
                # Speech detected
                session.has_speech = True
                session.silence_start = None
                logger.debug(f"[JARVIS VAD] Speech detected, energy={energy:.0f}")
            else:
                # Silence detected
                if session.silence_start is None:
                    session.silence_start = current_time
                    logger.debug(f"[JARVIS VAD] Silence started, energy={energy:.0f}")

                # Check if silence duration exceeded threshold
                silence_duration = current_time - session.silence_start
                if (session.has_speech and
                    session.total_duration >= VAD_MIN_SPEECH_DURATION and
                    silence_duration >= VAD_SILENCE_DURATION):
                    # Auto-stop: User finished speaking
                    logger.info(f"[JARVIS VAD] Auto-stop triggered after {silence_duration:.1f}s silence, "
                               f"total duration: {session.total_duration:.1f}s")

                    # Emit auto-stop event to client
                    await sio.emit('jarvis_auto_stop', {
                        'user_id': session.user_id,
                        'silence_duration': silence_duration
                    }, to=sid)

                    # Trigger the same pipeline as manual stop
                    await jarvis_listen_stop(sid, {'user_id': session.user_id})
                    return

        except Exception as e:
            logger.error(f"[JARVIS] Error in jarvis_audio_chunk: {e}", exc_info=True)
            await sio.emit('jarvis_error', {
                'error': str(e),
                'event': 'jarvis_audio_chunk'
            }, to=sid)


    @sio.event
    async def jarvis_listen_stop(sid, data):
        """
        Client stops voice input - trigger STT -> AI -> TTS pipeline

        Expected data: {user_id: str}
        Emits: jarvis_state, jarvis_transcript, jarvis_response, jarvis_audio
        """
        try:
            session = _active_sessions.get(sid)
            if not session:
                logger.warning(f"[JARVIS] No active session for sid={sid} in jarvis_listen_stop")
                return

            turn_start = time.perf_counter()
            stage_hits: List[str] = []
            stage_models: Dict[str, str] = {}
            first_response_ms: Optional[float] = None
            tts_provider = "none"
            tts_audio_format = "none"
            tts_duration_ms: Optional[float] = None
            tts_ok = False

            user_id = data.get('user_id')
            transcript_hint = (data.get('transcript_hint') or '').strip()
            if user_id != session.user_id:
                logger.warning(
                    f"[JARVIS] User ID mismatch: session={session.user_id}, data={user_id}"
                )

            stop_context = _extract_client_context(data)
            if stop_context:
                session.client_context.update(stop_context)

            logger.info(
                f"[JARVIS] Listen stopped for user {session.user_id}, "
                f"buffer size: {len(session.get_full_audio())} bytes, sid={sid}"
            )
            logger.info(
                f"[JARVIS] Stage machine enabled={JARVIS_STAGE_MACHINE_ENABLE}, "
                f"context_keys={list(session.client_context.keys())}"
            )

            # Transition to THINKING state
            session.state = JarvisState.THINKING
            await sio.emit('jarvis_state', {
                'state': JarvisState.THINKING,
                'user_id': session.user_id
            }, to=sid)

            # STT: Convert PCM buffer to WAV and transcribe with Whisper
            audio_data = session.get_full_audio()

            # MARKER_105_EDGE_CASES: Track STT confidence
            stt_confidence = 1.0  # Default high confidence

            if len(audio_data) < 1000:
                logger.warning(f"[JARVIS] Audio buffer too small: {len(audio_data)} bytes")
                if transcript_hint:
                    transcript = transcript_hint
                    stt_confidence = 0.78
                    logger.info("[JARVIS] Using transcript_hint due to small audio buffer")
                else:
                    transcript = ""
                    stt_confidence = 0.0
            elif HAS_MLX_WHISPER:
                # Convert Int16 PCM to WAV file for Whisper
                try:
                    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp_file:
                        tmp_path = tmp_file.name
                        with wave.open(tmp_file, 'wb') as wav_file:
                            wav_file.setnchannels(1)
                            wav_file.setsampwidth(2)  # 16-bit
                            wav_file.setframerate(session.sample_rate)
                            wav_file.writeframes(audio_data)

                    # Transcribe with MLX Whisper
                    logger.info(f"[JARVIS] Transcribing {len(audio_data)} bytes of audio...")
                    result = mlx_whisper.transcribe(
                        tmp_path,
                        path_or_hf_repo="mlx-community/whisper-base-mlx",
                        language=None  # auto-detect
                    )
                    transcript = result.get("text", "").strip()

                    # MARKER_105_EDGE_CASES: Extract STT confidence from Whisper
                    # Whisper returns segments with avg_logprob, use that as confidence
                    segments = result.get("segments", [])
                    if segments:
                        # Average the no_speech_prob inverse as confidence
                        # Lower no_speech_prob = higher confidence
                        avg_no_speech = sum(s.get("no_speech_prob", 0.5) for s in segments) / len(segments)
                        stt_confidence = 1.0 - avg_no_speech

                        # Also factor in compression ratio (too high = likely garbage)
                        avg_compression = sum(s.get("compression_ratio", 1.0) for s in segments) / len(segments)
                        if avg_compression > 2.4:  # Whisper's hallucination threshold
                            stt_confidence *= 0.5

                        logger.info(f"[JARVIS] STT confidence: {stt_confidence:.2f} (no_speech: {avg_no_speech:.2f})")
                    else:
                        stt_confidence = 0.8 if transcript else 0.0

                    logger.info(f"[JARVIS] STT transcript: {transcript}")

                    # Cleanup temp file
                    Path(tmp_path).unlink(missing_ok=True)

                except Exception as e:
                    logger.error(f"[JARVIS] STT failed: {e}")
                    if transcript_hint:
                        transcript = transcript_hint
                        stt_confidence = 0.72
                        logger.info("[JARVIS] Using transcript_hint due to STT failure")
                    else:
                        transcript = "[STT Error]"
                        stt_confidence = 0.0
            else:
                if transcript_hint:
                    logger.info("[JARVIS] No STT engine, using transcript_hint from client")
                    transcript = transcript_hint
                    stt_confidence = 0.70
                else:
                    # Fallback to shared realtime STT chain (gemini/openai/deepgram/whisper local)
                    # so Jarvis can still work when mlx_whisper is missing.
                    try:
                        from src.api.handlers.voice_realtime_providers import stt_from_pcm_bytes
                        transcript = (await stt_from_pcm_bytes(audio_data, provider="gemini")).strip()
                        if transcript:
                            logger.info("[JARVIS] STT from realtime provider fallback")
                            stt_confidence = 0.62
                        else:
                            logger.warning("[JARVIS] No STT engine available and realtime fallback returned empty")
                            transcript = "[No STT available]"
                            stt_confidence = 0.0
                    except Exception as e:
                        logger.warning(f"[JARVIS] No STT engine and realtime fallback failed: {e}")
                        transcript = "[No STT available]"
                        stt_confidence = 0.0

            session.transcript = transcript
            session.stt_confidence = stt_confidence

            # If server-side STT is uncertain but browser hint exists, prefer hint.
            if transcript_hint and stt_confidence < T9_STT_CONFIDENCE_THRESHOLD:
                transcript = transcript_hint
                stt_confidence = max(stt_confidence, 0.75)
                session.transcript = transcript
                session.stt_confidence = stt_confidence
                logger.info("[JARVIS] Replaced low-confidence STT with transcript_hint")

            logger.info(f"[JARVIS] STT transcript: {transcript} (confidence: {stt_confidence:.2f})")
            _remember_user_language_preference(session.user_id, _detect_language_hint(transcript))

            # MARKER_105_EDGE_CASES: Check STT edge cases before proceeding
            edge_response, edge_status = await handle_prediction_edge_cases(
                partial_input=transcript,
                prediction_confidence=1.0,  # Will be updated after LLM
                stt_confidence=stt_confidence,
                is_interrupted=session.is_interrupted
            )

            if edge_status == T9PredictionStatus.STT_RETRY:
                # Audio unclear, ask to repeat
                logger.info(f"[JARVIS] Edge case: {edge_status.value}")
                await sio.emit('jarvis_transcript', {
                    'text': transcript,
                    'user_id': session.user_id,
                    'confidence': stt_confidence,
                    'status': edge_status.value
                }, to=sid)
                await sio.emit('jarvis_response', {
                    'text': edge_response,
                    'user_id': session.user_id,
                    'status': edge_status.value
                }, to=sid)
                first_response_ms = round((time.perf_counter() - turn_start) * 1000, 1)
                # Reset and return to idle
                session.state = JarvisState.IDLE
                session.reset_buffer()
                await sio.emit('jarvis_state', {
                    'state': JarvisState.IDLE,
                    'user_id': session.user_id
                }, to=sid)
                _append_jarvis_trace({
                    "ts": time.time(),
                    "sid": sid,
                    "user_id": session.user_id,
                    "stt_lang": _detect_language_hint(transcript),
                    "stt_confidence": round(stt_confidence, 3),
                    "status": edge_status.value,
                    "stages": stage_hits,
                    "stage_models": stage_models,
                    "first_response_ms": first_response_ms,
                    "tts_provider": tts_provider,
                    "tts_audio_format": tts_audio_format,
                    "tts_duration_ms": tts_duration_ms,
                    "tts_ok": tts_ok,
                })
                return

            if edge_status == T9PredictionStatus.WAITING_FOR_INPUT:
                # Too few words, notify client but don't respond
                logger.info(f"[JARVIS] Edge case: waiting for more input")
                await sio.emit('jarvis_transcript', {
                    'text': transcript,
                    'user_id': session.user_id,
                    'confidence': stt_confidence,
                    'status': edge_status.value
                }, to=sid)
                # Reset and return to idle
                session.state = JarvisState.IDLE
                session.reset_buffer()
                await sio.emit('jarvis_state', {
                    'state': JarvisState.IDLE,
                    'user_id': session.user_id
                }, to=sid)
                _append_jarvis_trace({
                    "ts": time.time(),
                    "sid": sid,
                    "user_id": session.user_id,
                    "stt_lang": _detect_language_hint(transcript),
                    "stt_confidence": round(stt_confidence, 3),
                    "status": edge_status.value,
                    "stages": stage_hits,
                    "stage_models": stage_models,
                    "first_response_ms": first_response_ms,
                    "tts_provider": tts_provider,
                    "tts_audio_format": tts_audio_format,
                    "tts_duration_ms": tts_duration_ms,
                    "tts_ok": tts_ok,
                })
                return

            await sio.emit('jarvis_transcript', {
                'text': transcript,
                'user_id': session.user_id,
                'confidence': stt_confidence,
                'status': 'processing'
            }, to=sid)

            # AI Response: Phase 157.3.1 stage-machine (Chunk1/2/3/4)
            response_status = T9PredictionStatus.CONFIDENT

            if _is_hallucination(transcript):
                logger.warning("[JARVIS] Detected STT hallucination, ignoring")
                response_text = "I couldn't understand that clearly. Could you try again?"
            elif not transcript or transcript.startswith("["):
                response_text = "I didn't catch that. Could you please repeat?"
            elif HAS_LLM:
                try:
                    llm_start = time.perf_counter()
                    llm = get_jarvis_llm()
                    context = await get_jarvis_context(
                        session.user_id,
                        transcript,
                        extra_context=session.client_context,
                        session_id=sid,
                    )

                    stage_ready = asyncio.Event()
                    filler_task = asyncio.create_task(
                        _emit_planb_filler_if_slow(
                            sio=sio,
                            sid=sid,
                            user_id=session.user_id,
                            partial_input=transcript,
                            ready_event=stage_ready,
                        )
                    )

                    stage2_text = ""
                    stage3_text = ""
                    stage4_text = ""
                    lang_hint = _language_stage_hint(transcript, context)

                    if JARVIS_STAGE_MACHINE_ENABLE:
                        stage_hits.append("chunk2_fast")
                        await sio.emit("jarvis_stage", {"stage": "chunk2_fast", "user_id": session.user_id}, to=sid)
                        stage_models["chunk2_fast"] = JARVIS_STAGE2_MODEL
                        stage2_text = await _generate_stage_response(
                            llm=llm,
                            transcript=transcript,
                            user_id=session.user_id,
                            context=context,
                            model_id=JARVIS_STAGE2_MODEL,
                            stage_hint=f"{lang_hint} Give a quick, concise spoken response. 1-2 short sentences.",
                            timeout_ms=JARVIS_STAGE2_TIMEOUT_MS,
                        )
                        if stage2_text:
                            stage_ready.set()
                            await sio.emit(
                                "jarvis_response",
                                {
                                    "text": stage2_text,
                                    "user_id": session.user_id,
                                    "status": "stage2_draft",
                                    "is_draft": True,
                                },
                                to=sid,
                            )
                            if first_response_ms is None:
                                first_response_ms = round((time.perf_counter() - turn_start) * 1000, 1)

                        if _should_run_stage3(transcript, stage2_text):
                            stage_hits.append("chunk3_smart")
                            await sio.emit("jarvis_stage", {"stage": "chunk3_smart", "user_id": session.user_id}, to=sid)
                            stage3_candidates = [JARVIS_STAGE3_PRIMARY_MODEL, JARVIS_STAGE3_SECONDARY_MODEL]
                            for candidate in stage3_candidates:
                                if not candidate or candidate == JARVIS_STAGE2_MODEL:
                                    continue
                                stage_models["chunk3_smart"] = candidate
                                stage3_prompt = (
                                    f"Draft answer: {stage2_text}\n\n"
                                    f"Refine this for correctness and relevance to VETKA context. "
                                    f"Return a concise spoken response in user's language."
                                )
                                stage3_text = await _generate_stage_response(
                                    llm=llm,
                                    transcript=f"{transcript}\n\n{stage3_prompt}",
                                    user_id=session.user_id,
                                    context=context,
                                    model_id=candidate,
                                    stage_hint=f"{lang_hint} You are stage-3 smart refinement.",
                                    timeout_ms=JARVIS_STAGE3_TIMEOUT_MS,
                                )
                                if stage3_text:
                                    break

                        if JARVIS_STAGE4_ENABLE and _is_deep_query(transcript):
                            stage4_model = JARVIS_STAGE4_MODEL or str(context.get("llm_model") or "").strip()
                            if stage4_model and stage4_model not in {JARVIS_STAGE2_MODEL, JARVIS_STAGE3_PRIMARY_MODEL, JARVIS_STAGE3_SECONDARY_MODEL}:
                                stage_hits.append("chunk4_deep")
                                await sio.emit("jarvis_stage", {"stage": "chunk4_deep", "user_id": session.user_id}, to=sid)
                                stage_models["chunk4_deep"] = stage4_model
                                stage4_text = await _generate_stage_response(
                                    llm=llm,
                                    transcript=f"{transcript}\n\nKeep it concise but include essential deep findings.",
                                    user_id=session.user_id,
                                    context=context,
                                    model_id=stage4_model,
                                    stage_hint=f"{lang_hint} You are stage-4 deep follow-up.",
                                    timeout_ms=JARVIS_STAGE4_TIMEOUT_MS,
                                )

                        response_text = stage4_text or stage3_text or stage2_text
                        if not response_text:
                            response_text = "I heard you. Give me one more second and ask again."
                            response_status = T9PredictionStatus.TIMEOUT_FALLBACK
                    else:
                        async def _generate_llm_response(text: str) -> str:
                            return await llm.generate(text, session.user_id, context)

                        result = await timeout_wrapped_prediction(
                            predict_func=_generate_llm_response,
                            partial_input=transcript,
                            timeout_ms=JARVIS_LLM_TIMEOUT_MS,
                        )
                        if isinstance(result, tuple):
                            response_text, response_status = result
                        else:
                            response_text = result

                    stage_ready.set()
                    filler_emitted = False
                    try:
                        filler_emitted = await filler_task
                    except Exception:
                        filler_emitted = False
                    if filler_emitted and first_response_ms is None:
                        first_response_ms = round((time.perf_counter() - turn_start) * 1000, 1)

                    llm_duration = time.perf_counter() - llm_start
                    logger.info(f"[JARVIS] Stage response in {llm_duration:.2f}s: {response_text[:120]}...")
                    _learn_filler_phrase(transcript, response_text)
                    _remember_last_assistant_language(session.user_id, response_text)

                    try:
                        from src.memory.stm_buffer import get_stm_buffer
                        stm = get_stm_buffer()
                        stm.add_message(f"User: {transcript}", source="user")
                        stm.add_message(f"VETKA: {response_text}", source="agent")
                    except Exception as e:
                        logger.warning(f"[JARVIS] Could not store in STM: {e}")

                except Exception as e:
                    logger.error(f"[JARVIS] LLM failed: {e}", exc_info=True)
                    response_text = f"I heard you say: {transcript}. I'm having trouble with my language model."
                    response_status = T9PredictionStatus.TIMEOUT_FALLBACK
            else:
                response_text = f"I heard you say: {transcript}"

            session.response_text = response_text

            logger.info(f"[JARVIS] AI response ({response_status.value}): {response_text}")
            await sio.emit('jarvis_response', {
                'text': response_text,
                'user_id': session.user_id,
                'status': response_status.value,
                'is_draft': response_status == T9PredictionStatus.LOW_CONFIDENCE_DRAFT
            }, to=sid)

            # Transition to SPEAKING state
            session.state = JarvisState.SPEAKING
            await sio.emit('jarvis_state', {
                'state': JarvisState.SPEAKING,
                'user_id': session.user_id
            }, to=sid)

            # TTS: Synthesize response
            # Phase 104.7: Fast TTS (Edge-TTS ~1s) or Quality TTS (Qwen3 ~5-6s)
            if HAS_TTS and response_text:
                try:
                    tts_start = time.perf_counter()
                    emitted_audio_format = "unknown"
                    emitted_audio_bytes = b""
                    lang_hint = _detect_language_hint(f"{transcript}\n{response_text}")
                    tts_language = "Russian" if lang_hint == "ru" else "English"
                    use_fast_tts = HAS_FAST_TTS and (JARVIS_VOICE_LOCK_EDGE_RU_FEMALE or TTS_MODE == "fast" or lang_hint == "ru")
                    logger.info(
                        f"[JARVIS] TTS start mode={'fast' if use_fast_tts else 'quality'} "
                        f"lang={tts_language} chars={len(response_text)}"
                    )

                    if use_fast_tts:
                        preferred_provider = "edge" if JARVIS_VOICE_LOCK_EDGE_RU_FEMALE else (
                            JARVIS_TTS_PROVIDER if JARVIS_TTS_PROVIDER in {"edge", "espeak"} else "auto"
                        )
                        fast_voice, _ = _resolve_voice_setup()
                        espeak_voice = JARVIS_ESPEAK_VOICE_RU if lang_hint == "ru" else JARVIS_ESPEAK_VOICE_EN

                        async def _edge_synth() -> bytes:
                            if not HAS_FAST_TTS:
                                return b""
                            fast_tts = FastTTSClient(voice=fast_voice)
                            return await fast_tts.synthesize_auto(response_text)

                        async def _espeak_synth() -> bytes:
                            if not HAS_ESPEAK_TTS:
                                return b""
                            normalized_text = _normalize_text_for_espeak(response_text, lang_hint)
                            espeak = ESpeakTTSClient(
                                voice=espeak_voice,
                                rate=JARVIS_ESPEAK_RATE,
                                pitch=JARVIS_ESPEAK_PITCH,
                                amplitude=JARVIS_ESPEAK_AMPLITUDE,
                                preset=JARVIS_ESPEAK_PRESET,
                            )
                            return await espeak.synthesize(normalized_text)

                        audio_bytes = b""
                        if preferred_provider == "edge":
                            tts_provider = "fast_tts_edge"
                            audio_bytes = await _edge_synth()
                            if (
                                not JARVIS_VOICE_LOCK_EDGE_RU_FEMALE
                                and not audio_bytes
                                and JARVIS_TTS_FALLBACK_PROVIDER == "espeak"
                            ):
                                tts_provider = "espeak_tts_fallback"
                                audio_bytes = await _espeak_synth()
                        elif preferred_provider == "espeak":
                            tts_provider = "espeak_tts"
                            audio_bytes = await _espeak_synth()
                            if not audio_bytes and JARVIS_TTS_FALLBACK_PROVIDER == "edge":
                                tts_provider = "fast_tts_edge_fallback"
                                audio_bytes = await _edge_synth()
                        else:
                            # auto: edge first, then espeak fallback
                            tts_provider = "fast_tts_edge_auto"
                            audio_bytes = await _edge_synth()
                            if not audio_bytes:
                                tts_provider = "espeak_tts_auto_fallback"
                                audio_bytes = await _espeak_synth()

                        tts_duration = time.perf_counter() - tts_start

                        if audio_bytes:
                            detected = _detect_audio_format(audio_bytes)
                            if detected in {"mp3", "wav"}:
                                emitted_audio_bytes = audio_bytes
                                emitted_audio_format = detected
                            elif detected == "pcm":
                                emitted_audio_bytes = pcm_to_wav(audio_bytes, sample_rate=24000)
                                emitted_audio_format = "wav"
                            if emitted_audio_bytes and len(emitted_audio_bytes) >= 2048:
                                audio_base64 = base64.b64encode(emitted_audio_bytes).decode('utf-8')
                                audio_format = emitted_audio_format
                                tts_audio_format = emitted_audio_format
                                logger.info(
                                    f"[JARVIS] FastTTS in {tts_duration:.2f}s, raw_fmt={detected}, "
                                    f"emit_fmt={audio_format}, bytes={len(emitted_audio_bytes)}"
                                )
                            else:
                                logger.warning("[JARVIS] FastTTS produced invalid/too small audio, skipping emit")
                                audio_base64 = ""
                                audio_format = "mp3"
                        else:
                            audio_base64 = ""
                            audio_format = 'mp3'
                    else:
                        tts_provider = "qwen3_tts"
                        # Quality mode: Qwen3-TTS (~5-6s latency, better voice)
                        tts_client = Qwen3TTSClient(server_url="http://127.0.0.1:5003")
                        audio_bytes = await tts_client.synthesize(
                            text=response_text,
                            language=tts_language,
                            speaker="ryan"
                        )
                        await tts_client.close()

                        tts_duration = time.perf_counter() - tts_start

                        if audio_bytes:
                            detected = _detect_audio_format(audio_bytes)
                            if detected == "wav":
                                emitted_audio_bytes = audio_bytes
                                emitted_audio_format = "wav"
                            elif detected == "mp3":
                                emitted_audio_bytes = audio_bytes
                                emitted_audio_format = "mp3"
                            else:
                                emitted_audio_bytes = pcm_to_wav(audio_bytes, sample_rate=24000)
                                emitted_audio_format = "wav"

                            if emitted_audio_bytes and len(emitted_audio_bytes) >= 2048:
                                audio_base64 = base64.b64encode(emitted_audio_bytes).decode('utf-8')
                                audio_format = emitted_audio_format
                                tts_audio_format = emitted_audio_format
                                logger.info(
                                    f"[JARVIS] Qwen3TTS in {tts_duration:.2f}s, raw_fmt={detected}, "
                                    f"emit_fmt={audio_format}, bytes={len(emitted_audio_bytes)}"
                                )
                            else:
                                logger.warning("[JARVIS] Qwen3TTS produced invalid/too small audio, skipping emit")
                                audio_base64 = ""
                                audio_format = "wav"
                        else:
                            audio_base64 = ""
                            audio_format = 'wav'

                except Exception as e:
                    logger.error(f"[JARVIS] TTS failed: {e}")
                    audio_base64 = ""
                    audio_format = 'mp3'
                    tts_provider = "error"
            else:
                logger.warning("[JARVIS] No TTS available or empty response")
                audio_base64 = ""
                audio_format = 'mp3'

            # Only emit audio if we have it
            if audio_base64:
                await sio.emit('jarvis_audio', {
                    'audio': audio_base64,
                    'format': audio_format,  # 'mp3' for FastTTS, 'wav' for Qwen3
                    'user_id': session.user_id
                }, to=sid)
                logger.info(f"[JARVIS] Emitted jarvis_audio format={audio_format} len={len(audio_base64)}")
                tts_ok = True
            else:
                logger.info("[JARVIS] No audio to emit, skipping jarvis_audio event")
                tts_ok = False

            tts_duration_ms = round((time.perf_counter() - tts_start) * 1000, 1) if HAS_TTS and response_text else None

            # Transition back to IDLE state
            session.state = JarvisState.IDLE
            session.reset_buffer()

            logger.info(f"[JARVIS] Session complete, returning to idle for user {session.user_id}")
            await sio.emit('jarvis_state', {
                'state': JarvisState.IDLE,
                'user_id': session.user_id
            }, to=sid)

            trace_payload = {
                "ts": time.time(),
                "sid": sid,
                "user_id": session.user_id,
                "stt_lang": _detect_language_hint(transcript),
                "stt_confidence": round(stt_confidence, 3),
                "response_lang": _detect_language_hint(response_text),
                "response_status": response_status.value,
                "stages": stage_hits,
                "stage_models": stage_models,
                "context_keys": list((context or {}).keys()) if isinstance(locals().get("context"), dict) else [],
                "context_chars": len(json.dumps(context, ensure_ascii=False)) if isinstance(locals().get("context"), dict) else 0,
                "context_packer": (
                    dict((context or {}).get("context_packer_trace") or {})
                    if isinstance(locals().get("context"), dict)
                    else {}
                ),
                "packing_path": (
                    str(((context or {}).get("context_packer_trace") or {}).get("packing_path") or "")
                    if isinstance(locals().get("context"), dict)
                    else ""
                ),
                "jepa_mode": (
                    bool(((context or {}).get("context_packer_trace") or {}).get("jepa_mode", False))
                    if isinstance(locals().get("context"), dict)
                    else False
                ),
                "jepa_latency_ms": (
                    float(((context or {}).get("context_packer_trace") or {}).get("jepa_latency_ms", 0.0))
                    if isinstance(locals().get("context"), dict)
                    else 0.0
                ),
                "hidden_retrieval_hits": (
                    len(((context or {}).get("hidden_retrieval") or {}).get("items", []))
                    if isinstance(locals().get("context"), dict)
                    and isinstance((context or {}).get("hidden_retrieval"), dict)
                    else 0
                ),
                "state_key_query": (
                    str((context or {}).get("state_key_query") or "")
                    if isinstance(locals().get("context"), dict)
                    else ""
                ),
                "first_response_ms": first_response_ms,
                "total_turn_ms": round((time.perf_counter() - turn_start) * 1000, 1),
                "tts_provider": tts_provider,
                "voice_profile": JARVIS_VOICE_PROFILE,
                "tts_engine": "espeak" if "espeak" in str(tts_provider) else ("edge" if "fast_tts" in str(tts_provider) else "qwen3"),
                "tts_audio_format": tts_audio_format,
                "tts_duration_ms": tts_duration_ms,
                "tts_ok": tts_ok,
            }
            _append_jarvis_trace(trace_payload)
            logger.info(f"[JARVIS][TRACE] {json.dumps(trace_payload, ensure_ascii=False)}")

        except Exception as e:
            logger.error(f"[JARVIS] Error in jarvis_listen_stop: {e}", exc_info=True)

            # Reset to idle on error
            if session:
                session.state = JarvisState.IDLE
                session.reset_buffer()

            await sio.emit('jarvis_error', {
                'error': str(e),
                'event': 'jarvis_listen_stop'
            }, to=sid)
            await sio.emit('jarvis_state', {
                'state': JarvisState.IDLE,
                'user_id': session.user_id if session else 'unknown'
            }, to=sid)


    # MARKER_105_EDGE_CASES: Interrupt handling event
    @sio.event
    async def jarvis_interrupt_request(sid, data):
        """
        Client requests to interrupt current TTS playback.

        MARKER_105_EDGE_CASES: Handle user interrupts during TTS.

        Expected data: {user_id: str, new_input?: str}
        Emits: jarvis_interrupt with cancellation confirmation
        """
        try:
            session = _active_sessions.get(sid)
            if not session:
                logger.warning(f"[JARVIS] No session for interrupt request from {sid}")
                return

            user_id = data.get('user_id', session.user_id)
            new_input = data.get('new_input')

            logger.info(f"[JARVIS] Interrupt requested by {user_id}")

            # Mark session as interrupted
            session.is_interrupted = True

            # Handle the interrupt
            was_interrupted = await handle_jarvis_interrupt(
                sio=sio,
                sid=sid,
                user_id=user_id,
                new_input=new_input
            )

            if was_interrupted:
                # If we had new input, start processing it
                if new_input:
                    logger.info(f"[JARVIS] Restarting with new input: {new_input[:50]}...")
                    # The client should trigger jarvis_listen_start with new input
                    await sio.emit('jarvis_ready_for_input', {
                        'user_id': user_id,
                        'reason': 'interrupt_complete'
                    }, to=sid)
            else:
                logger.debug(f"[JARVIS] No active TTS to interrupt for {user_id}")
                await sio.emit('jarvis_interrupt', {
                    'user_id': user_id,
                    'reason': 'no_active_tts',
                    'new_input': new_input
                }, to=sid)

        except Exception as e:
            logger.error(f"[JARVIS] Error in jarvis_interrupt_request: {e}", exc_info=True)
            await sio.emit('jarvis_error', {
                'error': str(e),
                'event': 'jarvis_interrupt_request'
            }, to=sid)


    @sio.event
    async def disconnect(sid):
        """
        Clean up Jarvis session on client disconnect
        """
        if sid in _active_sessions:
            session = _active_sessions.pop(sid)
            logger.info(f"[JARVIS] Session cleaned up for user {session.user_id}, sid={sid}")
            # MARKER_105_EDGE_CASES: Clean up any active TTS tasks
            unregister_tts_task(sid, session.user_id)


    logger.info("[JARVIS] Voice interface handlers registered successfully")


def get_session(sid: str) -> Optional[JarvisSession]:
    """
    Get active Jarvis session by socket ID

    Args:
        sid: Socket.IO session ID

    Returns:
        JarvisSession if exists, None otherwise
    """
    return _active_sessions.get(sid)


def get_all_sessions() -> Dict[str, JarvisSession]:
    """
    Get all active Jarvis sessions (for debugging/monitoring)

    Returns:
        Dictionary of sid -> JarvisSession
    """
    return _active_sessions.copy()


# =============================================================================
# MARKER_105_PREDICT_DRAFT: T9-like Predictive Response Generation
# =============================================================================

async def _predict_draft(
    partial_input: str,
    context: dict,
    workflow_id: str,
    stream_manager=None
) -> Tuple[str, float]:
    """
    Generate draft response from partial user input (T9-style).

    This function attempts to predict what the user will say and pre-generate
    a response, reducing perceived latency for voice interactions.

    Args:
        partial_input: First 2-3 words from user speech
        context: Dict with stm_summary, arc_suggestions, viewport
        workflow_id: Current workflow ID
        stream_manager: For emitting prediction via Socket.IO

    Returns:
        (predicted_response, confidence) tuple

    Model selection (in order of preference):
        1. Local transformers pipeline (distilgpt2) - fastest
        2. ModelRegistry for fast local Ollama model
        3. Simple template-based prediction - fallback

    Target latency: <1500ms
    """
    start = time.time()

    # Only predict if we have at least 2 words
    words = partial_input.strip().split()
    if len(words) < 2:
        logger.debug(f"[JARVIS_T9] Skipping prediction - only {len(words)} word(s)")
        return ("", 0.0)

    predicted_response = ""
    confidence = 0.0

    try:
        # Build prompt with context
        prompt = _build_prediction_prompt(partial_input, context)

        # Try Option 1: Local transformers pipeline (fastest)
        predicted_response, confidence = await _predict_with_transformers(prompt)

        # If transformers failed or low confidence, try Option 2: Ollama
        if confidence < 0.3:
            predicted_response, confidence = await _predict_with_ollama(prompt)

        # If Ollama also failed, try Option 3: Template-based
        if confidence < 0.3:
            predicted_response, confidence = _predict_with_templates(partial_input, context)

        # Emit prediction via stream_manager if confidence is high enough
        if stream_manager and confidence >= 0.5:
            try:
                await stream_manager.emit_jarvis_prediction(
                    workflow_id=workflow_id,
                    partial_input=partial_input,
                    predicted_response=predicted_response,
                    confidence=confidence
                )
            except Exception as e:
                logger.warning(f"[JARVIS_T9] Failed to emit prediction: {e}")

    except Exception as e:
        logger.error(f"[JARVIS_T9] Prediction error: {e}", exc_info=True)
        predicted_response = ""
        confidence = 0.0

    elapsed_ms = (time.time() - start) * 1000
    logger.info(f"[JARVIS_T9] Draft predicted in {elapsed_ms:.0f}ms, confidence={confidence:.2f}")

    return (predicted_response, confidence)


def _build_prediction_prompt(partial_input: str, context: dict) -> str:
    """
    Build a prompt for draft prediction using context.

    Args:
        partial_input: First few words from user
        context: Dict with stm_summary, arc_suggestions, viewport

    Returns:
        Formatted prompt string
    """
    # Extract context components
    stm_summary = context.get("stm_summary", "")
    arc_suggestions = context.get("arc_suggestions", [])
    viewport = context.get("viewport", {})

    prompt_parts = [
        "You are a voice assistant predicting what the user wants.",
        "User started saying:",
        f'"{partial_input}..."',
        "",
        "Based on context, complete their request and provide a SHORT response (1-2 sentences).",
    ]

    if stm_summary:
        prompt_parts.append(f"\nRecent conversation:\n{stm_summary}")

    if arc_suggestions:
        suggestions_str = ", ".join(arc_suggestions[:3])
        prompt_parts.append(f"\nPossible topics: {suggestions_str}")

    if viewport and viewport.get("current_file"):
        prompt_parts.append(f"\nUser is viewing: {viewport.get('current_file')}")

    prompt_parts.append("\nPredicted response:")

    return "\n".join(prompt_parts)


async def _predict_with_transformers(prompt: str) -> Tuple[str, float]:
    """
    Attempt prediction using local transformers pipeline.

    Uses distilgpt2 for fast local inference.

    Args:
        prompt: The prediction prompt

    Returns:
        (predicted_response, confidence) tuple
    """
    try:
        # Lazy import to avoid startup overhead
        from transformers import pipeline as hf_pipeline

        # Use cached pipeline if available
        if not hasattr(_predict_with_transformers, "_pipeline"):
            logger.info("[JARVIS_T9] Loading distilgpt2 pipeline...")
            _predict_with_transformers._pipeline = hf_pipeline(
                "text-generation",
                model="distilgpt2",
                max_length=50,
                num_return_sequences=1,
                pad_token_id=50256  # Suppress warnings
            )
            logger.info("[JARVIS_T9] distilgpt2 pipeline loaded")

        generator = _predict_with_transformers._pipeline

        # Run in executor to avoid blocking
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            lambda: generator(prompt, max_new_tokens=30, do_sample=True, temperature=0.7)
        )

        if result and len(result) > 0:
            generated = result[0].get("generated_text", "")
            # Extract only the new part after our prompt
            if prompt in generated:
                response = generated[len(prompt):].strip()
            else:
                response = generated.strip()

            # Clean up response
            response = response.split("\n")[0].strip()  # Take first line only

            # Calculate confidence based on response quality
            confidence = 0.0
            if len(response) > 10:
                confidence = 0.5
            if len(response) > 20:
                confidence = 0.6

            return (response[:150], confidence)  # Limit length

    except ImportError:
        logger.debug("[JARVIS_T9] transformers not available")
    except Exception as e:
        logger.warning(f"[JARVIS_T9] Transformers prediction failed: {e}")

    return ("", 0.0)


async def _predict_with_ollama(prompt: str) -> Tuple[str, float]:
    """
    Attempt prediction using Ollama local model.

    Uses fast local models (qwen2.5:3b, phi3:mini) via ModelRegistry.

    Args:
        prompt: The prediction prompt

    Returns:
        (predicted_response, confidence) tuple
    """
    try:
        import aiohttp

        # Fast models for prediction (in order of preference)
        fast_models = ["qwen2.5:3b", "phi3:mini", "qwen2.5vl:3b", "llama3.2:1b"]

        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=2.0)) as session:
            # Check which model is available
            try:
                async with session.get("http://localhost:11434/api/tags") as resp:
                    if resp.status != 200:
                        return ("", 0.0)
                    data = await resp.json()
                    available = [m.get("name", "") for m in data.get("models", [])]
            except Exception:
                return ("", 0.0)

            # Find first available fast model
            selected_model = None
            for model in fast_models:
                if any(model in m for m in available):
                    selected_model = model
                    break

            if not selected_model:
                # Fallback to any available model
                if available:
                    selected_model = available[0]
                else:
                    return ("", 0.0)

            # Generate prediction
            payload = {
                "model": selected_model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "num_predict": 40,  # Very short for speed
                    "temperature": 0.7,
                    "num_ctx": 512,  # Minimal context
                }
            }

            async with session.post(
                "http://localhost:11434/api/generate",
                json=payload
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    response = data.get("response", "").strip()

                    # Clean up response
                    response = response.split("\n")[0].strip()

                    # Calculate confidence
                    confidence = 0.0
                    if len(response) > 10:
                        confidence = 0.5
                    if len(response) > 20:
                        confidence = 0.65

                    return (response[:150], confidence)

    except Exception as e:
        logger.warning(f"[JARVIS_T9] Ollama prediction failed: {e}")

    return ("", 0.0)


def _predict_with_templates(partial_input: str, context: dict) -> Tuple[str, float]:
    """
    Template-based prediction fallback.

    Uses pattern matching for common queries.

    Args:
        partial_input: First few words from user
        context: Context dict

    Returns:
        (predicted_response, confidence) tuple
    """
    partial_lower = partial_input.lower().strip()

    # Common patterns and their template responses
    templates = {
        "what is": ("I can explain that for you. What specifically would you like to know?", 0.5),
        "how do": ("I can help you with that. Let me explain the steps.", 0.5),
        "can you": ("Yes, I can help with that. What would you like me to do?", 0.55),
        "tell me": ("Sure, I'd be happy to tell you about that.", 0.5),
        "show me": ("I can show you that. Let me pull up the relevant information.", 0.5),
        "help me": ("Of course, I'm here to help. What do you need assistance with?", 0.55),
        "where is": ("Let me find that for you.", 0.5),
        "why is": ("That's a good question. Let me explain.", 0.5),
        "create a": ("I can help you create that. Let me set it up.", 0.55),
        "open the": ("Opening that for you now.", 0.6),
        "close the": ("Closing that for you.", 0.6),
        "search for": ("Searching for that now.", 0.6),
        "find the": ("Looking for that in the codebase.", 0.55),
    }

    for pattern, (response, confidence) in templates.items():
        if partial_lower.startswith(pattern):
            return (response, confidence)

    # Check context for more specific predictions
    stm_summary = context.get("stm_summary", "")
    if stm_summary:
        # If user seems to be continuing previous topic
        if "continue" in partial_lower or "more" in partial_lower:
            return ("Continuing from where we left off.", 0.5)
        if "again" in partial_lower or "repeat" in partial_lower:
            return ("Let me repeat that for you.", 0.5)

    # Generic fallback
    return ("I'm listening. Please continue.", 0.35)
