from __future__ import annotations

import asyncio
import base64
import hashlib
import re
from typing import AsyncGenerator, Dict, Iterable

import httpx

from src.voice.qwen_voice_catalog import normalize_qwen_voice_id

_TTS_URL = "http://127.0.0.1:5003/tts/generate"
_SENTENCE_SPLIT_RE = re.compile(r'(?<=[.!?])\s+')
_TOKEN_LIMIT = 120


def _split_sentences(text: str) -> list[str]:
    trimmed = (text or '').strip()
    if not trimmed or len(trimmed) <= 1:
        return []
    sentences = [s.strip() for s in _SENTENCE_SPLIT_RE.split(trimmed) if s.strip()]
    if not sentences:
        sentences = [trimmed]
    return sentences


def _build_payload(sentence: str, speaker: str, language: str, prosody: Dict[str, object] | None) -> Dict[str, object]:
    payload = {
        'text': sentence,
        'speaker': speaker,
        'language': language,
    }
    if isinstance(prosody, dict):
        for key in ('speed', 'pitch', 'energy', 'pause_profile'):
            if prosody.get(key) is not None:
                payload[key] = prosody[key]
    return payload


def _checksum(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class ProgressiveTtsService:
    """Sentence-level progressive TTS generator for solo voice pipeline."""

    def __init__(self, *, tts_url: str | None = None, client_timeout: float = 40.0):
        self.tts_url = tts_url or _TTS_URL
        self.client_timeout = client_timeout

    async def stream_sentences(
        self,
        text: str,
        *,
        speaker: str,
        language: str = 'en',
        prosody: Dict[str, object] | None = None,
        chunk_limit: int = 32,
    ) -> AsyncGenerator[Dict[str, object], None]:
        sentences = _split_sentences(text)
        if not sentences:
            return
        sentences = sentences[:chunk_limit]

        async with httpx.AsyncClient(timeout=self.client_timeout) as client:
            for seq, sentence in enumerate(sentences):
                try:
                    payload = _build_payload(sentence, speaker, language, prosody)
                    response = await client.post(self.tts_url, json=payload)
                    response.raise_for_status()
                    body = response.json() if response.content else {}
                    audio_b64 = (body.get('audio_b64') or body.get('audio') or '')
                    if not audio_b64:
                        continue
                    audio_bytes = base64.b64decode(audio_b64)
                    yield {
                        'seq': seq,
                        'is_final': seq == len(sentences) - 1,
                        'audio_b64': audio_b64,
                        'duration_ms': int(body.get('duration_ms') or 0),
                        'checksum': _checksum(audio_bytes),
                        'text': sentence,
                    }
                except Exception:
                    # swallow to keep stream alive
                    await asyncio.sleep(0)